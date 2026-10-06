"""Pruebas de la capa Bronze (sin red): lectores de formatos KOSIS, fechas de descarga y deduplicación."""
from pathlib import Path

import pandas as pd

from src.ingestion import bronze, lectores_kosis

DOBLE = ('"By province",2000,2000,2001,2001,2025.08\n'
         '"By province",Births,TFR,Births,TFR,Births\n'
         '"Seoul",100,0.9,90,0.8,7\n'
         '"Busan",50,1.0,-,0.9,3\n')

XML2003 = """<?xml version="1.0" encoding="EUC-KR" ?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Worksheet ss:Name="Data"><Table>
<Row><Cell><Data ss:Type="String">○ Titulo []</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">By administrative divisions</Data></Cell><Cell><Data ss:Type="String">Item</Data></Cell>
<Cell><Data ss:Type="String">2024 Year</Data></Cell><Cell><Data ss:Type="String">2025 Year</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">Whole country</Data></Cell><Cell><Data ss:Type="String">Total population[Person]</Data></Cell>
<Cell><Data ss:Type="Number">51805547</Data></Cell><Cell><Data ss:Type="Number">51817499</Data></Cell></Row>
</Table></Worksheet>
<Worksheet ss:Name="Meta Data"><Table>
<Row><Cell><Data ss:Type="String">< Statistics metadata ></Data></Cell></Row>
<Row><Cell><Data ss:Type="String">○Table ID</Data></Cell><Cell><Data ss:Type="String">DT_1IN1502</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">○Source</Data></Cell><Cell><Data ss:Type="String">KOSIS, 2026.10.02 09:47</Data></Cell></Row>
</Table></Worksheet></Workbook>"""


def test_csv_encabezado_doble(tmp_path: Path):
    p = tmp_path / "doble.csv"
    p.write_text(DOBLE, encoding="utf-8-sig")
    tabla, _ = lectores_kosis.leer(p, {"lector": "csv_doble", "encoding": "utf-8-sig", "dimensiones": ["territorio"]})
    assert list(tabla.columns) == ["By province", "2000 | Births", "2000 | TFR", "2001 | Births", "2001 | TFR",
                                   "2025.08 | Births"]
    assert tabla.shape == (2, 6)
    assert tabla.iloc[1, 3] == "-"          # bronze conserva el valor tal cual (sin convertir a nulo)


def test_xml2003_mal_formado_se_lee(tmp_path: Path):
    p = tmp_path / "censo.xls"
    p.write_bytes(XML2003.encode("euc-kr"))
    tabla, meta = lectores_kosis.leer(p, {"lector": "xml2003_kosis", "dimensiones": ["territorio", "item"]})
    assert tabla.loc[0, "2025 Year"] == "51817499"
    assert meta["Table ID"] == "DT_1IN1502"
    assert lectores_kosis.fecha_descarga(p, meta, {}) == "2026-10-02"


def test_fecha_descarga_desde_nombre_y_catalogo(tmp_path: Path):
    p = tmp_path / "Vital_Statistics_of_Korea_20261002100432.xlsx"
    p.write_bytes(b"x")
    assert lectores_kosis.fecha_descarga(p, {}, {}) == "2026-10-02"
    q = tmp_path / "tfr_sido_2000_2025.csv"
    q.write_bytes(b"x")
    assert lectores_kosis.fecha_descarga(q, {}, {"fecha_descarga": "2026-10-01"}) == "2026-10-01"


def test_hash_tabla_detecta_mismo_contenido_en_formatos_distintos():
    a = pd.DataFrame({"x": ["1", "2"], "y": ["a", "b"]})
    b = pd.DataFrame({"x": ["1", "2"], "y": ["a", "b"]})
    c = pd.DataFrame({"x": ["1", "3"], "y": ["a", "b"]})
    assert bronze.hash_tabla(a) == bronze.hash_tabla(b)
    assert bronze.hash_tabla(a) != bronze.hash_tabla(c)
