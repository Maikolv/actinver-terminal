"""Monte Carlo por combinación: remuestreo por bloques de días completos (conserva dependencia temporal y correlación
entre activos) con perturbaciones de costos, deslizamiento y diferencial del SIC. Mismo M para todas."""
from __future__ import annotations

import math

import numpy as np

from . import diseno as dz


def simular(bruto: np.ndarray, costo: np.ndarray, giro: np.ndarray, giro_sic: np.ndarray, H: int,
            semilla: int, m: int = dz.M_SIM, bloque: int = dz.BLOQUE) -> dict:
    """Arreglos ya restringidos a las fechas fuera de muestra antes del tramo intacto, en orden cronológico."""
    T = len(bruto)
    if T < bloque or H < 1:
        return {"m": 0, "motivo": f"serie de {T} sesiones: insuficiente para bloques de {bloque}"}
    rng = np.random.default_rng(semilla)
    nb = math.ceil(H / bloque)
    idx = (rng.integers(0, T - bloque + 1, size=(m, nb))[:, :, None] + np.arange(bloque)).reshape(m, nb * bloque)[:, :H]
    p = dz.PERTURBACIONES
    mult = rng.uniform(*p["multiplicador_comision"], size=(m, 1))
    slip = rng.uniform(*p["deslizamiento_pb"], size=(m, 1)) / 1e4
    sic = rng.uniform(*p["diferencial_sic_pb"], size=(m, 1)) / 1e4
    neto = bruto[idx] - costo[idx] * mult - giro[idx] * slip - giro_sic[idx] * sic
    v = np.cumprod(1 + neto, axis=1)
    pico = np.maximum.accumulate(np.concatenate([np.ones((m, 1)), v], axis=1), axis=1)[:, 1:]
    caida = (v / pico - 1).min(axis=1)
    ret = v[:, -1] - 1
    q5 = np.quantile(ret, 0.05)
    return {"m": m, "H": H, "bloque": bloque, "semilla": semilla, "sesiones_base": T,
            "ret_p5": float(q5), "ret_p50": float(np.median(ret)), "ret_p95": float(np.quantile(ret, 0.95)),
            "caida_p5": float(np.quantile(caida, 0.05)), "caida_p50": float(np.median(caida)),
            "caida_p95": float(np.quantile(caida, 0.95)), "prob_perdida": float((ret < 0).mean()),
            "cvar5": float(ret[ret <= q5].mean())}
