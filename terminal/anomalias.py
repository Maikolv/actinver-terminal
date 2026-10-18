"""Hipótesis ABIERTA y propia de anomalías de volumen sobre barras CERRADAS. No clona ni equivale al indicador privado
del reel DeSsMwAOXWz, cuyas reglas no son públicas; cualquier comparación con él queda pendiente.

Reglas fijadas antes de mirar resultados (docs/anomalias-volumen.md):
- z_t = (ln V_t − media(ln V_{t−n..t−1})) / desv(ln V_{t−n..t−1}), con n barras ANTERIORES (la barra t no entra).
- Anomalía si z_t ≥ umbral (2.0 por omisión) y la barra t está cerrada. Sentido = signo del log-retorno ln(C_t/C_{t−1}).
- Evaluación descriptiva: log-retorno de t+1 a t+h (solo datos posteriores) tras anomalías frente a todas las barras.
No repinta: el valor en t depende solo de barras ≤ t, así que agregar barras nuevas no cambia marcas pasadas. Ni la
anomalía ni su sentido prometen continuación; dos desviaciones no implican probabilidad normal.
"""
from __future__ import annotations

import math

import numpy as np

VERSION = "anomalias-volumen 1.0"


def detectar(barras: list[dict], ventana: int = 20, umbral: float = 2.0) -> list[dict]:
    if not 5 <= ventana <= 500 or not 0.5 <= umbral <= 10:
        raise ValueError("ventana 5–500 y umbral 0.5–10")
    out = []
    lv = [math.log(b["volumen"]) if b.get("volumen") and b["volumen"] > 0 else None for b in barras]
    for t, b in enumerate(barras):
        previos = [x for x in lv[max(0, t - ventana):t] if x is not None]
        z = None
        if lv[t] is not None and len(previos) == ventana and t >= ventana:
            d = float(np.std(previos, ddof=1))
            z = (lv[t] - float(np.mean(previos))) / d if d > 0 else None
        ret = math.log(b["cierre"] / barras[t - 1]["cierre"]) if t and barras[t - 1]["cierre"] > 0 and b["cierre"] > 0 else None
        out.append({"inicio": b["inicio"], "z_volumen": z, "log_retorno": ret,
                    "anomalia": z is not None and z >= umbral and b.get("cerrada", True),
                    "sentido": None if ret is None else (1 if ret > 0 else -1 if ret < 0 else 0)})
    return out


def evaluar(barras: list[dict], ventana: int = 20, umbral: float = 2.0, h: int = 1) -> dict:
    if not 1 <= h <= 20:
        raise ValueError("horizonte h entre 1 y 20 barras")
    marcas = detectar(barras, ventana, umbral)
    c = [b["cierre"] for b in barras]
    fut = [math.log(c[t + h] / c[t]) if t + h < len(c) and c[t] > 0 else None for t in range(len(c))]
    todos = [f for f in fut if f is not None]
    tras = [(m["sentido"], fut[t]) for t, m in enumerate(marcas) if m["anomalia"] and fut[t] is not None]
    mismo = [f * s for s, f in tras if s]               # retorno futuro en el sentido de la barra anómala
    return {"version": VERSION, "parametros": {"ventana": ventana, "umbral": umbral, "h": h},
            "barras": len(barras), "anomalias": sum(m["anomalia"] for m in marcas), "con_futuro": len(tras),
            "media_futura_todas": float(np.mean(todos)) if todos else None,
            "media_futura_en_sentido": float(np.mean(mismo)) if mismo else None,
            "marcas": marcas[-300:],
            "nota": "Descriptivo, sin costos ni prueba de significancia; con pocas anomalías no hay conclusión. "
                    "Algoritmo propio: no equivale al indicador privado del reel."}
