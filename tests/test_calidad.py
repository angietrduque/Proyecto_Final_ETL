"""Pruebas de las reglas de calidad y verificaciones de integridad sobre la capa Gold generada.

Las pruebas de integración (marcadas con `gold`) se omiten si el pipeline aún no se ha ejecutado.
"""
import pandas as pd
import pytest

from src.utils.config import RAIZ
from src.utils.control import Control
from src.validation import reglas

GOLD = RAIZ / "data" / "gold"


def _registro(**k):
    base = {"anio": 2020, "cod_territorio": "00", "cod_sexo": "T", "cod_edad": "TOTAL", "cod_indicador": "TFR", "valor": 0.8}
    base.update(k)
    return base


def test_reglas_de_aceptacion_rechazan_y_trazan():
    df = pd.DataFrame([
        _registro(),                                        # válido
        _registro(),                                        # duplicado de clave
        _registro(anio=2021, valor=12.0),                   # TFR fuera de rango [0, 8]
        _registro(anio=2022, cod_territorio="__RECHAZO__"),  # territorio inexistente
        _registro(anio=1800),                               # año inválido
    ])
    ctl = Control()
    ok = reglas.aceptar(df, "prueba", ctl)
    assert len(ok) == 1
    motivos = {r["regla"] for r in ctl.rechazos}
    assert motivos == {"duplicado_clave", "rango_valido", "integridad_cod_territorio", "fecha_valida"}
    assert len(ctl.rechazos) == 4                           # cada rechazo queda trazado con su registro


def test_igualdad_con_tolerancia_por_redondeo():
    ctl = Control()
    pub = pd.Series([64.7, 50.0])
    rec = pd.Series([64.74, 50.5])
    tol = pd.Series([0.1, 0.1])
    out = reglas.igualdad(pub, rec, "x", ctl, "tasa", tol, "prueba")
    assert ctl.validaciones[-1]["afectados"] == 1
    assert out.dif.abs().max() == pytest.approx(0.5)


def test_a_numero_trata_marcadores_de_faltante():
    s = reglas.a_numero(pd.Series(["1,234", "-", "", "x", "0.5"]))
    assert s.tolist()[0] == 1234 and s.isna().sum() == 3


# ---------------------------------------------------------------------------- integración sobre Gold
gold = pytest.mark.skipif(not (GOLD / "fact_indicador_historico.parquet").exists(), reason="pipeline no ejecutado")


@gold
def test_gold_claves_primarias_unicas():
    from src.load.sql import PK
    for tabla, pk in PK.items():
        p = GOLD / f"{tabla}.parquet"
        if p.exists():
            df = pd.read_parquet(p)
            assert not df.duplicated(subset=pk).any(), tabla


@gold
def test_gold_integridad_referencial():
    h = pd.read_parquet(GOLD / "fact_indicador_historico.parquet")
    p = pd.read_parquet(GOLD / "fact_indicador_proyeccion.parquet")
    for col, dim in (("cod_territorio", "dim_territorio"), ("cod_edad", "dim_edad"), ("cod_indicador", "dim_indicador")):
        validos = set(pd.read_parquet(GOLD / f"{dim}.parquet")[col])
        assert set(h[col]) <= validos and set(p[col]) <= validos, col
    assert set(p.cod_escenario) <= set(pd.read_parquet(GOLD / "dim_escenario.parquet").cod_escenario)


@gold
def test_gold_separa_observado_de_proyectado():
    """Retroalimentación del profesor: el histórico no contiene proyecciones y la proyección no contiene historia."""
    h = pd.read_parquet(GOLD / "fact_indicador_historico.parquet")
    p = pd.read_parquet(GOLD / "fact_indicador_proyeccion.parquet")
    assert "proyeccion_oficial" not in set(h.tipo_dato)
    assert h[h.cod_indicador == "POBLACION"].anio.max() <= 2022
    assert p.anio.min() >= 2023
    assert set(p.tipo_dato) <= {"proyeccion_oficial", "calculado"}
    f = pd.read_parquet(GOLD / "fact_fuerza_laboral_escenario.parquet")
    assert set(f.tipo_dato) == {"escenario_propio"}


@gold
def test_gold_resultados_clave_cumplen():
    o = pd.read_parquet(GOLD / "kpi_okr.parquet")
    assert set(o.objetivo_cod) == {"O1", "O2", "O3", "O4"}
    assert o.cumple.all(), o[~o.cumple.astype(bool)][["kr", "valor", "meta"]].to_string()


@gold
def test_gold_kpis_de_negocio_con_valor_y_semaforo():
    k = pd.read_parquet(GOLD / "kpi_indicadores.parquet")
    assert k.codigo.is_unique and len(k) >= 12
    assert k.valor.notna().all()
    assert set(k.semaforo) <= {"Crítico", "Alerta", "Normal", "Contexto"}
