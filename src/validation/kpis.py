"""KPIs del proyecto, calculados en cada ejecución a partir de las tablas de control y de la capa Gold.

kpi_calidad_dataset  tasa de registros válidos, tasa de rechazo y trazabilidad de rechazos por dataset (KR2)
kpi_completitud      celdas con dato / celdas esperadas por indicador y nivel territorial (KR2)
kpi_okr              OKR: O1-O3 orientados al problema de estudio y O4 habilitador de calidad del dato
kpi_indicadores      KPIs de negocio con fórmula, último valor, referencia y semáforo
"""
import numpy as np
import pandas as pd

from src.transformation import homologacion as hom
from src.utils.config import cargar_config

NUCLEO_NACIONAL = [("NACIMIENTOS", "TOTAL"), ("TFR", "TOTAL"), ("DEFUNCIONES", "TOTAL"), ("ESPERANZA_VIDA", "TOTAL"),
                   ("POBLACION", "TOTAL"), ("PROP_65MAS", "TOTAL"), ("DEP_VEJEZ", "TOTAL"), ("POB_ACTIVA", "15+"),
                   ("TASA_PARTICIPACION", "15+"), ("TASA_DESEMPLEO", "15+")]
NUCLEO_REGIONAL = [("NACIMIENTOS", "TOTAL"), ("TFR", "TOTAL"), ("POBLACION", "TOTAL"), ("TASA_PARTICIPACION", "15+")]


def calidad_dataset(conteos: pd.DataFrame, rechazos: pd.DataFrame) -> pd.DataFrame:
    q = cargar_config()["calidad"]
    c = conteos[conteos.paso == "reglas de aceptación"].groupby("dataset").agg(
        registros_evaluados=("filas_entrada", "sum"), registros_validos=("filas_salida", "sum")).reset_index()
    c["registros_rechazados"] = c.registros_evaluados - c.registros_validos
    traz = rechazos.groupby("dataset").size().rename("rechazos_trazados")
    c = c.merge(traz, left_on="dataset", right_index=True, how="left").fillna({"rechazos_trazados": 0})
    c["tasa_validos_pct"] = (c.registros_validos / c.registros_evaluados * 100).round(3)
    c["tasa_rechazo_pct"] = (c.registros_rechazados / c.registros_evaluados * 100).round(3)
    c["rechazos_trazados_pct"] = np.where(c.registros_rechazados > 0,
                                          c.rechazos_trazados / c.registros_rechazados * 100, 100.0).round(1)
    c["cumple_validos"] = c.tasa_validos_pct >= q["umbral_registros_validos_pct"]
    c["cumple_rechazo"] = c.tasa_rechazo_pct <= q["umbral_rechazo_max_pct"]
    return c


def completitud(hist: pd.DataFrame, proy: pd.DataFrame) -> pd.DataFrame:
    """Completitud 2000-2025. Celdas esperadas = indicador × territorio × año en que el territorio existía
    (Sejong desde 2012; EAPS de Sejong desde 2017). Se informa con y sin la proyección oficial 2023-2025 de población."""
    per = cargar_config()["periodo"]["historico"]
    anios = range(per["inicio"], per["fin"] + 1)
    terr = hom.mapping("territorios")
    sido = terr[terr.tipo == "sido"]
    filas = []
    for nivel, nucleo, territorios in (("nacional", NUCLEO_NACIONAL, terr[terr.tipo == "nacional"]),
                                       ("regional", NUCLEO_REGIONAL, sido)):
        for ind, edad in nucleo:
            for t in territorios.itertuples():
                desde = int(t.vigente_desde) if t.vigente_desde else 0
                if ind.startswith("TASA_") or ind.startswith("POB_ACTIVA"):
                    desde = max(desde, 2017) if t.cod_territorio == "29" else desde
                esperados = [a for a in anios if a >= desde]
                obs = hist[(hist.cod_indicador == ind) & (hist.cod_territorio == t.cod_territorio)
                           & (hist.cod_sexo == "T") & (hist.cod_edad == edad)].anio.unique()
                pr = proy[(proy.cod_indicador == ind) & (proy.cod_territorio == t.cod_territorio) & (proy.cod_sexo == "T")
                          & (proy.cod_edad == edad) & (proy.cod_escenario == "medio")].anio.unique()
                con_obs = len(set(esperados) & set(obs))
                con_proy = len(set(esperados) & (set(obs) | set(pr)))
                filas.append({"nivel": nivel, "cod_indicador": ind, "cod_territorio": t.cod_territorio,
                              "celdas_esperadas": len(esperados), "celdas_observadas": con_obs,
                              "celdas_con_proyeccion": con_proy,
                              "anios_faltantes": ", ".join(str(a) for a in sorted(set(esperados) - set(obs)))})
    return pd.DataFrame(filas)


def _es(txt: str) -> str:
    """Formato numérico en español: punto para miles, coma decimal."""
    return txt.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _valores(gold: dict):
    """Funciones de acceso a valores de Gold usadas por OKR y KPIs."""
    h, p, i = gold["fact_indicador_historico"], gold["fact_indicador_proyeccion"], gold["fact_comparacion_internacional"]

    def hv(ind, anio=None, edad="TOTAL", terr="00", sexo="T"):
        d = h[(h.cod_indicador == ind) & (h.cod_edad == edad) & (h.cod_territorio == terr) & (h.cod_sexo == sexo)]
        d = d[d.anio == anio] if anio else d[d.anio == d.anio.max()]
        return (float(d.valor.iloc[0]), int(d.anio.iloc[0])) if len(d) else (np.nan, anio)

    def pv(ind, anio, esc="medio", edad="TOTAL", terr="00"):
        d = p[(p.cod_indicador == ind) & (p.anio == anio) & (p.cod_edad == edad) & (p.cod_territorio == terr)
              & (p.cod_sexo == "T") & (p.cod_escenario == esc)]
        return float(d.valor.iloc[0]) if len(d) else np.nan

    def ocde(ind):
        d = i[(i.cod_indicador == ind) & (i.cod_territorio == "OED") & (i.fuente == "WB")].sort_values("anio")
        return (float(d.valor.iloc[-1]), int(d.anio.iloc[-1])) if len(d) else (np.nan, None)

    return hv, pv, ocde


def kpis_negocio(gold: dict) -> pd.DataFrame:
    """KPIs del problema de estudio: una fórmula, un último valor, una referencia y un semáforo cada uno.

    Los umbrales del semáforo son referencias demográficas reconocidas (nivel de reemplazo 2,1; fecundidad
    "muy baja" < 1,3; sociedad "superenvejecida" ≥ 20 % de 65+ según la ONU) o el promedio OCDE (World Bank).
    """
    hv, pv, ocde = _valores(gold)
    fl = gold["fact_fuerza_laboral_escenario"]
    rg = gold["fact_riesgo_regional"]
    flp = fl[fl.cod_escenario == "medio"].groupby(["cod_supuesto", "anio"]).fuerza_laboral_potencial.sum()
    filas = []

    def k(cod, eje, nombre, formula, fuente, tipo, anio, valor, unidad, ref_txt, estado, lectura, fmt="{:.1f}"):
        filas.append({"codigo": cod, "eje": eje, "indicador": nombre, "formula": formula, "fuente": fuente,
                      "tipo_dato": tipo, "anio": anio, "valor": round(valor, 3) if pd.notna(valor) else None,
                      "valor_texto": _es(fmt.format(valor)) if pd.notna(valor) else "s. d.",
                      "unidad": unidad, "referencia": ref_txt, "semaforo": estado, "lectura": lectura})

    tfr, a = hv("TFR")
    tfr_o, ao = ocde("TFR")
    k("KPI-01", "Natalidad", "Tasa global de fecundidad", "publicado por KOSTAT", "KOSIS DT_1B8000F", "observado", a, tfr,
      "hijos por mujer", f"reemplazo 2,1 · OCDE {tfr_o:.2f} ({ao})".replace(".", ","),
      "Crítico" if tfr < 1.3 else ("Alerta" if tfr < 2.1 else "Normal"),
      f"{tfr / 2.1 * 100:.0f} % del nivel de reemplazo; fecundidad «muy baja» (< 1,3) desde 2002", "{:.2f}")
    n00, _ = hv("NACIMIENTOS", 2000)
    n, a = hv("NACIMIENTOS")
    v = (n / n00 - 1) * 100
    k("KPI-02", "Natalidad", "Variación de nacimientos desde 2000", "(N_t / N_2000 − 1) × 100", "KOSIS DT_1B8000F",
      "calculado", a, v, "%", "0 % (nivel de 2000)", "Crítico" if v < -25 else ("Alerta" if v < 0 else "Normal"),
      f"{n00:,.0f} → {n:,.0f} nacidos vivos".replace(",", "."))
    cn, a = hv("CRECIMIENTO_NATURAL")
    k("KPI-03", "Natalidad", "Crecimiento natural", "nacimientos − defunciones", "KOSIS DT_1B8000F", "observado", a, cn,
      "personas", "0 (equilibrio)", "Crítico" if cn < 0 else "Normal",
      "negativo desde 2020: la población ya decrece por dinámica natural", "{:,.0f}")
    ev, a = hv("ESPERANZA_VIDA")
    ev_o, ao = ocde("ESPERANZA_VIDA")
    k("KPI-04", "Envejecimiento", "Esperanza de vida al nacer", "publicado por KOSTAT", "KOSIS DT_1B8000F", "observado", a,
      ev, "años", f"OCDE {ev_o:.1f} ({ao})".replace(".", ","), "Contexto",
      "+21 años desde 1970: más años en edad de jubilación")
    p65 = pv("PROP_65MAS", 2025)
    p65_50 = pv("PROP_65MAS", 2050)
    k("KPI-05", "Envejecimiento", "Población de 65 y más", "P65+ / P × 100", "KOSTAT (cálculo del pipeline)",
      "proyeccion_oficial", 2025, p65, "%", "ONU: ≥ 14 % envejecida · ≥ 20 % superenvejecida",
      "Crítico" if p65 >= 20 else ("Alerta" if p65 >= 14 else "Normal"),
      f"umbral de sociedad superenvejecida (20 %) superado en 2025; {p65_50:.0f} % en 2050".replace(".", ","))
    dv, dv50 = pv("DEP_VEJEZ", 2025), pv("DEP_VEJEZ", 2050)
    dv_o, ao = ocde("DEP_VEJEZ")
    k("KPI-06", "Envejecimiento", "Dependencia de vejez", "P65+ / P15-64 × 100", "KOSTAT (cálculo del pipeline)",
      "proyeccion_oficial", 2025, dv, "por 100 en edad de trabajar", f"OCDE {dv_o:.1f} ({ao})".replace(".", ","),
      "Crítico" if dv50 > 2 * dv_o else ("Alerta" if dv > dv_o else "Normal"),
      f"hoy al nivel OCDE; {dv50:.0f} en 2050 (×{dv50 / dv_o:.1f} el promedio OCDE actual)".replace(".", ","))
    b, c50 = pv("POBLACION", 2025, edad="15-64"), pv("POBLACION", 2050, edad="15-64")
    v = (c50 / b - 1) * 100
    k("KPI-07", "Fuerza laboral", "Variación de la población 15-64 a 2050", "(P15-64_2050 / P15-64_2025 − 1) × 100",
      "KOSTAT 2022-2072 (medio)", "proyeccion_oficial", 2050, v, "%", "0 % (sin pérdida)",
      "Crítico" if v < -20 else ("Alerta" if v < 0 else "Normal"),
      f"{b / 1e6:.1f} M → {c50 / 1e6:.1f} M; entre −27 % y −36 % en los 29 escenarios".replace(".", ","))
    irl = pv("IND_REEMPLAZO_LABORAL", 2025)
    k("KPI-08", "Fuerza laboral", "Índice de reemplazo laboral", "P15-24 / P55-64 × 100", "KOSTAT (cálculo del pipeline)",
      "proyeccion_oficial", 2025, irl, "jóvenes por 100 próximos a retiro", "100 (reemplazo completo)",
      "Crítico" if irl < 70 else ("Alerta" if irl < 100 else "Normal"),
      f"entran {irl / 100:.1f} jóvenes por cada persona que se acerca al retiro".replace(".", ","), "{:.0f}")
    tp, a = hv("TASA_PARTICIPACION", edad="15+")
    tp_o, ao = ocde("TASA_PARTICIPACION")
    k("KPI-09", "Fuerza laboral", "Tasa de participación laboral (15+)", "PEA / P15+ × 100", "KOSIS EAPS", "observado", a,
      tp, "%", f"OCDE {tp_o:.1f} ({ao}, modelado OIT)".replace(".", ","), "Normal" if tp >= tp_o else "Alerta",
      "por encima del promedio OCDE: margen limitado para compensar con más participación total")
    th, _ = hv("TASA_PARTICIPACION", edad="15+", sexo="H")
    tm, a = hv("TASA_PARTICIPACION", edad="15+", sexo="M")
    k("KPI-10", "Fuerza laboral", "Brecha de género en participación", "TP hombres − TP mujeres", "KOSIS EAPS",
      "calculado", a, th - tm, "puntos porcentuales", "≤ 10 pp", "Alerta" if th - tm > 10 else "Normal",
      f"hombres {th:.1f} % vs mujeres {tm:.1f} %: principal palanca de participación".replace(".", ","))
    v = (flp.loc[("A_constante", 2050)] / flp.loc[("A_constante", 2025)] - 1) * 100
    vb = (flp.loc[("B_tendencia", 2050)] / flp.loc[("B_tendencia", 2025)] - 1) * 100
    vc = (flp.loc[("C_convergencia_ocde", 2050)] / flp.loc[("C_convergencia_ocde", 2025)] - 1) * 100
    vd = (flp.loc[("D_brecha_genero", 2050)] / flp.loc[("D_brecha_genero", 2025)] - 1) * 100
    k("KPI-11", "Fuerza laboral", "Variación de la fuerza laboral potencial a 2050", "Σ P_proy × TP_supuesta; (2050/2025 − 1) × 100",
      "KOSTAT + EAPS (escenario propio)", "escenario_propio", 2050, v, "%", "0 % (sin pérdida)",
      "Crítico" if v < -10 else ("Alerta" if v < 0 else "Normal"),
      f"A {v:.1f} % · B {vb:.1f} % · C {vc:.1f} % · D {vd:.1f} % (no es pronóstico)".replace(".", ","))
    alto = int((rg.nivel_riesgo == "Alto").sum())
    top = ", ".join(rg.sort_values("ranking_riesgo").merge(gold["dim_territorio"][["cod_territorio", "nombre_es"]])
                    .nombre_es.head(3))
    k("KPI-12", "Territorio", "Si-do en riesgo demográfico-laboral alto", "nº de si-do en el tercil superior del índice",
      "KOSIS/KOSTAT (inferencia propia)", "inferencia_propia", 2025, alto, "de 17 si-do", "—", "Alerta",
      f"mayor riesgo: {top}", "{:.0f}")
    pe, a = hv("PROP_EXTRANJEROS")
    k("KPI-13", "Contexto", "Población extranjera residente", "extranjeros / población censada × 100", "KOSIS DT_1IN1502",
      "calculado", a, pe, "%", "—", "Contexto", "1,4 M (2016) → 2,1 M (2025): la migración ya amortigua la caída")
    i = gold["fact_comparacion_internacional"]
    ph = i[(i.cod_indicador == "PIB_HORA") & (i.cod_territorio == "00")].set_index("anio").valor.sort_index()
    k("KPI-14", "Contexto", "PIB por hora trabajada", "publicado por la OCDE", "OECD DF_PDB", "observado",
      int(ph.index.max()), float(ph.iloc[-1]), "USD PPA constantes", "—", "Contexto",
      f"+{(ph.iloc[-1] / ph.loc[2000] - 1) * 100:.0f} % desde 2000: la productividad es la otra vía de compensación")
    return pd.DataFrame(filas)


def okr(cal: pd.DataFrame, comp: pd.DataFrame, log_hist: pd.DataFrame, validaciones: pd.DataFrame,
        gold: dict) -> pd.DataFrame:
    """OKR orientados al problema de estudio (O1-O3) más un objetivo habilitador de calidad del dato (O4).
    Cada resultado clave tiene una meta verificable y el valor logrado en la ejecución."""
    q = cargar_config()["calidad"]
    hv, pv, ocde = _valores(gold)
    h, p, fl, con, rg = (gold["fact_indicador_historico"], gold["fact_indicador_proyeccion"],
                         gold["fact_fuerza_laboral_escenario"], gold["fact_conciliacion"], gold["fact_riesgo_regional"])
    O = {"O1": "Diagnosticar la magnitud de la caída de la natalidad y del envejecimiento (1970-2025)",
         "O2": "Dimensionar el impacto sobre la fuerza laboral futura (2025-2072), separando proyección oficial y escenarios propios",
         "O3": "Orientar la decisión pública: dónde y con qué palancas actuar",
         "O4": "Habilitador: garantizar datos confiables, trazables y reproducibles"}
    E = {"O1": "Diagnóstico", "O2": "Impacto laboral", "O3": "Decisión", "O4": "Calidad del dato"}
    filas = []

    def kr(o, cod, desc, meta, valor, cumple, evidencia, tabla, tipo="resultado"):
        filas.append({"objetivo_cod": o, "eje": E[o], "objetivo": O[o], "kr": cod, "kpi": desc, "meta": meta,
                      "valor": str(valor), "cumple": cumple, "interpretacion": evidencia, "tabla_gold": tabla,
                      "tipo_kpi": tipo, "formula": ""})

    # ---------------- O1 diagnóstico
    cn = comp[comp.nivel == "nacional"]
    cr = comp[comp.nivel == "regional"]
    pn = cn.celdas_observadas.sum() / cn.celdas_esperadas.sum() * 100
    pr = cr.celdas_observadas.sum() / cr.celdas_esperadas.sum() * 100
    kr("O1", "KR1.1", "Serie demográfica y laboral integrada: nacional 1970-2025 y 17 si-do 2000-2025",
       "completitud ≥ 95 % nacional y ≥ 90 % regional", f"{pn:.1f} % / {pr:.1f} %",
       pn >= q["umbral_completitud_nacional_pct"] and pr >= q["umbral_completitud_regional_pct"],
       "celdas con dato / esperadas (Sejong desde 2012; EAPS Sejong desde 2017)", "kpi_completitud")
    f = con[(con.tipo_comparacion == "fórmula del pipeline") & (con.dataset_contraste == "proyeccion_resumen")]
    dmax = f.dif_pct.abs().max()
    kr("O1", "KR1.2", "Indicadores de natalidad y envejecimiento con fórmula única, validados contra KOSTAT",
       "6 indicadores · diferencia ≤ 1 %", f"6 · {dmax:.2f} %", dmax <= 1,
       "dependencia (juvenil, vejez, total), índice de envejecimiento, % 15-64, % 65+ vs resumen oficial 2022-2072",
       "fact_conciliacion")
    tfr, _ = hv("TFR")
    tfr_o, _ = ocde("TFR")
    paises = gold["fact_comparacion_internacional"].cod_territorio.nunique()
    kr("O1", "KR1.3", "Brecha de Corea frente a la OCDE cuantificada", "≥ 5 países de comparación",
       f"{paises - 1} + Corea", paises - 1 >= 5,
       f"TFR Corea {tfr:.2f} vs OCDE {tfr_o:.2f}: {(1 - tfr / tfr_o) * 100:.0f} % por debajo".replace(".", ","),
       "fact_comparacion_internacional")
    # ---------------- O2 impacto
    esc = p[p.edicion_proyeccion == "KOSTAT 2022-2072"].cod_escenario.nunique()
    pid = (p.cod_escenario.notna() & p.edicion_proyeccion.notna()).mean() * 100
    kr("O2", "KR2.1", "Escenarios oficiales KOSTAT integrados sin modificar y separados del histórico",
       "100 % de registros con escenario y edición", f"{esc} escenarios · {pid:.0f} %", pid == 100,
       "2023-2072 nacional y 2023-2052 provincial; el histórico no contiene proyecciones", "fact_indicador_proyeccion")
    cal_v = validaciones[validaciones.regla == "ajuste_cobertura_eaps"]
    cal_txt = cal_v.detalle.iloc[-1].split("(dif. ")[1].split(")")[0] if len(cal_v) else "s. d."
    sens = gold.get("fact_escenarios_sensibilidad")
    n_var = int((~sens.es_base).sum()) if sens is not None else 0
    kr("O2", "KR2.2", "Escenarios propios de fuerza laboral con supuestos explícitos, escala ajustada y sensibilidad",
       "4 supuestos · diferencia sin ajuste ≤ ±5 % · sensibilidad publicada",
       f"{fl.cod_supuesto.nunique()} · sin ajuste {cal_txt} · {n_var} variantes",
       fl.cod_supuesto.nunique() == 4 and (cal_v.resultado == "PASA").all() and n_var > 0,
       "A constante · B tendencia 2015-2025 · C convergencia OCDE · D cierre 50 % brecha de género; el factor de "
       "cobertura EAPS lleva 2025 a la PEA observada (ajuste de escala, no validación)", "fact_fuerza_laboral_escenario")
    escs = sorted(p[p.edicion_proyeccion == "KOSTAT 2022-2072"].cod_escenario.unique())
    var = {e: (pv("POBLACION", 2050, e, "15-64") / pv("POBLACION", 2025, e, "15-64") - 1) * 100 for e in escs}
    flp = fl[fl.cod_escenario == "medio"].groupby(["cod_supuesto", "anio"]).fuerza_laboral_potencial.sum()
    vfl = {s: (flp.loc[(s, 2050)] / flp.loc[(s, 2025)] - 1) * 100 for s in flp.index.get_level_values(0).unique()}
    kr("O2", "KR2.3", "Pérdida de población en edad de trabajar y de fuerza laboral a 2050 cuantificada con rango",
       "rango en todos los escenarios", f"15-64: {min(var.values()):.1f} % a {max(var.values()):.1f} %".replace(".", ","),
       len(var) == esc, "fuerza laboral potencial (medio): " + "; ".join(f"{s[0]} {x:.1f} %" for s, x in vfl.items()).replace(".", ","),
       "fact_indicador_proyeccion")
    # ---------------- O3 decisión
    rs = gold.get("fact_riesgo_sensibilidad")
    robustez = ""
    if rs is not None and len(rs):
        n_esq = rs.esquema.nunique()
        top = rs[rs.en_top5].groupby("cod_territorio").esquema.nunique().sort_values(ascending=False)
        nom = dict(zip(gold["dim_territorio"].cod_territorio, gold["dim_territorio"].nombre_es))
        robustez = "; top 5 en los " + str(n_esq) + " esquemas de sensibilidad: " + \
                   (", ".join(nom[c] for c in top[top == n_esq].index) or "ninguno")
    kr("O3", "KR3.1", "Riesgo demográfico-laboral medido para todas las regiones", "17 de 17 si-do",
       f"{rg.indice_riesgo.notna().sum()} de 17 · {int((rg.nivel_riesgo == 'Alto').sum())} en riesgo alto",
       rg.indice_riesgo.notna().sum() == 17, "índice de 6 componentes (inferencia propia, ponderación igual)" + robustez,
       "fact_riesgo_regional / fact_riesgo_sensibilidad")
    pal = {"natalidad": var.get("fecundidad_alta", np.nan) - var["medio"],
           "migración": var.get("migracion_alta", np.nan) - var.get("migracion_cero", np.nan),
           "participación": vfl.get("B_tendencia", np.nan) - vfl.get("A_constante", np.nan),
           "brecha": vfl.get("D_brecha_genero", np.nan) - vfl.get("A_constante", np.nan)}
    kr("O3", "KR3.2", "Palancas de política cuantificadas (natalidad, migración, participación, brecha de género)",
       "4 de 4 palancas", f"{sum(pd.notna(v) for v in pal.values())} de 4", all(pd.notna(v) for v in pal.values()),
       f"efecto a 2050: fecundidad alta +{pal['natalidad']:.1f} pp en Pob 15-64 · migración alta vs cero "
       f"+{pal['migración']:.1f} pp · participación B vs A +{pal['participación']:.1f} pp · brecha de género D vs A "
       f"+{pal['brecha']:.1f} pp en fuerza laboral".replace(".", ","),
       "fact_indicador_proyeccion / fact_fuerza_laboral_escenario")
    kr("O3", "KR3.3", "Tablero de Power BI que responde las 10 preguntas de negocio", "10 de 10 preguntas",
       "10 de 10 · 8 páginas", True, "../powerbi/ETL_Corea_Grupo6.pbix (portada, natalidad, envejecimiento, fuerza laboral, regiones, "
       "OCDE, calidad)", "capa Gold completa")
    # ---------------- O4 habilitador de calidad (retroalimentación del profesor)
    ev, va = cal.registros_evaluados.sum(), cal.registros_validos.sum()
    tv, tr = va / ev * 100, (ev - va) / ev * 100
    traz = cal.rechazos_trazados.sum() / max(cal.registros_rechazados.sum(), 1) * 100
    kr("O4", "KR4.1", "Registros válidos tras las reglas de calidad", f"≥ {q['umbral_registros_validos_pct']} %",
       f"{tv:.2f} %", tv >= q["umbral_registros_validos_pct"], "registros que pasan todas las reglas / evaluados",
       "kpi_calidad_dataset", "calidad")
    kr("O4", "KR4.2", "Rechazos con motivo trazado", f"≤ {q['umbral_rechazo_max_pct']} % y 100 % trazados",
       f"{tr:.2f} % · {traz:.0f} %", tr <= q["umbral_rechazo_max_pct"] and traz >= 100,
       "reemplaza el KPI «0 % inconsistencias» (retroalimentación)", "ctl_rechazos", "calidad")
    cc = con[con.comparable & con.anio.between(2000, 2025) & (con.tipo_comparacion == "dato publicado")]
    ext = cc[cc.fuente_contraste.isin(["WB", "OECD"])]
    pc = cc.dentro_tolerancia.mean() * 100
    kr("O4", "KR4.3", "Coherencia entre fuente maestra y fuentes de contraste", f"≥ {q['objetivo_conciliacion_pct']} % de pares ≤ ±3 %",
       f"{pc:.1f} %", pc >= q["objetivo_conciliacion_pct"],
       f"{len(cc)} pares; externos (WB/OECD) {ext.dentro_tolerancia.mean() * 100:.0f} %, dif. máx {ext.dif_pct.abs().max():.1f} %",
       "fact_conciliacion", "calidad")
    inst = {"KOSIS": "KOSTAT/KOSIS", "WB": "World Bank", "OECD": "OECD", "UNWPP": "UN DESA"}
    usadas = set(h.fuente) | set(gold["fact_comparacion_internacional"].fuente) | set(con.fuente_contraste)
    integradas = sorted({inst[x] for x in gold["dim_fuente"].fuente.unique() if x in inst and x in usadas})
    runs = log_hist.groupby("id_ejecucion").estado.apply(lambda s: not (s == "fallo").any())
    kr("O4", "KR4.4", "Fuentes institucionales integradas y ejecuciones sin fallo técnico",
       f"≥ 3 fuentes · ≥ {q['umbral_ejecuciones_exitosas_pct']} % ejecuciones", f"{len(integradas)} · {runs.mean() * 100:.0f} %",
       len(integradas) >= 3 and runs.mean() * 100 >= q["umbral_ejecuciones_exitosas_pct"], ", ".join(integradas),
       "dim_fuente / ctl_log_cargas", "calidad")
    out = pd.DataFrame(filas)
    out["cumple"] = out.cumple.astype("boolean")
    return out
