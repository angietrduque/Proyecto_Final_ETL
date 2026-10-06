"""Lectores de los formatos en que KOSIS entrega sus tablas.

Cada lector devuelve (tabla, metadata):
  tabla     DataFrame con TODAS las celdas como texto y los encabezados originales (sin interpretar nada).
            En tablas con encabezado doble (fila 1 = periodo, fila 2 = ítem) la columna se llama "periodo | ítem".
  metadata  dict con lo que el propio archivo declara (Table ID, fecha de descarga, periodo, fuente, unidad).

Formatos encontrados en las descargas del proyecto:
  csv_ancho      CSV con 1 fila de encabezado y años como columnas (UTF-8 con BOM o CP949)
  csv_doble      CSV con 2 filas de encabezado (periodo / ítem)
  xlsx_kosis     XLSX/XLS con hoja "Data" (1 o 2 filas de encabezado) y hoja "Meta Data"
  xml2003_kosis  ".xls" que en realidad es XML Spreadsheet 2003 en EUC-KR; su XML no es válido
                 (contiene "< Statistics metadata >" sin escapar), por eso se lee con expresiones regulares.
"""
import html
import re
from pathlib import Path

import pandas as pd


def _unicos(nombres: list[str]) -> list[str]:
    vistos, out = {}, []
    for i, n in enumerate(nombres):
        n = (n or "").strip() or f"_columna_{i}"
        vistos[n] = vistos.get(n, 0) + 1
        out.append(n if vistos[n] == 1 else f"{n} #{vistos[n]}")
    return out


def _combinar_encabezados(fila_periodo: list, fila_item: list, n_dims: int) -> list[str]:
    nombres = []
    for j, (a, b) in enumerate(zip(fila_periodo, fila_item)):
        a, b = str(a or "").strip(), str(b or "").strip()
        nombres.append(a if (j < n_dims or not b or a == b) else f"{a} | {b}")
    return _unicos(nombres)


def _desde_matriz(raw: pd.DataFrame, n_dims: int) -> pd.DataFrame:
    """Matriz cruda (sin encabezado) -> tabla con encabezado simple o doble según su estructura."""
    raw = raw.fillna("").astype(str)
    doble = raw.shape[0] > 1 and raw.iloc[1, 0].strip() == raw.iloc[0, 0].strip() and raw.iloc[0, 0].strip() != ""
    if doble:
        cols = _combinar_encabezados(raw.iloc[0].tolist(), raw.iloc[1].tolist(), n_dims)
        cuerpo = raw.iloc[2:]
    else:
        cols = _unicos(raw.iloc[0].tolist())
        cuerpo = raw.iloc[1:]
    tabla = pd.DataFrame(cuerpo.values, columns=cols).reset_index(drop=True)
    return tabla


def leer_csv(path: Path, encoding: str, n_dims: int) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(path, encoding=encoding, header=None, dtype=str, keep_default_na=False)
    return _desde_matriz(raw, n_dims), {}


def leer_xlsx(path: Path, n_dims: int) -> tuple[pd.DataFrame, dict]:
    hojas = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
    datos = hojas.get("Data", next(iter(hojas.values())))
    tabla = _desde_matriz(datos, n_dims)
    meta = {}
    if "Meta Data" in hojas:
        for k, v in hojas["Meta Data"].fillna("").values.tolist():
            k = str(k).replace("○", "").strip()
            if k:
                meta[k] = str(v).strip()
    return tabla, meta


def leer_xml2003(path: Path) -> tuple[pd.DataFrame, dict]:
    texto = path.read_bytes().decode("euc-kr", errors="replace")
    hojas = dict(re.findall(r'<Worksheet ss:Name="([^"]+)">(.*?)</Worksheet>', texto, flags=re.S))

    def filas(cuerpo: str) -> list[list[str]]:
        return [[html.unescape(c).strip() for c in re.findall(r"<Data[^>]*>(.*?)</Data>", r, flags=re.S)]
                for r in re.findall(r"<Row[^>]*>(.*?)</Row>", cuerpo, flags=re.S)]

    data = filas(hojas["Data"])
    titulo, encabezado, cuerpo = data[0], data[1], data[2:]
    ancho = len(encabezado)
    cuerpo = [f + [""] * (ancho - len(f)) for f in cuerpo]
    tabla = pd.DataFrame(cuerpo, columns=_unicos(encabezado))
    meta = {"titulo": titulo[0] if titulo else ""}
    for f in filas(hojas.get("Meta Data", "")):
        if len(f) == 2 and f[0].startswith("○"):
            meta.setdefault(f[0].replace("○", "").strip(), f[1])
    return tabla, meta


def leer(path: Path, spec: dict) -> tuple[pd.DataFrame, dict]:
    n_dims = len(spec.get("dimensiones", []))
    lector = spec["lector"]
    if lector in ("csv_ancho", "csv_doble"):
        return leer_csv(path, spec.get("encoding", "utf-8-sig"), n_dims)
    if lector == "xlsx_kosis":
        return leer_xlsx(path, n_dims)
    if lector == "xml2003_kosis":
        return leer_xml2003(path)
    raise ValueError(f"lector '{lector}' no soportado")


def fecha_descarga(path: Path, meta: dict, spec: dict) -> str:
    """Fecha de extracción = fecha de descarga manual. Prioridad: metadata del archivo > sello en el nombre > catálogo."""
    for clave in ("Download Date", "Source"):
        m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", meta.get(clave, ""))
        if m:
            return "-".join(m.groups())
    m = re.search(r"_(\d{4})(\d{2})(\d{2})\d{6}", path.name)
    if m:
        return "-".join(m.groups())
    if spec.get("fecha_descarga"):
        return spec["fecha_descarga"]
    return pd.Timestamp(path.stat().st_mtime, unit="s").strftime("%Y-%m-%d")
