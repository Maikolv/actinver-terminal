"""Auditoría local y cuarentena reversible de cierres recibidos antes de su evento registrado."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

PROVEEDORES = ("tiingo", "alpaca", "eodhd", "barchart", "twelvedata")
CRITERIO = """tipo_dato='cierre' AND proveedor IN (?,?,?,?,?)
              AND julianday(obtenido_en)<julianday(event_time)"""


def auditar(con: sqlite3.Connection) -> dict:
    """Solo cuenta candidatos temporales; no certifica publicación, precio o integridad total."""
    filas = con.execute("SELECT proveedor,COUNT(*) FROM precios WHERE " + CRITERIO +
                        " GROUP BY proveedor ORDER BY proveedor", PROVEEDORES).fetchall()
    sin_marcas = con.execute(
        "SELECT COUNT(*) FROM precios WHERE tipo_dato='cierre' AND proveedor IN (?,?,?,?,?) "
        "AND (julianday(obtenido_en) IS NULL OR julianday(event_time) IS NULL)", PROVEEDORES).fetchone()[0]
    return {"candidatos": sum(f[1] for f in filas), "por_proveedor": {f[0]: f[1] for f in filas},
            "sin_marcas_evaluables": sin_marcas}


def poner_en_cuarentena(con: sqlite3.Connection, esperados: int, ahora: datetime | None = None) -> dict:
    """Conserva la fila completa antes de retirarla; ninguna orden o tabla de operaciones se toca."""
    if con.in_transaction:
        raise ValueError("La cuarentena requiere una conexión sin transacción pendiente.")
    if not isinstance(esperados, int) or isinstance(esperados, bool) or esperados < 0:
        raise ValueError("Indique el número de candidatos revisados.")
    marca = (ahora or datetime.now(UTC)).isoformat()
    cambios_previos = con.total_changes
    con.execute("BEGIN IMMEDIATE")
    try:
        cursor = con.execute("SELECT * FROM precios WHERE " + CRITERIO, PROVEEDORES)
        columnas = [c[0] for c in cursor.description]
        originales = [dict(zip(columnas, f)) for f in cursor.fetchall()]
        if len(originales) != esperados:
            raise ValueError("Cambió el conjunto de candidatos; vuelva a revisar antes de aplicarlo.")
        con.execute("CREATE TABLE IF NOT EXISTS precios_cuarentena ("
                    "huella TEXT PRIMARY KEY, motivo TEXT NOT NULL, detectado_en TEXT NOT NULL, "
                    "datos_originales TEXT NOT NULL)")
        insertados = retirados = 0
        for fila in originales:
            texto = json.dumps(fila, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()
            insertados += con.execute("INSERT OR IGNORE INTO precios_cuarentena VALUES (?,?,?,?)",
                                      (huella, "recibido_antes_del_evento_registrado", marca, texto)).rowcount
            eliminados = con.execute("DELETE FROM precios WHERE instrumento_id=? AND fecha=? AND proveedor=? "
                                     "AND obtenido_en=? AND event_time=?",
                                     (fila["instrumento_id"], fila["fecha"], fila["proveedor"],
                                      fila["obtenido_en"], fila["event_time"])).rowcount
            if eliminados != 1:
                raise RuntimeError("La fila cambió durante la cuarentena; se conserva el estado previo.")
            retirados += eliminados
        if con.total_changes - cambios_previos != insertados + retirados:
            raise RuntimeError("Se detectaron escrituras adicionales; se revierte la cuarentena.")
        con.commit()
        return {"retirados_de_precios": retirados, "archivados_nuevos": insertados,
                "criterio": "cierre recibido antes de su evento registrado; sin certificar precio/publicación"}
    except Exception:
        con.rollback()
        raise
