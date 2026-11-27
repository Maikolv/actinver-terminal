"""Miniaturas del video del concurso: YouTube (1280×720) y portada de TikTok (1080×1920).

Usan una captura real de Actinver Terminal (velas de MU en «Ficha técnica», grabación local) y las cifras reales del Reto.
Paleta de la terminal (DESIGN.md): fondo #090a0c, superficie #121419, rojo de identidad #d94848.
    uv run python scripts/miniaturas.py   → entregables/miniaturas/{miniatura_youtube,portada_tiktok}.png
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
MED = RAIZ / "data" / "medios"
SAL = RAIZ / "entregables" / "miniaturas"
NEGRO, SUP, LINEA = (9, 10, 12), (18, 20, 25), (52, 57, 66)
ROJO, ROJO_OSC, BLANCO, GRIS, VERDE, AMBAR = (217, 72, 72), (150, 30, 30), (243, 244, 246), (170, 176, 186), (76, 195, 138), (240, 182, 80)
F = "C:/Windows/Fonts/"


def fuente(nombre, n):
    return ImageFont.truetype(F + nombre, n)


def captura() -> Image.Image:
    """Cuadro real de la grabación vertical de «Ficha técnica» (MU): velas, medias y Bollinger."""
    g = MED / "video" / "grabaciones" / "vertical"
    m = json.loads((g / "marcas.json").read_text(encoding="utf-8"))["tecnico"]
    destino = MED / "miniaturas" / "fuente_tecnico.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(g / "tecnico.webm"), "-ss", f"{m + 10:.2f}",
                    "-frames:v", "1", str(destino)], check=True)
    return Image.open(destino).convert("RGB").crop((0, 206, 1060, 668))  # velas, Bollinger y volumen


def fondo(W, H):
    im = Image.new("RGB", (W, H), NEGRO)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 40):  # cuadrícula tenue de terminal
        d.line([(x, 0), (x, H)], fill=(16, 18, 22))
    for y in range(0, H, 40):
        d.line([(0, y), (W, y)], fill=(16, 18, 22))
    brillo = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(brillo).ellipse([W * 0.45, -H * 0.3, W * 1.3, H * 0.9], fill=(70, 14, 14))
    return Image.blend(im, brillo.filter(ImageFilter.GaussianBlur(160)), 0.45)


def ventana(img: Image.Image, ancho: int) -> Image.Image:
    """La captura dentro de una ventana con barra de dirección 127.0.0.1:8765 (la terminal es local)."""
    alto = int(img.height * ancho / img.width)
    barra = max(30, ancho // 28)
    v = Image.new("RGB", (ancho + 8, alto + barra + 8), ROJO)
    d = ImageDraw.Draw(v)
    d.rectangle([4, 4, ancho + 3, barra + 3], fill=SUP)
    for k, c in enumerate((ROJO, GRIS, GRIS)):
        cx = 4 + barra // 2 + k * (barra * 2 // 3)
        d.ellipse([cx - barra // 6, 4 + barra // 2 - barra // 6, cx + barra // 6, 4 + barra // 2 + barra // 6], fill=c)
    d.text((4 + barra * 2 + 30, 4 + barra // 2), "127.0.0.1:8765  ·  ACTINVER TERMINAL", font=fuente("consolab.ttf", int(barra * 0.5)),
           fill=BLANCO, anchor="lm")
    v.paste(img.resize((ancho, alto), Image.LANCZOS), (4, barra + 4))
    return v


def sombra(base: Image.Image, capa: Image.Image, xy, radio=30):
    s = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(s).rectangle([xy[0] + 12, xy[1] + 18, xy[0] + capa.width + 12, xy[1] + capa.height + 18], fill=(0, 0, 0, 200))
    base.paste(s.filter(ImageFilter.GaussianBlur(radio)), (0, 0), s.filter(ImageFilter.GaussianBlur(radio)))
    base.paste(capa, xy)


def texto_borde(d, xy, t, f, relleno, borde=NEGRO, grosor=4, anchor="la"):
    d.text(xy, t, font=f, fill=relleno, anchor=anchor, stroke_width=grosor, stroke_fill=borde)


def etiqueta(d, xy, t, f, fondo_c, texto_c=BLANCO, pad=(16, 8)):
    x, y = xy
    w = d.textlength(t, font=f)
    d.rectangle([x, y, x + w + pad[0] * 2, y + f.size + pad[1] * 2], fill=fondo_c)
    d.text((x + pad[0], y + pad[1] - 2), t, font=f, fill=texto_c)
    return x + w + pad[0] * 2


def flecha_bajista(d, pts, color=ROJO, ancho=14):
    d.line(pts, fill=color, width=ancho, joint="curve")
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    L = ancho * 3.2
    p1 = (x2 - L * math.cos(a - 0.5), y2 - L * math.sin(a - 0.5))
    p2 = (x2 - L * math.cos(a + 0.5), y2 - L * math.sin(a + 0.5))
    d.polygon([(x2 + ancho * 0.8 * math.cos(a), y2 + ancho * 0.8 * math.sin(a)), p1, p2], fill=color)


def youtube(cap, datos):
    W, H = 1280, 720
    im = fondo(W, H)
    v = ventana(cap, 700)
    sombra(im, v, (548, 150))
    d = ImageDraw.Draw(im)
    flecha_bajista(d, [(900, 330), (1010, 420), (1080, 400), (1215, 560)])
    # Texto principal a la izquierda
    etiqueta(d, (40, 36), "RETO ACTINVER 2026", fuente("bahnschrift.ttf", 30), ROJO)
    texto_borde(d, (40, 110), "CREAMOS", fuente("impact.ttf", 92), BLANCO)
    texto_borde(d, (40, 205), "NUESTRA", fuente("impact.ttf", 92), BLANCO)
    texto_borde(d, (40, 300), "TERMINAL", fuente("impact.ttf", 92), BLANCO)
    texto_borde(d, (40, 395), "CON IA", fuente("impact.ttf", 92), ROJO, borde=(40, 6, 6))
    # Resultado real
    d.rounded_rectangle([40, 505, 520, 676], radius=14, fill=SUP, outline=ROJO, width=4)
    d.text((62, 516), "$1,000,000 SIMULADOS", font=fuente("bahnschrift.ttf", 26), fill=GRIS)
    texto_borde(d, (60, 548), f"{datos['final']['rend'] * 100:.1f}%", fuente("impact.ttf", 74), ROJO, grosor=2)
    d.text((300, 586), "¿QUÉ\nAPRENDIMOS?", font=fuente("impact.ttf", 34), fill=BLANCO, spacing=2)
    # Marca del equipo
    etiqueta(d, (548, 664), "LYNX MARKET", fuente("bahnschrift.ttf", 26), SUP, ROJO)
    d.text((W - 30, 690), "MARKOWITZ · VaR · TELEGRAM", font=fuente("bahnschrift.ttf", 24), fill=GRIS, anchor="rm")
    return im


def tiktok(cap, datos):
    W, H = 1080, 1920
    im = fondo(W, H)
    d = ImageDraw.Draw(im)
    etiqueta(d, (60, 150), "RETO ACTINVER 2026", fuente("bahnschrift.ttf", 44), ROJO)
    texto_borde(d, (60, 250), "CREAMOS", fuente("impact.ttf", 150), BLANCO, grosor=6)
    texto_borde(d, (60, 405), "NUESTRA TERMINAL", fuente("impact.ttf", 104), BLANCO, grosor=5)
    texto_borde(d, (60, 520), "CON IA", fuente("impact.ttf", 150), ROJO, borde=(40, 6, 6), grosor=6)
    v = ventana(cap, 960)
    sombra(im, v, (56, 740))
    d = ImageDraw.Draw(im)
    flecha_bajista(d, [(640, 960), (790, 1080), (880, 1050), (985, 1185)], ancho=18)
    y = 740 + v.height + 50
    d.rounded_rectangle([60, y, 1020, y + 250], radius=20, fill=SUP, outline=ROJO, width=5)
    d.text((95, y + 22), "$1,000,000 SIMULADOS · 6 SEMANAS", font=fuente("bahnschrift.ttf", 38), fill=GRIS)
    texto_borde(d, (90, y + 70), f"{datos['final']['rend'] * 100:.1f}%", fuente("impact.ttf", 140), ROJO, grosor=3)
    d.text((610, y + 95), "¿QUÉ\nAPRENDIMOS?", font=fuente("impact.ttf", 62), fill=BLANCO, spacing=4)
    d.text((60, y + 300), "MARKOWITZ · VaR · TELEGRAM", font=fuente("bahnschrift.ttf", 44), fill=BLANCO)
    etiqueta(d, (60, y + 370), "LYNX MARKET", fuente("bahnschrift.ttf", 42), ROJO)
    return im


if __name__ == "__main__":
    SAL.mkdir(parents=True, exist_ok=True)
    datos = json.loads((MED / "informe" / "datos.json").read_text(encoding="utf-8"))
    cap = captura()
    youtube(cap, datos).save(SAL / "miniatura_youtube.png", optimize=True)
    tiktok(cap, datos).save(SAL / "portada_tiktok.png", optimize=True)
    for f in sorted(SAL.glob("*.png")):
        print(f, f.stat().st_size // 1024, "KB")
