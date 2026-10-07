"""Diagramas de arquitectura Medallion y del modelo estrella (PNG) -> docs/architecture/."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from src.analytics.figuras import AZUL, GRIS, ROJO, ROJOS, TINTA, TINTA2  # noqa: E402
from src.utils.config import RAIZ  # noqa: E402

BRONCE, PLATA, ORO = "#B07A4B", "#8C959D", "#C9A227"


def _caja(ax, x, y, w, h, titulo, lineas, color, texto_blanco=True, tam=8.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.025", fc=color, ec="none"))
    c = "white" if texto_blanco else TINTA
    ax.text(x + w / 2, y + h - 0.035, titulo, ha="center", va="top", fontsize=12, fontweight="bold", color=c)
    ax.text(x + 0.015, y + h - 0.095, "\n".join(lineas), ha="left", va="top", fontsize=tam, color=c, linespacing=1.45)


def _flecha(ax, x1, y1, x2, y2, color=TINTA2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18, lw=2, color=color))


def arquitectura():
    fig, ax = plt.subplots(figsize=(16, 7.6))
    ax.set_xlim(0, 1.6)
    ax.set_ylim(0, 0.76)
    ax.axis("off")
    _caja(ax, 0.01, 0.17, 0.25, 0.55, "Fuentes", [
        "KOSIS / KOSTAT (descarga manual*)", "  · Estadísticas vitales (F, H, I, K, G)", "  · TFR por si-do (A17)",
        "  · EAPS si-do y sexo×edad", "  · Población estimada y", "    proyecciones 2022-2072", "  · Censos 1925-2025",
        "World Bank WDI  (API v2)", "OECD SDMX  (API REST)", "UN WPP  (API, token opcional)", "",
        "* OpenAPI sólo para residentes", "  en Corea"], "#3C3C3B")
    _caja(ax, 0.33, 0.17, 0.27, 0.55, "BRONZE · crudo inmutable", [
        "landing → bronze/<fuente>/<fecha>/", "· copia byte a byte del original",
        "· instantánea tabular (todo TEXTO)", "· metadata JSON: URL, tabla, fecha,", "  versión sha256, filas, rol",
        "· dedupe por contenido (.xls = .xlsx)", "· _manifest.csv: versión vigente", "· 4 lectores: CSV UTF-8/CP949,",
        "  XLSX, XML-2003 EUC-KR", "· 28 datasets · ~21 mil filas"], BRONCE)
    _caja(ax, 0.67, 0.17, 0.29, 0.55, "SILVER · limpio y validado", [
        "Grano: año × territorio × sexo × edad", "          × indicador [× escenario]", "1 formato largo · 2 sólo años",
        "3 variables · 4 homologación", "5 territorios · 6 tipos y unidades", "7 sin imputar · 8 85+ agregado",
        "9 reglas → rechazos trazados", "Tablas: fact_historico,", "fact_proyeccion, fact_contraste,",
        "fact_internacional, conciliacion,", "sin_dato, dim_escenario"], PLATA)
    _caja(ax, 1.03, 0.17, 0.27, 0.55, "GOLD · modelo estrella", [
        "9 dimensiones: tiempo, territorio,", "sexo, edad, indicador, escenario,", "supuesto, tipo_dato, fuente",
        "fact_indicador_historico", "fact_indicador_proyeccion", "fact_fuerza_laboral_escenario", "fact_riesgo_regional",
        "fact_comparacion_internacional", "fact_conciliacion · kpi_okr", "dataset_nacional_anual", "dataset_regional_anual"], ORO, False)
    _caja(ax, 1.37, 0.43, 0.22, 0.29, "Consumo", ["SQLite (defecto)", "PostgreSQL (DB_URL)", "PK + FK declaradas",
                                                  "Power BI · CSV/Parquet"], ROJO)
    _caja(ax, 1.37, 0.17, 0.22, 0.22, "Calidad (ctl)", ["log_cargas · conteos", "rechazos · validaciones",
                                                        "reporte_calidad.md"], ROJOS[5])
    for x1, x2 in ((0.26, 0.33), (0.60, 0.67), (0.96, 1.03)):
        _flecha(ax, x1 + 0.005, 0.445, x2 - 0.005, 0.445)
    _flecha(ax, 1.31, 0.56, 1.37, 0.56)
    _flecha(ax, 1.31, 0.28, 1.37, 0.28)
    ax.text(0.01, 0.11, "Separación de la naturaleza del dato (retroalimentación del profesor):", fontsize=11,
            fontweight="bold", color=TINTA)
    ax.text(0.01, 0.045, "observado  ·  estimado (≤2022)  ·  proyeccion_oficial (KOSTAT, sin modificar)  ·  calculado (fórmula del pipeline)"
            "  ·  escenario_propio (supuestos A/B/C/D)  ·  inferencia_propia (índice regional)", fontsize=10, color=TINTA2)
    ax.text(0.01, 0.74, "Orquestación: main.py (CLI) · scheduler.py (librería schedule) · configuración única en config/config.yaml",
            fontsize=10, color=TINTA2)
    p = RAIZ / "docs" / "architecture" / "arquitectura_medallion.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def modelo():
    fig, ax = plt.subplots(figsize=(15, 8.6))
    ax.set_xlim(0, 1.5)
    ax.set_ylim(0, 0.92)
    ax.axis("off")
    hechos = {
        "fact_indicador_historico": (0.52, 0.55, ["PK anio, cod_territorio, cod_sexo,", "   cod_edad, cod_indicador",
                                                  "valor · tipo_dato · estado", "fuente · dataset · es_derivado"]),
        "fact_indicador_proyeccion": (0.52, 0.32, ["PK … + cod_escenario,", "   edicion_proyeccion", "valor · tipo_dato"]),
        "fact_fuerza_laboral_escenario": (0.52, 0.09, ["PK anio, cod_escenario, cod_supuesto,", "   cod_sexo, cod_edad (EAPS)",
                                                       "poblacion_proyectada · tasa_participacion", "fuerza_laboral_potencial · índice 2025=100"]),
    }
    for n, (x, y, l) in hechos.items():
        _caja(ax, x, y, 0.42, 0.19, n, l, ROJO, tam=9.5)
    dims = {"dim_tiempo": (0.03, 0.66, ["anio (PK) · decada · periodo", "horizonte · en_ventana_analisis"]),
            "dim_territorio": (0.03, 0.45, ["cod_territorio (PK) · nombre", "tipo · región · vigente_desde"]),
            "dim_sexo": (0.03, 0.27, ["cod_sexo (PK) · nombre"]),
            "dim_edad": (0.03, 0.08, ["cod_edad (PK) · edad_min/max", "tipo · grupo_funcional"]),
            "dim_indicador": (1.05, 0.66, ["cod_indicador (PK) · fórmula", "unidad · fuente maestra · aditivo"]),
            "dim_escenario": (1.05, 0.45, ["cod_escenario (PK) · familia", "supuestos fecundidad/EV/migración"]),
            "dim_supuesto": (1.05, 0.27, ["cod_supuesto (PK) · A / B / C / D"]),
            "dim_tipo_dato": (1.05, 0.08, ["observado · estimado · calculado", "proyección · escenario · inferencia"])}
    for n, (x, y, l) in dims.items():
        _caja(ax, x, y, 0.40, 0.14, n, l, AZUL, tam=9.5)
    for n, (x, y, _) in dims.items():
        xd = x + 0.40 if x < 0.5 else x
        for hn, (hx, hy, _) in hechos.items():
            if n in ("dim_escenario", "dim_supuesto") and hn == "fact_indicador_historico":
                continue
            if n == "dim_supuesto" and hn == "fact_indicador_proyeccion":
                continue
            xh = hx if x < 0.5 else hx + 0.42
            ax.plot([xd, xh], [y + 0.07, hy + 0.095], color=GRIS, lw=0.7, alpha=0.6, zorder=0)
    ax.text(0.03, 0.905, "Modelo estrella de la capa Gold (relaciones 1:* desde cada dimensión)", fontsize=14,
            fontweight="bold", color=TINTA)
    ax.text(0.03, 0.865, "Otras tablas Gold: fact_riesgo_regional · fact_comparacion_internacional · fact_conciliacion · "
            "dataset_nacional_anual · dataset_regional_anual · kpi_okr · kpi_calidad_dataset · dim_fuente",
            fontsize=10, color=TINTA2)
    p = RAIZ / "docs" / "architecture" / "modelo_estrella.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


if __name__ == "__main__":
    print(arquitectura())
    print(modelo())
