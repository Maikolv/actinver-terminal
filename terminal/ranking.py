"""Ranking de TODAS las acciones del universo, independiente de la cartera.

Se recalcula con el último precio disponible de cada emisora cada vez que se consulta; es «tiempo real» solo en la
medida en que lo sea el dato: cada fila muestra su tipo (cierre, tiempo real, retrasado), fecha y vigencia.
Criterio declarado (no es recomendación ni pronóstico; ordena por comportamiento reciente y estabilidad):
  puntuación = promedio ponderado de percentiles dentro del universo mostrado
    30 % rendimiento de 20 sesiones · 30 % rendimiento de 60 sesiones · 20 % estabilidad (1 / volatilidad de 60)
    · 20 % tendencia (precio frente a su media de 50)
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from . import mercado
from .config import Ajustes

PESOS = {"rend_20": 0.30, "rend_60": 0.30, "estabilidad": 0.20, "tendencia": 0.20}
CLASES = ("accion", "fibra", "reit", "etf")


def calcular(con: sqlite3.Connection, ajustes: Ajustes, mercado_filtro: str = "ambos") -> dict:
    ins = mercado.instrumentos(con)
    ids = [i for i, v in ins.items() if v["estado"] == "activo" and v["clase"] in CLASES
           and (mercado_filtro == "ambos" or (mercado_filtro == "nacionales") == (v["mercado_operable"] != "BMV-SIC"))]
    precios = mercado.precios_mxn(con, ajustes, ids, ajustados=False) if ids else pd.DataFrame()
    cot = mercado.cotizaciones(con, ajustes, ids) if ids else {}
    filas = []
    for i in ids:
        q = cot.get(i, {})
        s = precios[i].dropna() if i in precios.columns else pd.Series(dtype=float)
        if len(s) < 61 or q.get("estado") in ("sin_datos", None):
            continue
        r = np.log(s).diff().dropna()
        vol60 = float(r.iloc[-60:].std() * np.sqrt(252))
        filas.append({
            "id": i, "clave_operable": ins[i]["clave_operable"], "nombre": (ins[i]["nombre"] or "").strip()[:50],
            "mercado": "extranjera (SIC)" if ins[i]["mercado_operable"] == "BMV-SIC" else "nacional (BMV)",
            "clase": ins[i]["clase"], "precio_mxn": float(s.iloc[-1]),
            "rend_1": float(s.iloc[-1] / s.iloc[-2] - 1), "rend_5": float(s.iloc[-1] / s.iloc[-6] - 1),
            "rend_20": float(s.iloc[-1] / s.iloc[-21] - 1), "rend_60": float(s.iloc[-1] / s.iloc[-61] - 1),
            "vol_60": vol60, "estabilidad": 1 / vol60 if vol60 > 0 else 0.0,
            "tendencia": float(s.iloc[-1] / s.iloc[-50:].mean() - 1),
            "caida_60": float((s.iloc[-60:] / s.iloc[-60:].cummax() - 1).min()),
            "fecha": q.get("fecha"), "tipo_dato": q.get("tipo_dato"), "vigencia": q.get("estado"), "proveedor": q.get("proveedor"),
            "precio_es_referencia": ins[i]["mercado_operable"] == "BMV-SIC",
        })
    if filas:
        df = pd.DataFrame(filas)
        df["puntuacion"] = sum(df[k].rank(pct=True) * w for k, w in PESOS.items()) * 100
        df = df.sort_values("puntuacion", ascending=False).reset_index(drop=True)
        df["posicion"] = df.index + 1
        filas = df.round(6).to_dict("records")
    return {"filas": filas, "n": len(filas), "universo": len(ids), "criterio": PESOS, "filtro": mercado_filtro,
            "aviso": ("Ordena por comportamiento reciente y estabilidad; no es recomendación ni pronóstico. Se actualiza con "
                      "cada precio nuevo: hoy los precios BMV son cierres (EOD) y los del SIC son referencia de su bolsa de "
                      "origen convertida a pesos, no la cotización del SIC.")}
