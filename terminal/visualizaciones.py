"""Visualizaciones descriptivas basadas exclusivamente en cierres locales trazables."""
from __future__ import annotations

import sqlite3
from datetime import date

from .config import Ajustes


def _cierres(con: sqlite3.Connection, demo: bool, instrumento_id: str | None = None, limite: int = 120):
    """Elige una fuente por instrumento/fecha antes de limitar el histórico."""
    filtro = "p.proveedor = 'demo_sintetico'" if demo else "p.proveedor <> 'demo_sintetico'"
    tipos = "p.tipo_dato = 'sintetico'" if demo else "p.tipo_dato IN ('cierre', 'nav')"
    id_sql = "AND p.instrumento_id = ?" if instrumento_id else ""
    consulta = f"""
        WITH elegidos AS (
            SELECT p.instrumento_id, p.fecha, p.cierre, p.volumen, p.moneda, p.proveedor,
                   p.tipo_dato, p.obtenido_en,
                   ROW_NUMBER() OVER (
                       PARTITION BY p.instrumento_id, p.fecha
                       ORDER BY CASE p.proveedor
                           WHEN 'bmv_licenciado' THEN 0 WHEN 'infosel' THEN 1 WHEN 'lseg' THEN 2
                           WHEN 'eodhd' THEN 10 WHEN 'twelvedata' THEN 11 WHEN 'actinver_pdf' THEN 12
                           WHEN 'tiingo' THEN 20 WHEN 'alpaca' THEN 21 WHEN 'barchart' THEN 22
                           WHEN 'archivo' THEN 30 ELSE 35 END
                   ) AS prioridad
            FROM precios p WHERE {filtro} AND {tipos} {id_sql}
        ), fechados AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY instrumento_id ORDER BY fecha DESC) AS orden
            FROM elegidos WHERE prioridad = 1
        )
        SELECT instrumento_id, fecha, cierre, volumen, moneda, proveedor, tipo_dato, obtenido_en
        FROM fechados WHERE orden <= ? ORDER BY instrumento_id, fecha DESC
    """
    parametros = (instrumento_id, limite) if instrumento_id else (limite,)
    return [dict(r) for r in con.execute(consulta, parametros)]


def mapa(con: sqlite3.Connection, ajustes: Ajustes) -> dict:
    instrumentos = {r["id"]: dict(r) for r in con.execute(
        "SELECT id, clave_operable, nombre, estado, mercado_operable FROM instrumentos WHERE estado='activo'")}
    por_id: dict[str, list[dict]] = {}
    for fila in _cierres(con, ajustes.es_demo, limite=2):
        if fila["instrumento_id"] in instrumentos:
            por_id.setdefault(fila["instrumento_id"], []).append(fila)
    celdas = []
    for iid, registros in por_id.items():
        actual = registros[0]
        anterior = registros[1] if len(registros) > 1 else None
        cambio = None
        if anterior and anterior["moneda"] == actual["moneda"] and anterior["cierre"] > 0:
            cambio = actual["cierre"] / anterior["cierre"] - 1
        instrumento = instrumentos[iid]
        celdas.append({"id": iid, "clave": instrumento["clave_operable"],
                       "nombre": instrumento["nombre"], "mercado": instrumento["mercado_operable"],
                       "fecha": actual["fecha"], "fecha_anterior": anterior["fecha"] if anterior else None,
                       "cierre": actual["cierre"], "moneda": actual["moneda"],
                       "variacion": cambio, "proveedor": actual["proveedor"],
                       "obtenido_en": actual["obtenido_en"], "tipo_dato": actual["tipo_dato"],
                       "dias_calendario": max(0, (date.today() - date.fromisoformat(actual["fecha"])).days)})
    celdas.sort(key=lambda r: (r["mercado"] or "", r["clave"] or ""))
    return {"celdas": celdas, "total": len(celdas), "modo": "sintetico" if ajustes.es_demo else "real",
            "nota": "Variación entre los dos últimos cierres disponibles de cada instrumento, en su moneda de origen; "
                    "no equivale a un mapa en tiempo real ni a una cotización del simulador."}


def _indicadores(cierres: list[float]) -> list[dict]:
    salida = []
    for i, valor in enumerate(cierres):
        ventana = cierres[max(0, i-19):i+1]
        media = sum(ventana) / 20 if len(ventana) == 20 else None
        rsi = None
        if i >= 14:
            cambios = [cierres[j] - cierres[j-1] for j in range(i-13, i+1)]
            subidas = sum(max(c, 0) for c in cambios) / 14
            bajadas = sum(max(-c, 0) for c in cambios) / 14
            rsi = 100 if bajadas == 0 and subidas > 0 else 50 if bajadas == 0 else 100 - 100/(1 + subidas/bajadas)
        salida.append({"cierre": valor, "media_20": media, "rsi_14": rsi})
    return salida


def serie(con: sqlite3.Connection, ajustes: Ajustes, instrumento_id: str) -> dict:
    ins = con.execute("SELECT id, clave_operable, nombre FROM instrumentos WHERE id=? AND estado='activo'",
                      (instrumento_id,)).fetchone()
    if not ins:
        raise ValueError("Instrumento activo no encontrado")
    filas = list(reversed(_cierres(con, ajustes.es_demo, instrumento_id, 120)))
    cierre = [r["cierre"] for r in filas]
    indicadores = _indicadores(cierre)
    puntos = [{"fecha": r["fecha"], "cierre": r["cierre"], "media_20": ind["media_20"],
               "rsi_14": ind["rsi_14"], "volumen": r["volumen"]}
              for r, ind in zip(filas, indicadores)]
    ultimo = filas[-1] if filas else None
    return {"id": ins["id"], "clave": ins["clave_operable"], "nombre": ins["nombre"],
            "puntos": puntos, "moneda": ultimo["moneda"] if ultimo else None,
            "proveedor": ultimo["proveedor"] if ultimo else None,
            "obtenido_en": ultimo["obtenido_en"] if ultimo else None,
            "fecha": ultimo["fecha"] if ultimo else None,
            "modo": "sintetico" if ajustes.es_demo else "real",
            "nota": "Cierres diarios registrados; SMA20 y RSI14 son indicadores retrospectivos descriptivos. "
                    "No hay OHLC local verificado para construir velas. Abra la gráfica oficial externa para velas."}
