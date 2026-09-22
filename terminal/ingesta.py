"""Adquisición incremental de datos: elige adaptador por instrumento, respeta límites y registra cada corrida."""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

from . import vigencia
from .adaptadores import CLASES, FX_USDMXN, ErrorProveedor, LimiteAlcanzado
from .config import Ajustes, credencial
from .db import ahora, transaccion

log = logging.getLogger("terminal.ingesta")

ORDEN_PRECIOS = ["tiingo", "eodhd"]  # los fondos solo se alimentan por archivo (NAV)
ORDEN_FX = ["banxico", "fred"]
ANIOS_HISTORIA = 5


def construir_adaptadores(con: sqlite3.Connection, ajustes: Ajustes, cliente=None) -> dict:
    prov = ajustes["proveedores"]
    return {n: CLASES[n](con, prov.get(n, {}), credencial(n), cliente=cliente) for n in CLASES}


def estado_proveedores(con: sqlite3.Connection, ajustes: Ajustes) -> list[dict]:
    out = []
    for n, a in construir_adaptadores(con, ajustes).items():
        ult = con.execute("SELECT fin, estado, mensaje, registros FROM ingestas WHERE proveedor=? ORDER BY id DESC LIMIT 1",
                          (n,)).fetchone()
        out.append({"proveedor": n, "descripcion": a.descripcion, "uso_permitido": a.uso_permitido,
                    "tipo_dato": a.tipo_dato, "requiere_credencial": a.requiere_credencial,
                    "configurado": a.configurado(), "peticiones_restantes": a.peticiones_restantes(),
                    "ultima_corrida": dict(ult) if ult else None})
    return out


def _ultima_fecha(con, tabla: str, clave_col: str, clave: str, proveedor: str) -> date | None:
    fila = con.execute(f"SELECT MAX(fecha) FROM {tabla} WHERE {clave_col}=? AND proveedor=?",  # noqa: S608 (nombres fijos)
                       (clave, proveedor)).fetchone()
    return date.fromisoformat(fila[0]) if fila and fila[0] else None


def _registrar(con, proveedor: str, inicio: str, estado: str, registros: int, mensaje: str) -> None:
    con.execute("INSERT INTO ingestas (proveedor, inicio, fin, estado, registros, mensaje) VALUES (?,?,?,?,?,?)",
                (proveedor, inicio, ahora(), estado, registros, mensaje[:500]))
    con.commit()


def actualizar_fx(con, adaptadores: dict, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    for n in ORDEN_FX:
        a = adaptadores[n]
        if not a.configurado():
            continue
        inicio = ahora()
        ult = _ultima_fecha(con, "fx", "par", "USDMXN", n)
        desde = (ult + timedelta(days=1)) if ult else hoy - timedelta(days=365 * ANIOS_HISTORIA + 30)
        if desde > hoy:
            return {"proveedor": n, "estado": "al_dia", "registros": 0}
        try:
            barras = a.historico(FX_USDMXN, desde, hoy)
        except ErrorProveedor as e:
            _registrar(con, n, inicio, "error", 0, str(e))
            continue
        ts = ahora()
        with transaccion(con):
            con.executemany("INSERT OR REPLACE INTO fx VALUES ('USDMXN',?,?,?,?,?)",
                            [(b.fecha, b.cierre, n, "fx", ts) for b in barras])
        _registrar(con, n, inicio, "ok", len(barras), "tipo de cambio USD/MXN")
        return {"proveedor": n, "estado": "ok", "registros": len(barras)}
    return {"proveedor": None, "estado": "sin_proveedor", "registros": 0}


def actualizar_precios(con, adaptadores: dict, ids_prioritarios: list[str] | None = None,
                       hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    instrs = [dict(r) for r in con.execute("SELECT * FROM instrumentos WHERE estado='activo'")]
    prio = set(ids_prioritarios or [])
    instrs.sort(key=lambda i: (i["id"] not in prio, i["id"]))
    resumen = {n: {"registros": 0, "errores": 0, "omitidos_limite": 0, "al_dia": 0} for n in ORDEN_PRECIOS}
    agotados: set[str] = set()
    inicios = {n: ahora() for n in ORDEN_PRECIOS}
    mensajes: dict[str, list[str]] = {n: [] for n in ORDEN_PRECIOS}
    for ins in instrs:
        for n in ORDEN_PRECIOS:
            a = adaptadores[n]
            if not a.configurado() or not a.soporta(ins):
                continue
            if n in agotados:
                resumen[n]["omitidos_limite"] += 1
                break
            ult = _ultima_fecha(con, "precios", "instrumento_id", ins["id"], n)
            esperada = vigencia.ultima_sesion_cerrada(vigencia.codigo_calendario(ins))
            if ult and ult >= esperada:
                resumen[n]["al_dia"] += 1
                break
            desde = (ult + timedelta(days=1)) if ult else hoy - timedelta(days=365 * ANIOS_HISTORIA)
            try:
                barras = a.historico(ins, desde, hoy)
            except LimiteAlcanzado as e:
                agotados.add(n)
                mensajes[n].append(str(e))
                resumen[n]["omitidos_limite"] += 1
                break
            except ErrorProveedor as e:
                resumen[n]["errores"] += 1
                mensajes[n].append(f"{ins['id']}: {e}")
                continue
            ts = ahora()
            moneda = ins["moneda_referencia"] or "MXN"
            with transaccion(con):
                con.executemany(
                    "INSERT OR REPLACE INTO precios VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(ins["id"], b.fecha, b.cierre, b.cierre_ajustado, b.volumen, moneda, n, a.tipo_dato, None, ts)
                     for b in barras])
                eventos = [(ins["id"], b.fecha, "dividendo", b.dividendo, n) for b in barras if b.dividendo]
                eventos += [(ins["id"], b.fecha, "split", b.factor_split, n) for b in barras if b.factor_split != 1]
                con.executemany("INSERT OR REPLACE INTO eventos_corporativos VALUES (?,?,?,?,?)", eventos)
            resumen[n]["registros"] += len(barras)
            break
    for n in ORDEN_PRECIOS:
        if adaptadores[n].configurado():
            r = resumen[n]
            estado = "ok" if not r["errores"] and not r["omitidos_limite"] else "parcial"
            _registrar(con, n, inicios[n], estado, r["registros"],
                       f"al día {r['al_dia']}, errores {r['errores']}, pendientes por límite {r['omitidos_limite']}. "
                       + " | ".join(mensajes[n][:5]))
    return resumen


def actualizar_todo(con, ajustes: Ajustes, ids_prioritarios: list[str] | None = None, cliente=None) -> dict:
    if ajustes.es_demo:
        from .adaptadores import demo
        n = demo.generar(con, semilla=ajustes["optimizacion"]["semilla"])
        _registrar(con, "demo_sintetico", ahora(), "ok", n, "datos sintéticos regenerados (modo demostración)")
        return {"modo": "demo", "registros": n}
    ad = construir_adaptadores(con, ajustes, cliente=cliente)
    return {"fx": actualizar_fx(con, ad), "precios": actualizar_precios(con, ad, ids_prioritarios)}
