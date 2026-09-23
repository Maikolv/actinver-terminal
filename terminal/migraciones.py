"""Migraciones versionadas y marcas temporales `event_time` / `available_at`.

- `event_time`: cuándo ocurrió el hecho (cierre de la sesión, hora de la operación, publicación).
- `available_at`: cuándo pudo conocerlo el modelo. Una predicción emitida a la hora T solo usa filas con
  `available_at <= T`.

Reglas de disponibilidad (UTC, conservadoras y documentadas en docs/investigacion.md):
- Cierres diarios: cierre oficial de la sesión + retraso de publicación del proveedor ([disponibilidad] en ajustes).
- Cotización en vivo o recibida por webhook: la hora de recepción registrada.
- Importado por el usuario (CSV): el cierre + 1 día, salvo que la importación ocurra antes (entonces la hora de importación).
- Tipo de cambio: FIX de Banxico ≈ 12:00 CDMX + retraso; FRED publica con días de rezago.
- Operaciones: la hora en que se registraron en la terminal (`creado_en`).
- Noticias, calendario macro e insiders: la hora en que la terminal los obtuvo (`obtenido_en`).
Nunca se sobrescribe un `available_at` ya fijado: una revisión posterior de un dato no lo hace «conocido antes».
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, time, timedelta

import pandas as pd

from . import vigencia

RETRASO_HORAS_POR_DEFECTO = {  # publicación típica tras el cierre, por proveedor (se puede ajustar en [disponibilidad])
    "tiingo": 3, "alpaca": 1, "eodhd": 4, "barchart": 4, "archivo": 24, "demo_sintetico": 1,
    "banxico": 1, "fred": 72, "prueba": 1,
}


def _col(con, tabla: str) -> set[str]:
    return {r[1] for r in con.execute(f"PRAGMA table_info({tabla})")}  # noqa: S608 (nombre fijo)


def _agregar(con, tabla: str, columna: str, tipo: str) -> None:
    if columna not in _col(con, tabla):
        con.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")  # noqa: S608 (nombres fijos)


def _v1(con):
    for t in ("precios", "fx", "eventos_corporativos", "noticias", "eventos_macro", "insiders", "transacciones"):
        _agregar(con, t, "event_time", "TEXT")
        _agregar(con, t, "available_at", "TEXT")
    _agregar(con, "transacciones", "etapa", "TEXT")
    _agregar(con, "transacciones", "confirmada", "INTEGER NOT NULL DEFAULT 1")
    con.execute("CREATE INDEX IF NOT EXISTS ix_precios_disp ON precios(available_at)")


MIGRACIONES = [(1, _v1)]


def migrar(con: sqlite3.Connection, ajustes=None) -> int:
    con.execute("CREATE TABLE IF NOT EXISTS version_esquema (version INTEGER PRIMARY KEY, aplicada_en TEXT NOT NULL)")
    hecha = {r[0] for r in con.execute("SELECT version FROM version_esquema")}
    for v, fn in MIGRACIONES:
        if v not in hecha:
            fn(con)
            con.execute("INSERT INTO version_esquema VALUES (?, ?)", (v, datetime.now(UTC).isoformat(timespec="seconds")))
    con.commit()
    completar_tiempos(con, ajustes)
    return max((v for v, _ in MIGRACIONES), default=0)


# --------------------------------------------------------------------------------------------------------------
def cierre_utc(fecha: str, calendario: str) -> pd.Timestamp:
    c = vigencia.cierre_de_sesion(calendario, pd.Timestamp(fecha[:10]).date())
    if c is not None:
        t = pd.Timestamp(c)
        return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    # día sin sesión en el calendario (dato de otra bolsa): fin del día en Nueva York, conservador
    return pd.Timestamp(datetime.combine(pd.Timestamp(fecha[:10]).date(), time(23, 59)), tz="America/New_York").tz_convert("UTC")


def retrasos(ajustes=None) -> dict:
    extra = (ajustes.get("disponibilidad") if ajustes is not None else None) or {}
    return {**RETRASO_HORAS_POR_DEFECTO, **{k: float(v) for k, v in extra.items()}}


def disponibilidad_precio(fecha: str, proveedor: str, moneda: str, tipo_dato: str, hora_cotizacion: str | None,
                          obtenido_en: str | None, ajustes=None) -> tuple[str, str]:
    """(event_time, available_at) de una fila de precios."""
    if tipo_dato in ("tiempo_real", "retrasado") and hora_cotizacion:
        ev = pd.Timestamp(hora_cotizacion)
        ev = ev.tz_localize("UTC") if ev.tzinfo is None else ev.tz_convert("UTC")
        disp = pd.Timestamp(obtenido_en) if obtenido_en else ev
        disp = disp.tz_localize("UTC") if disp.tzinfo is None else disp.tz_convert("UTC")
        return ev.isoformat(), max(disp, ev).isoformat()
    cal = "XNYS" if moneda == "USD" else "XMEX"
    ev = cierre_utc(fecha, cal)
    disp = ev + timedelta(hours=retrasos(ajustes).get(proveedor, 24))
    if proveedor == "archivo" and obtenido_en:  # importado: no pudo conocerse antes de la importación si fue antes del plazo
        imp = pd.Timestamp(obtenido_en)
        imp = imp.tz_localize("UTC") if imp.tzinfo is None else imp.tz_convert("UTC")
        disp = max(ev, min(disp, imp))
    return ev.isoformat(), disp.isoformat()


def disponibilidad_fx(fecha: str, proveedor: str, ajustes=None) -> tuple[str, str]:
    if proveedor == "fred":
        ev = pd.Timestamp(datetime.combine(pd.Timestamp(fecha).date(), time(12, 0)), tz="America/New_York")
    else:  # Banxico FIX y demás: mediodía de la Ciudad de México
        ev = pd.Timestamp(datetime.combine(pd.Timestamp(fecha).date(), time(12, 0)), tz="America/Mexico_City")
    ev = ev.tz_convert("UTC")
    return ev.isoformat(), (ev + timedelta(hours=retrasos(ajustes).get(proveedor, 24))).isoformat()


def completar_tiempos(con: sqlite3.Connection, ajustes=None) -> int:
    """Rellena event_time/available_at donde falten. No toca filas que ya los tienen."""
    if "available_at" not in _col(con, "precios"):
        return 0
    n = 0
    filas = con.execute("SELECT rowid, fecha, proveedor, moneda, tipo_dato, hora_cotizacion, obtenido_en FROM precios "
                        "WHERE available_at IS NULL").fetchall()
    if filas:
        memo: dict = {}  # los cierres diarios comparten (fecha, proveedor, moneda): se calcula una vez por combinación
        valores = []
        for f in filas:
            clave = (f[1], f[2], f[3], f[4], f[5], f[6] if (f[2] == "archivo" or f[5]) else None)
            if clave not in memo:
                memo[clave] = disponibilidad_precio(f[1], f[2], f[3], f[4], f[5], f[6], ajustes)
            valores.append((*memo[clave], f[0]))
        con.executemany("UPDATE precios SET event_time=?, available_at=? WHERE rowid=?", valores)
        n += len(filas)
    filas = con.execute("SELECT rowid, fecha, proveedor FROM fx WHERE available_at IS NULL").fetchall()
    if filas:
        con.executemany("UPDATE fx SET event_time=?, available_at=? WHERE rowid=?",
                        [(*disponibilidad_fx(f[1], f[2], ajustes), f[0]) for f in filas])
        n += len(filas)
    # Eventos corporativos: se conocen con el precio del mismo día y proveedor.
    con.execute("UPDATE eventos_corporativos SET event_time = (SELECT p.event_time FROM precios p WHERE "
                "p.instrumento_id=eventos_corporativos.instrumento_id AND p.fecha=eventos_corporativos.fecha AND "
                "p.proveedor=eventos_corporativos.proveedor), available_at = (SELECT p.available_at FROM precios p WHERE "
                "p.instrumento_id=eventos_corporativos.instrumento_id AND p.fecha=eventos_corporativos.fecha AND "
                "p.proveedor=eventos_corporativos.proveedor) WHERE available_at IS NULL")
    con.execute("UPDATE transacciones SET event_time = fecha || 'T00:00:00-06:00', available_at = creado_en "
                "WHERE available_at IS NULL")
    for t, ev in (("noticias", "publicado"), ("eventos_macro", "fecha"), ("insiders", "fecha")):
        con.execute(f"UPDATE {t} SET event_time={ev}, available_at=obtenido_en WHERE available_at IS NULL")  # noqa: S608
    filas = con.execute("SELECT id, fecha FROM transacciones WHERE etapa IS NULL").fetchall()
    if filas:
        from . import reto
        con.executemany("UPDATE transacciones SET etapa=? WHERE id=?", [(reto.etapa_de_fecha(f[1]), f[0]) for f in filas])
    con.commit()
    return n
