# Integración del trabajo del equipo

El grupo desarrolló dos versiones del pipeline en paralelo: esta (SQLite + `schedule`, verificable en cualquier equipo
sin servidor) y la de Miguel ([miguelmendez04/ETL_CoreaDelSur](https://github.com/miguelmendez04/ETL_CoreaDelSur):
PostgreSQL en Docker + Apache Airflow). Ambas parten de la misma base: el Avance 2 y la capa Bronze que construyó Miguel
(catálogo de fuentes en `config.yaml`, sha256, metadata y bitácora `ctl.log_cargas`).

## Lo que esta versión incorporó del repositorio de Miguel

| Aporte | Cómo quedó aquí | Dónde |
|---|---|---|
| Supuesto C · convergencia al promedio OCDE (propuesto en su Avance 2) | Participación OCDE por sexo y edad por API (SDMX `DF_IALFS_LF_WAP_Q`); 15-19 y 60+ constantes | `config.yaml`, `gold.supuestos_participacion` |
| Supuesto D · cierre de la brecha de género que nunca baja una tasa | El antiguo C pasa a D con esa regla y su validación | `gold.supuestos_participacion`, prueba `test_supuesto_d_nunca_baja_una_tasa` |
| Factor de cobertura de la EAPS | Ajuste de escala por sexo y grupo; se reporta también la diferencia sin ajuste (+1,5 %) | `gold.factor_cobertura`, KR2.2 |
| Sensibilidad de los escenarios | 8 variantes de parámetros de B, C y D | `gold.fact_escenarios_sensibilidad` |
| Sensibilidad del índice regional | 7 esquemas, incluido su índice de 4 componentes mínimo-máximo | `gold.fact_riesgo_sensibilidad`, KR3.1 |
| Ejecución desde un clon nuevo sin internet | La última respuesta de World Bank y OECD queda versionada en Bronze | `.gitignore`, prueba `test_bronze_de_las_api_versionado_para_ejecutar_sin_api` |
| Más pruebas | 31 pruebas (antes 25) | `tests/` |

## Lo que se mantiene como alternativa del equipo (repositorio de Miguel)

* **PostgreSQL en Docker** con esquemas bronze/silver/gold/ctl: aquí el mismo código carga PostgreSQL con `DB_URL`,
  pero la carga verificada es SQLite (el equipo de trabajo no tiene Docker).
* **Apache Airflow** (DAG semanal, fuentes en paralelo, reintentos y alerta si un KPI no cumple): aquí la orquestación
  es `scheduler.py` con la librería `schedule`, que es la que pide el laboratorio.
* **UN WPP ejecutado con token**: aquí está soportado pero se omite sin token.

## Decisiones que difieren a propósito

* **Población 2023-2025:** aquí va en la tabla de proyecciones (prioridad de la retroalimentación: separar histórico y
  proyección en tablas distintas); en el repositorio de Miguel queda en el histórico marcada como `preliminar`.
* **Escenarios oficiales:** aquí se integran los 29 de KOSTAT; allá, 8 seleccionados.
* **Supuesto B:** aquí la tendencia se prolonga hasta 2035 con tope de ±10 pp (−4,9 % a 2050); allá, hasta 2050
  con tope de 15 pp (+0,5 %). La sensibilidad muestra el rango.
