"""Contratos normalizados y su procedencia. Cada observación lleva fuente, licencia, mercado, instante con zona horaria,
hora de captura, retraso y calidad (proveedor | importado | calculado | sintetico)."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

CALIDADES = ("proveedor", "importado", "calculado", "sintetico")
INTERVALOS = {"1Min": 60, "5Min": 300, "15Min": 900, "1Hour": 3600, "1Day": 86400}
LADOS_LIBRO = ("bid", "ask")
LADOS_OPERACION = ("compra", "venta")
TIPOS_OPCION = ("call", "put")
SIMBOLO = re.compile(r"[A-Z0-9][A-Z0-9.:/&_-]{0,39}")


def instante(valor, ahora: datetime | None = None) -> str:
    """ISO 8601 con zona horaria, convertido a UTC; rechaza fechas sin zona o futuras (> 5 min de tolerancia)."""
    try:
        t = valor if isinstance(valor, datetime) else datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"instante inválido: {str(valor)[:40]!r} (use ISO 8601 con zona horaria)") from None
    if t.tzinfo is None:
        raise ValueError("instante sin zona horaria: agregue el desfase (p. ej. -06:00 o Z)")
    t = t.astimezone(UTC)
    if (t - (ahora or datetime.now(UTC))).total_seconds() > 300:
        raise ValueError("instante en el futuro")
    return t.isoformat()


def positivo(valor, nombre: str, cero: bool = False) -> float:
    try:
        x = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre}: número inválido") from None
    if not math.isfinite(x) or x < 0 or (x == 0 and not cero):
        raise ValueError(f"{nombre}: debe ser {'mayor o igual a' if cero else 'mayor que'} cero")
    return x


def opcional(valor, nombre: str, cero: bool = True) -> float | None:
    return None if valor in (None, "") else positivo(valor, nombre, cero)


def simbolo(valor) -> str:
    s = str(valor or "").strip().upper()
    if not SIMBOLO.fullmatch(s):
        raise ValueError("símbolo inválido")
    return s


@dataclass
class Procedencia:
    fuente: str
    licencia: str
    mercado: str
    calidad: str = "proveedor"
    feed: str = ""
    retraso_s: float | None = None        # retraso MEDIDO o declarado por el proveedor (se dice cuál en `nota`)
    nota: str = ""
    capturado_en: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self):
        if self.calidad not in CALIDADES:
            raise ValueError("calidad desconocida")


@dataclass
class Barra:
    simbolo: str
    intervalo: str
    inicio: str
    apertura: float
    maximo: float
    minimo: float
    cierre: float
    volumen: float | None
    vwap: float | None = None

    def validar(self):
        if self.intervalo not in INTERVALOS:
            raise ValueError("intervalo inválido")
        if not (self.minimo <= min(self.apertura, self.cierre) and self.maximo >= max(self.apertura, self.cierre)):
            raise ValueError("OHLC inconsistente: el mínimo y el máximo deben contener apertura y cierre")


@dataclass
class Nivel:
    lado: str
    nivel: int
    precio: float
    tamano: float


@dataclass
class Libro:
    simbolo: str
    instante: str
    niveles: list[Nivel]

    def validar(self):
        bids = sorted((n.precio for n in self.niveles if n.lado == "bid"), reverse=True)
        asks = sorted(n.precio for n in self.niveles if n.lado == "ask")
        if bids and asks and bids[0] > asks[0]:
            raise ValueError("libro cruzado: el mejor bid supera al mejor ask")


@dataclass
class Operacion:
    simbolo: str
    instante: str
    precio: float
    tamano: float
    lado: str | None = None               # lado del agresor si el proveedor lo informa; nunca se infiere
    id_origen: str = ""


@dataclass
class ContratoOpcion:
    contrato: str
    subyacente: str
    vencimiento: str                      # AAAA-MM-DD
    strike: float
    tipo: str
    instante: str
    bid: float | None = None
    ask: float | None = None
    ultimo: float | None = None
    volumen: float | None = None
    interes_abierto: float | None = None
    iv: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    origen_iv: str | None = None          # proveedor | calculado | importado
    multiplicador: float | None = None    # títulos por contrato; solo si la fuente lo informa (nunca se supone 100)
    spot: float | None = None             # precio del subyacente de la MISMA referencia/instante que la cotización
    moneda: str | None = None             # moneda del spot y del contrato


class MarketDataProvider(Protocol):
    def barras(self, simbolo: str, intervalo: str, dias: int) -> tuple[list[Barra], Procedencia]: ...


class OrderBookProvider(Protocol):
    def libro(self, simbolo: str) -> tuple[Libro, Procedencia]: ...


class TradesProvider(Protocol):
    def operaciones(self, simbolo: str) -> tuple[list[Operacion], Procedencia]: ...


class OptionsChainProvider(Protocol):
    def cadena(self, subyacente: str) -> tuple[list[ContratoOpcion], Procedencia]: ...


@dataclass
class OperacionOpcion:
    contrato: str
    subyacente: str
    instante: str
    mercado_origen: str
    precio: float
    tamano: float
    condiciones: list[str]
    t_origen: str
    vencimiento: str
    strike: float
    tipo: str
