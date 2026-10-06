"""Pruebas de las transformaciones Silver/Gold con datos sintéticos de resultado conocido."""
import pandas as pd
import pytest

from src.transformation import derivados, homologacion as hom
from src.transformation.silver import _periodo, melt_kosis


@pytest.mark.parametrize("etiqueta,esperado", [
    ("2025", (2025, True, False)), ("2025 Year", (2025, True, False)), ("2022 년", (2022, True, False)),
    ("2025 p)", (2025, True, True)), ("2026.05 p)", (None, False, True)), ("2025.08", (None, False, False)),
])
def test_periodos(etiqueta, esperado):
    assert _periodo(etiqueta) == esperado


def test_melt_encabezado_doble():
    df = pd.DataFrame({"By province": ["Seoul"], "2000 | Births": ["100"], "2001 | Births": ["90"]})
    largo = melt_kosis(df, 1, ["territorio"])
    assert list(largo.periodo) == ["2000", "2001"]
    assert list(largo.item_col) == ["Births", "Births"]


def test_homologacion_territorios_y_cambios_de_nombre():
    s = pd.Series(["Gangwon-do", "Gangwon", "Gangwon-State", "sejong-si", "Jeollabuk-do", "Jeonbuk-State",
                   "Abroad", "Jeonnam-Gwangju", "Atlantis"])
    assert list(hom.territorio(s)) == ["32", "32", "32", "29", "35", "35", "__FUERA__", "__RECHAZO__", hom.NO_MAPEADO]


def test_homologacion_edades_colapsa_85_y_excluye_80mas():
    cod, acc = hom.edad(pd.Series(["35 - 39세", "85-89 year old", "100세 이상", "80 Years old & over"]), "x")
    assert list(cod) == ["35-39", "85+", "85+", "__AGREGADO__"]
    assert list(acc) == ["usar", "colapsar", "colapsar", "excluir"]


def test_homologacion_edades_eaps_total_es_15mas():
    cod, _ = hom.edad(pd.Series(["Total", "50-59 Yeras old"]), "eaps_sexo_edad")
    assert list(cod) == ["15+", "50-59"]


def test_escenarios_kostat():
    e = hom.escenario(pd.Series(["국제 무이동추계(출산율-중위 / 기대수명-중위 / 국제순이동-무이동)",
                                 "기타 추계(출산율-고위 / 기대수명-저위 / 국제순이동-중위)"]))
    assert e.cod_escenario.tolist() == ["migracion_cero", "otro_Falta_Ebaja_Mmedia"]
    assert e.supuesto_migracion.tolist() == ["cero", "media"]


def _poblacion(valores: dict) -> pd.DataFrame:
    return pd.DataFrame([{"anio": 2020, "cod_territorio": "00", "cod_sexo": "T", "cod_edad": k, "valor": v}
                         for k, v in valores.items()])


def test_indicadores_de_estructura_con_resultado_conocido():
    # 0-14 = 30, 15-64 = 100, 65+ = 50 (80+ = 20), total = 180
    v = {e: 0.0 for e in derivados.QUINQUENALES}
    v.update({"0-4": 10, "5-9": 10, "10-14": 10, "15-19": 10, "20-24": 10, "25-29": 10, "30-34": 10, "35-39": 10,
              "40-44": 10, "45-49": 10, "50-54": 10, "55-59": 10, "60-64": 10, "65-69": 20, "70-74": 10, "80-84": 15, "85+": 5})
    ind = derivados.indicadores_estructura(_poblacion(v), ["anio", "cod_territorio", "cod_sexo"]).set_index("cod_indicador").valor
    assert ind["DEP_VEJEZ"] == pytest.approx(50.0)
    assert ind["DEP_JUVENIL"] == pytest.approx(30.0)
    assert ind["DEP_TOTAL"] == pytest.approx(80.0)
    assert ind["IND_ENVEJECIMIENTO"] == pytest.approx(50 / 30 * 100)
    assert ind["PROP_65MAS"] == pytest.approx(50 / 180 * 100)
    assert ind["PROP_80MAS"] == pytest.approx(20 / 180 * 100)
    assert ind["RATIO_SOPORTE"] == pytest.approx(2.0)
    assert ind["IND_REEMPLAZO_LABORAL"] == pytest.approx(100.0)   # (15-24 = 20) / (55-64 = 20)


def test_agregados_funcionales_no_suman_grupos_incompletos():
    v = {e: 1.0 for e in derivados.QUINQUENALES if e != "85+"}   # falta 85+
    agg = derivados.agregados_funcionales(_poblacion(v), ["anio", "cod_territorio", "cod_sexo"]).set_index("cod_edad").valor
    assert agg["0-14"] == 3 and agg["15-64"] == 10
    assert "65+" not in agg.index                                 # no se inventa un 65+ incompleto
