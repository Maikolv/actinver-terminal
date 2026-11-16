"""Video explicativo de la terminal: diapositivas con capturas (datos simulados) y narración con la voz de Windows.
Uso: uv run python scripts/video_terminal.py  → docs/video/help-quote-terminal.mp4 (requiere ffmpeg en PATH)."""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = Path(__file__).resolve().parents[1]
CAP = RAIZ / "docs" / "capturas"
SALIDA = RAIZ / "docs" / "video" / "help-quote-terminal.mp4"
W, H = 1920, 1080
ESCENAS = [
    (None, "Help Quote Terminal", "Terminal local de análisis de portafolios. Compara su cartera real contra portafolios optimizados, mide el riesgo y le dice qué vender, comprar o mantener. Solo informa y simula: nunca ejecuta órdenes."),
    ("inicio.png", "Plan de acción", "El plan de acción ordena por prioridad qué hacer hoy: primero las ventas, luego las compras, con cantidad, precio límite, motivo y la condición que invalidaría cada sugerencia. El mismo plan llega por Telegram."),
    ("mercado-despues-demo-1440.jpg", "Estación de Mercado", "La estación de mercado reúne un monitor de instrumentos, un gráfico con su proyección de diez a noventa por ciento y un inspector. Cada dato muestra su fuente, fecha y vigencia; un dato vencido nunca se presenta como actual."),
    ("portafolios.png", "Mis portafolios", "En Mis portafolios usted construye portafolios con Markowitz, máximo Sharpe o Black-Litterman, y elige uno como portafolio principal. A partir de ahí, el plan lleva su cartera a esos pesos."),
    ("propuestas.png", "Propuestas", "El motor también calcula propuestas automáticas y las compara fuera de muestra contra la referencia más simple: el mismo peso en todo. Si un modelo no la supera, la terminal lo dice."),
    ("riesgo.png", "Riesgo", "La sección de riesgo mide el valor en riesgo, la pérdida esperada en los peores días y cuánto aporta cada posición. Las ventas por stop y tendencia mandan sobre el objetivo."),
    ("ranking.png", "Ranking", "El ranking clasifica los instrumentos por puntuación y capitalización bursátil, con datos de la SEC y de la Bolsa Mexicana."),
    ("mercado-despues-demo-claro-1440.jpg", "Seguridad y uso", "La terminal corre en su computadora, sus claves se quedan en su equipo y puede probarse en el navegador o en GitHub Codespaces. No es asesoría de inversión: usted decide y opera."),
]


def fuente(t):
    for f in ("segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(f, t)
        except OSError:
            pass
    return ImageFont.load_default()


def lamina(img, titulo, destino):
    fondo = Image.new("RGB", (W, H), (14, 16, 20))
    d = ImageDraw.Draw(fondo)
    d.rectangle([0, 0, W, 8], fill=(179, 38, 30))
    d.text((80, 50), titulo, font=fuente(64), fill=(236, 238, 242))
    if img:
        cap = Image.open(CAP / img).convert("RGB")
        cap = ImageOps.contain(cap, (W - 160, H - 220))  # también agranda capturas chicas
        fondo.paste(cap, ((W - cap.width) // 2, 170))
    else:
        d.text((80, 480), "Datos simulados · solo informa y simula", font=fuente(48), fill=(169, 176, 187))
    d.text((80, H - 60), "Help Quote Terminal · capturas con datos simulados", font=fuente(28), fill=(169, 176, 187))
    fondo.save(destino)


def voz(texto, destino):
    ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$s.SelectVoice('Microsoft Sabina Desktop'); $s.Rate=0; "
          f"$s.SetOutputToWaveFile('{destino}'); $s.Speak([IO.File]::ReadAllText('{destino}.txt')); $s.Dispose()")
    Path(f"{destino}.txt").write_text(texto, encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def main():
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        partes = []
        for i, (img, titulo, texto) in enumerate(ESCENAS):
            png, wav, mp4 = (str(Path(tmp) / f"{i}.{e}") for e in ("png", "wav", "mp4"))
            lamina(img, titulo, png)
            voz(texto, wav)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav, "-af", "apad=pad_dur=0.8",
                            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", mp4], check=True)
            partes.append(mp4)
        lista = Path(tmp) / "lista.txt"
        lista.write_text("".join(f"file '{p}'\n" for p in partes), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(SALIDA)], check=True)
    print(SALIDA)


if __name__ == "__main__":
    main()
