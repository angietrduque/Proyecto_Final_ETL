"""Homologación de etiquetas de las fuentes a los códigos de las dimensiones (config/mappings/*.csv).

Las fuentes nombran lo mismo de formas distintas ("Gangwon", "Gangwon-do", "강원"; "35-39 years old", "35 - 39세").
Aquí se traduce cada etiqueta a un código estable. Las etiquetas sin traducción NO se descartan en silencio:
se devuelven como "__NO_MAPEADO__" para que la capa de validación las rechace con su motivo.
"""
import re
from functools import lru_cache

import pandas as pd

from src.utils.config import ruta

NO_MAPEADO = "__NO_MAPEADO__"


@lru_cache(maxsize=None)
def mapping(nombre: str) -> pd.DataFrame:
    return pd.read_csv(ruta("mappings") / f"{nombre}.csv", dtype=str, keep_default_na=False)


def _limpiar(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def territorio(etiquetas: pd.Series) -> pd.Series:
    m = dict(zip(mapping("territorios_alias")["alias"], mapping("territorios_alias")["cod_territorio"]))
    return _limpiar(etiquetas).map(m).fillna(NO_MAPEADO)


def sexo(etiquetas: pd.Series) -> pd.Series:
    m = {}
    for r in mapping("sexo").itertuples():
        for a in r.alias.split("|"):
            m[a] = r.cod_sexo
    return _limpiar(etiquetas).map(m).fillna(NO_MAPEADO)


def edad(etiquetas: pd.Series, dataset: str) -> tuple[pd.Series, pd.Series]:
    """(cod_edad, accion) con prioridad a los alias específicos del dataset sobre los genéricos (*)."""
    al = mapping("edades_alias")
    gen = al[al.dataset == "*"]
    esp = al[al.dataset == dataset]
    m = {**dict(zip(gen.alias, gen.cod_edad)), **dict(zip(esp.alias, esp.cod_edad))}
    acc = {**dict(zip(gen.alias, gen.accion)), **dict(zip(esp.alias, esp.accion))}
    e = _limpiar(etiquetas)
    return e.map(m).fillna(NO_MAPEADO), e.map(acc).fillna("rechazar")


def items(dataset: str) -> pd.DataFrame:
    it = mapping("items_kosis")
    return it[it.dataset == dataset].drop(columns="dataset")


def escenario(etiquetas: pd.Series) -> pd.DataFrame:
    """Etiqueta KOSTAT (coreano) -> cod_escenario + componentes (fecundidad / esperanza de vida / migración)."""
    esc = mapping("escenarios")
    niveles = {"고위": "alta", "저위": "baja", "중위": "media", "무이동": "cero",
               "2022년 출산율 유지": "constante_2022", "OECD 평균": "promedio_ocde", "코로나19장기영향지속": "covid_largo"}

    def comp(texto: str, clave: str) -> str:
        m = re.search(clave + r"-([^/)]+)", texto)
        return niveles.get(m.group(1).strip(), m.group(1).strip()) if m else ""

    filas = []
    for t in _limpiar(etiquetas).unique():
        fila = esc[[t.startswith(p) for p in esc.prefijo_ko]]
        f, e, mi = comp(t, "출산율"), comp(t, "기대수명"), comp(t, "국제순이동")
        if fila.empty:
            cod, nombre, familia, orden = NO_MAPEADO, t, "", 99
        else:
            r = fila.iloc[0]
            cod, nombre, familia, orden = r.cod_escenario, r.nombre_es, r.familia, int(r.orden)
            if cod == "otro":
                cod = f"otro_F{f}_E{e}_M{mi}"
                nombre = f"Otra: fecundidad {f}, esp. vida {e}, migración {mi}"
        filas.append({"etiqueta": t, "cod_escenario": cod, "nombre_escenario": nombre, "familia": familia,
                      "supuesto_fecundidad": f, "supuesto_esperanza_vida": e, "supuesto_migracion": mi, "orden": orden})
    return pd.DataFrame(filas)
