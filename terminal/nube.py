"""Sincronización con el monitor de alertas en la nube (Cloudflare Workers, `cloud-alerts/`).

La terminal sigue siendo la fuente del portafolio y de los cálculos completos. A la nube solo viaja lo mínimo para
vigilar con la PC apagada:
- posiciones y efectivo de la cartera (con su hora de conciliación);
- umbrales y el último plan con su condición por emisora;
- el calendario bursátil de las próximas sesiones, el último tipo de cambio y los splits recientes.

Nunca viajan la base SQLite, `.env`, contraseñas, costos ni documentos del portal.

Cada sincronización es también un «latido»: mientras llegue cada 10 minutos, la nube no envía alertas (las envía la
terminal local); cuando deja de llegar, la nube toma el relevo. La petición va firmada con HMAC-SHA256 (secreto
`CLOUD_ALERTS_SECRET` en `.env`), con marca de tiempo, un nonce de un solo uso y una secuencia creciente.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import UTC, date, datetime, timedelta

import httpx
import pandas as pd

from . import db, servicios, vigencia
from .config import Ajustes

log = logging.getLogger("terminal.nube")
MAX_BYTES = 60_000
SIMBOLO = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
ID = re.compile(r"^(BMV|SIC|FONDO):[A-Z0-9.&+\-]{1,24}$")
POR_OMISION = {"cada_min": 10, "movimiento_pct": 0.03, "cartera_pct": 0.02, "sync_max_horas": 26,
               "conciliacion_max_horas": 30, "local_inactivo_min": 20}


def cfg(ajustes: Ajustes) -> dict:
    return {**POR_OMISION, **(ajustes.get("nube") or {})}


def configurado() -> bool:
    return bool(os.environ.get("CLOUD_ALERTS_URL") and len(os.environ.get("CLOUD_ALERTS_SECRET") or "") >= 32)


def firmar(secreto: str, ts: str, nonce: str, metodo: str, ruta: str, cuerpo: bytes) -> str:
    """Misma firma que `cloud-alerts/src/firma.js` (vector compartido en cloud-alerts/test/vector_firma.json)."""
    canon = f"v1:{ts}:{nonce}:{metodo.upper()}:{ruta}:{hashlib.sha256(cuerpo).hexdigest()}"
    return hmac.new(secreto.encode(), canon.encode(), hashlib.sha256).hexdigest()


def _cabeceras(metodo: str, ruta: str, cuerpo: bytes) -> dict:
    ts, nonce = str(int(time.time())), secrets.token_hex(16)
    return {"X-Marca-Tiempo": ts, "X-Nonce": nonce,
            "X-Firma": firmar(os.environ["CLOUD_ALERTS_SECRET"], ts, nonce, metodo, ruta, cuerpo)}


def _iso(x) -> str | None:
    if not x:
        return None
    try:
        return pd.Timestamp(x).tz_convert("UTC").isoformat() if pd.Timestamp(x).tzinfo else pd.Timestamp(x, tz="UTC").isoformat()
    except (ValueError, TypeError):
        return None


def _simbolo(ins: dict) -> str | None:
    s = (ins or {}).get("listado_referencia")
    return s if ins and ins.get("moneda_referencia") == "USD" and s and SIMBOLO.match(s) else None


def _calendario(dias: int = 14, hoy: date | None = None) -> list[dict]:
    hoy = hoy or datetime.now(UTC).date()
    out = []
    for m in ("XMEX", "XNYS"):
        for s in vigencia.calendario(m).sessions_in_range(pd.Timestamp(hoy), pd.Timestamp(hoy + timedelta(days=dias))):
            out.append({"mercado": m, "fecha": s.date().isoformat(), "apertura": vigencia.apertura_sesion(m, s).isoformat(),
                        "cierre": vigencia.cierre_sesion(m, s).isoformat()})
    return out


def _condicion(a: dict) -> str:
    lim = a.get("precio_limite")
    inval = (a.get("invalidacion") or "").strip()
    sufijo = f" Se invalida si: {inval[:110]}" if inval else ""
    if a["decision"] == "comprar" and lim:
        return (f"Comprar {a.get('cantidad')} títulos si la referencia está en ${lim:,.2f} o menos.{sufijo}")[:240]
    if a["decision"] == "vender" and lim:
        return (f"Vender {a.get('cantidad')} títulos si la referencia está en ${lim:,.2f} o más.{sufijo}")[:240]
    if a["decision"] == "mantener":
        return f"Esperar (mantener).{sufijo}"[:240]
    falta = "; ".join(a.get("falta") or [])[:150]
    return f"Esperar: falta {falta or 'confirmar datos'} antes de operar."[:240]


def _plan(con: sqlite3.Connection, ajustes: Ajustes, cart: dict) -> dict | None:
    from . import plan_accion, resumen
    props = servicios.propuestas_guardadas(con, ajustes, servicios.perfil_actual(con, ajustes))
    ref = resumen.propuesta_referencia(props)
    if not ref:
        return None
    p = plan_accion.calcular(con, ajustes, propuesta=ref, cartera=cart)
    ins = {r["id"]: dict(r) for r in con.execute("SELECT id, listado_referencia, moneda_referencia FROM instrumentos")}
    opciones = []
    for a in sorted(p["acciones"], key=lambda x: x["prioridad"])[:12]:
        if not ID.match(a["instrumento_id"]):
            continue
        lim = a.get("precio_limite")
        pr = a.get("precio") or {}
        opciones.append({
            "id": a["instrumento_id"], "clave": str(a.get("clave") or "")[:32], "simbolo_eeuu": _simbolo(ins.get(a["instrumento_id"])),
            "accion": a["decision"] if a["decision"] in ("comprar", "vender", "mantener") else "pendiente",
            "titulos": a.get("cantidad"), "precio_ref": lim or pr.get("precio_mxn"),
            "fuente_precio": (str(pr.get("fuente")) if pr.get("fuente") else None),
            "fecha_precio": (str(pr.get("hora") or pr.get("fecha"))[:40] if (pr.get("hora") or pr.get("fecha")) else None),
            "limite_compra": lim if a["decision"] == "comprar" else None,
            "limite_venta": lim if a["decision"] == "vender" else None, "condicion": _condicion(a)})
    validado = p["cuenta"]["confirmada"] and not p["reglas"].get("errores") and not p["faltan"]
    otras = sorted([x for x in resumen._vigentes(props) if x is not ref], key=lambda x: -x["puntuacion"]["total"])[:3]
    return {"calculado_en": p["generado_en"], "nombre": ref["nombre"][:120], "puntuacion": float(ref["puntuacion"]["total"]),
            "vigente": True, "validado": bool(validado),
            "motivo_no_validado": (None if validado else "; ".join(p["faltan"] or p["reglas"].get("errores") or ["sin confirmar"])[:240]),
            "opciones": opciones,
            "alternativas": [{"nombre": x["nombre"][:120], "puntuacion": float(x["puntuacion"]["total"])} for x in otras]}


def construir_carga(con: sqlite3.Connection, ajustes: Ajustes, prueba: bool = False, plan: bool = True) -> dict:
    c = cfg(ajustes)
    cart = servicios.cartera_actual(con, ajustes)
    ins = {r["id"]: dict(r) for r in con.execute("SELECT id, listado_referencia, moneda_referencia FROM instrumentos")}
    posiciones = []
    for p in cart.get("posiciones") or []:
        iid = p["instrumento_id"]
        if not ID.match(iid) or not (p.get("cantidad") or 0) > 0:
            continue
        precio = p.get("precio_mxn") or ((p["valor_mxn"] / p["cantidad"]) if p.get("valor_mxn") else None)
        posiciones.append({"id": iid, "clave": str(p.get("clave_operable") or iid)[:32], "simbolo_eeuu": _simbolo(ins.get(iid)),
                           "titulos": float(p["cantidad"]), "precio_ref": round(float(precio), 6) if precio else None, "moneda_ref": "MXN",
                           "fecha_precio": (str(p.get("fecha_precio"))[:10] if p.get("fecha_precio") else None),
                           "fuente_precio": (str(p.get("proveedor"))[:40] if p.get("proveedor") else None),
                           "tipo_precio": (str(p.get("tipo_dato"))[:30] if p.get("tipo_dato") else None)})
    ids = {p["id"] for p in posiciones}
    plan_d = None
    if plan:
        try:
            plan_d = _plan(con, ajustes, cart)
        except Exception:  # noqa: BLE001 - sin plan, la nube suspende sus condiciones y lo explica
            log.exception("no se pudo preparar el plan para la nube")
        ids |= {o["id"] for o in (plan_d or {}).get("opciones", [])}
    fx = con.execute("SELECT fecha, valor, proveedor FROM fx WHERE par='USDMXN' AND proveedor <> 'demo_sintetico' "
                     "ORDER BY fecha DESC, CASE proveedor WHEN 'banxico' THEN 0 ELSE 1 END LIMIT 1").fetchone()
    desde = (datetime.now(UTC).date() - timedelta(days=60)).isoformat()
    splits = [{"id": r[0], "fecha": r[1], "factor": float(r[2])} for r in con.execute(
        "SELECT DISTINCT instrumento_id, fecha, valor FROM eventos_corporativos WHERE tipo='split' AND fecha >= ? ORDER BY fecha", (desde,))
        if r[0] in ids and ID.match(r[0])][:40]
    captura = cart.get("captura") or {}
    carga = {
        "version": 1, "secuencia": _secuencia(con), "generado_en": datetime.now(UTC).isoformat(timespec="seconds"),
        "cartera": {"fuente": "portal" if cart.get("fuente") == "portal" else "local",
                    "hora_conciliacion": _iso(captura.get("hora_portal")) if cart.get("fuente") == "portal" else None,
                    "efectivo": round(float(cart.get("efectivo") or 0), 2), "por_liquidar": round(float(cart.get("por_liquidar") or 0), 2),
                    "valor_total": round(max(float(cart.get("valor_total") or 0), 0.0), 2), "posiciones": posiciones[:80]},
        "umbrales": {k: c[k] for k in ("movimiento_pct", "cartera_pct", "sync_max_horas", "conciliacion_max_horas", "local_inactivo_min")},
        "plan": plan_d, "calendario": _calendario(),
        "fx": ({"valor": round(float(fx[1]), 6), "fecha": fx[0], "fuente": str(fx[2])[:20]} if fx else None),
        "splits": splits,
    }
    if prueba:
        carga["prueba"] = True
    return carga


def _secuencia(con: sqlite3.Connection) -> int:
    """Creciente aunque el reloj retroceda: max(ahora en ms, última + 1)."""
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='nube'").fetchone()
    ultima = (json.loads(f[0]).get("secuencia") or 0) if f else 0
    return max(int(time.time() * 1000), int(ultima) + 1)


def _registrar(con: sqlite3.Connection, datos: dict) -> None:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='nube'").fetchone()
    previo = json.loads(f[0]) if f else {}
    with db.transaccion(con):
        con.execute("INSERT INTO ajustes_usuario VALUES ('nube', ?, ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, "
                    "actualizado_en=excluded.actualizado_en", (json.dumps({**previo, **datos}), db.ahora()))


def sincronizar(con: sqlite3.Connection, ajustes: Ajustes, prueba: bool = False, cliente: httpx.Client | None = None) -> dict:
    """Envía la carga mínima firmada. Devuelve {ok, ...}; nunca incluye el secreto ni la URL completa en el registro."""
    if not configurado():
        return {"ok": False, "error": "no_configurado"}
    carga = construir_carga(con, ajustes, prueba=prueba)
    cuerpo = json.dumps(carga, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(cuerpo) > MAX_BYTES:
        return {"ok": False, "error": f"carga de {len(cuerpo)} bytes: excede {MAX_BYTES}"}
    url = os.environ["CLOUD_ALERTS_URL"].rstrip("/") + "/sync"
    try:
        cli = cliente or httpx.Client(timeout=15)
        r = cli.post(url, content=cuerpo, headers={"Content-Type": "application/json", **_cabeceras("POST", "/sync", cuerpo)})
        res = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"ok": False}
        ok = r.status_code == 200 and res.get("ok")
        estado = {"ultimo_intento": db.ahora(), "ultimo_estado": "ok" if ok else f"http_{r.status_code}",
                  "ultimo_error": None if ok else str(res.get("error") or res.get("motivo") or "")[:120]}
        if ok:
            estado.update(ultima_sincronizacion=res.get("recibido_en"), secuencia=carga["secuencia"], bytes=len(cuerpo),
                          posiciones=len(carga["cartera"]["posiciones"]), plan=bool(carga["plan"]))
        _registrar(con, estado)
        return {"ok": bool(ok), "status": r.status_code, **{k: res.get(k) for k in ("error", "motivo", "recibido_en", "proxima_revision")},
                "bytes": len(cuerpo)}
    except httpx.HTTPError as e:
        _registrar(con, {"ultimo_intento": db.ahora(), "ultimo_estado": "sin_conexion", "ultimo_error": type(e).__name__})
        return {"ok": False, "error": "sin_conexion"}


def estado_remoto(cliente: httpx.Client | None = None) -> dict:
    if not configurado():
        return {"ok": False, "error": "no_configurado"}
    url = os.environ["CLOUD_ALERTS_URL"].rstrip("/") + "/estado"
    try:
        cli = cliente or httpx.Client(timeout=10)
        r = cli.get(url, headers=_cabeceras("GET", "/estado", b""))
        return r.json() if r.status_code == 200 else {"ok": False, "error": f"http_{r.status_code}"}
    except (httpx.HTTPError, ValueError) as e:
        return {"ok": False, "error": type(e).__name__}


def _hora(iso: str | None) -> str | None:
    if not iso:
        return None
    return pd.Timestamp(iso).tz_convert("America/Mexico_City").strftime("%d-%m-%Y %H:%M")


def estado(con: sqlite3.Connection, ajustes: Ajustes, remoto: dict | None = None) -> dict:
    """Estado comprensible para la terminal: activo o inactivo, última sincronización y ejecución, próxima revisión y
    motivos de las alertas suspendidas."""
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='nube'").fetchone()
    local = json.loads(f[0]) if f else {}
    if not configurado():
        return {"configurado": False, "activo": False, "local": local,
                "mensaje": "Monitor en la nube no configurado: vea cloud-alerts/README.md (CLOUD_ALERTS_URL y CLOUD_ALERTS_SECRET en .env)."}
    r = remoto if remoto is not None else estado_remoto()
    if not r.get("ok"):
        return {"configurado": True, "activo": False, "local": local, "error": r.get("error"),
                "mensaje": f"No se pudo consultar el monitor en la nube ({r.get('error')})."}
    ult = r.get("ultima_ejecucion") or {}
    edad_min = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(ult["inicio"])).total_seconds() / 60 if ult.get("inicio") else None
    # Activo: el disparador corre cada 15 min de 12 a 21 h UTC en días hábiles; fuera de esa ventana basta la última ejecución
    activo = bool(ult.get("inicio")) and (edad_min is not None and (edad_min <= 40 or not _en_ventana()))
    relevo = ult.get("relevo")
    return {
        "configurado": True, "activo": activo, "ultima_sincronizacion": _hora(r.get("ultima_sincronizacion")),
        "ultima_ejecucion": _hora(ult.get("inicio")), "proxima_revision": _hora(r.get("proxima_revision")),
        "relevo": relevo, "relevo_texto": {"local": "la terminal local envía las alertas (la nube en pausa)",
                                           "nube": "la nube envía las alertas (la terminal no sincroniza)",
                                           "sin_datos": "sin datos sincronizados"}.get(relevo, "—"),
        "suspendidas": r.get("suspendidas") or [], "telegram_configurado": r.get("telegram_configurado"),
        "fuentes_configuradas": r.get("fuentes_configuradas"), "fx": ult.get("fx"), "proveedores": ult.get("proveedores"),
        "avisos_recientes": [{k: a.get(k) for k in ("tipo", "estado", "creado_en", "enviado_en")} for a in r.get("avisos_recientes") or []],
        "local": local,
        "mensaje": ("Monitor en la nube activo." if activo else
                    "El monitor en la nube no se ha ejecutado recientemente en su horario: revise el despliegue."),
    }


def _en_ventana(ahora: datetime | None = None) -> bool:
    t = ahora or datetime.now(UTC)
    return t.weekday() < 5 and 12 <= t.hour <= 21


class Sincronizador:
    """Hilo ligero: sincroniza cada `cada_min` minutos mientras la terminal esté encendida (latido para el relevo)."""

    def __init__(self, ajustes: Ajustes):
        self.ajustes = ajustes
        self._stop = threading.Event()

    def iniciar(self) -> None:
        if configurado() and cfg(self.ajustes).get("activo", True):
            threading.Thread(target=self._bucle, daemon=True, name="nube").start()

    def detener(self) -> None:
        self._stop.set()

    def _bucle(self) -> None:
        while not self._stop.is_set():
            con = db.conectar()
            try:
                r = sincronizar(con, self.ajustes)
                if not r.get("ok"):
                    log.warning("sincronización con la nube: %s", r.get("error"))
            except Exception:  # noqa: BLE001 - la nube nunca detiene la terminal
                log.exception("sincronización con la nube falló")
            finally:
                con.close()
            self._stop.wait(max(5, int(cfg(self.ajustes)["cada_min"])) * 60)
