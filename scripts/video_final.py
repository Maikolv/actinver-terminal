"""Video final del concurso «Finanzas en la era de la IA» con estética de terminal financiera y las VOCES REALES del equipo.

Solo pantalla y voz en off. Cada bloque del guion combina:
  - grabaciones en video de la terminal local del equipo (scripts/grabar_terminal.cjs), o
  - paneles con los datos reales del Reto rehechos con el mismo diseño (scripts/video_paneles.py),
más barra de funciones, título que entra deslizándose, panel de datos clave fila por fila, cinta de datos en movimiento
y subtítulos sincronizados con la voz.

Entradas privadas (fuera del repositorio): data/medios/video/{voces,grabaciones,paneles}, data/medios/informe/*.json y
data/medios/equipo.json.

    uv run python scripts/video_final.py [horizontal|vertical] [4_integrantes|Miguel_y_Daniela]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
GUION = RAIZ / "docs" / "video" / "guiones-tiktok.md"
MED = RAIZ / "data" / "medios"
VOCES, GRAB, PAN = MED / "video" / "voces", MED / "video" / "grabaciones", MED / "video" / "paneles"
SAL = RAIZ / "entregables" / "video"
FPS = 25  # igual que las grabaciones: sin cuadros duplicados

# Paleta de Actinver Terminal (DESIGN.md, tema oscuro): fondos casi negros, rojo de identidad y texto claro.
NEGRO, BARRA, LINEA = (9, 10, 12), (18, 20, 25), (52, 57, 66)  # --fondo, --superficie, --borde
AMBAR, SOLIDO, MARCA = (240, 106, 106), (180, 38, 38), (217, 72, 72)  # --acento (texto), --acento-solido, --acento-grafico
BLANCO, GRIS = (243, 244, 246), (180, 186, 196)  # --texto, --texto-2
VERDE, ROJO, AZUL = (76, 195, 138), (242, 119, 122), (243, 244, 246)  # --positivo, --negativo; la terminal no usa azul
REAL, DEMO = ("DATOS REALES DEL RETO", VERDE), ("TERMINAL PROPIA · 127.0.0.1", AZUL)

VERSIONES = {
    "4_integrantes": ["Miguel 1", "Audio pt1", "valeria min 018-030", "Calle Bosques de México", "Miguel 2", "Audio pt2",
                      "valeria min 104-116", "Calle Bosques de México 2", "Miguel 3", "Audio pt3", "Valeria min 154 y 206",
                      "Miguel 5", "Calle Bosques de México 3", "Miguel 4"],
}
OPCIONALES = {"Miguel 5"}  # bloque de Telegram: si falta el audio, el video se arma sin ese bloque y lo avisa

_EQ = MED / "equipo.json"
EQ = json.loads(_EQ.read_text(encoding="utf-8")) if _EQ.exists() else {}
EQUIPO = EQ.get("integrantes", ["Miguel", "Daniela", "Valeria", "Camila"])
NOMBRE_EQUIPO = EQ.get("equipo", "")
AVISO = "Proyecto escolar independiente · no afiliado a Grupo Actinver · no es asesoría de inversión"


def mxn(x):
    return f"${x:,.0f}"


def bloques() -> list[dict]:
    """Los 14 bloques del guion: código de función, título, procedencia, contenido y datos clave (reales)."""
    d = json.loads((MED / "informe" / "datos.json").read_text(encoding="utf-8"))
    fm = json.loads((MED / "informe" / "fundamentales_mu.json").read_text(encoding="utf-8"))
    t, r, fin, bm = d["tecnico_mu"], d["riesgo"], d["final"], d["benchmark"]
    sym = lambda i: i.split(":")[1]  # noqa: E731
    pct = lambda x, s=True: f"{x * 100:+.2f} %" if s else f"{x * 100:.2f} %"  # noqa: E731
    col = lambda x: VERDE if x >= 0 else ROJO  # noqa: E731
    ini = d["inicial"]["posiciones"]
    finales = sorted(fin["posiciones"], key=lambda x: -x["peso"])[:5]
    return [
        dict(cod="TERM", titulo="ACTINVER TERMINAL", origen=DEMO, items=[("rec", "inicio")],
             datos=[("CAPITAL SIMULADO", "$1,000,000", BLANCO), ("PERIODO", "05-OCT → 12-NOV", BLANCO),
                    ("EQUIPO", NOMBRE_EQUIPO.upper() or "—", AMBAR), ("HERRAMIENTA", "PROPIA · CON IA", BLANCO)]),
        dict(cod="IA", titulo="LA IA COMO HERRAMIENTA", origen=DEMO, items=[("rec", "legal")],
             datos=[("ASISTENTES", "CLAUDE · CODEX", AZUL), ("DECISIONES", "DEL EQUIPO", AMBAR),
                    ("ÓRDENES", "CAPTURA MANUAL", BLANCO), ("FUENTES", "GRATUITAS Y LEGALES", BLANCO)]),
        dict(cod="01 PLAN", titulo="PLAN DE INVERSIÓN INICIAL", origen=REAL, items=[("panel", "distribucion")],
             datos=[(sym(x["instrumento"]), f"{x['peso'] * 100:.1f} %", AMBAR if i == 0 else BLANCO) for i, x in enumerate(ini)]),
        dict(cod="PORT", titulo="PERFIL AGRESIVO · MARKOWITZ", origen=DEMO, items=[("rec", "portafolios")],
             datos=[("PERFIL", "AGRESIVO", ROJO), ("HORIZONTE", "6 SEMANAS", BLANCO), ("MODELO", "MÁXIMO SHARPE", AZUL),
                    ("TOPE POR EMISORA", "50 %", AMBAR)]),
        dict(cod="MKT", titulo="PRECIOS CON PROCEDENCIA", origen=DEMO, items=[("rec", "mercado")],
             datos=[("FUENTE", "PROVEEDOR DECLARADO", BLANCO), ("FECHA", "CIERRE DEL DATO", BLANCO),
                    ("ESTADO", "VIGENTE / RETRASADO", AMBAR), ("SIN DATO", "NO SE INVENTA", ROJO)]),
        dict(cod="02 SEG", titulo="SEGUIMIENTO 06 → 31 OCT", origen=REAL, items=[("panel", "seguimiento")],
             datos=[("CAPTURAS DEL PORTAL", "34", BLANCO), ("MOVIMIENTOS", str(len(d["movimientos_octubre"])), BLANCO),
                    ("VALOR 30-OCT", mxn(d["corte_octubre"]["valor"]), BLANCO), ("RENDIMIENTO", pct(d["corte_octubre"]["rend"]), ROJO)]),
        dict(cod="MU US GP", titulo="ANÁLISIS TÉCNICO · MICRON", origen=REAL, items=[("rec", "tecnico"), ("panel", "tecnico")],
             datos=[("CIERRE USD", f"{t['cierre']:.2f}", AMBAR), ("SMA 20 / 50", f"{t['sma20']:.0f} / {t['sma50']:.0f}", AZUL),
                    ("RSI 14", f"{t['rsi14']:.1f}", BLANCO), ("MACD / SEÑAL", f"{t['macd']:.1f} / {t['senal']:.1f}", ROJO),
                    ("TENDENCIA", "BAJISTA", ROJO)]),
        dict(cod="MU US FA", titulo="ANÁLISIS FUNDAMENTAL", origen=REAL, items=[("rec", "ficha"), ("panel", "fundamentales")],
             datos=[("RAZÓN CIRCULANTE", f"{fm['razon_circulante']:.2f}x", VERDE), ("PASIVO / CAPITAL", f"{fm['pasivo_capital']:.2f}x", VERDE),
                    ("MARGEN NETO", f"{fm['margen_neto'] * 100:.1f} %", VERDE), ("ROE", f"{fm['roe'] * 100:.1f} %", VERDE),
                    ("P/E", f"{t['cierre'] / fm['bpa_diluido_usd']:.1f}x", AMBAR)]),
        dict(cod="03 RSK", titulo="RIESGO · DESVIACIÓN Y VaR", origen=REAL, items=[("rec", "riesgo")],
             datos=[("DESV. DIARIA", pct(r["desv_diaria"], False), AMBAR), ("DESV. ANUAL", pct(r["desv_anual"], False), AMBAR),
                    ("VaR 95 % · 1 DÍA", pct(r["var95_historico_diario"], False), ROJO), ("PEOR DÍA", pct(r["peor_dia"]), ROJO)]),
        dict(cod="PERF", titulo="RESULTADO vs MERCADO", origen=REAL, items=[("panel", "evolucion")],
             datos=[("VALOR FINAL", mxn(fin["valor"]), BLANCO), ("RENDIMIENTO", pct(fin["rend"]), ROJO),
                    ("NAFTRAC", pct(bm["rendimiento"]), VERDE), ("DIFERENCIA", f"{(fin['rend'] - bm['rendimiento']) * 100:+.2f} pp", ROJO)]),
        dict(cod="PORT", titulo="ROTACIÓN · CONSUMO Y SALUD", origen=REAL, items=[("panel", "rotacion"), ("rec", "guardados")],
             datos=[(sym(x["instrumento"]), f"{x['peso'] * 100:.1f} %", col(x["rend"] or 0)) for x in finales]),
        dict(cod="TG", titulo="AVISOS POR TELEGRAM", origen=DEMO, items=[("rec", "alertas")],
             datos=[("DERIVA", "≥ 5 PP", AMBAR), ("STOP", "-8 %", ROJO), ("TOMA DE UTILIDAD", "+15 %", VERDE),
                    ("CAÍDA DESDE MÁX.", "-10 %", ROJO), ("ÓRDENES", "NINGUNA · SOLO AVISA", BLANCO)]),
        dict(cod="BACK", titulo="LO QUE APRENDIMOS", origen=DEMO, items=[("rec", "propuestas"), ("rec", "backtesting")],
             datos=[("VENTAJA vs 1/N", "NO DEMOSTRADA", ROJO), ("LA IA", "ACELERA, NO ADIVINA", AMBAR),
                    ("PRIMERO", "MEDIR CONCENTRACIÓN", BLANCO), ("DESPUÉS", "BUSCAR RENDIMIENTO", BLANCO)]),
        dict(cod="HELP", titulo="PRUÉBALA GRATIS EN GITHUB", origen=DEMO, items=[("rec", "mesa")],
             datos=[("CÓDIGO", "GITHUB", AMBAR), ("DEMO", "GITHUB PAGES", BLANCO), ("ÓRDENES", "NINGUNA", BLANCO),
                    ("ASESORÍA", "NO ES ASESORÍA", ROJO)]),
    ]


def textos() -> list[str]:
    out = []
    for linea in GUION.read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in linea.strip().strip("|").split("|")]
        if len(c) == 4 and re.match(r"\d:\d\d–\d:\d\d", c[0]):
            out.append(re.sub(r"^«|»$", "", c[2]))
    assert len(out) == 14, f"el guion tiene {len(out)} bloques"
    return out


def cinta_texto() -> list[tuple[str, tuple]]:
    d = json.loads((MED / "informe" / "datos.json").read_text(encoding="utf-8"))
    out = [("RETO ACTINVER 2026 · DATOS DEL 05-OCT AL 12-NOV   ", GRIS),
           (f"LYNX MARKET {d['final']['valor']:,.2f} ", BLANCO), (f"▼ {abs(d['final']['rend']) * 100:.2f}%   ", ROJO),
           ("NAFTRAC ", BLANCO), (f"▲ {d['benchmark']['rendimiento'] * 100:.2f}%   ", VERDE)]
    for c in d["cerradas"] + d["final"]["posiciones"]:
        if c.get("rend") is not None and abs(c["rend"]) < 5:
            out += [(f"{c['instrumento'].split(':')[1]} ", BLANCO),
                    (f"{'▲' if c['rend'] >= 0 else '▼'} {abs(c['rend']) * 100:.1f}%   ", VERDE if c["rend"] >= 0 else ROJO)]
    if d.get("fx"):
        out += [("USD/MXN FIX ", BLANCO), (f"{d['fx']['fin'][1]:.4f}   ", AMBAR)]
    out += [(f"VaR95 1D {d['riesgo']['var95_historico_diario'] * 100:.2f}%   ", AMBAR)]
    if d.get("cetes28"):
        out += [(f"CETES 28 {d['cetes28']['valor'] * 100:.2f}%   ", AMBAR)]
    return out


# ───────────────────────────── dibujo ─────────────────────────────
def fuente(n, negrita=True):
    try:
        return ImageFont.truetype("consolab.ttf" if negrita else "consola.ttf", n)
    except OSError:
        return ImageFont.load_default()


def envolver(d, texto, f, ancho):
    lineas, actual = [], ""
    for p in texto.split():
        prueba = f"{actual} {p}".strip()
        if d.textlength(prueba, font=f) > ancho and actual:
            lineas.append(actual); actual = p
        else:
            actual = prueba
    return lineas + [actual] if actual else lineas


def trozos(texto: str, maximo: int) -> list[str]:
    frases = re.split(r"(?<=[.:;,])\s+", texto)
    out, actual = [], ""
    for f in frases:
        if actual and len(actual) + len(f) + 1 > maximo:
            out.append(actual); actual = f
        else:
            actual = f"{actual} {f}".strip()
    return out + [actual] if actual else out


def geometria(W, H, modo=None):
    """La ventana de la terminal ocupa todo el ancho; arriba, su barra de dirección (127.0.0.1:8765); abajo, fichas de datos.

    modo «tiktok»: todo centrado (x 120–960) y dentro de la zona segura de TikTok (y 190–1480): fuera de la barra
    superior «Siguiendo / Para ti», de los botones de la derecha y de la descripción de abajo."""
    if modo == "tiktok":
        g = dict(W=W, H=H, barra=84, tit_y=196, tit_h=54, tit_f=28, win=(120, 268, 840, 872), url_h=40,
                 fichas=(120, 1150, 840, 128), cols=3, sub=(120, 1288, 840, 190), sub_f=36, cinta_y=1500, cinta_h=40,
                 aviso_y=1550, aviso_f=20, max_sub=58, grab="tiktok", centro=W // 2)
    elif W > H:
        g = dict(W=W, H=H, barra=56, tit_y=70, tit_h=50, win=(20, 128, 1880, 724), url_h=44, fichas=(20, 860, 1880, 62), cols=6,
                 sub=(20, 930, 1880, 90), sub_f=32, cinta_y=1024, cinta_h=34, aviso_y=1062, aviso_f=14, max_sub=150, grab="horizontal")
    else:
        g = dict(W=W, H=H, barra=84, tit_y=100, tit_h=62, win=(10, 176, 1060, 1144), url_h=44, fichas=(10, 1330, 1060, 192), cols=2,
                 sub=(30, 1530, 1020, 260), sub_f=42, cinta_y=1798, cinta_h=46, aviso_y=1862, aviso_f=22, max_sub=80, grab="vertical")
    x, y, w, h = g["win"]
    g["cont"] = (x, y + g["url_h"], w, h - g["url_h"])  # área que muestra la grabación: mismo tamaño que el viewport grabado
    return g


def chrome(g, destino):
    """Marco fijo: barra de funciones, ventana de contenido, panel de datos, subtítulos, cinta y aviso."""
    W, H = g["W"], g["H"]
    im = Image.new("RGB", (W, H), NEGRO); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, g["barra"]], fill=BARRA)
    d.rectangle([0, g["barra"], W, g["barra"] + 3], fill=MARCA)
    f = fuente(26 if W > H else 34)
    if g.get("centro"):
        d.text((g["centro"], g["barra"] // 2), "ACTINVER TERMINAL", font=f, fill=AMBAR, anchor="mm")
    else:
        d.text((22, g["barra"] // 2), "ACTINVER TERMINAL", font=f, fill=AMBAR, anchor="lm")
    der = f"{NOMBRE_EQUIPO.upper()}  │  RETO ACTINVER 2026  │  UVM" if NOMBRE_EQUIPO else "RETO ACTINVER 2026  │  UVM"
    if not g.get("centro"):
        d.text((W - 22, g["barra"] // 2), der, font=fuente(18 if W > H else 20, False), fill=GRIS, anchor="rm")
    x, y, w, h = g["win"]
    d.rectangle([x - 2, y - 2, x + w + 1, y + h + 1], outline=LINEA, width=2)
    d.rectangle([x, y, x + w, y + g["url_h"]], fill=BARRA)  # barra del navegador
    for k, c in enumerate(((242, 119, 122), (180, 186, 196), (180, 186, 196))):
        cx = x + 22 + k * 22
        d.ellipse([cx - 6, y + 16, cx + 6, y + 28], fill=c)
    ux = x + 100
    d.rounded_rectangle([ux, y + 8, x + w - 16, y + g["url_h"] - 8], radius=13, fill=NEGRO, outline=LINEA)
    d.text((ux + 16, y + g["url_h"] // 2), "127.0.0.1:8765", font=fuente(18 if W > H else 20), fill=BLANCO, anchor="lm")
    d.text((x + w - 30, y + g["url_h"] // 2), "ACTINVER TERMINAL · LOCAL · SOLO LECTURA" if W > H else "LOCAL · SOLO LECTURA",
           font=fuente(15 if W > H else 16, False), fill=GRIS, anchor="rm")
    sx, sy, sw, sh = g["sub"]
    d.rectangle([sx, sy, sx + 6, sy + sh], fill=MARCA)
    d.rectangle([0, g["cinta_y"], W, g["cinta_y"] + g["cinta_h"]], fill=BARRA)
    d.line([(0, g["cinta_y"]), (W, g["cinta_y"])], fill=LINEA)
    for i, l in enumerate(envolver(d, AVISO, fuente(g["aviso_f"], False), W - 40)):
        d.text((W // 2, g["aviso_y"] + i * (g["aviso_f"] + 6)), l, font=fuente(g["aviso_f"], False), fill=GRIS, anchor="mt")
    im.save(destino)


def tira_titulo(b, g, destino):
    f, h = fuente(g.get("tit_f") or (30 if g["W"] > g["H"] else 34)), g["tit_h"]
    cod, tit, (etq, cetq) = f" {b['cod']} ", f"  {b['titulo']}", b["origen"]
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    fe = fuente(16 if g["W"] > g["H"] else 20)
    w_cod, w_tit, w_etq = tmp.textlength(cod, font=f), tmp.textlength(tit, font=f), tmp.textlength(etq, font=fe) + 24
    ancho = int(w_cod + w_tit + 30 + w_etq) + 4
    while ancho > g["win"][2] and f.size > 18:  # se achica hasta caber en la ventana: nada queda cortado
        f, fe = fuente(f.size - 1), fuente(max(12, fe.size - 1))
        w_cod, w_tit, w_etq = tmp.textlength(cod, font=f), tmp.textlength(tit, font=f), tmp.textlength(etq, font=fe) + 24
        ancho = int(w_cod + w_tit + 30 + w_etq) + 4
    im = Image.new("RGBA", (ancho, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w_cod, h], fill=SOLIDO, outline=MARCA, width=2)
    d.text((0, h // 2), cod, font=f, fill=BLANCO, anchor="lm")
    d.rectangle([w_cod, 0, w_cod + w_tit + 16, h], fill=BARRA)
    d.text((w_cod, h // 2), tit, font=f, fill=BLANCO, anchor="lm")
    x = w_cod + w_tit + 30
    d.rectangle([x, h // 2 - 15, x + w_etq, h // 2 + 15], outline=cetq, width=2)
    d.text((x + 12, h // 2), etq, font=fe, fill=cetq, anchor="lm")
    im.save(destino)
    return im.width


def ficha_dato(et, val, color, ancho, alto, g, destino):
    """Ficha de un dato clave: etiqueta arriba, valor abajo, con el acento rojo de la terminal a la izquierda."""
    grande = g["W"] > g["H"]
    im = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, ancho - 1, alto - 1], fill=BARRA, outline=LINEA)
    d.rectangle([0, 0, 4, alto - 1], fill=MARCA)
    d.text((16, 6), et, font=fuente(15 if grande else 17, False), fill=GRIS, anchor="lt")
    fv = fuente(26 if grande else 28)
    while d.textlength(val, font=fv) > ancho - 28 and fv.size > 14:
        fv = fuente(fv.size - 2)
    d.text((16, alto - 6), val, font=fv, fill=color, anchor="lb")
    im.save(destino)


def subtitulo(texto, g, destino):
    sx, sy, sw, sh = g["sub"]
    f = fuente(g["sub_f"])
    im = Image.new("RGBA", (sw - 30, sh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    lineas = envolver(d, texto, f, sw - 60)
    alto = len(lineas) * int(f.size * 1.3)
    y = (sh - alto) // 2
    for l in lineas:
        if g.get("centro"):
            d.text(((sw - 30) // 2, y), l, font=f, fill=BLANCO, anchor="ma")
        else:
            d.text((12, y), l, font=f, fill=BLANCO)
        y += int(f.size * 1.3)
    im.save(destino)


def cinta(g, destino):
    f = fuente(20 if g["W"] > g["H"] else 26)
    partes = cinta_texto()
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    seg = int(sum(tmp.textlength(t, font=f) for t, _ in partes)) + 40
    im = Image.new("RGBA", (seg * 2 + g["W"], g["cinta_h"]), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0
    while x < im.width:
        for t, c in partes:
            d.text((x, g["cinta_h"] // 2), t, font=f, fill=c, anchor="lm"); x += tmp.textlength(t, font=f)
        x += 40
    im.save(destino)
    return seg


def tarjeta(lineas, g, destino):
    """Tarjeta de portada o créditos: devuelve una capa por línea para revelarlas una a una."""
    W, H = g["W"], g["H"]
    capas = []
    y = H * 0.34
    for i, (texto, tam, color) in enumerate(lineas):
        f = fuente(tam if W > H or g.get("centro") else int(tam * 1.2), negrita=tam >= 30)
        im = Image.new("RGBA", (W, int(f.size * 1.5) + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((g.get("centro", W // 2), 4), texto, font=f, fill=color, anchor="mt")
        p = Path(f"{destino}_{i}.png"); im.save(p); capas.append((p, int(y)))
        y += f.size * 1.5 + 14
    return capas


# ───────────────────────────── video ─────────────────────────────
def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True)


def duracion(f) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True).stdout)


def audio(origen, destino, pausa=0.5):
    ff("-i", origen, "-af", f"highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur={pausa}", "-ar", 48000, "-ac", 2, destino)


def silencio(seg, destino):
    ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", seg, destino)


def voces() -> dict[str, Path]:
    return {unicodedata.normalize("NFC", f.name).removesuffix(".m4a.mp4"): f for f in VOCES.glob("*.mp4")}


CODEC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", FPS]


def contenido(items, D, cw, ch, t, destino, grab):
    """Clip de la ventana de contenido: grabaciones con desplazamiento real o paneles con revelado y acercamiento lento."""
    marcas = json.loads((grab / "marcas.json").read_text(encoding="utf-8"))
    partes = []
    for k, (tipo, nombre) in enumerate(items):
        d = D / len(items)
        out = t / f"c{k}.mp4"
        if tipo == "rec":
            src = grab / f"{nombre}.webm"
            ss = marcas.get(nombre, 0)
            # La grabación ya tiene el tamaño de la ventana y dura lo necesario: sin recorte, escala ni cámara lenta.
            ff("-ss", ss, "-i", src, "-vf", f"scale={cw}:{ch}:flags=lanczos,fps={FPS},"
               f"tpad=stop_mode=clone:stop_duration={d + 1},fade=t=in:st=0:d=0.35",
               "-t", f"{d:.3f}", "-an", *CODEC, out)
        else:
            png = PAN / f"{nombre}.png"
            n = int(d * FPS)
            ff("-loop", 1, "-framerate", FPS, "-t", f"{d:.3f}", "-i", png,
               "-f", "lavfi", "-t", f"{d:.3f}", "-i", f"color=c=0x090A0C:s={cw}x{ch}:r={FPS}",
               "-f", "lavfi", "-t", f"{d:.3f}", "-i", f"color=c=0xD94848:s=4x{ch}:r={FPS}",
               "-filter_complex",
               f"[0:v]scale={cw * 2}:{ch * 2}:force_original_aspect_ratio=decrease,pad={cw * 2}:{ch * 2}:(ow-iw)/2:(oh-ih)/2:color=0x090A0C,zoompan=z='1+0.05*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={cw}x{ch}:fps={FPS}[z];"
               f"[z][1:v]overlay=x='{cw}*min(max((t-0.15)/1.1,0),1)':y=0[a];"
               f"[a][2:v]overlay=x='{cw}*min(max((t-0.15)/1.1,0),1)-4':y=0:enable='lt(t,1.3)'",
               "-t", f"{d:.3f}", *CODEC, out)
        partes.append(out)
    lista = t / "lista_c.txt"
    lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
    ff("-f", "concat", "-safe", 0, "-i", lista, "-c", "copy", destino)


def segmento(b, texto, wav, g, base, t, offset, destino):
    """Un bloque completo: marco + contenido + título + datos + subtítulos + cinta, con la voz."""
    D = duracion(wav)
    W, H = g["W"], g["H"]
    wx, wy, cw, ch = g["cont"]
    contenido(b["items"], D, cw, ch, t, t / "contenido.mp4", GRAB / g["grab"])
    ancho_tit = tira_titulo(b, g, t / "titulo.png")
    tx = (W - ancho_tit) // 2 if g.get("centro") else g.get("tit_x", 22)
    entradas = ["-loop", 1, "-framerate", FPS, "-t", f"{D:.3f}", "-i", base["chrome"], "-i", t / "contenido.mp4",
                "-loop", 1, "-framerate", FPS, "-t", f"{D:.3f}", "-i", t / "titulo.png",
                "-loop", 1, "-framerate", FPS, "-t", f"{D:.3f}", "-i", base["cinta"]]
    fil = [f"[0:v][1:v]overlay={wx}:{wy}[v0]",
           f"[v0][2:v]overlay=x='if(lt(t,0.45),-w+({ancho_tit}+{tx})*t/0.45,{tx})':y={g['tit_y']}[v1]",
           f"[v1][3:v]overlay=x='-mod((t+{offset:.3f})*110,{base['seg']})':y={g['cinta_y']}[v2]"]
    n, ultimo = 4, "v2"
    fx, fy, fw, fh = g["fichas"]
    cols = min(g["cols"], len(b["datos"]))
    filas_f = -(-len(b["datos"]) // cols)
    gap = 8
    aw, ah = (fw - gap * (cols - 1)) // cols, (fh - gap * (filas_f - 1)) // filas_f
    for k, (et, val, c) in enumerate(b["datos"]):
        p = t / f"ficha{k}.png"; ficha_dato(et, val, c, aw, ah, g, p)
        entradas += ["-loop", 1, "-framerate", FPS, "-t", f"{D:.3f}", "-i", p]
        t0 = 0.6 + k * 0.25
        x0, y0 = fx + (k % cols) * (aw + gap), fy + (k // cols) * (ah + gap)
        if g.get("centro"):  # la última fila incompleta también queda centrada
            en_fila = min(cols, len(b["datos"]) - (k // cols) * cols)
            x0 += (fw - (en_fila * aw + (en_fila - 1) * gap)) // 2
        fil.append(f"[{ultimo}][{n}:v]overlay=x={x0}:y='{y0}+max(0,{t0 + 0.25}-t)*120':enable='gte(t,{t0})'[f{k}]")
        ultimo, n = f"f{k}", n + 1
    partes = trozos(texto, g["max_sub"])
    total = sum(len(p) for p in partes)
    t_ini = 0.0
    sx, sy, sw, sh = g["sub"]
    for j, parte in enumerate(partes):
        p = t / f"sub{j}.png"; subtitulo(parte, g, p)
        dur = (D - 0.5) * len(parte) / total
        entradas += ["-loop", 1, "-framerate", FPS, "-t", f"{D:.3f}", "-i", p]
        fin = D if j == len(partes) - 1 else t_ini + dur
        fil.append(f"[{ultimo}][{n}:v]overlay=x={sx + (15 if g.get('centro') else 22)}:y={sy}:enable='between(t,{t_ini:.3f},{fin:.3f})'[s{j}]")
        ultimo, n, t_ini = f"s{j}", n + 1, t_ini + dur
    largo = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength("ACTINVER TERMINAL", font=fuente(26 if W > H else 34)))
    cursor = g["centro"] + largo // 2 + 10 if g.get("centro") else 22 + largo + 10
    fil.append(f"[{ultimo}]drawbox=x={cursor}:y={g['barra'] // 2 - 12}:w=12:h=24:color=0xD94848:t=fill:enable='lt(mod(t,1),0.5)',"
               f"fade=t=in:st=0:d=0.25,format=yuv420p[out]")
    entradas += ["-i", wav]
    ff(*entradas, "-filter_complex", ";".join(fil), "-map", "[out]", "-map", f"{n}:a", "-t", f"{D:.3f}",
       *CODEC, "-c:a", "aac", "-b:a", "192k", "-ar", 48000, destino)
    return D


def tarjeta_video(lineas, seg, g, t, nombre, destino):
    capas = tarjeta(lineas, g, t / nombre)
    W, H = g["W"], g["H"]
    entradas = ["-f", "lavfi", "-t", seg, "-i", f"color=c=0x090A0C:s={W}x{H}:r={FPS}"]
    fil, ultimo = [], "0:v"
    for k, (p, y) in enumerate(capas):
        entradas += ["-loop", 1, "-framerate", FPS, "-t", seg, "-i", p]
        t0 = 0.2 + k * 0.45
        fil.append(f"[{ultimo}][{k + 1}:v]overlay=x=0:y='{y}+max(0,{t0 + 0.3}-t)*60':enable='gte(t,{t0})'[l{k}]")
        ultimo = f"l{k}"
    # Línea ámbar que crece de izquierda a derecha.
    entradas += ["-f", "lavfi", "-t", seg, "-i", f"color=c=0xD94848:s={W}x4:r={FPS}"]
    fil.append(f"[{ultimo}][{len(capas) + 1}:v]overlay=x='-W+W*min(t/1.2,1)':y={int(H * 0.30)}[a]")
    fil.append(f"[a]fade=t=in:st=0:d=0.3,fade=t=out:st={seg - 0.4}:d=0.4,format=yuv420p[out]")
    silencio(seg, t / f"{nombre}.wav")
    entradas += ["-i", t / f"{nombre}.wav"]
    ff(*entradas, "-filter_complex", ";".join(fil), "-map", "[out]", "-map", f"{len(capas) + 2}:a", "-t", seg,
       *CODEC, "-c:a", "aac", "-b:a", "192k", "-ar", 48000, destino)


def render(version: str, W: int, H: int, modo=None):
    archivos = VERSIONES[version]
    disponibles = voces()
    falta = [a for a in archivos if a not in disponibles and a not in OPCIONALES]
    if falta:
        sys.exit(f"Faltan audios en {VOCES}: {falta}")
    SAL.mkdir(parents=True, exist_ok=True)
    destino = SAL / f"Video_Actinver_Terminal_{version}_{modo or ('vertical' if H > W else 'horizontal')}.mp4"
    g = geometria(W, H, modo)
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        base = {"chrome": t / "chrome.png", "cinta": t / "cinta.png"}
        chrome(g, base["chrome"]); base["seg"] = cinta(g, base["cinta"])
        partes = [t / "intro.mp4"]
        tarjeta_video([("ACTINVER TERMINAL", 76, AMBAR), ("RETO ACTINVER 2026 · FINANZAS EN LA ERA DE LA IA", 30, BLANCO),
                       *([(f"EQUIPO {NOMBRE_EQUIPO.upper()}", 34, AMBAR)] if NOMBRE_EQUIPO else []),
                       ("UNIVERSIDAD DEL VALLE DE MÉXICO · CAMPUS HISPANO", 22, GRIS)], 3.5, g, t, "intro", partes[0])
        offset = 0.0
        for i, (b, texto, arch) in enumerate(zip(bloques(), textos(), archivos)):
            if arch not in disponibles:
                print(f"  AVISO: falta el audio «{arch}»; el bloque {b['titulo']} queda fuera de este video", flush=True)
                continue
            st = t / f"b{i:02d}"; st.mkdir()
            wav = st / "voz.wav"; audio(disponibles[arch], wav)
            out = t / f"seg{i:02d}.mp4"
            offset += segmento(b, texto, wav, g, base, st, offset, out)
            partes.append(out)
            print(f"  {version} {W}x{H} bloque {i + 1}/{len(archivos)}", flush=True)
        partes.append(t / "fin.mp4")
        tarjeta_video([(f"EQUIPO {NOMBRE_EQUIPO.upper()}".strip(), 44, AMBAR), *[(n.upper(), 26, BLANCO) for n in EQUIPO],
                       ("LIC. EN CONTADURÍA Y FINANZAS PÚBLICAS · UVM CAMPUS HISPANO", 20, GRIS),
                       ("GITHUB.COM/MAIKOLV/ACTINVER-TERMINAL", 24, AMBAR),
                       ("PANTALLAS: GRABADAS EN NUESTRA TERMINAL · CIFRAS DEL RETO: REALES", 18, GRIS),
                       (AVISO.upper(), 16, GRIS)], 6.0, g, t, "fin", partes[-1])
        lista = t / "lista.txt"
        lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
        ff("-f", "concat", "-safe", 0, "-i", lista, "-c", "copy", "-movflags", "+faststart", destino)
    print(destino, f"{duracion(destino):.1f} s", flush=True)


def necesidades():
    """Segundos que debe durar cada grabación (la versión más larga manda) → grabaciones/necesarios.json."""
    disp, out = voces(), {}
    for archivos in VERSIONES.values():
        for b, arch in zip(bloques(), archivos):
            d = ((duracion(disp[arch]) if arch in disp else 14.0) + 0.5) / len(b["items"])  # sin audio todavía: 14 s
            for tipo, nombre in b["items"]:
                if tipo == "rec":
                    out[nombre] = round(max(out.get(nombre, 0), d), 2)
    (GRAB / "necesarios.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    if "necesidades" in sys.argv:
        necesidades(); sys.exit()
    formatos = [a for a in sys.argv[1:] if a in ("horizontal", "vertical", "tiktok")] or ["horizontal", "vertical", "tiktok"]
    versiones = [a for a in sys.argv[1:] if a in VERSIONES] or list(VERSIONES)
    for version in versiones:
        if "horizontal" in formatos:
            render(version, 1920, 1080)
        if "vertical" in formatos:
            render(version, 1080, 1920)
        if "tiktok" in formatos:
            render(version, 1080, 1920, "tiktok")
