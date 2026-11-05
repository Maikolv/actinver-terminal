"""Gestión de riesgo del plan de acción: decide, posición por posición, si se mantiene, se reduce o se vende.

Reglas mecánicas y explícitas (se informan con sus cifras; ninguna se aplica a escondidas):
1. Stop dinámico por volatilidad (chandelier sobre cierres) confirmado por tendencia: si el precio cae debajo de
   máximo(últimas 22 sesiones) × (1 − 3 · σ diaria de 20 sesiones) Y debajo de su SMA50, la posición se VENDE. Sin la
   confirmación, una caída general de un día (5-nov: Nasdaq −7 %) vendía también lo que sigue en tendencia alcista.
2. Tendencia bajista (precio < SMA20 < SMA50): se REDUCE a la mitad; si además pierde ≥ 15 % contra su costo, se VENDE.
3. Concentración: ninguna posición por encima de 25 % de la cartera.
4. Volatilidad de la cartera: si la σ anual de lo que queda supera 30 %, todas las posiciones se recortan en la misma
   proporción hasta llegar a ese objetivo.
5. Reglas del Reto: si las ventas dejaran menos de 5 emisoras, se conserva una parte mínima de las de menor volatilidad.
Lo que se libera se reinvierte en las emisoras de la propuesta de referencia que estén en tendencia alcista
(precio > SMA50 y SMA20 > SMA50) y no tengan señal de venta; si ninguna pasa el filtro, queda en efectivo.

Son reglas de control de pérdidas, no un pronóstico: reducen caídas grandes a cambio de vender a veces antes de un
rebote. Ninguna regla garantiza utilidad. La terminal no envía órdenes.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import mercado, reto
from .config import Ajustes

REGLAS = {"ventana_maximo": 22, "ventana_sigma": 20, "k_sigma": 3.0, "sma_corta": 20, "sma_larga": 50,
          "perdida_costo": 0.15, "peso_max": 0.25, "vol_objetivo": 0.30, "peso_minimo_reto": 0.02}
DIAS = 252


def reglas(ajustes: Ajustes) -> dict:
    return {**REGLAS, **(ajustes.get("gestion_riesgo") or {})}


def _serie(P: pd.DataFrame, iid: str, precio: float | None) -> pd.Series:
    """Cierres diarios en MXN con el precio de la valuación de hoy como último punto."""
    s = P[iid].dropna() if iid in P.columns else pd.Series(dtype=float)
    if precio and precio > 0:
        hoy = pd.Timestamp.today().normalize()
        s = pd.concat([s[s.index < hoy], pd.Series([float(precio)], index=[hoy])])
    return s


def indicadores(s: pd.Series, r: dict) -> dict | None:
    if len(s) < r["sma_larga"] + 1:
        return None
    precio = float(s.iloc[-1])
    sigma = float(s.pct_change().tail(r["ventana_sigma"]).std())
    maximo = float(s.tail(r["ventana_maximo"]).max())
    sma_c, sma_l = float(s.tail(r["sma_corta"]).mean()), float(s.tail(r["sma_larga"]).mean())
    return {"precio": precio, "sigma_diaria": sigma, "maximo": maximo, "stop": maximo * (1 - r["k_sigma"] * sigma),
            "sma_corta": sma_c, "sma_larga": sma_l, "bajista": precio < sma_c < sma_l,
            "alcista": precio > sma_l and sma_c > sma_l}


def evaluar(con, ajustes: Ajustes, cartera: dict, propuesta: dict | None = None) -> dict:
    r = reglas(ajustes)
    total = float(cartera.get("valor_total") or 0)
    pos = [p for p in cartera.get("posiciones") or [] if (p.get("cantidad") or 0) > 0 and (p.get("valor_mxn") or 0) > 0
           and not str(p["instrumento_id"]).startswith("FONDO:")]
    if total <= 0 or not pos:
        return {"activo": False, "motivo": "sin posiciones valuadas", "posiciones": [], "filas": [], "reglas": r}
    cand = [a["id"] for a in (propuesta or {}).get("pesos") or [] if a.get("peso", 0) > 0]
    ids = list(dict.fromkeys([p["instrumento_id"] for p in pos] + cand))
    P = mercado.precios_mxn(con, ajustes, ids, ajustados="splits")
    filas, sin_dato = [], []
    for p in pos:
        iid, peso = p["instrumento_id"], float(p["valor_mxn"]) / total
        ind = indicadores(_serie(P, iid, p.get("precio_mxn")), r)
        f = {"id": iid, "clave": p.get("clave_operable") or iid, "peso_actual": peso, "peso_objetivo": peso,
             "perdida_costo": p.get("no_realizado_pct"), "motivos": [], "regla": None, **(ind or {})}
        if not ind:
            sin_dato.append(f["clave"])
            f["motivos"].append("Sin historia suficiente para evaluar el riesgo: se mantiene.")
            filas.append(f)
            continue
        perdida = float(p.get("no_realizado_pct") or 0)
        if ind["precio"] < ind["stop"] and ind["precio"] < ind["sma_larga"]:
            f["peso_objetivo"], f["regla"] = 0.0, "stop"
            f["motivos"].append(f"Rompió su stop: precio {ind['precio']:,.2f} < {ind['stop']:,.2f} (máximo de "
                                f"{r['ventana_maximo']} sesiones {ind['maximo']:,.2f} − {r['k_sigma']:g}× su volatilidad diaria "
                                f"de {ind['sigma_diaria']:.1%}) y está debajo de su SMA{r['sma_larga']} ({ind['sma_larga']:,.2f}).")
        elif ind["bajista"] and perdida <= -r["perdida_costo"]:
            f["peso_objetivo"], f["regla"] = 0.0, "tendencia_perdida"
            f["motivos"].append(f"Tendencia bajista (precio < SMA{r['sma_corta']} < SMA{r['sma_larga']}) y pierde "
                                f"{perdida:.0%} contra su costo.")
        elif ind["bajista"]:
            f["peso_objetivo"], f["regla"] = peso / 2, "tendencia"
            f["motivos"].append(f"Tendencia bajista (precio < SMA{r['sma_corta']} < SMA{r['sma_larga']}): se reduce a la mitad.")
        if f["peso_objetivo"] > r["peso_max"]:
            f["peso_objetivo"] = r["peso_max"]
            f["regla"] = f["regla"] or "concentracion"
            f["motivos"].append(f"Concentración: {peso:.0%} de la cartera; el tope de riesgo es {r['peso_max']:.0%}.")
        filas.append(f)

    # 4) volatilidad de la cartera con los pesos que quedan
    R = P[[f["id"] for f in filas if f["id"] in P.columns]].ffill(limit=3).pct_change(fill_method=None).tail(60).dropna(how="all")
    w = pd.Series({f["id"]: f["peso_objetivo"] for f in filas}).reindex(R.columns).fillna(0.0)
    cov = R.fillna(0.0).cov().values * DIAS
    vol_antes = float(math.sqrt(max(w.values @ cov @ w.values, 0.0))) if len(w) else 0.0
    w_actual = pd.Series({f["id"]: f["peso_actual"] for f in filas}).reindex(R.columns).fillna(0.0)
    vol_actual = float(math.sqrt(max(w_actual.values @ cov @ w_actual.values, 0.0))) if len(w_actual) else 0.0
    factor = min(1.0, r["vol_objetivo"] / vol_antes) if vol_antes > 0 else 1.0
    if factor < 0.999:
        for f in filas:
            if f["peso_objetivo"] > 0:
                f["peso_objetivo"] *= factor
                f["motivos"].append(f"La cartera tendría {vol_antes:.0%} de volatilidad anual (objetivo {r['vol_objetivo']:.0%}): "
                                    f"todas las posiciones se recortan al {factor:.0%}.")
                f["regla"] = f["regla"] or "volatilidad"

    # Reinversión: emisoras de la propuesta en tendencia alcista y sin señal de venta
    minimo = int(((reto.config().get("reglas") or {}).get("min_emisoras") or 5)) if reto.activo() else 0
    liberado = sum(f["peso_actual"] - f["peso_objetivo"] for f in filas)
    vender = {f["id"] for f in filas if f["peso_objetivo"] < f["peso_actual"] - 1e-9}
    compras = []
    if liberado > 0.005 and propuesta:
        objetivo_prop = {a["id"]: float(a["peso"]) for a in propuesta.get("pesos") or [] if a.get("peso", 0) > 0}
        aptas = {}
        for iid, wp in objetivo_prop.items():
            if iid in vender:
                continue
            ind = indicadores(_serie(P, iid, None), r)
            if ind and ind["alcista"]:
                aptas[iid] = (wp, ind)
        suma = sum(wp for wp, _ in aptas.values())
        if minimo and len({f["id"] for f in filas if f["peso_objetivo"] > 0} | set(aptas)) < minimo:
            _minimo_reto(filas, minimo, r)
            liberado = sum(f["peso_actual"] - f["peso_objetivo"] for f in filas)
        actuales = {f["id"]: f for f in filas}
        for iid, (wp, ind) in aptas.items():
            extra = liberado * wp / suma
            base = actuales[iid]["peso_objetivo"] if iid in actuales else 0.0
            nuevo = min(base + extra, r["peso_max"])
            if nuevo - base > 0.005:
                compras.append({"id": iid, "peso_actual": actuales[iid]["peso_actual"] if iid in actuales else 0.0,
                                "peso_objetivo": nuevo, "motivo": f"Reinversión en tendencia alcista (precio > SMA{r['sma_larga']} "
                                f"y SMA{r['sma_corta']} > SMA{r['sma_larga']}) de la propuesta «{propuesta.get('nombre', '')}».",
                                **{k: ind[k] for k in ("precio", "sma_corta", "sma_larga")}})

    if minimo and not compras and len([f for f in filas if f["peso_objetivo"] > 0]) < minimo:
        _minimo_reto(filas, minimo, r)
    ins = mercado.instrumentos(con)
    salida = []
    for f in filas:
        delta = f["peso_objetivo"] - f["peso_actual"]
        accion = "vender" if delta < -0.005 else "mantener"
        salida.append({"id": f["id"], "clave_operable": f["clave"], "peso_actual": f["peso_actual"],
                       "peso_objetivo": f["peso_objetivo"], "delta_pp": delta * 100, "monto_mxn": delta * total,
                       "accion": accion, "nota": " ".join(f["motivos"]) or "Sin señal de riesgo: se mantiene."})
    for c in compras:
        delta = c["peso_objetivo"] - c["peso_actual"]
        salida.append({"id": c["id"], "clave_operable": (ins.get(c["id"]) or {}).get("clave_operable") or c["id"],
                       "peso_actual": c["peso_actual"], "peso_objetivo": c["peso_objetivo"], "delta_pp": delta * 100,
                       "monto_mxn": delta * total, "accion": "comprar", "nota": c["motivo"]})
    finales = {**{f["id"]: f["peso_objetivo"] for f in filas}, **{c["id"]: c["peso_objetivo"] for c in compras}}
    Rf = P[[i for i in finales if i in P.columns]].ffill(limit=3).pct_change(fill_method=None).tail(60).fillna(0.0)
    w_final = pd.Series(finales).reindex(Rf.columns).fillna(0.0).values
    vol_final = float(math.sqrt(max(w_final @ (Rf.cov().values * DIAS) @ w_final, 0.0))) if len(w_final) else 0.0
    perdida_total = float(cartera.get("resultado_total") or 0) / float(cartera.get("aportacion_neta") or total)
    ventas = [s for s in salida if s["accion"] == "vender"]
    return {"activo": True, "reglas": r, "filas": salida, "posiciones": filas, "sin_dato": sin_dato,
            "ordenes": bool(ventas or compras), "liberado": liberado, "efectivo_resultante": liberado - sum(
                c["peso_objetivo"] - c["peso_actual"] for c in compras),
            "cartera": {"vol_actual": vol_actual, "vol_despues": vol_final, "resultado_total": perdida_total,
                        "valor_total": total},
            "nota": "Reglas de control de pérdidas, no un pronóstico: reducen caídas grandes a cambio de vender a veces antes "
                    "de un rebote. Ninguna regla garantiza utilidad."}


def _minimo_reto(filas: list[dict], minimo: int, r: dict) -> None:
    """Si las ventas dejaran menos emisoras que el mínimo del Reto, se conserva una parte de las de menor volatilidad."""
    for f in sorted([f for f in filas if f["peso_objetivo"] == 0], key=lambda f: f.get("sigma_diaria") or 9):
        if len([x for x in filas if x["peso_objetivo"] > 0]) >= minimo:
            break
        f["peso_objetivo"] = min(f["peso_actual"], r["peso_minimo_reto"])
        f["motivos"].append(f"Se conserva {f['peso_objetivo']:.0%} para cumplir el mínimo de {minimo} emisoras del Reto.")


def lineas(g: dict) -> list[str]:
    """Resumen en lenguaje sencillo para el plan de Telegram."""
    if not g.get("activo"):
        return []
    c = g["cartera"]
    out = [f"🛡️ Gestión de riesgo: tu cartera va {c['resultado_total']:+.1%} desde el inicio; su volatilidad es "
           f"{c['vol_actual']:.0%} al año" + (f" y quedaría en {c['vol_despues']:.0%} con este plan." if g["ordenes"] else ".")]
    for f in g["posiciones"]:
        if f["peso_objetivo"] < f["peso_actual"] - 0.005:
            que = "VENDER TODO" if f["peso_objetivo"] == 0 else f"REDUCIR de {f['peso_actual']:.0%} a {f['peso_objetivo']:.0%}"
            out.append(f"  • {f['clave'].replace(' *', '')}: {que}. {f['motivos'][0]}")
    if not g["ordenes"]:
        out.append("  • Ninguna posición rompió su stop ni está en tendencia bajista: mantener es la decisión de riesgo.")
    return out
