"""Estimaciones Black-Scholes-Merton para opciones europeas, sin datos externos."""

from __future__ import annotations

import math


def _numero(cuerpo: dict, clave: str, minimo: float, maximo: float, *, opcional: bool = False) -> float | None:
    valor = cuerpo.get(clave)
    if opcional and (valor is None or valor == ""):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{clave}: ingrese un número") from exc
    if not math.isfinite(numero) or not minimo <= numero <= maximo:
        raise ValueError(f"{clave}: debe estar entre {minimo:g} y {maximo:g}")
    return numero


def _normal(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _precio(tipo: str, spot: float, strike: float, tiempo: float, tasa: float, dividendo: float, sigma: float) -> float:
    raiz = math.sqrt(tiempo)
    d1 = (math.log(spot / strike) + (tasa - dividendo + 0.5 * sigma * sigma) * tiempo) / (sigma * raiz)
    d2 = d1 - sigma * raiz
    spot_presente = spot * math.exp(-dividendo * tiempo)
    strike_presente = strike * math.exp(-tasa * tiempo)
    if tipo == "call":
        return spot_presente * _normal(d1) - strike_presente * _normal(d2)
    return strike_presente * _normal(-d2) - spot_presente * _normal(-d1)


def _volatilidad_implicita(tipo: str, spot: float, strike: float, tiempo: float,
                           tasa: float, dividendo: float, prima: float) -> float:
    spot_presente = spot * math.exp(-dividendo * tiempo)
    strike_presente = strike * math.exp(-tasa * tiempo)
    minimo = max(0.0, spot_presente - strike_presente) if tipo == "call" else max(0.0, strike_presente - spot_presente)
    maximo = spot_presente if tipo == "call" else strike_presente
    if not minimo < prima < maximo:
        raise ValueError("prima_mercado: debe estar entre los límites de arbitraje para esta opción europea")
    inferior, superior = 0.0001, 5.0
    if not _precio(tipo, spot, strike, tiempo, tasa, dividendo, inferior) < prima < _precio(
        tipo, spot, strike, tiempo, tasa, dividendo, superior
    ):
        raise ValueError("prima_mercado: no permite estimar volatilidad entre 0.01 % y 500 %")
    for _ in range(80):
        medio = (inferior + superior) / 2
        if _precio(tipo, spot, strike, tiempo, tasa, dividendo, medio) < prima:
            inferior = medio
        else:
            superior = medio
    return (inferior + superior) / 2


def calcular(cuerpo: dict) -> dict:
    """Devuelve precio y griegas por opción; tasas y volatilidad entran en porcentaje anual."""
    tipo = str(cuerpo.get("tipo", "")).lower()
    if tipo not in {"call", "put"}:
        raise ValueError("tipo: use call o put")
    spot = _numero(cuerpo, "spot", 0.0001, 1e9)
    strike = _numero(cuerpo, "strike", 0.0001, 1e9)
    dias = _numero(cuerpo, "dias", 1, 3650)
    tasa_pct = _numero(cuerpo, "tasa_pct", -20, 100)
    dividendo_pct = _numero(cuerpo, "dividendo_pct", 0, 100)
    prima = _numero(cuerpo, "prima_mercado", 0, 1e9, opcional=True)
    tasa, dividendo, tiempo = tasa_pct / 100, dividendo_pct / 100, dias / 365
    if prima is None:
        sigma = _numero(cuerpo, "volatilidad_pct", 0.01, 500) / 100
    else:
        sigma = _volatilidad_implicita(tipo, spot, strike, tiempo, tasa, dividendo, prima)
    raiz = math.sqrt(tiempo)
    d1 = (math.log(spot / strike) + (tasa - dividendo + 0.5 * sigma * sigma) * tiempo) / (sigma * raiz)
    d2 = d1 - sigma * raiz
    densidad = math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
    descuento_q = math.exp(-dividendo * tiempo)
    descuento_r = math.exp(-tasa * tiempo)
    comun_theta = -(spot * descuento_q * densidad * sigma) / (2 * raiz)
    if tipo == "call":
        delta = descuento_q * _normal(d1)
        theta = comun_theta - tasa * strike * descuento_r * _normal(d2) + dividendo * spot * descuento_q * _normal(d1)
        rho = strike * tiempo * descuento_r * _normal(d2)
        intrinseco = max(spot - strike, 0.0)
    else:
        delta = descuento_q * (_normal(d1) - 1)
        theta = comun_theta + tasa * strike * descuento_r * _normal(-d2) - dividendo * spot * descuento_q * _normal(-d1)
        rho = -strike * tiempo * descuento_r * _normal(-d2)
        intrinseco = max(strike - spot, 0.0)
    precio = _precio(tipo, spot, strike, tiempo, tasa, dividendo, sigma)
    return {
        "modelo": "Black-Scholes-Merton europeo", "tipo": tipo, "precio_teorico": precio,
        "volatilidad_pct": sigma * 100, "volatilidad_implicita": prima is not None,
        "delta": delta, "gamma": descuento_q * densidad / (spot * sigma * raiz),
        "vega_por_1pct": spot * descuento_q * densidad * raiz / 100,
        "theta_por_dia": theta / 365, "rho_por_1pct": rho / 100,
        "intrinseco_actual": intrinseco,
        "nota": "Estimación para una opción europea. No usa cotizaciones ni flujo de órdenes y no ejecuta operaciones.",
    }
