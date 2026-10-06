"""Reglas de consistencia interna (Silver) y conciliación entre fuente maestra y fuentes de contraste.

La conciliación responde a la retroalimentación del profesor ("las fuentes se solapan: escojan una fuente maestra"):
el valor de contraste NUNCA reemplaza al maestro; sólo se registra la diferencia para documentar la coherencia.
"""
import numpy as np
import pandas as pd

from src.transformation import derivados
from src.utils.config import cargar_config
from src.utils.control import Control
from src.validation import reglas


def _sel(df, **f):
    m = pd.Series(True, index=df.index)
    for k, v in f.items():
        m &= df[k].isin(v if isinstance(v, (list, tuple, set)) else [v])
    return df[m]


def ejecutar(t: dict, ctl: Control) -> None:
    q = cargar_config()["calidad"]
    tol = q["tolerancia_suma_partes_pct"]
    k = t["_kosis"]
    idx = ["anio", "cod_indicador"]

    # 1. Vitales: suma de 17 si-do = nacional (nacimientos y defunciones)
    reg = _sel(k["vitales_sigungu"], cod_indicador=["NACIMIENTOS", "DEFUNCIONES"])
    nac = _sel(k["vitales_nacional"], cod_indicador=["NACIMIENTOS", "DEFUNCIONES"])
    both = pd.concat([nac, reg[reg.cod_territorio != "00"]])
    reglas.suma_partes(both, "vitales_sigungu", ctl, both.cod_territorio == "00", both.cod_territorio != "00", idx,
                       "suma_sido_igual_nacional", tol, "Σ 17 si-do (DT_1B8000I) = nacional (DT_1B8000F)")

    # 2. Nacimientos por sexo: H + M = T
    ns = k["nacimientos_sexo"]
    reglas.suma_partes(ns, "nacimientos_sexo", ctl, ns.cod_sexo == "T", ns.cod_sexo.isin(["H", "M"]),
                       ["anio", "cod_territorio", "cod_indicador"], "hombres_mas_mujeres_igual_total", tol, "H + M = T")

    # 3. Identidad contable: crecimiento natural = nacimientos - defunciones
    w = nac_w = k["vitales_nacional"].pivot_table(index="anio", columns="cod_indicador", values="valor")
    reglas.igualdad(w["CRECIMIENTO_NATURAL"], w["NACIMIENTOS"] - w["DEFUNCIONES"], "vitales_nacional", ctl,
                    "identidad_crecimiento_natural", 0.5, "crecimiento natural = nacimientos - defunciones")

    # 4. Población: Σ quinquenales = total; H + M = T; Σ si-do = nacional
    for ds in ["poblacion_nacional", "poblacion_sido", "proyeccion_escenarios"]:
        p = k[ds]
        claves = ["anio", "cod_territorio", "cod_sexo"] + (["cod_escenario"] if "cod_escenario" in p else [])
        quin = p.cod_edad.isin(derivados.QUINQUENALES)
        reglas.suma_partes(p, ds, ctl, p.cod_edad == "TOTAL", quin, claves, "suma_edades_igual_total", tol,
                           "Σ grupos quinquenales (85+ agregado) = total")
        c2 = [c for c in claves if c != "cod_sexo"] + ["cod_edad"]
        reglas.suma_partes(p, ds, ctl, p.cod_sexo == "T", p.cod_sexo.isin(["H", "M"]), c2,
                           "hombres_mas_mujeres_igual_total", tol, "H + M = T")
    ps = k["poblacion_sido"]
    ps = ps[ps.cod_edad == "TOTAL"]
    reglas.suma_partes(ps, "poblacion_sido", ctl, ps.cod_territorio == "00", ps.cod_territorio != "00",
                       ["anio", "cod_sexo"], "suma_sido_igual_nacional", tol, "Σ 17 si-do = Whole country")
    pn = _sel(k["poblacion_nacional"], cod_edad="TOTAL").set_index(["anio", "cod_sexo"])["valor"]
    pw = ps[ps.cod_territorio == "00"].set_index(["anio", "cod_sexo"])["valor"]
    reglas.igualdad(pn, pw, "poblacion_sido", ctl, "nacional_igual_entre_tablas", tol,
                    "Whole country de DT_1BPB001 = total de DT_1BPA001", relativa=True)

    # 5. Escenarios: el año base 2022 es común a todos los escenarios (punto de partida idéntico)
    pe = _sel(k["proyeccion_escenarios"], anio=2022, cod_edad="TOTAL", cod_sexo="T")
    base = _sel(k["poblacion_nacional"], anio=2022, cod_edad="TOTAL", cod_sexo="T")["valor"]
    if len(pe) and len(base):
        dif = (pe.valor - base.iloc[0]).abs() / base.iloc[0] * 100
        ctl.validar("proyeccion_escenarios", "anio_base_comun", "consistencia", int((dif > 0.01).sum()), len(pe),
                    not (dif > 0.01).any(), f"población 2022 idéntica en los {len(pe)} escenarios ({base.iloc[0]:,.0f})")

    # 6. EAPS: identidades contables y tasas publicadas vs recalculadas
    for ds in ["eaps_sido", "eaps_sexo_edad"]:
        e = k[ds]
        llave = ["anio", "cod_territorio", "cod_sexo", "cod_edad"]
        w = e.pivot_table(index=llave, columns="cod_indicador", values="valor")
        # Los niveles se publican redondeados a miles (±500 personas) y las tasas a 1 decimal (±0,05 pp): la
        # tolerancia es el error máximo que puede producir ese redondeo, no un umbral arbitrario.
        r = 500.0
        reglas.igualdad(w["POB_ACTIVA"], w["OCUPADOS"] + w["DESOCUPADOS"], ds, ctl, "activos_igual_ocupados_mas_desocupados",
                        3 * r, "PEA = ocupados + desocupados (personas; niveles redondeados a miles)")
        reglas.igualdad(w["POB_15MAS"], w["POB_ACTIVA"] + w["INACTIVOS"], ds, ctl, "pob15_igual_activos_mas_inactivos",
                        3 * r, "Pob 15+ = PEA + inactivos (personas; niveles redondeados a miles)")
        tol_tp = 100 * (r / w["POB_15MAS"] + w["POB_ACTIVA"] * r / w["POB_15MAS"] ** 2) + 0.05
        tol_td = 100 * (r / w["POB_ACTIVA"] + w["DESOCUPADOS"] * r / w["POB_ACTIVA"] ** 2) + 0.05
        reglas.igualdad(w["TASA_PARTICIPACION"], w["POB_ACTIVA"] / w["POB_15MAS"] * 100, ds, ctl,
                        "tasa_participacion_recalculada", tol_tp, "TP publicada vs PEA / Pob15+ × 100 (pp)")
        reglas.igualdad(w["TASA_DESEMPLEO"], w["DESOCUPADOS"] / w["POB_ACTIVA"] * 100, ds, ctl,
                        "tasa_desempleo_recalculada", tol_td, "TD publicada vs desocupados / PEA × 100 (pp)")
    e = _sel(k["eaps_sido"], cod_indicador=["POB_ACTIVA", "OCUPADOS", "POB_15MAS"])
    reglas.suma_partes(e, "eaps_sido", ctl, e.cod_territorio == "00", e.cod_territorio != "00", idx,
                       "suma_sido_igual_nacional", 0.5, "Σ si-do = total nacional (EAPS)")

    # 7. Censo de registros: Σ si-do = nacional; extranjeros <= total
    c = _sel(k["censo_registros"], cod_indicador=["POB_CENSO_TOTAL", "POB_EXTRANJERA"], cod_sexo="T")
    reglas.suma_partes(c, "censo_registros", ctl, c.cod_territorio == "00", c.cod_territorio != "00", idx,
                       "suma_sido_igual_nacional", tol, "Σ si-do = nacional (censo de registros)")


# ------------------------------------------------------------------------------------------------- conciliación
NO_COMPARABLE = {
    ("TASA_PARTICIPACION", "WB"): "World Bank publica una estimación modelada de la OIT; no es la EAPS",
}


def conciliar(t: dict, ctl: Control) -> pd.DataFrame:
    tol = cargar_config()["calidad"]["tolerancia_conciliacion_pct"]
    h = t["fact_historico"]
    # la población maestra se agrega a grupos funcionales para compararla con World Bank
    pob = h[(h.cod_indicador == "POBLACION") & (h.cod_territorio == "00")]
    agg = derivados.agregados_funcionales(pob, ["anio", "cod_territorio", "cod_sexo"])
    maestra = pd.concat([h, agg.assign(fuente="KOSIS", dataset="poblacion_nacional", tabla_fuente="DT_1BPA001")],
                        ignore_index=True)
    c = t["fact_contraste"]
    m = maestra[reglas.CLAVE + ["valor", "fuente", "dataset"]].rename(
        columns={"valor": "valor_maestra", "fuente": "fuente_maestra", "dataset": "dataset_maestra"})
    x = c[reglas.CLAVE + ["valor", "fuente", "dataset"]].rename(
        columns={"valor": "valor_contraste", "fuente": "fuente_contraste", "dataset": "dataset_contraste"})
    con = m.merge(x, on=reglas.CLAVE, how="inner")
    con = con[con.dataset_maestra != con.dataset_contraste]
    con["dif_abs"] = con.valor_contraste - con.valor_maestra
    con["dif_pct"] = con.dif_abs / con.valor_maestra.abs().replace(0, np.nan) * 100
    con["comparable"] = True
    con["nota"] = ""
    for (ind, fuente), nota in NO_COMPARABLE.items():
        mk = (con.cod_indicador == ind) & (con.fuente_contraste == fuente)
        con.loc[mk, "comparable"] = False
        con.loc[mk, "nota"] = nota
    con["dentro_tolerancia"] = con.dif_pct.abs() <= tol
    ev = con[con.comparable & con.anio.between(2000, 2025)]
    ok = int(ev.dentro_tolerancia.sum())
    meta = cargar_config()["calidad"]["objetivo_conciliacion_pct"]
    pct = ok / len(ev) * 100 if len(ev) else 0
    ctl.validar("conciliacion", "maestra_vs_contraste", "consistencia_entre_fuentes", len(ev) - ok, len(ev),
                pct >= meta, f"{pct:.1f} % de {len(ev)} pares año-indicador dentro de ±{tol} % (meta ≥ {meta} %)",
                "documentar desvíos" if pct < 100 else "")
    for (ind, fc), g in ev.groupby(["cod_indicador", "fuente_contraste"]):
        ctl.validar("conciliacion", f"{ind} vs {fc}", "consistencia_entre_fuentes", int((~g.dentro_tolerancia).sum()),
                    len(g), bool(g.dentro_tolerancia.all()),
                    f"dif. máx {g.dif_pct.abs().max():.2f} %; mediana {g.dif_pct.abs().median():.2f} %")
    return con.reset_index(drop=True)
