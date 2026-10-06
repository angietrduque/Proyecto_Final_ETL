"""Reporte de calidad legible (docs/reporte_calidad.md), regenerado en cada ejecución del pipeline."""
from datetime import datetime

import pandas as pd

from src.utils.config import RAIZ, cargar_config


def _md(df: pd.DataFrame, max_filas: int = 60) -> str:
    df = df.head(max_filas).copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda x: "" if pd.isna(x) else f"{x:,.2f}")
    df = df.astype(str).replace({"nan": "", "None": "", "<NA>": ""})
    cab = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return cab + "\n".join("| " + " | ".join("" if pd.isna(v) else str(v).replace("|", "/") for v in r) + " |" for r in df.values.tolist())


def generar(t: dict, cal: pd.DataFrame, comp: pd.DataFrame, okr: pd.DataFrame, g: dict) -> None:
    ki = g.get("kpi_indicadores", pd.DataFrame())
    cfg = cargar_config()
    log = t["log_cargas"]
    v = t["validaciones"]
    c = t["conteos"]
    ok = okr.copy()
    ok["cumple"] = ok.cumple.map({True: "✅", False: "❌"}).fillna("— (monitoreo)")
    comp_r = comp.groupby(["nivel", "cod_indicador"]).agg(esperadas=("celdas_esperadas", "sum"),
                                                         observadas=("celdas_observadas", "sum"),
                                                         con_proyeccion=("celdas_con_proyeccion", "sum")).reset_index()
    comp_r["completitud_%"] = comp_r.observadas / comp_r.esperadas * 100
    comp_r["con_proyeccion_%"] = comp_r.con_proyeccion / comp_r.esperadas * 100
    sin = g.get("sin_dato")
    texto = f"""# Reporte de calidad del pipeline

Generado automáticamente por `main.py` · ejecución `{t['log_cargas'].id_ejecucion.iloc[0] if len(log) else ''}` ·
{datetime.now():%Y-%m-%d %H:%M} · versión del pipeline {cfg['proyecto']['version_pipeline']}

> Este archivo se sobrescribe en cada ejecución. Las tablas completas están en `data/ctl/*.parquet`,
> `data/gold/kpi_*.csv` y en la base SQL (`ctl_*`, `gold_kpi_*`).

## 1. OKR (O1-O3 problema de estudio · O4 habilitador de calidad)

{_md(ok[['objetivo_cod', 'kr', 'kpi', 'meta', 'valor', 'cumple', 'interpretacion']])}

## 1b. KPIs de negocio (último valor, referencia y semáforo)

{_md(ki[['codigo', 'eje', 'indicador', 'formula', 'valor_texto', 'unidad', 'anio', 'referencia', 'semaforo', 'tipo_dato']]) if len(ki) else ''}

## 2. Bitácora de cargas Bronze

{_md(log[log.capa == 'bronze'][['fuente', 'dataset', 'estado', 'filas', 'mensaje']], 80)}

## 3. Calidad por dataset (reglas de aceptación)

{_md(cal[['dataset', 'registros_evaluados', 'registros_validos', 'registros_rechazados', 'tasa_validos_pct', 'tasa_rechazo_pct', 'rechazos_trazados_pct']], 80)}

## 4. Rechazos (motivo trazado)

{_md(t['rechazos'].groupby(['dataset', 'regla', 'motivo']).size().rename('registros').reset_index())}

## 5. Reglas de consistencia y conciliación

{_md(v[v.tipo.isin(['consistencia', 'consistencia_entre_fuentes', 'trazabilidad'])][['dataset', 'regla', 'evaluados', 'afectados', 'resultado', 'detalle']], 120)}

## 6. Completitud 2000-2025 (núcleo de indicadores)

{_md(comp_r)}

## 7. Conteo de registros antes y después de cada transformación

{_md(c[['capa', 'dataset', 'paso', 'filas_entrada', 'filas_salida', 'diferencia', 'nota']], 250)}
"""
    (RAIZ / "docs" / "reporte_calidad.md").write_text(texto, encoding="utf-8")
