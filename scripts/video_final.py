"""Video final del concurso «Finanzas en la era de la IA» con las VOCES REALES del equipo.

Solo pantalla y voz en off: nadie aparece a cuadro. El texto de los subtítulos sale de docs/video/guiones-tiktok.md.
Las imágenes son capturas de la demo pública (datos simulados) y gráficas o pantallas del portal con datos reales
del Reto; cada cuadro dice cuál de las dos es.

Audios esperados en data/medios/video/voces/ (privado, fuera del repositorio), un archivo por bloque del guion.
Las dos versiones usan los nombres de archivo tal como los envió el equipo (ver VERSIONES).

    uv run python scripts/video_final.py            → entregables/video/*.mp4 (4 renders)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = Path(__file__).resolve().parents[1]
GUION = RAIZ / "docs" / "video" / "guiones-tiktok.md"
VOCES = RAIZ / "data" / "medios" / "video" / "voces"
CAPV = RAIZ / "data" / "medios" / "video" / "capturas"
INF = RAIZ / "data" / "medios" / "informe"
DOCS = RAIZ / "docs" / "capturas"
SAL = RAIZ / "entregables" / "video"

REAL, DEMO = "DATOS REALES DEL RETO", "DEMO · DATOS SIMULADOS"
# Título, imagen y procedencia de cada uno de los 13 bloques del guion.
BLOQUES = [
    ("Actinver Terminal", DOCS / "inicio.png", DEMO),
    ("La IA como herramienta", CAPV / "legal.png", DEMO),
    ("1 · Plan de inversión inicial", INF / "distribucion_inicial.png", REAL),
    ("Perfil agresivo y Markowitz", CAPV / "portafolios.png", DEMO),
    ("Precios con procedencia", CAPV / "mercado.png", DEMO),
    ("2 · Seguimiento del 6 al 31 de octubre", INF / "portal" / "p114_0.png", REAL),
    ("Análisis técnico · Micron (MU)", INF / "tecnico_mu.png", REAL),
    ("Análisis fundamental", CAPV / "investigacion.png", DEMO),
    ("3 · Riesgo: desviación estándar y VaR", CAPV / "riesgo.png", DEMO),
    ("Resultado final frente al NAFTRAC", INF / "evolucion.png", REAL),
    ("Rotación a consumo y salud", INF / "portal" / "p132_0.png", REAL),
    ("Lo que aprendimos", CAPV / "propuestas.png", DEMO),
    ("Pruébala gratis en GitHub", DOCS / "inicio.png", DEMO),
]
VERSIONES = {
    "4_integrantes": ["Miguel 1", "Audio pt1", "valeria min 018-030", "Calle Bosques de México", "Miguel 2", "Audio pt2",
                      "valeria min 104-116", "Calle Bosques de México 2", "Miguel 3", "Audio pt3", "Valeria min 154 y 206",
                      "Calle Bosques de México 3", "Miguel 4"],
    "Miguel_y_Daniela": ["Miguel v Daniela 1", "Audio pt1", "Miguel v Daniela 2", "Calle Bosques de México", "Miguel v Daniela 3",
                         "Audio pt2", "Miguel v Daniela 4", "Calle Bosques de México 2", "Miguel v Daniela 5", "Audio pt3",
                         "Miguel v Daniela 6", "Calle Bosques de México 3", "Miguel v Daniela 7"],
}
# Nombres del equipo: archivo privado fuera del repositorio (data/medios/equipo.json).
_EQ = RAIZ / "data" / "medios" / "equipo.json"
EQUIPO = json.loads(_EQ.read_text(encoding="utf-8"))["integrantes"] if _EQ.exists() else ["Miguel", "Daniela", "Valeria", "Camila"]
AVISO = "Proyecto escolar independiente · no afiliado a Grupo Actinver · no es asesoría de inversión"
FONDO, ROJO, BLANCO, GRIS = (14, 16, 20), (179, 38, 30), (236, 238, 242), (150, 157, 168)


def textos() -> list[str]:
    out = []
    for linea in GUION.read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in linea.strip().strip("|").split("|")]
        if len(c) == 4 and re.match(r"\d:\d\d–\d:\d\d", c[0]):
            out.append(re.sub(r"^«|»$", "", c[2]))
    assert len(out) == len(BLOQUES), f"el guion tiene {len(out)} bloques"
    return out


def fuente(n, negrita=True):
    for f in (("segoeuib.ttf", "arialbd.ttf") if negrita else ("segoeui.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
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
    """Divide el texto hablado en frases de subtítulo de hasta `maximo` caracteres."""
    frases = re.split(r"(?<=[.:;,])\s+", texto)
    out, actual = [], ""
    for f in frases:
        if actual and len(actual) + len(f) + 1 > maximo:
            out.append(actual); actual = f
        else:
            actual = f"{actual} {f}".strip()
    return out + [actual] if actual else out


def cuadro(titulo, imagen, origen, sub, W, H, destino):
    v = H > W
    im = Image.new("RGB", (W, H), FONDO); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 8], fill=ROJO)
    d.text((40, 34), "Actinver Terminal · Finanzas en la era de la IA", font=fuente(26 if not v else 30), fill=GRIS)
    color = (52, 168, 83) if origen == REAL else (230, 170, 40)
    f_et = fuente(22 if not v else 28)
    ancho_et = d.textlength(origen, font=f_et) + 28
    x0 = W - 40 - ancho_et if not v else 40
    y0 = 30 if not v else 84
    d.rounded_rectangle([x0, y0, x0 + ancho_et, y0 + (38 if not v else 46)], 8, outline=color, width=3)
    d.text((x0 + 14, y0 + (7 if not v else 8)), origen, font=f_et, fill=color)
    y_t = 84 if not v else 160
    f_tit = fuente(48 if not v else 62)
    for linea in envolver(d, titulo, f_tit, W - 80):
        d.text((40, y_t), linea, font=f_tit, fill=(242, 119, 122)); y_t += int(f_tit.size * 1.25)
    if not v:
        caja, top = (W - 80, int(H * 0.60)), y_t + 16
    else:  # vertical: la imagen ocupa el ancho y se centra en la franja superior; subtítulos fijos debajo
        caja = (W - 40, int(H * 0.60) - y_t - 30)
    cap = ImageOps.contain(Image.open(imagen).convert("RGB"), caja, Image.LANCZOS)
    if v:
        top = y_t + 20 + (caja[1] - cap.height) // 2
    x = (W - cap.width) // 2
    d.rectangle([x - 3, top - 3, x + cap.width + 2, top + cap.height + 2], outline=(60, 64, 72), width=3)
    im.paste(cap, (x, top))
    f_sub = fuente(38 if not v else 54)
    y = top + cap.height + 34 if not v else int(H * 0.64)
    for linea in envolver(d, sub, f_sub, W - 120):
        w = d.textlength(linea, font=f_sub)
        d.text(((W - w) / 2, y), linea, font=f_sub, fill=BLANCO, stroke_width=2, stroke_fill=(0, 0, 0)); y += int(f_sub.size * 1.3)
    f_av = fuente(22 if not v else 26, negrita=False)
    for i, linea in enumerate(envolver(d, AVISO, f_av, W - 80)):
        d.text((40, H - (48 if not v else 90) + i * 32), linea, font=f_av, fill=GRIS)
    im.save(destino)


def tarjeta(lineas, W, H, destino):
    im = Image.new("RGB", (W, H), FONDO); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 8], fill=ROJO)
    y = H * 0.30
    for texto, tam, color in lineas:
        f = fuente(tam if W > H else int(tam * 1.15), negrita=tam >= 40)
        for l in envolver(d, texto, f, W - 140):
            w = d.textlength(l, font=f)
            d.text(((W - w) / 2, y), l, font=f, fill=color); y += f.size * 1.35
        y += 18
    im.save(destino)


def duracion(f) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True).stdout)


def audio(origen, destino, pausa=0.45):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(origen), "-af",
                    f"highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur={pausa}", "-ar", "48000", "-ac", "2", str(destino)], check=True)


def silencio(seg, destino):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(seg), str(destino)], check=True)


def voces() -> dict[str, Path]:
    """Nombre normalizado (NFC, sin «.m4a.mp4») → archivo; los nombres del teléfono vienen en NFD."""
    return {unicodedata.normalize("NFC", f.name).removesuffix(".m4a.mp4"): f for f in VOCES.glob("*.mp4")}


def render(version: str, W: int, H: int):
    archivos = VERSIONES[version]
    disponibles = voces()
    falta = [a for a in archivos if a not in disponibles]
    if falta:
        sys.exit(f"Faltan audios en {VOCES}: {falta}")
    SAL.mkdir(parents=True, exist_ok=True)
    destino = SAL / f"Video_Actinver_Terminal_{version}_{'vertical' if H > W else 'horizontal'}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        imgs, wavs = [], []
        tarjeta([("Actinver Terminal", 76, BLANCO), ("Reto Actinver 2026 · Finanzas en la era de la IA", 40, (242, 119, 122)),
                 ("Universidad del Valle de México · Campus Hispano", 30, GRIS)], W, H, t / "intro.png")
        silencio(3.0, t / "intro.wav"); imgs.append((t / "intro.png", 3.0)); wavs.append(t / "intro.wav")
        for i, ((titulo, imagen, origen), texto, arch) in enumerate(zip(BLOQUES, textos(), archivos)):
            wav = t / f"{i:02d}.wav"; audio(disponibles[arch], wav); wavs.append(wav)
            dur = duracion(wav)
            partes = trozos(texto, 120 if W > H else 95)
            total = sum(len(p) for p in partes)
            for j, parte in enumerate(partes):
                png = t / f"{i:02d}_{j}.png"
                cuadro(titulo, imagen, origen, parte, W, H, png)
                imgs.append((png, dur * len(parte) / total))
        tarjeta([("Equipo", 44, (242, 119, 122)), *[(n, 34, BLANCO) for n in EQUIPO],
                 ("Licenciatura en Contaduría y Finanzas Públicas · UVM Campus Hispano", 26, GRIS),
                 ("github.com/Maikolv/help-quote-terminal", 30, (242, 119, 122)),
                 ("Las pantallas de la terminal son de la demo con datos simulados; las cifras del Reto son reales. " + AVISO, 22, GRIS)],
                W, H, t / "fin.png")
        silencio(5.0, t / "fin.wav"); imgs.append((t / "fin.png", 5.0)); wavs.append(t / "fin.wav")
        lista_v = t / "v.txt"
        lista_v.write_text("".join(f"file '{p.as_posix()}'\nduration {d:.3f}\n" for p, d in imgs) + f"file '{imgs[-1][0].as_posix()}'\n", encoding="utf-8")
        lista_a = t / "a.txt"
        lista_a.write_text("".join(f"file '{w.as_posix()}'\n" for w in wavs), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(t / "a.txt"), str(t / "voz.wav")], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista_v), "-i", str(t / "voz.wav"),
                        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-tune", "stillimage",
                        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(destino)], check=True)
    print(destino, f"{duracion(destino):.1f} s")


if __name__ == "__main__":
    formatos = sys.argv[1:] or ["horizontal", "vertical"]  # p. ej. `vertical` para regenerar solo 9:16
    for version in VERSIONES:
        if "horizontal" in formatos:
            render(version, 1920, 1080)
        if "vertical" in formatos:
            render(version, 1080, 1920)
