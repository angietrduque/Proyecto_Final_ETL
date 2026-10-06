"""Pipeline ETL Corea del Sur — arquitectura Medallion (Bronze -> Silver -> Gold -> SQL / Power BI).

Uso:
    python main.py                       # pipeline completo: bronze + silver + gold + KPIs + carga SQL + reporte
    python main.py --sin-api             # no consulta APIs (usa la última versión de WB/OECD guardada en bronze)
    python main.py --capa silver         # reconstruye desde silver (bronze ya existe) en adelante
    python main.py --capa gold           # sólo gold + KPIs + carga
    python main.py --sin-db              # no carga en la base SQL (sólo archivos parquet/csv)
    python main.py --fuente kosis oecd   # limita la ingesta bronze a algunas fuentes
"""
import argparse
import json
import logging
import sys
import time
import warnings

import pandas as pd

from src.ingestion import bronze
from src.load import sql
from src.transformation import gold, silver
from src.utils.config import RAIZ, cargar_config, ruta
from src.utils.control import Control
from src.utils.logs import configurar_logging
from src.validation import kpis, reporte

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
CAPAS = ["bronze", "silver", "gold"]


def persistir_control(ctl: Control) -> dict[str, pd.DataFrame]:
    """Tablas ctl de esta ejecución + histórico de cargas (para el KPI de ejecuciones exitosas)."""
    carpeta = RAIZ / "data" / "ctl"
    carpeta.mkdir(parents=True, exist_ok=True)
    t = ctl.tablas()
    hist_p = carpeta / "log_cargas_historico.parquet"
    previo = pd.read_parquet(hist_p) if hist_p.exists() else pd.DataFrame()
    historico = pd.concat([previo, t["log_cargas"]], ignore_index=True)
    historico.to_parquet(hist_p, index=False)
    for n, df in t.items():
        df.to_parquet(carpeta / f"{n}.parquet", index=False)
    t["log_cargas_historico"] = historico
    return t


def bronze_sql() -> dict[str, pd.DataFrame]:
    """Bronze en la base: el manifest (versiones) y los registros vigentes tal como llegaron (JSON por fila)."""
    man = pd.read_csv(ruta("bronze") / bronze.MANIFEST, dtype=str)
    filas = []
    for r in man[man.vigente == "True"].itertuples():
        df, meta = bronze.leer_vigente(r.fuente, r.dataset)
        for i, rec in enumerate(df.astype(object).where(df.notna(), None).to_dict("records")):
            filas.append({"fuente": r.fuente, "dataset": r.dataset, "version": r.sha256[:12], "fila": i,
                          "fecha_extraccion": r.fecha_extraccion, "registro": json.dumps(rec, ensure_ascii=False)})
    return {"manifest": man, "registros": pd.DataFrame(filas)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Pipeline ETL Corea del Sur (Medallion)")
    ap.add_argument("--capa", choices=CAPAS + ["todo"], default="todo", help="capa desde la que se ejecuta")
    ap.add_argument("--fuente", nargs="+", choices=["kosis", "worldbank", "oecd", "unwpp"])
    ap.add_argument("--sin-api", action="store_true", help="no consultar APIs (usa la última versión en bronze)")
    ap.add_argument("--sin-db", action="store_true", help="no cargar la base de datos SQL")
    args = ap.parse_args()

    configurar_logging()
    log = logging.getLogger("pipeline")
    cfg = cargar_config()
    ctl = Control()
    t0 = time.perf_counter()
    log.info("=== %s · v%s · ejecución %s ===", cfg["proyecto"]["nombre"], cfg["proyecto"]["version_pipeline"], ctl.id_ejecucion)
    inicio = CAPAS.index(args.capa) if args.capa != "todo" else 0
    if inicio == 2:  # sólo gold: se reutiliza el control de calidad de la última ejecución de silver
        previo = RAIZ / "data" / "ctl"
        for nombre, lista in (("conteos", ctl.conteos), ("rechazos", ctl.rechazos), ("validaciones", ctl.validaciones)):
            p = previo / f"{nombre}.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                lista += df[df.dataset.ne("") & ~df.dataset.str.startswith("gold.")].to_dict("records") \
                    if nombre == "validaciones" else df.to_dict("records")
    try:
        if inicio <= 0:
            log.info("--- BRONZE: ingesta")
            bronze.ejecutar(ctl, args.fuente, usar_api=not args.sin_api)
        if inicio <= 1:
            log.info("--- SILVER: limpieza, homologación y validación")
            silver.ejecutar(ctl)
        log.info("--- GOLD: modelo dimensional, escenarios e indicadores")
        g = gold.ejecutar(ctl)
    except Exception:
        log.exception("El pipeline se detuvo por un error no controlado")
        ctl.registrar_carga("pipeline", "-", "-", "fallo", mensaje="error no controlado (ver logs/pipeline.log)")
        persistir_control(ctl)
        return 1
    for nombre in ["fact_indicador_historico", "fact_indicador_proyeccion"]:
        ctl.registrar_carga("gold", "Pipeline", nombre, "exito", filas=len(g[nombre]), metodo="pipeline")

    log.info("--- KPIs de calidad y OKR")
    t = persistir_control(ctl)
    cal = kpis.calidad_dataset(t["conteos"], t["rechazos"])
    comp = kpis.completitud(g["fact_indicador_historico"], g["fact_indicador_proyeccion"])
    okr = kpis.okr(cal, comp, t["log_cargas_historico"], t["validaciones"], g)
    kpi_ind = kpis.kpis_negocio(g)
    for n, df in (("kpi_calidad_dataset", cal), ("kpi_completitud", comp), ("kpi_okr", okr), ("kpi_indicadores", kpi_ind)):
        df.to_parquet(ruta("gold") / f"{n}.parquet", index=False)
        df.to_csv(ruta("gold") / f"{n}.csv", index=False, encoding="utf-8-sig")
    g.update({"kpi_calidad_dataset": cal, "kpi_completitud": comp, "kpi_okr": okr, "kpi_indicadores": kpi_ind})

    if not args.sin_db:
        log.info("--- CARGA SQL")
        silver_t = {n: silver.leer(n) for n in ["fact_historico", "fact_proyeccion", "fact_contraste",
                                                "fact_internacional", "conciliacion", "sin_dato", "dim_escenario"]}
        tablas = {"ctl": {k: v for k, v in t.items()}, "bronze": bronze_sql(), "silver": silver_t, "gold": g}
        res = sql.cargar(tablas)
        sql.ddl({"gold": g}, RAIZ / "sql")
        res.to_csv(RAIZ / "data" / "ctl" / "resumen_carga_sql.csv", index=False)
    reporte.generar(t, cal, comp, okr, g)
    log.info("--- Documentación: figuras, diagramas y diccionario de datos")
    from src.analytics import diagramas, diccionario, figuras
    figuras.generar_todas()
    diagramas.arquitectura()
    diagramas.modelo()
    diccionario.generar()
    from src.analytics import powerbi   # capa de servicio para el tablero (data/gold/powerbi/pbi_*.parquet)
    for n, df in powerbi.tablas_servicio().items():
        powerbi.SERV.mkdir(parents=True, exist_ok=True)
        df.to_parquet(powerbi.SERV / f"{n}.parquet", index=False)
    seg = time.perf_counter() - t0
    falla = okr[okr.cumple == False]  # noqa: E712
    log.info("=== Fin en %.1f s · resultados clave que no cumplen: %d · reporte: docs/reporte_calidad.md ===", seg, len(falla))
    return 0


if __name__ == "__main__":
    sys.exit(main())
