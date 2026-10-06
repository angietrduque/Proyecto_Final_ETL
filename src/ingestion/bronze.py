"""Capa BRONZE: ingesta con tratamiento mínimo.

Por cada dataset del catálogo (config.yaml):
  1. Obtiene el crudo: KOSIS desde data/landing/kosis (descarga manual); WB/OECD/UN WPP por API.
  2. Guarda una copia INMUTABLE del crudo en data/bronze/<fuente>/<fecha_extraccion>/<archivo original>.
     Nunca sobrescribe: si el contenido es idéntico al ya guardado, lo reutiliza (idempotencia).
  3. Guarda una instantánea tabular (todas las columnas como TEXTO, encabezados originales) en <dataset>.parquet.
     Es el único "tratamiento": volver la tabla legible por máquina, sin limpiar ni tipar nada.
  4. Escribe <dataset>_metadata.json: fuente, tabla, URL, fecha de extracción, versión (sha256), filas, columnas,
     metadata declarada por el propio archivo y rol de la fuente.
  5. Registra el resultado en ctl.log_cargas y en data/bronze/_manifest.csv (versión vigente de cada dataset).

Archivos duplicados (p. ej. la misma tabla descargada en .xls y .xlsx) se detectan por el hash del CONTENIDO tabular
y se registran como 'duplicado' sin ingerirse dos veces.
"""
import fnmatch
import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.ingestion import apis, lectores_kosis
from src.utils.config import cargar_config, relativa, ruta
from src.utils.control import Control, ahora

log = logging.getLogger("bronze")
MANIFEST = "_manifest.csv"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def hash_tabla(df: pd.DataFrame) -> str:
    return sha256_bytes(pd.util.hash_pandas_object(df.reset_index(drop=True), index=False).values.tobytes()
                        + "|".join(df.columns).encode("utf-8"))


def _guardar(fuente: str, fecha: str, dataset: str, nombre: str, contenido: bytes, tabla: pd.DataFrame,
             meta: dict) -> tuple[Path, Path]:
    carpeta = ruta("bronze") / fuente / fecha
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    if destino.exists() and sha256_bytes(destino.read_bytes()) != sha256_bytes(contenido):
        destino = carpeta / f"{Path(nombre).stem}_{datetime.now():%H%M%S}{Path(nombre).suffix}"
    if not destino.exists():
        destino.write_bytes(contenido)
    pq = carpeta / f"{dataset}.parquet"
    tabla.astype("string").to_parquet(pq, index=False)
    (carpeta / f"{dataset}_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str),
                                                      encoding="utf-8", newline="\n")
    return destino, pq


def _metadata(fuente, dataset, spec, archivo, fecha, sha, tabla, meta_archivo, params, metodo) -> dict:
    return {"fuente": fuente, "dataset": dataset, "tabla_fuente": spec.get("tabla_kosis") or spec.get("dataflow") or dataset,
            "tbl_id": spec.get("tbl_id"), "rol": spec.get("rol"), "uso": spec.get("uso"), "metodo": metodo,
            "params": params, "fecha_extraccion": fecha, "fecha_ingesta": ahora(), "archivo_crudo": archivo,
            "sha256_crudo": sha, "version": sha[:12], "filas": int(len(tabla)), "columnas": int(tabla.shape[1]),
            "encabezados": list(tabla.columns[:12]) + (["..."] if tabla.shape[1] > 12 else []),
            "metadata_declarada_por_archivo": meta_archivo}


# ------------------------------------------------------------------------------------------------ KOSIS
def ingerir_kosis(ctl: Control, solo: list[str] | None = None) -> list[dict]:
    cfg = cargar_config()
    landing = ruta("landing") / "kosis"
    archivos = sorted(p for p in landing.iterdir() if p.is_file())
    filas_manifest = []
    for dataset, spec in cfg["kosis"]["datasets"].items():
        if solo and dataset not in solo:
            continue
        candidatos = [p for p in archivos if any(fnmatch.fnmatch(p.name, pat) for pat in spec["patron"])]
        if not candidatos:
            ctl.registrar_carga("bronze", "KOSIS", dataset, "fallo", mensaje=f"sin archivos {spec['patron']} en landing",
                                metodo="descarga_manual")
            log.error("[KOSIS] %s: no hay archivo en %s", dataset, relativa(landing))
            continue
        vistos = {}
        for p in candidatos:
            inicio = ahora()
            try:
                tabla, meta = lectores_kosis.leer(p, spec)
                h = hash_tabla(tabla)
                fecha = lectores_kosis.fecha_descarga(p, meta, spec)
                contenido = p.read_bytes()
                if h in vistos:
                    ctl.registrar_carga("bronze", "KOSIS", dataset, "duplicado", filas=len(tabla), archivo=p.name,
                                        hash_archivo=sha256_bytes(contenido), metodo="descarga_manual", inicio=inicio,
                                        mensaje=f"contenido idéntico a {vistos[h]}: no se ingiere dos veces")
                    log.info("[KOSIS] %-22s %s -> duplicado de %s", dataset, p.name, vistos[h])
                    continue
                vistos[h] = p.name
                url = cfg["kosis"]["url_tabla"].format(**spec) if spec.get("tbl_id") else cfg["kosis"]["url_portal"]
                sha = sha256_bytes(contenido)
                meta_json = _metadata("KOSIS", dataset, spec, p.name, fecha, sha, tabla, meta,
                                      {"url": url, "archivo": p.name, "lector": spec["lector"]}, "descarga_manual")
                destino, pq = _guardar("kosis", fecha, dataset, p.name, contenido, tabla, meta_json)
                ctl.registrar_carga("bronze", "KOSIS", dataset, "exito", filas=len(tabla), archivo=relativa(destino),
                                    hash_archivo=sha, metodo="descarga_manual", inicio=inicio)
                filas_manifest.append({"fuente": "KOSIS", "dataset": dataset, "fecha_extraccion": fecha,
                                       "archivo_crudo": relativa(destino), "parquet": relativa(pq),
                                       "sha256": sha, "filas": len(tabla), "columnas": tabla.shape[1],
                                       "rol": spec.get("rol"), "tbl_id": spec.get("tbl_id"), "url": url})
                log.info("[KOSIS] %-22s %s -> %d filas x %d cols (%s)", dataset, p.name, len(tabla), tabla.shape[1], fecha)
            except Exception as e:  # un archivo defectuoso no detiene el resto
                ctl.registrar_carga("bronze", "KOSIS", dataset, "fallo", archivo=p.name, metodo="descarga_manual",
                                    mensaje=f"{type(e).__name__}: {e}", inicio=inicio)
                log.exception("[KOSIS] %s: fallo leyendo %s", dataset, p.name)
    return filas_manifest


# ------------------------------------------------------------------------------------------------ APIs
def _ingerir_api(ctl: Control, fuente: str, carpeta: str, nombre: str, spec: dict, funcion, cfg) -> dict | None:
    inicio = ahora()
    try:
        contenido, archivo, tabla, params = funcion(nombre, cfg)
        fecha = datetime.now().strftime("%Y-%m-%d")
        sha = sha256_bytes(contenido)
        meta = _metadata(fuente, nombre, spec, archivo, fecha, sha, tabla, {}, params, "api")
        destino, pq = _guardar(carpeta, fecha, nombre, archivo, contenido, tabla, meta)
        ctl.registrar_carga("bronze", fuente, nombre, "exito", filas=len(tabla), archivo=relativa(destino),
                            hash_archivo=sha, metodo="api", inicio=inicio)
        log.info("[%s] %-22s -> %d filas", fuente, nombre, len(tabla))
        return {"fuente": fuente, "dataset": nombre, "fecha_extraccion": fecha, "archivo_crudo": relativa(destino),
                "parquet": relativa(pq), "sha256": sha, "filas": len(tabla), "columnas": tabla.shape[1],
                "rol": spec.get("rol"), "tbl_id": None, "url": params.get("url")}
    except apis.SinCredencial as e:
        ctl.registrar_carga("bronze", fuente, nombre, "omitido", metodo="api", mensaje=str(e), inicio=inicio)
        log.warning("[%s] %s omitido: %s", fuente, nombre, e)
    except Exception as e:
        ctl.registrar_carga("bronze", fuente, nombre, "fallo", metodo="api", mensaje=f"{type(e).__name__}: {e}", inicio=inicio)
        log.error("[%s] %s fallo: %s (se usará la última versión en bronze si existe)", fuente, nombre, e)
    return None


def ingerir_apis(ctl: Control, fuentes: list[str]) -> list[dict]:
    cfg = cargar_config()
    out = []
    if "worldbank" in fuentes:
        for codigo, spec in cfg["worldbank"]["datasets"].items():
            out.append(_ingerir_api(ctl, "WB", "worldbank", codigo, spec, apis.worldbank, cfg))
    if "oecd" in fuentes:
        for nombre, spec in cfg["oecd"]["datasets"].items():
            out.append(_ingerir_api(ctl, "OECD", "oecd", nombre, spec, apis.oecd, cfg))
    if "unwpp" in fuentes:
        for nombre, spec in cfg["unwpp"]["datasets"].items():
            out.append(_ingerir_api(ctl, "UNWPP", "unwpp", nombre, spec, apis.unwpp, cfg))
    return [x for x in out if x]


# ------------------------------------------------------------------------------------------------ manifest
def actualizar_manifest(nuevas: list[dict]) -> pd.DataFrame:
    """Manifest = todas las versiones ingeridas; la vigente de cada dataset es la de fecha más reciente."""
    p = ruta("bronze") / MANIFEST
    previo = pd.read_csv(p, dtype=str) if p.exists() else pd.DataFrame()
    todo = pd.concat([previo, pd.DataFrame(nuevas).astype(str)], ignore_index=True)
    if not todo.empty:
        todo = todo.drop_duplicates(subset=["fuente", "dataset", "sha256"], keep="last")
        todo = todo.sort_values(["fuente", "dataset", "fecha_extraccion"])
        todo["vigente"] = ~todo.duplicated(subset=["fuente", "dataset"], keep="last")
        todo.to_csv(p, index=False)
    return todo


def ejecutar(ctl: Control, fuentes: list[str] | None = None, usar_api: bool = True) -> pd.DataFrame:
    fuentes = fuentes or ["kosis", "worldbank", "oecd", "unwpp"]
    nuevas = []
    if "kosis" in fuentes:
        nuevas += ingerir_kosis(ctl)
    api = [f for f in fuentes if f != "kosis"]
    if api and usar_api:
        nuevas += ingerir_apis(ctl, api)
    elif api:
        for f in api:
            ctl.registrar_carga("bronze", f.upper(), "*", "omitido", metodo="api", mensaje="ejecución con --sin-api")
    return actualizar_manifest(nuevas)


def leer_vigente(fuente: str, dataset: str) -> tuple[pd.DataFrame, dict]:
    """Instantánea tabular vigente de un dataset de bronze + su metadata (lo consume Silver)."""
    man = pd.read_csv(ruta("bronze") / MANIFEST, dtype=str)
    fila = man[(man.fuente == fuente) & (man.dataset == dataset) & (man.vigente == "True")]
    if fila.empty:
        raise FileNotFoundError(f"No hay versión vigente de {fuente}/{dataset} en bronze. Ejecutar: python main.py --capa bronze")
    from src.utils.config import RAIZ
    pq = RAIZ / fila.iloc[0]["parquet"]
    meta = json.loads(pq.with_name(f"{dataset}_metadata.json").read_text(encoding="utf-8"))
    return pd.read_parquet(pq), meta


def existe_vigente(fuente: str, dataset: str) -> bool:
    p = ruta("bronze") / MANIFEST
    if not p.exists():
        return False
    man = pd.read_csv(p, dtype=str)
    return not man[(man.fuente == fuente) & (man.dataset == dataset) & (man.vigente == "True")].empty
