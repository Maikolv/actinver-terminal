"""Gráfica del informe: pesos del último registro del Reto frente al portafolio idóneo guardado en Mis portafolios.

Entradas privadas: data/medios/informe/datos.json y data/medios/propuesta/idoneo.json (markowitz.generar + guardar).
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
r = json.loads((MED / "propuesta" / "idoneo.json").read_text(encoding="utf-8"))  # portafolio idóneo (id 7)
antes = {p["instrumento"]: p["valor"] for p in d["final"]["posiciones"]}
tot = sum(antes.values())
filas = sorted([a for a in r["activos"] if a["peso"] > 0.0005 or a["id"] in antes], key=lambda a: a["peso"])
nombres = [a["id"].split(":")[1] for a in filas]
fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=150)
y = range(len(filas))
ax.barh([i + .2 for i in y], [antes.get(a["id"], 0) / tot * 100 for a in filas], .4, color=GRIS, label="Último registro (12-nov, % de lo invertido)")
ax.barh([i - .2 for i in y], [a["peso"] * 100 for a in filas], .4, color=ROJO, label="Portafolio idóneo (Solver de Markowitz, tope 10 %)")
ax.set_yticks(list(y), nombres, fontsize=8); ax.set_xlabel("Peso (%)", fontsize=8); ax.tick_params(labelsize=8)
ax.grid(axis="x", alpha=.25); ax.legend(frameon=False, fontsize=7, loc="lower right")
ax.set_title("Último registro del Reto frente al portafolio idóneo de Markowitz", fontsize=10, color=TEXTO)
fig.tight_layout(); fig.savefig(MED / "informe" / "propuesta_markowitz.png"); plt.close(fig)
