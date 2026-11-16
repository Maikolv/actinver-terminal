"""Portafolio principal: el portafolio de «Mis portafolios» que el usuario elige como objetivo de su cartera real.

Cuando hay uno elegido, el plan de acción y su seguimiento comparan la cartera registrada contra SUS pesos (no contra la
propuesta automática del motor). Solo informa y simula: no envía órdenes.
"""
from __future__ import annotations

import json
import sqlite3

from . import db

CLAVE = "portafolio_principal"


def obtener_id(con: sqlite3.Connection) -> int | None:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave=?", (CLAVE,)).fetchone()
    if not f:
        return None
    try:
        pid = int(json.loads(f[0]).get("id"))
    except (ValueError, TypeError, AttributeError):
        return None
    existe = con.execute("SELECT 1 FROM portafolios_usuario WHERE id=?", (pid,)).fetchone()
    return pid if existe else None


def elegir(con: sqlite3.Connection, pid: int | None) -> int | None:
    """Fija (o quita, con None) el portafolio principal."""
    with db.transaccion(con):
        if pid is None:
            con.execute("DELETE FROM ajustes_usuario WHERE clave=?", (CLAVE,))
            return None
        if not con.execute("SELECT 1 FROM portafolios_usuario WHERE id=?", (pid,)).fetchone():
            raise KeyError(pid)
        con.execute("INSERT INTO ajustes_usuario (clave, valor, actualizado_en) VALUES (?,?,?) "
                    "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, actualizado_en=excluded.actualizado_en",
                    (CLAVE, json.dumps({"id": pid}), db.ahora()))
    return pid


def propuesta(con: sqlite3.Connection, cartera: dict, banda_pp: float = 2.0) -> dict | None:
    """Propuesta de referencia con el formato que usa el plan, a partir del portafolio principal y la cartera real."""
    pid = obtener_id(con)
    if pid is None:
        return None
    r = con.execute("SELECT nombre, resultado FROM portafolios_usuario WHERE id=?", (pid,)).fetchone()
    res = json.loads(r["resultado"]) if r and r["resultado"] else None
    if not res:
        return None
    pesos = [{"id": a["id"], "peso": float(a["peso"]), "clave_operable": a.get("clave")}
             for a in res.get("activos") or [] if float(a.get("peso") or 0) >= 0.005]
    total = sum(p["peso"] for p in pesos) or 1.0
    for p in pesos:
        p["peso"] = p["peso"] / total
    valor = float(cartera.get("valor_total") or 0)
    actuales = {x["instrumento_id"]: x for x in cartera.get("posiciones") or [] if (x.get("cantidad") or 0) > 0}
    objetivo = {p["id"]: p for p in pesos}
    filas = []
    for iid in sorted(set(objetivo) | set(actuales)):
        actual = float((actuales.get(iid) or {}).get("peso") or 0)
        meta = float((objetivo.get(iid) or {}).get("peso") or 0)
        delta = (meta - actual) * 100
        accion = "mantener" if abs(delta) < banda_pp else ("comprar" if delta > 0 else "vender")
        filas.append({"id": iid, "clave_operable": (objetivo.get(iid) or {}).get("clave_operable")
                      or (actuales.get(iid) or {}).get("clave_operable") or iid,
                      "peso_actual": actual, "peso_objetivo": meta, "delta_pp": round(delta, 2),
                      "monto_mxn": round((meta - actual) * valor, 2), "accion": accion,
                      "nota": "" if accion != "vender" or meta else f"No está en «{r['nombre']}»: salir de la posición."})
    return {"nombre": r["nombre"], "origen": "mis_portafolios", "portafolio_id": pid, "pesos": pesos,
            "cambios": {"filas": filas}, "perfil": {}, "metricas": res.get("metricas"),
            "calculado_en": res.get("calculado_en")}
