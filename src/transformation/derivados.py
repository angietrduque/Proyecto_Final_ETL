"""Cálculos derivados: una sola fórmula para todos los años, territorios, sexos y escenarios.

Se calculan dentro del pipeline (no se toman ya calculados de fuentes con definiciones distintas, p. ej. la OCDE
define la dependencia de vejez como 65+/20-64). Las fórmulas están documentadas en config/mappings/indicadores.csv.
"""
import numpy as np
import pandas as pd

QUINQUENALES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54",
                "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]
GRUPOS = {
    "0-14": ["0-4", "5-9", "10-14"],
    "15-64": ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64"],
    "65+": ["65-69", "70-74", "75-79", "80-84", "85+"],
}


def pivot_edades(pob: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """Población quinquenal en formato ancho (una columna por grupo de edad) para las claves dadas."""
    q = pob[pob.cod_edad.isin(QUINQUENALES)]
    return q.pivot_table(index=claves, columns="cod_edad", values="valor", aggfunc="sum")


def agregados_funcionales(pob: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """Filas nuevas de POBLACION para 0-14, 15-64 y 65+ (suma de quinquenales). Devuelve formato largo."""
    w = pivot_edades(pob, claves)
    filas = []
    for g, cols in GRUPOS.items():
        s = w.reindex(columns=cols).sum(axis=1, min_count=len(cols))
        filas.append(s.rename("valor").reset_index().assign(cod_edad=g))
    out = pd.concat(filas, ignore_index=True)
    out["cod_indicador"] = "POBLACION"
    return out.dropna(subset=["valor"])


def indicadores_estructura(pob: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """Indicadores de estructura por edad (formato largo, cod_edad = TOTAL)."""
    w = pivot_edades(pob, claves)
    if w.empty:
        return pd.DataFrame(columns=claves + ["cod_indicador", "valor", "cod_edad"])
    s = lambda cols: w.reindex(columns=cols).sum(axis=1, min_count=len(cols))  # noqa: E731
    p014, p1564, p65 = s(GRUPOS["0-14"]), s(GRUPOS["15-64"]), s(GRUPOS["65+"])
    tot = s(QUINQUENALES)
    p80 = s(["80-84", "85+"])
    p1524, p5564 = s(["15-19", "20-24"]), s(["55-59", "60-64"])
    div = lambda a, b: a / b.replace(0, np.nan)  # noqa: E731
    calc = {
        "PROP_0_14": div(p014, tot) * 100,
        "PROP_15_64": div(p1564, tot) * 100,
        "PROP_65MAS": div(p65, tot) * 100,
        "PROP_80MAS": div(p80, tot) * 100,
        "DEP_JUVENIL": div(p014, p1564) * 100,
        "DEP_VEJEZ": div(p65, p1564) * 100,
        "DEP_TOTAL": div(p014 + p65, p1564) * 100,
        "IND_ENVEJECIMIENTO": div(p65, p014) * 100,
        "RATIO_SOPORTE": div(p1564, p65),
        "IND_REEMPLAZO_LABORAL": div(p1524, p5564) * 100,
    }
    out = pd.concat([v.rename("valor").reset_index().assign(cod_indicador=k) for k, v in calc.items()], ignore_index=True)
    out["cod_edad"] = "TOTAL"
    return out.dropna(subset=["valor"])
