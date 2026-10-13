"""Visualizaciones descriptivas basadas exclusivamente en cierres locales trazables.

- Una sola regla de prioridad entre fuentes: `mercado.PRIORIDAD_FUENTE` (la misma de propuestas y valuación).
- Precio ajustado SOLO por splits (`mercado._solo_splits`), como el simulador del Reto: un split no aparece como una
  caída o subida falsa.
- RSI de Wilder (el mismo método que TradingView), en `flujo/calculos.py`.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pandas as pd

from . import mercado
from .config import Ajustes
from .flujo import calculos

VENTANAS = (1, 5, 20)
ZONA = "America/Mexico_City"


def _cierres(con: sqlite3.Connection, demo: bool, instrumento_id: str | None = None, dias: int = 200) -> pd.DataFrame:
    """Un cierre por instrumento y fecha (fuente prioritaria), con precio ajustado por splits en la columna `p`."""
    filtro = "proveedor = 'demo_sintetico'" if demo else "proveedor <> 'demo_sintetico'"
    tipos = "tipo_dato = 'sintetico'" if demo else "tipo_dato IN ('cierre', 'nav')"
    args: list = [(date.today() - timedelta(days=dias)).isoformat()]
    extra = ""
    if instrumento_id:
        extra, args = "AND instrumento_id = ?", [*args, instrumento_id]
    df = pd.DataFrame([tuple(r) for r in con.execute(
        f"SELECT instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, proveedor, tipo_dato, obtenido_en "
        f"FROM precios WHERE {filtro} AND {tipos} AND fecha >= ? {extra}", args)],
        columns=["id", "fecha", "p", "aj", "volumen", "moneda", "proveedor", "tipo_dato", "obtenido_en"])
    if df.empty:
        return df
    df["p"] = pd.to_numeric(df["p"], errors="coerce")
    df["aj"] = pd.to_numeric(df["aj"], errors="coerce")
    df = df[df["p"] > 0]
    df["cierre"] = df["p"]
    df["prio"] = df["proveedor"].map(mercado.prioridad_fuente)
    df = df.sort_values(["id", "fecha", "prio", "obtenido_en"], ascending=[True, True, True, False])
    df = df.drop_duplicates(["id", "fecha"], keep="first").reset_index(drop=True)
    df["p"] = mercado._solo_splits(df)
    return df


def mapa(con: sqlite3.Connection, ajustes: Ajustes, ventana: int = 1) -> dict:
    if ventana not in VENTANAS:
        raise ValueError(f"ventana: use {', '.join(map(str, VENTANAS))} sesiones")
    instrumentos = {r["id"]: dict(r) for r in con.execute(
        "SELECT id, clave_operable, nombre, estado, mercado_operable, clase, categoria FROM instrumentos WHERE estado='activo'")}
    df = _cierres(con, ajustes.es_demo, dias=max(40, ventana * 3))
    celdas = []
    hoy = date.today()
    for iid, g in (df.groupby("id") if not df.empty else []):
        if iid not in instrumentos:
            continue
        g = g.sort_values("fecha")
        actual = g.iloc[-1]
        anterior = g.iloc[-1 - ventana] if len(g) > ventana else None
        cambio = None
        if anterior is not None and anterior["moneda"] == actual["moneda"] and anterior["p"] > 0:
            cambio = float(actual["p"] / anterior["p"] - 1)
        ins = instrumentos[iid]
        celdas.append({"id": iid, "clave": ins["clave_operable"], "nombre": ins["nombre"], "mercado": ins["mercado_operable"],
                       "clase": ins["clase"], "sector": ins["categoria"],
                       "fecha": actual["fecha"], "fecha_anterior": anterior["fecha"] if anterior is not None else None,
                       "cierre": float(actual["cierre"]), "cierre_anterior": float(anterior["cierre"]) if anterior is not None else None,
                       "moneda": actual["moneda"], "variacion": cambio, "proveedor": actual["proveedor"],
                       "tipo_dato": actual["tipo_dato"], "obtenido_en": actual["obtenido_en"],
                       "dias_calendario": max(0, (hoy - date.fromisoformat(actual["fecha"])).days),
                       "ajuste_split": bool(abs(float(actual["p"]) - float(actual["cierre"])) > 1e-9
                                            or (anterior is not None and abs(float(anterior["p"]) - float(anterior["cierre"])) > 1e-9))})
    celdas.sort(key=lambda r: (r["mercado"] or "", r["clave"] or ""))
    return {"celdas": celdas, "total": len(celdas), "ventana": ventana, "ventanas": list(VENTANAS),
            "modo": "sintetico" if ajustes.es_demo else "real", "zona_horaria": ZONA,
            "metodo": f"Variación = cierre más reciente / cierre de {ventana} sesión(es) antes − 1, por instrumento, en su "
                      "moneda de origen, con precio ajustado solo por splits (como el simulador del Reto). Fuente por "
                      "fecha según la prioridad única de la terminal.",
            "nota": "Cierres históricos locales: no es un mapa en tiempo real ni la cotización del simulador. Las emisoras "
                    "del SIC se miden en USD de su bolsa de origen."}


def serie(con: sqlite3.Connection, ajustes: Ajustes, instrumento_id: str) -> dict:
    ins = con.execute("SELECT id, clave_operable, nombre FROM instrumentos WHERE id=? AND estado='activo'",
                      (instrumento_id,)).fetchone()
    if not ins:
        raise ValueError("Instrumento activo no encontrado")
    df = _cierres(con, ajustes.es_demo, instrumento_id, dias=400)
    filas = df.sort_values("fecha").tail(120).to_dict("records") if not df.empty else []
    cierre = [float(r["p"]) for r in filas]
    puntos = [{"fecha": r["fecha"], "cierre": c, "media_20": m, "rsi_14": s, "volumen": r["volumen"]}
              for r, c, m, s in zip(filas, cierre, calculos.sma(cierre, 20), calculos.rsi_wilder(cierre, 14))]
    ultimo = filas[-1] if filas else None
    return {"id": ins["id"], "clave": ins["clave_operable"], "nombre": ins["nombre"],
            "puntos": puntos, "moneda": ultimo["moneda"] if ultimo else None,
            "proveedor": ultimo["proveedor"] if ultimo else None,
            "obtenido_en": ultimo["obtenido_en"] if ultimo else None,
            "fecha": ultimo["fecha"] if ultimo else None,
            "modo": "sintetico" if ajustes.es_demo else "real",
            "nota": "Cierres diarios registrados, ajustados solo por splits; SMA20 y RSI14 (Wilder) son indicadores "
                    "retrospectivos descriptivos. Las velas OHLCV reales están en «Velas» cuando hay proveedor o CSV."}
