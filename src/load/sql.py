"""Carga en base de datos SQL (SQLAlchemy): SQLite por defecto, PostgreSQL si se define DB_URL en .env.

Estructura:
  * PostgreSQL: un esquema por capa (ctl, bronze, silver, gold).
  * SQLite (no tiene esquemas): prefijo por capa (ctl_*, bronze_*, silver_*, gold_*).
Cada tabla Gold se crea con su CLAVE PRIMARIA y CLAVES FORÁNEAS hacia las dimensiones antes de insertar los datos
(la estructura queda declarada en la base, no sólo en la documentación). La carga es idempotente: cada ejecución
reemplaza el contenido de las tablas (las versiones anteriores quedan en Bronze y en ctl).
"""
import json
import logging
import os

import pandas as pd
import sqlalchemy as sa

from src.utils.config import RAIZ, cargar_config

log = logging.getLogger("load")

PK = {
    "dim_tiempo": ["anio"], "dim_territorio": ["cod_territorio"], "dim_sexo": ["cod_sexo"], "dim_edad": ["cod_edad"],
    "dim_indicador": ["cod_indicador"], "dim_escenario": ["cod_escenario"], "dim_supuesto": ["cod_supuesto"],
    "dim_tipo_dato": ["tipo_dato"], "dim_fuente": ["fuente", "dataset"],
    "fact_indicador_historico": ["anio", "cod_territorio", "cod_sexo", "cod_edad", "cod_indicador"],
    "fact_indicador_proyeccion": ["anio", "cod_territorio", "cod_sexo", "cod_edad", "cod_indicador", "cod_escenario",
                                  "edicion_proyeccion"],
    "fact_fuerza_laboral_escenario": ["anio", "cod_escenario", "cod_supuesto", "cod_sexo", "cod_edad"],
    "fact_riesgo_regional": ["cod_territorio"],
    "fact_riesgo_sensibilidad": ["esquema", "cod_territorio"],
    "fact_escenarios_sensibilidad": ["cod_supuesto", "variante"],
    "fact_comparacion_internacional": ["anio", "cod_territorio", "cod_sexo", "cod_edad", "cod_indicador", "fuente"],
    "dataset_nacional_anual": ["anio", "cod_territorio"], "dataset_regional_anual": ["anio", "cod_territorio"],
    "kpi_okr": ["kr"], "kpi_indicadores": ["codigo"], "kpi_calidad_dataset": ["dataset"],
}
FK = {"anio": ("dim_tiempo", "anio"), "cod_territorio": ("dim_territorio", "cod_territorio"),
      "cod_sexo": ("dim_sexo", "cod_sexo"), "cod_edad": ("dim_edad", "cod_edad"),
      "cod_indicador": ("dim_indicador", "cod_indicador"), "cod_escenario": ("dim_escenario", "cod_escenario"),
      "cod_supuesto": ("dim_supuesto", "cod_supuesto"), "tipo_dato": ("dim_tipo_dato", "tipo_dato")}


def motor() -> tuple[sa.Engine, str]:
    cargar_config()
    url = os.getenv("DB_URL")
    if url:
        return sa.create_engine(url), "postgresql" if url.startswith("postgres") else url.split(":")[0]
    ruta = RAIZ / cargar_config()["base_datos"]["sqlite_path"]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    eng = sa.create_engine(f"sqlite:///{ruta.as_posix()}")

    @sa.event.listens_for(eng, "connect")
    def _fk(dbapi_con, _):  # SQLite sólo valida claves foráneas si se activa por conexión
        dbapi_con.execute("PRAGMA foreign_keys=ON")
    return eng, "sqlite"


def _tipo(serie: pd.Series):
    if pd.api.types.is_bool_dtype(serie):
        return sa.Boolean
    if pd.api.types.is_integer_dtype(serie):
        return sa.BigInteger
    if pd.api.types.is_float_dtype(serie):
        return sa.Float
    return sa.Text


def _nombre(capa: str, tabla: str, dialecto: str) -> tuple[str, str | None]:
    return (f"{capa}_{tabla}", None) if dialecto == "sqlite" else (tabla, capa)


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in df.columns:
        if isinstance(df[c].dtype, pd.CategoricalDtype):
            df[c] = df[c].astype(str)
        if df[c].dtype == object and df[c].map(lambda x: isinstance(x, (list, dict))).any():
            df[c] = df[c].map(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x)
    return df


def cargar(tablas: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """tablas = {capa: {nombre: DataFrame}}. Devuelve un resumen de la carga (filas por tabla)."""
    eng, dialecto = motor()
    resumen = []
    with eng.begin() as con:
        if dialecto == "postgresql":
            for capa in tablas:
                con.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {capa}"))
    meta = sa.MetaData()
    orden = []
    for capa, grupo in tablas.items():
        # primero dimensiones, después hechos (por las claves foráneas)
        for nombre in sorted(grupo, key=lambda n: (not n.startswith("dim_"), n)):
            df = _preparar(grupo[nombre])
            tnombre, esquema = _nombre(capa, nombre, dialecto)
            pk = PK.get(nombre, []) if capa == "gold" else []
            cols = []
            for c in df.columns:
                fk = []
                if capa == "gold" and not nombre.startswith("dim_") and c in FK and nombre in PK:
                    ref_t, ref_c = FK[c]
                    rt, rs = _nombre("gold", ref_t, dialecto)
                    fk = [sa.ForeignKey(f"{rs + '.' if rs else ''}{rt}.{ref_c}")]
                cols.append(sa.Column(c, _tipo(df[c]), *fk, primary_key=c in pk, nullable=c not in pk))
            orden.append((sa.Table(tnombre, meta, *cols, schema=esquema), df))
    with eng.begin() as con:
        for tabla, _ in reversed(orden):
            tabla.drop(con, checkfirst=True)
        for tabla, df in orden:
            tabla.create(con)
            if len(df):
                con.execute(tabla.insert(), df.astype(object).where(df.notna(), None).to_dict("records"))
            resumen.append({"tabla": f"{tabla.schema + '.' if tabla.schema else ''}{tabla.name}", "filas": len(df),
                            "clave_primaria": ", ".join(c.name for c in tabla.primary_key.columns)})
            log.info("[carga] %-45s %8d filas", resumen[-1]["tabla"], len(df))
    return pd.DataFrame(resumen)


def ddl(tablas: dict[str, dict[str, pd.DataFrame]], destino) -> None:
    """Escribe el DDL (CREATE TABLE con PK/FK) que genera la carga, para documentación (sql/*.sql)."""
    from sqlalchemy.schema import CreateTable
    for dialecto, nombre_archivo in (("sqlite", "ddl_sqlite.sql"), ("postgresql", "ddl_postgresql.sql")):
        meta = sa.MetaData()
        sentencias = [f"-- DDL generado automáticamente por src/load/sql.py ({dialecto})\n"]
        eng = sa.create_mock_engine(f"{dialecto}://", lambda *a, **k: None)
        for capa, grupo in tablas.items():
            if capa != "gold":
                continue
            for nombre in sorted(grupo, key=lambda n: (not n.startswith("dim_"), n)):
                df = _preparar(grupo[nombre])
                tnombre, esquema = _nombre(capa, nombre, dialecto)
                pk = PK.get(nombre, [])
                cols = []
                for c in df.columns:
                    fk = []
                    if not nombre.startswith("dim_") and c in FK and nombre in PK:
                        rt, rs = _nombre("gold", FK[c][0], dialecto)
                        fk = [sa.ForeignKey(f"{rs + '.' if rs else ''}{rt}.{FK[c][1]}")]
                    cols.append(sa.Column(c, _tipo(df[c]), *fk, primary_key=c in pk, nullable=c not in pk))
                t = sa.Table(tnombre, meta, *cols, schema=esquema)
                sentencias.append(str(CreateTable(t).compile(dialect=eng.dialect)).strip() + ";\n")
        (destino / nombre_archivo).write_text("\n".join(sentencias), encoding="utf-8")
