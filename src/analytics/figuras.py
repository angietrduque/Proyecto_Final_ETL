"""Figuras del análisis (Matplotlib) a partir de la capa Gold -> docs/figuras/*.png.

Convenciones visuales (las mismas del tablero de Power BI y de la presentación):
  * Paleta categórica validada para daltonismo (ΔE OKLab mínimo ≥ 9 en deuteranopía/protanopía/tritanopía):
    rojo y azul de la bandera de Corea, ámbar, verde azulado, púrpura — siempre en ese orden.
  * Naturaleza del dato: línea continua = observado/estimado; línea discontinua = proyección oficial KOSTAT;
    banda sombreada = rango de escenarios; marcador hueco = escenario propio del equipo.
  * Un solo eje Y por gráfico (sin ejes dobles); cuadrícula tenue; etiquetas directas selectivas.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.transformation.gold import leer  # noqa: E402
from src.utils.config import ruta  # noqa: E402

ROJO, AZUL, AMBAR, VERDE, PURPURA = "#CD2E3A", "#0047A0", "#E69F00", "#3A9E8E", "#8E6BB0"   # rojo y azul de la bandera de Corea
CATEG = [ROJO, AZUL, AMBAR, VERDE, PURPURA]
TINTA, TINTA2, GRIS, GRIS_CLARO = "#1E1E1E", "#555555", "#9A9A9A", "#E6E6E6"
ROJOS = ["#FBE3E5", "#F4B4BB", "#E87A86", "#D9414F", "#C8102E", "#8F0B21"]

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 11, "axes.edgecolor": GRIS, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRIS_CLARO,
    "grid.linewidth": 0.8, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlecolor": TINTA,
    "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2, "legend.frameon": False,
    "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight", "lines.linewidth": 2.2,
})


def _guardar(fig, nombre: str):
    p = ruta("figuras") / f"{nombre}.png"
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    return p


def _fuente(ax, texto: str):
    ax.annotate(texto, xy=(0, -0.13), xycoords="axes fraction", fontsize=8.5, color=GRIS, ha="left", va="top")


def _serie(df, ind, terr="00", sexo="T", edad="TOTAL", esc=None):
    d = df[(df.cod_indicador == ind) & (df.cod_territorio == terr) & (df.cod_sexo == sexo) & (df.cod_edad == edad)]
    if esc is not None:
        d = d[(d.cod_escenario == esc) & (d.edicion_proyeccion == "KOSTAT 2022-2072")]
    return d.set_index("anio")["valor"].sort_index()


def datos():
    return {n: leer(n) for n in ["fact_indicador_historico", "fact_indicador_proyeccion", "fact_fuerza_laboral_escenario",
                                 "fact_riesgo_regional", "fact_comparacion_internacional", "dim_territorio",
                                 "fact_conciliacion", "dim_escenario"]}


# ------------------------------------------------------------------------------------------------ 1 natalidad
def natalidad(d):
    h = d["fact_indicador_historico"]
    nac, tfr = _serie(h, "NACIMIENTOS"), _serie(h, "TFR")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7.2), sharex=True, gridspec_kw={"hspace": 0.28})
    a1.bar(nac.index, nac.values / 1000, color=ROJO, width=0.75)
    a1.set_title("Nacimientos por año (miles)", loc="left")
    for anio in (1970, 2000, 2025):
        a1.annotate(f"{nac[anio] / 1000:,.0f} mil".replace(",", " "), (anio, nac[anio] / 1000), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9, color=TINTA)
    a2.plot(tfr.index, tfr.values, color=ROJO)
    a2.axhline(2.1, color=TINTA2, ls=":", lw=1.2)
    a2.text(1971, 2.18, "Nivel de reemplazo generacional (2,1)", fontsize=9, color=TINTA2)
    a2.set_title("Tasa global de fecundidad (hijos por mujer)", loc="left")
    for anio in (1970, 2000, 2023, 2025):
        a2.annotate(f"{tfr[anio]:.2f}".replace(".", ","), (anio, tfr[anio]), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=9, color=TINTA)
    a2.set_ylim(0, 4.8)
    _fuente(a2, "Fuente: KOSIS DT_1B8000F (Vital Statistics of Korea). Datos observados 1970-2025.")
    return _guardar(fig, "01_natalidad_fecundidad")


# ------------------------------------------------------------------------------------------------ 2 pirámides
def piramides(d):
    h, p = d["fact_indicador_historico"], d["fact_indicador_proyeccion"]
    edades = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59",
              "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]
    cortes = [(2000, h, "Estimada"), (2022, h, "Estimada (año base)"), (2050, p, "Proyección KOSTAT medio"),
              (2072, p, "Proyección KOSTAT medio")]
    fig, axs = plt.subplots(1, 4, figsize=(15, 5.6), sharey=True)
    for ax, (anio, df, etiqueta) in zip(axs, cortes):
        sel = df[(df.cod_indicador == "POBLACION") & (df.cod_territorio == "00") & (df.anio == anio)]
        if "cod_escenario" in sel:
            sel = sel[(sel.cod_escenario == "medio") & (sel.edicion_proyeccion == "KOSTAT 2022-2072")]
        tot = sel[(sel.cod_sexo == "T") & sel.cod_edad.isin(edades)].valor.sum()
        hm = sel[sel.cod_sexo == "H"].set_index("cod_edad").valor.reindex(edades) / tot * 100
        mm = sel[sel.cod_sexo == "M"].set_index("cod_edad").valor.reindex(edades) / tot * 100
        y = np.arange(len(edades))
        col = lambda e: ROJO if e in ("65-69", "70-74", "75-79", "80-84", "85+") else (AZUL if e not in ("0-4", "5-9", "10-14") else AMBAR)  # noqa: E731
        ax.barh(y, -hm.values, color=[col(e) for e in edades], height=0.82, alpha=0.9)
        ax.barh(y, mm.values, color=[col(e) for e in edades], height=0.82, alpha=0.6)
        ax.axvline(0, color="white", lw=2)
        ax.set_title(f"{anio}", loc="center")
        ax.text(0.5, -0.12, etiqueta, transform=ax.transAxes, ha="center", fontsize=9, color=TINTA2)
        ax.set_xlim(-7.8, 7.8)
        ax.set_xticks([-6, -3, 0, 3, 6], ["6 %", "3 %", "0", "3 %", "6 %"])
        ax.grid(axis="y", visible=False)
        p65 = sel[(sel.cod_sexo == "T") & sel.cod_edad.isin(["65-69", "70-74", "75-79", "80-84", "85+"])].valor.sum() / tot * 100
        ax.text(0.97, 0.03, f"65+: {p65:.0f} %", transform=ax.transAxes, ha="right", va="bottom", fontsize=10,
                color=TINTA, fontweight="bold")
    axs[0].set_yticks(np.arange(len(edades)), edades)
    axs[0].text(0.02, 1.02, "Hombres ◂", transform=axs[0].transAxes, fontsize=9, color=TINTA2)
    axs[0].text(0.75, 1.02, "▸ Mujeres", transform=axs[0].transAxes, fontsize=9, color=TINTA2)
    fig.suptitle("De pirámide a urna: estructura por sexo y edad (% de la población total)", x=0.06, ha="left",
                 fontsize=15, fontweight="bold", color=TINTA)
    fig.text(0.06, -0.03, "Colores: ámbar 0-14 · azul 15-64 (edad de trabajar) · rojo 65+. Fuente: KOSTAT DT_1BPA001 "
             "(estimada hasta 2022; proyección medio desde 2023).", fontsize=8.5, color=GRIS)
    return _guardar(fig, "02_piramides_poblacion")


# ------------------------------------------------------------------------------------------------ 3 estructura
def estructura(d):
    h, p = d["fact_indicador_historico"], d["fact_indicador_proyeccion"]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    for ind, color, nombre in (("PROP_15_64", AZUL, "15-64 años"), ("PROP_65MAS", ROJO, "65 y más"),
                               ("PROP_0_14", AMBAR, "0-14 años")):
        sh, sp = _serie(h, ind), _serie(p, ind, esc="medio")
        ax.plot(sh.index, sh.values, color=color)
        ax.plot(sp.index, sp.values, color=color, ls="--")
        dy = {"PROP_65MAS": 3, "PROP_15_64": -3}.get(ind, 0)
        ax.text(2073, sp.iloc[-1] + dy, f"{nombre} {sp.iloc[-1]:.0f} %", color=TINTA, fontsize=9.5, va="center")
        ax.annotate(f"{sh.iloc[0]:.0f} %", (2000, sh.iloc[0]), xytext=(-30, 0), textcoords="offset points",
                    fontsize=9, color=TINTA, va="center")
    ax.axvspan(2022.5, 2072, color=GRIS_CLARO, alpha=0.45, lw=0)
    ax.text(2024, 92, "Proyección oficial KOSTAT (medio) →", fontsize=9, color=TINTA2)
    ax.set_ylim(0, 100)
    ax.set_xlim(1994, 2088)
    ax.set_ylabel("% de la población total")
    ax.set_title("Grandes grupos de edad: la población en edad de trabajar cae de 72 % a 46 %", loc="left")
    _fuente(ax, "Línea continua: estimación oficial (2000-2022). Discontinua: proyección KOSTAT 2022-2072. Cálculo: pipeline.")
    return _guardar(fig, "03_estructura_edad")


# ------------------------------------------------------------------------------------------------ 4 dependencia
def dependencia(d):
    h, p = d["fact_indicador_historico"], d["fact_indicador_proyeccion"]
    nat = p[(p.cod_indicador == "DEP_VEJEZ") & (p.cod_territorio == "00") & (p.cod_sexo == "T")
            & (p.edicion_proyeccion == "KOSTAT 2022-2072")]
    banda = nat.groupby("anio").valor.agg(["min", "max"])
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.fill_between(banda.index, banda["min"], banda["max"], color=ROJOS[1], alpha=0.55, lw=0,
                    label="Rango de los 29 escenarios KOSTAT")
    sh = _serie(h, "DEP_VEJEZ")
    sp = _serie(p, "DEP_VEJEZ", esc="medio")
    ax.plot(sh.index, sh.values, color=ROJO, label="Estimado (2000-2022)")
    ax.plot(sp.index, sp.values, color=ROJO, ls="--", label="Proyección medio")
    for anio, s in ((2000, sh), (2022, sh), (2050, sp), (2072, sp)):
        ax.annotate(f"{s[anio]:.0f}", (anio, s[anio]), xytext=(0, 8), textcoords="offset points", ha="center",
                    fontsize=10, color=TINTA, fontweight="bold")
    ax.axhline(100, color=TINTA2, ls=":", lw=1)
    ax.text(2001, 102, "100 = una persona mayor por cada persona en edad de trabajar", fontsize=9, color=TINTA2)
    ax.set_ylabel("Personas de 65+ por cada 100 de 15-64")
    ax.set_title("Tasa de dependencia de vejez", loc="left")
    ax.legend(loc="lower right")
    _fuente(ax, "Fuente: KOSTAT (estimación y 29 escenarios de proyección 2022-2072). Fórmula única del pipeline: P65+ / P15-64 × 100.")
    return _guardar(fig, "04_dependencia_vejez")


# ------------------------------------------------------------------------------------------------ 5 edad de trabajar
def edad_trabajar(d):
    h, p = d["fact_indicador_historico"], d["fact_indicador_proyeccion"]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    sh = _serie(h, "POBLACION", edad="15-64") / 1e6
    ax.plot(sh.index, sh.values, color=TINTA, label="Estimada")
    escs = [("medio", ROJO, "Medio"), ("fecundidad_baja", AZUL, "Fecundidad baja"),
            ("migracion_cero", AMBAR, "Sin migración"), ("envejecimiento_lento", VERDE, "Envejecimiento lento")]
    for e, c, n in escs:
        s = _serie(p, "POBLACION", edad="15-64", esc=e) / 1e6
        ax.plot(s.index, s.values, color=c, ls="--", label=n)
        ax.text(2073, s.iloc[-1], f"{n}: {s.iloc[-1]:.1f} M", color=TINTA, fontsize=9, va="center")
    ax.annotate(f"Máximo {sh.max():.1f} M ({sh.idxmax()})", (sh.idxmax(), sh.max()), xytext=(-60, 15),
                textcoords="offset points", fontsize=9.5, color=TINTA, arrowprops={"arrowstyle": "-", "color": GRIS})
    ax.set_xlim(1998, 2090)
    ax.set_ylim(0, 42)
    ax.set_ylabel("Millones de personas de 15-64 años")
    ax.set_title("Población en edad de trabajar según escenarios oficiales KOSTAT", loc="left")
    ax.legend(loc="lower left", ncol=5, fontsize=9)
    _fuente(ax, "Las líneas discontinuas son proyecciones oficiales KOSTAT 2022-2072 (no son cálculos del equipo).")
    return _guardar(fig, "05_poblacion_edad_trabajar")


# ------------------------------------------------------------------------------------------------ 6 fuerza laboral
def fuerza_laboral(d):
    h, fl = d["fact_indicador_historico"], d["fact_fuerza_laboral_escenario"]
    obs = _serie(h, "POB_ACTIVA", edad="15+") / 1e6
    t = fl.groupby(["cod_escenario", "cod_supuesto", "anio"]).fuerza_laboral_potencial.sum() / 1e6
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.plot(obs.index, obs.values, color=TINTA, label="Población activa observada (EAPS)")
    banda = t.xs("A_constante", level="cod_supuesto").unstack("cod_escenario").agg(["min", "max"], axis=1)
    ax.fill_between(banda.index, banda["min"], banda["max"], color=GRIS_CLARO, lw=0,
                    label="Supuesto A en los 29 escenarios de población")
    finales = {}
    for sup, c, n in (("A_constante", ROJO, "A · participación constante"), ("B_tendencia", AZUL, "B · tendencia 2015-2025"),
                      ("C_convergencia_ocde", VERDE, "C · convergencia al promedio OCDE"),
                      ("D_brecha_genero", AMBAR, "D · cierre 50 % brecha de género")):
        s = t.loc[("medio", sup)]
        ax.plot(s.index, s.values, color=c, ls="--", label=n)
        finales[sup] = s.iloc[-1]
    # etiquetas finales separadas al menos 0,9 M para que no se monten
    y_prev = None
    for sup, y in sorted(finales.items(), key=lambda kv: kv[1]):
        y_txt = y if y_prev is None else max(y, y_prev + 0.9)
        ax.text(2073, y_txt, f"{sup[0]}: {y:.1f} M", color=TINTA, fontsize=9, va="center")
        y_prev = y_txt
    ax.set_xlim(1998, 2080)
    ax.set_ylim(0, 35)
    ax.set_ylabel("Millones de personas")
    ax.set_title("Fuerza laboral potencial: escenarios propios sobre la población proyectada", loc="left")
    ax.legend(loc="lower left", fontsize=9)
    _fuente(ax, "Escenario propio del equipo (no es pronóstico): Σ población KOSTAT (sexo × edad) × cobertura EAPS × tasa de participación supuesta.")
    return _guardar(fig, "06_fuerza_laboral_escenarios")


# ------------------------------------------------------------------------------------------------ 7 participación
def participacion(d):
    h = d["fact_indicador_historico"]
    edades = ["15-19", "20-29", "30-39", "40-49", "50-59", "60+"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.1, 1]})
    for sexo, c, n, off in (("H", AZUL, "Hombres", -0.2), ("M", ROJO, "Mujeres", 0.2)):
        v = h[(h.cod_indicador == "TASA_PARTICIPACION") & (h.anio == 2025) & (h.cod_sexo == sexo)
              & (h.cod_territorio == "00")].set_index("cod_edad").valor.reindex(edades)
        b = a1.bar(np.arange(6) + off, v.values, width=0.38, color=c, label=n)
        a1.bar_label(b, fmt="%.0f", fontsize=8.5, color=TINTA, padding=2)
    a1.set_xticks(np.arange(6), edades)
    a1.set_ylim(0, 100)
    a1.set_title("Participación laboral por edad, 2025 (%)", loc="left")
    a1.legend(loc="upper right")
    for edad, c in (("60+", ROJO), ("30-39", AZUL), ("15+", TINTA)):
        s = _serie(h, "TASA_PARTICIPACION", sexo="M", edad=edad)
        a2.plot(s.index, s.values, color=c)
        a2.text(2025.5, s.iloc[-1], f"{edad}: {s.iloc[-1]:.0f} %", fontsize=9, color=TINTA, va="center")
    a2.set_xlim(1999, 2031)
    a2.set_title("Mujeres: participación 2000-2025 (%)", loc="left")
    _fuente(a1, "Fuente: KOSIS EAPS DT_1DA7012S (promedio anual publicado). Datos observados.")
    return _guardar(fig, "07_participacion_sexo_edad")


# ------------------------------------------------------------------------------------------------ 8 riesgo regional
def riesgo_regional(d):
    r = d["fact_riesgo_regional"].merge(d["dim_territorio"][["cod_territorio", "nombre_es"]], on="cod_territorio")
    r = r.sort_values("indice_riesgo")
    col = {"Alto": ROJOS[4], "Medio": ROJOS[2], "Bajo": ROJOS[1]}
    fig, ax = plt.subplots(figsize=(10, 6.4))
    b = ax.barh(r.nombre_es, r.indice_riesgo, color=[col[n] for n in r.nivel_riesgo], height=0.7)
    ax.axvline(0, color=TINTA2, lw=1)
    for rect, (_, f) in zip(b, r.iterrows()):
        ax.text(max(rect.get_width(), 0) + 0.04, rect.get_y() + 0.35,
                f"TFR {f.tfr:.2f} · 65+ {f.prop_65mas:.0f} % · Δ15-64 {f.var_pob_15_64_2052_pct:+.0f} %",
                fontsize=8, color=TINTA2, va="center", ha="left")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(-2.4, 2.6)
    ax.set_xlabel("Índice de riesgo demográfico-laboral (promedio de 6 componentes estandarizados)")
    ax.set_title("¿Qué regiones enfrentan mayor riesgo? (2025)", loc="left")
    handles = [plt.Rectangle((0, 0), 1, 1, color=col[k]) for k in ("Alto", "Medio", "Bajo")]
    ax.legend(handles, ["Riesgo alto", "Medio", "Bajo"], loc="lower right")
    _fuente(ax, "Inferencia propia (ponderación igual): TFR, % 65+, dependencia, participación, reemplazo laboral y Δ pob. 15-64 2025-2052.")
    return _guardar(fig, "08_riesgo_regional")


# ------------------------------------------------------------------------------------------------ 9 internacional
def internacional(d):
    i = d["fact_comparacion_internacional"]
    i = i[i.fuente == "WB"]
    paises = [("00", "Corea del Sur", ROJO), ("JPN", "Japón", AZUL), ("ITA", "Italia", AMBAR), ("USA", "Estados Unidos", VERDE),
              ("OED", "Miembros OCDE", PURPURA)]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.9))
    for ax, ind, tit in ((a1, "TFR", "Tasa global de fecundidad"), (a2, "PROP_65MAS", "Población de 65+ (%)")):
        for cod, n, c in paises:
            s = i[(i.cod_indicador == ind) & (i.cod_territorio == cod)].set_index("anio").valor.sort_index()
            ax.plot(s.index, s.values, color=c, lw=2.6 if cod == "00" else 1.8, label=n)
            dy = {("TFR", "ITA"): 0.025, ("TFR", "JPN"): -0.025, ("PROP_65MAS", "OED"): 0.5,
                  ("PROP_65MAS", "USA"): -0.5}.get((ind, cod), 0)
            ax.text(s.index[-1] + 0.4, s.iloc[-1] + dy, f"{s.iloc[-1]:.2f}" if ind == "TFR" else f"{s.iloc[-1]:.0f}",
                    fontsize=8.5, color=TINTA, va="center")
        ax.set_title(tit, loc="left")
        ax.set_xlim(1999, 2028)
    a1.legend(loc="upper right", fontsize=9)
    _fuente(a1, "Fuente: World Bank WDI (comparación internacional, mismo productor para todos los países).")
    return _guardar(fig, "09_comparacion_internacional")


# ------------------------------------------------------------------------------------------------ 10 productividad
def productividad(d):
    h, i = d["fact_indicador_historico"], d["fact_comparacion_internacional"]
    prod = i[(i.cod_indicador == "PIB_HORA") & (i.cod_territorio == "00")].set_index("anio").valor
    p65 = _serie(h, "PROP_65MAS")
    df = pd.concat({"pib_hora": prod, "p65": p65}, axis=1).dropna()
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    ax.plot(df.p65, df.pib_hora, color=GRIS, lw=1)
    sc = ax.scatter(df.p65, df.pib_hora, c=df.index, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("r", ROJOS[1:]),
                    s=60, edgecolor="white", linewidth=1.5, zorder=3)
    for a in (df.index.min(), df.index.max()):
        ax.annotate(str(a), (df.p65[a], df.pib_hora[a]), xytext=(6, -12), textcoords="offset points", fontsize=9, color=TINTA)
    r = np.corrcoef(df.p65, df.pib_hora)[0, 1]
    ax.text(0.03, 0.95, f"r de Pearson = {r:.2f} (n = {len(df)})\nAsociación temporal, no causalidad:\nambas series crecen con el tiempo.",
            transform=ax.transAxes, va="top", fontsize=9.5, color=TINTA)
    ax.set_xlabel("Población de 65+ (% del total)")
    ax.set_ylabel("PIB por hora trabajada (USD PPA constantes)")
    ax.set_title("Envejecimiento y productividad laboral", loc="left")
    fig.colorbar(sc, ax=ax, label="Año", shrink=0.8)
    _fuente(ax, "Fuentes: OECD Productivity Database (maestra) y KOSTAT (estimación de población).")
    return _guardar(fig, "10_productividad_envejecimiento")


# ------------------------------------------------------------------------------------------------ 11 reemplazo laboral
def reemplazo(d):
    h, p = d["fact_indicador_historico"], d["fact_indicador_proyeccion"]
    sh, sp = _serie(h, "IND_REEMPLAZO_LABORAL"), _serie(p, "IND_REEMPLAZO_LABORAL", esc="medio")
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(sh.index, sh.values, color=AZUL)
    ax.plot(sp.index, sp.values, color=AZUL, ls="--")
    ax.axhline(100, color=TINTA2, ls=":", lw=1)
    todo = pd.concat([sh, sp]).sort_index()
    ax.fill_between(todo.index, todo.values, 100, where=todo.values < 100, color=ROJOS[0], lw=0, interpolate=True)
    for anio, s in ((2000, sh), (2022, sh), (2040, sp), (2072, sp)):
        ax.annotate(f"{s[anio]:.0f}", (anio, s[anio]), xytext=(0, 8), textcoords="offset points", ha="center",
                    fontsize=10, color=TINTA, fontweight="bold")
    ax.text(2001, 104, "100 = por cada persona que se acerca al retiro entra una joven", fontsize=9, color=TINTA2)
    ax.set_ylabel("Pob. 15-24 por cada 100 de 55-64")
    ax.set_title("Señal temprana de escasez: índice de reemplazo de la fuerza laboral", loc="left")
    _fuente(ax, "Cálculo del pipeline sobre estimación (continua) y proyección KOSTAT medio (discontinua).")
    return _guardar(fig, "11_reemplazo_laboral")


# ------------------------------------------------------------------------------------------------ 12 esperanza de vida
def esperanza_vida(d):
    h = d["fact_indicador_historico"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for sexo, c, n in (("M", ROJO, "Mujeres"), ("T", TINTA, "Total"), ("H", AZUL, "Hombres")):
        s = _serie(h, "ESPERANZA_VIDA", sexo=sexo)
        ax.plot(s.index, s.values, color=c, lw=2.4 if sexo == "T" else 1.8)
        ax.text(s.index[-1] + 0.6, s.iloc[-1], f"{n} {s.iloc[-1]:.1f}", fontsize=9, color=TINTA, va="center")
        if sexo == "T":
            ax.annotate(f"{s.iloc[0]:.1f}", (s.index[0], s.iloc[0]), xytext=(0, -14), textcoords="offset points",
                        fontsize=9, color=TINTA, ha="center")
    ax.set_xlim(1968, 2033)
    ax.set_ylabel("Años")
    ax.set_title("Esperanza de vida al nacer: +21 años desde 1970", loc="left")
    _fuente(ax, "Fuente: KOSIS DT_1B8000F. La tabla de vida 2025 aún no estaba publicada a la fecha de descarga.")
    return _guardar(fig, "12_esperanza_vida")


# ------------------------------------------------------------------------------------------------ 13 calidad
def calidad(conteos: pd.DataFrame, conc: pd.DataFrame):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.2, 1]})
    pasos = conteos[conteos.capa == "silver"].groupby("paso", sort=False)[["filas_entrada", "filas_salida"]].sum()
    claves = [("formato largo (melt)", "Celdas en formato largo"),
              ("descartar columnas no anuales (meses) y columnas vacías", "Sólo periodos anuales"),
              ("selección de variables mapeadas (items_kosis.csv)", "Variables del estudio"),
              ("excluir unidades territoriales fuera de alcance", "Territorios en alcance"),
              ("separar celdas sin dato (no se imputan)", "Con dato (sin imputar)"),
              ("reglas de aceptación", "Válidos (85+ agregado y reglas)")]
    vals = [pasos.loc[k, "filas_salida"] for k, _ in claves if k in pasos.index]
    nombres = [n for k, n in claves if k in pasos.index]
    b = a1.barh(nombres[::-1], vals[::-1], color=[ROJOS[min(i, 5)] for i in range(1, len(vals) + 1)][::-1], height=0.65)
    a1.bar_label(b, labels=[f"{v:,.0f}".replace(",", ".") for v in vals[::-1]], padding=3, fontsize=9, color=TINTA)
    a1.set_title("Embudo KOSIS: registros tras cada transformación", loc="left")
    a1.grid(axis="y", visible=False)
    a1.set_xlim(0, max(vals) * 1.25)
    c = conc[conc.comparable & conc.anio.between(2000, 2025) & conc.fuente_contraste.isin(["WB", "OECD"])]
    grupos = c.groupby("fuente_contraste").dif_pct.apply(lambda s: s.abs().values)
    a2.boxplot(list(grupos.values), tick_labels=list(grupos.index), orientation="horizontal", widths=0.5,
               boxprops={"color": AZUL}, medianprops={"color": ROJO, "lw": 2}, flierprops={"markeredgecolor": GRIS})
    a2.axvline(3, color=ROJO, ls=":", lw=1.2)
    a2.text(3.05, 0.55, "tolerancia ±3 %", color=TINTA2, fontsize=9)
    a2.set_xlabel("|diferencia| maestra vs contraste (%)")
    a2.set_title("Conciliación con fuentes externas", loc="left")
    a2.text(0.98, 0.02, "Contrastes internos KOSIS: diferencia 0 % (máx. 0,64 % por redondeo)", transform=a2.transAxes,
            ha="right", fontsize=8.5, color=TINTA2)
    return _guardar(fig, "13_calidad_pipeline")


def generar_todas() -> list:
    d = datos()
    from src.utils.config import RAIZ
    conteos = pd.read_parquet(RAIZ / "data" / "ctl" / "conteos.parquet")
    salidas = [f(d) for f in (natalidad, piramides, estructura, dependencia, edad_trabajar, fuerza_laboral, participacion,
                              riesgo_regional, internacional, productividad, reemplazo, esperanza_vida)]
    salidas.append(calidad(conteos, d["fact_conciliacion"]))
    return salidas


if __name__ == "__main__":
    for p in generar_todas():
        print(p)
