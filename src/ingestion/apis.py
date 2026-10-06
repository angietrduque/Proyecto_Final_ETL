"""Extractores de fuentes con API pública: World Bank (WDI v2), OECD (SDMX REST) y UN WPP (Data Portal, con token).

Cada extractor devuelve (contenido_crudo_bytes, nombre_archivo, tabla_texto, params) para que la capa Bronze
guarde el crudo tal como llegó y una instantánea tabular con todas las columnas como texto.
"""
import io
import json
import logging
import os
import time

import pandas as pd
import requests

log = logging.getLogger("ingestion.apis")


def http_get(url: str, cfg: dict, params: dict | None = None, headers: dict | None = None) -> requests.Response:
    """GET con reintentos ante errores de red, 429 y 5xx. Otros 4xx fallan de inmediato."""
    ex = cfg["extraccion"]
    headers = {"User-Agent": ex["user_agent"], **(headers or {})}
    for intento in range(1, ex["reintentos"] + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=ex["timeout_s"])
            if r.status_code < 400:
                return r
            if r.status_code != 429 and r.status_code < 500:
                r.raise_for_status()
            motivo = f"HTTP {r.status_code}"
        except requests.HTTPError:
            raise
        except requests.RequestException as e:
            motivo = type(e).__name__
        if intento == ex["reintentos"]:
            raise RuntimeError(f"{motivo} tras {intento} intentos: {url}")
        log.warning("  %s (intento %d/%d), reintentando en %ss", motivo, intento, ex["reintentos"], ex["espera_reintento_s"])
        time.sleep(ex["espera_reintento_s"])


# ---------------------------------------------------------------------------------------------- World Bank
def worldbank(codigo: str, cfg: dict):
    wb, per = cfg["worldbank"], cfg["periodo"]["historico"]
    url = f"{wb['base_url']}/country/{';'.join(wb['paises'])}/indicator/{codigo}"
    params = {"format": "json", "date": f"{per['inicio']}:{per['fin']}", "per_page": wb["per_page"]}
    meta, datos, pagina = None, [], 1
    while True:
        cuerpo = http_get(url, cfg, {**params, "page": pagina}).json()
        if len(cuerpo) < 2:
            raise ValueError(f"World Bank rechazó la consulta: {cuerpo[0]}")
        meta = meta or cuerpo[0]
        datos += cuerpo[1] or []
        if pagina >= cuerpo[0]["pages"]:
            break
        pagina += 1
    contenido = json.dumps([meta, datos], ensure_ascii=False).encode("utf-8")
    tabla = pd.DataFrame([{"indicator_id": d["indicator"]["id"], "indicator": d["indicator"]["value"],
                           "countryiso3code": d["countryiso3code"], "country": d["country"]["value"],
                           "date": d["date"], "value": d["value"], "obs_status": d.get("obs_status"),
                           "lastupdated": meta.get("lastupdated")} for d in datos]).astype("string")
    return contenido, f"{codigo}.json", tabla, {"url": url, **params}


# ---------------------------------------------------------------------------------------------- OECD
def oecd(nombre: str, cfg: dict):
    oe = cfg["oecd"]
    ds = oe["datasets"][nombre]
    clave = ds["clave"].format(paises="+".join(oe["paises"]))
    url = f"{oe['base_url']}/data/{ds['dataflow']}/{clave}"
    params = {"startPeriod": cfg["periodo"]["historico"]["inicio"], "format": oe["formato"]}
    r = http_get(url, cfg, params)
    tabla = pd.read_csv(io.BytesIO(r.content), dtype=str, keep_default_na=False)
    return r.content, f"{nombre}.csv", tabla, {"url": url, **params, "dataflow": ds["dataflow"], "clave": clave}


# ---------------------------------------------------------------------------------------------- UN WPP
class SinCredencial(Exception):
    """La fuente es opcional y no hay token configurado: la extracción se omite (no es un fallo técnico)."""


def unwpp(nombre: str, cfg: dict):
    un = cfg["unwpp"]
    ds = un["datasets"][nombre]
    token = os.getenv(un["token_env"])
    if not token:
        raise SinCredencial(f"{un['token_env']} no está definido en .env (token gratuito en "
                            "https://population.un.org/dataportalapi/token/index.html)")
    url = (f"{un['base_url']}/data/indicators/{ds['indicator_id']}/locations/{ds['location_code']}"
           f"/start/{ds['inicio']}/end/{ds['fin']}")
    params = {"format": "json", "pageSize": 1000}
    filas, pagina, paginas = [], 1, None
    while paginas is None or pagina <= paginas:
        cuerpo = http_get(url, cfg, {**params, "pageNumber": pagina}, headers={"Authorization": f"Bearer {token}"}).json()
        filas += cuerpo["data"]
        paginas = cuerpo.get("pages", 1)
        pagina += 1
    contenido = json.dumps(filas, ensure_ascii=False).encode("utf-8")
    return contenido, f"{nombre}.json", pd.DataFrame(filas).astype("string"), {"url": url, **params}
