"""Adaptadores de proveedores autorizados. Cada uno declara fuente, licencia, feed y retraso, tiene interruptor en
`[flujo]` de la configuración, límite de consultas y nunca registra credenciales.

- Alpaca (datos de mercado, plan gratuito): barras OHLCV SIP con ≥ 15 min de retraso; operaciones SIP históricas con
  ≥ 15 min de retraso (sin lado del agresor); mejor bid/ask de IEX (un solo nivel); cadenas de opciones con el feed
  «indicative» (diferido). Contratos: GET autorizado solo en Paper; nunca órdenes, cuentas ni posiciones.
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
from .contratos import Barra, ContratoOpcion, Libro, Nivel, Operacion, OperacionOpcion, Procedencia, instante

URL_CONTRATOS_PAPER = "https://paper-api.alpaca.markets/v2/options/contracts"
URL_DATOS = "https://data.alpaca.markets"
RETRASO_SIP_S = 16 * 60
VENTANA_SPOT_S = 60  # máxima distancia entre la cotización de un contrato y el spot que se le une
LIC_ALPACA = "Alpaca Market Data, plan gratuito: uso personal, sin redistribución"
OCC = re.compile(r"^([A-Z.]{1,6})(\d{6})([CP])(\d{8})$")


def _nanosegundos(valor: str) -> int:
    """Compara marcas ISO sin perder la fracción original de hasta nueve dígitos."""
    t = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("instante sin zona horaria")
    fraccion = re.search(r"\.(\d+)", valor)
    digitos = fraccion[1] if fraccion else ""
    if len(digitos) > 9:
        raise ValueError("precisión temporal superior a nanosegundos")
    delta = t.replace(microsecond=0).astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + int(digitos.ljust(9, "0") or "0")


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

    def contratos_opciones(self, subyacente: str, limite: int = 1000, paginas: int = 3) -> tuple[list[dict], Procedencia]:
        """Metadatos: única excepción autorizada, Paper y GET sin redirecciones."""
        if not self.cfg.get("activo", True) or not self.cfg.get("contratos_oi", False):
            raise FuenteNoDisponible("consulta de contratos Paper desactivada en [flujo.alpaca] contratos_oi")
        if not re.fullmatch(r"[A-Z][A-Z.]{0,9}", subyacente) or not 1 <= limite <= 1000 or not 1 <= paginas <= 3:
            raise ValueError("subyacente o límites de contratos inválidos")
        kid, sec = self.env.get("ALPACA_PAPER_API_KEY_ID"), self.env.get("ALPACA_PAPER_API_SECRET_KEY")
        if not (kid and sec):
            raise FuenteNoDisponible("faltan credenciales específicas ALPACA_PAPER_API_KEY_ID/ALPACA_PAPER_API_SECRET_KEY para Paper")
        hoy = datetime.now(UTC).date()
        params = {"underlying_symbols": subyacente, "limit": limite, "status": "active",
                  "expiration_date_gte": hoy.isoformat(), "expiration_date_lte": (hoy + timedelta(days=183)).isoformat()}
        cli = self.cliente or httpx.Client(timeout=15)
        out, tokens, parcial = [], set(), False
        try:
            for _ in range(paginas):
                try:
                    r = cli.get(URL_CONTRATOS_PAPER, params=params,
                                headers={"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}, follow_redirects=False)
                except httpx.HTTPError:
                    raise FuenteNoDisponible("Alpaca Paper: sin conexión") from None
                if r.status_code != 200:
                    raise FuenteNoDisponible(f"Alpaca Paper: consulta no disponible (HTTP {r.status_code}); sin alternativa de pago")
                try:
                    d = r.json()
                    for c in d.get("option_contracts") or []:
                        contrato = c.get("symbol") or ""
                        if not OCC.fullmatch(contrato) or c.get("underlying_symbol") != subyacente:
                            continue
                        def numero(v, positivo=False):
                            if v in (None, ""):
                                return None
                            n = float(v)
                            if not math.isfinite(n) or n < 0 or (positivo and n <= 0):
                                raise ValueError()
                            return n
                        fecha = date.fromisoformat(c["open_interest_date"]).isoformat() if c.get("open_interest_date") else None
                        out.append({"contrato": contrato, "subyacente": subyacente,
                                    "interes_abierto": numero(c.get("open_interest")), "fecha_oi": fecha,
                                    "multiplicador": numero(c.get("size"), True)})
                    token = d.get("next_page_token")
                    parcial = bool(token)
                    if not token or token in tokens:
                        break
                    tokens.add(token)
                    params["page_token"] = token
                except (ValueError, TypeError, KeyError, AttributeError):
                    raise FuenteNoDisponible("Alpaca Paper: respuesta de contratos inválida") from None
        finally:
            if self.cliente is None:
                cli.close()
        return out, Procedencia("alpaca_paper", LIC_ALPACA, "EE. UU. (contratos de opciones)", feed="contracts-paper",
                                nota="Solo lectura Paper. OI de cierre previo, fechado; no es intradía. Sin spot, NBBO ni patas. "
                                     + ("Cobertura parcial por límite de paginación." if parcial else ""))

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

    def operaciones_opciones(self, contratos: list[str], minutos: int = 60) -> tuple[list[OperacionOpcion], Procedencia]:
        """Cinta indicativa diferida; solo datos de mercado. Máximo 100 contratos y 3 páginas."""
        contratos = list(dict.fromkeys(contratos))
        if not contratos or len(contratos) > 100 or any(not OCC.fullmatch(c) for c in contratos):
            raise ValueError("se requieren de 1 a 100 contratos OCC válidos")
        if not 1 <= int(minutos) <= 1440:
            raise ValueError("minutos debe estar entre 1 y 1440")
        fin = datetime.now(UTC) - timedelta(seconds=RETRASO_SIP_S)
        inicio = fin - timedelta(minutes=int(minutos))
        params = {"symbols": ",".join(contratos), "feed": "indicative", "start": inicio.isoformat(),
                  "end": fin.isoformat(), "limit": 10000, "sort": "asc"}
        out, tokens = [], set()
        truncada = False
        for _ in range(3):
            d = self._get("/v1beta1/options/trades", params)
            for contrato, trades in (d.get("trades") or {}).items():
                if contrato not in contratos:
                    continue
                m = OCC.fullmatch(contrato)
                venc = date(2000 + int(m[2][:2]), int(m[2][2:4]), int(m[2][4:])).isoformat()
                for t in trades:
                    ts = instante(t["t"])
                    if not _nanosegundos(inicio.isoformat()) <= _nanosegundos(str(t["t"])) <= _nanosegundos(fin.isoformat()):
                        continue  # nunca aceptar datos posteriores al corte solicitado
                    precio, tamano = float(t["p"]), float(t["s"])
                    if not math.isfinite(precio) or not math.isfinite(tamano) or precio <= 0 or tamano <= 0:
                        raise ValueError("precio o tamaño de operación inválido")
                    out.append(OperacionOpcion(contrato, m[1], ts, str(t.get("x") or ""), precio, tamano,
                                               list(t.get("c") or []), str(t["t"]), venc, int(m[4]) / 1000,
                                               "call" if m[3] == "C" else "put"))
            token = d.get("next_page_token")
            if not token:
                break
            truncada = True
            if token in tokens:
                break
            tokens.add(token)
            params["page_token"] = token
            truncada = False
        else:
            truncada = bool(token)
        return out, Procedencia("alpaca", LIC_ALPACA, "EE. UU. (OPRA indicativo)", feed="indicative",
                                retraso_s=RETRASO_SIP_S,
                                nota="Cinta indicativa solicitada con ≥ 15 min de retraso. Sin NBBO del instante, patas ni OI. "
                                     + ("Resultado parcial: límite de paginación alcanzado." if truncada else ""))

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
            out.append(c)
        nota_spot = self._unir_spot(subyacente, out)
        for c in out:
            dias_v = (date.fromisoformat(c.vencimiento) - hoy).days
            s_iv = c.spot or spot  # el spot unido de la misma referencia; si no hay, el último cierre (sin GEX)
            if c.iv is None and s_iv and c.bid and c.ask and dias_v >= 1:
                _iv_calculada(c, s_iv, tasa, dias_v)
        return out, Procedencia("alpaca", LIC_ALPACA + "; feed «indicative» de OPRA, diferido", "EE. UU. (OPRA indicativo)",
                                feed="indicative", retraso_s=15 * 60,
                                nota="Feed indicativo gratuito (diferido ~15 min según Alpaca). Sin interés abierto. Si "
                                     "el proveedor no trae IV, se calcula con Black-Scholes-Merton europeo sobre el punto "
                                     "medio (origen «calculado»); las opciones de EE. UU. son americanas. " + nota_spot)

    def _unir_spot(self, origen: str, contratos: list[ContratoOpcion]) -> str:
        """Spot de la MISMA referencia temporal que la cadena: R = la cotización más reciente de la cadena; spot = la
        última operación de la acción en Alpaca en (R − 60 s, R]. Solo los contratos cotizados a ≤ 60 s de R lo reciben;
        los demás quedan sin spot y el GEX los excluye y los cuenta. Nunca se usa un cierre ni otra hora."""
        if not contratos:
            return ""
        ref = max(datetime.fromisoformat(c.instante) for c in contratos)
        feed = "sip" if datetime.now(UTC) - ref >= timedelta(seconds=RETRASO_SIP_S) else "iex"  # SIP solo con ≥ 15 min
        try:
            d = self._get(f"/v2/stocks/{origen}/trades", {"feed": feed, "start": (ref - timedelta(seconds=VENTANA_SPOT_S)).isoformat(),
                                                         "end": ref.isoformat(), "limit": 1, "sort": "desc"})
        except FuenteNoDisponible as e:
            return f"Sin spot unido ({e}): el GEX no se calcula."
        t = (d.get("trades") or [None])[0]
        if not t or not t.get("p"):
            return f"Sin operación de {origen} en el minuto previo a la referencia {ref.isoformat()}: sin spot, sin GEX."
        hora = datetime.fromisoformat(instante(t["t"][:26] + "Z" if len(t["t"]) > 27 else t["t"]))
        if abs((ref - hora).total_seconds()) > VENTANA_SPOT_S:
            return "La operación más cercana está a más de 60 s de la referencia: sin spot, sin GEX."
        n = 0
        for c in contratos:
            if abs((datetime.fromisoformat(c.instante) - ref).total_seconds()) <= VENTANA_SPOT_S:
                c.spot, c.moneda, n = float(t["p"]), "USD", n + 1
        return (f"Spot {float(t['p']):.2f} USD: última operación de {origen} ({feed.upper()}, Alpaca) a las {hora.isoformat()}, "
                f"≤ 60 s antes de la referencia {ref.isoformat()}; unido a {n} de {len(contratos)} contratos cotizados a "
                "≤ 60 s de ella.")


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
