"""Tablas de control de una ejecución del pipeline (capa ctl).

Todo lo que el pipeline hace queda registrado aquí y se persiste en data/gold/ctl_*.parquet y en la base SQL:
  ctl.log_cargas  una fila por dataset y capa (estado, filas, archivo, hash, mensaje)
  ctl.conteos     filas antes/después de cada paso de transformación
  ctl.rechazos    registros rechazados con la regla y el motivo
  ctl.validaciones resultado de cada regla de calidad (pasa/falla, afectados, umbral)
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


def ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class Control:
    id_ejecucion: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6])
    cargas: list = field(default_factory=list)
    conteos: list = field(default_factory=list)
    rechazos: list = field(default_factory=list)
    validaciones: list = field(default_factory=list)

    # ------------------------------------------------------------------ log de cargas
    def registrar_carga(self, capa: str, fuente: str, dataset: str, estado: str, filas: int | None = None,
                        archivo: str | None = None, hash_archivo: str | None = None, mensaje: str = "",
                        metodo: str | None = None, inicio: str | None = None) -> None:
        self.cargas.append({"id_ejecucion": self.id_ejecucion, "id_carga": len(self.cargas) + 1, "capa": capa,
                            "fuente": fuente, "dataset": dataset, "metodo": metodo, "estado": estado,
                            "filas": filas, "archivo": archivo, "hash_archivo": hash_archivo,
                            "mensaje": mensaje, "inicio": inicio or ahora(), "fin": ahora()})

    # ------------------------------------------------------------------ conteos
    def contar(self, capa: str, dataset: str, paso: str, filas_entrada: int, filas_salida: int, nota: str = "") -> None:
        self.conteos.append({"id_ejecucion": self.id_ejecucion, "capa": capa, "dataset": dataset,
                             "orden": len(self.conteos) + 1, "paso": paso, "filas_entrada": int(filas_entrada),
                             "filas_salida": int(filas_salida), "diferencia": int(filas_salida) - int(filas_entrada),
                             "nota": nota})

    # ------------------------------------------------------------------ rechazos
    def rechazar(self, dataset: str, regla: str, motivo: str, registros: pd.DataFrame, max_guardar: int = 5000) -> None:
        """Registra cada fila rechazada (registro completo en JSON) con su regla y motivo."""
        if registros is None or registros.empty:
            return
        for rec in registros.head(max_guardar).to_dict("records"):
            self.rechazos.append({"id_ejecucion": self.id_ejecucion, "dataset": dataset, "regla": regla,
                                  "motivo": motivo, "registro": json.dumps(rec, ensure_ascii=False, default=str)})

    # ------------------------------------------------------------------ validaciones
    def validar(self, dataset: str, regla: str, tipo: str, afectados: int, evaluados: int, pasa: bool,
                detalle: str = "", accion: str = "") -> None:
        self.validaciones.append({"id_ejecucion": self.id_ejecucion, "dataset": dataset, "regla": regla,
                                  "tipo": tipo, "evaluados": int(evaluados), "afectados": int(afectados),
                                  "pct_afectados": round(afectados / evaluados * 100, 3) if evaluados else 0.0,
                                  "resultado": "PASA" if pasa else "FALLA", "detalle": detalle, "accion": accion})

    def tablas(self) -> dict[str, pd.DataFrame]:
        cols_r = ["id_ejecucion", "dataset", "regla", "motivo", "registro"]
        log = pd.DataFrame(self.cargas)
        if "filas" in log:
            log["filas"] = pd.to_numeric(log["filas"]).astype("Int64")
        return {"log_cargas": log, "conteos": pd.DataFrame(self.conteos),
                "rechazos": pd.DataFrame(self.rechazos, columns=cols_r),
                "validaciones": pd.DataFrame(self.validaciones)}
