"""Gráfica del informe: pesos del último registro del Reto frente a la propuesta de Markowitz guardada en Mis portafolios.

Entradas privadas: data/medios/informe/datos.json y data/medios/propuesta/resultado.json (markowitz.guardar).
    uv run --with matplotlib python scripts/propuesta_markowitz_grafica.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MED = Path(__file__).resolve().parents[1] / "data" / "medios"
ROJO, GRIS, TEXTO = "#b3261e", "#7d828c", "#15171c"
d = json.loads((MED / "informe" / "datos.json").read_text(encoding="utf-8"))
r = json.loads((MED / "propuesta" / "resultado.json").read_text(encoding="utf-8"))
antes = {p["instrumento"]: p["valor"] for p in d["final"]["posiciones"]}
tot = sum(antes.values())
filas = sorted(r["activos"], key=lambda a: a["peso"])
nombres = [a["id"].split(":")[1] for a in filas]
fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
y = range(len(filas))
ax.barh([i + .2 for i in y], [antes[a["id"]] / tot * 100 for a in filas], .4, color=GRIS, label="Último registro (12-nov, % de lo invertido)")
ax.barh([i - .2 for i in y], [a["peso"] * 100 for a in filas], .4, color=ROJO, label="Propuesta Markowitz (máximo Sharpe)")
ax.set_yticks(list(y), nombres, fontsize=8); ax.set_xlabel("Peso (%)", fontsize=8); ax.tick_params(labelsize=8)
ax.grid(axis="x", alpha=.25); ax.legend(frameon=False, fontsize=7, loc="lower right")
ax.set_title("Mismos 12 instrumentos, repartidos con la plantilla de Markowitz", fontsize=10, color=TEXTO)
fig.tight_layout(); fig.savefig(MED / "informe" / "propuesta_markowitz.png"); plt.close(fig)
