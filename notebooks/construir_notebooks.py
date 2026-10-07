"""Genera y ejecuta los notebooks del proyecto (salidas embebidas). Uso: python notebooks/construir_notebooks.py

Los notebooks NO reimplementan el pipeline: leen sus salidas (bronze/silver/gold/ctl) para explorar, explicar y validar.
Ejecutar primero `python main.py`.
"""
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

AQUI = Path(__file__).resolve().parent
SETUP = """import sys, warnings
from pathlib import Path
RAIZ = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(RAIZ))
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from IPython.display import Image, display, Markdown
pd.set_option('display.max_columns', 40); pd.set_option('display.width', 200); pd.set_option('display.max_colwidth', 80)
GOLD, SILVER, CTL = RAIZ/'data'/'gold', RAIZ/'data'/'silver', RAIZ/'data'/'ctl'"""


def md(t):
    return nbf.v4.new_markdown_cell(t.strip())


def code(t):
    return nbf.v4.new_code_cell(t.strip())


# ============================================================================================ 01 BRONZE
NB01 = [
    md("""# 01 · Bronze — Extracción y exploración inicial (EDA)
**Proyecto ETL 2026 · Grupo 6 · UAO** — ¿Cómo impactará la disminución de la natalidad y el envejecimiento poblacional
en la disponibilidad futura de la fuerza laboral en Corea del Sur?

Este notebook sigue la guía del *Laboratorio práctico de ETL* (partes 1 a 6) aplicada a nuestras fuentes:
extracción verificada, comprensión de cada dataset, perfil de calidad (nulos, únicos, duplicados, tipos),
estadísticos descriptivos y preguntas de negocio sobre los **datos originales**. Aquí **no se limpia ni se imputa nada**:
eso ocurre en Silver."""),
    code(SETUP),
    md("## 1. Extracción: qué quedó en Bronze\n`data/bronze/_manifest.csv` registra cada versión ingerida (fuente, fecha, sha256, filas). "
       "Las descargas manuales de KOSIS se copian sin modificar; World Bank y OECD se descargan por API."),
    code("""from src.ingestion.bronze import leer_vigente
man = pd.read_csv(RAIZ/'data'/'bronze'/'_manifest.csv')
vig = man[man.vigente]
print(f'{len(vig)} datasets vigentes · {vig.filas.sum():,} filas crudas')
vig[['fuente','dataset','tbl_id','fecha_extraccion','filas','columnas','rol']]"""),
    code("""log = pd.read_parquet(CTL/'log_cargas.parquet')
log[log.capa=='bronze'].groupby(['fuente','estado']).size().unstack(fill_value=0)"""),
    md("Dos archivos llegaron **duplicados** (la misma tabla en `.xls` y `.xlsx`): Bronze los detecta por el hash del "
       "contenido tabular y no los ingiere dos veces. UN WPP queda **omitido** porque requiere un token (fuente de contraste opcional)."),
    md("## 2. Verificación de la extracción (shape, columnas, head, muestra aleatoria)"),
    code("""ds_kosis = ['vitales_nacional','vitales_sigungu','tfr_sido','eaps_sido','eaps_sexo_edad','poblacion_nacional',
            'poblacion_sido','proyeccion_escenarios','censo_registros']
crudos = {d: leer_vigente('KOSIS', d)[0] for d in ds_kosis}
for d, df in crudos.items():
    print(f'{d:24s} shape={df.shape}  primeras columnas={list(df.columns[:4])}')"""),
    code("""df = crudos['vitales_nacional']
display(df.iloc[:5, :8]); display(df.sample(5, random_state=6).iloc[:, [0, -3, -2, -1]])"""),
    code("""df = crudos['eaps_sido']
display(df.iloc[:5, :5]); display(df.sample(5, random_state=6).iloc[:, :4])"""),
    md("## 3. Comprensión inicial de cada dataset\n¿Qué representa una fila? ¿Cuáles son los identificadores, las variables "
       "categóricas, numéricas y temporales? (Bronze guarda **todo como texto**, por diseño.)"),
    code("""def perfil(nombre, df, n_dims):
    periodos = sorted({c.split(' | ')[0] for c in df.columns[n_dims:] if not c.startswith('_col')})
    anuales = [p for p in periodos if p[:4].isdigit() and len(p.split()[0]) == 4]
    return {'dataset': nombre, 'filas': len(df), 'variables': df.shape[1],
            'identificadores (dimensiones)': ', '.join(df.columns[:n_dims]),
            'columnas de periodo/ítem': df.shape[1] - n_dims,
            'rango temporal': f"{min(anuales)[:4]}-{max(anuales)[:4]}" if anuales else '',
            'tipo en bronze': ', '.join(sorted({str(t) for t in df.dtypes}))}
dims = {'vitales_nacional':1,'vitales_sigungu':1,'tfr_sido':1,'eaps_sido':1,'eaps_sexo_edad':2,'poblacion_nacional':3,
        'poblacion_sido':6,'proyeccion_escenarios':5,'censo_registros':3}
pd.DataFrame([perfil(d, crudos[d], dims[d]) for d in ds_kosis])"""),
    md("""| Dataset | ¿Qué representa una fila (en bronze)? |
|---|---|
| vitales_nacional (DT_1B8000F) | Un ítem vital (nacimientos, TFR, esperanza de vida…) con un valor por año 1970-2025 en columnas |
| vitales_sigungu (DT_1B8000I) | Un si-do con 10 ítems × 26 años en columnas (encabezado doble periodo / ítem) |
| tfr_sido (DT_1B81A17) | Un si-do con la TFR y las tasas específicas por edad de la madre × 26 años |
| eaps_sido (DT_1DA7004S) | Un si-do con 9 indicadores laborales; mezcla columnas anuales y **mensuales** |
| eaps_sexo_edad (DT_1DA7012S) | Una combinación sexo × grupo de edad con 8 indicadores laborales por periodo |
| poblacion_nacional / poblacion_sido | Un escenario × (si-do) × sexo × grupo de edad con la población por año en columnas |
| proyeccion_escenarios | Uno de los 28 escenarios × sexo × edad con la población proyectada 2022-2072 |
| censo_registros (DT_1IN1502) | Una unidad administrativa (país, si-do, si-gun-gu, agregados urbanos) × ítem del censo |

**Variables categóricas:** territorio, sexo, grupo de edad, escenario, ítem. **Numéricas:** los valores de cada
celda año-ítem (llegan como texto). **Temporales:** los encabezados de periodo (`2025`, `2025 Year`, `2022 년`, `2026.05 p)`)."""),
    md("## 4. Perfil inicial de calidad\n### 4.1 Valores faltantes\nKOSIS marca la ausencia de dato con `-` o con celdas vacías; "
       "pandas no los ve como nulos porque Bronze guarda texto. Se cuantifican aquí, **sin eliminar ni imputar**."),
    code("""def faltantes(nombre, df, n_dims):
    v = df.iloc[:, n_dims:]
    v = v.loc[:, ~v.columns.str.startswith('_col')]
    marcados = v.isin(['-', '', 'x', '...']).sum().sum() + v.isna().sum().sum()
    return {'dataset': nombre, 'celdas_valor': v.size, 'faltantes': int(marcados),
            'pct_faltantes': round(marcados / v.size * 100, 2)}
nul = pd.DataFrame([faltantes(d, crudos[d], dims[d]) for d in ds_kosis]).sort_values('pct_faltantes', ascending=False)
nul"""),
    code("""s = pd.read_parquet(SILVER/'sin_dato.parquet')
s.groupby(['dataset','motivo']).size().rename('celdas').reset_index().sort_values('celdas', ascending=False)"""),
    md("""**Interpretación de los nulos.** La mayoría son *esperados* por el funcionamiento de la fuente: Sejong no existía
como si-do antes de 2012 (y la EAPS lo publica desde 2017), la tabla de vida 2025 aún no se publicaba en la fecha de descarga,
la mortalidad infantil anual se publica desde 2009 y los censos antiguos no traen todos los grupos de edad.
Los únicos faltantes que representan un problema de calidad son los de la región combinada **Jeonnam-Gwangju**
(sólo existe en 2025) — en Silver se rechaza con motivo trazado."""),
    md("### 4.2 Valores únicos (cardinalidad) y 4.3 duplicados"),
    code("""filas = []
for d in ds_kosis:
    df = crudos[d]
    for c in df.columns[:dims[d]]:
        filas.append({'dataset': d, 'variable': c, 'n_unicos': df[c].nunique(),
                      'ejemplos': ', '.join(df[c].astype(str).unique()[:4])})
card = pd.DataFrame(filas); card"""),
    code("""dup = pd.DataFrame([{'dataset': d, 'filas_duplicadas_completas': int(crudos[d].duplicated().sum()),
                     'claves_dimension_repetidas': int(crudos[d].duplicated(subset=list(crudos[d].columns[:dims[d]])).sum())}
                    for d in ds_kosis]); dup"""),
    code("""c = crudos['censo_registros']; t = c.iloc[:, 0].str.strip()
rep = t[c.Item.eq('Total population[Person]')].value_counts(); rep[rep > 1]"""),
    md("""En el censo de registros se repiten nombres de distritos (`Jung-gu` existe en varias ciudades) y **Sejong** aparece
dos veces (como si-do y como ciudad). Como sólo se usan el nivel nacional y los si-do, el único duplicado relevante es
Sejong: Silver conserva la primera aparición y traza las 70 filas rechazadas.
Las proyecciones por escenario repiten claves por diseño (28 escenarios): la clave incluye el escenario."""),
    md("### 4.4 Tipos de datos\nTodo llega como texto (`string`). Columnas a revisar antes de analizar: valores con `-`, "
       "encabezados de periodo heterogéneos, unidades en **miles** en la EAPS, y la codificación CP949 / EUC-KR de dos archivos."),
    md("## 5. Estadísticos descriptivos (conversión numérica sólo para describir)"),
    code("""def a_largo_num(df, n_dims):
    l = df.melt(id_vars=list(df.columns[:n_dims]), var_name='col', value_name='v')
    l['valor'] = pd.to_numeric(l.v.astype(str).str.replace(',', ''), errors='coerce')
    l['periodo'] = l.col.str.split(' | ', regex=False).str[0]; l['item'] = l.col.str.split(' | ', regex=False).str[1]
    return l
v = a_largo_num(crudos['vitales_nacional'], 1)
v.groupby('By items').valor.describe().round(2)"""),
    code("""e = a_largo_num(crudos['eaps_sido'], 1)
e = e[e.periodo.str.fullmatch(r'\\d{4}')]
e.groupby('item').valor.describe().round(1)"""),
    md("## 6. Preguntas de negocio sobre los datos originales (pandas)"),
    code("""nac = v[v['By items'].eq('Live births(persons)')].set_index('periodo').valor
tfr = v[v['By items'].eq('Total fertility rate(persons)')].set_index('periodo').valor
ev = v[v['By items'].eq('Life expectancy at birth-total(age)')].set_index('periodo').valor.dropna()
print('P1. Año con más nacimientos desde 1970:', nac.idxmax(), f'({nac.max():,.0f})')
print('P2. Año con la TFR más baja:', tfr.idxmin(), f'({tfr.min()})')
print('P3. Primer año con más defunciones que nacimientos:',
      v[v['By items'].eq('Natural increase(persons)')].set_index('periodo').valor.lt(0).idxmax())
print('P4. Ganancia de esperanza de vida', ev.index[0], '→', ev.index[-1], ':', round(ev.iloc[-1] - ev.iloc[0], 1), 'años')
print('P5. Caída de nacimientos 2000 → 2025:', f"{(nac['2025'] / nac['2000'] - 1) * 100:.1f} %")"""),
    code("""t = a_largo_num(crudos['tfr_sido'], 1)
t = t[t.item.eq('Total Fertility Rate') & t.periodo.eq('2025')]
t = t.set_index(t.iloc[:, 0].str.strip()).valor
print('P6. Si-do con la TFR más baja en 2025:', t.drop('Whole country').idxmin(), t.drop('Whole country').min())
print('P7. Si-do con la TFR más alta en 2025:', t.drop('Whole country').idxmax(), t.drop('Whole country').max())
ea = e[e.item.eq('Labor Force Participation rate (%)') & e.periodo.eq('2025')].set_index('By province').valor
print('P8. Si-do con mayor participación laboral en 2025:', ea.drop('Total').idxmax(), ea.drop('Total').max())
es = a_largo_num(crudos['eaps_sexo_edad'], 2)
f60 = es[(es['By gender']=='Female') & es['By age group'].str.startswith('60') & es.item.eq('Labor Force Participation rate (%)')
         & es.periodo.isin(['2000','2025'])].set_index('periodo').valor
print('P9. Participación de mujeres 60+: 2000 =', f60['2000'], '% → 2025 =', f60['2025'], '%')
c = crudos['censo_registros']; fx = c[(c.iloc[:,0].str.strip()=='Whole country') & c.Item.str.startswith('Foreigner-Total')]
print('P10. Población extranjera residente 2016 → 2025:', fx['2016 Year'].iloc[0], '→', fx['2025 Year'].iloc[0])"""),
    md("""## Conclusiones de la exploración (hallazgos)
1. **Formatos heterogéneos:** CSV UTF-8, CSV **CP949**, XLSX y "XLS" que en realidad es XML Spreadsheet 2003 en **EUC-KR**
   con XML mal formado → se requirieron 4 lectores específicos.
2. **Duplicados de archivo:** dos tablas se descargaron en `.xls` y `.xlsx` con contenido idéntico (detectado por hash).
3. **Huecos de la fuente:** la descarga DT_1B8000H no contiene el año **2022** ni la TFR de varios años; DT_1B8000I
   (mismo productor) sí está completa → se elige como fuente maestra regional.
4. **Periodicidades mezcladas:** EAPS y vitales mensuales traen columnas mensuales (`2026.05 p)`) junto con las anuales.
5. **Cambios territoriales:** Sejong (2012), región combinada Jeonnam-Gwangju (sólo 2025), nombres nuevos
   `Gangwon-State` / `Jeonbuk-State`, ciudades metropolitanas creadas entre 1963 y 1997.
6. **Unidades:** la EAPS publica niveles en **miles de personas**; las tasas a 1 decimal.
7. **Agregados redundantes:** `80 Years old & over` coexiste con 80-84, 85-89…; sumarlo duplicaría población.
8. **Proyección disfrazada de historia:** las tablas de población 2000-2072 son de proyección: 2023-2025 **no son observados**.
9. **Faltantes mayormente esperados** (Sejong, tabla de vida 2025, series que empiezan después): no se imputan.
10. Los datos confirman el problema: nacimientos −60 % entre 2000 y 2025, TFR mínima de 0,72 en 2023 y crecimiento
    natural negativo desde 2020."""),
]

# ============================================================================================ 02 SILVER
NB02 = [
    md("""# 02 · Silver — Transformación, limpieza y control de calidad
Cada transformación se registra con el conteo de filas **antes y después** (`ctl.conteos`). Los registros que
incumplen una regla se **rechazan con su motivo** (`ctl.rechazos`) en vez de corregirse en silencio."""),
    code(SETUP),
    md("## 1. Grano y clave de Silver\nUna fila = **valor de un indicador para un año, un territorio, un sexo y un grupo de edad** "
       "(+ escenario y edición en proyecciones). Clave natural: `anio + cod_territorio + cod_sexo + cod_edad + cod_indicador`."),
    code("""h = pd.read_parquet(SILVER/'fact_historico.parquet'); p = pd.read_parquet(SILVER/'fact_proyeccion.parquet')
print('fact_historico', h.shape, '· fact_proyeccion', p.shape)
h.sample(6, random_state=1)[['anio','cod_territorio','cod_sexo','cod_edad','cod_indicador','valor','tipo_dato','estado','fuente','tabla_fuente']]"""),
    md("## 2. Transformaciones y conteos antes/después"),
    code("""c = pd.read_parquet(CTL/'conteos.parquet')
c[c.dataset.isin(['eaps_sido','poblacion_sido','censo_registros'])][['dataset','paso','filas_entrada','filas_salida','diferencia','nota']]"""),
    md("""| # | Transformación | Justificación |
|---|---|---|
| 1 | Formato largo (melt) | Las tablas KOSIS son anchas (un año por columna); el análisis y el modelo dimensional requieren una observación por fila |
| 2 | Sólo periodos anuales | Grano común anual; los meses de EAPS/vitales son otra periodicidad (el promedio anual oficial ya está publicado) |
| 3 | Selección de variables (`items_kosis.csv`) | Se conservan sólo las variables del estudio; el resto queda en Bronze |
| 4 | Homologación (territorio, sexo, edad, escenario) | La misma entidad aparece con nombres distintos (Gangwon/Gangwon-do/Gangwon-State; "35-39 years old"/"35 - 39세") |
| 5 | Territorios fuera de alcance | Si-gun-gu, "Abroad", agregados urbano/rural y provincias anteriores a 1945 no responden las preguntas |
| 6 | Tipos y unidades | Texto → número; miles → personas (×1000); marca preliminar/definitivo desde la propia etiqueta `p)` |
| 7 | Celdas sin dato | Se separan en `sin_dato` con su motivo; **no se imputan** (inventar demografía sesgaría los KPIs) |
| 8 | 85-89…100+ → 85+; se excluye 80+ | Grupo abierto común a todas las fuentes; 80+ duplicaría población |
| 9 | Reglas de aceptación | Integridad referencial, año válido, tipo, rango plausible, unicidad de clave |"""),
    md("## 3. Tratamiento de valores nulos (decisión por variable)"),
    code("""s = pd.read_parquet(SILVER/'sin_dato.parquet')
s.groupby(['cod_indicador','motivo']).size().rename('celdas').reset_index().sort_values('celdas', ascending=False).head(15)"""),
    md("""**Decisión:** ningún valor demográfico se imputa con media, mediana o moda: son conteos y tasas oficiales y un valor
inventado contaminaría los KPIs. El nulo se mantiene cuando tiene interpretación válida (territorio inexistente,
dato aún no publicado). La única "sustitución" es estructural y documentada: el agregado **CNSJ = Chungnam + Sejong**
para comparar 2000-2025, y la elección de DT_1B8000I como maestra regional porque DT_1B8000H no trae 2022."""),
    md("## 4. Rechazos trazados"),
    code("""r = pd.read_parquet(CTL/'rechazos.parquet')
display(r.groupby(['dataset','regla','motivo']).size().rename('registros').reset_index())
r.head(3)"""),
    md("## 5. Reglas de consistencia (no rechazan; dejan evidencia)"),
    code("""v = pd.read_parquet(CTL/'validaciones.parquet')
v[v.tipo=='consistencia'][['dataset','regla','evaluados','afectados','resultado','detalle']]"""),
    md("## 6. Conciliación fuente maestra vs contraste (una fuente maestra por indicador)"),
    code("""k = pd.read_parquet(GOLD/'fact_conciliacion.parquet')
k = k[k.comparable & k.anio.between(2000, 2025)]
k.groupby(['tipo_comparacion','cod_indicador','fuente_contraste']).agg(pares=('dif_pct','size'),
    dentro_tolerancia=('dentro_tolerancia','mean'), dif_max_pct=('dif_pct', lambda s: s.abs().max())).round(3)"""),
    code("display(Image(str(RAIZ/'docs'/'figuras'/'13_calidad_pipeline.png')))"),
    md("""**Lectura:** las fórmulas del pipeline reproducen los indicadores oficiales de KOSTAT (dependencia, envejecimiento,
% 65+) con diferencias < 0,4 %. Frente al Banco Mundial la dependencia de vejez difiere hasta 3,5 % porque el Banco
Mundial usa las estimaciones de población de la ONU, no las de KOSTAT: es una diferencia de **fuente**, no de cálculo,
y por eso KOSTAT es la fuente maestra."""),
]

# ============================================================================================ 03 GOLD
NB03 = [
    md("""# 03 · Gold — Indicadores, escenarios y respuestas a las preguntas de negocio
Cada respuesta indica la **naturaleza del dato**: observado, estimado, proyección oficial, cálculo del pipeline,
escenario propio o inferencia propia (retroalimentación del profesor)."""),
    code(SETUP + "\nfrom src.transformation.gold import leer\nh, p, fl = leer('fact_indicador_historico'), leer('fact_indicador_proyeccion'), leer('fact_fuerza_laboral_escenario')\nF = RAIZ/'docs'/'figuras'"),
    md("## Tablero OKR"),
    code("o = pd.read_parquet(GOLD/'kpi_okr.parquet'); o[['kr','kpi','valor','meta','cumple','interpretacion']]"),
    md("## P1 · ¿Cómo han evolucionado la natalidad y la fecundidad? *(observado)*"),
    code("display(Image(str(F/'01_natalidad_fecundidad.png')))"),
    md("## P2 · ¿Existe relación entre la caída de la natalidad y la población en edad de trabajar? *(estimado + proyección oficial)*"),
    code("""nac = h[(h.cod_indicador=='NACIMIENTOS')&(h.cod_territorio=='00')&(h.cod_sexo=='T')].set_index('anio').valor
p1564 = h[(h.cod_indicador=='POBLACION')&(h.cod_territorio=='00')&(h.cod_edad=='15-64')&(h.cod_sexo=='T')].set_index('anio').valor
p1519 = h[(h.cod_indicador=='POBLACION')&(h.cod_territorio=='00')&(h.cod_edad=='15-19')&(h.cod_sexo=='T')].set_index('anio').valor
# quienes nacen en t entran a la edad de trabajar entre t+15 y t+19: correlación con rezago de 17 años (punto medio)
rez = pd.DataFrame({'nacimientos_t_menos_17': nac.reindex(p1519.index - 17).values,
                    'poblacion_15_19_t': p1519.values, 'poblacion_15_64_t': p1564.reindex(p1519.index).values},
                   index=p1519.index).dropna()
print(rez.corr().round(3)); display(Image(str(F/'05_poblacion_edad_trabajar.png')))"""),
    md("Los nacimientos de hace 15 años determinan casi por completo la población que hoy entra a la edad laboral (15-19). "
       "La población 15-64 alcanzó su máximo en 2019 y, según **todas** las variantes oficiales de KOSTAT, cae en las próximas décadas."),
    md("## P3 · ¿Cómo cambia la proporción de adultos mayores y la dependencia? *(estimado / proyección / cálculo)*"),
    code("display(Image(str(F/'02_piramides_poblacion.png'))); display(Image(str(F/'03_estructura_edad.png'))); display(Image(str(F/'04_dependencia_vejez.png')))"),
    md("## P4 · ¿Qué tendencias presenta la fuerza laboral frente al envejecimiento? *(observado)*"),
    code("display(Image(str(F/'07_participacion_sexo_edad.png'))); display(Image(str(F/'12_esperanza_vida.png')))"),
    md("## P5 · ¿Qué regiones tienen mayor riesgo demográfico? *(inferencia propia)*"),
    code("""r = leer('fact_riesgo_regional').merge(leer('dim_territorio')[['cod_territorio','nombre_es']])
display(r.sort_values('ranking_riesgo')[['ranking_riesgo','nombre_es','nivel_riesgo','indice_riesgo','tfr','prop_65mas','dep_vejez','tasa_participacion','var_pob_15_64_2052_pct']].round(2))
display(Image(str(F/'08_riesgo_regional.png')))"""),
    md("## P6a · Población en edad de trabajar según proyecciones oficiales *(proyección oficial)*  \n## P6b · Fuerza laboral potencial bajo supuestos *(escenario propio — no es pronóstico)*"),
    code("""t = fl.groupby(['cod_escenario','cod_supuesto','anio']).fuerza_laboral_potencial.sum().unstack('anio')[[2025,2035,2050,2072]]/1e6
display(t.loc[['medio','fecundidad_baja','fecundidad_alta','migracion_cero','migracion_alta','envejecimiento_rapido']].round(2))
display(Image(str(F/'06_fuerza_laboral_escenarios.png')))"""),
    md("Supuestos: **A** constante · **B** tendencia 2015-2025 · **C** convergencia al promedio OCDE · **D** cierre del 50 % de la "
       "brecha de género (C y D, aportes del Avance 2 y del repositorio de Miguel). Incluso con B o D la fuerza laboral potencial "
       "cae después de 2035: el efecto demográfico domina. La migración es la palanca con mayor efecto en el corto plazo."),
    md("**Sensibilidad:** cada fila cambia un parámetro de un supuesto y recalcula la variación 2025 → 2050 (escenario medio)."),
    code("""s = pd.read_parquet(GOLD/'fact_escenarios_sensibilidad.parquet')
display(s[['cod_supuesto','variante','var_2050_pct','var_2072_pct']].round(1))"""),
    md("## P7 · Envejecimiento, empleo y productividad *(observado; asociación, no causalidad)*"),
    code("display(Image(str(F/'10_productividad_envejecimiento.png')))"),
    md("## P8 · Señales tempranas de escasez laboral *(cálculo sobre estimado + proyección)*"),
    code("display(Image(str(F/'11_reemplazo_laboral.png')))"),
    md("## P9 · Comparación con la OCDE *(observado, World Bank)*"),
    code("display(Image(str(F/'09_comparacion_internacional.png')))"),
    md("""## P10 · Información para política pública
- **Natalidad:** aun si la TFR se recuperara (escenario fecundidad alta), los nacidos después de 2025 no entran a la
  edad laboral antes de 2040: el efecto sobre la fuerza laboral de 2050 es pequeño (≈ 1,3 pp en la población 15-64).
- **Participación:** el mayor margen está en mujeres (brecha de 16 pp) y en personas de 60+ (supuestos B y D).
- **Migración:** pasar de migración cero a alta cambia la población 15-64 de 2050 en ≈ 8 pp.
- **Territorio:** Busan, Daegu y Gyeongsang concentran el mayor riesgo; Sejong y Gyeonggi el menor."""),
    md("**Robustez del índice regional:** veces que cada si-do queda en el top 5 con los 7 esquemas de ponderación."),
    code("""r = pd.read_parquet(GOLD/'fact_riesgo_sensibilidad.parquet').merge(pd.read_parquet(GOLD/'dim_territorio.parquet')[['cod_territorio','nombre_es']])
display(r[r.en_top5].groupby('nombre_es').esquema.nunique().sort_values(ascending=False).rename('esquemas en el top 5'))"""),
]

# ============================================================================================ 04 VALIDACIÓN
NB04 = [
    md("""# 04 · Validación del pipeline
Comprueba que el pipeline se ejecutó, que las tablas Gold cumplen claves e integridad, que los KPIs se calculan y que
la base SQL quedó cargada."""),
    code(SETUP),
    md("## 1. Pruebas automatizadas (pytest)"),
    code("""import subprocess
r = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(RAIZ/'tests')], capture_output=True, text=True, cwd=RAIZ)
print(r.stdout[-1500:])"""),
    md("## 2. Base de datos SQL: tablas, filas e integridad referencial"),
    code("""import sqlite3
con = sqlite3.connect(RAIZ/'database'/'etl_corea.sqlite')
tablas = pd.read_sql("select name from sqlite_master where type='table' order by name", con)
filas = [(t, con.execute(f'select count(*) from "{t}"').fetchone()[0]) for t in tablas.name]
display(pd.DataFrame(filas, columns=['tabla','filas']))
print('Violaciones de claves foráneas:', con.execute('PRAGMA foreign_key_check').fetchall())"""),
    md("## 3. Consultas analíticas de ejemplo (como las usaría Power BI)"),
    code("""q = '''select t.periodo, f.anio, round(f.valor,1) as dep_vejez, f.tipo_dato
from gold_fact_indicador_historico f join gold_dim_tiempo t on t.anio=f.anio
where f.cod_indicador='DEP_VEJEZ' and f.cod_territorio='00' and f.cod_sexo='T' and f.anio in (2000,2010,2022)
union all
select t.periodo, f.anio, round(f.valor,1), f.tipo_dato from gold_fact_indicador_proyeccion f join gold_dim_tiempo t on t.anio=f.anio
where f.cod_indicador='DEP_VEJEZ' and f.cod_territorio='00' and f.cod_sexo='T' and f.cod_escenario='medio'
  and f.edicion_proyeccion='KOSTAT 2022-2072' and f.anio in (2030,2050,2072) order by 2'''
pd.read_sql(q, con)"""),
    code("""pd.read_sql('''select s.nombre as supuesto, f.anio, round(sum(f.fuerza_laboral_potencial)/1e6,2) as millones
from gold_fact_fuerza_laboral_escenario f join gold_dim_supuesto s using(cod_supuesto)
where f.cod_escenario='medio' and f.anio in (2025,2050) group by 1,2 order by 1,2''', con)"""),
    md("## 4. KPIs de calidad por dataset"),
    code("pd.read_parquet(GOLD/'kpi_calidad_dataset.parquet').sort_values('tasa_validos_pct').head(10)"),
    code("""o = pd.read_parquet(GOLD/'kpi_okr.parquet'); proc = o[o.tipo_kpi=='proceso']
print(f"KPIs de proceso que cumplen: {int(proc.cumple.sum())} de {len(proc)}")
proc[['kr','kpi','valor','meta','cumple']]"""),
]


def construir(nombre, celdas):
    nb = nbf.v4.new_notebook()
    nb.cells = celdas
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(AQUI)}}).execute()
    nbf.write(nb, AQUI / nombre)
    print("ok", nombre)


if __name__ == "__main__":
    construir("01_bronze_exploracion.ipynb", NB01)
    construir("02_silver_transformacion_calidad.ipynb", NB02)
    construir("03_gold_analisis_kpis.ipynb", NB03)
    construir("04_validacion_pipeline.ipynb", NB04)
