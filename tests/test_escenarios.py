"""Pruebas de los escenarios propios de fuerza laboral, de la sensibilidad y de la reproducibilidad de Bronze.

Las de supuestos usan datos sintéticos (no dependen de una ejecución previa); las de Gold se omiten si aún no se ha
ejecutado el pipeline.
"""
from pathlib import Path

import pandas as pd
import pytest

from src.transformation import gold as g
from src.utils.config import RAIZ, cargar_config

GOLD = RAIZ / "data" / "gold"
gold = pytest.mark.skipif(not (GOLD / "fact_fuerza_laboral_escenario.parquet").exists(), reason="pipeline sin ejecutar")
GRUPOS = ["15-19", "20-29", "30-39", "40-49", "50-59", "60+"]


def _historico_sintetico():
    """Tasas de participación EAPS 2015-2025: hombres 70 %, mujeres 50 % (salvo 20-29, donde las mujeres participan más)."""
    filas = []
    for anio in range(2015, 2026):
        for edad in GRUPOS:
            th, tm = (60.0, 66.0) if edad == "20-29" else (70.0, 50.0 + (anio - 2015) * 0.5)
            for sexo, t in (("H", th), ("M", tm)):
                filas.append({"anio": anio, "cod_territorio": "00", "cod_sexo": sexo, "cod_edad": edad,
                              "cod_indicador": "TASA_PARTICIPACION", "valor": t})
    return pd.DataFrame(filas)


def _ocde_sintetico():
    filas = [{"anio": 2024, "cod_territorio": "OED", "cod_sexo": s, "cod_edad": e, "cod_indicador": "TASA_PARTICIPACION",
              "valor": v, "fuente": "OECD"}
             for s, e, v in (("H", "15-24", 52), ("H", "25-54", 91), ("H", "55-64", 76),
                             ("M", "15-24", 45), ("M", "25-54", 76), ("M", "55-64", 59))]
    return pd.DataFrame(filas)


def test_supuestos_generan_a_b_c_d():
    s = g.supuestos_participacion(_historico_sintetico(), [2025, 2050], _ocde_sintetico())
    assert set(s.cod_supuesto) == {"A_constante", "B_tendencia", "C_convergencia_ocde", "D_brecha_genero"}
    base = s[s.anio == 2025].pivot_table(index=["cod_sexo", "cod_edad"], columns="cod_supuesto", values="tasa_participacion")
    assert (base.max(axis=1) - base.min(axis=1)).abs().max() < 1e-9      # en el año base todos parten de la tasa observada


def test_supuesto_d_nunca_baja_una_tasa():
    s = g.supuestos_participacion(_historico_sintetico(), [2050], _ocde_sintetico())
    a = s[s.cod_supuesto == "A_constante"].set_index(["cod_sexo", "cod_edad"]).tasa_participacion
    d = s[s.cod_supuesto == "D_brecha_genero"].set_index(["cod_sexo", "cod_edad"]).tasa_participacion
    assert (d >= a - 1e-9).all()
    assert d[("M", "20-29")] == a[("M", "20-29")]                  # las mujeres ya participaban más: no cambia
    assert d[("M", "40-49")] == pytest.approx(50 + 5 + 0.5 * (70 - 55))  # cierra la mitad de la brecha a 2050


def test_supuesto_c_llega_al_objetivo_ocde_en_2050():
    s = g.supuestos_participacion(_historico_sintetico(), [2050], _ocde_sintetico())
    c = s[s.cod_supuesto == "C_convergencia_ocde"].set_index(["cod_sexo", "cod_edad"]).tasa_participacion
    assert c[("H", "30-39")] == pytest.approx(91)                   # 30-39 ≙ 25-54 de la OCDE
    assert c[("M", "20-29")] == pytest.approx(0.5 * 45 + 0.5 * 76)  # 20-29 ≙ mitad 15-24, mitad 25-54
    assert c[("H", "15-19")] == pytest.approx(70)                   # sin equivalencia OCDE: constante


@gold
def test_ajuste_de_cobertura_reproduce_la_pea_2025():
    f = pd.read_parquet(GOLD / "fact_fuerza_laboral_escenario.parquet")
    h = pd.read_parquet(GOLD / "fact_indicador_historico.parquet")
    pea = h[(h.cod_indicador == "POB_ACTIVA") & (h.cod_territorio == "00") & (h.cod_sexo == "T") & (h.cod_edad == "15+")
            & (h.anio == 2025)].valor.iloc[0]
    mod = f[(f.anio == 2025) & (f.cod_escenario == "medio") & (f.cod_supuesto == "A_constante")].fuerza_laboral_potencial.sum()
    assert abs(mod / pea - 1) < 0.005
    # el más bajo es hombres 20-29 (≈ 0,88): el servicio militar obligatorio queda fuera del universo de la EAPS
    assert f.factor_cobertura.between(0.85, 1.05).all()


@gold
def test_sensibilidad_publicada():
    e = pd.read_parquet(GOLD / "fact_escenarios_sensibilidad.parquet")
    assert e.es_base.sum() == 4 and (~e.es_base).sum() >= 6
    r = pd.read_parquet(GOLD / "fact_riesgo_sensibilidad.parquet")
    assert r.groupby("esquema").cod_territorio.nunique().eq(17).all()
    assert len(cargar_config()["riesgo_regional"]["esquemas_sensibilidad"]) == r.esquema.nunique()


def test_bronze_de_las_api_versionado_para_ejecutar_sin_api():
    """En un clon nuevo, `python main.py --sin-api` necesita la última versión de World Bank y OECD en Bronze."""
    man = pd.read_csv(RAIZ / "data" / "bronze" / "_manifest.csv")
    vig = man[man.vigente & man.fuente.isin(["WB", "OECD"])]
    assert len(vig) >= 10
    for archivo in vig.archivo_crudo:
        assert (RAIZ / archivo).exists(), archivo
    ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "data/bronze/worldbank/" not in ignorados.splitlines() and "data/bronze/oecd/" not in ignorados.splitlines()
