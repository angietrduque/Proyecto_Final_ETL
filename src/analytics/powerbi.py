"""Tablero de Power BI como proyecto PBIP (modelo TMDL + reporte PBIR) generado desde la capa Gold.

1. Capa de servicio para BI: data/gold/powerbi/pbi_*.parquet — tablas con la forma exacta que necesita cada visual
   (las transformaciones quedan en Python, auditadas; Power Query sólo lee los archivos).
2. Modelo semántico TMDL: tablas, tipos, relaciones por año y territorio y medidas DAX documentadas.
3. Reporte PBIR: portada + 7 páginas con menú lateral; estética limpia (azul marino, rojo y azul de la bandera de
   Corea, fondos claros) y convención continuo = observado/estimado · discontinuo = proyección.

Uso: python -m src.analytics.powerbi   ->  powerbi/ETL_Corea_Grupo6.pbip (abrir con Power BI Desktop y guardar como .pbix)
"""
import json
import shutil
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import RAIZ

GOLD = RAIZ / "data" / "gold"
SERV = GOLD / "powerbi"
EXT = RAIZ.parent                      # entregables fuera del repositorio
PBI = EXT / "powerbi"
NOMBRE = "ETL_Corea_Grupo6"
GRAF = RAIZ.parent / "elementos_graficos"
ROJO, ROJO_OSC, TINTA, GRIS, AZUL, AMBAR, VERDE = "#C8102E", "#8F0B21", "#1E1E1E", "#555555", "#1F4E79", "#E69F00", "#3A9E8E"
ESC_CLAVE = ["medio", "fecundidad_baja", "fecundidad_alta", "migracion_cero", "migracion_alta", "envejecimiento_rapido",
             "envejecimiento_lento"]
ICONO_SEM = {"Crítico": "🔴 Crítico", "Alerta": "🟠 Alerta", "Normal": "🟢 Normal", "Contexto": "⚪ Contexto"}


def g(nombre):
    return pd.read_parquet(GOLD / f"{nombre}.parquet")


# =============================================================================================== 1. capa de servicio
def tablas_servicio() -> dict[str, pd.DataFrame]:
    h, p = g("fact_indicador_historico"), g("fact_indicador_proyeccion")
    terr, edad, esc = g("dim_territorio"), g("dim_edad"), g("dim_escenario")
    nom_esc = dict(zip(esc.cod_escenario, esc.nombre_escenario))
    t = {}

    n = g("dataset_nacional_anual")
    n = n[n.cod_territorio == "00"].drop(columns="cod_territorio")
    t["pbi_nacional"] = n

    anios = pd.DataFrame({"anio": range(1970, 2073)})
    anios["periodo"] = np.where(anios.anio <= 2025, "Histórico", "Proyección")
    anios["decada"] = (anios.anio // 10 * 10).astype(str) + "s"
    t["pbi_anios"] = anios
    t["pbi_anio_sel"] = pd.DataFrame({"anio_piramide": [2000, 2010, 2022, 2025, 2030, 2040, 2050, 2060, 2072]})

    # escenarios oficiales clave (se agrega 2022, año base estimado, para que las líneas arranquen juntas)
    base = p[(p.cod_territorio == "00") & (p.cod_sexo == "T") & (p.edicion_proyeccion == "KOSTAT 2022-2072")
             & p.cod_escenario.isin(ESC_CLAVE)]
    sel = [("POBLACION", "15-64", "Población 15-64 (millones)", 1e-6), ("DEP_VEJEZ", "TOTAL", "Dependencia de vejez", 1),
           ("PROP_65MAS", "TOTAL", "Población 65+ (%)", 1)]
    partes = []
    for ind, ed, nombre, f in sel:
        d = base[(base.cod_indicador == ind) & (base.cod_edad == ed)][["anio", "cod_escenario", "valor"]].copy()
        hb = h[(h.cod_indicador == ind) & (h.cod_edad == ed) & (h.cod_territorio == "00") & (h.cod_sexo == "T") & (h.anio == 2022)]
        if len(hb):
            d = pd.concat([d] + [pd.DataFrame({"anio": [2022], "cod_escenario": [e], "valor": [hb.valor.iloc[0]]}) for e in ESC_CLAVE])
        d["indicador"] = nombre
        d["valor"] = d.valor * f
        partes.append(d)
    e = pd.concat(partes, ignore_index=True)
    e["escenario"] = e.cod_escenario.map(nom_esc)
    e["orden_escenario"] = e.cod_escenario.map({c: i for i, c in enumerate(ESC_CLAVE)})
    t["pbi_escenarios"] = e.sort_values(["indicador", "orden_escenario", "anio"]).reset_index(drop=True)
    t["pbi_escenario_sel"] = pd.DataFrame({"escenario": [nom_esc[c] for c in ESC_CLAVE], "orden": range(len(ESC_CLAVE))})

    fl = g("fact_fuerza_laboral_escenario")
    fl = fl[fl.cod_escenario.isin(ESC_CLAVE)].groupby(["anio", "cod_escenario", "cod_supuesto"], as_index=False).agg(
        flp=("fuerza_laboral_potencial", "sum"), indice_2025=("indice_base_2025", "first"))
    sup = g("dim_supuesto")
    fl["supuesto"] = fl.cod_supuesto.map(dict(zip(sup.cod_supuesto, sup.nombre)))
    fl["escenario"] = fl.cod_escenario.map(nom_esc)
    t["pbi_flp"] = fl

    # pirámide: estimación hasta 2022 + proyección medio desde 2023, % del total de cada año
    q = edad[edad.tipo == "quinquenal"][["cod_edad", "etiqueta", "orden"]].astype({"orden": int})
    ph = h[(h.cod_indicador == "POBLACION") & (h.cod_territorio == "00") & h.cod_sexo.isin(["H", "M"]) & h.cod_edad.isin(q.cod_edad)]
    pp = p[(p.cod_indicador == "POBLACION") & (p.cod_territorio == "00") & p.cod_sexo.isin(["H", "M"]) & p.cod_edad.isin(q.cod_edad)
           & (p.cod_escenario == "medio") & (p.edicion_proyeccion == "KOSTAT 2022-2072")]
    pir = pd.concat([ph, pp])[["anio", "cod_sexo", "cod_edad", "valor"]].merge(q, on="cod_edad")
    pir["pct"] = pir.valor / pir.groupby("anio").valor.transform("sum") * 100
    pir["sexo"] = pir.cod_sexo.map({"H": "Hombres", "M": "Mujeres"})
    pir["grupo"] = np.where(pir.orden <= 3, "0-14", np.where(pir.orden <= 13, "15-64", "65+"))
    t["pbi_piramide"] = pir.rename(columns={"etiqueta": "edad", "valor": "poblacion"}).drop(columns=["cod_sexo"])

    tp = h[(h.cod_indicador == "TASA_PARTICIPACION") & (h.cod_territorio == "00") & h.cod_sexo.isin(["H", "M"])
           & h.cod_edad.isin(["15-19", "20-29", "30-39", "40-49", "50-59", "60+"])]
    tp = tp[["anio", "cod_sexo", "cod_edad", "valor"]].rename(columns={"valor": "tasa"})
    tp["sexo"] = tp.cod_sexo.map({"H": "Hombres", "M": "Mujeres"})
    tp["edad"] = tp.cod_edad
    tp["orden"] = tp.cod_edad.map({"15-19": 1, "20-29": 2, "30-39": 3, "40-49": 4, "50-59": 5, "60+": 6})
    t["pbi_participacion"] = tp.drop(columns=["cod_sexo", "cod_edad"])

    sido = terr[terr.tipo.isin(["sido"])][["cod_territorio", "nombre_es", "nombre_en", "region_macro", "orden"]].astype({"orden": int})
    t["pbi_territorio"] = sido.rename(columns={"nombre_es": "si_do", "nombre_en": "nombre_ingles"})
    rg = g("fact_riesgo_regional")
    cols = ["cod_territorio", "tfr", "prop_65mas", "dep_vejez", "tasa_participacion", "ind_reemplazo_laboral",
            "var_pob_15_64_2052_pct", "var_nacimientos_10a_pct", "indice_riesgo", "ranking_riesgo", "nivel_riesgo"]
    t["pbi_riesgo"] = rg[cols]
    reg = g("dataset_regional_anual")
    reg = reg[reg.cod_territorio.isin(sido.cod_territorio)][["anio", "cod_territorio", "TFR", "NACIMIENTOS", "PROP_65MAS",
                                                            "DEP_VEJEZ", "TASA_PARTICIPACION", "POB_15_64", "tipo_dato_poblacion"]]
    t["pbi_regional"] = reg

    i = g("fact_comparacion_internacional")
    paises = {"00": "Corea del Sur", "JPN": "Japón", "ITA": "Italia", "DEU": "Alemania", "ESP": "España", "USA": "Estados Unidos",
              "FRA": "Francia", "OED": "Promedio OCDE"}
    nombres = {"TFR": "Fecundidad (TFR)", "PROP_65MAS": "Población 65+ (%)", "DEP_VEJEZ": "Dependencia de vejez",
               "TASA_PARTICIPACION": "Participación laboral (%)", "ESPERANZA_VIDA": "Esperanza de vida"}
    ii = i[(i.fuente == "WB") & i.cod_territorio.isin(paises) & i.cod_indicador.isin(nombres) & (i.cod_edad.isin(["TOTAL", "15+"]))]
    ii = ii[["anio", "cod_territorio", "cod_indicador", "valor"]].copy()
    ii["pais"] = ii.cod_territorio.map(paises)
    ii["indicador"] = ii.cod_indicador.map(nombres)
    ii["es_corea"] = ii.cod_territorio.eq("00")
    t["pbi_internacional"] = ii.drop(columns=["cod_territorio"])

    k = g("kpi_indicadores")
    k["semaforo_icono"] = k.semaforo.map(ICONO_SEM)
    k["ultimo_valor"] = k.valor_texto + " (" + k.anio.astype(str) + ")"
    t["pbi_kpi"] = k
    o = g("kpi_okr")
    o["estado"] = np.where(o.cumple.fillna(False), "✅ Logrado", "❌ Pendiente")
    t["pbi_okr"] = o[["objetivo_cod", "eje", "objetivo", "kr", "kpi", "meta", "valor", "estado", "interpretacion", "tabla_gold"]]
    t["pbi_calidad"] = g("kpi_calidad_dataset")
    c = g("fact_conciliacion")
    c = c[c.comparable & c.anio.between(2000, 2025)]
    c["fuente_contraste"] = np.where(c.tipo_comparacion == "fórmula del pipeline", "Fórmula vs " + c.fuente_contraste,
                                     c.fuente_contraste)
    t["pbi_conciliacion"] = c.groupby(["cod_indicador", "fuente_contraste"], as_index=False).agg(
        pares=("dif_pct", "size"), pct_dentro=("dentro_tolerancia", "mean"), dif_max_pct=("dif_pct", lambda s: s.abs().max()))
    t["pbi_conciliacion"]["pct_dentro"] *= 100

    # tipos limpios para Power BI: enteros sin nulos -> int64; textos -> str; bool -> bool
    for nombre, df in t.items():
        df = df.reset_index(drop=True)
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                df[col] = df[col].astype("int64") if df[col].notna().all() else df[col].astype("float64")
            elif pd.api.types.is_bool_dtype(df[col]):
                df[col] = df[col].astype(bool)
            elif pd.api.types.is_float_dtype(df[col]):
                df[col] = df[col].astype("float64")
            else:
                df[col] = df[col].astype(str).replace({"nan": None, "<NA>": None, "None": None})
        t[nombre] = df
    return t


# =============================================================================================== 2. modelo TMDL
def _guid():
    return str(uuid.uuid4())


def _tipo(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_integer_dtype(s):
        return "int64"
    if pd.api.types.is_float_dtype(s):
        return "double"
    return "string"


def _q(nombre: str) -> str:
    return f"'{nombre}'" if not nombre.replace("_", "").isalnum() else nombre


# medidas por tabla: (nombre, expresión DAX, formato, descripción)
F_M = '#,0.0" M"'
MEDIDAS = {
    "pbi_nacional": [
        ("Fecundidad (TFR)", "SUM(pbi_nacional[TFR])", "0.00", "Tasa global de fecundidad (observado, KOSIS)"),
        ("Nivel de reemplazo", "IF(NOT ISBLANK([Fecundidad (TFR)]), 2.1)", "0.0", "Referencia demográfica: 2,1 hijos por mujer"),
        ("Nacimientos (miles)", "DIVIDE(SUM(pbi_nacional[NACIMIENTOS]), 1000)", "#,0", "Nacidos vivos (observado)"),
        ("Defunciones (miles)", "DIVIDE(SUM(pbi_nacional[DEFUNCIONES]), 1000)", "#,0", "Defunciones (observado)"),
        ("Esperanza de vida", "SUM(pbi_nacional[ESPERANZA_VIDA])", "0.0", "Años (observado)"),
        ("% 0-14", "SUM(pbi_nacional[PROP_0_14])", "0.0", "Estimado ≤2022 · proyección KOSTAT medio ≥2023"),
        ("% 15-64", "SUM(pbi_nacional[PROP_15_64])", "0.0", "Estimado ≤2022 · proyección KOSTAT medio ≥2023"),
        ("% 65+", "SUM(pbi_nacional[PROP_65MAS])", "0.0", "Estimado ≤2022 · proyección KOSTAT medio ≥2023"),
        ("Dependencia de vejez · estimada",
         'CALCULATE(SUM(pbi_nacional[DEP_VEJEZ]), pbi_nacional[tipo_dato_poblacion] = "estimado")', "0.0",
         "P65+/P15-64×100 sobre población estimada (≤2022)"),
        ("Dependencia de vejez · proyección", "CALCULATE(SUM(pbi_nacional[DEP_VEJEZ]), pbi_nacional[anio] >= 2022)", "0.0",
         "Proyección oficial KOSTAT (escenario medio) desde 2023; arranca en el año base 2022"),
        ("Población 15-64 · estimada",
         'CALCULATE(DIVIDE(SUM(pbi_nacional[POB_15_64]), 1e6), pbi_nacional[tipo_dato_poblacion] = "estimado")', F_M, ""),
        ("Población 15-64 · proyección", "CALCULATE(DIVIDE(SUM(pbi_nacional[POB_15_64]), 1e6), pbi_nacional[anio] >= 2022)", F_M, ""),
        ("Reemplazo laboral · estimado",
         'CALCULATE(SUM(pbi_nacional[IND_REEMPLAZO_LABORAL]), pbi_nacional[tipo_dato_poblacion] = "estimado")', "0",
         "Jóvenes 15-24 por cada 100 personas de 55-64"),
        ("Reemplazo laboral · proyección", "CALCULATE(SUM(pbi_nacional[IND_REEMPLAZO_LABORAL]), pbi_nacional[anio] >= 2022)", "0", ""),
        ("Referencia 100", "IF(NOT ISBLANK([Reemplazo laboral · estimado]) || NOT ISBLANK([Reemplazo laboral · proyección]), 100)", "0", ""),
        ("Población activa observada", "DIVIDE(SUM(pbi_nacional[POB_ACTIVA]), 1e6)", F_M, "EAPS, promedio anual"),
        ("PIB por hora", "SUM(pbi_nacional[PIB_HORA])", "0.0", "USD PPA constantes (OECD)"),
        ("Participación laboral 15+", "SUM(pbi_nacional[TASA_PARTICIPACION])", "0.0", "EAPS (observado)"),
    ],
    "pbi_kpi": [(f"KPI {c}", f'CALCULATE(MAX(pbi_kpi[valor]), pbi_kpi[codigo] = "{c}")', fmt, d) for c, fmt, d in [
        ("KPI-01", "0.00", "Fecundidad (hijos por mujer)"), ("KPI-02", '0.0" %"', "Nacimientos vs 2000"),
        ("KPI-03", "#,0", "Crecimiento natural"), ("KPI-05", '0.0" %"', "Población 65+"),
        ("KPI-06", "0.0", "Dependencia de vejez 2025"), ("KPI-07", '0.0" %"', "Población 15-64 a 2050"),
        ("KPI-08", "0", "Reemplazo laboral"), ("KPI-09", '0.0" %"', "Participación 15+"), ("KPI-10", '0.0" pp"', "Brecha de género"),
        ("KPI-11", '0.0" %"', "Fuerza laboral potencial a 2050"), ("KPI-12", "0", "Si-do en riesgo alto")]],
    "pbi_escenarios": [
        ("Población 15-64 por escenario",
         'CALCULATE(SUM(pbi_escenarios[valor]), pbi_escenarios[indicador] = "Población 15-64 (millones)")', F_M,
         "Proyección oficial KOSTAT; 2022 = año base estimado"),
        ("Dependencia por escenario", 'CALCULATE(SUM(pbi_escenarios[valor]), pbi_escenarios[indicador] = "Dependencia de vejez")',
         "0.0", "Proyección oficial KOSTAT"),
    ],
    "pbi_flp": [
        ("Fuerza laboral potencial",
         'VAR e = SELECTEDVALUE(pbi_escenario_sel[escenario], "Medio (base)") RETURN '
         'CALCULATE(DIVIDE(SUM(pbi_flp[flp]), 1e6), pbi_flp[escenario] = e)', F_M,
         "Escenario propio (no es pronóstico): población KOSTAT × tasa de participación supuesta"),
        ("Índice FLP (2025 = 100)",
         'VAR e = SELECTEDVALUE(pbi_escenario_sel[escenario], "Medio (base)") RETURN '
         'CALCULATE(AVERAGE(pbi_flp[indice_2025]), pbi_flp[escenario] = e)', "0.0", ""),
        ("Escenario seleccionado", 'SELECTEDVALUE(pbi_escenario_sel[escenario], "Medio (base)")', "", ""),
    ],
    "pbi_piramide": [
        ("Hombres (%)", 'VAR a = SELECTEDVALUE(pbi_anio_sel[anio_piramide], 2025) RETURN '
                        '-CALCULATE(SUM(pbi_piramide[pct]), pbi_piramide[sexo] = "Hombres", pbi_piramide[anio] = a)',
         '0.0;0.0', "% de la población total del año (se grafica a la izquierda)"),
        ("Mujeres (%)", 'VAR a = SELECTEDVALUE(pbi_anio_sel[anio_piramide], 2025) RETURN '
                        'CALCULATE(SUM(pbi_piramide[pct]), pbi_piramide[sexo] = "Mujeres", pbi_piramide[anio] = a)', "0.0", ""),
        ("Año de la pirámide", 'VAR a = SELECTEDVALUE(pbi_anio_sel[anio_piramide], 2025) RETURN '
                               'a & IF(a <= 2022, " · estimada", " · proyección KOSTAT medio")', "", ""),
    ],
    "pbi_participacion": [
        ("Participación 2025", "CALCULATE(AVERAGE(pbi_participacion[tasa]), pbi_participacion[anio] = 2025)", "0.0", ""),
        ("Participación mujeres", 'CALCULATE(AVERAGE(pbi_participacion[tasa]), pbi_participacion[sexo] = "Mujeres")', "0.0", ""),
    ],
    "pbi_riesgo": [
        ("Índice de riesgo", "AVERAGE(pbi_riesgo[indice_riesgo])", "0.00", "Inferencia propia: promedio de 6 componentes estandarizados"),
        ("Si-do en riesgo alto", 'CALCULATE(COUNTROWS(pbi_riesgo), pbi_riesgo[nivel_riesgo] = "Alto")', "0", ""),
    ],
    "pbi_regional": [
        ("TFR 2025 por si-do", "CALCULATE(AVERAGE(pbi_regional[TFR]), pbi_regional[anio] = 2025)", "0.00", ""),
    ],
    "pbi_internacional": [
        ("Fecundidad (país)", 'CALCULATE(AVERAGE(pbi_internacional[valor]), pbi_internacional[indicador] = "Fecundidad (TFR)")', "0.00", ""),
        ("65+ (país)", 'CALCULATE(AVERAGE(pbi_internacional[valor]), pbi_internacional[indicador] = "Población 65+ (%)")', "0.0", ""),
        ("Dependencia (país)", 'CALCULATE(AVERAGE(pbi_internacional[valor]), pbi_internacional[indicador] = "Dependencia de vejez")', "0.0", ""),
    ],
    "pbi_calidad": [
        ("Registros válidos (%)", "DIVIDE(SUM(pbi_calidad[registros_validos]), SUM(pbi_calidad[registros_evaluados])) * 100", "0.00", ""),
        ("Rechazo (%)", "DIVIDE(SUM(pbi_calidad[registros_rechazados]), SUM(pbi_calidad[registros_evaluados])) * 100", "0.00", ""),
        ("Registros evaluados", "SUM(pbi_calidad[registros_evaluados])", "#,0", ""),
    ],
    "pbi_conciliacion": [
        ("Pares dentro de ±3 %", "DIVIDE(SUMX(pbi_conciliacion, pbi_conciliacion[pares] * pbi_conciliacion[pct_dentro]), "
                                 "SUM(pbi_conciliacion[pares]))", '0.0" %"', ""),
    ],
    "pbi_okr": [("Resultados clave logrados", 'CALCULATE(COUNTROWS(pbi_okr), pbi_okr[estado] = "✅ Logrado") & " de " & COUNTROWS(pbi_okr)', "", "")],
}
RELACIONES = [("pbi_nacional", "anio", "pbi_anios", "anio"), ("pbi_escenarios", "anio", "pbi_anios", "anio"),
              ("pbi_flp", "anio", "pbi_anios", "anio"), ("pbi_internacional", "anio", "pbi_anios", "anio"),
              ("pbi_participacion", "anio", "pbi_anios", "anio"), ("pbi_regional", "anio", "pbi_anios", "anio"),
              ("pbi_riesgo", "cod_territorio", "pbi_territorio", "cod_territorio"),
              ("pbi_regional", "cod_territorio", "pbi_territorio", "cod_territorio")]
ORDEN_POR = {("pbi_piramide", "edad"): "orden", ("pbi_participacion", "edad"): "orden",
             ("pbi_escenarios", "escenario"): "orden_escenario", ("pbi_escenario_sel", "escenario"): "orden",
             ("pbi_territorio", "si_do"): "orden"}
DESCRIPCIONES = {
    "pbi_nacional": "Una fila por año (1970-2072), Corea del Sur. Vitales y laborales observados; población y estructura "
                    "estimadas hasta 2022 y proyección KOSTAT medio desde 2023 (columna tipo_dato_poblacion).",
    "pbi_escenarios": "Proyección oficial KOSTAT para 7 escenarios clave (de 29 en Gold).",
    "pbi_flp": "Escenario propio de fuerza laboral potencial (supuestos A/B/C/D). No es pronóstico.",
    "pbi_riesgo": "Índice de riesgo demográfico-laboral por si-do (inferencia propia, ponderación igual).",
}


def escribir_modelo(t: dict, destino: Path, ruta_gold: str):
    d = destino / f"{NOMBRE}.SemanticModel"
    if d.exists():
        shutil.rmtree(d)
    (d / "definition" / "tables").mkdir(parents=True)
    (d / "definition.pbism").write_text(json.dumps({"version": "4.1", "settings": {}}, indent=2), encoding="utf-8")
    (d / "definition" / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1601\n\n", encoding="utf-8")
    refs = "\n".join(f"ref table {_q(n)}" for n in t)
    orden = json.dumps(["RutaGold"] + list(t), ensure_ascii=False)
    (d / "definition" / "model.tmdl").write_text(
        "model Model\n\tculture: es-ES\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: es-CO\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_QueryOrder = {orden}\n\nannotation __PBI_TimeIntelligenceEnabled = 0\n\n{refs}\n\n", encoding="utf-8")
    (d / "definition" / "expressions.tmdl").write_text(
        f'/// Carpeta de la capa Gold. Cambiarla en Transformar datos > Parámetros si el proyecto se mueve.\n'
        f'expression RutaGold = "{ruta_gold}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
        f"\tlineageTag: {_guid()}\n\n\tannotation PBI_ResultType = Text\n\n", encoding="utf-8")
    rel = []
    for a, ca, b, cb in RELACIONES:
        rel.append(f"relationship {_guid()}\n\tfromColumn: {a}.{ca}\n\ttoColumn: {b}.{cb}\n")
    (d / "definition" / "relationships.tmdl").write_text("\n".join(rel) + "\n", encoding="utf-8")
    for n, df in t.items():
        lin = []
        if n in DESCRIPCIONES:
            lin.append(f"/// {DESCRIPCIONES[n]}")
        lin += [f"table {_q(n)}", f"\tlineageTag: {_guid()}", ""]
        for nombre, expr, fmt, desc in MEDIDAS.get(n, []):
            if desc:
                lin.append(f"\t/// {desc}")
            lin.append(f"\tmeasure '{nombre}' = {expr}")
            if fmt:
                lin.append(f"\t\tformatString: {fmt}")
            lin += [f"\t\tlineageTag: {_guid()}", ""]
        for col in df.columns:
            tipo = _tipo(df[col])
            lin += [f"\tcolumn {_q(col)}", f"\t\tdataType: {tipo}"]
            if tipo == "double":
                lin.append("\t\tformatString: 0.00")
            elif tipo == "int64":
                lin.append("\t\tformatString: 0")
            lin += [f"\t\tlineageTag: {_guid()}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {col}"]
            if (n, col) in ORDEN_POR:
                lin.append(f"\t\tsortByColumn: {ORDEN_POR[(n, col)]}")
            if n == "pbi_territorio" and col == "nombre_ingles":
                lin.append("\t\tdataCategory: StateOrProvince")
            lin += ["", "\t\tannotation SummarizationSetBy = User", ""]
        lin += [f"\tpartition {_q(n)} = m", "\t\tmode: import", "\t\tsource =", "\t\t\t\tlet",
                f'\t\t\t\t\tFuente = Parquet.Document(File.Contents(RutaGold & "powerbi\\{n}.parquet"))',
                "\t\t\t\tin", "\t\t\t\t\tFuente", "", "\tannotation PBI_ResultType = Table", ""]
        (d / "definition" / "tables" / f"{n}.tmdl").write_text("\n".join(lin), encoding="utf-8")


# =============================================================================================== 3. reporte PBIR
S_VIS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json"
S_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json"


def L(v):  # literal
    return {"expr": {"Literal": {"Value": v}}}


def txt(s):
    return L("'" + s.replace("'", "''") + "'")


def color(hexa):
    return {"solid": {"color": L(f"'{hexa}'")}}


def campo(tabla, prop, medida=False):
    k = "Measure" if medida else "Column"
    return {k: {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": prop}}


def proy(tabla, prop, medida=False, nombre=None):
    p = {"field": campo(tabla, prop, medida), "queryRef": f"{tabla}.{prop}", "nativeQueryRef": prop}
    if nombre:
        p["displayName"] = nombre
    if not medida:
        p["active"] = True
    return p


class Pagina:
    def __init__(self, nombre, menu, titulo, subtitulo, icono="barras", fondo=None, transparencia=0):
        self.nombre, self.menu, self.titulo, self.subtitulo, self.icono = nombre, menu, titulo, subtitulo, icono
        self.fondo, self.transparencia = fondo, transparencia
        self.visuales = []
        self._z = 1000

    def add(self, nombre, tipo, x, y, w, h, query=None, objects=None, vco=None, sort=None, filtros=None):
        self._z += 100
        v = {"$schema": S_VIS, "name": nombre,
             "position": {"x": x, "y": y, "z": self._z, "height": h, "width": w, "tabOrder": self._z},
             "visual": {"visualType": tipo}}
        if query:
            q = {"queryState": query}
            if sort:
                q["sortDefinition"] = {"sort": sort, "isDefaultSort": True}
            v["visual"]["query"] = q
        if objects:
            v["visual"]["objects"] = objects
        if vco:
            v["visual"]["visualContainerObjects"] = vco
        v["visual"]["drillFilterOtherVisuals"] = True
        if filtros:
            v["filterConfig"] = {"filters": filtros}
        self.visuales.append(v)
        return v


# Paleta limpia: azul marino como estructura, rojo y azul de la bandera de Corea como acentos, fondos claros
MARINO, MARINO_2, ROJO_K, AZUL_K = "#0F2747", "#1C3A66", "#CD2E3A", "#0047A0"
FONDO_PAG, BORDE, AZUL_CLARO, ROJO_CLARO, REJILLA = "#F4F6FA", "#E3E8F0", "#EAF0F9", "#FBECEE", "#E9EDF3"
TINTA_K, GRIS_K, AMBAR_K, VERDE_K = "#1E2430", "#5F6B7A", "#D98E04", "#2F8F7F"
ROJO_OSC_PORTADA = "#8F0B21"     # la portada conserva su estética roja UAO
X0, W_CONT = 196, 1068          # zona de contenido (a la derecha de la barra lateral)
MENU = [("resumen", "Resumen"), ("natalidad", "Natalidad"), ("envejecimiento", "Envejecimiento"),
        ("fuerza_laboral", "Fuerza laboral"), ("regiones", "Regiones"), ("contexto_ocde", "Corea vs OCDE"),
        ("calidad", "Calidad y OKR")]


def contenedor(titulo=None, borde=True, fondo="#FFFFFF", subtitulo=None, transparencia="0D"):
    o = {"title": [{"properties": {"show": L("true" if titulo else "false"),
                                   **({"text": txt(titulo), "fontColor": color(MARINO), "fontSize": L("13D"),
                                       "fontFamily": txt("Segoe UI Semibold"), "bold": L("true")} if titulo else {})}}],
         "border": [{"properties": {"show": L("true" if borde else "false"), "color": color(BORDE), "radius": L("10D")}}],
         "background": [{"properties": {"show": L("true" if fondo else "false"), "color": color(fondo or "#FFFFFF"),
                                        "transparency": L(transparencia)}}],
         "dropShadow": [{"properties": {"show": L("true" if borde else "false"), "color": color(MARINO),
                                        "transparency": L("92D"), "position": txt("Outer"), "preset": txt("BottomRight")}}]}
    if subtitulo:
        o["subTitle"] = [{"properties": {"show": L("true"), "text": txt(subtitulo), "fontColor": color(GRIS_K), "fontSize": L("10D")}}]
    return o


def bloque(pag, nombre, x, y, w, h, fondo, transparencia="0D", radio="0D"):
    """Rectángulo de color (textbox vacío con fondo): bandas, barra lateral, acentos y velos."""
    pag.add(nombre, "textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": " "}]}]}}]},
            vco={"background": [{"properties": {"show": L("true"), "color": color(fondo), "transparency": L(transparencia)}}],
                 "border": [{"properties": {"show": L("true" if radio != "0D" else "false"), "color": color(fondo), "radius": L(radio)}}]})


def textbox(pag, nombre, x, y, w, h, runs, alinear=None):
    """runs: lista de párrafos; cada párrafo lista de (texto, tamaño, color, negrita)."""
    pars = []
    for par in runs:
        p = {"textRuns": [{"value": t, "textStyle": {"fontFamily": "Segoe UI Semibold" if b else "Segoe UI",
                                                     "fontSize": f"{s}pt", "color": c, **({"fontWeight": "bold"} if b else {})}}
                          for t, s, c, b in par]}
        if alinear:
            p["horizontalTextAlignment"] = alinear
        pars.append(p)
    pag.add(nombre, "textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": pars}}]},
            vco={"background": [{"properties": {"show": L("false")}}], "border": [{"properties": {"show": L("false")}}]})


def imagen(pag, nombre, x, y, w, h, archivo, escala="'Fit'", marco=None):
    vco = {"background": [{"properties": {"show": L("false")}}], "border": [{"properties": {"show": L("false")}}]}
    if marco:
        vco["border"] = [{"properties": {"show": L("true"), "color": color(marco), "radius": L("14D")}}]
        vco["dropShadow"] = [{"properties": {"show": L("true"), "color": color(MARINO), "transparency": L("80D"),
                                             "preset": txt("BottomRight")}}]
    pag.add(nombre, "image", x, y, w, h, objects={"general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {
        "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": archivo}}}}}],
        "imageScaling": [{"properties": {"imageScalingType": L(escala)}}]}, vco=vco)


def boton(pag, nombre, x, y, w, h, texto_, destino, fondo, color_txt, tam=11, alinear="left", radio="8D", hover=None):
    """Botón de navegación de un solo color, sin contorno (el contorno se apaga en todos los estados)."""
    hover = hover or fondo
    sin_borde = {"show": L("false"), "lineColor": color(fondo), "weight": L("0D"), "transparency": L("100D")}
    pag.add(nombre, "actionButton", x, y, w, h, objects={
        # En los botones, "show" va en una entrada sin selector; el estilo, en cada estado
        # esquinas redondeadas: Power BI las lee del estado "default" y en entero (L), no en decimal (D)
        "shape": [{"properties": {"tileShape": txt("rectangleRounded")}},
                  {"properties": {"tileShape": txt("rectangleRounded"), "roundEdge": L(radio.replace("D", "L"))},
                   "selector": {"id": "default"}}],
        "icon": [{"properties": {"show": L("false")}}, {"properties": {"show": L("false")}, "selector": {"id": "default"}}],
        "text": [{"properties": {"show": L("true")}},
                 {"properties": {"show": L("true"), "text": txt(texto_), "fontColor": color(color_txt), "fontSize": L(f"{tam}D"),
                                 "fontFamily": txt("Segoe UI Semibold"), "horizontalAlignment": txt(alinear),
                                 "leftMargin": L("14D")}, "selector": {"id": "default"}}],
        "fill": [{"properties": {"show": L("true")}},
                 {"properties": {"show": L("true"), "fillColor": color(fondo), "transparency": L("0D")}, "selector": {"id": "default"}},
                 {"properties": {"fillColor": color(hover), "transparency": L("0D")}, "selector": {"id": "hover"}},
                 {"properties": {"fillColor": color(hover), "transparency": L("0D")}, "selector": {"id": "selected"}}],
        "outline": [{"properties": {"show": L("false")}}] +
                   [{"properties": sin_borde, "selector": {"id": s}} for s in ("default", "hover", "press", "selected")]},
        vco={"visualLink": [{"properties": {"show": L("true"), "type": txt("PageNavigation"), "navigationSection": txt(destino)}}],
             "border": [{"properties": {"show": L("false"), "radius": L(radio)}}],
             "background": [{"properties": {"show": L("false")}}],
             "dropShadow": [{"properties": {"show": L("false")}}],
             "title": [{"properties": {"show": L("false")}}]})


def navegacion(pag):
    """Barra lateral azul marino: logo, secciones (la actual en blanco con marca roja) y regreso a la portada."""
    bloque(pag, "barraLateral", 0, 0, 184, 720, MARINO)
    imagen(pag, "logoBlanco", 16, 20, 152, 46, "logo_uao2_blanco.png")
    textbox(pag, "menuTitulo", 16, 76, 160, 34, [[("SECCIONES", 9, "#8EA3C2", True)]])
    for i, (destino, etiqueta) in enumerate(MENU):
        actual = destino == pag.nombre
        y = 108 + i * 50
        boton(pag, f"nav{i}", 12, y, 160, 40, etiqueta, destino, "#FFFFFF" if actual else MARINO,
              MARINO if actual else "#DCE4F0", tam=12, hover="#FFFFFF" if actual else MARINO_2)
        if actual:
            bloque(pag, "marcaActual", 4, y + 6, 4, 28, ROJO_K, radio="2D")
    boton(pag, "navPortada", 12, 656, 160, 36, "⟵  Portada", "portada", MARINO_2, "#FFFFFF", tam=10, hover=AZUL_K)


def encabezado(pag):
    """Encabezado blanco y limpio: franja superior con el rojo y el azul de la bandera, ícono, título y subtítulo."""
    bloque(pag, "banda", 184, 0, 1096, 80, "#FFFFFF")
    bloque(pag, "franjaRoja", 184, 0, 548, 5, ROJO_K)
    bloque(pag, "franjaAzul", 732, 0, 548, 5, AZUL_K)
    bloque(pag, "circulo", 204, 17, 50, 50, AZUL_CLARO, radio="25D")
    imagen(pag, "icono", 214, 27, 30, 30, f"{pag.icono}_azul.png")
    textbox(pag, "titulo", 264, 6, 900, 50, [[(pag.titulo, 22, MARINO, True)]])
    textbox(pag, "subtitulo", 266, 44, 920, 34, [[(pag.subtitulo, 11, GRIS_K, False)]])
    imagen(pag, "bandera", 1196, 20, 64, 42, "bandera_coreadelsur.png")


def tarjeta(pag, nombre, x, y, w, h, tabla, medida, etiqueta, nota=None, acento=AZUL_K):
    """KPI en tarjeta blanca: cifra en el color de acento y una franja superior del mismo color."""
    pag.add(nombre, "card", x, y, w, h,
            query={"Values": {"projections": [proy(tabla, medida, True, etiqueta)]}},
            objects={"labels": [{"properties": {"color": color(acento), "fontSize": L("27D"), "fontFamily": txt("Segoe UI Semibold")}}],
                     "categoryLabels": [{"properties": {"show": L("true"), "color": color(TINTA_K), "fontSize": L("11D")}}]},
            vco={"title": [{"properties": {"show": L("false")}}],
                 "background": [{"properties": {"show": L("true"), "color": color("#FFFFFF"), "transparency": L("0D")}}],
                 "border": [{"properties": {"show": L("true"), "color": color(BORDE), "radius": L("10D")}}],
                 "dropShadow": [{"properties": {"show": L("true"), "color": color(MARINO), "transparency": L("92D"),
                                                "preset": txt("BottomRight")}}],
                 **({"subTitle": [{"properties": {"show": L("true"), "text": txt(nota), "fontColor": color(GRIS_K),
                                                  "fontSize": L("9D")}}]} if nota else {})})
    bloque(pag, nombre + "Acento", x + 14, y, w - 28, 5, acento, radio="2D")


def _ejes(obj):
    obj["categoryAxis"] = [{"properties": {"showAxisTitle": L("false"), "gridlineShow": L("false"), "fontSize": L("10D"),
                                           "labelColor": color(GRIS_K)}}]
    obj["valueAxis"] = [{"properties": {"showAxisTitle": L("false"), "gridlineColor": color(REJILLA), "fontSize": L("10D"),
                                        "labelColor": color(GRIS_K)}}]
    obj["legend"] = [{"properties": {"show": L("true"), "position": txt("Top"), "fontSize": L("10D"), "labelColor": color(TINTA_K)}}]
    return obj


def linea(pag, nombre, x, y, w, h, tabla_x, col_x, medidas, titulo, colores, discontinuas=(), leyenda=None, sub=None):
    q = {"Category": {"projections": [proy(tabla_x, col_x)]},
         "Y": {"projections": [proy(t_, m, True) for t_, m in medidas]}}
    if leyenda:
        q["Series"] = {"projections": [proy(*leyenda)]}
    obj = _ejes({"lineStyles": [{"properties": {"strokeWidth": L("3D")}}]})
    obj["categoryAxis"][0]["properties"]["axisType"] = txt("Scalar")
    if leyenda and leyenda[1] == "pais":
        obj["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": campo(*leyenda), "Right": {"Literal": {"Value": f"'{pais}'"}}}}}]}}
            for pais, c in (("Corea del Sur", ROJO_K), ("Promedio OCDE", MARINO), ("Japón", AZUL_K), ("Italia", AMBAR_K),
                            ("Estados Unidos", VERDE_K), ("Alemania", "#8E6BB0"), ("España", "#A7B0BE"), ("Francia", "#C9B8D9"))]
        obj["lineStyles"] += [{"properties": {"strokeWidth": L("5D")}, "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": campo(*leyenda), "Right": {"Literal": {"Value": "'Corea del Sur'"}}}}}]}}]
    if not leyenda:
        obj["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{t_}.{m}"}}
                            for (t_, m), c in zip(medidas, colores)]
        obj["lineStyles"] += [{"properties": {"lineStyle": txt("dashed")}, "selector": {"metadata": f"{t_}.{m}"}}
                              for (t_, m) in medidas if m in discontinuas]
    pag.add(nombre, "lineChart", x, y, w, h, query=q, objects=obj, vco=contenedor(titulo, subtitulo=sub),
            sort=[{"field": campo(tabla_x, col_x), "direction": "Ascending"}])


def barras(pag, nombre, x, y, w, h, tipo, cat, medidas, titulo, colores=None, leyenda=None, orden=None, sub=None, etiquetas=True):
    q = {"Category": {"projections": [proy(*cat)]}, "Y": {"projections": [proy(t_, m, True) for t_, m in medidas]}}
    if leyenda:
        q["Series"] = {"projections": [proy(*leyenda)]}
    obj = _ejes({"labels": [{"properties": {"show": L("true" if etiquetas else "false"), "fontSize": L("9D"), "color": color(TINTA_K)}}]})
    obj["legend"][0]["properties"]["show"] = L("true" if (leyenda or len(medidas) > 1) else "false")
    obj["valueAxis"][0]["properties"]["show"] = L("false" if etiquetas else "true")
    if colores and not leyenda:
        # color por defecto sin selector (las barras de una sola medida lo necesitan) + color por medida
        obj["dataPoint"] = [{"properties": {"fill": color(colores[0])}}] + \
                           [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{t_}.{m}"}}
                            for (t_, m), c in zip(medidas, colores)]
    pag.add(nombre, tipo, x, y, w, h, query=q, objects=obj, vco=contenedor(titulo, subtitulo=sub), sort=orden)


def tabla(pag, nombre, x, y, w, h, columnas, titulo=None, tam="10D"):
    pag.add(nombre, "tableEx", x, y, w, h,
            query={"Values": {"projections": [proy(t_, c, med, nom) for t_, c, med, nom in columnas]}},
            objects={"columnHeaders": [{"properties": {"fontColor": color("#FFFFFF"), "backColor": color(MARINO),
                                                       "fontFamily": txt("Segoe UI Semibold"), "fontSize": L(tam)}}],
                     "values": [{"properties": {"fontSize": L(tam), "fontColorPrimary": color(TINTA_K),
                                                "backColorSecondary": color("#F3F6FB")}}],
                     "grid": [{"properties": {"rowPadding": L("4D"), "gridHorizontalColor": color(BORDE)}}]},
            vco=contenedor(titulo))


def segmentador(pag, nombre, x, y, w, h, tabla_, col, titulo, unico=True):
    pag.add(nombre, "slicer", x, y, w, h, query={"Values": {"projections": [proy(tabla_, col)]}},
            objects={"data": [{"properties": {"mode": txt("Dropdown")}}],
                     "selection": [{"properties": {"singleSelect": L("true" if unico else "false")}}],
                     "header": [{"properties": {"show": L("true"), "text": txt(titulo), "fontColor": color(MARINO),
                                                "fontSize": L("10D")}}],
                     "items": [{"properties": {"fontColor": color(TINTA_K), "fontSize": L("10D")}}]},
            vco=contenedor())


def nota_lectura(pag, nombre, x, y, w, h, titulo, lineas, acento=AZUL_K):
    """Recuadro de lectura en azul muy claro con una barra de acento."""
    bloque(pag, nombre + "Fondo", x, y, w, h, AZUL_CLARO, radio="10D")
    bloque(pag, nombre + "Barra", x, y + 12, 5, h - 24, acento, radio="2D")
    textbox(pag, nombre, x + 14, y + 6, w - 22, h - 12,
            [[(titulo, 13, acento, True)]] + [[(l, 10, c, False)] for l, c in lineas])


def paginas() -> list[Pagina]:
    P = []
    C = X0                      # x de inicio del contenido
    # ------------------------------------------------------------------ 0 Portada (se conserva; botones de un solo color)
    p = Pagina("portada", "Portada", "Portada", "", fondo="fondo3.jpg", transparencia=0)
    bloque(p, "velo", 0, 0, 1280, 720, "#5A0612", transparencia="22D")
    bloque(p, "panel", 40, 150, 700, 420, ROJO_OSC_PORTADA, transparencia="15D", radio="18D")
    imagen(p, "logo", 44, 36, 300, 86, "logo_uao2_blanco.png")
    imagen(p, "bandera", 1150, 40, 90, 60, "bandera_coreadelsur.png")
    textbox(p, "etiqueta", 70, 170, 640, 30, [[("PROYECTO ETL 2026 · GRUPO 6 · TABLERO DE ANÁLISIS", 11, "#F7C5CB", True)]])
    textbox(p, "titulo", 70, 200, 650, 150, [[("Natalidad, envejecimiento y", 30, "#FFFFFF", True)],
                                             [("fuerza laboral en Corea del Sur", 30, "#FFFFFF", True)]])
    textbox(p, "pregunta", 70, 345, 640, 90, [[("¿Cómo impactará la disminución de la natalidad y el envejecimiento poblacional "
                                                "en la disponibilidad futura de la fuerza laboral?", 13, "#FFE4E7", False)]])
    textbox(p, "equipo", 70, 438, 640, 60, [[("Angie Rodríguez · Karin Parra · Maicol Narváez · Miguel Méndez", 11, "#FFFFFF", True)],
                                            [("Maestría en Inteligencia Artificial y Ciencia de Datos · UAO", 10, "#F7C5CB", False)]])
    boton(p, "entrar", 70, 505, 260, 46, "Ingresar al tablero  ⟶", "resumen", "#FFFFFF", ROJO_K, tam=14, alinear="center",
          radio="23D", hover="#FBE3E5")
    imagen(p, "foto1", 780, 150, 220, 200, "madre_bebe.jpg", "'Fill'", marco="#FFFFFF")
    imagen(p, "foto2", 1020, 150, 220, 200, "familia.jpg", "'Fill'", marco="#FFFFFF")
    imagen(p, "foto3", 780, 370, 460, 200, "trabajadores.jpg", "'Fill'", marco="#FFFFFF")
    bloque(p, "barraNav", 0, 610, 1280, 110, "#2B0308", transparencia="25D")
    textbox(p, "navTit", 40, 612, 400, 36, [[("EXPLORE LAS SECCIONES", 10, "#F7C5CB", True)]])
    for i, (destino, etiqueta) in enumerate(MENU):
        fondo_b = ROJO_K if i % 2 == 0 else AZUL_K           # rojo y azul de la bandera, alternados
        boton(p, f"nav{i}", 40 + i * 172, 650, 160, 44, etiqueta, destino, fondo_b, "#FFFFFF",
              tam=11, alinear="center", radio="22D", hover=MARINO)
    P.append(p)

    # ------------------------------------------------------------------ 1 Resumen
    p = Pagina("resumen", "Resumen", "Corea del Sur en 14 indicadores",
               "Resumen ejecutivo · último valor, referencia y semáforo de cada KPI del estudio", "barras")
    cards = [("KPI KPI-01", "Fecundidad 2025", "reemplazo: 2,1", ROJO_K),
             ("KPI KPI-02", "Nacimientos vs 2000", "observado · KOSIS", AZUL_K),
             ("KPI KPI-05", "% 65+ en 2025", "ONU: ≥ 20 % superenvejecida", MARINO),
             ("KPI KPI-07", "Pob. 15-64 a 2050", "proyección oficial", ROJO_K),
             ("KPI KPI-08", "Reemplazo laboral", "jóvenes por 100 a retiro", AMBAR_K),
             ("KPI KPI-11", "Fuerza laboral a 2050", "escenario propio A", VERDE_K)]
    for i, (m, et, nota, acento) in enumerate(cards):
        tarjeta(p, f"card{i}", C + i * 179, 94, 170, 114, "pbi_kpi", m, et, nota, acento)
    tabla(p, "tablaKPI", C, 222, 774, 486, [("pbi_kpi", "codigo", False, "KPI"), ("pbi_kpi", "indicador", False, "Indicador"),
                                            ("pbi_kpi", "ultimo_valor", False, "Último valor"),
                                            ("pbi_kpi", "referencia", False, "Referencia"),
                                            ("pbi_kpi", "semaforo_icono", False, "Semáforo")],
          "14 KPIs del problema · una fórmula cada uno", tam="9D")
    imagen(p, "foto", C + 788, 222, 280, 200, "madre_bebe.jpg", "'Fill'", marco="#FFFFFF")
    nota_lectura(p, "lectura", C + 788, 434, 280, 274, "¿Qué nos dicen los datos?", [
        ("La fecundidad está en 38 % del nivel de reemplazo y los nacimientos cayeron 60 % desde 2000.", TINTA_K),
        ("La población en edad de trabajar perderá cerca de un tercio a 2050 en los 29 escenarios oficiales.", TINTA_K),
        ("Línea continua = dato observado · discontinua = proyección oficial.", GRIS_K)])
    P.append(p)

    # ------------------------------------------------------------------ 2 Natalidad
    p = Pagina("natalidad", "Natalidad", "Natalidad y fecundidad",
               "Datos observados · KOSIS Vital Statistics 1970-2025 y TFR por si-do", "bebe")
    barras(p, "nacimientos", C, 94, 530, 298, "columnChart", ("pbi_anios", "anio"), [("pbi_nacional", "Nacimientos (miles)")],
           "Nacimientos por año (miles)", [AZUL_K], etiquetas=False,
           orden=[{"field": campo("pbi_anios", "anio"), "direction": "Ascending"}])
    linea(p, "tfr", C + 544, 94, 524, 298, "pbi_anios", "anio", [("pbi_nacional", "Fecundidad (TFR)"), ("pbi_nacional", "Nivel de reemplazo")],
          "Hijos por mujer frente al nivel de reemplazo (2,1)", [ROJO_K, "#8C96A5"], discontinuas=("Nivel de reemplazo",))
    barras(p, "tfrSido", C, 406, 400, 302, "clusteredBarChart", ("pbi_territorio", "si_do"), [("pbi_regional", "TFR 2025 por si-do")],
           "Fecundidad 2025 por si-do", [ROJO_K], orden=[{"field": campo("pbi_regional", "TFR 2025 por si-do", True), "direction": "Ascending"}])
    linea(p, "defunciones", C + 414, 406, 440, 302, "pbi_anios", "anio",
          [("pbi_nacional", "Nacimientos (miles)"), ("pbi_nacional", "Defunciones (miles)")],
          "Nacimientos vs defunciones (miles)", [AZUL_K, MARINO], sub="desde 2020 mueren más personas de las que nacen")
    imagen(p, "foto", C + 868, 406, 200, 302, "familia.jpg", "'Fill'", marco="#FFFFFF")
    P.append(p)

    # ------------------------------------------------------------------ 3 Envejecimiento
    p = Pagina("envejecimiento", "Envejecimiento", "Envejecimiento de la población",
               "Estimación oficial hasta 2022 · proyección KOSTAT (escenario medio) desde 2023", "mayor")
    segmentador(p, "anioPir", C, 94, 380, 62, "pbi_anio_sel", "anio_piramide", "Año de la pirámide (2025 por defecto)")
    barras(p, "piramide", C, 166, 380, 542, "clusteredBarChart", ("pbi_piramide", "edad"),
           [("pbi_piramide", "Hombres (%)"), ("pbi_piramide", "Mujeres (%)")], "Pirámide de población (% del total)",
           [AZUL_K, ROJO_K], orden=[{"field": campo("pbi_piramide", "edad"), "direction": "Descending"}], etiquetas=False)
    p.visuales[-1]["visual"]["objects"]["valueAxis"] = [{"properties": {"show": L("true"), "showAxisTitle": L("false"), "fontSize": L("10D")}}]
    p.visuales[-1]["visual"]["objects"]["general"] = [{"properties": {"layout": txt("Overlap")}}]
    linea(p, "estructura", C + 394, 94, 674, 298, "pbi_anios", "anio",
          [("pbi_nacional", "% 0-14"), ("pbi_nacional", "% 15-64"), ("pbi_nacional", "% 65+")],
          "Grandes grupos de edad (% de la población)", [AMBAR_K, AZUL_K, ROJO_K])
    linea(p, "dependencia", C + 394, 406, 430, 302, "pbi_anios", "anio",
          [("pbi_nacional", "Dependencia de vejez · estimada"), ("pbi_nacional", "Dependencia de vejez · proyección")],
          "Mayores por cada 100 personas en edad de trabajar", [ROJO_K, ROJO_K], discontinuas=("Dependencia de vejez · proyección",))
    linea(p, "ev", C + 838, 406, 230, 302, "pbi_anios", "anio", [("pbi_nacional", "Esperanza de vida")],
          "Esperanza de vida (años)", [VERDE_K])
    P.append(p)

    # ------------------------------------------------------------------ 4 Fuerza laboral
    p = Pagina("fuerza_laboral", "Fuerza laboral", "Fuerza laboral futura",
               "Escenarios oficiales KOSTAT (7 de 29) y escenarios propios A/B/C/D de participación (no son pronósticos)", "maletin")
    linea(p, "pob1564", C, 94, 530, 298, "pbi_anios", "anio", [("pbi_escenarios", "Población 15-64 por escenario")],
          "Población de 15-64 años por escenario oficial (millones)", [], leyenda=("pbi_escenarios", "escenario"))
    segmentador(p, "escFLP", C + 544, 94, 524, 60, "pbi_escenario_sel", "escenario", "Escenario de población para A/B/C/D")
    linea(p, "flp", C + 544, 162, 524, 230, "pbi_anios", "anio", [("pbi_flp", "Fuerza laboral potencial")],
          "Fuerza laboral potencial (millones) · escenario propio", [], leyenda=("pbi_flp", "supuesto"))
    linea(p, "reemplazo", C, 406, 470, 302, "pbi_anios", "anio",
          [("pbi_nacional", "Reemplazo laboral · estimado"), ("pbi_nacional", "Reemplazo laboral · proyección"),
           ("pbi_nacional", "Referencia 100")],
          "Señal temprana: jóvenes 15-24 por cada 100 de 55-64", [AZUL_K, AZUL_K, "#8C96A5"],
          discontinuas=("Reemplazo laboral · proyección", "Referencia 100"))
    barras(p, "participacion", C + 484, 406, 584, 302, "clusteredColumnChart", ("pbi_participacion", "edad"),
           [("pbi_participacion", "Participación 2025")], "Participación laboral por edad y sexo, 2025 (%)",
           leyenda=("pbi_participacion", "sexo"), orden=[{"field": campo("pbi_participacion", "edad"), "direction": "Ascending"}])
    P.append(p)

    # ------------------------------------------------------------------ 5 Regiones
    p = Pagina("regiones", "Regiones", "¿Dónde es mayor el riesgo?",
               "Índice de riesgo demográfico-laboral 2025 · inferencia propia con 6 componentes y ponderación igual", "mapa")
    barras(p, "indice", C, 94, 430, 614, "clusteredBarChart", ("pbi_territorio", "si_do"), [("pbi_riesgo", "Índice de riesgo")],
           "Índice de riesgo por si-do (mayor = más riesgo)", [ROJO_K],
           orden=[{"field": campo("pbi_riesgo", "Índice de riesgo", True), "direction": "Descending"}])
    tabla(p, "componentes", C + 444, 94, 624, 378, [
        ("pbi_territorio", "si_do", False, "Si-do"), ("pbi_riesgo", "nivel_riesgo", False, "Nivel"),
        ("pbi_riesgo", "tfr", False, "TFR"), ("pbi_riesgo", "prop_65mas", False, "% 65+"),
        ("pbi_riesgo", "dep_vejez", False, "Dependencia"), ("pbi_riesgo", "tasa_participacion", False, "Particip."),
        ("pbi_riesgo", "var_pob_15_64_2052_pct", False, "Δ 15-64 a 2052 %")], "Componentes del índice (2025)")
    imagen(p, "mapa", C + 444, 486, 250, 222, "mapa_corea.png", marco=BORDE)
    tarjeta(p, "alto", C + 708, 486, 360, 104, "pbi_riesgo", "Si-do en riesgo alto", "si-do en riesgo alto",
            "tercil superior del índice", ROJO_K)
    nota_lectura(p, "nota", C + 708, 600, 360, 108, "Lectura", [
        ("Busan, Daegu y Gyeongsang: baja fecundidad, alta dependencia y mayor pérdida proyectada de población 15-64.",
         TINTA_K)], ROJO_K)
    P.append(p)

    # ------------------------------------------------------------------ 6 Contexto OCDE
    p = Pagina("contexto_ocde", "Corea vs OCDE", "Corea frente a la OCDE",
               "World Bank WDI (mismo productor para todos los países) · OECD productividad · Corea en rojo", "globo")
    linea(p, "tfrPais", C, 94, 530, 298, "pbi_anios", "anio", [("pbi_internacional", "Fecundidad (país)")],
          "Tasa global de fecundidad", [], leyenda=("pbi_internacional", "pais"))
    linea(p, "p65Pais", C + 544, 94, 524, 298, "pbi_anios", "anio", [("pbi_internacional", "65+ (país)")],
          "Población de 65 años y más (%)", [], leyenda=("pbi_internacional", "pais"))
    linea(p, "depPais", C, 406, 530, 302, "pbi_anios", "anio", [("pbi_internacional", "Dependencia (país)")],
          "Dependencia de vejez", [], leyenda=("pbi_internacional", "pais"))
    linea(p, "pib", C + 544, 406, 320, 302, "pbi_anios", "anio", [("pbi_nacional", "PIB por hora")],
          "PIB por hora trabajada, Corea (USD PPA)", [AZUL_K], sub="asociación, no causalidad")
    imagen(p, "foto", C + 878, 406, 190, 302, "trabajadores_seul.jpg", "'Fill'", marco="#FFFFFF")
    P.append(p)

    # ------------------------------------------------------------------ 7 Calidad
    p = Pagina("calidad", "Calidad y OKR", "Calidad del dato y OKR",
               "OKR orientados al problema (O1-O3) y objetivo habilitador de calidad (O4)", "check")
    for i, (t_, m, et, acento) in enumerate([("pbi_okr", "Resultados clave logrados", "resultados clave (O1-O4)", VERDE_K),
                                             ("pbi_calidad", "Registros válidos (%)", "registros válidos · meta ≥ 98 %", AZUL_K),
                                             ("pbi_calidad", "Rechazo (%)", "rechazo trazado · meta ≤ 2 %", ROJO_K),
                                             ("pbi_conciliacion", "Pares dentro de ±3 %", "conciliación entre fuentes", MARINO)]):
        tarjeta(p, f"k{i}", C + i * 269, 94, 260, 102, t_, m, et, acento=acento)
    tabla(p, "okrTabla", C, 208, W_CONT, 352, [("pbi_okr", "kr", False, "KR"), ("pbi_okr", "kpi", False, "Resultado clave"),
                                               ("pbi_okr", "meta", False, "Meta"), ("pbi_okr", "valor", False, "Logrado"),
                                               ("pbi_okr", "estado", False, "Estado")],
          "O1 diagnóstico · O2 impacto laboral · O3 decisión · O4 calidad", tam="9D")
    tabla(p, "calidadTabla", C, 572, 520, 136, [("pbi_calidad", "dataset", False, "Dataset"),
                                                ("pbi_calidad", "tasa_validos_pct", False, "% válidos"),
                                                ("pbi_calidad", "registros_rechazados", False, "Rechazados")],
          "Reglas de calidad por dataset", tam="9D")
    nota_lectura(p, "controles", C + 534, 572, 534, 136, "Controles aplicados en cada corrida", [
        ("Tipos · nulos esperados e inesperados · duplicados · rangos por indicador · años válidos · integridad referencial · "
         "Σ si-do = nacional · H + M = total · PEA = ocupados + desocupados.", TINTA_K),
        ("Nada se corrige en silencio: cada rechazo queda en ctl.rechazos con su motivo.", GRIS_K)])
    P.append(p)

    for p in P[1:]:
        navegacion(p)
        encabezado(p)
    return P


def _preparar_imagenes(destino: Path) -> dict:
    """Imágenes del tablero a partir de elementos_graficos (recortes, conversión y logo en blanco) e íconos en azul."""
    from PIL import Image, ImageDraw, ImageFont
    out = {}
    im = Image.open(GRAF / "fertilidad1.jpg")
    im.crop((0, 0, im.width - 70, im.height)).save(destino / "familia.jpg", quality=92)       # quita la marca de agua
    Image.open(GRAF / "fertilidad2.jpg").convert("RGB").save(destino / "madre_bebe.jpg", quality=92)
    Image.open(GRAF / "mercado_laboral2.jfif").convert("RGB").save(destino / "trabajadores_seul.jpg", quality=92)
    Image.open(GRAF / "mercado_laboral.png").convert("RGB").save(destino / "trabajadores.jpg", quality=92)
    Image.open(GRAF / "fondo3.jpg").convert("RGB").save(destino / "fondo3.jpg", quality=90)
    for n in ("mapa_corea", "bandera_coreadelsur"):
        Image.open(GRAF / f"{n}.png").convert("RGBA").save(destino / f"{n}.png")
    lg = Image.open(GRAF / "logo_uao2.png").convert("RGBA")
    px = lg.load()
    for x in range(lg.width):
        for y in range(lg.height):
            r, g_, b, a = px[x, y]
            px[x, y] = (255, 255, 255, a if (r > 150 and g_ < 120) else 0)
    lg.save(destino / "logo_uao2_blanco.png")
    fuente = ImageFont.truetype("C:/Windows/Fonts/seguisym.ttf", 200)
    simbolos = {"barras": "\U0001F4CA", "bebe": "\U0001F476", "mayor": "\U0001F474", "maletin": "\U0001F4BC",
                "mapa": "\U0001F5FA", "globo": "\U0001F310", "check": "\u2714"}
    for n, car in simbolos.items():
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x0, y0, x1, y1 = d.textbbox((0, 0), car, font=fuente)
        d.text(((256 - (x1 - x0)) / 2 - x0, (256 - (y1 - y0)) / 2 - y0), car, font=fuente, fill=(0, 71, 160, 255))
        img.save(destino / f"{n}_azul.png")
    return {f.name: f for f in destino.iterdir() if f.suffix in (".png", ".jpg")}


def escribir_reporte(destino: Path, paginas_: list[Pagina]):
    r = destino / f"{NOMBRE}.Report"
    if r.exists():
        shutil.rmtree(r)
    defn = r / "definition"
    (defn / "pages").mkdir(parents=True)
    reg = r / "StaticResources" / "RegisteredResources"
    reg.mkdir(parents=True)
    base = r / "StaticResources" / "SharedResources" / "BaseThemes"
    base.mkdir(parents=True)
    shutil.copy(PBI / "recursos" / "CY24SU10.json", base / "CY24SU10.json")   # tema base de Power BI (Microsoft)
    tema = json.loads((PBI / "tema_uao_corea.json").read_text(encoding="utf-8"))
    (reg / "TemaUAOCorea.json").write_text(json.dumps(tema, ensure_ascii=False, indent=2), encoding="utf-8")
    imagenes = _preparar_imagenes(reg)
    items = [{"name": "TemaUAOCorea.json", "path": "TemaUAOCorea.json", "type": "CustomTheme"}] + \
            [{"name": n, "path": n, "type": "Image"} for n in imagenes]
    (r / "definition.pbir").write_text(json.dumps({"version": "4.0", "datasetReference": {"byPath": {
        "path": f"../{NOMBRE}.SemanticModel"}}}, indent=2), encoding="utf-8")
    (defn / "version.json").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0"}, indent=2), encoding="utf-8")
    report = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.61", "type": "SharedResources"},
                            "customTheme": {"name": "TemaUAOCorea.json", "reportVersionAtImport": "5.61", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
                             {"name": "RegisteredResources", "type": "RegisteredResources", "items": items}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True, "useEnhancedTooltips": True}}
    (defn / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (defn / "pages" / "pages.json").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.nombre for p in paginas_], "activePageName": paginas_[0].nombre}, indent=2), encoding="utf-8")
    for p in paginas_:
        dp = defn / "pages" / p.nombre
        (dp / "visuals").mkdir(parents=True)
        pj = {"$schema": S_PAGE, "name": p.nombre, "displayName": p.menu,
              "displayOption": "FitToPage", "height": 720, "width": 1280,
              "objects": {"background": [{"properties": {"color": color(FONDO_PAG), "transparency": L("0D")}}]}}
        if p.fondo:
            pj["objects"]["background"] = [{"properties": {
                "image": {"image": {"name": txt(p.fondo), "url": {"expr": {"ResourcePackageItem": {
                    "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": p.fondo}}}, "scaling": txt("Fill")}},
                "transparency": L(f"{p.transparencia}D")}}]
        (dp / "page.json").write_text(json.dumps(pj, ensure_ascii=False, indent=2), encoding="utf-8")
        for v in p.visuales:
            v["name"] = f"{p.nombre[:8]}_{v['name']}"[:50]
            dv = dp / "visuals" / v["name"]
            dv.mkdir()
            (dv / "visual.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")


def construir():
    t = tablas_servicio()
    SERV.mkdir(parents=True, exist_ok=True)
    for n, df in t.items():
        df.to_parquet(SERV / f"{n}.parquet", index=False)
    PBI.mkdir(exist_ok=True)
    escribir_modelo(t, PBI, str(GOLD) + "\\")
    escribir_reporte(PBI, paginas())
    (PBI / f"{NOMBRE}.pbip").write_text(json.dumps({"version": "1.0", "artifacts": [{"report": {"path": f"{NOMBRE}.Report"}}],
                                                    "settings": {"enableAutoRecovery": True}}, indent=2), encoding="utf-8")
    print("tablas:", {n: len(df) for n, df in t.items()})
    return PBI / f"{NOMBRE}.pbip"


if __name__ == "__main__":
    print(construir())
