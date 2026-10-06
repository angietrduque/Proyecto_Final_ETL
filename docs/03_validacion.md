# Fase 4 — Validación (evidencia de la ejecución del 2026-10-05)

| Comprobación | Cómo se verificó | Resultado |
|---|---|---|
| El pipeline se ejecuta de punta a punta | `python main.py` (con APIs de World Bank y OECD) desde un control limpio | ✅ 43,6 s, código de salida 0 (`logs/ultima_ejecucion.txt`) |
| Bronze | `data/bronze/_manifest.csv`, `ctl_log_cargas` | ✅ 31 cargas: 28 éxito, 2 duplicados detectados, UN WPP omitido (sin token) |
| Transformaciones Silver | `ctl.conteos` (antes/después por paso) y reglas de consistencia | ✅ 99,96 % válidos; todas las reglas de consistencia PASAN; 82 rechazos trazados (Jeonnam-Gwangju, Sejong repetido en el censo) |
| Tablas Gold | parquet + carga SQL con PK/FK y `PRAGMA foreign_keys=ON` | ✅ 20 tablas Gold; 0 violaciones de claves foráneas (`notebooks/04`) |
| KPIs calculables | `data/gold/kpi_okr.csv` | ✅ 13/13 resultados clave cumplen; 14 KPIs de negocio calculados |
| Fórmulas correctas | indicadores derivados vs KOSTAT DT_1BPA002 | ✅ diferencia máxima 0,37 % (51 años, 6 indicadores) |
| Escenarios propios | calibración del modelo vs PEA observada 2025 | ✅ +1,51 % |
| Retroalimentación atendida | `docs/retroalimentacion_trazabilidad.md` + prueba `test_gold_separa_observado_de_proyectado` | ✅ 7 comentarios + 2 prioridades |
| Pruebas automatizadas | `pytest -q` | ✅ 25 pruebas pasan |
| Notebooks | `python notebooks/construir_notebooks.py` (ejecución completa con salidas) | ✅ 4 notebooks ejecutados sin errores |
| Presentación | validador OOXML + exportación con PowerPoint | ✅ 19 diapositivas con vínculos internos, guion 15:00 min (`../presentacion`) |

**No verificado en este equipo:** la carga en PostgreSQL (no hay servidor instalado; el código y el DDL
`sql/ddl_postgresql.sql` están listos) y la extracción de UN WPP (requiere token). El tablero `.pbix` (portada + 7 páginas con menú lateral) está en `../powerbi/ETL_Corea_Grupo6.pbix`; se abrió y actualizó en Power BI Desktop y sus páginas se exportaron a `../powerbi/ETL_Corea_Grupo6_paginas.pdf`. La versión web `../powerbi/ETL_Corea_Grupo6.html` se revisó página por página en Microsoft Edge.
