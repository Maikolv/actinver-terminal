"""Ranking de acciones, ETF y fondos del universo, independiente de la cartera.

Se recalcula con el último precio disponible de cada emisora cada vez que se consulta; es «tiempo real» solo en la
medida en que lo sea el dato: cada fila muestra su tipo (cierre, tiempo real, retrasado), fecha y vigencia.
Criterio declarado (no es recomendación ni pronóstico; ordena por comportamiento reciente y estabilidad):
  puntuación = promedio ponderado de percentiles dentro del universo mostrado
    30 % rendimiento de 20 sesiones · 30 % rendimiento de 60 sesiones · 20 % estabilidad (1 / volatilidad de 60)
    · 20 % tendencia (precio frente a su media de 50)
Las percentiles se calculan DENTRO de la clase elegida (acciones, ETF o fondos): un fondo de deuda no compite en
estabilidad con una acción. Los fondos del portal tienen poca historia (NAV oficiales desde hace pocas semanas): con
menos de 61 sesiones se usan ventanas cortas (la mitad y el total de lo disponible, mínimo 11 sesiones) y la fila se
marca «historia corta»; no es comparable con las ventanas de 20 y 60 sesiones.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from . import capitalizacion, mercado, reto
from .config import Ajustes

PESOS = {"rend_20": 0.30, "rend_60": 0.30, "estabilidad": 0.20, "tendencia": 0.20}
CLASES = {"acciones": ("accion", "fibra", "reit"), "etf": ("etf",),
          "fondos": ("fondo_deuda", "fondo_renta_variable", "fondo_multiactivo")}
MIN_CORTA = 11


def calcular(con: sqlite3.Connection, ajustes: Ajustes, mercado_filtro: str = "ambos", clase: str = "acciones") -> dict:
    if clase not in CLASES:
        raise ValueError("clase: acciones, etf o fondos")
    ins = mercado.instrumentos(con)
    ids = [i for i, v in ins.items() if v["estado"] == "activo" and v["clase"] in CLASES[clase]
           and (mercado_filtro == "ambos" or (mercado_filtro == "nacionales") == (v["mercado_operable"] != "BMV-SIC"))]
    # Durante el Reto solo se ordena lo que el simulador permite operar (mismo criterio que las propuestas)
    catalogo = {r[0] for r in con.execute("SELECT id FROM universo_simulador")} if reto.activo() else set()
    fuera = [i for i in ids if catalogo and i not in catalogo]
    ids = [i for i in ids if i not in set(fuera)]
    precios = mercado.precios_mxn(con, ajustes, ids, ajustados="splits") if ids else pd.DataFrame()
    cot = mercado.cotizaciones(con, ajustes, ids) if ids else {}
    filas = []
    for i in ids:
        q = cot.get(i, {})
        s = precios[i].dropna() if i in precios.columns else pd.Series(dtype=float)
        if len(s) < (MIN_CORTA if clase == "fondos" else 61) or q.get("estado") in ("sin_datos", None):
            continue
        larga = min(60, len(s) - 1)               # 60 sesiones, o lo disponible en fondos con historia corta
        corta = min(20, larga // 2) if larga < 60 else 20
        r = np.log(s).diff().dropna()
        vol60 = float(r.iloc[-larga:].std() * np.sqrt(252))
        filas.append({
            "id": i, "clave_operable": ins[i]["clave_operable"], "nombre": (ins[i]["nombre"] or "").strip()[:50],
            "mercado": "extranjera (SIC)" if ins[i]["mercado_operable"] == "BMV-SIC" else "nacional (BMV)",
            "clase": ins[i]["clase"], "precio_mxn": float(s.iloc[-1]),
            "rend_1": float(s.iloc[-1] / s.iloc[-2] - 1), "rend_5": float(s.iloc[-1] / s.iloc[-6] - 1),
            "rend_20": float(s.iloc[-1] / s.iloc[-1 - corta] - 1), "rend_60": float(s.iloc[-1] / s.iloc[-1 - larga] - 1),
            "vol_60": vol60, "estabilidad": 1 / vol60 if vol60 > 0 else 0.0,
            "tendencia": float(s.iloc[-1] / s.iloc[-min(50, larga):].mean() - 1),
            "caida_60": float((s.iloc[-larga:] / s.iloc[-larga:].cummax() - 1).min()),
            "ventanas": [corta, larga], "historia_corta": larga < 60, "sesiones": len(s),
            "fecha": q.get("fecha"), "tipo_dato": q.get("tipo_dato"), "vigencia": q.get("estado"), "proveedor": q.get("proveedor"),
            "precio_es_referencia": ins[i]["mercado_operable"] == "BMV-SIC",
        })
    cal = {r["instrumento_id"]: dict(r) for r in con.execute(
        "SELECT c.* FROM calificaciones c JOIN (SELECT instrumento_id, MAX(fecha) f FROM calificaciones GROUP BY instrumento_id) u "
        "ON c.instrumento_id=u.instrumento_id AND c.fecha=u.f")}
    for f in filas:
        c = cal.get(f["id"])
        f["calificacion_sa"] = ({"quant": c["quant"], "autores": c["autores"], "wall_street": c["wall_street"],
                                 "fecha": c["fecha"]} if c else None)
    caps = capitalizacion.para_precios(con, ajustes, {f["id"]: f["precio_mxn"] for f in filas})
    for f in filas:
        f.update(caps.get(f["id"]) or {"cap_mxn": None, "cap_usd": None, "cap_categoria": None, "cap_estado": "sin_dato",
                                        "cap_detalle": None, "cap_fecha": None, "cap_fuente": None})
    if filas:
        df = pd.DataFrame(filas)
        df["puntuacion"] = sum(df[k].rank(pct=True) * w for k, w in PESOS.items()) * 100
        df = df.sort_values("puntuacion", ascending=False).reset_index(drop=True)
        df["posicion"] = df.index + 1
        filas = df.round(6).astype(object).where(df.notna(), None).to_dict("records")
    return {"filas": filas, "n": len(filas), "universo": len(ids), "criterio": PESOS, "filtro": mercado_filtro, "clase": clase,
            "fuera_del_catalogo": len(fuera), "capitalizacion": capitalizacion.guia(),
            "aviso": ("Ordena por comportamiento reciente y estabilidad; no es recomendación ni pronóstico. Se actualiza con "
                      "cada precio nuevo: hoy los precios BMV son cierres (EOD) y los del SIC son referencia de su bolsa de "
                      "origen convertida a pesos, no la cotización del SIC.")}
