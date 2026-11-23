"""Subtítulos .srt de las versiones A y B y MONTAJE PROVISIONAL de la versión A (9:16 y 16:9) a partir de
docs/video/guiones-tiktok.md. La voz es sintética (Windows) y cada cuadro lleva el rótulo «MONTAJE PROVISIONAL»:
sirve para ensayar ritmo y encuadre; los videos finales necesitan las grabaciones del equipo.
Uso: uv run python scripts/video_guion_provisional.py   (requiere ffmpeg)"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = Path(__file__).resolve().parents[1]
GUION = RAIZ / "docs" / "video" / "guiones-tiktok.md"
CAP = RAIZ / "docs" / "capturas"
SAL = RAIZ / "docs" / "video"
# Cada función del guion se ilustra con una captura real de la demo (datos simulados).
CAPTURA = {"F1": "inicio.png", "F2": "mercado-despues-demo-1440.jpg", "F3": "mercado-despues-demo-1440.jpg",
           "F4": "inicio.png", "F5": "riesgo.png", "F6": "portafolios.png", "F7": "inicio.png", "F8": "estacion-movil.jpg"}


def filas(version: str) -> list[dict]:
    bloque = GUION.read_text(encoding="utf-8").split(f"## Versión {version}")[1].split("\n## ")[0]
    out = []
    for linea in bloque.splitlines():
        c = [x.strip() for x in linea.strip().strip("|").split("|")]
        m = re.match(r"(\d+)–(\d+)", c[0]) if len(c) >= 6 else None
        if not m:
            continue
        habla = re.findall(r"«(.+?)»", c[3])
        funcion = re.search(r"F\d", c[4])
        out.append({"ini": int(m[1]), "fin": int(m[2]), "quien": c[2], "texto": " ".join(habla),
                    "captura": CAPTURA.get(funcion[0]) if funcion else None, "rotulo": c[5].strip("«»— ")})
    return out


def srt(version: str) -> None:
    t = lambda s: f"00:00:{s:02d},000"  # noqa: E731
    texto = "\n".join(f"{i}\n{t(f['ini'])} --> {t(f['fin'])}\n{f['quien']}: {f['texto']}\n" for i, f in enumerate(filas(version), 1))
    (SAL / f"{version}-60s.srt").write_text(texto, encoding="utf-8")


def fuente(n):
    for f in ("segoeuib.ttf", "arialbd.ttf"):
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


def cuadro(fila, W, H, destino):
    im = Image.new("RGB", (W, H), (14, 16, 20)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 8], fill=(179, 38, 30))
    if fila["captura"]:
        cap = ImageOps.contain(Image.open(CAP / fila["captura"]).convert("RGB"), (W - 60, int(H * .58)))
        im.paste(cap, ((W - cap.width) // 2, int(H * .12)))
    else:
        d.text((W // 2, H // 3), fila["quien"], font=fuente(70), fill=(236, 238, 242), anchor="mm")
    y = int(H * .73)
    if fila["rotulo"]:
        d.text((40, y - 70), fila["rotulo"], font=fuente(44 if W > H else 52), fill=(242, 119, 122))
    for linea in envolver(d, f"{fila['quien']}: {fila['texto']}", fuente(34 if W > H else 40), W - 80)[:4]:
        d.text((40, y), linea, font=fuente(34 if W > H else 40), fill=(236, 238, 242)); y += 50
    d.text((40, 30), "MONTAJE PROVISIONAL — voz sintética · datos simulados", font=fuente(26), fill=(255, 204, 0))
    d.text((40, H - 50), "Proyecto escolar independiente · no afiliado a Grupo Actinver · no es asesoría", font=fuente(22), fill=(169, 176, 187))
    im.save(destino)


def voz(texto, wav):
    Path(f"{wav}.txt").write_text(texto, encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SelectVoice('Microsoft Sabina Desktop'); $s.SetOutputToWaveFile('{wav}'); "
          f"$s.Speak([IO.File]::ReadAllText('{wav}.txt')); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def montaje(version, W, H, nombre):
    destino = SAL / "provisional" / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        partes = []
        for i, f in enumerate(filas(version)):
            png, wav, mp4 = (str(Path(tmp) / f"{i}.{e}") for e in ("png", "wav", "mp4"))
            cuadro(f, W, H, png); voz(f["texto"] or f["rotulo"], wav)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav, "-af", "apad=pad_dur=0.4",
                            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-shortest", mp4], check=True)
            partes.append(mp4)
        lista = Path(tmp) / "lista.txt"
        lista.write_text("".join(f"file '{p}'\n" for p in partes), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(destino)], check=True)
    print(destino)


if __name__ == "__main__":
    for v in ("A", "B"):
        srt(v)
    montaje("A", 1080, 1920, "A-vertical-PROVISIONAL.mp4")
    montaje("A", 1920, 1080, "A-horizontal-PROVISIONAL.mp4")
