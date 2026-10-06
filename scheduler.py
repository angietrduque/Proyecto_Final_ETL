"""Orquestador periódico del pipeline con la librería `schedule` (requisito del laboratorio, parte 8).

La frecuencia se configura en config/config.yaml -> orquestacion. KOSIS se actualiza por descarga manual: el
programador re-ejecuta todo el pipeline, que ingiere lo que haya nuevo en data/landing/kosis y vuelve a consultar
las APIs de World Bank y OECD. Bronze no duplica versiones idénticas (sha256), así que re-ejecutar es seguro.

Uso:
    python scheduler.py            # deja el proceso corriendo y ejecuta según la configuración
    python scheduler.py --ahora    # ejecuta una vez inmediatamente y luego sigue según la configuración
"""
import logging
import subprocess
import sys
import time

import schedule

from src.utils.config import RAIZ, cargar_config
from src.utils.logs import configurar_logging


def correr_pipeline() -> None:
    log = logging.getLogger("scheduler")
    log.info("Ejecución programada del pipeline")
    r = subprocess.run([sys.executable, str(RAIZ / "main.py")], cwd=RAIZ)
    log.info("Pipeline terminó con código %s", r.returncode)


def programar() -> None:
    o = cargar_config()["orquestacion"]
    if o["frecuencia"] == "diaria":
        schedule.every().day.at(o["hora"]).do(correr_pipeline)
    elif o["frecuencia"] == "semanal":
        getattr(schedule.every(), o["dia"]).at(o["hora"]).do(correr_pipeline)
    elif o["frecuencia"] == "mensual":  # schedule no tiene meses: se revisa a diario y se ejecuta el día 1
        schedule.every().day.at(o["hora"]).do(lambda: time.localtime().tm_mday == 1 and correr_pipeline())
    else:
        raise ValueError(f"frecuencia no soportada: {o['frecuencia']}")


if __name__ == "__main__":
    configurar_logging()
    programar()
    if "--ahora" in sys.argv:
        correr_pipeline()
    logging.getLogger("scheduler").info("Programador activo: %s", schedule.get_jobs())
    while True:
        schedule.run_pending()
        time.sleep(30)
