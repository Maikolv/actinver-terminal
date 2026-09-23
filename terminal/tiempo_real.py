"""Flujo en vivo (solo lectura): último precio de acciones y ETF de EE. UU. por WebSocket de Alpaca (IEX).

Sirve para las emisoras del SIC: en el Reto cotizan en MXN y su precio sigue al de su bolsa de origen por el
tipo de cambio. Las emisoras locales de la BMV no tienen fuente gratuita en vivo y siguen con su cierre.

- Solo se conecta a los dominios de datos de Alpaca; no existe código que llame a la API de operaciones.
- Plan gratuito: una conexión, hasta 30 símbolos. Prioridad: posiciones, propuestas vigentes, referencias.
- Si el WebSocket falla repetidamente se consulta el último precio por REST (etiquetado «retrasado»).
- Las cotizaciones se guardan como precio del día (`alpaca_vivo`) y el cierre oficial las sustituye.
- Las credenciales nunca se registran ni se exponen en el estado.
"""
from __future__ import annotations

import json
import logging
import threading
import time

import httpx
import pandas as pd

from . import db, vigencia
from .config import Ajustes, credencial, secreto
from .ingesta import PROVEEDOR_VIVO

log = logging.getLogger("terminal.tiempo_real")
URL_WS = "wss://stream.data.alpaca.markets/v2/{feed}"
URL_ULTIMOS = "https://data.alpaca.markets/v2/stocks/trades/latest"
ERRORES_FATALES = {401, 402, 409}  # sin autenticar, credencial rechazada, suscripción insuficiente


class ErrorFlujo(Exception):
    pass


class ErrorFatal(ErrorFlujo):
    pass


def simbolos(con, maximo: int = 30, referencias: list[str] | None = None) -> dict[str, list[str]]:
    """símbolo → ids de instrumento. Prioridad: posiciones, propuestas vigentes, referencias, resto del universo."""
    ins = {r["id"]: r["listado_referencia"] for r in con.execute(
        "SELECT id, listado_referencia FROM instrumentos WHERE estado='activo' AND moneda_referencia='USD' "
        "AND listado_referencia IS NOT NULL AND listado_referencia <> ''")}
    orden: list[str] = []
    posiciones = con.execute("SELECT instrumento_id, SUM(CASE tipo WHEN 'compra' THEN cantidad WHEN 'venta' THEN -cantidad "
                             "ELSE 0 END) AS n FROM transacciones WHERE anulada=0 AND instrumento_id IS NOT NULL "
                             "GROUP BY instrumento_id HAVING n > 0")
    orden += [r[0] for r in posiciones]
    for (res,) in con.execute("SELECT resultado FROM propuestas WHERE id IN (SELECT MAX(id) FROM propuestas GROUP BY tipo)"):
        try:
            orden += [p["id"] for p in json.loads(res).get("pesos") or []]
        except (ValueError, TypeError):
            continue
    orden += list(referencias or []) + sorted(ins)
    mapa: dict[str, list[str]] = {}
    for iid in orden:
        s = ins.get(iid)
        if not s or (s not in mapa and len(mapa) >= maximo):
            continue
        mapa.setdefault(s, [])
        if iid not in mapa[s]:
            mapa[s].append(iid)
    return mapa


class FlujoVivo:
    def __init__(self, ajustes: Ajustes):
        self.ajustes = ajustes
        self.cfg = dict(ajustes.get("tiempo_real") or {})
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._ultimos: dict[str, tuple[float, str]] = {}
        self._pendientes: set[str] = set()
        self._base: dict[str, float] = {}
        self._nuevos = False
        self._ultimo_recalculo = time.monotonic()
        self._mapa: dict[str, list[str]] = {}
        self._tipo = "tiempo_real"
        self.estado = {"modo": "iniciando", "mensaje": "", "mensajes": 0, "ultimo_precio": None}

    # --- control -------------------------------------------------------------------------------------------
    def configurado(self) -> bool:
        return bool(credencial("alpaca") and secreto("alpaca"))

    def iniciar(self) -> None:
        threading.Thread(target=self._bucle, name="flujo-vivo", daemon=True).start()

    def detener(self) -> None:
        self._stop.set()

    def resumen(self) -> dict:
        with self._lock:
            return {"activo": self.estado["modo"] in ("websocket", "consulta"), "proveedor": "alpaca",
                    "feed": self.cfg.get("feed", "iex"), "simbolos": len(self._mapa),
                    "limite_simbolos": int(self.cfg.get("max_simbolos", 30)), "tipo_dato": self._tipo,
                    "movimiento_max": round(self._movimiento(), 4), **self.estado}

    def _fijar(self, modo: str, mensaje: str = "") -> None:
        with self._lock:
            self.estado.update(modo=modo, mensaje=mensaje)

    # --- señales para el motor --------------------------------------------------------------------------------
    def _movimiento(self) -> float:
        movs = [abs(p / self._base[s] - 1) for s, (p, _) in self._ultimos.items() if self._base.get(s)]
        return max(movs, default=0.0)

    def debe_recalcular(self) -> bool:
        """Hay precios nuevos guardados y (movimiento ≥ umbral o pasó el intervalo), con un mínimo entre cálculos."""
        with self._lock:
            if not self._nuevos:
                return False
            transcurrido = time.monotonic() - self._ultimo_recalculo
            if transcurrido < float(self.cfg.get("recalculo_minimo_seg", 120)):
                return False
            return (self._movimiento() >= float(self.cfg.get("umbral_movimiento", 0.01))
                    or transcurrido >= float(self.cfg.get("recalcular_cada_min", 5)) * 60)

    def marcar_recalculo(self) -> None:
        with self._lock:
            self._base = {s: p for s, (p, _) in self._ultimos.items()}
            self._nuevos = False
            self._ultimo_recalculo = time.monotonic()

    # --- bucle principal ------------------------------------------------------------------------------------
    def _bucle(self) -> None:
        espera, fallos = 1.0, 0
        while not self._stop.wait(espera):
            if not self.cfg.get("activo", True):
                self._fijar("desactivado", "Desactivado en [tiempo_real] activo = false")
                espera = 300
                continue
            if self.ajustes.es_demo:
                self._fijar("demo", "Modo demostración: el flujo en vivo solo opera con datos reales")
                espera = 30
                continue
            if not self.configurado():
                self._fijar("sin_credencial", "Falta ALPACA_API_KEY_ID o ALPACA_API_SECRET_KEY en .env")
                espera = 120
                continue
            if not vigencia.mercado_abierto("XNYS"):
                self._fijar("mercado_cerrado", "Mercado de EE. UU. cerrado: se usan los cierres")
                espera = 60
                continue
            self._actualizar_mapa()
            if not self._mapa:
                self._fijar("sin_simbolos", "No hay instrumentos de EE. UU. activos en el universo")
                espera = 300
                continue
            try:
                self._websocket()
                fallos, espera = 0, 2
            except ErrorFatal as e:
                self._fijar("error", str(e))
                log.warning("flujo en vivo detenido: %s", e)
                espera = 900
            except Exception as e:  # noqa: BLE001 - red, protocolo o límite de conexiones: reintentar
                fallos += 1
                self._fijar("reconectando", f"{type(e).__name__}: {str(e)[:120]}")
                log.info("flujo en vivo: reconexión %s (%s)", fallos, type(e).__name__)
                if fallos >= 3:
                    self._consulta(minutos=5)
                espera = min(5 * 2 ** min(fallos, 5), 120)
            finally:
                self._guardar()

    def _actualizar_mapa(self) -> dict[str, list[str]]:
        con = db.conectar()
        try:
            ref = (self.ajustes.get("referencias") or {}).get("sp500")
            mapa = simbolos(con, int(self.cfg.get("max_simbolos", 30)), [ref] if ref else [])
        finally:
            con.close()
        with self._lock:
            self._mapa = mapa
        return mapa

    # --- WebSocket ------------------------------------------------------------------------------------------
    def _esperar(self, ws, esperado: str) -> None:
        limite = time.monotonic() + 20
        while time.monotonic() < limite:
            for m in json.loads(ws.recv(timeout=20)):
                if m.get("T") == "error":
                    self._error(m)
                if m.get("T") == "success" and m.get("msg") == esperado:
                    return
        raise ErrorFlujo(f"sin respuesta «{esperado}»")

    @staticmethod
    def _error(m: dict) -> None:
        codigo, texto = m.get("code"), str(m.get("msg", ""))[:120]
        if codigo in ERRORES_FATALES:
            raise ErrorFatal(f"Alpaca rechazó la conexión ({codigo} {texto}); revise las claves en .env")
        raise ErrorFlujo(f"Alpaca {codigo} {texto}")  # 406: otra conexión abierta con la misma cuenta

    def _websocket(self) -> None:
        from websockets.sync.client import connect
        feed = self.cfg.get("feed", "iex")
        self._fijar("conectando")
        with connect(URL_WS.format(feed=feed), open_timeout=15, close_timeout=5, max_size=2 ** 22) as ws:
            self._esperar(ws, "connected")
            ws.send(json.dumps({"action": "auth", "key": credencial("alpaca"), "secret": secreto("alpaca")}))
            self._esperar(ws, "authenticated")
            suscritos = set(self._mapa)
            ws.send(json.dumps({"action": "subscribe", "trades": sorted(suscritos)}))
            with self._lock:
                self._tipo = "tiempo_real"
            self._fijar("websocket", f"Conectado a IEX en vivo ({len(suscritos)} símbolos)")
            guardado = revision = time.monotonic()
            while not self._stop.is_set():
                try:
                    crudo = ws.recv(timeout=5)
                except TimeoutError:
                    crudo = None
                if crudo:
                    self._procesar(json.loads(crudo))
                ahora = time.monotonic()
                if ahora - guardado >= float(self.cfg.get("guardar_cada_seg", 15)):
                    self._guardar()
                    guardado = ahora
                if ahora - revision >= 300:  # la cartera o las propuestas pudieron cambiar
                    revision = ahora
                    if not vigencia.mercado_abierto("XNYS") or self.ajustes.es_demo:
                        return
                    nuevos = set(self._actualizar_mapa())
                    if nuevos - suscritos:
                        ws.send(json.dumps({"action": "subscribe", "trades": sorted(nuevos - suscritos)}))
                    if suscritos - nuevos:
                        ws.send(json.dumps({"action": "unsubscribe", "trades": sorted(suscritos - nuevos)}))
                    suscritos = nuevos

    def _procesar(self, mensajes: list[dict]) -> None:
        for m in mensajes:
            if m.get("T") == "t" and m.get("p"):
                with self._lock:
                    self._ultimos[m["S"]] = (float(m["p"]), m["t"])
                    self._pendientes.add(m["S"])
                    self.estado["mensajes"] += 1
                    self.estado["ultimo_precio"] = m["t"]
            elif m.get("T") == "error":
                self._error(m)

    # --- respaldo por consulta REST ---------------------------------------------------------------------------
    def _consulta(self, minutos: float) -> None:
        with self._lock:
            self._tipo = "retrasado"
        self._fijar("consulta", "WebSocket no disponible: último precio por consulta cada minuto")
        cab = {"APCA-API-KEY-ID": credencial("alpaca") or "", "APCA-API-SECRET-KEY": secreto("alpaca") or ""}
        fin = time.monotonic() + minutos * 60
        with httpx.Client(timeout=20) as cli:
            while time.monotonic() < fin and not self._stop.is_set() and vigencia.mercado_abierto("XNYS"):
                try:
                    r = cli.get(URL_ULTIMOS, params={"symbols": ",".join(sorted(self._mapa)), "feed": self.cfg.get("feed", "iex")},
                                headers=cab)
                except httpx.HTTPError as e:
                    self._fijar("reconectando", f"consulta: {type(e).__name__}")
                    return
                if r.status_code in (401, 403):
                    raise ErrorFatal(f"Alpaca rechazó la credencial (HTTP {r.status_code}); revise .env")
                if r.status_code == 200:
                    self._procesar([{"T": "t", "S": s, "p": t.get("p"), "t": t.get("t")}
                                    for s, t in (r.json().get("trades") or {}).items()])
                    self._guardar()
                self._stop.wait(60)

    # --- persistencia ---------------------------------------------------------------------------------------
    def _guardar(self) -> None:
        with self._lock:
            pendientes, self._pendientes = self._pendientes, set()
            datos = [(s, *self._ultimos[s]) for s in pendientes if s in self._ultimos]
            mapa, tipo = dict(self._mapa), self._tipo
        if not datos or self.ajustes.es_demo:
            return
        filas, ts = [], db.ahora()
        for s, precio, hora in datos:
            t = pd.Timestamp(hora)
            t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
            fecha = t.tz_convert("America/New_York").date().isoformat()
            filas += [(iid, fecha, precio, None, None, "USD", PROVEEDOR_VIVO, tipo, t.isoformat(), ts)
                      for iid in mapa.get(s, [])]
        con = db.conectar()
        try:
            with db.transaccion(con):
                con.executemany("INSERT OR REPLACE INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, proveedor, tipo_dato, hora_cotizacion, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)", filas)
        finally:
            con.close()
        with self._lock:
            self._nuevos = True
