"""Modelo de Heston (1993): precio de opciones europeas y calibración a una cadena guardada. Código propio.

Referencias publicadas (no se copió código de ningún repositorio):
- S. Heston, «A Closed-Form Solution for Options with Stochastic Volatility», Review of Financial Studies 6 (1993).
- H. Albrecher et al., «The Little Heston Trap», Wilmott (2007): forma de la función característica estable.
- Y. Cui, S. del Baño Rollin, G. Germano, «Full and fast calibration of the Heston stochastic volatility model»,
  EJOR 263 (2017): calibración por mínimos cuadrados (aquí con diferencias numéricas, no con su gradiente analítico).
  El repositorio local `Heston-Calibration` no tiene licencia: solo se usó como referencia de lectura.

Es un MODELO descriptivo de la superficie de volatilidad: europeo (las opciones de EE. UU. son americanas), sin
dividendos discretos y con tasa constante. No es una predicción ni una señal.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np

from .. import modelos_opciones

NODOS, LIMITE = np.polynomial.legendre.leggauss(256), 250.0
LIMITES = {"v0": (1e-4, 4.0), "kappa": (0.01, 20.0), "theta": (1e-4, 4.0), "sigma": (0.01, 5.0), "rho": (-0.99, 0.99)}
ORDEN = ("v0", "kappa", "theta", "sigma", "rho")


def _cf(u, T, spot, r, q, v0, kappa, theta, sigma, rho):
    """Función característica de ln S_T (forma de Albrecher). u: arreglo complejo; T escalar o arreglo compatible."""
    iu = 1j * u
    b = kappa - rho * sigma * iu
    d = np.sqrt(b * b + sigma * sigma * (iu + u * u))
    g = (b - d) / (b + d)
    e = np.exp(-d * T)
    C = (r - q) * iu * T + kappa * theta / sigma ** 2 * ((b - d) * T - 2 * np.log((1 - g * e) / (1 - g)))
    D = (b - d) / sigma ** 2 * (1 - e) / (1 - g * e)
    return np.exp(C + D * v0 + iu * math.log(spot))


def precio_call(spot, strikes, T, r, q, p: dict) -> np.ndarray:
    """Precio de calls europeas (P1/P2 de Heston, integración de Gauss-Legendre en [0, 250]). strikes y T: arreglos."""
    K = np.atleast_1d(np.asarray(strikes, float))[:, None]
    T = np.atleast_1d(np.asarray(T, float))[:, None]
    x, w = NODOS
    u = (x + 1) * LIMITE / 2 + 1e-8
    w = w * LIMITE / 2
    args = (spot, r, q, p["v0"], p["kappa"], p["theta"], p["sigma"], p["rho"])
    phi = _cf(u[None, :], T, *args)
    phi_i = _cf(u[None, :] - 1j, T, *args)
    fwd = spot * np.exp((r - q) * T)                       # φ(−i) = E[S_T]
    k = np.exp(-1j * u[None, :] * np.log(K))
    p2 = 0.5 + (w * np.real(k * phi / (1j * u[None, :]))).sum(axis=1)[:, None] / math.pi
    p1 = 0.5 + (w * np.real(k * phi_i / (1j * u[None, :] * fwd))).sum(axis=1)[:, None] / math.pi
    c = spot * np.exp(-q * T) * p1 - K * np.exp(-r * T) * p2
    return np.maximum(c[:, 0], 0.0)


def precio(tipo, spot, strikes, T, r, q, p: dict) -> np.ndarray:
    c = precio_call(spot, strikes, T, r, q, p)
    if tipo == "call":
        return c
    K, Tn = np.asarray(strikes, float), np.asarray(T, float)
    return np.maximum(c - spot * np.exp(-q * Tn) + K * np.exp(-r * Tn), 0.0)   # paridad put-call


def _vega_bs(spot, K, T, r, q, iv):
    d1 = (math.log(spot / K) + (r - q + 0.5 * iv * iv) * T) / (iv * math.sqrt(T))
    return spot * math.exp(-q * T) * math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi) * math.sqrt(T)


def seleccionar(cadena: list[dict], spot: float, hoy, max_contratos: int = 60) -> list[dict]:
    """Contratos fuera del dinero con bid y ask, IV y 7–180 días; |ln(K/S)| ≤ 0.3. Reparte entre vencimientos."""
    elegibles = []
    for c in cadena:
        dias = (datetime.fromisoformat(c["vencimiento"]).date() - hoy).days
        if not (c.get("bid") and c.get("ask") and c.get("iv") and 7 <= dias <= 180 and c["ask"] >= c["bid"]):
            continue
        lk = math.log(c["strike"] / spot)
        if abs(lk) > 0.3 or (c["tipo"] == "call" and lk < 0) or (c["tipo"] == "put" and lk >= 0):
            continue
        elegibles.append({**c, "T": dias / 365.0, "medio": (c["bid"] + c["ask"]) / 2})
    if len(elegibles) <= max_contratos:
        return elegibles
    paso = len(elegibles) / max_contratos
    return [sorted(elegibles, key=lambda c: (c["vencimiento"], c["strike"]))[int(i * paso)] for i in range(max_contratos)]


def calibrar(cadena: list[dict], spot: float, tasa: float, q: float = 0.0, hoy=None) -> dict:
    """Ajusta (v0, κ, θ, σ, ρ) minimizando errores de precio divididos entre la vega de Black-Scholes, lo que
    aproxima errores en puntos de volatilidad. Devuelve parámetros, error, condición de Feller y advertencias."""
    from scipy.optimize import least_squares
    hoy = hoy or datetime.now(UTC).date()
    sel = seleccionar(cadena, spot, hoy)
    if len(sel) < 8:
        raise ValueError(f"datos insuficientes: {len(sel)} contratos aptos (se necesitan ≥ 8 fuera del dinero, con bid/ask "
                         "e IV, de 7 a 180 días)")
    K = np.array([c["strike"] for c in sel])
    T = np.array([c["T"] for c in sel])
    tipos = [c["tipo"] for c in sel]
    obs = np.array([c["medio"] for c in sel])
    vegas = np.array([max(_vega_bs(spot, c["strike"], c["T"], tasa, q, c["iv"]), 1e-3) for c in sel])
    ivs = np.array([c["iv"] for c in sel])
    es_call = np.array([t == "call" for t in tipos])

    def modelo(x):
        p = dict(zip(ORDEN, x))
        c = precio_call(spot, K, T, tasa, q, p)
        put = c - spot * np.exp(-q * T) + K * np.exp(-tasa * T)
        return np.where(es_call, c, put)

    iv_media = float(np.median(ivs))
    x0 = [iv_media ** 2, 2.0, iv_media ** 2, 0.6, -0.5]
    lo, hi = zip(*(LIMITES[k] for k in ORDEN))
    r = least_squares(lambda x: (modelo(x) - obs) / vegas, x0, bounds=(lo, hi), max_nfev=400, x_scale="jac")
    p = dict(zip(ORDEN, map(float, r.x)))
    err_iv = (modelo(r.x) - obs) / vegas
    rmse = float(np.sqrt(np.mean(err_iv ** 2)))
    feller = 2 * p["kappa"] * p["theta"] - p["sigma"] ** 2
    avisos = []
    if feller <= 0:
        avisos.append("No cumple la condición de Feller (2κθ ≤ σ²): la varianza puede tocar cero.")
    if any(abs(p[k] - b) < 1e-3 * (hi_ - lo_) for k, (lo_, hi_) in LIMITES.items() for b in (lo_, hi_)):
        avisos.append("Algún parámetro quedó en su límite: el ajuste puede no estar identificado.")
    if rmse > 0.05:
        avisos.append(f"Error medio alto ({rmse:.1%} de volatilidad): el modelo describe mal esta superficie.")
    return {"parametros": p, "rmse_iv": rmse, "feller": feller, "contratos": len(sel), "convergio": bool(r.success),
            "iteraciones": int(r.nfev), "spot": spot, "tasa": tasa, "dividendo": q, "avisos": avisos,
            "ajuste": [{"contrato": c["contrato"], "vencimiento": c["vencimiento"], "strike": c["strike"], "tipo": c["tipo"],
                        "iv_mercado": c["iv"], "error_iv": float(e)} for c, e in zip(sel, err_iv)],
            "nota": "Heston europeo calibrado a precios medios bid/ask (error ponderado por vega ≈ error en puntos de "
                    "volatilidad). Describe la superficie observada; no predice precios ni es una señal."}


def comprobar_contra_bs(spot=100.0, K=100.0, T=0.5, r=0.04, iv=0.25) -> tuple[float, float]:
    """Heston con σ→0 y v0=θ=iv² debe reproducir Black-Scholes (lo usan las pruebas)."""
    h = float(precio_call(spot, [K], [T], r, 0.0, {"v0": iv * iv, "kappa": 5.0, "theta": iv * iv, "sigma": 1e-3, "rho": 0.0})[0])
    b = modelos_opciones.calcular({"tipo": "call", "spot": spot, "strike": K, "dias": T * 365, "tasa_pct": r * 100,
                                   "dividendo_pct": 0, "volatilidad_pct": iv * 100})["precio_teorico"]
    return h, b
