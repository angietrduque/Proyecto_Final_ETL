"""Capa SILVER: datos limpios, tipados, homologados, validados e integrables.

Grano común (formato largo): UNA FILA = el valor de un indicador para un año, un territorio, un sexo y un grupo de
edad [y un escenario, en proyecciones]. Clave natural: anio + cod_territorio + cod_sexo + cod_edad + cod_indicador
[+ cod_escenario + edicion_proyeccion].

Tablas que produce (data/silver/*.parquet y esquema silver en SQL):
  fact_historico      valores OBSERVADOS / ESTIMADOS de las fuentes maestras (nunca proyecciones)
  fact_proyeccion     proyecciones oficiales KOSTAT sin modificar (29 escenarios nacionales, medio regional)
  fact_contraste      mismos indicadores en fuentes de contraste (KOSIS secundarias, World Bank, OECD) para conciliar
  fact_internacional  World Bank / OECD para Corea y países de comparación
  sin_dato            celdas vacías ("-") clasificadas como esperadas o inesperadas (KPI de completitud)
  dim_escenario       escenarios de proyección KOSTAT con sus supuestos

Transformaciones (en orden, con conteo antes/después en ctl.conteos):
  1. formato largo (melt) de las tablas anchas de KOSIS
  2. filtro de periodos fuera de alcance (columnas mensuales "2026.05 p)")
  3. selección de variables (ítems) mapeadas en config/mappings/items_kosis.csv
  4. homologación de territorio, sexo, edad y escenario a códigos de dimensión
  5. filtro de unidades territoriales fuera de alcance (Abroad, si-gun-gu, provincias previas a 1945)
  6. conversión de tipos (texto -> número), unidades (miles -> personas) y marca preliminar/definitivo
  7. separación de celdas sin dato (no se imputan)
  8. agregación de edades 85-89 ... 100+ en 85+ (exclusión del agregado redundante 80+)
  9. reglas de aceptación (src/validation/reglas.py) -> rechazos trazados
"""
import logging
import re

import numpy as np
import pandas as pd

from src.ingestion.bronze import existe_vigente, leer_vigente
from src.transformation import homologacion as hom
from src.utils.config import cargar_config, ruta
from src.utils.control import Control
from src.validation import reglas

log = logging.getLogger("silver")
COLS = ["anio", "cod_territorio", "cod_sexo", "cod_edad", "cod_indicador", "valor", "estado", "tipo_dato",
        "fuente", "tabla_fuente", "dataset", "version_fuente", "fecha_extraccion", "etiqueta_original"]


# =============================================================================================== utilidades
def _periodo(p: str) -> tuple[int | None, bool, bool]:
    """'2025' | '2025 Year' | '2022 년' | '2025 p)' -> (anio, es_anual, preliminar). Meses '2026.05' -> no anual."""
    p = str(p).strip()
    m = re.fullmatch(r"(\d{4})(?:\s*(?:Year|년))?(\s*p\))?", p)
    if m:
        return int(m.group(1)), True, bool(m.group(2))
    return None, False, "p)" in p


def melt_kosis(df: pd.DataFrame, n_dims: int, nombres_dims: list[str]) -> pd.DataFrame:
    """Tabla ancha de KOSIS -> largo con columnas de dimensión, periodo, item (si encabezado doble) y valor_txt."""
    dims = list(df.columns[:n_dims])
    largo = df.melt(id_vars=dims, var_name="columna", value_name="valor_txt")
    largo = largo.rename(columns=dict(zip(dims, nombres_dims)))
    partes = largo["columna"].str.split(" | ", n=1, regex=False)
    largo["periodo"] = partes.str[0]
    largo["item_col"] = partes.str[1]
    return largo


def _completar(df: pd.DataFrame, meta: dict, dataset: str, tipo_dato: str) -> pd.DataFrame:
    df = df.copy()
    df["fuente"] = meta["fuente"]
    df["tabla_fuente"] = meta.get("tbl_id") or meta.get("tabla_fuente")
    df["dataset"] = dataset
    df["version_fuente"] = meta.get("version")
    df["fecha_extraccion"] = meta.get("fecha_extraccion")
    if "tipo_dato" not in df:
        df["tipo_dato"] = tipo_dato
    if "estado" not in df:
        df["estado"] = "definitivo"
    for c in COLS:
        if c not in df:
            df[c] = pd.NA
    return df


def _clasificar_sin_dato(df: pd.DataFrame) -> pd.Series:
    """Motivo esperado de una celda vacía (o 'inesperado')."""
    terr = hom.mapping("territorios").set_index("cod_territorio")
    desde = pd.to_numeric(df["cod_territorio"].map(terr["vigente_desde"]), errors="coerce")
    motivo = pd.Series("inesperado", index=df.index)
    motivo[desde.notna() & (df["anio"] < desde)] = "territorio aún no existía como si-do"
    motivo[df["cod_territorio"] == "__RECHAZO__"] = "región combinada (Jeonnam-Gwangju) sólo publicada en 2025"
    motivo[(df["dataset"] == "censo_historico") & (motivo == "inesperado")] = \
        "grupo de edad o territorio no publicado en ese censo"
    motivo[(df["cod_territorio"] == "29") & (df["dataset"].isin(["eaps_sido"])) & (df["anio"] < 2017)] = \
        "EAPS publica Sejong desde 2017"
    motivo[(df["cod_indicador"] == "ESPERANZA_VIDA") & (df["anio"] == 2025)] = "tabla de vida 2025 aún no publicada"
    motivo[(df["cod_indicador"] == "MORTALIDAD_INFANTIL") & (df["anio"] < 2009)] = "serie publicada desde 2009"
    motivo[(df["cod_territorio"] != "00") & (df["dataset"] == "nacimientos_sexo")
           & df["cod_indicador"].isin(["MATRIMONIOS", "DIVORCIOS"])] = "no se desagrega por sexo"
    motivo[df["cod_sexo"].isin(["H", "M"]) & df["cod_indicador"].isin(["MATRIMONIOS", "DIVORCIOS"])] = \
        "no se desagrega por sexo"
    motivo[df["cod_indicador"].isin(["TASA_FEC_EDAD"]) & (df["cod_territorio"] == "29")] = \
        "territorio aún no existía (Sejong < 2012)"
    return motivo


def estandarizar_kosis(dataset: str, ctl: Control, n_dims: int, nombres_dims: list[str], tipo_dato: str,
                       territorio_fijo: str | None = None, sexo_fijo: str | None = None,
                       edad_desde_dim: bool = False, item_desde_dim: str | None = None,
                       territorio_no_mapeado: str = "rechazar",
                       escenarios: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pipeline genérico de estandarización de una tabla KOSIS. Devuelve (validos, sin_dato)."""
    raw, meta = leer_vigente("KOSIS", dataset)
    if "territorio" in nombres_dims and dataset == "nacimientos_sexo":
        # Estructura de la descarga: el nombre del si-do sólo aparece en la fila "Total"; Male/Female lo heredan.
        raw.iloc[:, 0] = raw.iloc[:, 0].replace("", pd.NA).ffill()
        ctl.contar("silver", dataset, "relleno hacia abajo del si-do (celdas combinadas en la descarga)", len(raw), len(raw))
    df = melt_kosis(raw, n_dims, nombres_dims)
    n_celdas = len(df)
    ctl.contar("silver", dataset, "formato largo (melt)", len(raw), n_celdas, f"{raw.shape[1] - n_dims} columnas de periodo/ítem")

    # 2. periodos fuera de alcance
    info = df["periodo"].map(_periodo)
    df["anio"] = info.str[0]
    df["estado"] = np.where(info.str[2], "preliminar", "definitivo")
    anual = info.str[1].astype(bool)
    no_periodo = df["periodo"].str.startswith("_columna_")
    ctl.contar("silver", dataset, "descartar columnas no anuales (meses) y columnas vacías", n_celdas, int(anual.sum()),
               f"{int((~anual & ~no_periodo).sum())} celdas mensuales/fuera de periodo; {int(no_periodo.sum())} de columna vacía")
    df = df[anual]

    # 3. selección de variables
    it = hom.items(dataset)
    item_src = df[item_desde_dim] if item_desde_dim else df["item_col"]
    df["item"] = item_src.fillna("*").astype(str).str.strip()   # tablas sin columna de ítem: una sola variable
    n = len(df)
    df = df.merge(it, on="item", how="left")
    fuera_item = df["cod_indicador"].isna()
    if fuera_item.any():
        excl = df.loc[fuera_item, "item"].value_counts()
        nota = "; ".join(f"{k} ({v})" for k, v in excl.head(8).items())
    else:
        nota = ""
    df = df[~fuera_item]
    ctl.contar("silver", dataset, "selección de variables mapeadas (items_kosis.csv)", n, len(df),
               f"ítems no usados: {nota}" if nota else "todas las variables mapeadas")

    # 4-5. homologación de dimensiones
    df["etiqueta_original"] = df["item"]
    if territorio_fijo:
        df["cod_territorio"] = territorio_fijo
    else:
        df["etiqueta_original"] = df["territorio"].astype(str).str.strip() + " · " + df["item"]
        df["cod_territorio"] = hom.territorio(df["territorio"])
        if territorio_no_mapeado == "fuera":
            df.loc[df.cod_territorio == hom.NO_MAPEADO, "cod_territorio"] = "__FUERA__"
    n = len(df)
    fuera_terr = df["cod_territorio"] == "__FUERA__"
    excl = df.loc[fuera_terr, "territorio"].nunique() if "territorio" in df else 0
    df = df[~fuera_terr]
    ctl.contar("silver", dataset, "excluir unidades territoriales fuera de alcance", n, len(df),
               f"{excl} etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945)")

    if "cod_sexo" in it.columns and "sexo" in df:
        df["cod_sexo"] = df["cod_sexo"].fillna("").mask(df["cod_sexo"].fillna("") == "", hom.sexo(df["sexo"]))
    elif "sexo" in df:
        df["cod_sexo"] = hom.sexo(df["sexo"])
    df["cod_sexo"] = df["cod_sexo"].fillna("").replace("", sexo_fijo or "T")

    df["cod_edad"] = df["cod_edad"].fillna("")
    if edad_desde_dim:
        cod, accion = hom.edad(df["edad"], dataset)
        df["cod_edad"] = df["cod_edad"].mask(df["cod_edad"] == "", cod)
        df["accion_edad"] = accion
    else:
        df["cod_edad"] = df["cod_edad"].replace("", "TOTAL")
        df["accion_edad"] = "usar"
    n = len(df)
    df = df[df["accion_edad"] != "excluir"]
    ctl.contar("silver", dataset, "excluir agregados de edad redundantes (80+)", n, len(df))

    if escenarios is not None:
        df["cod_escenario"] = df["escenario"].astype(str).str.strip().map(
            dict(zip(escenarios.etiqueta, escenarios.cod_escenario))).fillna(hom.NO_MAPEADO)
        malo = df["cod_escenario"] == hom.NO_MAPEADO
        ctl.validar(dataset, "integridad_cod_escenario", "integridad_referencial", int(malo.sum()), len(df), not malo.any(),
                    "escenario de proyección reconocido en dim_escenario", "rechazar registro" if malo.any() else "")
        ctl.rechazar(dataset, "integridad_cod_escenario", "escenario no reconocido", df[malo])
        df = df[~malo]

    # 6. tipos y unidades
    df["valor"] = reglas.a_numero(df["valor_txt"]) * pd.to_numeric(df["factor"]).fillna(1)
    sin = df[df["valor"].isna()].copy()
    df = df[df["valor"].notna()]
    ctl.contar("silver", dataset, "separar celdas sin dato (no se imputan)", n, len(df), f"{len(sin)} celdas vacías o '-'")

    # 8. 85-89 ... 100+ -> 85+
    if (df["accion_edad"] == "colapsar").any():
        n = len(df)
        grupo = [c for c in df.columns if c not in ("valor", "valor_txt", "edad", "item_col", "columna")]
        base = df[df.accion_edad != "colapsar"]
        col = df[df.accion_edad == "colapsar"].groupby([c for c in grupo if c != "etiqueta_original"], dropna=False,
                                                         as_index=False)["valor"].sum()
        col["etiqueta_original"] = "85-89 + 90-94 + 95-99 + 100+"
        df = pd.concat([base, col], ignore_index=True)
        ctl.contar("silver", dataset, "agregar 85-89, 90-94, 95-99 y 100+ en 85+", n, len(df))

    df = _completar(df, meta, dataset, tipo_dato)
    sin = _completar(sin, meta, dataset, tipo_dato)
    sin["motivo"] = _clasificar_sin_dato(sin) if len(sin) else pd.Series(dtype=str)
    extra = ["cod_escenario"] if escenarios is not None else []
    validos = reglas.aceptar(df, dataset, ctl, clave=reglas.CLAVE + extra)
    return validos[COLS + extra], sin[COLS + ["motivo"]]


# =============================================================================================== KOSIS
def dimension_escenarios() -> pd.DataFrame:
    etiquetas = pd.concat([leer_vigente("KOSIS", "poblacion_nacional")[0].iloc[:, 0],
                           leer_vigente("KOSIS", "proyeccion_escenarios")[0].iloc[:, 0],
                           pd.Series(["Medium"])]).drop_duplicates()
    dim = hom.escenario(etiquetas)
    medio = dim[dim.cod_escenario == "medio"].iloc[0]
    for c in ["cod_escenario", "nombre_escenario", "familia", "orden"]:
        dim.loc[dim.etiqueta == "Medium", c] = medio[c]
    return dim


def silver_kosis(ctl: Control, dim_esc: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out, sin = {}, []

    def corre(nombre, *a, **k):
        v, s = estandarizar_kosis(nombre, ctl, *a, **k)
        out[nombre] = v
        sin.append(s)
        log.info("[silver] %-22s %7d registros válidos, %5d celdas sin dato", nombre, len(v), len(s))

    corre("vitales_nacional", 1, ["item_dim"], "observado", territorio_fijo="00", item_desde_dim="item_dim")
    corre("vitales_nacional_repo", 1, ["item_dim"], "observado", territorio_fijo="00", item_desde_dim="item_dim")
    corre("vitales_sigungu", 1, ["territorio"], "observado")
    corre("vitales_sido", 1, ["territorio"], "observado")
    corre("vitales_sido_mensual", 1, ["territorio"], "observado")
    corre("nacimientos_sexo", 2, ["territorio", "sexo"], "observado")
    corre("tfr_sido", 1, ["territorio"], "observado")
    corre("eaps_sido", 1, ["territorio"], "observado")
    corre("eaps_sexo_edad", 2, ["sexo", "edad"], "observado", territorio_fijo="00", edad_desde_dim=True)
    corre("poblacion_nacional", 3, ["escenario", "sexo", "edad"], "estimado", territorio_fijo="00",
          edad_desde_dim=True, escenarios=dim_esc)
    corre("poblacion_sido", 6, ["escenario", "territorio", "sexo", "edad", "item_dim", "unidad"], "estimado",
          edad_desde_dim=True, item_desde_dim="item_dim", escenarios=dim_esc)
    corre("proyeccion_escenarios", 5, ["escenario", "sexo", "edad", "item_dim", "unidad"], "proyeccion_oficial",
          territorio_fijo="00", edad_desde_dim=True, item_desde_dim="item_dim", escenarios=dim_esc)
    corre("proyeccion_resumen", 2, ["escenario", "item_dim"], "proyeccion_oficial", territorio_fijo="00",
          item_desde_dim="item_dim")
    corre("censo_registros", 3, ["territorio", "item_dim", "unidad"], "observado", item_desde_dim="item_dim",
          territorio_no_mapeado="fuera")
    corre("censo_historico", 4, ["territorio", "edad", "item_dim", "unidad"], "observado", item_desde_dim="item_dim",
          edad_desde_dim=True)
    out["_sin_dato"] = pd.concat(sin, ignore_index=True)
    return out


# =============================================================================================== World Bank / OECD
WB_EDAD = {"SP.POP.1564.TO": ("POBLACION", "15-64"), "SP.POP.TOTL": ("POBLACION", "TOTAL"),
           "SP.POP.0014.TO": ("POBLACION", "0-14"), "SP.POP.65UP.TO": ("POBLACION", "65+")}


def _territorio_pais(iso3: pd.Series) -> pd.Series:
    return iso3.replace({"KOR": "00"})


def silver_worldbank(ctl: Control) -> pd.DataFrame:
    cfg = cargar_config()["worldbank"]["datasets"]
    partes = []
    for codigo, spec in cfg.items():
        ds = f"WB/{codigo}"
        if not existe_vigente("WB", codigo):
            ctl.validar(ds, "disponibilidad", "completitud", 1, 1, False, "sin versión en bronze")
            continue
        raw, meta = leer_vigente("WB", codigo)
        ind, edad = WB_EDAD.get(codigo, (spec["indicador"], "15+" if spec["indicador"] == "TASA_PARTICIPACION" else "TOTAL"))
        df = pd.DataFrame({"anio": pd.to_numeric(raw["date"]), "cod_territorio": _territorio_pais(raw["countryiso3code"]),
                           "cod_sexo": "T", "cod_edad": edad, "cod_indicador": ind,
                           "valor": reglas.a_numero(raw["value"]), "etiqueta_original": raw["indicator"]})
        df = _completar(df, {**meta, "tbl_id": codigo}, ds, "observado")
        n = len(df)
        df = df[df.valor.notna()]
        ctl.contar("silver", ds, "descartar años sin dato publicado", n, len(df), "la API devuelve null en años no publicados")
        partes.append(reglas.aceptar(df, ds, ctl))
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=COLS)


def silver_oecd(ctl: Control) -> pd.DataFrame:
    """Filtros obligatorios: los CSV de la OECD mezclan series (niveles, índices, tasas de crecimiento, sub-sectores)."""
    partes = []
    if existe_vigente("OECD", "productividad"):
        raw, meta = leer_vigente("OECD", "productividad")
        partes.append(("productividad", meta, raw[raw.TRANSFORMATION == "N"], "PIB_HORA", 1, "TOTAL"))
    if existe_vigente("OECD", "fuerza_laboral"):
        raw, meta = leer_vigente("OECD", "fuerza_laboral")
        b = raw[(raw.SEX == "_T") & (raw.AGE == "Y_GE15") & (raw.WORKER_STATUS == "_Z") & (raw.ACTIVITY == "_Z")]
        partes.append(("fuerza_laboral", meta, b[(b.MEASURE == "LF") & (b.UNIT_MEASURE == "PS")], "POB_ACTIVA", 1000, "15+"))
        partes.append(("fuerza_laboral", meta, b[(b.MEASURE == "EMP") & (b.UNIT_MEASURE == "PS")], "OCUPADOS", 1000, "15+"))
        partes.append(("fuerza_laboral", meta, b[(b.MEASURE == "UNE_LF") & (b.UNIT_MEASURE == "PT_LF_SUB")],
                       "TASA_DESEMPLEO", 1, "15+"))
    if existe_vigente("OECD", "fecundidad"):
        raw, meta = leer_vigente("OECD", "fecundidad")
        partes.append(("fecundidad", meta, raw[(raw.MEASURE == "FERT_RATIO") & (raw.AGE == "_T")], "TFR", 1, "TOTAL"))
        partes.append(("fecundidad", meta, raw[(raw.MEASURE == "LIVE_BIRTHS") & (raw.UNIT_MEASURE == "BR")],
                       "NACIMIENTOS", 1, "TOTAL"))
    salida = []
    if existe_vigente("OECD", "participacion_edad_sexo"):
        # promedio OCDE por sexo y edad: insumo del supuesto C (convergencia), sólo comparación internacional
        raw, meta = leer_vigente("OECD", "participacion_edad_sexo")
        edades = {"Y15T24": "15-24", "Y25T54": "25-54", "Y55T64": "55-64"}
        r = raw[(raw.REF_AREA == "OECD") & raw.SEX.isin(["M", "F"]) & raw.AGE.isin(edades)]
        ds = "OECD/participacion_edad_sexo/TASA_PARTICIPACION"
        df = pd.DataFrame({"anio": pd.to_numeric(r["TIME_PERIOD"].str[:4]), "cod_territorio": "OED",
                           "cod_sexo": r["SEX"].map({"M": "H", "F": "M"}), "cod_edad": r["AGE"].map(edades),
                           "cod_indicador": "TASA_PARTICIPACION", "valor": reglas.a_numero(r["OBS_VALUE"]),
                           "etiqueta_original": r["Measure"]})
        ctl.contar("silver", ds, "filtro de la serie relevante del dataflow", int(meta["filas"]), len(df))
        df = _completar(df, {**meta, "tbl_id": meta["params"].get("dataflow")}, ds, "observado")
        salida.append(reglas.aceptar(df, ds, ctl))
    for nombre, meta, r, ind, factor, edad in partes:
        ds = f"OECD/{nombre}/{ind}"
        df = pd.DataFrame({"anio": pd.to_numeric(r["TIME_PERIOD"].str[:4]), "cod_territorio": _territorio_pais(r["REF_AREA"]),
                           "cod_sexo": "T", "cod_edad": edad, "cod_indicador": ind,
                           "valor": reglas.a_numero(r["OBS_VALUE"]) * factor, "etiqueta_original": r["Measure"]})
        ctl.contar("silver", ds, "filtro de la serie relevante del dataflow", int(meta["filas"]), len(df))
        df = _completar(df, {**meta, "tbl_id": meta["params"].get("dataflow")}, ds, "observado")
        salida.append(reglas.aceptar(df, ds, ctl))
    return pd.concat(salida, ignore_index=True) if salida else pd.DataFrame(columns=COLS)


# =============================================================================================== ensamblaje
def TODO(d: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=d.index)


# dataset -> filas que son MAESTRAS del indicador; el resto de ese dataset se usa como CONTRASTE
MAESTRA = {
    "vitales_nacional": TODO,                                              # nacional 1970-2025 (DT_1B8000F)
    "vitales_sigungu": lambda d: d.cod_territorio.ne("00"),                # si-do completo 2000-2025 (DT_1B8000I)
    "nacimientos_sexo": lambda d: d.cod_sexo.isin(["H", "M"]),             # sólo la desagregación por sexo
    "tfr_sido": lambda d: d.cod_territorio.ne("00") | d.cod_indicador.eq("TASA_FEC_EDAD"),
    "eaps_sido": lambda d: d.cod_territorio.ne("00"),                      # nacional sale de eaps_sexo_edad
    "eaps_sexo_edad": TODO,
    "poblacion_nacional": lambda d: d.anio.le(2022),                       # 2023+ es proyección
    "poblacion_sido": lambda d: d.cod_territorio.ne("00") & d.anio.le(2022),
    "censo_registros": TODO,
    "censo_historico": TODO,
}
CONTRASTE = ["vitales_nacional_repo", "vitales_sido", "vitales_sido_mensual", "proyeccion_resumen"]


def construir(ctl: Control) -> dict[str, pd.DataFrame]:
    dim_esc = dimension_escenarios()
    k = silver_kosis(ctl, dim_esc)
    wb = silver_worldbank(ctl)
    oe = silver_oecd(ctl)

    hist, contr = [], []
    for ds, filtro in MAESTRA.items():
        d = k[ds]
        m = filtro(d)
        hist.append(d[m].drop(columns=["cod_escenario"], errors="ignore"))
        resto = d[~m]
        if ds.startswith("poblacion"):
            resto = resto[resto.anio.le(2022)]   # lo posterior a 2022 es proyección, no contraste
        contr.append(resto.drop(columns=["cod_escenario"], errors="ignore"))
    contr += [k[ds] for ds in CONTRASTE]
    fact_historico = pd.concat(hist, ignore_index=True)
    n = len(fact_historico)
    dup = fact_historico.duplicated(subset=reglas.CLAVE, keep="first")
    ctl.rechazar("fact_historico", "duplicado_entre_fuentes", "misma clave en dos tablas maestras", fact_historico[dup])
    ctl.validar("fact_historico", "unicidad_clave_integrada", "duplicados", int(dup.sum()), n, not dup.any(),
                "unicidad de la clave natural tras unir todas las tablas maestras")
    fact_historico = fact_historico[~dup]
    ctl.contar("silver", "fact_historico", "integración de tablas maestras (una por indicador)", n, len(fact_historico))

    # Proyecciones oficiales: nacional medio (DT_1BPA001 > 2022), 28 escenarios alternativos, regional medio (DT_1BPB001)
    pn, ps, pe = k["poblacion_nacional"], k["poblacion_sido"], k["proyeccion_escenarios"]
    fact_proyeccion = pd.concat([
        pn[pn.anio > 2022].assign(edicion_proyeccion="KOSTAT 2022-2072"),
        pe[pe.anio > 2022].assign(edicion_proyeccion="KOSTAT 2022-2072"),
        ps[(ps.anio > 2022) & ps.cod_territorio.ne("00")].assign(edicion_proyeccion="KOSTAT 2022-2052 (provincial)"),
    ], ignore_index=True).assign(tipo_dato="proyeccion_oficial")
    n = len(fact_proyeccion)
    dup = fact_proyeccion.duplicated(subset=reglas.CLAVE + ["cod_escenario", "edicion_proyeccion"])
    ctl.validar("fact_proyeccion", "unicidad_clave_proyeccion", "duplicados", int(dup.sum()), n, not dup.any(),
                "anio+territorio+sexo+edad+indicador+escenario+edición únicos")
    fact_proyeccion = fact_proyeccion[~dup]
    ctl.contar("silver", "fact_proyeccion", "integración de proyecciones oficiales (sin modificar valores)", n,
               len(fact_proyeccion), "el año base 2022 queda sólo en el histórico (tipo_dato = estimado)")

    fact_contraste = pd.concat(contr + [wb[wb.cod_territorio == "00"], oe[oe.cod_territorio == "00"]], ignore_index=True)
    fact_internacional = pd.concat([wb, oe], ignore_index=True)
    dim = dim_esc[dim_esc.etiqueta != "Medium"].drop_duplicates("cod_escenario")
    return {"fact_historico": fact_historico, "fact_proyeccion": fact_proyeccion, "fact_contraste": fact_contraste,
            "fact_internacional": fact_internacional, "sin_dato": k["_sin_dato"], "dim_escenario": dim, "_kosis": k}



def guardar(tablas: dict[str, pd.DataFrame]) -> None:
    for nombre, df in tablas.items():
        if nombre.startswith("_"):
            continue
        df.to_parquet(ruta("silver") / f"{nombre}.parquet", index=False)
        log.info("[silver] %-20s %8d filas -> data/silver/%s.parquet", nombre, len(df), nombre)


def ejecutar(ctl: Control) -> dict[str, pd.DataFrame]:
    tablas = construir(ctl)
    from src.validation import consistencia
    consistencia.ejecutar(tablas, ctl)
    tablas["conciliacion"] = consistencia.conciliar(tablas, ctl)
    guardar(tablas)
    return tablas


def leer(nombre: str) -> pd.DataFrame:
    return pd.read_parquet(ruta("silver") / f"{nombre}.parquet")
