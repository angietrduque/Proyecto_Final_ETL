"""Genera el diccionario de datos de la capa Gold a partir de las tablas reales (docs/data_dictionary/).

Así el diccionario no se desactualiza: tipos, claves, nulos y ejemplos salen de los parquet; las descripciones
de columnas y tablas se mantienen aquí, en un solo lugar.
"""
import pandas as pd

from src.load.sql import FK, PK
from src.utils.config import RAIZ

TABLAS = {
    "dim_tiempo": "Calendario anual 1925-2072. Separa periodo Histórico (≤2025) y Proyección.",
    "dim_territorio": "País, 17 si-do, agregado CNSJ (Chungnam+Sejong) y países de comparación.",
    "dim_sexo": "Total, hombres, mujeres.",
    "dim_edad": "Grupos quinquenales, grupos funcionales (0-14, 15-64, 65+) y grupos de la EAPS.",
    "dim_indicador": "Catálogo de indicadores: definición, fórmula, unidad, fuente maestra/contraste, rango válido, aditividad.",
    "dim_escenario": "29 escenarios de proyección KOSTAT 2022-2072 (medio + 28 alternativos) con sus supuestos de fecundidad, esperanza de vida y migración.",
    "dim_supuesto": "Supuestos A/B/C/D de participación laboral de los escenarios propios.",
    "dim_tipo_dato": "Naturaleza del dato: observado, estimado, calculado, proyección oficial, escenario propio, inferencia propia.",
    "dim_fuente": "Versión vigente de cada dataset de Bronze (fuente, tabla, URL, fecha de extracción, sha256).",
    "fact_indicador_historico": "Grano: año × territorio × sexo × edad × indicador. Datos observados/estimados y derivados. Nunca proyecciones.",
    "fact_indicador_proyeccion": "Grano: año × territorio × sexo × edad × indicador × escenario × edición. Proyección KOSTAT y derivados.",
    "fact_fuerza_laboral_escenario": "Grano: año × escenario de población × supuesto × sexo × grupo EAPS. Escenario propio (no pronóstico).",
    "fact_riesgo_regional": "Grano: si-do (año de referencia 2025). Componentes e índice compuesto de riesgo (inferencia propia).",
    "fact_riesgo_sensibilidad": "Grano: esquema de ponderación × si-do. Índice y ranking del riesgo regional con 7 esquemas (robustez).",
    "fact_escenarios_sensibilidad": "Grano: supuesto × variante de parámetro. Variación de la fuerza laboral potencial 2025-2050 y 2025-2072.",
    "fact_comparacion_internacional": "Grano: año × país × indicador × fuente (World Bank / OECD).",
    "fact_conciliacion": "Pares fuente maestra vs contraste y fórmulas del pipeline vs publicadas, con diferencia %.",
    "dataset_nacional_anual": "Tabla plana: una fila por año (1970-2072) con los indicadores nacionales clave en columnas.",
    "dataset_regional_anual": "Tabla plana: una fila por año y si-do con los indicadores regionales clave.",
    "kpi_okr": "OKR del estudio: 13 resultados clave (O1 diagnóstico, O2 impacto laboral, O3 decisión, O4 calidad).",
    "kpi_calidad_dataset": "Registros evaluados, válidos y rechazados por dataset (reglas de aceptación).",
    "kpi_completitud": "Celdas con dato / esperadas 2000-2025 por indicador y territorio.",
}
COLUMNAS = {
    "anio": "Año calendario (clave hacia dim_tiempo)", "cod_territorio": "Código de territorio (KOSIS si-do / ISO3)",
    "cod_sexo": "T total, H hombres, M mujeres", "cod_edad": "Código de grupo de edad (dim_edad)",
    "cod_indicador": "Código del indicador (dim_indicador)", "valor": "Valor numérico en la unidad del indicador",
    "tipo_dato": "Naturaleza del dato (dim_tipo_dato)", "estado": "definitivo / preliminar (según marca 'p)' de la fuente) / proyectado",
    "fuente": "Institución productora (KOSIS, WB, OECD) o 'Pipeline' si es cálculo propio",
    "dataset": "Dataset de origen en Bronze (o regla de cálculo)", "tabla_fuente": "ID de la tabla en la fuente (tblId / código WDI / dataflow)",
    "version_fuente": "Primeros 12 caracteres del sha256 del archivo crudo", "es_derivado": "True si el valor es un cálculo del pipeline",
    "cod_escenario": "Escenario KOSTAT (dim_escenario)", "edicion_proyeccion": "Edición de la proyección (nacional 2022-2072 o provincial 2022-2052)",
    "cod_supuesto": "Supuesto de participación A/B/C/D (dim_supuesto)",
    "factor_cobertura": "Población 15+ EAPS / población KOSTAT en 2025, por sexo y grupo (ajuste de escala)",
    "esquema": "Esquema de ponderación/normalización del índice de riesgo", "en_top5": "Si el si-do queda entre los 5 de mayor riesgo",
    "variante": "Parámetro modificado del supuesto (base = parámetros de config.yaml)", "poblacion_proyectada": "Población KOSTAT del grupo sexo × edad (personas)",
    "tasa_participacion": "Tasa de participación supuesta (%)", "fuerza_laboral_potencial": "poblacion_proyectada × tasa_participacion / 100 (personas)",
    "fuerza_laboral_total_anio": "Suma de la fuerza laboral potencial del año, escenario y supuesto",
    "fuerza_laboral_total_base": "Misma suma en el año base 2025", "indice_base_2025": "fuerza_laboral_total_anio / base × 100",
    "indice_riesgo": "Promedio de los 6 componentes estandarizados (z) con signo de riesgo",
    "ranking_riesgo": "1 = mayor riesgo", "nivel_riesgo": "Terciles: Alto / Medio / Bajo",
    "tipo_dato_poblacion": "estimado (≤2022) o proyeccion_oficial (≥2023) para la población y estructura de esa fila",
    "dif_pct": "(contraste - maestra) / |maestra| × 100", "dentro_tolerancia": "|dif_pct| ≤ 3 %",
    "comparable": "False cuando las definiciones no son comparables (p. ej. participación modelada OIT)",
}


def generar() -> pd.DataFrame:
    gold = RAIZ / "data" / "gold"
    filas = []
    for tabla, desc in TABLAS.items():
        p = gold / f"{tabla}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        for c in df.columns:
            s = df[c]
            ejemplo = s.dropna().astype(str).iloc[0] if s.notna().any() else ""
            filas.append({"tabla": tabla, "descripcion_tabla": desc, "columna": c, "tipo": str(s.dtype),
                          "clave": "PK" if c in PK.get(tabla, []) else ("FK → " + FK[c][0] if c in FK and not tabla.startswith("dim_") and tabla in PK else ""),
                          "descripcion": COLUMNAS.get(c, ""), "nulos_pct": round(s.isna().mean() * 100, 2),
                          "valores_distintos": int(s.nunique()), "ejemplo": ejemplo[:40]})
    dic = pd.DataFrame(filas)
    out = RAIZ / "docs" / "data_dictionary"
    out.mkdir(parents=True, exist_ok=True)
    ind = pd.read_csv(RAIZ / "config" / "mappings" / "indicadores.csv")
    with pd.ExcelWriter(out / "diccionario_datos.xlsx") as xw:
        dic.to_excel(xw, sheet_name="columnas", index=False)
        ind.to_excel(xw, sheet_name="indicadores", index=False)
    lineas = ["# Diccionario de datos — capa Gold", "",
              "Generado automáticamente por `src/analytics/diccionario.py` a partir de `data/gold/*.parquet`. "
              "Versión Excel: `diccionario_datos.xlsx` (hojas *columnas* e *indicadores*).", ""]
    for tabla, g in dic.groupby("tabla", sort=False):
        n = len(pd.read_parquet(gold / f"{tabla}.parquet"))
        lineas += [f"## `{tabla}` ({n:,} filas)".replace(",", "."), "", TABLAS[tabla], "",
                   "| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |", "|---|---|---|---|---|---|"]
        lineas += [f"| {r.columna} | {r.tipo} | {r.clave} | {r.descripcion} | {r.nulos_pct} | {str(r.ejemplo).replace('|', '/')} |"
                   for r in g.itertuples()]
        lineas.append("")
    lineas += ["## Catálogo de indicadores (`dim_indicador`)", "",
               "| Código | Nombre | Categoría | Fórmula | Unidad | Fuente maestra | Contraste | Derivado |", "|---|---|---|---|---|---|---|---|"]
    lineas += [f"| {r.cod_indicador} | {r.nombre} | {r.categoria} | {r.formula} | {r.unidad} | {r.fuente_maestra} | "
               f"{'' if pd.isna(r.fuente_contraste) else r.fuente_contraste} | {r.es_derivado} |" for r in ind.itertuples()]
    (out / "diccionario_datos.md").write_text("\n".join(lineas), encoding="utf-8")
    return dic


if __name__ == "__main__":
    print(len(generar()), "columnas documentadas")
