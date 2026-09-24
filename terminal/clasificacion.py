"""Control de clasificación de instrumentos: qué series pueden valuar acciones, ETF y fondos del Reto.

- CFD (contrato por diferencias): derivado apalancado cuyo precio lo fija el proveedor del contrato; no equivale a poseer
  la acción (https://www.dukascopy.com/swiss/spanish/cfd/what-are-cfds/). Una serie CFD nunca alimenta la valuación.
- Criptoactivos (formato unificado de ccxt «BASE/QUOTE», p. ej. BTC/USDT; ccxt/ccxt): no son valores de la BMV ni del SIC.
- Una acción de EE. UU., su ADR y la serie del SIC en pesos son objetos distintos (ver cotizaciones.normalizar_simbolo).
"""
from __future__ import annotations

import re

PATRON_CFD = re.compile(r"(\bCFD\b|\.CFD$|_CFD$|CFD:|DUKASCOPY:|\bCASH\b|USD\.IDX|\.CMD/)", re.I)
# ccxt: símbolo unificado BASE/QUOTE y sufijos de derivados «:QUOTE» (perpetuos) — ccxt/python/ccxt/base/exchange.py
PATRON_CRIPTO = re.compile(r"^[A-Z0-9]{2,12}/[A-Z0-9]{2,12}(:[A-Z0-9]+)?(-\d{6})?$|^(BINANCE|COINBASE|KRAKEN|BYBIT|OKX|BITSO):", re.I)
CRIPTO_COMUNES = {"BTC", "ETH", "USDT", "USDC", "SOL", "XRP", "DOGE", "BNB"}


class InstrumentoNoElegible(ValueError):
    pass


def clasificar_serie(simbolo: str, fuente: str = "") -> str:
    s = (simbolo or "").strip()
    if PATRON_CFD.search(s) or "cfd" in (fuente or "").lower():
        return "cfd"
    base = s.split(":")[-1].upper()
    if PATRON_CRIPTO.search(s) or base in CRIPTO_COMUNES or base.endswith(("USDT", "BUSD")):
        return "cripto"
    return "valor"


def exigir_valor(simbolo: str, fuente: str = "") -> None:
    """Lanza si la serie es un CFD o un criptoactivo: no puede valuar un instrumento del Reto."""
    tipo = clasificar_serie(simbolo, fuente)
    if tipo == "cfd":
        raise InstrumentoNoElegible(f"{simbolo}: serie CFD (derivado); no equivale a poseer la acción y no valúa el Reto")
    if tipo == "cripto":
        raise InstrumentoNoElegible(f"{simbolo}: criptoactivo (formato ccxt); no es un valor de la BMV ni del SIC")
