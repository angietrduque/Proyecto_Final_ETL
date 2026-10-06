# OKR y KPIs orientados al problema de estudio

**Pregunta central:** ¿Cómo impactará la disminución de la natalidad y el envejecimiento poblacional en la disponibilidad
futura de la fuerza laboral en Corea del Sur?

Los OKR se rediseñaron para medir **los resultados del estudio** (diagnóstico, impacto y decisión), no sólo la operación
del pipeline. La calidad del dato se conserva como **objetivo habilitador (O4)** porque es lo que pidió la
retroalimentación del profesor (tasas de válidos y de rechazo en lugar de "0 % inconsistencias"). Estructura inspirada en
la propuesta del grupo 5 (objetivos con resultados clave verificables + KPIs de dominio con una sola fórmula).

Valores de la última ejecución: `data/gold/kpi_okr.csv` y `data/gold/kpi_indicadores.csv` (se recalculan en cada corrida
de `python main.py`; también en `docs/reporte_calidad.md` y en el tablero de Power BI).

## 1. Objetivos y resultados clave

| Objetivo | KR | Resultado clave | Meta | Logrado | Evidencia (tabla Gold) |
|---|---|---|---|---|---|
| **O1 · Diagnóstico** — Diagnosticar la magnitud de la caída de la natalidad y del envejecimiento (1970-2025) | KR1.1 | Serie demográfica y laboral integrada (nacional 1970-2025, 17 si-do 2000-2025) | completitud ≥ 95 % nac. / ≥ 90 % reg. | 96,2 % / 97,0 % | kpi_completitud |
| | KR1.2 | Indicadores de natalidad y envejecimiento con fórmula única, validados contra KOSTAT | 6 indicadores, dif. ≤ 1 % | 6 · 0,37 % | fact_conciliacion |
| | KR1.3 | Brecha de Corea frente a la OCDE cuantificada | ≥ 5 países | 8 + Corea (TFR 46 % bajo la OCDE) | fact_comparacion_internacional |
| **O2 · Impacto laboral** — Dimensionar el impacto sobre la fuerza laboral futura (2025-2072), separando proyección oficial y escenarios propios | KR2.1 | Escenarios oficiales KOSTAT integrados sin modificar y separados del histórico | 100 % con escenario y edición | 29 escenarios · 100 % | fact_indicador_proyeccion |
| | KR2.2 | Escenarios propios de fuerza laboral con supuestos explícitos y calibrados | 3 supuestos · calibración ≤ ±5 % | 3 · +1,51 % | fact_fuerza_laboral_escenario |
| | KR2.3 | Pérdida de población 15-64 y de fuerza laboral a 2050 cuantificada con rango | rango en todos los escenarios | 15-64: −36,4 % a −27,4 % · FLP: A −12,2 %, B −5,5 %, C −6,4 % | fact_indicador_proyeccion |
| **O3 · Decisión** — Orientar la decisión pública: dónde y con qué palancas actuar | KR3.1 | Riesgo demográfico-laboral medido para todas las regiones | 17 de 17 si-do | 17 · 6 en riesgo alto | fact_riesgo_regional |
| | KR3.2 | Palancas de política cuantificadas | 3 de 3 | fecundidad alta +1,4 pp · migración alta vs cero +7,7 pp · participación B vs A +6,7 pp | fact_indicador_proyeccion / fact_fuerza_laboral_escenario |
| | KR3.3 | Tablero de Power BI que responde las 10 preguntas de negocio | 10 de 10 | 10 de 10 · 8 páginas con portada y navegador | ../powerbi/ETL_Corea_Grupo6.pbix |
| **O4 · Calidad del dato (habilitador)** — Garantizar datos confiables, trazables y reproducibles | KR4.1 | Registros válidos tras las reglas | ≥ 98 % | 99,96 % | kpi_calidad_dataset |
| | KR4.2 | Rechazos con motivo trazado | ≤ 2 % y 100 % trazados | 0,04 % · 100 % | ctl_rechazos |
| | KR4.3 | Coherencia maestra vs contraste | ≥ 90 % de pares ≤ ±3 % | 100 % (externos dif. máx 2,8 %) | fact_conciliacion |
| | KR4.4 | Fuentes integradas y ejecuciones sin fallo | ≥ 3 · ≥ 95 % | 3 · 100 % | dim_fuente / ctl_log_cargas |

## 2. KPIs del problema (una fórmula, un valor, una referencia, un semáforo)

| Eje | KPI | Indicador | Fórmula | Último valor | Referencia | Semáforo | Naturaleza |
|---|---|---|---|---|---|---|---|
| Natalidad | KPI-01 | Tasa global de fecundidad | publicado por KOSTAT | 0,80 (2025) | reemplazo 2,1 · OCDE 1,48 | 🔴 Crítico (< 1,3 «muy baja») | observado |
| Natalidad | KPI-02 | Variación de nacimientos desde 2000 | (N_t / N_2000 − 1) × 100 | −60,3 % (2025) | 0 % | 🔴 Crítico | calculado |
| Natalidad | KPI-03 | Crecimiento natural | nacimientos − defunciones | −108.627 (2025) | 0 | 🔴 Crítico (negativo desde 2020) | observado |
| Envejecimiento | KPI-04 | Esperanza de vida al nacer | publicado por KOSTAT | 83,7 años (2024) | OCDE 80,4 | Contexto | observado |
| Envejecimiento | KPI-05 | Población de 65 y más | P65+ / P × 100 | 20,3 % (2025) | ONU: ≥ 20 % superenvejecida | 🔴 Crítico | proyección oficial |
| Envejecimiento | KPI-06 | Dependencia de vejez | P65+ / P15-64 × 100 | 29,3 (2025) → 77 (2050) | OCDE 29,5 | 🔴 Crítico (2050 > 2× OCDE) | proyección oficial |
| Fuerza laboral | KPI-07 | Variación de la población 15-64 a 2050 | (P15-64₂₀₅₀ / P15-64₂₀₂₅ − 1) × 100 | −31,9 % | 0 % | 🔴 Crítico | proyección oficial |
| Fuerza laboral | KPI-08 | Índice de reemplazo laboral | P15-24 / P55-64 × 100 | 58 (2025) | 100 | 🔴 Crítico (< 70) | proyección oficial |
| Fuerza laboral | KPI-09 | Tasa de participación laboral (15+) | PEA / P15+ × 100 | 64,7 % (2025) | OCDE 60,6 % | 🟢 Normal | observado |
| Fuerza laboral | KPI-10 | Brecha de género en participación | TP_H − TP_M | 15,8 pp (2025) | ≤ 10 pp | 🟠 Alerta | calculado |
| Fuerza laboral | KPI-11 | Variación de la fuerza laboral potencial a 2050 | Σ P_proy × TP_supuesta | −12,2 % (A) · −5,5 % (B) · −6,4 % (C) | 0 % | 🔴 Crítico | escenario propio |
| Territorio | KPI-12 | Si-do en riesgo alto | nº en el tercil superior del índice | 6 de 17 | — | 🟠 Alerta | inferencia propia |
| Contexto | KPI-13 | Población extranjera residente | extranjeros / población censada × 100 | 4,1 % (2025) | — | Contexto | calculado |
| Contexto | KPI-14 | PIB por hora trabajada | publicado por la OCDE | 53,4 USD PPA (2025) | — | Contexto | observado |

**Umbrales del semáforo** (definidos por el equipo con referencias reconocidas): nivel de reemplazo 2,1 y fecundidad
"muy baja" < 1,3 (literatura demográfica); envejecida ≥ 14 % y superenvejecida ≥ 20 % de 65+ (clasificación de la ONU);
promedio OCDE del World Bank para dependencia y participación; 100 como reemplazo completo de la fuerza laboral.
Son referencias de lectura, no metas que el proyecto pueda controlar.

## 3. Preguntas de negocio → capa → KPI → página del tablero

(Mapeo por capa tomado del aporte de Miguel en el Avance 2, separando 6a y 6b.)

| N.º | Pregunta | Capa | KPI | Página Power BI |
|---|---|---|---|---|
| 1 | ¿Cómo han evolucionado la TFR y los nacimientos 2000-2025? | Histórico | KPI-01, 02, 03 | Natalidad |
| 2 | ¿Hay relación entre la caída de la natalidad y la población 15-64? | Histórico | KPI-02, 07 | Fuerza laboral |
| 3 | ¿Cómo cambian la proporción de 65+ y la dependencia de vejez? | Histórico + proyección | KPI-05, 06 | Envejecimiento |
| 4 | ¿Qué tendencias presentan la PEA y la participación frente al envejecimiento? | Histórico | KPI-09, 10 | Fuerza laboral |
| 5 | ¿Qué si-do presentan mayores riesgos? | Histórico + proyección provincial | KPI-12 | Regiones |
| 6a | ¿Cómo evolucionará la población en edad de trabajar hasta 2072 según KOSTAT? | Proyección oficial | KPI-07 | Fuerza laboral |
| 6b | ¿Qué rango de fuerza laboral resulta bajo supuestos de participación? | Escenario propio | KPI-11 | Fuerza laboral |
| 7 | ¿Cómo se asocia el envejecimiento con el empleo y la productividad? (no causal) | Histórico | KPI-09, 14 | Contexto OCDE |
| 8 | ¿Qué indicadores son señales tempranas de escasez laboral? | Histórico + proyección | KPI-03, 08 | Resumen |
| 9 | ¿Cómo se compara Corea con la OCDE? | Histórico | KPI-01, 06, 09 | Contexto OCDE |
| 10 | ¿Qué información integrada apoya la política pública? | Las tres capas | KR3.2 (palancas) | Resumen y Regiones |

## 4. Revisión de los KPIs del Avance 1

| KPI original | Decisión |
|---|---|
| ≥ 3 fuentes (KOSIS, KOSTAT, OECD) | KOSIS y KOSTAT son una misma institución → KR4.4 cuenta instituciones (3) |
| % cargas exitosas ≥ 95 | se mantiene en KR4.4 |
| % años sin lagunas = 100 % | imposible por Sejong y datos no publicados → completitud sobre celdas esperadas (KR1.1) |
| Número de filas consolidadas | métrica descriptiva en `ctl.conteos`, no objetivo |
| 4 indicadores automatizados | ampliado a 14 KPIs de dominio con fórmula única (sección 2) |
| % inconsistencias = 0 % | reemplazado por KR4.1 y KR4.2 (retroalimentación) |

## 5. Limitaciones
* Población por edad 2023-2025 = proyección KOSTAT (rotulada); se contrasta con el censo de registros.
* Escenario C: el Avance 2 proponía convergencia al promedio OCDE; sin tasas OCDE por sexo × edad comparables con la EAPS
  se usa el cierre del 50 % de la brecha de género.
* EAPS con grupos decenales y 60+ abierto; las cifras regionales de la EAPS son muestrales (mayor error que las
  nacionales: se leen como tendencias, no como diferencias exactas entre si-do).
* KPI-09 se compara con una estimación modelada de la OIT (World Bank): referencia de orden de magnitud.
