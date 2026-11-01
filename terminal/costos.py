"""Servicios que podrían cobrar: catálogo, estado y aprobación del usuario.

Regla: ningún servicio que cobre se usa sin aprobación expresa. Si la terminal detecta uno (por ejemplo, una
credencial de la API de Claude), lo deja SIN USAR, lo marca «pendiente de tu aprobación» y emite una alerta (escritorio
y Telegram, como las demás) para que el usuario apruebe o desista. La terminal nunca contrata, sube de plan ni registra
tarjetas; los proveedores de datos se usan en sus planes gratuitos.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from .alertas import Condicion

DECISIONES = ("aprobado", "desistido")

# id, nombre, cómo cobra, detector (None = solo informativo: plan gratuito sin forma de generar cargos desde aquí)
SERVICIOS = [
    {"id": "claude_api", "nombre": "API de Claude (Asistente y bot de Telegram)", "cobro": "pago por uso (tokens)",
     "nota": "Solo se usa con tu aprobación; sin ella responden Ollama o el motor local, que no cobran."},
    {"id": "alpaca", "nombre": "Alpaca (datos de EE. UU.)", "cobro": "gratis (IEX y SIP con retraso)", "nota": "Sin órdenes; solo datos."},
    {"id": "tiingo", "nombre": "Tiingo", "cobro": "gratis (plan sin costo)", "nota": "Límite diario; no sube de plan solo."},
    {"id": "eodhd", "nombre": "EODHD (cierres BMV)", "cobro": "gratis (20 consultas al día)", "nota": "El plan de pago lo contrata solo el usuario."},
    {"id": "alpha_vantage", "nombre": "Alpha Vantage", "cobro": "gratis (25 consultas al día)", "nota": ""},
    {"id": "fred_bls_eia", "nombre": "FRED, BLS y EIA", "cobro": "gratis (datos públicos)", "nota": ""},
    {"id": "banxico", "nombre": "Banxico SIE", "cobro": "gratis (token público)", "nota": ""},
    {"id": "sec_edgar", "nombre": "SEC EDGAR", "cobro": "gratis (sin clave)", "nota": ""},
    {"id": "telegram", "nombre": "Telegram", "cobro": "gratis", "nota": ""},
    {"id": "cloudflare", "nombre": "Cloudflare Workers (monitor en la nube)", "cobro": "gratis (plan Free, sin tarjeta)",
     "nota": "Al rebasar el límite gratuito el plan Free falla, no cobra."},
]


def _detectores() -> dict:
    from . import bot_telegram
    return {"claude_api": bot_telegram.credencial_claude}


def decision(con: sqlite3.Connection, servicio: str) -> str | None:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave=?", (f"costo_{servicio}",)).fetchone()
    return f[0] if f and f[0] in DECISIONES else None


def decidir(con: sqlite3.Connection, servicio: str, valor: str) -> dict:
    if servicio not in {s["id"] for s in SERVICIOS if s["id"] in _detectores()}:
        raise ValueError("servicio sin cobro que aprobar")
    if valor not in DECISIONES:
        raise ValueError("decisión inválida: aprobado o desistido")
    con.execute("INSERT OR REPLACE INTO ajustes_usuario (clave, valor, actualizado_en) VALUES (?, ?, ?)",
                (f"costo_{servicio}", valor, datetime.now(UTC).isoformat(timespec="seconds")))
    con.commit()
    return estado(con)


def estado(con: sqlite3.Connection) -> dict:
    det = _detectores()
    filas = []
    for s in SERVICIOS:
        detectado = det[s["id"]]() if s["id"] in det else None
        d = decision(con, s["id"]) if s["id"] in det else None
        if s["id"] not in det:
            e = "gratis"
        elif not detectado:
            e = "sin credencial: no se usa ni cobra"
        else:
            e = {"aprobado": "aprobado por ti: puede generar cargos", "desistido": "desistido: no se usa"}.get(d, "pendiente de tu aprobación: no se usa")
        filas.append({**s, "detectado": detectado, "decision": d, "estado": e, "requiere_decision": bool(detectado) and d is None,
                      "puede_decidir": s["id"] in det})
    return {"servicios": filas,
            "nota": "La terminal no contrata, no sube de plan y no registra tarjetas. Un servicio de pago solo se usa si "
                    "lo apruebas aquí; puedes desistir en cualquier momento."}


def reglas_costos(con: sqlite3.Connection) -> list[Condicion]:
    """Alerta mientras haya un servicio que cobra detectado y sin decisión."""
    out = []
    for f in estado(con)["servicios"]:
        if f["puede_decidir"]:
            out.append(Condicion(regla="costo", clave=f["id"], activa=f["requiere_decision"], severidad="alta",
                                 titulo=f"Servicio con costo pendiente de aprobación: {f['nombre']}",
                                 motivo=f"Se detectó {f['nombre']} ({f['cobro']}). No se usará hasta que lo apruebes.",
                                 fuente="terminal", accion="Aprueba o desiste en Datos y fuentes › Servicios con costo.",
                                 rearme=False))
    return out
