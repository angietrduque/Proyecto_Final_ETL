# Diccionario de datos — capa Gold

Generado automáticamente por `src/analytics/diccionario.py` a partir de `data/gold/*.parquet`. Versión Excel: `diccionario_datos.xlsx` (hojas *columnas* e *indicadores*).

## `dim_tiempo` (148 filas)

Calendario anual 1925-2072. Separa periodo Histórico (≤2025) y Proyección.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | int64 | PK | Año calendario (clave hacia dim_tiempo) | 0.0 | 1925 |
| decada | str |  |  | 0.0 | 1920s |
| quinquenio | str |  |  | 0.0 | 1925-1929 |
| periodo | str |  |  | 0.0 | Histórico |
| en_ventana_analisis | bool |  |  | 0.0 | False |
| horizonte | str |  |  | 0.0 | Antes de 2000 |

## `dim_territorio` (27 filas)

País, 17 si-do, agregado CNSJ (Chungnam+Sejong) y países de comparación.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_territorio | str | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 00 |
| nombre_es | str |  |  | 0.0 | Corea del Sur (nacional) |
| nombre_en | str |  |  | 0.0 | South Korea |
| nombre_ko | str |  |  | 0.0 | 전국 |
| tipo | str |  |  | 0.0 | nacional |
| region_macro | str |  |  | 0.0 | Nacional |
| cod_oecd_tl3 | str |  |  | 0.0 |  |
| iso3 | str |  |  | 0.0 | KOR |
| vigente_desde | str |  |  | 0.0 |  |
| orden | str |  |  | 0.0 | 0 |
| observacion | str |  |  | 0.0 | Total nacional |

## `dim_sexo` (3 filas)

Total, hombres, mujeres.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_sexo | str | PK | T total, H hombres, M mujeres | 0.0 | T |
| nombre | str |  |  | 0.0 | Total |
| orden | int64 |  |  | 0.0 | 0 |

## `dim_edad` (32 filas)

Grupos quinquenales, grupos funcionales (0-14, 15-64, 65+) y grupos de la EAPS.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_edad | str | PK | Código de grupo de edad (dim_edad) | 0.0 | TOTAL |
| etiqueta | str |  |  | 0.0 | Todas las edades |
| edad_min | str |  |  | 0.0 | 0 |
| edad_max | str |  |  | 0.0 |  |
| tipo | str |  |  | 0.0 | total |
| grupo_funcional | str |  |  | 0.0 | Total |
| orden | str |  |  | 0.0 | 0 |
| observacion | str |  |  | 0.0 |  |

## `dim_indicador` (45 filas)

Catálogo de indicadores: definición, fórmula, unidad, fuente maestra/contraste, rango válido, aditividad.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_indicador | str | PK | Código del indicador (dim_indicador) | 0.0 | NACIMIENTOS |
| nombre | str |  |  | 0.0 | Nacimientos |
| categoria | str |  |  | 0.0 | Natalidad |
| definicion | str |  |  | 0.0 | Nacidos vivos registrados en el año |
| formula | str |  |  | 0.0 | dato publicado |
| unidad | str |  |  | 0.0 | personas |
| frecuencia_original | str |  |  | 0.0 | anual |
| fuente_maestra | str |  |  | 0.0 | KOSIS DT_1B8000F (nacional) / DT_1B8000I |
| fuente_contraste | str |  |  | 0.0 | KOSIS DT_1B8000H; OECD; WB |
| es_derivado | str |  | True si el valor es un cálculo del pipeline | 0.0 | false |
| aditivo | str |  |  | 0.0 | true |
| rango_min | str |  |  | 0.0 | 0 |
| rango_max | str |  |  | 0.0 | 50000000 |
| decimales | str |  |  | 0.0 | 0 |

## `dim_escenario` (29 filas)

29 escenarios de proyección KOSTAT 2022-2072 (medio + 28 alternativos) con sus supuestos de fecundidad, esperanza de vida y migración.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_escenario | str | PK | Escenario KOSTAT (dim_escenario) | 0.0 | medio |
| nombre_escenario | str |  |  | 0.0 | Medio (base) |
| familia | str |  |  | 0.0 | Base |
| supuesto_fecundidad | str |  |  | 0.0 | media |
| supuesto_esperanza_vida | str |  |  | 0.0 | media |
| supuesto_migracion | str |  |  | 0.0 | media |
| orden | int64 |  |  | 0.0 | 1 |
| etiqueta_kostat | str |  |  | 0.0 | 중위 추계(기본 추계: 출산율-중위 / 기대수명-중위 / 국제순이동-중위 |

## `dim_supuesto` (4 filas)

Supuestos A/B/C/D de participación laboral de los escenarios propios.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_supuesto | str | PK | Supuesto de participación A/B/C/D (dim_supuesto) | 0.0 | A_constante |
| nombre | str |  |  | 0.0 | A · Participación constante |
| descripcion | str |  |  | 0.0 | Tasas de participación por sexo y grupo  |

## `dim_tipo_dato` (6 filas)

Naturaleza del dato: observado, estimado, calculado, proyección oficial, escenario propio, inferencia propia.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| tipo_dato | str | PK | Naturaleza del dato (dim_tipo_dato) | 0.0 | observado |
| descripcion | str |  |  | 0.0 | Dato publicado por la fuente (registro a |
| orden | int64 |  |  | 0.0 | 1 |

## `dim_fuente` (29 filas)

Versión vigente de cada dataset de Bronze (fuente, tabla, URL, fecha de extracción, sha256).

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| fuente | str | PK | Institución productora (KOSIS, WB, OECD) o 'Pipeline' si es cálculo propio | 0.0 | KOSIS |
| dataset | str | PK | Dataset de origen en Bronze (o regla de cálculo) | 0.0 | censo_historico |
| tbl_id | str |  |  | 51.72 | DT_1IN0001 |
| rol | str |  |  | 0.0 | contexto |
| url | str |  |  | 0.0 | https://kosis.kr/statHtml/statHtml.do?or |
| fecha_extraccion | str |  |  | 0.0 | 2026-10-02 |
| filas | str |  |  | 0.0 | 2632 |
| archivo_crudo | str |  |  | 0.0 | data/bronze/kosis/2026-10-02/101_DT_1IN0 |
| version | str |  |  | 0.0 | 886ae1f37ea9 |

## `fact_indicador_historico` (81.087 filas)

Grano: año × territorio × sexo × edad × indicador. Datos observados/estimados y derivados. Nunca proyecciones.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | Int64 | PK | Año calendario (clave hacia dim_tiempo) | 0.0 | 1970 |
| cod_territorio | str | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 00 |
| cod_sexo | str | PK | T total, H hombres, M mujeres | 0.0 | T |
| cod_edad | str | PK | Código de grupo de edad (dim_edad) | 0.0 | TOTAL |
| cod_indicador | str | PK | Código del indicador (dim_indicador) | 0.0 | NACIMIENTOS |
| valor | Float64 |  | Valor numérico en la unidad del indicador | 5.65 | 1006645.0 |
| tipo_dato | str | FK → dim_tipo_dato | Naturaleza del dato (dim_tipo_dato) | 0.0 | observado |
| estado | str |  | definitivo / preliminar (según marca 'p)' de la fuente) / proyectado | 0.0 | definitivo |
| fuente | str |  | Institución productora (KOSIS, WB, OECD) o 'Pipeline' si es cálculo propio | 0.0 | KOSIS |
| dataset | str |  | Dataset de origen en Bronze (o regla de cálculo) | 0.0 | vitales_nacional |
| tabla_fuente | str |  | ID de la tabla en la fuente (tblId / código WDI / dataflow) | 29.64 | DT_1B8000F |
| version_fuente | str |  | Primeros 12 caracteres del sha256 del archivo crudo | 29.64 | 7db493a61158 |
| es_derivado | bool |  | True si el valor es un cálculo del pipeline | 0.0 | False |

## `fact_indicador_proyeccion` (188.160 filas)

Grano: año × territorio × sexo × edad × indicador × escenario × edición. Proyección KOSTAT y derivados.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | Int64 | PK | Año calendario (clave hacia dim_tiempo) | 0.0 | 2072 |
| cod_territorio | str | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 00 |
| cod_sexo | str | PK | T total, H hombres, M mujeres | 0.0 | T |
| cod_edad | str | PK | Código de grupo de edad (dim_edad) | 0.0 | TOTAL |
| cod_indicador | str | PK | Código del indicador (dim_indicador) | 0.0 | POBLACION |
| cod_escenario | str | PK | Escenario KOSTAT (dim_escenario) | 0.0 | medio |
| edicion_proyeccion | str | PK | Edición de la proyección (nacional 2022-2072 o provincial 2022-2052) | 0.0 | KOSTAT 2022-2072 |
| valor | Float64 |  | Valor numérico en la unidad del indicador | 0.0 | 36222293.0 |
| tipo_dato | str | FK → dim_tipo_dato | Naturaleza del dato (dim_tipo_dato) | 0.0 | proyeccion_oficial |
| fuente | str |  | Institución productora (KOSIS, WB, OECD) o 'Pipeline' si es cálculo propio | 0.0 | KOSIS |
| dataset | str |  | Dataset de origen en Bronze (o regla de cálculo) | 0.0 | poblacion_nacional |
| estado | str |  | definitivo / preliminar (según marca 'p)' de la fuente) / proyectado | 0.0 | proyectado |

## `fact_fuerza_laboral_escenario` (69.600 filas)

Grano: año × escenario de población × supuesto × sexo × grupo EAPS. Escenario propio (no pronóstico).

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | Int64 | PK | Año calendario (clave hacia dim_tiempo) | 0.0 | 2023 |
| cod_escenario | str | PK | Escenario KOSTAT (dim_escenario) | 0.0 | covid_largo_plazo |
| cod_sexo | str | PK | T total, H hombres, M mujeres | 0.0 | H |
| cod_edad | str | PK | Código de grupo de edad (dim_edad) | 0.0 | 15-19 |
| poblacion_proyectada | Float64 |  | Población KOSTAT del grupo sexo × edad (personas) | 0.0 | 1188393.0 |
| tasa_participacion | Float64 |  | Tasa de participación supuesta (%) | 0.0 | 5.3 |
| cod_supuesto | str | PK | Supuesto de participación A/B/C/D (dim_supuesto) | 0.0 | A_constante |
| factor_cobertura | Float64 |  | Población 15+ EAPS / población KOSTAT en 2025, por sexo y grupo (ajuste de escala) | 0.0 | 0.9710101245359017 |
| fuerza_laboral_potencial | Float64 |  | poblacion_proyectada × tasa_participacion / 100 (personas) | 0.0 | 61158.90665116248 |
| tipo_dato | str | FK → dim_tipo_dato | Naturaleza del dato (dim_tipo_dato) | 0.0 | escenario_propio |
| fuerza_laboral_total_anio | Float64 |  | Suma de la fuerza laboral potencial del año, escenario y supuesto | 0.0 | 29463939.20639693 |
| fuerza_laboral_total_base | Float64 |  | Misma suma en el año base 2025 | 0.0 | 29593423.670705568 |
| indice_base_2025 | Float64 |  | fuerza_laboral_total_anio / base × 100 | 0.0 | 99.56245527469397 |

## `fact_riesgo_regional` (17 filas)

Grano: si-do (año de referencia 2025). Componentes e índice compuesto de riesgo (inferencia propia).

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_territorio | str | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 11 |
| tfr | Float64 |  |  | 0.0 | 0.632 |
| prop_65mas | Float64 |  |  | 0.0 | 19.862238412728868 |
| dep_vejez | Float64 |  |  | 0.0 | 27.667889397883798 |
| tasa_participacion | Float64 |  | Tasa de participación supuesta (%) | 0.0 | 63.7 |
| ind_reemplazo_laboral | Float64 |  |  | 0.0 | 64.46575882438016 |
| pob_15_64_base | Float64 |  |  | 0.0 | 6704935.0 |
| pob_15_64_2052 | Float64 |  |  | 0.0 | 4387767.0 |
| nacimientos_2015 | Float64 |  |  | 0.0 | 83005.0 |
| nacimientos_base | Float64 |  |  | 0.0 | 45516.0 |
| var_pob_15_64_2052_pct | Float64 |  |  | 0.0 | -34.55914188579009 |
| var_nacimientos_10a_pct | Float64 |  |  | 0.0 | -45.164749111499304 |
| z_tfr | Float64 |  |  | 0.0 | 2.203359263544553 |
| z_prop_65mas | Float64 |  |  | 0.0 | -0.26913179721712266 |
| z_dep_vejez | Float64 |  |  | 0.0 | -0.4543237313289979 |
| z_tasa_participacion | Float64 |  |  | 0.0 | 0.4682502025990293 |
| z_ind_reemplazo_laboral | Float64 |  |  | 0.0 | -0.3757881066658348 |
| z_var_pob_15_64_2052_pct | Float64 |  |  | 0.0 | 0.03267824369927586 |
| indice_riesgo | Float64 |  | Promedio de los 6 componentes estandarizados (z) con signo de riesgo | 0.0 | 0.2675073457718172 |
| ranking_riesgo | int64 |  | 1 = mayor riesgo | 0.0 | 8 |
| nivel_riesgo | str |  | Terciles: Alto / Medio / Bajo | 0.0 | Medio |
| anio_referencia | int64 |  |  | 0.0 | 2025 |
| tipo_dato | str | FK → dim_tipo_dato | Naturaleza del dato (dim_tipo_dato) | 0.0 | inferencia_propia |
| nota | str |  |  | 0.0 | TFR, participación y nacimientos observa |

## `fact_riesgo_sensibilidad` (119 filas)

Grano: esquema de ponderación × si-do. Índice y ranking del riesgo regional con 7 esquemas (robustez).

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| esquema | str | PK | Esquema de ponderación/normalización del índice de riesgo | 0.0 | base_6z |
| descripcion | str |  |  | 0.0 | Esquema base · 6 componentes estandariza |
| cod_territorio | str | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 11 |
| indice | float64 |  |  | 0.0 | 0.2675073457718172 |
| ranking | int64 |  |  | 0.0 | 8 |
| en_top5 | bool |  | Si el si-do queda entre los 5 de mayor riesgo | 0.0 | False |
| tipo_dato | str | FK → dim_tipo_dato | Naturaleza del dato (dim_tipo_dato) | 0.0 | inferencia_propia |

## `fact_escenarios_sensibilidad` (12 filas)

Grano: supuesto × variante de parámetro. Variación de la fuerza laboral potencial 2025-2050 y 2025-2072.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| cod_supuesto | str | PK | Supuesto de participación A/B/C/D (dim_supuesto) | 0.0 | A_constante |
| variante | str | PK | Parámetro modificado del supuesto (base = parámetros de config.yaml) | 0.0 | base |
| es_base | bool |  |  | 0.0 | True |
| fuerza_laboral_2025 | float64 |  |  | 0.0 | 29606821.0 |
| fuerza_laboral_2050 | float64 |  |  | 0.0 | 26135624.82746642 |
| var_2050_pct | float64 |  |  | 0.0 | -11.724312355364253 |
| var_2072_pct | float64 |  |  | 0.0 | -33.65917608036406 |
| tipo_dato | str | FK → dim_tipo_dato | Naturaleza del dato (dim_tipo_dato) | 0.0 | escenario_propio |

## `fact_comparacion_internacional` (3.480 filas)

Grano: año × país × indicador × fuente (World Bank / OECD).

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | Int64 | PK | Año calendario (clave hacia dim_tiempo) | 0.0 | 2024 |
| cod_territorio | string | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | CHN |
| cod_sexo | str | PK | T total, H hombres, M mujeres | 0.0 | T |
| cod_edad | str | PK | Código de grupo de edad (dim_edad) | 0.0 | TOTAL |
| cod_indicador | str | PK | Código del indicador (dim_indicador) | 0.0 | TFR |
| valor | Float64 |  | Valor numérico en la unidad del indicador | 0.0 | 1.013 |
| fuente | str | PK | Institución productora (KOSIS, WB, OECD) o 'Pipeline' si es cálculo propio | 0.0 | WB |
| dataset | str |  | Dataset de origen en Bronze (o regla de cálculo) | 0.0 | WB/SP.DYN.TFRT.IN |
| tabla_fuente | str |  | ID de la tabla en la fuente (tblId / código WDI / dataflow) | 0.0 | SP.DYN.TFRT.IN |
| tipo_dato | str | FK → dim_tipo_dato | Naturaleza del dato (dim_tipo_dato) | 0.0 | observado |

## `fact_conciliacion` (9.441 filas)

Pares fuente maestra vs contraste y fórmulas del pipeline vs publicadas, con diferencia %.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | Int64 |  | Año calendario (clave hacia dim_tiempo) | 0.0 | 1990 |
| cod_territorio | str |  | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 00 |
| cod_sexo | str |  | T total, H hombres, M mujeres | 0.0 | T |
| cod_edad | str |  | Código de grupo de edad (dim_edad) | 0.0 | TOTAL |
| cod_indicador | str |  | Código del indicador (dim_indicador) | 0.0 | NACIMIENTOS |
| valor_maestra | Float64 |  |  | 0.0 | 649738.0 |
| fuente_maestra | str |  |  | 0.0 | KOSIS |
| dataset_maestra | str |  |  | 0.0 | vitales_nacional |
| valor_contraste | Float64 |  |  | 0.0 | 649738.0 |
| fuente_contraste | str |  |  | 0.0 | KOSIS |
| dataset_contraste | str |  |  | 0.0 | vitales_sido |
| dif_abs | Float64 |  |  | 0.0 | 0.0 |
| dif_pct | Float64 |  | (contraste - maestra) / |maestra| × 100 | 0.02 | 0.0 |
| comparable | bool |  | False cuando las definiciones no son comparables (p. ej. participación modelada OIT) | 0.0 | True |
| nota | str |  |  | 0.0 |  |
| dentro_tolerancia | boolean |  | |dif_pct| ≤ 3 % | 0.02 | True |
| tipo_comparacion | str |  |  | 0.0 | dato publicado |

## `dataset_nacional_anual` (103 filas)

Tabla plana: una fila por año (1970-2072) con los indicadores nacionales clave en columnas.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | Int64 | PK | Año calendario (clave hacia dim_tiempo) | 0.0 | 1970 |
| cod_territorio | str | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 00 |
| CRECIMIENTO_NATURAL | Float64 |  |  | 45.63 | 748056.0 |
| DEFUNCIONES | Float64 |  |  | 45.63 | 258589.0 |
| DEP_JUVENIL | Float64 |  |  | 29.13 | 29.408441983211315 |
| DEP_TOTAL | Float64 |  |  | 29.13 | 39.48172371800285 |
| DEP_VEJEZ | Float64 |  |  | 29.13 | 10.073281734791534 |
| ESPERANZA_VIDA | Float64 |  |  | 46.6 | 62.3 |
| IND_ENVEJECIMIENTO | Float64 |  |  | 29.13 | 34.25302755087184 |
| IND_REEMPLAZO_LABORAL | Float64 |  |  | 29.13 | 201.30573344196137 |
| MATRIMONIOS | Float64 |  |  | 45.63 | 295137.0 |
| MORTALIDAD_INFANTIL | Float64 |  |  | 75.73 | 5.4 |
| NACIMIENTOS | Float64 |  |  | 45.63 | 1006645.0 |
| OCUPADOS | Float64 |  |  | 74.76 | 21173000.0 |
| POB_15MAS | Float64 |  |  | 74.76 | 36192000.0 |
| POB_ACTIVA | Float64 |  |  | 74.76 | 22151000.0 |
| POB_EXTRANJERA | Float64 |  |  | 90.29 | 1413758.0 |
| PROP_0_14 | Float64 |  |  | 29.13 | 21.084082702238344 |
| PROP_15_64 | Float64 |  |  | 29.13 | 71.69398064091536 |
| PROP_65MAS | Float64 |  |  | 29.13 | 7.221936656846305 |
| PROP_80MAS | Float64 |  |  | 29.13 | 1.028305519445357 |
| PROP_EXTRANJEROS | Float64 |  |  | 90.29 | 2.7575000945005295 |
| RATIO_SOPORTE | Float64 |  |  | 29.13 | 9.927251379718259 |
| TASA_BRUTA_NATALIDAD | Float64 |  |  | 45.63 | 31.2 |
| TASA_DESEMPLEO | Float64 |  |  | 74.76 | 4.4 |
| TASA_EMPLEO | Float64 |  |  | 74.76 | 58.5 |
| TASA_PARTICIPACION | Float64 |  |  | 74.76 | 61.2 |
| TFR | Float64 |  |  | 45.63 | 4.53 |
| POB_0_14 | Float64 |  |  | 29.13 | 9911229.0 |
| POB_15_64 | Float64 |  |  | 29.13 | 33701986.0 |
| POB_65MAS | Float64 |  |  | 29.13 | 3394896.0 |
| POB_TOTAL | Float64 |  |  | 29.13 | 47008111.0 |
| tipo_dato_poblacion | str |  | estimado (≤2022) o proyeccion_oficial (≥2023) para la población y estructura de esa fila | 0.0 | estimado |
| FLP_A | Float64 |  |  | 51.46 | 29463939.20639693 |
| FLP_B | Float64 |  |  | 51.46 | 29463939.20639693 |
| FLP_C | Float64 |  |  | 51.46 | 29463939.20639693 |
| FLP_D | Float64 |  |  | 51.46 | 29463939.20639693 |
| PIB_HORA | Float64 |  |  | 74.76 | 19.522798554740376 |
| periodo | str |  |  | 0.0 | Histórico |

## `dataset_regional_anual` (915 filas)

Tabla plana: una fila por año y si-do con los indicadores regionales clave.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| anio | Int64 | PK | Año calendario (clave hacia dim_tiempo) | 0.0 | 2000 |
| cod_territorio | str | PK | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 11 |
| CRECIMIENTO_NATURAL | Float64 |  |  | 50.16 | 93858.0 |
| DEFUNCIONES | Float64 |  |  | 50.16 | 39296.0 |
| DEP_JUVENIL | Float64 |  |  | 0.33 | 24.374465055973154 |
| DEP_TOTAL | Float64 |  |  | 0.33 | 31.397363430786314 |
| DEP_VEJEZ | Float64 |  |  | 0.33 | 7.022898374813156 |
| IND_ENVEJECIMIENTO | Float64 |  |  | 0.33 | 28.812523100243958 |
| IND_REEMPLAZO_LABORAL | Float64 |  |  | 0.33 | 218.31377294898263 |
| MATRIMONIOS | Float64 |  |  | 50.16 | 78745.0 |
| NACIMIENTOS | Float64 |  |  | 50.16 | 133154.0 |
| OCUPADOS | Float64 |  |  | 50.71 | 4668000.0 |
| POB_15MAS | Float64 |  |  | 50.71 | 8015000.0 |
| POB_ACTIVA | Float64 |  |  | 50.71 | 4918000.0 |
| POB_EXTRANJERA | Float64 |  |  | 80.33 | 335167.0 |
| PROP_0_14 | Float64 |  |  | 0.33 | 18.550193412984598 |
| PROP_15_64 | Float64 |  |  | 0.33 | 76.10502782475929 |
| PROP_65MAS | Float64 |  |  | 0.33 | 5.34477876225612 |
| PROP_80MAS | Float64 |  |  | 0.33 | 0.7665079713772993 |
| PROP_EXTRANJEROS | Float64 |  |  | 81.42 | 3.4181509857828853 |
| RATIO_SOPORTE | Float64 |  |  | 0.33 | 14.239135277628233 |
| TASA_BRUTA_NATALIDAD | Float64 |  |  | 53.01 | 12.9 |
| TASA_DESEMPLEO | Float64 |  |  | 50.71 | 5.1 |
| TASA_EMPLEO | Float64 |  |  | 50.71 | 58.2 |
| TASA_PARTICIPACION | Float64 |  |  | 50.71 | 61.4 |
| TFR | Float64 |  |  | 53.01 | 1.275 |
| POB_0_14 | Float64 |  |  | 0.33 | 1869569.0 |
| POB_15_64 | Float64 |  |  | 0.33 | 7670195.0 |
| POB_65MAS | Float64 |  |  | 0.33 | 538670.0 |
| POB_TOTAL | Float64 |  |  | 0.33 | 10078434.0 |
| tipo_dato_poblacion | str |  | estimado (≤2022) o proyeccion_oficial (≥2023) para la población y estructura de esa fila | 0.0 | estimado |
| periodo | str |  |  | 0.0 | Histórico |

## `kpi_okr` (13 filas)

OKR del estudio: 13 resultados clave (O1 diagnóstico, O2 impacto laboral, O3 decisión, O4 calidad).

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| objetivo_cod | str |  |  | 0.0 | O1 |
| eje | str |  |  | 0.0 | Diagnóstico |
| objetivo | str |  |  | 0.0 | Diagnosticar la magnitud de la caída de  |
| kr | str | PK |  | 0.0 | KR1.1 |
| kpi | str |  |  | 0.0 | Serie demográfica y laboral integrada: n |
| meta | str |  |  | 0.0 | completitud ≥ 95 % nacional y ≥ 90 % reg |
| valor | str |  | Valor numérico en la unidad del indicador | 0.0 | 96.2 % / 97.0 % |
| cumple | boolean |  |  | 0.0 | True |
| interpretacion | str |  |  | 0.0 | celdas con dato / esperadas (Sejong desd |
| tabla_gold | str |  |  | 0.0 | kpi_completitud |
| tipo_kpi | str |  |  | 0.0 | resultado |
| formula | str |  |  | 0.0 |  |

## `kpi_calidad_dataset` (32 filas)

Registros evaluados, válidos y rechazados por dataset (reglas de aceptación).

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| dataset | str | PK | Dataset de origen en Bronze (o regla de cálculo) | 0.0 | OECD/fecundidad/NACIMIENTOS |
| registros_evaluados | int64 |  |  | 0.0 | 176 |
| registros_validos | int64 |  |  | 0.0 | 176 |
| registros_rechazados | int64 |  |  | 0.0 | 0 |
| rechazos_trazados | float64 |  |  | 0.0 | 0.0 |
| tasa_validos_pct | float64 |  |  | 0.0 | 100.0 |
| tasa_rechazo_pct | float64 |  |  | 0.0 | 0.0 |
| rechazos_trazados_pct | float64 |  |  | 0.0 | 100.0 |
| cumple_validos | bool |  |  | 0.0 | True |
| cumple_rechazo | bool |  |  | 0.0 | True |

## `kpi_completitud` (78 filas)

Celdas con dato / esperadas 2000-2025 por indicador y territorio.

| Columna | Tipo | Clave | Descripción | % nulos | Ejemplo |
|---|---|---|---|---|---|
| nivel | str |  |  | 0.0 | nacional |
| cod_indicador | str |  | Código del indicador (dim_indicador) | 0.0 | NACIMIENTOS |
| cod_territorio | str |  | Código de territorio (KOSIS si-do / ISO3) | 0.0 | 00 |
| celdas_esperadas | int64 |  |  | 0.0 | 26 |
| celdas_observadas | int64 |  |  | 0.0 | 26 |
| celdas_con_proyeccion | int64 |  |  | 0.0 | 26 |
| anios_faltantes | str |  |  | 0.0 |  |

## Catálogo de indicadores (`dim_indicador`)

| Código | Nombre | Categoría | Fórmula | Unidad | Fuente maestra | Contraste | Derivado |
|---|---|---|---|---|---|---|---|
| NACIMIENTOS | Nacimientos | Natalidad | dato publicado | personas | KOSIS DT_1B8000F (nacional) / DT_1B8000I (si-do) | KOSIS DT_1B8000H; OECD; WB | False |
| TFR | Tasa global de fecundidad | Natalidad | dato publicado | hijos por mujer | KOSIS DT_1B8000F (nacional) / DT_1B81A17 (si-do) | KOSIS DT_1B8000H; OECD; WB | False |
| TASA_FEC_EDAD | Tasa específica de fecundidad por edad | Natalidad | dato publicado | por 1.000 mujeres | KOSIS DT_1B81A17 |  | False |
| TASA_BRUTA_NATALIDAD | Tasa bruta de natalidad | Natalidad | dato publicado | por 1.000 hab. | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| RAZON_SEXO_NACER | Razón de sexo al nacer | Natalidad | dato publicado | niños por 100 niñas | KOSIS DT_1B8000F |  | False |
| BRECHA_REEMPLAZO | Brecha frente al nivel de reemplazo | Natalidad | 2.1 - TFR | hijos por mujer | Pipeline |  | True |
| DEFUNCIONES | Defunciones | Mortalidad | dato publicado | personas | KOSIS DT_1B8000F / DT_1B8000I | KOSIS DT_1B8000H | False |
| TASA_BRUTA_MORTALIDAD | Tasa bruta de mortalidad | Mortalidad | dato publicado | por 1.000 hab. | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| MORTALIDAD_INFANTIL | Tasa de mortalidad infantil | Mortalidad | dato publicado | por 1.000 nacidos vivos | KOSIS DT_1B8000F |  | False |
| ESPERANZA_VIDA | Esperanza de vida al nacer | Mortalidad | dato publicado | años | KOSIS DT_1B8000F | WB SP.DYN.LE00.IN | False |
| CRECIMIENTO_NATURAL | Crecimiento natural | Mortalidad | dato publicado (= NACIMIENTOS - DEFUNCIONES) | personas | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| TASA_CRECIMIENTO_NATURAL | Tasa de crecimiento natural | Mortalidad | dato publicado | por 1.000 hab. | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| MATRIMONIOS | Matrimonios | Nupcialidad | dato publicado | casos | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| TASA_NUPCIALIDAD | Tasa bruta de nupcialidad | Nupcialidad | dato publicado | por 1.000 hab. | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| DIVORCIOS | Divorcios | Nupcialidad | dato publicado | casos | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| TASA_DIVORCIALIDAD | Tasa bruta de divorcialidad | Nupcialidad | dato publicado | por 1.000 hab. | KOSIS DT_1B8000F / DT_1B8000I |  | False |
| POBLACION | Población | Estructura | dato publicado | personas | KOSIS DT_1BPA001 (nacional) / DT_1BPB001 (si-do) | WB SP.POP.*; KOSIS DT_1IN1502; KOSIS DT_1BPA002 | False |
| PROP_0_14 | Proporción de 0-14 años | Estructura | P(0-14) / P(total) × 100 | % | Pipeline |  | True |
| PROP_15_64 | Proporción en edad de trabajar | Estructura | P(15-64) / P(total) × 100 | % | Pipeline | KOSIS DT_1BPA002 | True |
| PROP_65MAS | Proporción de 65 y más | Envejecimiento | P(65+) / P(total) × 100 | % | Pipeline | WB SP.POP.65UP.TO.ZS; KOSIS DT_1BPA002 | True |
| PROP_80MAS | Proporción de 80 y más | Envejecimiento | P(80-84 + 85+) / P(total) × 100 | % | Pipeline |  | True |
| DEP_JUVENIL | Tasa de dependencia juvenil | Envejecimiento | P(0-14) / P(15-64) × 100 | por 100 en edad de trabajar | Pipeline | KOSIS DT_1BPA002 | True |
| DEP_VEJEZ | Tasa de dependencia de vejez | Envejecimiento | P(65+) / P(15-64) × 100 | por 100 en edad de trabajar | Pipeline | WB SP.POP.DPND.OL; KOSIS DT_1BPA002 | True |
| DEP_TOTAL | Tasa de dependencia total | Envejecimiento | (P(0-14) + P(65+)) / P(15-64) × 100 | por 100 en edad de trabajar | Pipeline | KOSIS DT_1BPA002 | True |
| IND_ENVEJECIMIENTO | Índice de envejecimiento | Envejecimiento | P(65+) / P(0-14) × 100 | por 100 menores de 15 | Pipeline | KOSIS DT_1BPA002 | True |
| RATIO_SOPORTE | Razón de soporte potencial | Envejecimiento | P(15-64) / P(65+) | personas por adulto mayor | Pipeline |  | True |
| IND_REEMPLAZO_LABORAL | Índice de reemplazo de la fuerza laboral | Laboral | P(15-24) / P(55-64) × 100 | por 100 | Pipeline |  | True |
| EDAD_MEDIANA | Edad mediana | Envejecimiento | dato publicado | años | KOSIS DT_1BPA002 |  | False |
| POB_CENSO_TOTAL | Población censada (registros) | Estructura | dato publicado | personas | KOSIS DT_1IN1502 |  | False |
| POB_EXTRANJERA | Población extranjera residente | Migración | dato publicado | personas | KOSIS DT_1IN1502 |  | False |
| PROP_EXTRANJEROS | Proporción de extranjeros | Migración | POB_EXTRANJERA / POB_CENSO_TOTAL × 100 | % | Pipeline |  | True |
| HOGARES | Hogares | Estructura | dato publicado | hogares | KOSIS DT_1IN1502 |  | False |
| POB_CENSO_HIST | Población censada (histórica) | Estructura | dato publicado | personas | KOSIS DT_1IN0001 |  | False |
| POB_15MAS | Población de 15 años y más (EAPS) | Laboral | dato publicado × 1.000 | personas | KOSIS DT_1DA7004S / DT_1DA7012S |  | False |
| POB_ACTIVA | Población económicamente activa | Laboral | dato publicado × 1.000 | personas | KOSIS DT_1DA7004S / DT_1DA7012S | OECD DF_SUMTAB | False |
| OCUPADOS | Ocupados | Laboral | dato publicado × 1.000 | personas | KOSIS DT_1DA7004S / DT_1DA7012S | OECD DF_SUMTAB | False |
| DESOCUPADOS | Desocupados | Laboral | dato publicado × 1.000 | personas | KOSIS DT_1DA7004S / DT_1DA7012S |  | False |
| INACTIVOS | Población económicamente inactiva | Laboral | dato publicado × 1.000 | personas | KOSIS DT_1DA7004S / DT_1DA7012S |  | False |
| TASA_PARTICIPACION | Tasa de participación laboral | Laboral | dato publicado (verificado con niveles) | % | KOSIS DT_1DA7004S / DT_1DA7012S | WB SL.TLF.CACT.ZS (modelado OIT) | False |
| TASA_DESEMPLEO | Tasa de desempleo | Laboral | dato publicado (verificado con niveles) | % | KOSIS DT_1DA7004S / DT_1DA7012S | OECD DF_SUMTAB | False |
| TASA_EMPLEO | Tasa de ocupación | Laboral | dato publicado | % | KOSIS DT_1DA7004S / DT_1DA7012S |  | False |
| TASA_EMPLEO_15_64 | Tasa de ocupación 15-64 | Laboral | dato publicado | % | KOSIS DT_1DA7004S |  | False |
| FUERZA_LABORAL_POTENCIAL | Fuerza laboral potencial (escenario) | Laboral | Σ P_proy(s;edad) × TP(s;edad;supuesto) | personas | Pipeline (escenario propio) | EAPS 2025 (calibración) | True |
| PIB_HORA | PIB por hora trabajada | Productividad | dato publicado | USD PPA constantes | OECD DF_PDB | WB SL.GDP.PCAP.EM.KD (por ocupado) | False |
| PIB_POR_OCUPADO | PIB por ocupado | Productividad | dato publicado | USD PPA 2021 | World Bank WDI |  | False |