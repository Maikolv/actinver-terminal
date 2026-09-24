"""Escenarios de estrés: cómo responde el sistema cuando cambian la volatilidad, los spreads o la calidad de los datos.

Principio: ante incertidumbre material (precio retrasado, emisora suspendida, falta de cotización SIC, noticias
contradictorias) se INHIBE la alerta direccional y se muestra una alerta de datos (ver alertas.inhibir_direccionales).
Las funciones de volatilidad y spread cuantifican el impacto; no generan recomendaciones.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def estres_volatilidad(retornos: pd.Series | np.ndarray, factor: float = 2.0, nivel: float = 0.95) -> dict:
    """VaR y CVaR históricos diarios con la volatilidad multiplicada por `factor` (misma media, desvíos escalados)."""
    r = np.asarray(pd.Series(retornos).dropna(), dtype=float)
    if len(r) < 30:
        return {"n": len(r), "nota": "historia insuficiente"}
    esc = r.mean() + (r - r.mean()) * factor
    q = np.quantile(esc, 1 - nivel)
    base_q = np.quantile(r, 1 - nivel)
    return {"n": len(r), "factor": factor, "var_base": float(-base_q), "var_estres": float(-q),
            "cvar_base": float(-r[r <= base_q].mean()), "cvar_estres": float(-esc[esc <= q].mean()),
            "vol_base": float(r.std()), "vol_estres": float(esc.std())}


def estres_spread(importe_operado: float, spread_relativo: float, costo_base: float = 0.00116) -> dict:
    """Costo total de operar un importe si al costo del simulador se suma medio spread por operación."""
    extra = importe_operado * spread_relativo / 2
    base = importe_operado * costo_base
    return {"importe": importe_operado, "costo_base": round(base, 2), "costo_spread": round(extra, 2),
            "costo_total": round(base + extra, 2), "multiplo_vs_base": round((base + extra) / base, 2) if base else None}
