"""Proveedores de cotizaciones intercambiables (`MarketDataProvider`) para el monitor del Reto.

Principios:
- Una cotización solo es «confiable» para un instrumento del simulador si el proveedor tiene COBERTURA VERIFICADA de
  ese instrumento exacto (serie, moneda MXN y mercado BMV local o SIC) y el dato no es obsoleto. Si no, la interfaz
  muestra «SIN PRECIO CONFIABLE». Una cotización de la bolsa de origen en USD nunca sustituye en silencio a la de la
  BMV en pesos: se muestra aparte como «referencia externa».
- El estado REAL_TIME / DELAYED / EOD / UNKNOWN se calcula con la latencia MEDIDA (hora de recepción − hora del
  evento de mercado), no con la publicidad del proveedor.
- Conmutación a otro proveedor solo si cubre el mismo instrumento con calidad comprobada (cobertura verificada y
  latencia medida dentro del umbral). Sin eso: «SIN PRECIO CONFIABLE».
- Credenciales solo por variables de entorno (.env, excluido de Git). Nunca se registran ni se devuelven.
- Los conectores contratados (BMV, LSEG, ICE) se describen con un archivo de especificación que el usuario copia de
  la documentación de su contrato. Sin contrato, especificación o credenciales quedan «pendiente» con la lista exacta
  de lo que falta; la terminal no inventa endpoints.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

from . import vigencia
from .config import RAIZ

SIN_PRECIO = "SIN PRECIO CONFIABLE"
ESTADOS = ("REAL_TIME", "DELAYED", "EOD", "UNKNOWN")
UMBRAL_TIEMPO_REAL_S = 15          # latencia medida máxima para llamar «REAL_TIME» a una cotización
UMBRAL_RETRASADO_S = 20 * 60       # hasta 20 min: DELAYED
MERCADOS = ("local", "SIC", "origen_extranjero", "fondo")


class ProveedorNoDisponible(Exception):
    """El proveedor no está configurado o no puede usarse; `pendientes` dice exactamente qué falta."""

    def __init__(self, mensaje: str, pendientes: list[str] | None = None):
        super().__init__(mensaje)
        self.pendientes = pendientes or []


# ----------------------------------------------------------------------------------------------------------------
@dataclass
class Cotizacion:
    proveedor: str
    simbolo_origen: str
    simbolo_normalizado: str
    instrumento_id: str | None
    mercado: str                   # local | SIC | origen_extranjero | fondo
    bolsa: str | None
    precio: float
    moneda: str
    hora_evento: str               # hora del evento de mercado (UTC ISO)
    hora_recepcion: str            # hora en que la terminal la recibió (UTC ISO)
    latencia_declarada_s: float | None = None
    estado_latencia: str = "UNKNOWN"
    sintetico: bool = False
    detalle: str = ""

    @property
    def latencia_medida_s(self) -> float | None:
        try:
            return (pd.Timestamp(self.hora_recepcion) - pd.Timestamp(self.hora_evento)).total_seconds()
        except (ValueError, TypeError):
            return None

    def a_dict(self) -> dict:
        return {**asdict(self), "latencia_medida_s": self.latencia_medida_s}


def _utc(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def ahora_iso() -> str:
    return datetime.now(UTC).isoformat()


def clasificar_latencia(hora_evento: str, hora_recepcion: str, es_cierre: bool = False) -> str:
    """Estado por latencia medida. Un cierre diario es EOD aunque se reciba en segundos."""
    if es_cierre:
        return "EOD"
    try:
        lat = (_utc(hora_recepcion) - _utc(hora_evento)).total_seconds()
    except (ValueError, TypeError):
        return "UNKNOWN"
    if lat < -5:  # reloj del proveedor adelantado: no se puede afirmar nada
        return "UNKNOWN"
    if lat <= UMBRAL_TIEMPO_REAL_S:
        return "REAL_TIME"
    if lat <= UMBRAL_RETRASADO_S:
        return "DELAYED"
    return "UNKNOWN"


# ----------------------------------------------------------------------------------------------------------------
# Símbolos y catálogo
def _limpiar(txt: str) -> str:
    return re.sub(r"\s+", " ", str(txt or "").strip().upper())


def normalizar_simbolo(texto: str, instrumentos: dict[str, dict]) -> dict | None:
    """Convierte un símbolo de origen a (instrumento del catálogo, mercado, moneda esperada).

    - «BMV:WALMEX», «WALMEX *», «WALMEX*», «WALMEX.MX»  → BMV:WALMEX, mercado local, MXN
    - «BMV:AAPL», «AAPL *» (listado SIC en la BMV)       → SIC:AAPL, mercado SIC, MXN
    - «NASDAQ:AAPL», «NYSE:AA»                           → SIC:… pero mercado «origen_extranjero», USD (NO es la cotización BMV)
    Devuelve None si no pertenece al catálogo.
    """
    t = _limpiar(texto)
    if not t:
        return None
    from .clasificacion import exigir_valor
    exigir_valor(t)  # un CFD o un criptoactivo nunca se normaliza a un instrumento del Reto
    bolsa, _, tk = t.rpartition(":")
    tk = tk.replace(".MX", "").strip()
    serie = None
    if " " in tk:
        tk, serie = tk.split(" ", 1)
    elif tk.endswith("*"):
        tk, serie = tk[:-1], "*"
    tk = tk.strip()
    por_clave: dict[str, list[dict]] = {}
    por_origen: dict[str, list[dict]] = {}
    for i in instrumentos.values():
        por_clave.setdefault(_limpiar(i.get("clave")), []).append(i)
        if i.get("moneda_referencia") == "USD" and i.get("listado_referencia"):
            por_origen.setdefault(_limpiar(i["listado_referencia"]), []).append(i)

    def elegir(cands):
        if serie and len(cands) > 1:
            con_serie = [c for c in cands if _limpiar(c.get("serie")) == _limpiar(serie)]
            cands = con_serie or cands
        return cands[0] if cands else None

    if bolsa in ("", "BMV", "BIVA", "MX"):
        i = elegir(por_clave.get(tk, []))
        if i is None and bolsa in ("BMV", "BIVA", ""):
            # TradingView lista el SIC con el ticker de origen: BMV:AAPL → clave SIC «AAPL»
            i = elegir([c for c in por_origen.get(tk, []) if c.get("mercado_operable") == "BMV-SIC"])
        if i is None:
            return None
        mercado = "SIC" if i.get("mercado_operable") == "BMV-SIC" else ("fondo" if str(i.get("clase", "")).startswith("fondo") else "local")
        return {"instrumento_id": i["id"], "mercado": mercado, "moneda": i.get("moneda_operable") or "MXN",
                "bolsa": bolsa or "BMV", "simbolo_normalizado": i["id"]}
    i = elegir(por_origen.get(tk, []))
    if i is None:
        return None
    return {"instrumento_id": i["id"], "mercado": "origen_extranjero", "moneda": "USD", "bolsa": bolsa,
            "simbolo_normalizado": f"{bolsa}:{tk}"}


def catalogo(con: sqlite3.Connection) -> list[dict]:
    """Catálogo del simulador si fue importado; si no, el universo verificado (marcado como tal)."""
    sim = {r[0] for r in con.execute("SELECT id FROM universo_simulador")}
    filas = [dict(r) for r in con.execute("SELECT * FROM instrumentos WHERE estado IN ('activo','por_confirmar') ORDER BY id")]
    for f in filas:
        f["en_catalogo_simulador"] = (f["id"] in sim) if sim else None
        f["mercado"] = ("SIC" if f["mercado_operable"] == "BMV-SIC" else
                        "fondo" if str(f["clase"]).startswith("fondo") else "local")
    return [f for f in filas if f["en_catalogo_simulador"] is not False]


# ----------------------------------------------------------------------------------------------------------------
class MarketDataProvider:
    """Interfaz común. Las subclases implementan `_consultar(instrumento)`."""
    nombre = "base"
    descripcion = ""
    sintetico = False
    entrega_mercado: tuple[str, ...] = ()  # mercados cuya cotización BMV/MXN puede entregar (local, SIC, fondo)
    latencia_declarada_s: float | None = None
    ttl_cache_s = 30.0
    max_por_minuto = 60

    def __init__(self, con: sqlite3.Connection | None = None, entorno: dict | None = None):
        self.con = con
        self.env = entorno if entorno is not None else os.environ
        self._cache: dict[str, tuple[float, Cotizacion]] = {}
        self._llamadas: list[float] = []
        self._lock = threading.Lock()

    # --- configuración ------------------------------------------------------------------------------------------
    def pendientes(self) -> list[str]:
        """Lo que falta para poder usar el proveedor (vacío = listo para verificar cobertura)."""
        return []

    def configurado(self) -> bool:
        return not self.pendientes()

    def estado(self) -> dict:
        p = self.pendientes()
        return {"proveedor": self.nombre, "descripcion": self.descripcion, "configurado": not p, "pendientes": p,
                "sintetico": self.sintetico, "mercados": list(self.entrega_mercado),
                "latencia_declarada_s": self.latencia_declarada_s, "metricas": self.metricas()}

    # --- consulta con caché, límite y métricas -----------------------------------------------------------------------
    def cotizacion(self, instrumento: dict) -> Cotizacion:
        p = self.pendientes()
        if p:
            raise ProveedorNoDisponible(f"{self.nombre}: no configurado", p)
        clave = instrumento["id"]
        with self._lock:
            c = self._cache.get(clave)
            if c and time.monotonic() - c[0] < self.ttl_cache_s:
                return c[1]
            ahora = time.monotonic()
            self._llamadas = [x for x in self._llamadas if ahora - x < 60]
            if len(self._llamadas) >= self.max_por_minuto:
                raise ProveedorNoDisponible(f"{self.nombre}: límite de {self.max_por_minuto} consultas/min alcanzado")
            self._llamadas.append(ahora)
        try:
            q = self._consultar(instrumento)
        except ProveedorNoDisponible:
            self._metrica(False, "no disponible")
            raise
        except Exception as e:  # noqa: BLE001 - se registra el tipo, nunca el mensaje (podría contener URL con clave)
            self._metrica(False, type(e).__name__)
            raise ProveedorNoDisponible(f"{self.nombre}: fallo {type(e).__name__}") from None
        validar_cotizacion(q)
        self._metrica(True, None)
        with self._lock:
            self._cache[clave] = (time.monotonic(), q)
        return q

    def _consultar(self, instrumento: dict) -> Cotizacion:  # pragma: no cover - lo implementan las subclases
        raise NotImplementedError

    def con_reintentos(self, fn, intentos: int = 3, espera: float = 1.0):
        """Reconexión con espera exponencial para conectores de red."""
        ultimo = None
        for i in range(intentos):
            try:
                return fn()
            except (httpx.HTTPError, ConnectionError, TimeoutError) as e:
                ultimo = e
                if i < intentos - 1:
                    time.sleep(espera * 2 ** i)
        raise ProveedorNoDisponible(f"{self.nombre}: sin conexión tras {intentos} intentos ({type(ultimo).__name__})")

    # --- métricas persistentes -----------------------------------------------------------------------------------------
    def _metrica(self, ok: bool, error: str | None) -> None:
        if self.con is None:
            return
        ts = ahora_iso()
        self.con.execute("INSERT INTO metricas_proveedor (proveedor) VALUES (?) ON CONFLICT(proveedor) DO NOTHING", (self.nombre,))
        if ok:
            self.con.execute("UPDATE metricas_proveedor SET solicitudes=solicitudes+1, fallos_consecutivos=0, ultimo_exito=? "
                             "WHERE proveedor=?", (ts, self.nombre))
        else:
            self.con.execute("UPDATE metricas_proveedor SET solicitudes=solicitudes+1, fallos=fallos+1, "
                             "fallos_consecutivos=fallos_consecutivos+1, ultimo_fallo=?, ultimo_error=? WHERE proveedor=?",
                             (ts, (error or "")[:120], self.nombre))
        self.con.commit()

    def metricas(self) -> dict:
        if self.con is None:
            return {}
        f = self.con.execute("SELECT * FROM metricas_proveedor WHERE proveedor=?", (self.nombre,)).fetchone()
        return dict(f) if f else {}


def validar_cotizacion(q: Cotizacion) -> None:
    if not isinstance(q.precio, (int, float)) or not math.isfinite(q.precio) or q.precio <= 0:
        raise ProveedorNoDisponible(f"{q.proveedor}: precio inválido")
    if q.estado_latencia not in ESTADOS:
        raise ProveedorNoDisponible(f"{q.proveedor}: estado de latencia inválido")
    if q.mercado not in MERCADOS:
        raise ProveedorNoDisponible(f"{q.proveedor}: mercado inválido")
    _utc(q.hora_evento), _utc(q.hora_recepcion)  # lanzan si no son fechas


# ----------------------------------------------------------------------------------------------------------------
# Conectores contratados: definidos por un archivo de especificación del contrato (no se inventan endpoints)
def _ruta(obj, camino: str):
    for parte in camino.split("."):
        if isinstance(obj, list):
            obj = obj[int(parte)]
        elif isinstance(obj, dict):
            obj = obj.get(parte)
        else:
            return None
    return obj


class ConectorContratado(MarketDataProvider):
    """Conector REST descrito por una especificación JSON copiada de la documentación del contrato.

    Variables: <PREFIJO>_ESPECIFICACION (ruta al JSON), <PREFIJO>_API_KEY y las que declare la especificación.
    Formato de la especificación en docs/proveedores.md. Sin especificación no se hace ninguna petición.
    """
    prefijo = "X"
    requisito_contrato = ""
    ttl_cache_s = 2.0

    def __init__(self, *a, cliente: httpx.Client | None = None, **k):
        super().__init__(*a, **k)
        self._cliente = cliente
        self._espec: dict | None = None

    def especificacion(self) -> dict | None:
        if self._espec is None:
            ruta = self.env.get(f"{self.prefijo}_ESPECIFICACION")
            if ruta:
                p = Path(ruta)
                p = p if p.is_absolute() else RAIZ / p
                if p.exists():
                    self._espec = json.loads(p.read_text(encoding="utf-8"))
        return self._espec

    def pendientes(self) -> list[str]:
        faltan = []
        if not self.env.get(f"{self.prefijo}_ESPECIFICACION"):
            faltan.append(f"{self.requisito_contrato}; con la documentación del contrato, crear la especificación "
                          f"(plantilla config/proveedores/ejemplo_especificacion.json) y fijar {self.prefijo}_ESPECIFICACION")
        elif self.especificacion() is None:
            faltan.append(f"{self.prefijo}_ESPECIFICACION apunta a un archivo inexistente")
        if not self.env.get(f"{self.prefijo}_API_KEY"):
            faltan.append(f"credencial {self.prefijo}_API_KEY (entregada por el proveedor con el contrato)")
        e = self.especificacion() or {}
        for var in e.get("variables_requeridas", []):
            if not self.env.get(var):
                faltan.append(f"variable {var} exigida por la especificación")
        if e and not (e.get("cotizacion") or {}).get("ruta"):
            faltan.append("la especificación no define cotizacion.ruta")
        if e and not (self.env.get(e.get("variable_url_base", f"{self.prefijo}_URL_BASE")) or e.get("url_base")):
            faltan.append(f"URL base del servicio contratado ({e.get('variable_url_base', f'{self.prefijo}_URL_BASE')})")
        return faltan

    @property
    def cliente(self) -> httpx.Client:
        if self._cliente is None:
            self._cliente = httpx.Client(timeout=10)
        return self._cliente

    def simbolo_proveedor(self, instrumento: dict) -> str:
        e = self.especificacion() or {}
        mapa = e.get("mapa_simbolos") or {}
        if instrumento["id"] in mapa:
            return mapa[instrumento["id"]]
        plantilla = e.get("plantilla_simbolo", "{clave}{serie}")
        serie = (instrumento.get("serie") or "").replace(" ", "")
        return plantilla.format(clave=instrumento.get("clave", ""), serie=serie, id=instrumento["id"],
                                origen=instrumento.get("listado_referencia") or "")

    def _consultar(self, instrumento: dict) -> Cotizacion:
        e = self.especificacion() or {}
        c = e["cotizacion"]
        base = self.env.get(e.get("variable_url_base", f"{self.prefijo}_URL_BASE")) or e.get("url_base")
        if not base:
            raise ProveedorNoDisponible(f"{self.nombre}: falta la URL base", [f"{self.prefijo}_URL_BASE"])
        sim = self.simbolo_proveedor(instrumento)
        aut = e.get("autenticacion") or {"tipo": "cabecera", "nombre": "Authorization", "formato": "Bearer {clave}"}
        clave = self.env.get(f"{self.prefijo}_API_KEY", "")
        headers, params = {}, {k: str(v).format(simbolo=sim) for k, v in (c.get("parametros") or {}).items()}
        if aut.get("tipo") == "parametro":
            params[aut["nombre"]] = clave
        else:
            headers[aut.get("nombre", "Authorization")] = aut.get("formato", "{clave}").format(clave=clave)
        url = base.rstrip("/") + c["ruta"].format(simbolo=sim)
        r = self.con_reintentos(lambda: self.cliente.request(c.get("metodo", "GET"), url, params=params, headers=headers))
        if r.status_code in (401, 403):
            raise ProveedorNoDisponible(f"{self.nombre}: credencial rechazada (HTTP {r.status_code})")
        if r.status_code != 200:
            raise ProveedorNoDisponible(f"{self.nombre}: HTTP {r.status_code}")
        d = r.json()
        campos = c["campos"]
        recepcion = ahora_iso()
        moneda = str(_ruta(d, campos["moneda"]) or "") if campos.get("moneda") else str(e.get("moneda_fija") or "")
        simbolo_resp = str(_ruta(d, campos["simbolo"]) or sim) if campos.get("simbolo") else sim
        hora = _ruta(d, campos["hora_evento"])
        if hora is None:
            raise ProveedorNoDisponible(f"{self.nombre}: la respuesta no trae hora del evento")
        if isinstance(hora, (int, float)):  # epoch en s o ms según la especificación
            hora = pd.Timestamp(hora, unit=campos.get("unidad_hora", "s"), tz="UTC").isoformat()
        mercado = "SIC" if instrumento.get("mercado_operable") == "BMV-SIC" else "local"
        return Cotizacion(self.nombre, simbolo_resp, instrumento["id"], instrumento["id"], mercado,
                          str(_ruta(d, campos["bolsa"])) if campos.get("bolsa") else e.get("bolsa"),
                          float(_ruta(d, campos["precio"])), moneda, _utc(hora).isoformat(), recepcion,
                          e.get("latencia_declarada_s"), clasificar_latencia(hora, recepcion))


class BmvLicensedProvider(ConectorContratado):
    nombre = "bmv_licenciado"
    descripcion = ("Producto de datos de Grupo BMV (Web Services de Grupo BMV o distribuidor autorizado) con acceso "
                   "programático contratado. SiBolsa es la plataforma de consulta de Grupo BMV: su pantalla no se "
                   "extrae; su equivalente programático es este contrato")
    prefijo = "BMV"
    entrega_mercado = ("local", "SIC")
    requisito_contrato = ("Contrato de datos de mercado con Grupo BMV o un distribuidor autorizado que permita acceso "
                          "programático a cotizaciones del mercado local y del SIC (uso no profesional) y su documentación técnica")


class EodhdDiferidoProvider(ConectorContratado):
    """Precio diferido de la BMV (EODHD «Live OHLCV», 15–20 min de retraso según su documentación) con la especificación
    config/proveedores/eodhd_diferido.json. APAGADO por omisión: se activa con EODHD_DIFERIDO_ESPECIFICACION. Cada
    consulta gasta una de las 20 peticiones diarias del plan gratuito (las mismas de los cierres), así que sin plan de pago
    solo sirve para MEDIR el retraso real en unas pocas emisoras. EODHD declara sus precios «indicativos»; no es un
    contrato con Grupo BMV. El retraso se clasifica con la hora del evento que devuelve, nunca se supone."""
    nombre = "eodhd_diferido"
    descripcion = "Precio diferido BMV de EODHD (15–20 min declarados; se mide con la hora del evento)"
    prefijo = "EODHD_DIFERIDO"
    entrega_mercado = ("local",)
    requisito_contrato = "Clave EODHD (plan gratuito: 20 peticiones/día compartidas con los cierres; planes de pago: 100,000)"

    def pendientes(self) -> list[str]:  # usa la misma clave EODHD_API_KEY de los cierres
        return [p for p in super().pendientes() if "EODHD_DIFERIDO_API_KEY" not in p] + (
            [] if self.env.get("EODHD_API_KEY") else ["credencial EODHD_API_KEY"])

    def simbolo_proveedor(self, instrumento: dict) -> str:  # mismo símbolo que los cierres EODHD (GMEXICOB.MX, AC.MX)
        mapa = (self.especificacion() or {}).get("mapa_simbolos") or {}
        return mapa.get(instrumento["id"]) or EodhdBmvProvider.simbolo(None, instrumento)

    def _consultar(self, instrumento: dict) -> Cotizacion:
        self.env = {**self.env, "EODHD_DIFERIDO_API_KEY": self.env.get("EODHD_API_KEY", "")}
        return super()._consultar(instrumento)


class InfoselProvider(ConectorContratado):
    """Infosel Market API v3 (Infosel HUB): último hecho y mejores posturas de BMV y del SIC en MXN.

    Contrato público de la API (documentación Swagger de su entorno de pruebas, versión 3.21):
      GET {INFOSEL_URL_BASE}/api/v3/instruments/last?instrumentKey=<mercado>/<tipoValor>/<bolsa>/<símbolo>
      autenticación: cabecera «Authorization: Bearer <JWT>» (el token lo entrega Infosel con el contrato)
      claves: BMV local «1/12576/0/AC*», BMV-SIC «1/12609/0/AAPL*»; símbolo = emisora + serie sin espacios
      respuesta: {"data": [{"uniqueKey", "emisora", "serie", "precioActual", "fechaPrecioActual" (DD-MM-AAAA),
                 "hora" (HH:MM:SS, hora de la Ciudad de México), "posturaPrecioCompra", "posturaPrecioVenta", ...}]}
    La especificación JSON es opcional: solo sirve para corregir símbolos con «mapa_simbolos»."""
    nombre = "infosel"
    descripcion = "Infosel Market API v3 (Infosel HUB) — último hecho BMV y SIC en MXN con acceso contratado"
    prefijo = "INFOSEL"
    entrega_mercado = ("local", "SIC")
    requisito_contrato = ("Contrato de las APIs financieras de Infosel (infosel.com/apis) con derechos de BMV para uso "
                          "no profesional")
    RUTA = "/api/v3/instruments/last"
    MERCADOS_CLAVE = {"local": "1/12576/0", "SIC": "1/12609/0"}
    CAMPOS = "uniqueKey,emisora,serie,precioActual,fechaPrecioActual,hora,posturaPrecioCompra,posturaPrecioVenta"

    def pendientes(self) -> list[str]:
        faltan = []
        if not self.env.get("INFOSEL_API_KEY"):
            faltan.append(f"{self.requisito_contrato}; token INFOSEL_API_KEY (JWT que entrega Infosel con el contrato)")
        if not self.env.get("INFOSEL_URL_BASE"):
            faltan.append("INFOSEL_URL_BASE (URL de producción que indique su contrato; la de pruebas es "
                          "https://hub-market-qa.infosel-digitalfactory.com)")
        if self.env.get("INFOSEL_ESPECIFICACION") and self.especificacion() is None:
            faltan.append("INFOSEL_ESPECIFICACION apunta a un archivo inexistente")
        return faltan

    def clave_instrumento(self, instrumento: dict) -> str:
        mapa = (self.especificacion() or {}).get("mapa_simbolos") or {}
        if instrumento["id"] in mapa:
            return mapa[instrumento["id"]]
        mercado = "SIC" if instrumento.get("mercado_operable") == "BMV-SIC" else "local"
        simbolo = f"{instrumento.get('clave', '')}{instrumento.get('serie') or ''}".replace(" ", "")
        return f"{self.MERCADOS_CLAVE[mercado]}/{simbolo}"

    def _consultar(self, instrumento: dict) -> Cotizacion:
        clave_inst = self.clave_instrumento(instrumento)
        url = self.env["INFOSEL_URL_BASE"].rstrip("/") + self.RUTA
        r = self.con_reintentos(lambda: self.cliente.get(
            url, params={"instrumentKey": clave_inst, "fields": self.CAMPOS},
            headers={"Authorization": f"Bearer {self.env['INFOSEL_API_KEY']}"}))
        if r.status_code in (401, 403):
            raise ProveedorNoDisponible(f"{self.nombre}: token rechazado (HTTP {r.status_code}); pida uno nuevo a Infosel")
        if r.status_code != 200:
            raise ProveedorNoDisponible(f"{self.nombre}: HTTP {r.status_code}")
        recepcion = ahora_iso()
        datos = [d for d in (r.json().get("data") or []) if d]
        simbolo = clave_inst.split("/", 3)[-1].replace(" ", "")
        d = next((x for x in datos if str(x.get("uniqueKey", "")).replace(" ", "") == clave_inst.replace(" ", "")
                  or f"{x.get('emisora', '')}{x.get('serie', '')}".replace(" ", "") == simbolo), None)  # serie exacta
        if not d or d.get("precioActual") in (None, 0):
            raise ProveedorNoDisponible(f"{self.nombre}: sin último hecho para {clave_inst}")
        if not d.get("fechaPrecioActual") or not d.get("hora"):
            raise ProveedorNoDisponible(f"{self.nombre}: la respuesta no trae fecha y hora del hecho")
        hora = pd.Timestamp(pd.to_datetime(f"{d['fechaPrecioActual']} {d['hora']}", format="%d-%m-%Y %H:%M:%S"),
                            tz="America/Mexico_City").tz_convert("UTC").isoformat()
        mercado = "SIC" if clave_inst.startswith(self.MERCADOS_CLAVE["SIC"]) else "local"
        detalle = ""
        if d.get("posturaPrecioCompra") and d.get("posturaPrecioVenta"):
            detalle = f"Posturas: compra {d['posturaPrecioCompra']} / venta {d['posturaPrecioVenta']}"
        return Cotizacion(self.nombre, str(d.get("uniqueKey") or clave_inst), instrumento["id"], instrumento["id"], mercado,
                          "BMV", float(d["precioActual"]), "MXN", hora, recepcion, None,
                          clasificar_latencia(hora, recepcion), detalle=detalle)


class EdimexProvider(ConectorContratado):
    """Edimex / EDI Financial (Economatica). Su sitio es de consulta; no publica una API abierta. Solo con un acceso
    programático contratado (API o archivo de entrega) y su documentación; mientras tanto, sus exportaciones se importan
    como CSV de precios con la columna «fuente»."""
    nombre = "edimex"
    descripcion = "Edimex / EDI Financial — solo con acceso programático contratado"
    prefijo = "EDIMEX"
    entrega_mercado = ("local", "SIC", "fondo")
    requisito_contrato = ("Contrato con Edimex / EDI Financial que incluya acceso programático (API o archivo de entrega) y "
                          "su documentación; sin él, importe sus exportaciones como CSV de precios (fuente=Edimex)")


class LsegProvider(ConectorContratado):
    nombre = "lseg"
    descripcion = "LSEG (Refinitiv) — solo con acceso contratado y documentación verificable"
    prefijo = "LSEG"
    entrega_mercado = ("local", "SIC")
    requisito_contrato = "Suscripción LSEG con derechos de la bolsa mexicana (BMV) y documentación de la API contratada"


class IceProvider(ConectorContratado):
    nombre = "ice"
    descripcion = "ICE Data Services — solo con acceso contratado y documentación verificable"
    prefijo = "ICE"
    entrega_mercado = ("local", "SIC")
    requisito_contrato = "Contrato ICE con cobertura de la BMV y documentación de la API contratada"


# ----------------------------------------------------------------------------------------------------------------
class ForeignMarketLicensedProvider(ConectorContratado):
    """Cotizaciones de la BOLSA DE ORIGEN (acciones, ETF y fondos extranjeros) con licencia y cobertura comprobadas.
    Nunca entrega la serie SIC en MXN: su mercado es «origen_extranjero» y su uso es de referencia e investigación."""
    nombre = "extranjero_licenciado"
    descripcion = "Proveedor contratado de la bolsa de origen (USD u otra moneda); referencia, no serie BMV"
    prefijo = "EXT"
    entrega_mercado = ("origen_extranjero",)
    requisito_contrato = ("Contrato con un proveedor de datos de la bolsa de origen (NYSE/Nasdaq/otras) que permita uso "
                          "programático personal, con su documentación")

    def _consultar(self, instrumento: dict) -> Cotizacion:
        q = super()._consultar({**instrumento, "clave": instrumento.get("listado_referencia") or instrumento.get("clave"),
                                "serie": ""})
        if q.moneda in ("MXN", ""):
            raise ProveedorNoDisponible(f"{self.nombre}: moneda {q.moneda or 'ausente'} no corresponde a la bolsa de origen")
        return Cotizacion(q.proveedor, q.simbolo_origen, f"{instrumento.get('bolsa_referencia')}:{instrumento.get('listado_referencia')}",
                          instrumento["id"], "origen_extranjero", q.bolsa, q.precio, q.moneda, q.hora_evento, q.hora_recepcion,
                          q.latencia_declarada_s, q.estado_latencia, detalle="Bolsa de origen; no es la cotización SIC en MXN")


class ManualOrCsvProvider(MarketDataProvider):
    """Precios que el participante captura o importa (CSV) y operaciones confirmadas. Siempre EOD o UNKNOWN."""
    nombre = "manual_csv"
    descripcion = "Precios y operaciones confirmadas capturados o importados por el participante"
    entrega_mercado = ("local", "SIC", "fondo")
    ttl_cache_s = 5.0

    def _consultar(self, instrumento: dict) -> Cotizacion:
        f = self.con.execute("SELECT fecha, cierre, moneda, tipo_dato, obtenido_en, event_time FROM precios "
                             "WHERE instrumento_id=? AND proveedor='archivo' ORDER BY fecha DESC LIMIT 1",
                             (instrumento["id"],)).fetchone()
        if not f:
            raise ProveedorNoDisponible(f"{self.nombre}: sin precio capturado para {instrumento['id']}")
        mercado = "SIC" if instrumento.get("mercado_operable") == "BMV-SIC" else (
            "fondo" if str(instrumento.get("clase", "")).startswith("fondo") else "local")
        return Cotizacion(self.nombre, instrumento.get("clave_operable") or instrumento["id"], instrumento["id"],
                          instrumento["id"], mercado, "BMV" if mercado != "fondo" else "Fondos Actinver", f["cierre"],
                          f["moneda"], hora_cierre(f["event_time"], f["fecha"]), _utc(f["obtenido_en"]).isoformat(), None,
                          "EOD" if f["tipo_dato"] in ("cierre", "nav") else "UNKNOWN",
                          detalle="Capturado por el participante; verifique contra el portal")


class DemoProvider(MarketDataProvider):
    """Datos FICTICIOS para desarrollo y pruebas. Nunca se usan en modo real ni se mezclan con datos de mercado."""
    nombre = "demo"
    descripcion = "Datos ficticios (demostración); jamás representan cotizaciones reales"
    sintetico = True
    entrega_mercado = ("local", "SIC", "fondo")

    def __init__(self, *a, modo_demo: bool = False, **k):
        super().__init__(*a, **k)
        self.modo_demo = modo_demo

    def pendientes(self) -> list[str]:
        return [] if self.modo_demo else ["solo disponible en modo demostración (datos ficticios)"]

    def _consultar(self, instrumento: dict) -> Cotizacion:
        f = self.con.execute("SELECT fecha, cierre, obtenido_en, moneda, event_time FROM precios WHERE instrumento_id=? AND "
                             "proveedor='demo_sintetico' ORDER BY fecha DESC LIMIT 1", (instrumento["id"],)).fetchone()
        if not f:
            raise ProveedorNoDisponible(f"{self.nombre}: sin dato ficticio para {instrumento['id']}")
        precio = f["cierre"]
        if f["moneda"] == "USD":  # el SIC ficticio se expresa en pesos con el tipo de cambio ficticio del mismo día
            fx = self.con.execute("SELECT valor FROM fx WHERE proveedor='demo_sintetico' AND fecha<=? ORDER BY fecha DESC LIMIT 1",
                                  (f["fecha"],)).fetchone()
            if not fx:
                raise ProveedorNoDisponible(f"{self.nombre}: sin tipo de cambio ficticio")
            precio = f["cierre"] * fx[0]
        mercado = normalizar_mercado(instrumento)
        return Cotizacion(self.nombre, instrumento["id"], instrumento["id"], instrumento["id"], mercado, "DEMO",
                          precio, "MXN", _utc(f["event_time"] or f["fecha"]).isoformat(), _utc(f["obtenido_en"]).isoformat(), None,
                          "UNKNOWN", sintetico=True, detalle="FICTICIO — solo demostración")


class ReferenciaOrigenProvider(MarketDataProvider):
    """Último precio de la bolsa de ORIGEN (USD) que ya guarda la terminal (Alpaca IEX en vivo, Tiingo/Alpaca EOD).
    Solo es «referencia externa» del SIC: nunca cuenta como cotización BMV en pesos."""
    nombre = "referencia_origen"
    descripcion = "Precio en la bolsa de origen (USD) — referencia, no cotización BMV"
    entrega_mercado = ()  # no entrega cotización BMV/MXN de ningún mercado

    def _consultar(self, instrumento: dict) -> Cotizacion:
        f = self.con.execute("SELECT fecha, cierre, proveedor, tipo_dato, hora_cotizacion, obtenido_en, event_time FROM precios "
                             "WHERE instrumento_id=? AND moneda='USD' AND proveedor<>'demo_sintetico' "
                             "ORDER BY fecha DESC, CASE proveedor WHEN 'alpaca_vivo' THEN 0 ELSE 1 END LIMIT 1",
                             (instrumento["id"],)).fetchone()
        if not f:
            raise ProveedorNoDisponible(f"{self.nombre}: sin precio de origen para {instrumento['id']}")
        ev = f["hora_cotizacion"] or f["event_time"] or f["fecha"]
        rec = f["obtenido_en"]
        estado = clasificar_latencia(ev, rec, es_cierre=f["tipo_dato"] == "cierre")
        return Cotizacion(f["proveedor"], instrumento.get("listado_referencia") or "",
                          f"{instrumento.get('bolsa_referencia')}:{instrumento.get('listado_referencia')}",
                          instrumento["id"], "origen_extranjero", instrumento.get("bolsa_referencia"), f["cierre"], "USD",
                          _utc(ev).isoformat(), _utc(rec).isoformat(), None, estado,
                          detalle="Bolsa de origen en USD; no es el precio del SIC en la BMV")


def hora_cierre(event_time: str | None, fecha: str) -> str:
    """Hora del evento de un cierre. Si solo hay fecha, se usa el cierre de esa sesión de la BMV (hora de la Ciudad de
    México); tomarla como medianoche UTC la movería al día anterior y la marcaría obsoleta."""
    if event_time:
        return _utc(event_time).isoformat()
    c = vigencia.cierre_de_sesion("XMEX", pd.Timestamp(fecha).date())
    return (_utc(c) if c else pd.Timestamp(f"{fecha} 23:59", tz="America/Mexico_City").tz_convert("UTC")).isoformat()


class CierreAlmacenadoProvider(MarketDataProvider):
    """Último cierre (o NAV) que ya guardó un adaptador de descarga. Siempre EOD: nunca se presenta como tiempo real.
    La cobertura se verifica al descargar la serie exacta (ver ingesta.registrar_cobertura)."""
    fuente = ""
    mercado = "local"
    bolsa = "BMV"
    variable = ""
    requisito = ""

    def pendientes(self) -> list[str]:
        return [] if (not self.variable or self.env.get(self.variable)) else [self.requisito]

    def simbolo(self, instrumento: dict) -> str:
        return instrumento.get("clave_operable") or instrumento["id"]

    def _consultar(self, instrumento: dict) -> Cotizacion:
        f = self.con.execute("SELECT fecha, cierre, moneda, obtenido_en, event_time FROM precios WHERE instrumento_id=? "
                             "AND proveedor=? ORDER BY fecha DESC LIMIT 1", (instrumento["id"], self.fuente)).fetchone()
        if not f:
            raise ProveedorNoDisponible(f"{self.nombre}: sin cierre descargado para {instrumento['id']}")
        return Cotizacion(self.nombre, self.simbolo(instrumento), instrumento["id"], instrumento["id"], self.mercado,
                          self.bolsa, f["cierre"], f["moneda"], hora_cierre(f["event_time"], f["fecha"]),
                          _utc(f["obtenido_en"]).isoformat(), None, "EOD")


class EodhdBmvProvider(CierreAlmacenadoProvider):
    """Cierres diarios de la BMV (MXN) que ya descarga el adaptador EODHD. Siempre EOD."""
    nombre = "eodhd_bmv"
    descripcion = "Cierre diario de la BMV en MXN (EODHD); requiere EODHD_API_KEY"
    entrega_mercado = ("local",)
    fuente, variable = "eodhd", "EODHD_API_KEY"
    requisito = "credencial EODHD_API_KEY (plan gratuito: 20 peticiones/día)"

    def simbolo(self, instrumento: dict) -> str:
        return (instrumento.get("clave", "") + (instrumento.get("serie") or "").replace("*", "").replace(" ", "")) + ".MX"


class TwelveDataBmvProvider(CierreAlmacenadoProvider):
    """Cierres diarios de la BMV (XMEX) descargados de Twelve Data; plan Pro. Siempre EOD."""
    nombre = "twelvedata_bmv"
    descripcion = "Cierre diario de la BMV en MXN (Twelve Data, plan Pro); requiere TWELVEDATA_API_KEY"
    entrega_mercado = ("local",)
    fuente, variable = "twelvedata", "TWELVEDATA_API_KEY"
    requisito = "credencial TWELVEDATA_API_KEY de un plan Pro o superior (la BMV no está en planes menores)"


class ActinverPdfProvider(CierreAlmacenadoProvider):
    """Valor por unidad de los fondos Actinver tomado de su hoja oficial «Reporte Diario» (PDF). EOD (NAV)."""
    nombre = "actinver_pdf"
    descripcion = "Precio (NAV) de fondos Actinver de la hoja oficial de precios y rendimientos"
    entrega_mercado = ("fondo",)
    fuente, mercado, bolsa = "actinver_pdf", "fondo", "Fondos Actinver"


# ----------------------------------------------------------------------------------------------------------------
def construir(con: sqlite3.Connection, modo_demo: bool, entorno: dict | None = None) -> dict[str, MarketDataProvider]:
    env = entorno if entorno is not None else os.environ
    ps = [BmvLicensedProvider(con, env), InfoselProvider(con, env), LsegProvider(con, env), EdimexProvider(con, env), IceProvider(con, env), EodhdDiferidoProvider(con, env),
          EodhdBmvProvider(con, env),
          TwelveDataBmvProvider(con, env), ActinverPdfProvider(con, env),
          ManualOrCsvProvider(con, env), DemoProvider(con, env, modo_demo=modo_demo), ReferenciaOrigenProvider(con, env),
          ForeignMarketLicensedProvider(con, env)]
    return {p.nombre: p for p in ps}


PRIORIDAD = ["bmv_licenciado", "infosel", "lseg", "ice", "edimex", "eodhd_diferido", "eodhd_bmv", "twelvedata_bmv", "actinver_pdf",
             "manual_csv"]
VIGENCIA_S = {"REAL_TIME": 120, "DELAYED": 30 * 60}


def registrar(con: sqlite3.Connection, q: Cotizacion) -> None:
    con.execute("INSERT INTO cotizaciones_registro (proveedor, simbolo_origen, simbolo_normalizado, instrumento_id, mercado, "
                "bolsa, precio, moneda, hora_evento, hora_recepcion, latencia_declarada_s, latencia_medida_s, estado_latencia, "
                "sintetico, detalle) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (q.proveedor, q.simbolo_origen, q.simbolo_normalizado, q.instrumento_id, q.mercado, q.bolsa, q.precio,
                 q.moneda, q.hora_evento, q.hora_recepcion, q.latencia_declarada_s, q.latencia_medida_s,
                 q.estado_latencia, int(q.sintetico), q.detalle[:300]))


def es_obsoleta(q: Cotizacion, instrumento: dict, ahora: datetime | None = None) -> bool:
    ahora_ts = _utc(ahora or datetime.now(UTC))
    edad = (ahora_ts - _utc(q.hora_evento)).total_seconds()
    cal = "XMEX"
    if q.estado_latencia in VIGENCIA_S and vigencia.mercado_abierto(cal, ahora):
        return edad > VIGENCIA_S[q.estado_latencia]
    # EOD, UNKNOWN o mercado cerrado: vale si corresponde a la última sesión cerrada de la BMV
    ultima = vigencia.ultima_sesion_cerrada(cal, ahora)
    if q.mercado == "fondo":  # los fondos publican el valor por unidad con un día de desfase (T+1)
        ultima = vigencia.calendario(cal).previous_session(pd.Timestamp(ultima)).date()
    return _utc(q.hora_evento).tz_convert("America/Mexico_City").date() < ultima


CALIDADES = ("REAL_TIME", "DELAYED", "EOD", "STALE", "UNKNOWN")


def calidad_actual(q: dict | Cotizacion, ahora: datetime | None = None) -> str:
    """REAL_TIME / DELAYED / EOD / UNKNOWN según la latencia medida al recibirla; STALE si ya no es vigente ahora."""
    if isinstance(q, dict):
        q = Cotizacion(**{k: q[k] for k in Cotizacion.__dataclass_fields__})
    return "STALE" if es_obsoleta(q, {}, ahora) else q.estado_latencia


def cobertura_verificada(con: sqlite3.Connection, proveedor: str, instrumento_id: str) -> dict | None:
    f = con.execute("SELECT * FROM cobertura WHERE proveedor=? AND instrumento_id=? AND estado='verificado'",
                    (proveedor, instrumento_id)).fetchone()
    return dict(f) if f else None


def precio_confiable(con: sqlite3.Connection, proveedores: dict[str, MarketDataProvider], instrumento: dict,
                     ahora: datetime | None = None, prioridad: list[str] | None = None) -> dict:
    """Cotización BMV en pesos de un instrumento del simulador, o «SIN PRECIO CONFIABLE» con el motivo.
    Recorre los proveedores en orden y SOLO acepta uno con cobertura verificada de ese instrumento exacto."""
    motivos, cat = [], normalizar_mercado(instrumento)
    for nombre in prioridad or PRIORIDAD:
        p = proveedores.get(nombre)
        if p is None:
            continue
        if not p.configurado():
            motivos.append(f"{nombre}: pendiente ({'; '.join(p.pendientes())[:160]})")
            continue
        cob = cobertura_verificada(con, nombre, instrumento["id"])
        if not cob and nombre not in ("manual_csv", "demo"):  # lo capturado por el usuario y lo ficticio no se «verifican»
            motivos.append(f"{nombre}: cobertura de {instrumento['id']} no verificada")
            continue
        try:
            q = p.cotizacion(instrumento)
        except ProveedorNoDisponible as e:
            motivos.append(str(e))
            continue
        if q.mercado != cat or q.moneda != (instrumento.get("moneda_operable") or "MXN"):
            motivos.append(f"{nombre}: entregó {q.mercado}/{q.moneda}, se esperaba {cat}/{instrumento.get('moneda_operable')}")
            continue
        if es_obsoleta(q, instrumento, ahora):
            motivos.append(f"{nombre}: dato obsoleto ({q.hora_evento})")
            continue
        return {"estado": "confiable", "cotizacion": q.a_dict(), "calidad": calidad_actual(q, ahora), "motivos": motivos}
    return {"estado": SIN_PRECIO, "cotizacion": None, "calidad": SIN_PRECIO, "motivos": motivos}


def normalizar_mercado(instrumento: dict) -> str:
    if instrumento.get("mercado_operable") == "BMV-SIC":
        return "SIC"
    return "fondo" if str(instrumento.get("clase", "")).startswith("fondo") else "local"


# ----------------------------------------------------------------------------------------------------------------
def verificar_cobertura(con: sqlite3.Connection, proveedores: dict[str, MarketDataProvider], instrumentos: list[dict],
                        nombres: list[str] | None = None) -> list[dict]:
    """Comprueba por consulta real que cada proveedor entrega el instrumento EXACTO (moneda y mercado) y mide latencia.
    Sin configuración queda «pendiente»; con error, «no_cubierto»; si coincide, «verificado». Nada se da por cubierto
    por la descripción general del proveedor."""
    out = []
    ts = ahora_iso()
    for nombre in nombres or PRIORIDAD:
        p = proveedores[nombre]
        pend = p.pendientes()
        for ins in instrumentos:
            fila = {"proveedor": nombre, "instrumento_id": ins["id"], "simbolo_origen": None, "moneda_observada": None,
                    "bolsa_observada": None, "mercado_observado": None, "latencia_mediana_s": None, "estado_latencia": None}
            esperado = normalizar_mercado(ins)
            if pend:
                fila.update(estado="pendiente", detalle="; ".join(pend)[:300])
            elif esperado not in p.entrega_mercado:
                fila.update(estado="no_aplica", detalle=f"el proveedor no entrega el mercado {esperado}")
            else:
                try:
                    q = p.cotizacion(ins)
                    ok = q.moneda == (ins.get("moneda_operable") or "MXN") and q.mercado == esperado
                    fila.update(simbolo_origen=q.simbolo_origen, moneda_observada=q.moneda, bolsa_observada=q.bolsa,
                                mercado_observado=q.mercado, latencia_mediana_s=q.latencia_medida_s,
                                estado_latencia=q.estado_latencia, estado="verificado" if ok else "no_coincide",
                                detalle="" if ok else f"esperado {esperado}/{ins.get('moneda_operable')}")
                    if ok:  # la base rechaza (disparador) registrar una serie BMV/SIC que no venga en MXN
                        registrar(con, q)
                except ProveedorNoDisponible as e:
                    fila.update(estado="no_cubierto", detalle=str(e)[:300])
            con.execute("INSERT OR REPLACE INTO cobertura (proveedor, instrumento_id, simbolo_origen, estado, moneda_observada, "
                        "bolsa_observada, mercado_observado, latencia_mediana_s, estado_latencia, detalle, verificado_en) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (fila["proveedor"], fila["instrumento_id"], fila["simbolo_origen"], fila["estado"],
                         fila["moneda_observada"], fila["bolsa_observada"], fila["mercado_observado"],
                         fila["latencia_mediana_s"], fila["estado_latencia"], fila["detalle"], ts))
            out.append(fila)
    con.commit()
    return out


def latencias_medidas(con: sqlite3.Connection) -> list[dict]:
    """Latencia medida por proveedor (mediana y p90) con las cotizaciones registradas."""
    df = pd.read_sql_query("SELECT proveedor, estado_latencia, latencia_medida_s FROM cotizaciones_registro "
                           "WHERE latencia_medida_s IS NOT NULL", con)
    if df.empty:
        return []
    g = df.groupby("proveedor")["latencia_medida_s"]
    return [{"proveedor": k, "n": int(v.size), "mediana_s": round(float(v.median()), 2),
             "p90_s": round(float(v.quantile(0.9)), 2),
             "estados": df[df.proveedor == k]["estado_latencia"].value_counts().to_dict()} for k, v in g]


def tabla_cobertura(con: sqlite3.Connection, proveedores: dict[str, MarketDataProvider]) -> list[dict]:
    ver = {(r["proveedor"], r["instrumento_id"]): dict(r) for r in con.execute("SELECT * FROM cobertura")}
    filas = []
    for ins in catalogo(con):
        fila = {"instrumento_id": ins["id"], "clave_operable": ins["clave_operable"], "serie": ins["serie"],
                "mercado": ins["mercado"], "moneda": ins["moneda_operable"], "en_catalogo_simulador": ins["en_catalogo_simulador"]}
        for n in PRIORIDAD:
            v = ver.get((n, ins["id"]))
            fila[n] = v["estado"] if v else ("pendiente" if proveedores[n].pendientes() else "sin_verificar")
        filas.append(fila)
    return filas


def a_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


__all__ = ["MarketDataProvider", "BmvLicensedProvider", "InfoselProvider", "EdimexProvider", "LsegProvider", "IceProvider", "ManualOrCsvProvider",
           "DemoProvider", "ReferenciaOrigenProvider", "EodhdBmvProvider", "TwelveDataBmvProvider", "ActinverPdfProvider", "Cotizacion", "SIN_PRECIO", "ProveedorNoDisponible",
           "normalizar_simbolo", "precio_confiable", "verificar_cobertura", "clasificar_latencia", "construir"]
