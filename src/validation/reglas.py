"""Reglas de calidad de datos (Silver).

Dos tipos de reglas:
  * Reglas de ACEPTACIÓN (por registro): si un registro las incumple se RECHAZA, se guarda en ctl.rechazos con la
    regla y el motivo, y no pasa a Silver. -> tipos, fechas, integridad referencial, rangos, duplicados, etiquetas
    inesperadas.
  * Reglas de CONSISTENCIA (por conjunto): comparan agregados (suma de si-do = nacional, H + M = T, activos =
    ocupados + desocupados, tasa publicada = tasa recalculada, maestra ≈ contraste). No rechazan registros: dejan
    evidencia en ctl.validaciones (PASA/FALLA) para que un analista revise.

Valores faltantes: las celdas sin dato ("-", vacías) NO son errores ni se imputan (no se inventan datos demográficos).
Se cuentan por separado para el KPI de completitud y se clasifican como esperadas o inesperadas.
"""
import numpy as np
import pandas as pd

from src.transformation import homologacion as hom
from src.utils.control import Control

CLAVE = ["anio", "cod_territorio", "cod_sexo", "cod_edad", "cod_indicador"]


def dimensiones() -> dict[str, set]:
    return {"cod_territorio": set(hom.mapping("territorios").cod_territorio),
            "cod_sexo": set(hom.mapping("sexo").cod_sexo),
            "cod_edad": set(hom.mapping("edades").cod_edad),
            "cod_indicador": set(hom.mapping("indicadores").cod_indicador)}


def a_numero(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.replace(",", "", regex=False).str.strip()
    t = t.mask(t.isin(["", "-", "x", "X", "...", "nan", "None", "<NA>"]))
    return pd.to_numeric(t, errors="coerce")


def aceptar(df: pd.DataFrame, dataset: str, ctl: Control, clave: list[str] | None = None) -> pd.DataFrame:
    """Aplica las reglas de aceptación y devuelve sólo los registros válidos. Registra rechazos y conteos."""
    clave = clave or CLAVE
    n0 = len(df)
    dims = dimensiones()
    df = df.copy()
    rechazado = pd.Series(False, index=df.index)

    def marcar(mask: pd.Series, regla: str, motivo: str, tipo: str) -> None:
        nonlocal rechazado
        nuevos = mask & ~rechazado
        ctl.validar(dataset, regla, tipo, int(nuevos.sum()), n0, pasa=not nuevos.any(), detalle=motivo,
                    accion="rechazar registro" if nuevos.any() else "")
        if nuevos.any():
            ctl.rechazar(dataset, regla, motivo, df[nuevos])
        rechazado |= nuevos

    # 1. Registros inesperados / integridad referencial
    for col, validos in dims.items():
        if col in df:
            m = ~df[col].isin(validos)
            ejemplos = ", ".join(sorted(df.loc[m, col].astype(str).unique())[:5])
            marcar(m, f"integridad_{col}", f"código fuera de la dimensión {col} ({ejemplos})" if m.any() else
                   f"todos los {col} existen en la dimensión", "integridad_referencial")
    # 2. Fechas (año válido)
    anio = pd.to_numeric(df["anio"], errors="coerce")
    marcar(anio.isna() | (anio < 1900) | (anio > 2100), "fecha_valida", "año no numérico o fuera de [1900, 2100]", "fechas")
    df["anio"] = anio.astype("Int64")
    # 3. Tipo de dato del valor
    marcar(df["valor"].isna(), "tipo_valor", "valor no numérico tras la conversión", "tipos")
    # 4. Rangos válidos por indicador
    ind = hom.mapping("indicadores").set_index("cod_indicador")
    rmin = pd.to_numeric(df["cod_indicador"].map(ind["rango_min"]), errors="coerce")
    rmax = pd.to_numeric(df["cod_indicador"].map(ind["rango_max"]), errors="coerce")
    fuera = (rmin.notna() & (df["valor"] < rmin)) | (rmax.notna() & (df["valor"] > rmax))
    marcar(fuera, "rango_valido", "valor fuera del rango plausible definido en dim_indicador", "rangos")
    # 5. Duplicados sobre la clave natural
    dup = df.duplicated(subset=clave, keep="first") & ~rechazado
    marcar(dup, "duplicado_clave", f"clave natural repetida ({' + '.join(clave)}); se conserva la primera aparición",
           "duplicados")

    validos = df[~rechazado].copy()
    ctl.contar("silver", dataset, "reglas de aceptación", n0, len(validos),
               f"{int(rechazado.sum())} rechazados ({rechazado.mean() * 100 if n0 else 0:.2f} %)")
    return validos


# ------------------------------------------------------------------------------------- consistencia
def suma_partes(df: pd.DataFrame, dataset: str, ctl: Control, total_mask, partes_mask, por: list[str],
                regla: str, tolerancia_pct: float, descripcion: str) -> pd.DataFrame:
    """Compara la suma de las partes con el total publicado. Devuelve la tabla de diferencias."""
    tot = df[total_mask].groupby(por)["valor"].sum()
    par = df[partes_mask].groupby(por)["valor"].sum()
    comp = pd.concat({"total": tot, "suma_partes": par}, axis=1).dropna()
    comp["dif_pct"] = (comp.suma_partes - comp.total) / comp.total.replace(0, np.nan) * 100
    malos = comp["dif_pct"].abs() > tolerancia_pct
    ctl.validar(dataset, regla, "consistencia", int(malos.sum()), len(comp), pasa=not malos.any(),
                detalle=f"{descripcion}; tolerancia ±{tolerancia_pct} %; dif. máx {comp.dif_pct.abs().max():.3f} %"
                if len(comp) else descripcion, accion="revisar" if malos.any() else "")
    return comp.reset_index()


def igualdad(a: pd.Series, b: pd.Series, dataset: str, ctl: Control, regla: str, tolerancia,
             descripcion: str, relativa: bool = False) -> pd.DataFrame:
    """tolerancia: número fijo o Serie alineada con `a` (p. ej. el error máximo atribuible al redondeo)."""
    comp = pd.concat({"publicado": a, "recalculado": b}, axis=1).dropna()
    dif = comp.recalculado - comp.publicado
    if relativa:
        dif = dif / comp.publicado.replace(0, np.nan) * 100
    comp["dif"] = dif
    tol = tolerancia.reindex(comp.index) if isinstance(tolerancia, pd.Series) else tolerancia
    comp["tolerancia"] = tol
    malos = comp.dif.abs() > comp.tolerancia
    txt_tol = "error máximo de redondeo" if isinstance(tolerancia, pd.Series) else f"±{tolerancia}{' %' if relativa else ''}"
    ctl.validar(dataset, regla, "consistencia", int(malos.sum()), len(comp), pasa=not malos.any(),
                detalle=f"{descripcion}; tolerancia {txt_tol}; dif. máx {comp.dif.abs().max():.4f}" if len(comp) else descripcion,
                accion="revisar" if malos.any() else "")
    return comp.reset_index()
