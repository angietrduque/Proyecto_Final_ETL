# Reporte de calidad del pipeline

Generado automáticamente por `main.py` · ejecución `20261006_200124_521c9a` ·
2026-10-06 20:02 · versión del pipeline 2.0.0

> Este archivo se sobrescribe en cada ejecución. Las tablas completas están en `data/ctl/*.parquet`,
> `data/gold/kpi_*.csv` y en la base SQL (`ctl_*`, `gold_kpi_*`).

## 1. OKR (O1-O3 problema de estudio · O4 habilitador de calidad)

| objetivo_cod | kr | kpi | meta | valor | cumple | interpretacion |
|---|---|---|---|---|---|---|
| O1 | KR1.1 | Serie demográfica y laboral integrada: nacional 1970-2025 y 17 si-do 2000-2025 | completitud ≥ 95 % nacional y ≥ 90 % regional | 96.2 % / 97.0 % | ✅ | celdas con dato / esperadas (Sejong desde 2012; EAPS Sejong desde 2017) |
| O1 | KR1.2 | Indicadores de natalidad y envejecimiento con fórmula única, validados contra KOSTAT | 6 indicadores · diferencia ≤ 1 % | 6 · 0.37 % | ✅ | dependencia (juvenil, vejez, total), índice de envejecimiento, % 15-64, % 65+ vs resumen oficial 2022-2072 |
| O1 | KR1.3 | Brecha de Corea frente a la OCDE cuantificada | ≥ 5 países de comparación | 8 + Corea | ✅ | TFR Corea 0,80 vs OCDE 1,48: 46 % por debajo |
| O2 | KR2.1 | Escenarios oficiales KOSTAT integrados sin modificar y separados del histórico | 100 % de registros con escenario y edición | 29 escenarios · 100 % | ✅ | 2023-2072 nacional y 2023-2052 provincial; el histórico no contiene proyecciones |
| O2 | KR2.2 | Escenarios propios de fuerza laboral con supuestos explícitos, escala ajustada y sensibilidad | 4 supuestos · diferencia sin ajuste ≤ ±5 % · sensibilidad publicada | 4 · sin ajuste +1.51 % · 8 variantes | ✅ | A constante · B tendencia 2015-2025 · C convergencia OCDE · D cierre 50 % brecha de género; el factor de cobertura EAPS lleva 2025 a la PEA observada (ajuste de escala, no validación) |
| O2 | KR2.3 | Pérdida de población en edad de trabajar y de fuerza laboral a 2050 cuantificada con rango | rango en todos los escenarios | 15-64: -36,4 % a -27,4 % | ✅ | fuerza laboral potencial (medio): A -11,7 %; B -4,9 %; C -11,8 %; D -5,7 % |
| O3 | KR3.1 | Riesgo demográfico-laboral medido para todas las regiones | 17 de 17 si-do | 17 de 17 · 6 en riesgo alto | ✅ | índice de 6 componentes (inferencia propia, ponderación igual); top 5 en los 7 esquemas de sensibilidad: Busan, Gyeongsangbuk-do |
| O3 | KR3.2 | Palancas de política cuantificadas (natalidad, migración, participación, brecha de género) | 4 de 4 palancas | 4 de 4 | ✅ | efecto a 2050: fecundidad alta +1,4 pp en Pob 15-64 · migración alta vs cero +7,7 pp · participación B vs A +6,8 pp · brecha de género D vs A +6,0 pp en fuerza laboral |
| O3 | KR3.3 | Tablero de Power BI que responde las 10 preguntas de negocio | 10 de 10 preguntas | 10 de 10 · 8 páginas | ✅ | ../powerbi/ETL_Corea_Grupo6.pbix (portada, natalidad, envejecimiento, fuerza laboral, regiones, OCDE, calidad) |
| O4 | KR4.1 | Registros válidos tras las reglas de calidad | ≥ 98.0 % | 99.96 % | ✅ | registros que pasan todas las reglas / evaluados |
| O4 | KR4.2 | Rechazos con motivo trazado | ≤ 2.0 % y 100 % trazados | 0.04 % · 100 % | ✅ | reemplaza el KPI «0 % inconsistencias» (retroalimentación) |
| O4 | KR4.3 | Coherencia entre fuente maestra y fuentes de contraste | ≥ 90.0 % de pares ≤ ±3 % | 100.0 % | ✅ | 8950 pares; externos (WB/OECD) 100 %, dif. máx 2.8 % |
| O4 | KR4.4 | Fuentes institucionales integradas y ejecuciones sin fallo técnico | ≥ 3 fuentes · ≥ 95.0 % ejecuciones | 3 · 100 % | ✅ | KOSTAT/KOSIS, OECD, World Bank |

## 1b. KPIs de negocio (último valor, referencia y semáforo)

| codigo | eje | indicador | formula | valor_texto | unidad | anio | referencia | semaforo | tipo_dato |
|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | Natalidad | Tasa global de fecundidad | publicado por KOSTAT | 0,80 | hijos por mujer | 2025 | reemplazo 2,1 · OCDE 1,48 (2024) | Crítico | observado |
| KPI-02 | Natalidad | Variación de nacimientos desde 2000 | (N_t / N_2000 − 1) × 100 | -60,3 | % | 2025 | 0 % (nivel de 2000) | Crítico | calculado |
| KPI-03 | Natalidad | Crecimiento natural | nacimientos − defunciones | -108.627 | personas | 2025 | 0 (equilibrio) | Crítico | observado |
| KPI-04 | Envejecimiento | Esperanza de vida al nacer | publicado por KOSTAT | 83,7 | años | 2024 | OCDE 80,4 (2024) | Contexto | observado |
| KPI-05 | Envejecimiento | Población de 65 y más | P65+ / P × 100 | 20,3 | % | 2025 | ONU: ≥ 14 % envejecida · ≥ 20 % superenvejecida | Crítico | proyeccion_oficial |
| KPI-06 | Envejecimiento | Dependencia de vejez | P65+ / P15-64 × 100 | 29,3 | por 100 en edad de trabajar | 2025 | OCDE 29,5 (2025) | Crítico | proyeccion_oficial |
| KPI-07 | Fuerza laboral | Variación de la población 15-64 a 2050 | (P15-64_2050 / P15-64_2025 − 1) × 100 | -31,9 | % | 2050 | 0 % (sin pérdida) | Crítico | proyeccion_oficial |
| KPI-08 | Fuerza laboral | Índice de reemplazo laboral | P15-24 / P55-64 × 100 | 58 | jóvenes por 100 próximos a retiro | 2025 | 100 (reemplazo completo) | Crítico | proyeccion_oficial |
| KPI-09 | Fuerza laboral | Tasa de participación laboral (15+) | PEA / P15+ × 100 | 64,7 | % | 2025 | OCDE 60,6 (2025, modelado OIT) | Normal | observado |
| KPI-10 | Fuerza laboral | Brecha de género en participación | TP hombres − TP mujeres | 15,8 | puntos porcentuales | 2025 | ≤ 10 pp | Alerta | calculado |
| KPI-11 | Fuerza laboral | Variación de la fuerza laboral potencial a 2050 | Σ P_proy × TP_supuesta; (2050/2025 − 1) × 100 | -11,7 | % | 2050 | 0 % (sin pérdida) | Crítico | escenario_propio |
| KPI-12 | Territorio | Si-do en riesgo demográfico-laboral alto | nº de si-do en el tercil superior del índice | 6 | de 17 si-do | 2025 | — | Alerta | inferencia_propia |
| KPI-13 | Contexto | Población extranjera residente | extranjeros / población censada × 100 | 4,1 | % | 2025 | — | Contexto | calculado |
| KPI-14 | Contexto | PIB por hora trabajada | publicado por la OCDE | 53,4 | USD PPA constantes | 2025 | — | Contexto | observado |

## 2. Bitácora de cargas Bronze

| fuente | dataset | estado | filas | mensaje |
|---|---|---|---|---|
| KOSIS | vitales_nacional | exito | 16 |  |
| KOSIS | vitales_nacional | duplicado | 16 | contenido idéntico a Vital_Statistics_of_Korea_20261002100432.xlsx: no se ingiere dos veces |
| KOSIS | vitales_nacional_repo | exito | 16 |  |
| KOSIS | vitales_sido | exito | 19 |  |
| KOSIS | vitales_sigungu | exito | 19 |  |
| KOSIS | vitales_sido_mensual | exito | 19 |  |
| KOSIS | nacimientos_sexo | exito | 54 |  |
| KOSIS | nacimientos_sexo | duplicado | 54 | contenido idéntico a Live_Births_and_Deaths_by_administrative_districts_20261003100249.xlsx: no se ingiere dos veces |
| KOSIS | tfr_sido | exito | 18 |  |
| KOSIS | eaps_sido | exito | 19 |  |
| KOSIS | eaps_sexo_edad | exito | 30 |  |
| KOSIS | poblacion_nacional | exito | 69 |  |
| KOSIS | poblacion_sido | exito | 1242 |  |
| KOSIS | proyeccion_escenarios | exito | 1848 |  |
| KOSIS | proyeccion_resumen | exito | 21 |  |
| KOSIS | censo_registros | exito | 6580 |  |
| KOSIS | censo_historico | exito | 2632 |  |
| WB | SP.DYN.TFRT.IN | exito | 234 |  |
| WB | SP.POP.65UP.TO.ZS | exito | 234 |  |
| WB | SP.POP.1564.TO | exito | 234 |  |
| WB | SP.POP.TOTL | exito | 234 |  |
| WB | SP.POP.0014.TO | exito | 234 |  |
| WB | SP.POP.65UP.TO | exito | 234 |  |
| WB | SP.POP.DPND.OL | exito | 234 |  |
| WB | SL.TLF.CACT.ZS | exito | 234 |  |
| WB | SP.DYN.LE00.IN | exito | 234 |  |
| WB | SL.GDP.PCAP.EM.KD | exito | 234 |  |
| OECD | productividad | exito | 208 |  |
| OECD | fuerza_laboral | exito | 4282 |  |
| OECD | fecundidad | exito | 1381 |  |
| OECD | participacion_edad_sexo | exito | 612 |  |
| UNWPP | poblacion_edad_sexo | omitido |  | UNWPP_API_TOKEN no está definido en .env (token gratuito en https://population.un.org/dataportalapi/token/index.html) |

## 3. Calidad por dataset (reglas de aceptación)

| dataset | registros_evaluados | registros_validos | registros_rechazados | tasa_validos_pct | tasa_rechazo_pct | rechazos_trazados_pct |
|---|---|---|---|---|---|---|
| OECD/fecundidad/NACIMIENTOS | 176 | 176 | 0 | 100.00 | 0.00 | 100.00 |
| OECD/fecundidad/TFR | 173 | 173 | 0 | 100.00 | 0.00 | 100.00 |
| OECD/fuerza_laboral/OCUPADOS | 181 | 181 | 0 | 100.00 | 0.00 | 100.00 |
| OECD/fuerza_laboral/POB_ACTIVA | 181 | 181 | 0 | 100.00 | 0.00 | 100.00 |
| OECD/fuerza_laboral/TASA_DESEMPLEO | 181 | 181 | 0 | 100.00 | 0.00 | 100.00 |
| OECD/participacion_edad_sexo/TASA_PARTICIPACION | 84 | 84 | 0 | 100.00 | 0.00 | 100.00 |
| OECD/productividad/PIB_HORA | 182 | 182 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SL.GDP.PCAP.EM.KD | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SL.TLF.CACT.ZS | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.DYN.LE00.IN | 225 | 225 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.DYN.TFRT.IN | 225 | 225 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.POP.0014.TO | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.POP.1564.TO | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.POP.65UP.TO | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.POP.65UP.TO.ZS | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.POP.DPND.OL | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| WB/SP.POP.TOTL | 234 | 234 | 0 | 100.00 | 0.00 | 100.00 |
| censo_historico | 11703 | 11703 | 0 | 100.00 | 0.00 | 100.00 |
| censo_registros | 1330 | 1260 | 70 | 94.74 | 5.26 | 100.00 |
| eaps_sexo_edad | 6240 | 6240 | 0 | 100.00 | 0.00 | 100.00 |
| eaps_sido | 4068 | 4059 | 9 | 99.78 | 0.22 | 100.00 |
| nacimientos_sexo | 3492 | 3492 | 0 | 100.00 | 0.00 | 100.00 |
| poblacion_nacional | 4161 | 4161 | 0 | 100.00 | 0.00 | 100.00 |
| poblacion_sido | 53694 | 53694 | 0 | 100.00 | 0.00 | 100.00 |
| proyeccion_escenarios | 81396 | 81396 | 0 | 100.00 | 0.00 | 100.00 |
| proyeccion_resumen | 561 | 561 | 0 | 100.00 | 0.00 | 100.00 |
| tfr_sido | 3648 | 3648 | 0 | 100.00 | 0.00 | 100.00 |
| vitales_nacional | 862 | 862 | 0 | 100.00 | 0.00 | 100.00 |
| vitales_nacional_repo | 104 | 104 | 0 | 100.00 | 0.00 | 100.00 |
| vitales_sido | 5980 | 5980 | 0 | 100.00 | 0.00 | 100.00 |
| vitales_sido_mensual | 1371 | 1368 | 3 | 99.78 | 0.22 | 100.00 |
| vitales_sigungu | 4560 | 4560 | 0 | 100.00 | 0.00 | 100.00 |

## 4. Rechazos (motivo trazado)

| dataset | regla | motivo | registros |
|---|---|---|---|
| censo_registros | duplicado_clave | clave natural repetida (anio + cod_territorio + cod_sexo + cod_edad + cod_indicador); se conserva la primera aparición | 70 |
| eaps_sido | integridad_cod_territorio | código fuera de la dimensión cod_territorio (__RECHAZO__) | 9 |
| vitales_sido_mensual | integridad_cod_territorio | código fuera de la dimensión cod_territorio (__RECHAZO__) | 3 |

## 5. Reglas de consistencia y conciliación

| dataset | regla | evaluados | afectados | resultado | detalle |
|---|---|---|---|---|---|
| vitales_sigungu | suma_sido_igual_nacional | 52 | 0 | PASA | Σ 17 si-do (DT_1B8000I) = nacional (DT_1B8000F); tolerancia ±0.5 %; dif. máx 0.000 % |
| nacimientos_sexo | hombres_mas_mujeres_igual_total | 1164 | 0 | PASA | H + M = T; tolerancia ±0.5 %; dif. máx 0.000 % |
| vitales_nacional | identidad_crecimiento_natural | 56 | 0 | PASA | crecimiento natural = nacimientos - defunciones; tolerancia ±0.5; dif. máx 0.0000 |
| poblacion_nacional | suma_edades_igual_total | 219 | 0 | PASA | Σ grupos quinquenales (85+ agregado) = total; tolerancia ±0.5 %; dif. máx 0.000 % |
| poblacion_nacional | hombres_mas_mujeres_igual_total | 1387 | 0 | PASA | H + M = T; tolerancia ±0.5 %; dif. máx 0.000 % |
| poblacion_sido | suma_edades_igual_total | 2826 | 0 | PASA | Σ grupos quinquenales (85+ agregado) = total; tolerancia ±0.5 %; dif. máx 0.000 % |
| poblacion_sido | hombres_mas_mujeres_igual_total | 17898 | 0 | PASA | H + M = T; tolerancia ±0.5 %; dif. máx 0.000 % |
| proyeccion_escenarios | suma_edades_igual_total | 4284 | 0 | PASA | Σ grupos quinquenales (85+ agregado) = total; tolerancia ±0.5 %; dif. máx 0.000 % |
| proyeccion_escenarios | hombres_mas_mujeres_igual_total | 27132 | 0 | PASA | H + M = T; tolerancia ±0.5 %; dif. máx 0.000 % |
| poblacion_sido | suma_sido_igual_nacional | 159 | 0 | PASA | Σ 17 si-do = Whole country; tolerancia ±0.5 %; dif. máx 0.000 % |
| poblacion_sido | nacional_igual_entre_tablas | 159 | 0 | PASA | Whole country de DT_1BPB001 = total de DT_1BPA001; tolerancia ±0.5 %; dif. máx 0.0000 |
| proyeccion_escenarios | anio_base_comun | 28 | 0 | PASA | población 2022 idéntica en los 28 escenarios (51,672,569) |
| eaps_sido | activos_igual_ocupados_mas_desocupados | 451 | 0 | PASA | PEA = ocupados + desocupados (personas; niveles redondeados a miles); tolerancia ±1500.0; dif. máx 1000.0000 |
| eaps_sido | pob15_igual_activos_mas_inactivos | 451 | 0 | PASA | Pob 15+ = PEA + inactivos (personas; niveles redondeados a miles); tolerancia ±1500.0; dif. máx 1000.0000 |
| eaps_sido | tasa_participacion_recalculada | 451 | 0 | PASA | TP publicada vs PEA / Pob15+ × 100 (pp); tolerancia error máximo de redondeo; dif. máx 0.1613 |
| eaps_sido | tasa_desempleo_recalculada | 451 | 0 | PASA | TD publicada vs desocupados / PEA × 100 (pp); tolerancia error máximo de redondeo; dif. máx 0.3316 |
| eaps_sexo_edad | activos_igual_ocupados_mas_desocupados | 780 | 0 | PASA | PEA = ocupados + desocupados (personas; niveles redondeados a miles); tolerancia ±1500.0; dif. máx 1000.0000 |
| eaps_sexo_edad | pob15_igual_activos_mas_inactivos | 780 | 0 | PASA | Pob 15+ = PEA + inactivos (personas; niveles redondeados a miles); tolerancia ±1500.0; dif. máx 1000.0000 |
| eaps_sexo_edad | tasa_participacion_recalculada | 780 | 0 | PASA | TP publicada vs PEA / Pob15+ × 100 (pp); tolerancia error máximo de redondeo; dif. máx 0.0894 |
| eaps_sexo_edad | tasa_desempleo_recalculada | 780 | 0 | PASA | TD publicada vs desocupados / PEA × 100 (pp); tolerancia error máximo de redondeo; dif. máx 0.5000 |
| eaps_sido | suma_sido_igual_nacional | 78 | 0 | PASA | Σ si-do = total nacional (EAPS); tolerancia ±0.5 %; dif. máx 0.013 % |
| censo_registros | suma_sido_igual_nacional | 20 | 0 | PASA | Σ si-do = nacional (censo de registros); tolerancia ±0.5 %; dif. máx 0.000 % |
| conciliacion | maestra_vs_contraste | 8950 | 2 | PASA | 100.0 % de 8950 pares año-indicador dentro de ±3.0 % (meta ≥ 90.0 %) |
| conciliacion | CRECIMIENTO_NATURAL vs KOSIS | 825 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | DEFUNCIONES vs KOSIS | 1281 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | DESOCUPADOS vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | DIVORCIOS vs KOSIS | 411 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | ESPERANZA_VIDA vs WB | 25 | 0 | PASA | dif. máx 0.17 %; mediana 0.09 % |
| conciliacion | INACTIVOS vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | MATRIMONIOS vs KOSIS | 411 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | NACIMIENTOS vs KOSIS | 1281 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | NACIMIENTOS vs OECD | 25 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | OCUPADOS vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | OCUPADOS vs OECD | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | POBLACION vs KOSIS | 1315 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | POBLACION vs WB | 92 | 0 | PASA | dif. máx 2.77 %; mediana 0.33 % |
| conciliacion | POB_15MAS vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | POB_ACTIVA vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | POB_ACTIVA vs OECD | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_BRUTA_MORTALIDAD vs KOSIS | 411 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_BRUTA_NATALIDAD vs KOSIS | 411 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_CRECIMIENTO_NATURAL vs KOSIS | 411 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_DESEMPLEO vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_DESEMPLEO vs OECD | 26 | 0 | PASA | dif. máx 1.82 %; mediana 0.63 % |
| conciliacion | TASA_DIVORCIALIDAD vs KOSIS | 411 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_EMPLEO vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_NUPCIALIDAD vs KOSIS | 411 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TASA_PARTICIPACION vs KOSIS | 26 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TFR vs KOSIS | 893 | 0 | PASA | dif. máx 0.64 %; mediana 0.00 % |
| conciliacion | TFR vs OECD | 25 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| conciliacion | TFR vs WB | 25 | 0 | PASA | dif. máx 0.00 %; mediana 0.00 % |
| gold.fact_indicador_proyeccion | escenario_y_edicion_identificados | 188160 | 0 | PASA | KR3: 100 % de registros de proyección con edición y escenario |
| gold.fact_fuerza_laboral_escenario | ajuste_cobertura_eaps | 1 | 0 | PASA | PEA observada EAPS 2025 = 29,599,000; modelo sin ajuste 30,046,905 (dif. +1.51 %); con factor de cobertura 29,606,821 (dif. +0.03 %): la diferencia sin ajuste es de universo (población total vs civil no institucional), no un error del modelo |
| gold.fact_fuerza_laboral_escenario | supuesto_D_no_baja_tasas | 17400 | 0 | PASA | cerrar la brecha de género nunca reduce una tasa de participación |
| gold.fact_riesgo_sensibilidad | ranking_robusto | 7 | 0 | PASA | si-do en el top 5 en todos los esquemas: Busan, Gyeongsangbuk-do |
| gold.formulas | DEP_JUVENIL vs proyeccion_resumen | 51 | 0 | PASA | 51 años; dif. máx 0.372 %; mediana 0.182 % |
| gold.formulas | DEP_TOTAL vs proyeccion_resumen | 51 | 0 | PASA | 51 años; dif. máx 0.102 %; mediana 0.035 % |
| gold.formulas | DEP_VEJEZ vs WB/SP.POP.DPND.OL | 26 | 1 | FALLA | 26 años; dif. máx 3.527 %; mediana 1.201 % |
| gold.formulas | DEP_VEJEZ vs proyeccion_resumen | 51 | 0 | PASA | 51 años; dif. máx 0.175 %; mediana 0.034 % |
| gold.formulas | IND_ENVEJECIMIENTO vs proyeccion_resumen | 51 | 0 | PASA | 51 años; dif. máx 0.021 %; mediana 0.005 % |
| gold.formulas | PROP_15_64 vs proyeccion_resumen | 51 | 0 | PASA | 51 años; dif. máx 0.097 %; mediana 0.041 % |
| gold.formulas | PROP_65MAS vs WB/SP.POP.65UP.TO.ZS | 26 | 0 | PASA | 26 años; dif. máx 2.771 %; mediana 0.862 % |
| gold.formulas | PROP_65MAS vs proyeccion_resumen | 51 | 0 | PASA | 51 años; dif. máx 0.256 %; mediana 0.076 % |

## 6. Completitud 2000-2025 (núcleo de indicadores)

| nivel | cod_indicador | esperadas | observadas | con_proyeccion | completitud_% | con_proyeccion_% |
|---|---|---|---|---|---|---|
| nacional | DEFUNCIONES | 26 | 26 | 26 | 100.00 | 100.00 |
| nacional | DEP_VEJEZ | 26 | 23 | 26 | 88.46 | 100.00 |
| nacional | ESPERANZA_VIDA | 26 | 25 | 25 | 96.15 | 96.15 |
| nacional | NACIMIENTOS | 26 | 26 | 26 | 100.00 | 100.00 |
| nacional | POBLACION | 26 | 23 | 26 | 88.46 | 100.00 |
| nacional | POB_ACTIVA | 26 | 26 | 26 | 100.00 | 100.00 |
| nacional | PROP_65MAS | 26 | 23 | 26 | 88.46 | 100.00 |
| nacional | TASA_DESEMPLEO | 26 | 26 | 26 | 100.00 | 100.00 |
| nacional | TASA_PARTICIPACION | 26 | 26 | 26 | 100.00 | 100.00 |
| nacional | TFR | 26 | 26 | 26 | 100.00 | 100.00 |
| regional | NACIMIENTOS | 430 | 430 | 430 | 100.00 | 100.00 |
| regional | POBLACION | 430 | 379 | 430 | 88.14 | 100.00 |
| regional | TASA_PARTICIPACION | 425 | 425 | 425 | 100.00 | 100.00 |
| regional | TFR | 430 | 430 | 430 | 100.00 | 100.00 |

## 7. Conteo de registros antes y después de cada transformación

| capa | dataset | paso | filas_entrada | filas_salida | diferencia | nota |
|---|---|---|---|---|---|---|
| silver | vitales_nacional | formato largo (melt) | 16 | 896 | 880 | 56 columnas de periodo/ítem |
| silver | vitales_nacional | descartar columnas no anuales (meses) y columnas vacías | 896 | 896 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | vitales_nacional | selección de variables mapeadas (items_kosis.csv) | 896 | 896 | 0 | todas las variables mapeadas |
| silver | vitales_nacional | excluir unidades territoriales fuera de alcance | 896 | 896 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | vitales_nacional | excluir agregados de edad redundantes (80+) | 896 | 896 | 0 |  |
| silver | vitales_nacional | separar celdas sin dato (no se imputan) | 896 | 862 | -34 | 34 celdas vacías o '-' |
| silver | vitales_nacional | reglas de aceptación | 862 | 862 | 0 | 0 rechazados (0.00 %) |
| silver | vitales_nacional_repo | formato largo (melt) | 16 | 416 | 400 | 26 columnas de periodo/ítem |
| silver | vitales_nacional_repo | descartar columnas no anuales (meses) y columnas vacías | 416 | 416 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | vitales_nacional_repo | selección de variables mapeadas (items_kosis.csv) | 416 | 104 | -312 | ítems no usados: Crude birth rate(per 1,000 population) (26); Crude death rate(per 1,000 population) (26); Natural increase rate(per 1,000 population) (26); Masculinity of birth(persons) (26); Infant mortality rate(per 1,000 live births) (26); Marriages(cases) (26); Crude marriage rate(per 1,000 population) (26); Divorces(cases) (26) |
| silver | vitales_nacional_repo | excluir unidades territoriales fuera de alcance | 104 | 104 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | vitales_nacional_repo | excluir agregados de edad redundantes (80+) | 104 | 104 | 0 |  |
| silver | vitales_nacional_repo | separar celdas sin dato (no se imputan) | 104 | 104 | 0 | 0 celdas vacías o '-' |
| silver | vitales_nacional_repo | reglas de aceptación | 104 | 104 | 0 | 0 rechazados (0.00 %) |
| silver | vitales_sigungu | formato largo (melt) | 19 | 4940 | 4921 | 260 columnas de periodo/ítem |
| silver | vitales_sigungu | descartar columnas no anuales (meses) y columnas vacías | 4940 | 4940 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | vitales_sigungu | selección de variables mapeadas (items_kosis.csv) | 4940 | 4940 | 0 | todas las variables mapeadas |
| silver | vitales_sigungu | excluir unidades territoriales fuera de alcance | 4940 | 4680 | -260 | 1 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | vitales_sigungu | excluir agregados de edad redundantes (80+) | 4680 | 4680 | 0 |  |
| silver | vitales_sigungu | separar celdas sin dato (no se imputan) | 4680 | 4560 | -120 | 120 celdas vacías o '-' |
| silver | vitales_sigungu | reglas de aceptación | 4560 | 4560 | 0 | 0 rechazados (0.00 %) |
| silver | vitales_sido | formato largo (melt) | 19 | 6631 | 6612 | 349 columnas de periodo/ítem |
| silver | vitales_sido | descartar columnas no anuales (meses) y columnas vacías | 6631 | 6631 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | vitales_sido | selección de variables mapeadas (items_kosis.csv) | 6631 | 6631 | 0 | todas las variables mapeadas |
| silver | vitales_sido | excluir unidades territoriales fuera de alcance | 6631 | 6282 | -349 | 1 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | vitales_sido | excluir agregados de edad redundantes (80+) | 6282 | 6282 | 0 |  |
| silver | vitales_sido | separar celdas sin dato (no se imputan) | 6282 | 5980 | -302 | 302 celdas vacías o '-' |
| silver | vitales_sido | reglas de aceptación | 5980 | 5980 | 0 | 0 rechazados (0.00 %) |
| silver | vitales_sido_mensual | formato largo (melt) | 19 | 8037 | 8018 | 423 columnas de periodo/ítem |
| silver | vitales_sido_mensual | descartar columnas no anuales (meses) y columnas vacías | 8037 | 7410 | -627 | 627 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | vitales_sido_mensual | selección de variables mapeadas (items_kosis.csv) | 7410 | 1482 | -5928 | ítems no usados: Crude Birth Rate(per 1000 population) (494); Crude Dearh Rate(per 1000 population) (494); Natural increase(persons) (494); Natural increase rate(per 1000 population) (494); Marriages(cases) (494); Crude Marrige Rate(per 1000 population) (494); Divorces(cases) (494); Crude Divorce Rate(per 1000 population) (494) |
| silver | vitales_sido_mensual | excluir unidades territoriales fuera de alcance | 1482 | 1482 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | vitales_sido_mensual | excluir agregados de edad redundantes (80+) | 1482 | 1482 | 0 |  |
| silver | vitales_sido_mensual | separar celdas sin dato (no se imputan) | 1482 | 1371 | -111 | 111 celdas vacías o '-' |
| silver | vitales_sido_mensual | reglas de aceptación | 1371 | 1368 | -3 | 3 rechazados (0.22 %) |
| silver | nacimientos_sexo | relleno hacia abajo del si-do (celdas combinadas en la descarga) | 54 | 54 | 0 |  |
| silver | nacimientos_sexo | formato largo (melt) | 54 | 5940 | 5886 | 110 columnas de periodo/ítem |
| silver | nacimientos_sexo | descartar columnas no anuales (meses) y columnas vacías | 5940 | 5940 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | nacimientos_sexo | selección de variables mapeadas (items_kosis.csv) | 5940 | 3564 | -2376 | ítems no usados: Marriages(cases) (1188); Divorces(cases) (1188) |
| silver | nacimientos_sexo | excluir unidades territoriales fuera de alcance | 3564 | 3564 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | nacimientos_sexo | excluir agregados de edad redundantes (80+) | 3564 | 3564 | 0 |  |
| silver | nacimientos_sexo | separar celdas sin dato (no se imputan) | 3564 | 3492 | -72 | 72 celdas vacías o '-' |
| silver | nacimientos_sexo | reglas de aceptación | 3492 | 3492 | 0 | 0 rechazados (0.00 %) |
| silver | tfr_sido | formato largo (melt) | 18 | 3744 | 3726 | 208 columnas de periodo/ítem |
| silver | tfr_sido | descartar columnas no anuales (meses) y columnas vacías | 3744 | 3744 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | tfr_sido | selección de variables mapeadas (items_kosis.csv) | 3744 | 3744 | 0 | todas las variables mapeadas |
| silver | tfr_sido | excluir unidades territoriales fuera de alcance | 3744 | 3744 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | tfr_sido | excluir agregados de edad redundantes (80+) | 3744 | 3744 | 0 |  |
| silver | tfr_sido | separar celdas sin dato (no se imputan) | 3744 | 3648 | -96 | 96 celdas vacías o '-' |
| silver | tfr_sido | reglas de aceptación | 3648 | 3648 | 0 | 0 rechazados (0.00 %) |
| silver | eaps_sido | formato largo (melt) | 19 | 6669 | 6650 | 351 columnas de periodo/ítem |
| silver | eaps_sido | descartar columnas no anuales (meses) y columnas vacías | 6669 | 4446 | -2223 | 2223 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | eaps_sido | selección de variables mapeadas (items_kosis.csv) | 4446 | 4446 | 0 | todas las variables mapeadas |
| silver | eaps_sido | excluir unidades territoriales fuera de alcance | 4446 | 4446 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | eaps_sido | excluir agregados de edad redundantes (80+) | 4446 | 4446 | 0 |  |
| silver | eaps_sido | separar celdas sin dato (no se imputan) | 4446 | 4068 | -378 | 378 celdas vacías o '-' |
| silver | eaps_sido | reglas de aceptación | 4068 | 4059 | -9 | 9 rechazados (0.22 %) |
| silver | eaps_sexo_edad | formato largo (melt) | 30 | 6960 | 6930 | 232 columnas de periodo/ítem |
| silver | eaps_sexo_edad | descartar columnas no anuales (meses) y columnas vacías | 6960 | 6240 | -720 | 720 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | eaps_sexo_edad | selección de variables mapeadas (items_kosis.csv) | 6240 | 6240 | 0 | todas las variables mapeadas |
| silver | eaps_sexo_edad | excluir unidades territoriales fuera de alcance | 6240 | 6240 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | eaps_sexo_edad | excluir agregados de edad redundantes (80+) | 6240 | 6240 | 0 |  |
| silver | eaps_sexo_edad | separar celdas sin dato (no se imputan) | 6240 | 6240 | 0 | 0 celdas vacías o '-' |
| silver | eaps_sexo_edad | reglas de aceptación | 6240 | 6240 | 0 | 0 rechazados (0.00 %) |
| silver | poblacion_nacional | formato largo (melt) | 69 | 5037 | 4968 | 73 columnas de periodo/ítem |
| silver | poblacion_nacional | descartar columnas no anuales (meses) y columnas vacías | 5037 | 5037 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | poblacion_nacional | selección de variables mapeadas (items_kosis.csv) | 5037 | 5037 | 0 | todas las variables mapeadas |
| silver | poblacion_nacional | excluir unidades territoriales fuera de alcance | 5037 | 5037 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | poblacion_nacional | excluir agregados de edad redundantes (80+) | 5037 | 4818 | -219 |  |
| silver | poblacion_nacional | separar celdas sin dato (no se imputan) | 5037 | 4818 | -219 | 0 celdas vacías o '-' |
| silver | poblacion_nacional | agregar 85-89, 90-94, 95-99 y 100+ en 85+ | 4818 | 4161 | -657 |  |
| silver | poblacion_nacional | reglas de aceptación | 4161 | 4161 | 0 | 0 rechazados (0.00 %) |
| silver | poblacion_sido | formato largo (melt) | 1242 | 67068 | 65826 | 54 columnas de periodo/ítem |
| silver | poblacion_sido | descartar columnas no anuales (meses) y columnas vacías | 67068 | 65826 | -1242 | 0 celdas mensuales/fuera de periodo; 1242 de columna vacía |
| silver | poblacion_sido | selección de variables mapeadas (items_kosis.csv) | 65826 | 65826 | 0 | todas las variables mapeadas |
| silver | poblacion_sido | excluir unidades territoriales fuera de alcance | 65826 | 65826 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | poblacion_sido | excluir agregados de edad redundantes (80+) | 65826 | 62964 | -2862 |  |
| silver | poblacion_sido | separar celdas sin dato (no se imputan) | 65826 | 62172 | -3654 | 792 celdas vacías o '-' |
| silver | poblacion_sido | agregar 85-89, 90-94, 95-99 y 100+ en 85+ | 62172 | 53694 | -8478 |  |
| silver | poblacion_sido | reglas de aceptación | 53694 | 53694 | 0 | 0 rechazados (0.00 %) |
| silver | proyeccion_escenarios | formato largo (melt) | 1848 | 96096 | 94248 | 52 columnas de periodo/ítem |
| silver | proyeccion_escenarios | descartar columnas no anuales (meses) y columnas vacías | 96096 | 94248 | -1848 | 0 celdas mensuales/fuera de periodo; 1848 de columna vacía |
| silver | proyeccion_escenarios | selección de variables mapeadas (items_kosis.csv) | 94248 | 94248 | 0 | todas las variables mapeadas |
| silver | proyeccion_escenarios | excluir unidades territoriales fuera de alcance | 94248 | 94248 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | proyeccion_escenarios | excluir agregados de edad redundantes (80+) | 94248 | 94248 | 0 |  |
| silver | proyeccion_escenarios | separar celdas sin dato (no se imputan) | 94248 | 94248 | 0 | 0 celdas vacías o '-' |
| silver | proyeccion_escenarios | agregar 85-89, 90-94, 95-99 y 100+ en 85+ | 94248 | 81396 | -12852 |  |
| silver | proyeccion_escenarios | reglas de aceptación | 81396 | 81396 | 0 | 0 rechazados (0.00 %) |
| silver | proyeccion_resumen | formato largo (melt) | 21 | 1071 | 1050 | 51 columnas de periodo/ítem |
| silver | proyeccion_resumen | descartar columnas no anuales (meses) y columnas vacías | 1071 | 1071 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | proyeccion_resumen | selección de variables mapeadas (items_kosis.csv) | 1071 | 561 | -510 | ítems no usados: 남자(명) (51); 여자(명) (51); 성비(여자1백명당) (51); 인구성장률 (51); - 구성비(%): 0-14세 (51); 중위연령(세)-남자 (51); 중위연령(세)-여자 (51); 평균연령(세) (51) |
| silver | proyeccion_resumen | excluir unidades territoriales fuera de alcance | 561 | 561 | 0 | 0 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | proyeccion_resumen | excluir agregados de edad redundantes (80+) | 561 | 561 | 0 |  |
| silver | proyeccion_resumen | separar celdas sin dato (no se imputan) | 561 | 561 | 0 | 0 celdas vacías o '-' |
| silver | proyeccion_resumen | reglas de aceptación | 561 | 561 | 0 | 0 rechazados (0.00 %) |
| silver | censo_registros | formato largo (melt) | 6580 | 65800 | 59220 | 10 columnas de periodo/ítem |
| silver | censo_registros | descartar columnas no anuales (meses) y columnas vacías | 65800 | 65800 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | censo_registros | selección de variables mapeadas (items_kosis.csv) | 65800 | 23030 | -42770 | ítems no usados: Korean - total[Person] (3290); Korean - male[Person] (3290); Korean - Female[Person] (3290); Type of occupancy[households] (3290); Institutional households[households] (3290); Foreigner household[households] (3290); Housing units-Total[Housing] (3290); Detached dwelling[Housing] (3290) |
| silver | censo_registros | excluir unidades territoriales fuera de alcance | 23030 | 1330 | -21700 | 241 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | censo_registros | excluir agregados de edad redundantes (80+) | 1330 | 1330 | 0 |  |
| silver | censo_registros | separar celdas sin dato (no se imputan) | 1330 | 1330 | 0 | 0 celdas vacías o '-' |
| silver | censo_registros | reglas de aceptación | 1330 | 1260 | -70 | 70 rechazados (5.26 %) |
| silver | censo_historico | formato largo (melt) | 2632 | 47376 | 44744 | 18 columnas de periodo/ítem |
| silver | censo_historico | descartar columnas no anuales (meses) y columnas vacías | 47376 | 47376 | 0 | 0 celdas mensuales/fuera de periodo; 0 de columna vacía |
| silver | censo_historico | selección de variables mapeadas (items_kosis.csv) | 47376 | 35532 | -11844 | ítems no usados: Sex ratio (11844) |
| silver | censo_historico | excluir unidades territoriales fuera de alcance | 35532 | 24030 | -11502 | 10 etiquetas fuera de alcance (Abroad, si-gun-gu, áreas urbanas/rurales, provincias pre-1945) |
| silver | censo_historico | excluir agregados de edad redundantes (80+) | 24030 | 20196 | -3834 |  |
| silver | censo_historico | separar celdas sin dato (no se imputan) | 24030 | 11703 | -12327 | 8493 celdas vacías o '-' |
| silver | censo_historico | reglas de aceptación | 11703 | 11703 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.DYN.TFRT.IN | descartar años sin dato publicado | 234 | 225 | -9 | la API devuelve null en años no publicados |
| silver | WB/SP.DYN.TFRT.IN | reglas de aceptación | 225 | 225 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.POP.65UP.TO.ZS | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SP.POP.65UP.TO.ZS | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.POP.1564.TO | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SP.POP.1564.TO | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.POP.TOTL | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SP.POP.TOTL | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.POP.0014.TO | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SP.POP.0014.TO | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.POP.65UP.TO | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SP.POP.65UP.TO | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.POP.DPND.OL | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SP.POP.DPND.OL | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SL.TLF.CACT.ZS | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SL.TLF.CACT.ZS | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SP.DYN.LE00.IN | descartar años sin dato publicado | 234 | 225 | -9 | la API devuelve null en años no publicados |
| silver | WB/SP.DYN.LE00.IN | reglas de aceptación | 225 | 225 | 0 | 0 rechazados (0.00 %) |
| silver | WB/SL.GDP.PCAP.EM.KD | descartar años sin dato publicado | 234 | 234 | 0 | la API devuelve null en años no publicados |
| silver | WB/SL.GDP.PCAP.EM.KD | reglas de aceptación | 234 | 234 | 0 | 0 rechazados (0.00 %) |
| silver | OECD/participacion_edad_sexo/TASA_PARTICIPACION | filtro de la serie relevante del dataflow | 612 | 84 | -528 |  |
| silver | OECD/participacion_edad_sexo/TASA_PARTICIPACION | reglas de aceptación | 84 | 84 | 0 | 0 rechazados (0.00 %) |
| silver | OECD/productividad/PIB_HORA | filtro de la serie relevante del dataflow | 208 | 182 | -26 |  |
| silver | OECD/productividad/PIB_HORA | reglas de aceptación | 182 | 182 | 0 | 0 rechazados (0.00 %) |
| silver | OECD/fuerza_laboral/POB_ACTIVA | filtro de la serie relevante del dataflow | 4282 | 181 | -4101 |  |
| silver | OECD/fuerza_laboral/POB_ACTIVA | reglas de aceptación | 181 | 181 | 0 | 0 rechazados (0.00 %) |
| silver | OECD/fuerza_laboral/OCUPADOS | filtro de la serie relevante del dataflow | 4282 | 181 | -4101 |  |
| silver | OECD/fuerza_laboral/OCUPADOS | reglas de aceptación | 181 | 181 | 0 | 0 rechazados (0.00 %) |
| silver | OECD/fuerza_laboral/TASA_DESEMPLEO | filtro de la serie relevante del dataflow | 4282 | 181 | -4101 |  |
| silver | OECD/fuerza_laboral/TASA_DESEMPLEO | reglas de aceptación | 181 | 181 | 0 | 0 rechazados (0.00 %) |
| silver | OECD/fecundidad/TFR | filtro de la serie relevante del dataflow | 1381 | 173 | -1208 |  |
| silver | OECD/fecundidad/TFR | reglas de aceptación | 173 | 173 | 0 | 0 rechazados (0.00 %) |
| silver | OECD/fecundidad/NACIMIENTOS | filtro de la serie relevante del dataflow | 1381 | 176 | -1205 |  |
| silver | OECD/fecundidad/NACIMIENTOS | reglas de aceptación | 176 | 176 | 0 | 0 rechazados (0.00 %) |
| silver | fact_historico | integración de tablas maestras (una por indicador) | 57054 | 57054 | 0 |  |
| silver | fact_proyeccion | integración de proyecciones oficiales (sin modificar valores) | 111720 | 111720 | 0 | el año base 2022 queda sólo en el histórico (tipo_dato = estimado) |
| gold | fact_indicador_historico | silver + derivados + agregado CNSJ | 57054 | 81087 | 24033 | 24033 filas calculadas |
| gold | fact_indicador_proyeccion | proyección + agregados + indicadores por escenario | 111720 | 188160 | 76440 |  |
| gold | fact_fuerza_laboral_escenario | población proyectada × cobertura EAPS × tasas supuestas (A, B, C, D) | 17400 | 69600 | 52200 |  |
