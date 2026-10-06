# Fase 1 — Diagnóstico del proyecto

Proyecto ETL 2026 · Grupo 6 · Maestría en IA y Ciencia de Datos · Universidad Autónoma de Occidente
Pregunta central: **¿Cómo impactará la disminución de la natalidad y el envejecimiento poblacional en la disponibilidad futura de la fuerza laboral en Corea del Sur?**

Insumos analizados: *Avance 1* (PDF entregado), *Avance 2 – borrador de Miguel* (docx), *retroalimentación del profesor*,
*fuentes_datos.docx*, *prompt_TF.docx* (catálogo de descargas KOSIS de Angie), repositorio
[miguelmendez04/ETL_CoreaDelSur](https://github.com/miguelmendez04/ETL_CoreaDelSur) (rama `main`, descargado el 2026-10-05),
carpeta `bases/` (8 archivos KOSIS descargados el 2 y 3 de octubre de 2026), *lab2-etl.pdf* y *rubrica.xlsx*.

---

## 1. Resumen del proyecto actual

| Elemento | Estado |
|---|---|
| Problema y contexto | Bien desarrollado en el Avance 1 (árbol de problemas, usuarios, 10 preguntas). |
| Respuesta a la retroalimentación | El borrador del Avance 2 ya reformula fuentes (una maestra por indicador), grano, capas histórico/proyección/escenario y KPIs de calidad. **Es la mejor base conceptual disponible** y se adopta. |
| Código | Capa **Bronze implementada y bien diseñada** (catálogo en `config.yaml`, sha256, metadata JSON, bitácora `ctl.log_cargas`). **Silver y Gold no existen**: `main.py --capa silver` sólo imprime "pendiente". |
| Datos | 9 CSV de KOSIS versionados en el repo; World Bank, OECD y UN WPP **no están versionados** (se re-descargan por API). 8 archivos KOSIS adicionales en `bases/` aún no integrados. |
| Base de datos | Diseño PostgreSQL vía Docker (`sql/00_schemas.sql`). En el equipo actual **no hay Docker ni PostgreSQL**, por lo que el pipeline del repo no puede ejecutarse de punta a punta. |

## 2. Estructura actual del repositorio

```
ETL_CoreaDelSur-main/
├── main.py                 orquestación (sólo bronze)
├── config/config.yaml      catálogo de fuentes + notas de perfilamiento
├── config/mappings/        territorios, edades, sexo, indicadores (CSV)
├── sql/00_schemas.sql      DDL ctl / bronze / silver (gold vacío)
├── src/extract/            comun, ejecutar, kosis, oecd, worldbank, unwpp
├── src/load/bronze.py      COPY a PostgreSQL + ctl.log_cargas
├── src/quality/perfilamiento.py   completitud, duplicados, rangos, conciliación
├── src/transform/lectura_bronze.py   lectura a formato largo (sin homologar)
├── notebooks/01..05        perfilamiento por fuente + conciliación
├── tests/test_extract.py   pruebas de bronze (sin red)
└── data/bronze/kosis/      9 CSV + metadata
```

**Lo que se reutiliza:** el patrón de extracción por catálogo, los hashes y metadata, el diseño de tablas `ctl`,
los mapeos de dimensiones, la lógica de `lectura_bronze.py` y las notas de perfilamiento de `config.yaml`
(contienen hallazgos verificados por el equipo: unidades en miles, Sejong, "Jeonnam-Gwangju", etc.).

**Lo que se corrige o completa:** dependencia obligatoria de PostgreSQL/Docker, ausencia de Silver/Gold,
de validaciones con rechazo trazado, de EDA con visualizaciones, de diccionario de datos, linaje y orquestación con `schedule`.

## 3. Problemas e inconsistencias identificados

| # | Hallazgo | Evidencia | Impacto | Propuesta |
|---|---|---|---|---|
| P1 | **La población 2023–2025 tratada como "histórica" es proyección.** | Los archivos `poblacion_*_medio.csv` (DT_1BPA001 / DT_1BPB001) son tablas de *proyección*: 2000–2022 es población estimada (base), 2023+ es escenario medio. `config.yaml` lo reconoce ("2022-2025 marcados como proyectados"), pero el Avance 2 los presenta como observados 2000–2025. | Mezcla observado y proyectado — exactamente lo que critica el profesor. | Cada registro lleva `tipo_dato` (`observado`, `estimado_base`, `proyeccion_oficial`, `escenario_propio`). Población por edad 2023–2025 = `proyeccion_oficial`; se concilia contra el **censo de registros** DT_1IN1502 (total observado 2016–2025). |
| P2 | Fuentes de estadísticas vitales distintas entre repo y descargas nuevas. | Repo: DT_1B8000G (mensual por provincia, hay que descartar meses). `bases/`: DT_1B8000H (anual por provincia 1990–2025, número y tasa). | DT_1B8000H es la tabla correcta para grano anual. | Maestra regional = **DT_1B8000H**; DT_1B8000G e DT_1B8000I quedan como contraste. |
| P3 | Variables del árbol de problemas sin fuente en el repo. | Esperanza de vida, mortalidad infantil, matrimonios no estaban integrados. | El árbol cita "incremento de la esperanza de vida" como causa directa. | **DT_1B8000F** (1970–2025) aporta esperanza de vida por sexo, mortalidad, matrimonios → se integra. |
| P4 | Migración sin fuente observada. | No se descargó tabla de migración internacional. | El árbol menciona "necesidad de atraer inmigración". | Se usan dos insumos oficiales ya disponibles: (a) población extranjera del censo DT_1IN1502 (2016–2025); (b) escenarios de **migración internacional alta / baja / cero** de KOSTAT (archivo de 29 escenarios). No se inventan flujos migratorios. |
| P5 | Los escenarios "alto/bajo" del repo son variantes de **sólo fecundidad**. | El archivo trae 29 escenarios y no incluye los compuestos 고위/저위. | Etiquetarlos "alto/bajo" sugiere los escenarios compuestos oficiales. | Se nombran con su significado real: `fecundidad_alta`, `fecundidad_baja`, `migracion_cero`, `envejecimiento_rapido`, etc. |
| P6 | KOSIS y KOSTAT contadas como dos fuentes en el Avance 1. | KPI ">= 3 fuentes (KOSIS, KOSTAT, OECD)". | Infla el KPI: KOSIS es el portal de KOSTAT. | Fuentes institucionales: KOSTAT/KOSIS, OECD, Banco Mundial (+ UN WPP opcional). |
| P7 | EAPS: el Avance 2 dice "mensual → anual". | `config.yaml`: se descargó el promedio **anual publicado** (`prd_se: Y`). | Agregar meses en el pipeline sería redundante y podría diferir del oficial. | Se usa el anual publicado; los meses se descartan con regla documentada. |
| P8 | Sejong y regiones nuevas. | Sejong: población desde 2012, EAPS desde 2017. "Jeonnam-Gwangju" sólo en 2025. Nombres Gangwon/Jeonbuk cambian. | Series regionales no comparables 2000–2025 sin homologar. | `dim_territorio` con códigos estables y agregado **CNSJ (Chungnam + Sejong)**; "Jeonnam-Gwangju" se rechaza con motivo trazado. |
| P9 | Dependencia de vejez OECD = 65+/20-64. | Nota en `config.yaml`. | No comparable 1 a 1 con 65+/15-64. | Se calcula en el pipeline con una sola fórmula; la OECD queda como contraste con advertencia. |
| P10 | Duplicados de archivos en `bases/`. | `Vital_Statistics_of_Korea` y `Live_Births_and_Deaths` vienen en .xls y .xlsx. | Doble carga. | Bronze compara sha256 del contenido tabular; se ingiere una versión y la otra queda registrada como duplicada. |
| P11 | Formatos KOSIS heterogéneos. | CSV UTF-8, CSV CP949, XLSX, y "XLS" que en realidad es XML Spreadsheet 2003 en EUC-KR con XML mal formado. | Lectores genéricos fallan. | Lector específico por formato en Bronze. |
| P12 | Sin motor SQL disponible localmente. | No hay Docker/PostgreSQL instalados. | El pipeline del repo no corre. | Carga con SQLAlchemy: **SQLite por defecto (verificable)** y PostgreSQL configurable por `.env` con el mismo modelo. |
| P13 | Requisitos del curso no cubiertos. | `lab2-etl`: EDA cuantificado, Matplotlib, `schedule`, autores en `config.yaml`. Rúbrica: carga SQL, EDA, storytelling. | Pérdida de puntos. | Notebooks de EDA, módulo de visualización, `scheduler.py`, autores en `config.yaml`. |

## 4. Retroalimentación del profesor (análisis)

| # | Comentario | Problema que señala | Cambio requerido |
|---|---|---|---|
| R1 | Definir con más precisión el **grano** del dataset. | No se sabía qué representa una fila. | Grano explícito por tabla (anio × territorio × sexo × grupo_edad × indicador [× escenario]). |
| R2 | Diferenciar **análisis histórico, proyecciones oficiales e inferencias propias**. | Riesgo de presentar proyecciones como observaciones. | Tablas separadas en Silver y Gold + columna `tipo_dato`. |
| R3 | **Fuentes solapadas** → fuente maestra por indicador. | Mismo indicador en KOSIS/OECD/WB/UN con definiciones distintas. | Catálogo maestra/contraste + tabla de conciliación. |
| R4 | La **disponibilidad futura** exige distinguir proyección oficial vs modelo propio; el ETL no produce proyecciones. | Pregunta 6 del Avance 1 ("¿qué proyección puede inferirse?"). | Proyección = KOSTAT sin modificar; fuerza laboral futura = **escenario contable propio** con supuestos explícitos, rotulado como tal. |
| R5 | KPI "0 % inconsistencias" mal formulado. | Un pipeline maduro detecta y rechaza. | Tasa de registros válidos, tasa de rechazo trazada, completitud con umbrales. |
| R6 | Confirmar **granularidad subnacional** comparable. | Pregunta 5 sobre regiones. | Validación de cobertura por si-do e indicador; matriz de cobertura en el reporte de calidad. |
| R7 | Definir **periodo, frecuencia, unidad y claves** antes de consolidar. | Faltaba metadato por serie. | `dim_indicador` + diccionario de datos con esos campos. |
| P-1 | Prioridad: separar serie histórica de proyecciones en tablas/capas distintas. | = R2. | `fact_historico`, `fact_proyeccion`, `fact_escenario_fuerza_laboral`. |
| P-2 | Prioridad: KPIs de calidad con umbrales realistas. | = R5. | `gold.kpi_calidad_pipeline` calculado en cada ejecución. |
| H | Herramientas recomendadas: APIs KOSIS/OECD/WB, Python/Pandas, PostgreSQL o MySQL, Power BI. | — | APIs OECD/WB en uso; KOSIS por descarga (API restringida a residentes, documentado); SQL vía SQLAlchemy (PostgreSQL soportado). |

## 5. OKRs y KPIs (estado)

* **Avance 1:** 1 objetivo, 3 KR, 6 KPIs. Dos KPIs no son rigurosos: "0 % inconsistencias" (R5) y "100 % años sin lagunas"
  (imposible a nivel regional por Sejong y "Jeonnam-Gwangju"). No había KPIs **de negocio** (demográficos/laborales), sólo de proceso.
* **Avance 2 (borrador):** 4 KR con umbrales realistas. Se conservan como objetivo habilitador de calidad (O4) y se **agregan tres objetivos de negocio (O1 diagnóstico, O2 impacto laboral, O3 decisión)** con indicadores de
  riesgo demográfico-laboral (TFR, % 65+, dependencia de vejez, población 15–64, tasa de participación, fuerza laboral potencial)
  para que el tablero responda la pregunta central y no sólo mida el pipeline. Detalle en `docs/kpi_trazabilidad.md`.

## 6. Fuentes de datos (resumen; detalle en `docs/fuentes_datos.md`)

| Fuente / tabla | Aporta | Periodo | Unidad estadística | Rol |
|---|---|---|---|---|
| KOSIS DT_1B8000F Vital Statistics of Korea | nacimientos, defunciones, TFR, esperanza de vida, mortalidad infantil, matrimonios | 1970–2025 (EV hasta 2024) | país-año | **maestra nacional** |
| KOSIS DT_1B8000H Vital statistics for Provinces | nacimientos, defunciones, tasas brutas, matrimonios | 1990–2025 | si-do-año | **maestra regional** |
| KOSIS DT_1B81A17 TFR por si-gun-gu (repo) | TFR y tasas por edad de la madre | 2000–2025 | si-do-año | **maestra TFR regional** |
| KOSIS DT_1B8000K Births & deaths by sex | nacimientos y defunciones por sexo | 2004–2025 | si-do-sexo-año | complementaria |
| KOSIS DT_1B8000I / DT_1B8000G | mismas variables vitales | 2000–2025 | si-do | contraste |
| KOSIS DT_1BPA001 / DT_1BPB001 (repo) | población por sexo y edad (estimada 2000–2022 + proyección) | 2000–2072 / 2000–2052 | país / si-do × sexo × edad | **maestra población y proyección medio** |
| KOSIS proyección por escenario (repo, 29 escenarios) | población por sexo y edad bajo escenarios de fecundidad, esperanza de vida y migración | 2022–2072 | país × sexo × edad | **maestra escenarios oficiales** |
| KOSIS DT_1BPA002 indicadores resumen (repo) | dependencia, índice de envejecimiento oficiales | 2022–2072 | país | contraste del cálculo propio |
| KOSIS DT_1DA7004S / DT_1DA7012S EAPS (repo) | población 15+, activos, ocupados, desocupados, tasas | 2000–2025 | si-do / sexo × edad | **maestra mercado laboral** |
| KOSIS DT_1IN1502 Censo (registros) | población total, por sexo, extranjeros, hogares, viviendas | 2016–2025 | si-do / si-gun-gu | maestra extranjeros + contraste población |
| KOSIS DT_1IN0001 Censo histórico | población por si-do, sexo, edad | 1925–2010 (quinquenal) | si-do × edad | contexto de largo plazo |
| World Bank WDI (API) | TFR, % 65+, pob 15–64, participación, PIB por ocupado (9 países) | 2000–2025 | país-año | comparación internacional + contraste |
| OECD SDMX (API) | PIB por hora trabajada; fuerza laboral; fecundidad | 2000–2025 | país-año | **maestra productividad** + contraste |
| UN WPP 2024 (API con token) | población por edad, variantes | 2000–2072 | país | contraste opcional (requiere token) |

## 7. Brechas principales a resolver

1. Implementar Silver (limpieza, homologación, validación con rechazos) y Gold (modelo dimensional orientado a KPIs).
2. Separar observado / proyección oficial / escenario propio en tablas y con `tipo_dato` (R2, R4, P1).
3. Integrar las descargas nuevas de `bases/` (esperanza de vida, vitales anuales por provincia, censo, extranjeros).
4. Reformular KPIs de calidad y calcularlos automáticamente (R5).
5. Validar cobertura subnacional y construir agregado CNSJ (R6, P8).
6. Hacer el pipeline ejecutable sin Docker (SQLite) y mantener PostgreSQL como opción (P12).
7. EDA con visualizaciones, diccionario, linaje, matrices de trazabilidad, orquestación `schedule` (P13).
8. Preparar la capa Gold para Power BI (esquema estrella, medidas DAX, tema visual UAO) y la presentación.
