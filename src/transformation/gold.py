"""Capa GOLD: modelo dimensional orientado a los OKR/KPI y listo para Power BI.

Esquema estrella (claves en dim_*; hechos con granularidad declarada):

  dim_tiempo(anio) · dim_territorio(cod_territorio) · dim_sexo(cod_sexo) · dim_edad(cod_edad)
  dim_indicador(cod_indicador) · dim_escenario(cod_escenario) · dim_supuesto(cod_supuesto) · dim_tipo_dato · dim_fuente

  fact_indicador_historico   anio × territorio × sexo × edad × indicador            (observado / estimado / calculado)
  fact_indicador_proyeccion  anio × territorio × sexo × edad × indicador × escenario (proyeccion_oficial / calculado)
  fact_fuerza_laboral_escenario  anio × escenario × supuesto × sexo × grupo EAPS     (escenario_propio)
  fact_riesgo_regional       si-do (año de referencia)                               (inferencia_propia)
  fact_comparacion_internacional  anio × país × indicador                            (observado)
  fact_conciliacion          pares maestra-contraste                                 (control de calidad)
  kpi_calidad_dataset / kpi_okr                                                       (KPIs del pipeline y de negocio)

Distinción de la naturaleza del dato (retroalimentación del profesor): columna tipo_dato en todos los hechos
  observado            dato publicado por la fuente (registro, encuesta)
  estimado             estimación oficial de población (KOSTAT, hasta 2022)
  proyeccion_oficial   proyección KOSTAT 2022-2072 sin modificar
  calculado            indicador derivado con fórmula del pipeline sobre datos observados/estimados/proyectados
  escenario_propio     ejercicio contable del equipo con supuestos explícitos (no es pronóstico)
  inferencia_propia    índice compuesto del equipo (ponderaciones declaradas)
"""
import logging

import numpy as np
import pandas as pd

from src.transformation import derivados, homologacion as hom
from src.transformation.silver import leer as leer_silver
from src.utils.config import cargar_config, ruta
from src.utils.control import Control

log = logging.getLogger("gold")
CLAVE = ["anio", "cod_territorio", "cod_sexo", "cod_edad", "cod_indicador"]
ADITIVOS = ["NACIMIENTOS", "DEFUNCIONES", "CRECIMIENTO_NATURAL", "MATRIMONIOS", "DIVORCIOS", "POBLACION", "POB_15MAS",
            "POB_ACTIVA", "OCUPADOS", "DESOCUPADOS", "INACTIVOS", "POB_CENSO_TOTAL", "POB_EXTRANJERA", "HOGARES"]
EAPS_GRUPO = {"15-19": "15-19", "20-24": "20-29", "25-29": "20-29", "30-34": "30-39", "35-39": "30-39", "40-44": "40-49",
              "45-49": "40-49", "50-54": "50-59", "55-59": "50-59", "60-64": "60+", "65-69": "60+", "70-74": "60+",
              "75-79": "60+", "80-84": "60+", "85+": "60+"}


# ============================================================================================ dimensiones
def dimensiones(silver: dict) -> dict[str, pd.DataFrame]:
    anios = range(1925, 2073)
    per = cargar_config()["periodo"]
    dim_tiempo = pd.DataFrame({"anio": list(anios)})
    dim_tiempo["decada"] = (dim_tiempo.anio // 10 * 10).astype(str) + "s"
    dim_tiempo["quinquenio"] = (dim_tiempo.anio // 5 * 5).astype(str) + "-" + (dim_tiempo.anio // 5 * 5 + 4).astype(str)
    dim_tiempo["periodo"] = np.where(dim_tiempo.anio <= per["historico"]["fin"], "Histórico", "Proyección")
    dim_tiempo["en_ventana_analisis"] = dim_tiempo.anio.between(per["historico"]["inicio"], per["historico"]["fin"])
    dim_tiempo["horizonte"] = pd.cut(dim_tiempo.anio, [0, 1999, 2025, 2035, 2050, 2100],
                                     labels=["Antes de 2000", "2000-2025", "2026-2035", "2036-2050", "2051-2072"]).astype(str)

    dim_territorio = hom.mapping("territorios").copy()
    dim_sexo = hom.mapping("sexo")[["cod_sexo", "nombre"]].copy()
    dim_sexo["orden"] = [0, 1, 2]
    dim_edad = hom.mapping("edades").copy()
    dim_indicador = hom.mapping("indicadores").copy()
    esc = silver["dim_escenario"][["cod_escenario", "nombre_escenario", "familia", "supuesto_fecundidad",
                                   "supuesto_esperanza_vida", "supuesto_migracion", "orden", "etiqueta"]]
    dim_escenario = esc.rename(columns={"etiqueta": "etiqueta_kostat"}).sort_values("orden")
    sup = cargar_config()["escenarios_fuerza_laboral"]["supuestos"]
    dim_supuesto = pd.DataFrame([{"cod_supuesto": k, "nombre": v["nombre"], "descripcion": " ".join(v["descripcion"].split())}
                                 for k, v in sup.items()])
    dim_tipo_dato = pd.DataFrame([
        ("observado", "Dato publicado por la fuente (registro administrativo, encuesta o censo)", 1),
        ("estimado", "Estimación oficial de población de KOSTAT (hasta el año base 2022)", 2),
        ("calculado", "Indicador derivado por el pipeline con fórmula documentada", 3),
        ("proyeccion_oficial", "Proyección oficial KOSTAT 2022-2072 integrada sin modificar", 4),
        ("escenario_propio", "Ejercicio contable del equipo con supuestos explícitos; no es un pronóstico", 5),
        ("inferencia_propia", "Índice compuesto del equipo con ponderaciones declaradas", 6),
    ], columns=["tipo_dato", "descripcion", "orden"])
    man = pd.read_csv(ruta("bronze") / "_manifest.csv", dtype=str)
    man = man[man.vigente == "True"]
    dim_fuente = man[["fuente", "dataset", "tbl_id", "rol", "url", "fecha_extraccion", "sha256", "filas", "archivo_crudo"]].copy()
    dim_fuente["version"] = dim_fuente.sha256.str[:12]
    dim_fuente = dim_fuente.drop(columns="sha256").reset_index(drop=True)
    return {"dim_tiempo": dim_tiempo, "dim_territorio": dim_territorio, "dim_sexo": dim_sexo, "dim_edad": dim_edad,
            "dim_indicador": dim_indicador, "dim_escenario": dim_escenario, "dim_supuesto": dim_supuesto,
            "dim_tipo_dato": dim_tipo_dato, "dim_fuente": dim_fuente}


# ============================================================================================ utilidades
def _agregado_cnsj(df: pd.DataFrame, extra: list[str]) -> pd.DataFrame:
    """Chungnam + Sejong (34 + 29) para series regionales comparables 2000-2025. Sólo indicadores aditivos;
    las tasas laborales se recalculan desde los niveles (nunca se suman tasas)."""
    base = df[df.cod_territorio.isin(["34", "29"]) & df.cod_indicador.isin(ADITIVOS)]
    llaves = [c for c in ["anio", "cod_sexo", "cod_edad", "cod_indicador"] + extra if c in base]
    agg = base.groupby(llaves, as_index=False)["valor"].sum()
    agg["cod_territorio"] = "CNSJ"
    w = agg.pivot_table(index=[c for c in llaves if c != "cod_indicador"], columns="cod_indicador", values="valor")
    tasas = []
    if {"POB_ACTIVA", "POB_15MAS"} <= set(w.columns):
        r = pd.DataFrame({"TASA_PARTICIPACION": w.POB_ACTIVA / w.POB_15MAS * 100,
                          "TASA_DESEMPLEO": w.DESOCUPADOS / w.POB_ACTIVA * 100,
                          "TASA_EMPLEO": w.OCUPADOS / w.POB_15MAS * 100})
        tasas.append(r.rename_axis(columns="cod_indicador").stack().rename("valor").reset_index())
    pob = agg[agg.cod_indicador == "POBLACION"]
    estructura = derivados.indicadores_estructura(pob, ["anio", "cod_territorio", "cod_sexo"]) if len(pob) else None
    out = pd.concat([agg] + tasas + ([estructura] if estructura is not None else []), ignore_index=True)
    out["cod_territorio"] = "CNSJ"
    return out


def _anotar(df: pd.DataFrame, tipo: str, fuente: str, dataset: str, estado: str = "definitivo") -> pd.DataFrame:
    df = df.copy()
    df["tipo_dato"] = tipo
    df["fuente"] = fuente
    df["dataset"] = dataset
    df["estado"] = estado
    return df


# ============================================================================================ hechos
def fact_historico(silver: dict, ctl: Control) -> pd.DataFrame:
    h = silver["fact_historico"].copy()
    cols = CLAVE + ["valor", "tipo_dato", "estado", "fuente", "dataset", "tabla_fuente", "version_fuente"]
    h = h[cols]
    partes = [h]
    pob = h[h.cod_indicador == "POBLACION"]
    claves = ["anio", "cod_territorio", "cod_sexo"]
    partes.append(_anotar(derivados.agregados_funcionales(pob, claves), "calculado", "Pipeline", "agregados_edad"))
    partes.append(_anotar(derivados.indicadores_estructura(pob, claves), "calculado", "Pipeline", "estructura_edad"))
    tfr = h[h.cod_indicador == "TFR"][CLAVE + ["valor"]].assign(cod_indicador="BRECHA_REEMPLAZO")
    tfr["valor"] = 2.1 - tfr["valor"]
    partes.append(_anotar(tfr, "calculado", "Pipeline", "brecha_reemplazo"))
    cen = h[h.cod_indicador.isin(["POB_EXTRANJERA", "POB_CENSO_TOTAL"])].pivot_table(
        index=["anio", "cod_territorio", "cod_sexo", "cod_edad"], columns="cod_indicador", values="valor")
    if not cen.empty:
        pe = (cen.POB_EXTRANJERA / cen.POB_CENSO_TOTAL * 100).rename("valor").reset_index()
        partes.append(_anotar(pe.assign(cod_indicador="PROP_EXTRANJEROS"), "calculado", "Pipeline", "prop_extranjeros"))
    g = pd.concat(partes, ignore_index=True)
    cn = _agregado_cnsj(g, [])
    partes_cn = _anotar(cn, "calculado", "Pipeline", "agregado_CNSJ")
    g = pd.concat([g, partes_cn], ignore_index=True)
    g["es_derivado"] = g.tipo_dato.eq("calculado")
    n = len(g)
    dup = g.duplicated(subset=CLAVE)
    ctl.validar("gold.fact_indicador_historico", "unicidad_clave", "duplicados", int(dup.sum()), n, not dup.any(),
                "clave anio+territorio+sexo+edad+indicador única")
    g = g[~dup]
    ctl.contar("gold", "fact_indicador_historico", "silver + derivados + agregado CNSJ", len(h), len(g),
               f"{len(g) - len(h)} filas calculadas")
    return g


def fact_proyeccion(silver: dict, ctl: Control) -> pd.DataFrame:
    p = silver["fact_proyeccion"].copy()
    cols = CLAVE + ["cod_escenario", "edicion_proyeccion", "valor", "tipo_dato", "fuente", "dataset"]
    p = p[cols]
    claves = ["anio", "cod_territorio", "cod_sexo", "cod_escenario", "edicion_proyeccion"]
    agg = _anotar(derivados.agregados_funcionales(p, claves), "calculado", "Pipeline", "agregados_edad")
    ind = _anotar(derivados.indicadores_estructura(p, claves), "calculado", "Pipeline", "estructura_edad")
    g = pd.concat([p, agg, ind], ignore_index=True)
    g["estado"] = "proyectado"
    n = len(g)
    dup = g.duplicated(subset=CLAVE + ["cod_escenario", "edicion_proyeccion"])
    ctl.validar("gold.fact_indicador_proyeccion", "unicidad_clave", "duplicados", int(dup.sum()), n, not dup.any(),
                "clave + escenario + edición única")
    falta = g.cod_escenario.isna() | g.edicion_proyeccion.isna()
    ctl.validar("gold.fact_indicador_proyeccion", "escenario_y_edicion_identificados", "trazabilidad", int(falta.sum()),
                n, not falta.any(), "KR3: 100 % de registros de proyección con edición y escenario")
    ctl.contar("gold", "fact_indicador_proyeccion", "proyección + agregados + indicadores por escenario", len(p), len(g))
    return g[~dup]


def tasas_participacion(hist: pd.DataFrame) -> pd.DataFrame:
    tp = hist[(hist.cod_indicador == "TASA_PARTICIPACION") & (hist.cod_territorio == "00")
              & hist.cod_sexo.isin(["H", "M"]) & hist.cod_edad.isin(sorted(set(EAPS_GRUPO.values())))]
    return tp.pivot_table(index=["cod_sexo", "cod_edad"], columns="anio", values="valor")


def supuestos_participacion(hist: pd.DataFrame, anios: list[int]) -> pd.DataFrame:
    """Tasa de participación (sexo × grupo EAPS) para cada año del horizonte bajo los supuestos A, B y C."""
    cfg = cargar_config()["escenarios_fuerza_laboral"]["supuestos"]
    base = cargar_config()["periodo"]["anio_base_escenarios"]
    tp = tasas_participacion(hist)
    t0 = tp[base]
    filas = []
    # B: pendiente lineal (MCO) 2015-2025, extrapolada hasta 2035 y luego constante; tope [0, 95] y ±10 pp
    b = cfg["B_tendencia"]
    x = np.arange(b["anios_tendencia"][0], b["anios_tendencia"][1] + 1)
    pend = tp[x].apply(lambda r: np.polyfit(x, r.values.astype(float), 1)[0], axis=1)
    # C: cierre de la brecha de género
    c = cfg["C_brecha_genero"]
    for anio in anios:
        a = t0
        dt = min(anio, b["horizonte_tendencia"]) - base
        bb = (t0 + pend * max(dt, 0)).clip(lower=t0 - b["tope_pp"], upper=t0 + b["tope_pp"]).clip(0, 95)
        frac = min(max((anio - base) / (c["anio_meta"] - base), 0), 1) * c["fraccion_cierre"]
        cc = t0.copy()
        brecha = t0.xs("H", level="cod_sexo") - t0.xs("M", level="cod_sexo")
        for edad, gap in brecha.items():
            cc.loc[("M", edad)] = t0.loc[("M", edad)] + frac * gap
        for cod, serie in (("A_constante", a), ("B_tendencia", bb), ("C_brecha_genero", cc)):
            filas.append(serie.rename("tasa_participacion").reset_index().assign(anio=anio, cod_supuesto=cod))
    return pd.concat(filas, ignore_index=True)


def fact_fuerza_laboral(hist: pd.DataFrame, proy: pd.DataFrame, ctl: Control) -> pd.DataFrame:
    """Escenario propio: Fuerza laboral potencial = Σ población proyectada (sexo, edad) × tasa de participación supuesta.
    Ejercicio contable transparente, NO un pronóstico. Se reporta también como índice 2025 = 100 para aislar el
    efecto demográfico del nivel absoluto."""
    base = cargar_config()["periodo"]["anio_base_escenarios"]
    nac = proy[(proy.cod_territorio == "00") & (proy.cod_indicador == "POBLACION") & proy.cod_sexo.isin(["H", "M"])
               & proy.cod_edad.isin(EAPS_GRUPO) & (proy.edicion_proyeccion == "KOSTAT 2022-2072") & (proy.tipo_dato != "calculado")]
    nac = nac.assign(grupo_eaps=nac.cod_edad.map(EAPS_GRUPO))
    pob = nac.groupby(["anio", "cod_escenario", "cod_sexo", "grupo_eaps"], as_index=False)["valor"].sum()
    pob = pob.rename(columns={"valor": "poblacion_proyectada", "grupo_eaps": "cod_edad"})
    anios = sorted(pob.anio.unique())
    sup = supuestos_participacion(hist, anios)
    f = pob.merge(sup, on=["anio", "cod_sexo", "cod_edad"], how="left")
    f["fuerza_laboral_potencial"] = f.poblacion_proyectada * f.tasa_participacion / 100
    f["tipo_dato"] = "escenario_propio"
    f["fuerza_laboral_total_anio"] = f.groupby(["anio", "cod_escenario", "cod_supuesto"])["fuerza_laboral_potencial"].transform("sum")
    ref = (f[f.anio == base].groupby(["cod_escenario", "cod_supuesto"])["fuerza_laboral_potencial"].sum()
           .rename("fuerza_laboral_total_base").reset_index())
    f = f.merge(ref, on=["cod_escenario", "cod_supuesto"], how="left")
    f["indice_base_2025"] = f.fuerza_laboral_total_anio / f.fuerza_laboral_total_base * 100
    # Calibración: el modelo en el año base frente a la población activa observada en la EAPS 2025
    obs = hist[(hist.cod_indicador == "POB_ACTIVA") & (hist.cod_territorio == "00") & (hist.cod_sexo == "T")
               & (hist.cod_edad == "15+") & (hist.anio == base)]["valor"]
    mod = f[(f.anio == base) & (f.cod_escenario == "medio") & (f.cod_supuesto == "A_constante")].fuerza_laboral_potencial.sum()
    if len(obs):
        dif = (mod - obs.iloc[0]) / obs.iloc[0] * 100
        ctl.validar("gold.fact_fuerza_laboral_escenario", "calibracion_anio_base", "consistencia", int(abs(dif) > 5), 1,
                    abs(dif) <= 5, f"modelo 2025 = {mod:,.0f} vs PEA observada EAPS 2025 = {obs.iloc[0]:,.0f} "
                                   f"(dif. {dif:+.2f} %); diferencia por universo (población total vs civil no institucional)")
    falta = f.tasa_participacion.isna()
    ctl.validar("gold.fact_fuerza_laboral_escenario", "tasas_disponibles", "completitud", int(falta.sum()), len(f),
                not falta.any(), "todas las celdas sexo × edad tienen tasa de participación supuesta")
    ctl.contar("gold", "fact_fuerza_laboral_escenario", "población proyectada × tasas supuestas (A, B, C)", len(pob), len(f))
    return f


def fact_riesgo_regional(hist: pd.DataFrame, proy: pd.DataFrame, ctl: Control) -> pd.DataFrame:
    """Índice compuesto de riesgo demográfico-laboral por si-do (inferencia propia, ponderación igual).
    Cada componente se estandariza (z) con el signo que hace que un valor alto = más riesgo."""
    base = cargar_config()["periodo"]["anio_base_escenarios"]
    sido = hom.mapping("territorios")
    sido = sido[sido.tipo == "sido"].cod_territorio.tolist()

    def val(df, ind, anio, edad="TOTAL", sexo="T", esc=None):
        d = df[(df.cod_indicador == ind) & (df.anio == anio) & (df.cod_edad == edad) & (df.cod_sexo == sexo)
               & df.cod_territorio.isin(sido)]
        if esc:
            d = d[d.cod_escenario == esc]
        return d.set_index("cod_territorio")["valor"]

    pr = proy[proy.edicion_proyeccion.str.contains("provincial")]
    comp = pd.DataFrame({
        "tfr": val(hist, "TFR", base),
        "prop_65mas": val(pr, "PROP_65MAS", base, esc="medio"),
        "dep_vejez": val(pr, "DEP_VEJEZ", base, esc="medio"),
        "tasa_participacion": val(hist, "TASA_PARTICIPACION", base, edad="15+"),
        "ind_reemplazo_laboral": val(pr, "IND_REEMPLAZO_LABORAL", base, esc="medio"),
        "pob_15_64_base": val(pr, "POBLACION", base, edad="15-64", esc="medio"),
        "pob_15_64_2052": val(pr, "POBLACION", 2052, edad="15-64", esc="medio"),
        "nacimientos_2015": val(hist, "NACIMIENTOS", 2015),
        "nacimientos_base": val(hist, "NACIMIENTOS", base),
    })
    comp["var_pob_15_64_2052_pct"] = (comp.pob_15_64_2052 / comp.pob_15_64_base - 1) * 100
    comp["var_nacimientos_10a_pct"] = (comp.nacimientos_base / comp.nacimientos_2015 - 1) * 100
    signo = {"tfr": -1, "prop_65mas": 1, "dep_vejez": 1, "tasa_participacion": -1, "ind_reemplazo_laboral": -1,
             "var_pob_15_64_2052_pct": -1}
    for c, s in signo.items():
        comp[f"z_{c}"] = s * (comp[c] - comp[c].mean()) / comp[c].std(ddof=0)
    comp["indice_riesgo"] = comp[[f"z_{c}" for c in signo]].mean(axis=1)
    comp["ranking_riesgo"] = comp.indice_riesgo.rank(ascending=False, method="min").astype(int)
    comp["nivel_riesgo"] = pd.qcut(comp.indice_riesgo, 3, labels=["Bajo", "Medio", "Alto"]).astype(str)
    comp["anio_referencia"] = base
    comp["tipo_dato"] = "inferencia_propia"
    comp["nota"] = ("TFR, participación y nacimientos observados; estructura por edad 2025 y 2052 de la proyección "
                    "provincial KOSTAT (escenario medio). Ponderación igual de 6 componentes estandarizados.")
    falt = comp[list(signo)].isna().any(axis=1)
    ctl.validar("gold.fact_riesgo_regional", "componentes_completos", "completitud", int(falt.sum()), len(comp),
                not falt.any(), "los 17 si-do tienen los 6 componentes del índice")
    return comp.reset_index().rename(columns={"index": "cod_territorio"})


def fact_internacional(silver: dict) -> pd.DataFrame:
    i = silver["fact_internacional"].copy()
    i = i[CLAVE + ["valor", "fuente", "dataset", "tabla_fuente"]]
    i["tipo_dato"] = "observado"
    # cuando un país-año-indicador está en WB y OECD se conserva una fila por fuente (la fuente es parte de la clave)
    return i.drop_duplicates(subset=CLAVE + ["fuente"])


def conciliar_derivados(hist: pd.DataFrame, proy: pd.DataFrame, ctl: Control) -> pd.DataFrame:
    """Valida las FÓRMULAS del pipeline: indicadores derivados propios vs los publicados por KOSTAT (resumen oficial
    de la proyección, 2023-2072) y por el World Bank (2000-2022). Mismo formato que silver.conciliacion."""
    tol = cargar_config()["calidad"]["tolerancia_conciliacion_pct"]
    c = leer_silver("fact_contraste")
    inds = ["PROP_15_64", "PROP_65MAS", "DEP_JUVENIL", "DEP_VEJEZ", "DEP_TOTAL", "IND_ENVEJECIMIENTO"]
    nuestra = pd.concat([
        hist[(hist.cod_territorio == "00") & hist.cod_indicador.isin(inds) & (hist.cod_sexo == "T")].assign(dataset_maestra="pipeline (histórico)"),
        proy[(proy.cod_territorio == "00") & proy.cod_indicador.isin(inds) & (proy.cod_sexo == "T")
             & (proy.cod_escenario == "medio") & (proy.edicion_proyeccion == "KOSTAT 2022-2072")].assign(dataset_maestra="pipeline (proyección medio)"),
    ])
    oficial = c[c.cod_indicador.isin(inds) & (c.cod_territorio == "00")]
    m = nuestra[CLAVE + ["valor", "dataset_maestra"]].rename(columns={"valor": "valor_maestra"}).merge(
        oficial[CLAVE + ["valor", "fuente", "dataset"]].rename(
            columns={"valor": "valor_contraste", "fuente": "fuente_contraste", "dataset": "dataset_contraste"}), on=CLAVE)
    m["fuente_maestra"] = "Pipeline"
    m["dif_abs"] = m.valor_contraste - m.valor_maestra
    m["dif_pct"] = m.dif_abs / m.valor_maestra.abs() * 100
    m["comparable"] = True
    m["nota"] = "validación de fórmula: indicador calculado por el pipeline vs publicado oficialmente"
    m["dentro_tolerancia"] = m.dif_pct.abs() <= tol
    for (ind, ds), g in m.groupby(["cod_indicador", "dataset_contraste"]):
        ctl.validar("gold.formulas", f"{ind} vs {ds}", "consistencia_entre_fuentes", int((~g.dentro_tolerancia).sum()),
                    len(g), bool(g.dentro_tolerancia.all()),
                    f"{len(g)} años; dif. máx {g.dif_pct.abs().max():.3f} %; mediana {g.dif_pct.abs().median():.3f} %")
    return m


# ============================================================================================ datasets consolidados
INDICADORES_NACIONALES = ["NACIMIENTOS", "TFR", "TASA_BRUTA_NATALIDAD", "DEFUNCIONES", "CRECIMIENTO_NATURAL",
                          "ESPERANZA_VIDA", "MORTALIDAD_INFANTIL", "MATRIMONIOS", "PROP_0_14", "PROP_15_64",
                          "PROP_65MAS", "PROP_80MAS", "DEP_VEJEZ", "DEP_JUVENIL", "DEP_TOTAL", "IND_ENVEJECIMIENTO",
                          "RATIO_SOPORTE", "IND_REEMPLAZO_LABORAL", "POB_15MAS", "POB_ACTIVA", "OCUPADOS",
                          "TASA_PARTICIPACION", "TASA_DESEMPLEO", "TASA_EMPLEO", "POB_EXTRANJERA", "PROP_EXTRANJEROS"]


def dataset_consolidado(hist: pd.DataFrame, proy: pd.DataFrame, fl: pd.DataFrame, internac: pd.DataFrame,
                        territorios: list[str]) -> pd.DataFrame:
    """Una fila por año y territorio con los indicadores clave en columnas (para Power BI/Excel sin DAX complejo).
    La población y los indicadores de estructura usan el histórico hasta 2022 y la proyección medio desde 2023;
    la columna tipo_dato_poblacion lo declara explícitamente."""
    h = hist[hist.cod_territorio.isin(territorios) & (hist.cod_sexo == "T")]
    sel = h[h.cod_indicador.isin(INDICADORES_NACIONALES) & h.cod_edad.isin(["TOTAL", "15+"])]
    w = sel.pivot_table(index=["anio", "cod_territorio"], columns="cod_indicador", values="valor")
    pobh = h[(h.cod_indicador == "POBLACION") & h.cod_edad.isin(["TOTAL", "0-14", "15-64", "65+"])].pivot_table(
        index=["anio", "cod_territorio"], columns="cod_edad", values="valor")
    pobh.columns = [f"POB_{c.replace('-', '_').replace('+', 'MAS')}" for c in pobh.columns]
    p = proy[proy.cod_territorio.isin(territorios) & (proy.cod_sexo == "T") & (proy.cod_escenario == "medio")]
    pw = p[p.cod_indicador.isin(INDICADORES_NACIONALES) & (p.cod_edad == "TOTAL")].pivot_table(
        index=["anio", "cod_territorio"], columns="cod_indicador", values="valor")
    pobp = p[(p.cod_indicador == "POBLACION") & p.cod_edad.isin(["TOTAL", "0-14", "15-64", "65+"])].pivot_table(
        index=["anio", "cod_territorio"], columns="cod_edad", values="valor")
    pobp.columns = [f"POB_{c.replace('-', '_').replace('+', 'MAS')}" for c in pobp.columns]
    hist_w = w.join(pobh, how="outer")
    proy_w = pw.join(pobp, how="outer")
    out = hist_w.combine_first(proy_w)  # el histórico prevalece; la proyección completa 2023+
    out["tipo_dato_poblacion"] = np.where(out.index.get_level_values("anio") <= 2022, "estimado", "proyeccion_oficial")
    out = out.reset_index()
    if "00" in territorios:
        f = fl[(fl.cod_escenario == "medio")].groupby(["anio", "cod_supuesto"]).fuerza_laboral_potencial.sum().unstack()
        f.columns = [f"FLP_{c.split('_')[0]}" for c in f.columns]
        out = out.merge(f.reset_index().assign(cod_territorio="00"), on=["anio", "cod_territorio"], how="left")
        prod = internac[(internac.cod_territorio == "00") & (internac.cod_indicador == "PIB_HORA")][["anio", "valor"]]
        out = out.merge(prod.rename(columns={"valor": "PIB_HORA"}).assign(cod_territorio="00"),
                        on=["anio", "cod_territorio"], how="left")
    out["periodo"] = np.where(out.anio <= 2025, "Histórico", "Proyección")
    return out.sort_values(["cod_territorio", "anio"]).reset_index(drop=True)


# ============================================================================================ orquestación
def ejecutar(ctl: Control) -> dict[str, pd.DataFrame]:
    silver = {n: leer_silver(n) for n in ["fact_historico", "fact_proyeccion", "fact_internacional", "conciliacion",
                                          "dim_escenario", "sin_dato"]}
    dims = dimensiones(silver)
    hist = fact_historico(silver, ctl)
    proy = fact_proyeccion(silver, ctl)
    fl = fact_fuerza_laboral(hist, proy, ctl)
    riesgo = fact_riesgo_regional(hist, proy, ctl)
    internac = fact_internacional(silver)
    sido = dims["dim_territorio"]
    regiones = sido[sido.tipo.isin(["sido", "agregado"])].cod_territorio.tolist()
    tablas = {**dims,
              "fact_indicador_historico": hist,
              "fact_indicador_proyeccion": proy,
              "fact_fuerza_laboral_escenario": fl,
              "fact_riesgo_regional": riesgo,
              "fact_comparacion_internacional": internac,
              "fact_conciliacion": pd.concat([silver["conciliacion"].assign(tipo_comparacion="dato publicado"),
                                              conciliar_derivados(hist, proy, ctl).assign(tipo_comparacion="fórmula del pipeline")],
                                             ignore_index=True),
              "dataset_nacional_anual": dataset_consolidado(hist, proy, fl, internac, ["00"]),
              "dataset_regional_anual": dataset_consolidado(hist, proy, fl, internac, regiones)}
    for n, df in tablas.items():
        df.to_parquet(ruta("gold") / f"{n}.parquet", index=False)
        if n.startswith("dataset_") or n.startswith("dim_") or n == "fact_riesgo_regional":
            df.to_csv(ruta("gold") / f"{n}.csv", index=False, encoding="utf-8-sig")
        log.info("[gold] %-32s %8d filas", n, len(df))
    return tablas


def leer(nombre: str) -> pd.DataFrame:
    return pd.read_parquet(ruta("gold") / f"{nombre}.parquet")
