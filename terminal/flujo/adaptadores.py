"""Adaptadores de proveedores autorizados. Cada uno declara fuente, licencia, feed y retraso, tiene interruptor en
`[flujo]` de la configuración, límite de consultas y nunca registra credenciales.

- Alpaca (datos de mercado, plan gratuito): barras OHLCV SIP con ≥ 15 min de retraso; operaciones SIP históricas con
  ≥ 15 min de retraso (sin lado del agresor); mejor bid/ask de IEX (un solo nivel); cadenas de opciones con el feed
  «indicative» (diferido). Solo usa `data.alpaca.markets`: no existe código hacia la API de operaciones.
- Cripto (ccxt, MIT): libro y operaciones públicos del exchange configurado (Bitso por omisión, pares en MXN). Fuera
  del Reto: sirve para analizar flujo de órdenes con datos reales y autorizados.
"""
from __future__ import annotations

import math
import os
import re
from datetime import UTC, date, datetime, timedelta

import httpx

from .. import modelos_opciones
from .contratos import Barra, ContratoOpcion, Libro, Nivel, Operacion, Procedencia, instante

URL_DATOS = "https://data.alpaca.markets"
RETRASO_SIP_S = 16 * 60
LIC_ALPACA = "Alpaca Market Data, plan gratuito: uso personal, sin redistribución"
OCC = re.compile(r"^([A-Z.]{1,6})(\d{6})([CP])(\d{8})$")


class FuenteNoDisponible(Exception):
    """Falta credencial, el adaptador está apagado o el proveedor no respondió. El mensaje nunca contiene secretos."""


def _cfg(ajustes, clave: str) -> dict:
    return dict(((ajustes.get("flujo") or {}) if ajustes else {}).get(clave) or {})


class Alpaca:
    nombre = "alpaca"

    def __init__(self, ajustes=None, env: dict | None = None, cliente: httpx.Client | None = None):
        self.env = os.environ if env is None else env
        self.cfg = {"activo": True, **_cfg(ajustes, "alpaca")}
        self.cliente = cliente

    def _get(self, ruta: str, params: dict) -> dict:
        if not self.cfg.get("activo", True):
            raise FuenteNoDisponible("Alpaca desactivado en [flujo.alpaca]")
        kid, sec = self.env.get("ALPACA_API_KEY_ID"), self.env.get("ALPACA_API_SECRET_KEY")
        if not (kid and sec):
            raise FuenteNoDisponible("faltan ALPACA_API_KEY_ID y ALPACA_API_SECRET_KEY en .env")
        cli = self.cliente or httpx.Client(timeout=15)
        try:
            r = cli.get(URL_DATOS + ruta, params=params, headers={"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec})
        except httpx.HTTPError as e:
            raise FuenteNoDisponible(f"Alpaca: sin conexión ({type(e).__name__})") from None
        finally:
            if self.cliente is None:
                cli.close()
        if r.status_code in (401, 403):
            raise FuenteNoDisponible(f"Alpaca: credencial rechazada o sin permiso para este dato (HTTP {r.status_code})")
        if r.status_code == 429:
            raise FuenteNoDisponible("Alpaca: límite de consultas (HTTP 429)")
        if r.status_code != 200:
            raise FuenteNoDisponible(f"Alpaca: HTTP {r.status_code}")
        return r.json()

    def barras(self, simbolo_origen: str, simbolo: str, intervalo: str, dias: int) -> tuple[list[Barra], Procedencia]:
        fin = datetime.now(UTC) - timedelta(seconds=RETRASO_SIP_S)
        d = self._get("/v2/stocks/bars", {"symbols": simbolo_origen, "timeframe": intervalo, "feed": "sip",
                                         "start": (fin - timedelta(days=dias)).isoformat(), "end": fin.isoformat(),
                                         "limit": 10000, "adjustment": "split"})
        barras = [Barra(simbolo, intervalo, instante(b["t"]), float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"]),
                        float(b.get("v") or 0), float(b["vw"]) if b.get("vw") else None)
                  for b in (d.get("bars") or {}).get(simbolo_origen) or []]
        return barras, Procedencia("alpaca", LIC_ALPACA, "EE. UU. (consolidado SIP)", feed="sip", retraso_s=RETRASO_SIP_S,
                                   nota="Barras OHLCV del consolidado SIP pedidas con ≥ 15 min de retraso; ajustadas por "
                                        "splits. Precio de origen en USD, no el precio del SIC en MXN.")

    def operaciones(self, simbolo_origen: str, simbolo: str, minutos: int = 60) -> tuple[list[Operacion], Procedencia]:
        fin = datetime.now(UTC) - timedelta(seconds=RETRASO_SIP_S)
        d = self._get(f"/v2/stocks/{simbolo_origen}/trades", {"feed": "sip", "start": (fin - timedelta(minutes=minutos)).isoformat(),
                                                             "end": fin.isoformat(), "limit": 10000, "sort": "desc"})
        ops = [Operacion(simbolo, instante(t["t"][:26] + "Z" if len(t["t"]) > 27 else t["t"]), float(t["p"]), float(t["s"]),
                         None, f"{t.get('x', '')}{t.get('i', '')}") for t in d.get("trades") or []]
        return ops, Procedencia("alpaca", LIC_ALPACA, "EE. UU. (consolidado SIP)", feed="sip", retraso_s=RETRASO_SIP_S,
                                nota="Operaciones del consolidado SIP con ≥ 15 min de retraso. El proveedor no informa el "
                                     "lado del agresor: no hay delta de volumen.")

    def mejor_precio(self, simbolo_origen: str, simbolo: str) -> tuple[Libro, Procedencia]:
        d = self._get(f"/v2/stocks/{simbolo_origen}/quotes/latest", {"feed": "iex"})
        q = d.get("quote") or {}
        niveles = []
        if q.get("bp"):
            niveles.append(Nivel("bid", 1, float(q["bp"]), float(q.get("bs") or 0)))
        if q.get("ap"):
            niveles.append(Nivel("ask", 1, float(q["ap"]), float(q.get("as") or 0)))
        t = q.get("t") or datetime.now(UTC).isoformat()
        inst = instante(t[:26] + "Z" if len(t) > 27 else t)
        retraso = (datetime.now(UTC) - datetime.fromisoformat(inst)).total_seconds()
        return Libro(simbolo, inst, niveles), Procedencia(
            "alpaca", LIC_ALPACA, "EE. UU. (IEX)", feed="iex", retraso_s=retraso,
            nota="Solo el primer nivel de IEX (≈ 2–3 % del volumen de EE. UU.); no es la profundidad del mercado. "
                 "Retraso medido con la hora de la cotización.")

    def cadena(self, subyacente: str, spot: float | None, tasa: float | None, dias: int = 60,
               rango: float = 0.30, paginas: int = 3) -> tuple[list[ContratoOpcion], Procedencia]:
        hoy = datetime.now(UTC).date()
        params = {"feed": "indicative", "limit": 1000, "expiration_date_gte": hoy.isoformat(),
                  "expiration_date_lte": (hoy + timedelta(days=dias)).isoformat()}
        if spot:
            params.update(strike_price_gte=round(spot * (1 - rango), 2), strike_price_lte=round(spot * (1 + rango), 2))
        snaps: dict = {}
        for _ in range(paginas):
            d = self._get(f"/v1beta1/options/snapshots/{subyacente}", params)
            snaps.update(d.get("snapshots") or {})
            if not d.get("next_page_token"):
                break
            params["page_token"] = d["next_page_token"]
        out = []
        for sim, s in snaps.items():
            m = OCC.match(sim)
            if not m:
                continue
            venc = date(2000 + int(m[2][:2]), int(m[2][2:4]), int(m[2][4:]))
            strike, tipo = int(m[4]) / 1000, "call" if m[3] == "C" else "put"
            q, t, bar = s.get("latestQuote") or {}, s.get("latestTrade") or {}, s.get("dailyBar") or {}
            g = s.get("greeks") or {}
            ts = q.get("t") or t.get("t") or datetime.now(UTC).isoformat()
            c = ContratoOpcion(sim, subyacente, venc.isoformat(), strike, tipo, instante(ts[:26] + "Z" if len(ts) > 27 else ts),
                               q.get("bp") or None, q.get("ap") or None, t.get("p"), bar.get("v"), None,
                               s.get("impliedVolatility"), g.get("delta"), g.get("gamma"), g.get("theta"), g.get("vega"),
                               "proveedor" if s.get("impliedVolatility") else None)
            if c.iv is None and spot and c.bid and c.ask and (venc - hoy).days >= 1:
                _iv_calculada(c, spot, tasa, (venc - hoy).days)
            out.append(c)
        return out, Procedencia("alpaca", LIC_ALPACA + "; feed «indicative» de OPRA, diferido", "EE. UU. (OPRA indicativo)",
                                feed="indicative", retraso_s=15 * 60,
                                nota="Feed indicativo gratuito (diferido ~15 min según Alpaca). Sin interés abierto. Si "
                                     "el proveedor no trae IV, se calcula con Black-Scholes-Merton europeo sobre el punto "
                                     "medio (origen «calculado»); las opciones de EE. UU. son americanas.")


def _iv_calculada(c: ContratoOpcion, spot: float, tasa: float | None, dias: int) -> None:
    medio = (c.bid + c.ask) / 2
    try:
        r = modelos_opciones.calcular({"tipo": c.tipo, "spot": spot, "strike": c.strike, "dias": dias,
                                       "tasa_pct": (tasa if tasa is not None else 4.0), "dividendo_pct": 0,
                                       "prima_mercado": medio})
    except ValueError:
        return  # fuera de los límites de arbitraje: sin IV antes que una IV falsa
    c.iv, c.delta, c.gamma = r["volatilidad_pct"] / 100, r["delta"], r["gamma"]
    c.theta, c.vega, c.origen_iv = r["theta_por_dia"], r["vega_por_1pct"], "calculado"


class Cripto:
    """Libro y operaciones públicos vía ccxt. Apagado con [flujo.cripto] activo = false."""
    PARES = ["BTC/MXN", "ETH/MXN", "SOL/MXN", "XRP/MXN"]

    def __init__(self, ajustes=None, exchange=None):
        self.cfg = {"activo": True, "exchange": "bitso", "pares": self.PARES, "niveles": 50, **_cfg(ajustes, "cripto")}
        self._ex = exchange

    @property
    def ex(self):
        if not self.cfg.get("activo", True):
            raise FuenteNoDisponible("adaptador de cripto desactivado en [flujo.cripto]")
        if self._ex is None:
            try:
                import ccxt
            except ImportError:
                raise FuenteNoDisponible("falta el paquete ccxt (uv sync)") from None
            nombre = str(self.cfg["exchange"]).lower()
            if not hasattr(ccxt, nombre):
                raise FuenteNoDisponible(f"exchange desconocido para ccxt: {nombre}")
            self._ex = getattr(ccxt, nombre)({"enableRateLimit": True, "timeout": 15000})
        return self._ex

    def simbolo(self, par: str) -> str:
        return f"{str(self.cfg['exchange']).upper()}:{par}"

    def _proc(self, retraso, nota) -> Procedencia:
        ex = str(self.cfg["exchange"]).lower()
        return Procedencia(ex, f"API pública de {ex} (términos del exchange); datos vía ccxt (MIT)", f"cripto ({ex})",
                           feed="publico", retraso_s=retraso, nota=nota)

    def _par(self, par: str) -> str:
        if par not in self.cfg["pares"]:
            raise FuenteNoDisponible(f"par no configurado: {par}")
        return par

    def barras(self, par: str, intervalo: str, dias: int) -> tuple[list[Barra], Procedencia]:
        par = self._par(par)
        tf = {"1Min": "1m", "5Min": "5m", "15Min": "15m", "1Hour": "1h", "1Day": "1d"}[intervalo]
        desde = int((datetime.now(UTC) - timedelta(days=dias)).timestamp() * 1000)
        try:
            velas = self.ex.fetch_ohlcv(par, tf, since=desde, limit=1000)
        except FuenteNoDisponible:
            raise
        except Exception as e:  # noqa: BLE001
            raise FuenteNoDisponible(f"{self.cfg['exchange']}: {type(e).__name__}") from None
        barras = [Barra(self.simbolo(par), intervalo, instante(datetime.fromtimestamp(t / 1000, UTC)), float(o), float(h),
                        float(lo), float(c), float(v) if v is not None else None)
                  for t, o, h, lo, c, v in velas if None not in (t, o, h, lo, c)]
        return barras, self._proc(None, "Velas OHLCV públicas del exchange (la última puede estar en formación).")

    def libro(self, par: str) -> tuple[Libro, Procedencia]:
        par = self._par(par)
        try:
            ob = self.ex.fetch_order_book(par, limit=int(self.cfg["niveles"]))
        except FuenteNoDisponible:
            raise
        except Exception as e:  # noqa: BLE001 - errores de red o del exchange; nunca hay secretos en juego
            raise FuenteNoDisponible(f"{self.cfg['exchange']}: {type(e).__name__}") from None
        ahora = datetime.now(UTC)
        ts = datetime.fromtimestamp(ob["timestamp"] / 1000, UTC) if ob.get("timestamp") else None
        niveles = [Nivel("bid", i + 1, float(p), float(q)) for i, (p, q, *_) in enumerate(ob.get("bids") or [])]
        niveles += [Nivel("ask", i + 1, float(p), float(q)) for i, (p, q, *_) in enumerate(ob.get("asks") or [])]
        inst = instante(min(ts, ahora) if ts else ahora)
        retraso = (ahora - ts).total_seconds() if ts else None
        return Libro(self.simbolo(par), inst, niveles), self._proc(
            retraso, "Libro público del exchange; retraso medido con su marca de tiempo." if ts else
            "El exchange no informó la hora del libro: se usa la hora de captura y el retraso es desconocido.")

    def operaciones(self, par: str, limite: int = 200) -> tuple[list[Operacion], Procedencia]:
        par = self._par(par)
        try:
            trs = self.ex.fetch_trades(par, limit=limite)
        except FuenteNoDisponible:
            raise
        except Exception as e:  # noqa: BLE001
            raise FuenteNoDisponible(f"{self.cfg['exchange']}: {type(e).__name__}") from None
        ops = [Operacion(self.simbolo(par), instante(datetime.fromtimestamp(t["timestamp"] / 1000, UTC)), float(t["price"]),
                         float(t["amount"]), {"buy": "compra", "sell": "venta"}.get(t.get("side")), str(t.get("id") or ""))
               for t in trs if t.get("timestamp") and t.get("price") and t.get("amount")]
        ultimo = max((datetime.fromisoformat(o.instante) for o in ops), default=None)
        return ops, self._proc((datetime.now(UTC) - ultimo).total_seconds() if ultimo else None,
                               "Operaciones públicas del exchange con el lado del agresor que informa el exchange.")


def tasa_libre_riesgo(con) -> tuple[float | None, str]:
    """Última tasa a 2 años (FRED DGS2) del centro de investigación, en %. Sin dato: None (el cálculo usa 4 % y lo dice)."""
    f = con.execute("SELECT valor, periodo FROM investigacion_observaciones WHERE fuente='fred_macro' AND serie='DGS2' "
                    "ORDER BY periodo DESC LIMIT 1").fetchone()
    return (float(f[0]), f"FRED DGS2 al {f[1]}") if f and f[0] is not None and math.isfinite(f[0]) else (None, "4 % supuesto")
