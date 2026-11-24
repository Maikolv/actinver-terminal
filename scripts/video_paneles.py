"""Paneles del video con estética de terminal (fondos oscuros y rojo de Actinver Terminal, Consolas): las gráficas y tablas del informe rehechas con
el mismo diseño, colores y fuente del video. Datos reales del Reto (data/medios/informe/*.json, privados).

    uv run --with matplotlib python scripts/video_paneles.py   → data/medios/video/paneles/*.png (1060×770)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
INF = RAIZ / "data" / "medios" / "informe"
SAL = RAIZ / "data" / "medios" / "video" / "paneles"
W, H = 1060, 770
# Paleta de Actinver Terminal (DESIGN.md, tema oscuro); AMBAR conserva el nombre pero es el rojo de identidad.
NEGRO, PANEL, AMBAR, BLANCO, GRIS, LINEA = "#090a0c", "#121419", "#d94848", "#f3f4f6", "#b4bac4", "#343942"
VERDE, ROJO, AZUL = "#4cc38a", "#f2777a", "#c9ced6"
FONDO_DIR = Path("C:/Windows/Fonts")
for f in ("consola.ttf", "consolab.ttf"):
    if (FONDO_DIR / f).exists():
        font_manager.fontManager.addfont(str(FONDO_DIR / f))
plt.rcParams.update({"font.family": "Consolas", "text.color": BLANCO, "axes.labelcolor": GRIS, "xtick.color": GRIS,
                     "ytick.color": GRIS, "axes.edgecolor": LINEA, "axes.facecolor": PANEL, "figure.facecolor": NEGRO,
                     "axes.grid": True, "grid.color": LINEA, "grid.linewidth": 0.6, "font.size": 13})


def fuente(n, negrita=False):
    try:
        return ImageFont.truetype(str(FONDO_DIR / ("consolab.ttf" if negrita else "consola.ttf")), n)
    except OSError:
        return ImageFont.load_default()


def figura():
    return plt.figure(figsize=(W / 100, H / 100), dpi=100)


def guardar(fig, nombre):
    fig.savefig(SAL / f"{nombre}.png", facecolor=NEGRO); plt.close(fig)


def encabezado(fig, texto, sub=""):
    fig.text(0.02, 0.955, texto, color=AMBAR, fontsize=20, weight="bold", va="center")
    if sub:
        fig.text(0.98, 0.955, sub, color=GRIS, fontsize=12, ha="right", va="center")


def lienzo(titulo, sub=""):
    im = Image.new("RGB", (W, H), NEGRO); d = ImageDraw.Draw(im)
    d.text((22, 18), titulo, font=fuente(26, True), fill=AMBAR)
    if sub:
        d.text((W - 22, 24), sub, font=fuente(17), fill=GRIS, anchor="ra")
    d.line([(22, 62), (W - 22, 62)], fill=AMBAR, width=2)
    return im, d


def main() -> None:
    SAL.mkdir(parents=True, exist_ok=True)
    d = json.loads((INF / "datos.json").read_text(encoding="utf-8"))
    fm = json.loads((INF / "fundamentales_mu.json").read_text(encoding="utf-8"))
    sym = lambda i: i.split(":")[1]  # noqa: E731

    # 1. Distribución inicial: dona + leyenda con sector.
    ini = d["inicial"]["posiciones"]
    fig = figura(); encabezado(fig, "DISTRIBUCIÓN INICIAL DEL CAPITAL", "CAPTURA DEL PORTAL · 05-OCT-2026")
    ax = fig.add_axes([0.03, 0.06, 0.5, 0.82]); ax.set_facecolor(NEGRO)
    col = [AMBAR, BLANCO, "#7c828d", "#b42626", "#f06a6a", "#4a505a"]
    ax.pie([x["valor"] for x in ini], colors=col, startangle=90, counterclock=False,
           wedgeprops={"width": 0.33, "edgecolor": NEGRO, "linewidth": 3})
    ax.text(0, 0.08, "$1,000,000", ha="center", fontsize=22, weight="bold", color=BLANCO)
    ax.text(0, -0.14, "MXN SIMULADOS", ha="center", fontsize=12, color=GRIS)
    for k, (x, c) in enumerate(zip(ini, col)):
        y = 0.80 - k * 0.12
        fig.patches.append(plt.Rectangle((0.56, y - 0.012), 0.018, 0.035, color=c, transform=fig.transFigure))
        fig.text(0.595, y, f"{sym(x['instrumento']):<8}", fontsize=19, weight="bold", color=BLANCO, va="center")
        fig.text(0.97, y, f"{x['peso'] * 100:5.1f} %", fontsize=19, weight="bold", color=c, ha="right", va="center")
        fig.text(0.595, y - 0.045, x["sector"][:34], fontsize=11, color=GRIS, va="center")
    guardar(fig, "distribucion")

    # 2. Seguimiento: movimientos del 6 al 31 de octubre + indicadores.
    oct_ = d["corte_octubre"]
    im, dr = lienzo("SEGUIMIENTO 06-OCT → 31-OCT", "9 MOVIMIENTOS · CAPTURAS DEL PORTAL")
    for k, (et, val, c) in enumerate([("VALOR AL 30-OCT", f"${oct_['valor']:,.2f}", BLANCO), ("RENDIMIENTO", f"{oct_['rend'] * 100:+.2f} %", ROJO)]):
        x = 22 + k * 520
        dr.rectangle([x, 80, x + 495, 175], outline=LINEA, width=2)
        dr.text((x + 18, 92), et, font=fuente(18), fill=GRIS)
        dr.text((x + 18, 118), val, font=fuente(40, True), fill=c)
    cab = ["FECHA", "EMISORA", "OPERACIÓN", "TÍTULOS"]
    xs = [30, 260, 470, 720]
    for x, t in zip(xs, cab):
        dr.text((x, 200), t, font=fuente(18, True), fill=AMBAR)
    dr.line([(22, 228), (W - 22, 228)], fill=LINEA, width=1)
    for i, m in enumerate(d["movimientos_octubre"]):
        y = 240 + i * 55
        if i % 2:
            dr.rectangle([22, y - 8, W - 22, y + 42], fill="#1b1e24")
        c = VERDE if m["tipo"] == "compra" else ROJO
        dr.text((xs[0], y), m["fecha"], font=fuente(22), fill=BLANCO)
        dr.text((xs[1], y), sym(m["instrumento"]), font=fuente(22, True), fill=BLANCO)
        dr.text((xs[2], y), ("▲ COMPRA" if m["tipo"] == "compra" else "▼ VENTA"), font=fuente(22, True), fill=c)
        dr.text((xs[3], y), f"{m['de']:,.0f} → {m['a']:,.0f}", font=fuente(22), fill=BLANCO)
    im.save(SAL / "seguimiento.png")

    # 3. Técnico de MU: precio con medias, RSI y MACD (cierres guardados por la terminal).
    import pandas as pd  # noqa: PLC0415
    import sqlite3  # noqa: PLC0415
    con = sqlite3.connect(f"file:{RAIZ / 'data' / 'archivo' / d['archivo']}?mode=ro", uri=True)
    mu = pd.Series({pd.Timestamp(f): p for f, p in con.execute(
        "SELECT fecha, cierre FROM precios WHERE instrumento_id='SIC:MU' AND fecha BETWEEN '2026-05-01' AND '2026-11-13' "
        "AND tipo_dato='cierre' ORDER BY fecha")}).groupby(level=0).last()
    dif = mu.diff(); up = dif.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-dif.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn)
    macd = mu.ewm(span=12, adjust=False).mean() - mu.ewm(span=26, adjust=False).mean(); senal = macd.ewm(span=9, adjust=False).mean()
    v = mu.index >= mu.index[-1] - pd.Timedelta(days=92)
    fig = figura(); encabezado(fig, "MU US · MICRON · 3 MESES", "CIERRES EN USD · TIINGO/ALPACA")
    g = fig.add_gridspec(3, 1, height_ratios=[3, 1, 1], left=0.07, right=0.98, top=0.9, bottom=0.07, hspace=0.12)
    a1, a2, a3 = fig.add_subplot(g[0]), fig.add_subplot(g[1]), fig.add_subplot(g[2])
    a1.plot(mu[v].index, mu[v], color=AMBAR, lw=2.2, label="CIERRE")
    a1.plot(mu[v].index, mu.rolling(20).mean()[v], color=AZUL, lw=1.4, label="SMA 20")
    a1.plot(mu[v].index, mu.rolling(50).mean()[v], color="#f06a6a", lw=1.4, label="SMA 50")
    a1.legend(frameon=False, fontsize=12, loc="upper left", labelcolor=BLANCO, ncol=3)
    a1.annotate(f"{mu.iloc[-1]:.2f}", (mu.index[-1], mu.iloc[-1]), color=NEGRO, fontsize=12, weight="bold",
                xytext=(-10, 14), textcoords="offset points", ha="right", va="center", bbox={"boxstyle": "square,pad=0.2", "fc": AMBAR, "ec": AMBAR})
    a2.plot(rsi[v].index, rsi[v], color=VERDE, lw=1.4); a2.axhline(70, color=ROJO, lw=0.8, ls="--"); a2.axhline(30, color=VERDE, lw=0.8, ls="--")
    a2.set_ylabel("RSI 14"); a2.set_ylim(10, 90)
    h = (macd - senal)[v]
    a3.bar(h.index, h, color=[VERDE if x >= 0 else ROJO for x in h], width=1)
    a3.plot(macd[v].index, macd[v], color=AMBAR, lw=1.3); a3.plot(senal[v].index, senal[v], color=AZUL, lw=1.1); a3.set_ylabel("MACD")
    for a in (a1, a2):
        a.tick_params(labelbottom=False)
    for a in (a1, a2, a3):
        a.tick_params(labelsize=11)
    guardar(fig, "tecnico")

    # 4. Fundamentales de MU (10-K en SEC EDGAR).
    im, dr = lienzo("MU US · FUNDAMENTALES", f"10-K EJERCICIO {fm['ejercicio'][:4]} · SEC EDGAR")
    filas = [("LIQUIDEZ", "Razón circulante", f"{fm['razon_circulante']:.2f}x", VERDE),
             ("APALANCAMIENTO", "Pasivo / capital", f"{fm['pasivo_capital']:.2f}x", VERDE),
             ("OPERATIVIDAD", "Rotación de activos", f"{fm['rotacion_activos']:.2f}x", BLANCO),
             ("RENTABILIDAD", "Margen neto", f"{fm['margen_neto'] * 100:.1f} %", VERDE),
             ("RENTABILIDAD", "ROE", f"{fm['roe'] * 100:.1f} %", VERDE),
             ("VALUACIÓN", "P/E", f"{d['tecnico_mu']['cierre'] / fm['bpa_diluido_usd']:.1f}x", AMBAR),
             ("CRECIMIENTO", "Ventas", f"{fm['crec_ventas'] * 100:+.0f} %", VERDE),
             ("COSTO-BENEFICIO", "Utilidad / precio", f"{fm['bpa_diluido_usd'] / d['tecnico_mu']['cierre'] * 100:.1f} %", AMBAR)]
    for i, (cat, nom, val, c) in enumerate(filas):
        y = 86 + i * 82
        if i % 2 == 0:
            dr.rectangle([22, y - 6, W - 22, y + 70], fill="#1b1e24")
        dr.text((40, y + 4), cat, font=fuente(17), fill=GRIS)
        dr.text((40, y + 28), nom, font=fuente(28, True), fill=BLANCO)
        dr.text((W - 44, y + 18), val, font=fuente(40, True), fill=c, anchor="ra")
    im.save(SAL / "fundamentales.png")

    # 5. Evolución del portafolio frente a NAFTRAC (base 100).
    s = pd.Series({pd.Timestamp(x["fecha"]): x["valor"] for x in d["serie"]})
    naf = pd.Series({pd.Timestamp(f): p for f, p in con.execute(
        "SELECT fecha, cierre FROM precios WHERE instrumento_id='BMV:NAFTRAC' AND fecha BETWEEN ? AND ? ORDER BY fecha",
        (s.index[0].date().isoformat(), s.index[-1].date().isoformat()))})
    fig = figura(); encabezado(fig, "PORTAFOLIO vs NAFTRAC · BASE 100", "05-OCT → 12-NOV-2026")
    ax = fig.add_axes([0.07, 0.08, 0.9, 0.8])
    base = s / d["capital_inicial"] * 100
    ax.fill_between(base.index, base, 100, where=base < 100, color=ROJO, alpha=0.18)
    ax.plot(base.index, base, color=AMBAR, lw=2.6, label="LYNX MARKET")
    ax.plot(naf.index, naf / naf.iloc[0] * 100, color=AZUL, lw=2, ls="--", label="NAFTRAC")
    ax.axhline(100, color=GRIS, lw=0.8)
    ax.legend(frameon=False, fontsize=14, labelcolor=BLANCO, loc="lower left")
    for serie, c in ((base, AMBAR), (naf / naf.iloc[0] * 100, AZUL)):
        ax.annotate(f"{serie.iloc[-1] - 100:+.2f} %", (serie.index[-1], serie.iloc[-1]), color=NEGRO, fontsize=14, weight="bold",
                    xytext=(-8, 0), textcoords="offset points", ha="right", va="center", bbox={"boxstyle": "square,pad=0.25", "fc": c, "ec": c})
    ax.tick_params(labelsize=12)
    fig.autofmt_xdate()
    guardar(fig, "evolucion")

    # 6. Rotación final: pesos y rendimiento de cada posición al 12-nov.
    fin = sorted(d["final"]["posiciones"], key=lambda x: x["peso"])
    fig = figura(); encabezado(fig, "CARTERA FINAL · CONSUMO Y SALUD", "CAPTURA DEL PORTAL · 12-NOV-2026")
    ax = fig.add_axes([0.13, 0.1, 0.62, 0.8])
    ax.barh([sym(x["instrumento"]) for x in fin], [x["peso"] * 100 for x in fin], color=[VERDE if (x["rend"] or 0) >= 0 else ROJO for x in fin], height=0.62)
    ax.set_xlabel("% DEL PORTAFOLIO"); ax.tick_params(labelsize=14); ax.grid(axis="y", visible=False)
    for k, x in enumerate(fin):
        fig.text(0.97, 0.1 + 0.8 * (k + 0.5) / len(fin), f"{(x['rend'] or 0) * 100:+6.1f} %", fontsize=15, weight="bold",
                 color=VERDE if (x["rend"] or 0) >= 0 else ROJO, ha="right", va="center")
    fig.text(0.97, 0.915, "REND.", color=GRIS, fontsize=12, ha="right")
    guardar(fig, "rotacion")
    print("paneles:", sorted(p.name for p in SAL.glob("*.png")))


if __name__ == "__main__":
    main()
