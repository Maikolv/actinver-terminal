"""Validación fuera de muestra de las reglas de `gestion_riesgo` frente a mantener y a 1/N.

Simula carteras al azar del universo con historia. Sin fuga temporal: la señal usa cierres hasta el día t y la orden se
ejecuta al cierre de t+1, con comisión. Los parámetros son los vigentes (no se ajustan aquí) y la ventana termina antes
del 1-oct-2026: las reglas se escribieron el 5-nov-2026, así que toda la muestra es anterior a su diseño.
Límites: precios ajustados solo por splits (sin dividendos, igual para todas las variantes); la reinversión usa ocho
emisoras al azar como sustituto de la propuesta Markowitz (no se reproduce el optimizador); sin mínimo de emisoras del Reto.
Uso: `uv run python -m terminal.validacion_riesgo` (solo lee la base; escribe docs/evidencia/validacion-riesgo.json).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .gestion_riesgo import DIAS, REGLAS

COMISION = 0.00116
CORTE = "2026-09-30"
CONCENTRADA = np.array([0.46, 0.17, 0.14, 0.12, 0.06, 0.03, 0.015, 0.005])  # perfil de la cartera real del 3-nov
VARIANTES = {"reglas (efectivo)": {"stop", "tendencia", "concentracion", "volatilidad"},
             "reglas + reinversión": {"stop", "tendencia", "concentracion", "volatilidad", "reinversion"},
             "reglas suaves + reinversión": {"stop", "tendencia", "concentracion", "volatilidad", "reinversion", "suave"},
             "solo stop": {"stop"}, "solo tendencia": {"tendencia"}, "solo concentración": {"concentracion"},
             "solo volatilidad": {"volatilidad"}}


def senales(P: pd.DataFrame, r: dict = REGLAS) -> dict:
    """Las mismas cifras que `gestion_riesgo.indicadores`, para todas las fechas a la vez (cada fila solo mira atrás)."""
    sigma = P.pct_change(fill_method=None).rolling(r["ventana_sigma"]).std()
    sma_c, sma_l = P.rolling(r["sma_corta"]).mean(), P.rolling(r["sma_larga"]).mean()
    stop = P.rolling(r["ventana_maximo"]).max() * (1 - r["k_sigma"] * sigma)
    return {"stop": (P < stop) & (P < sma_l), "bajista": (P < sma_c) & (sma_c < sma_l),
            "alcista": (P > sma_l) & (sma_c > sma_l)}


def simular(P: pd.DataFrame, S: dict, ids: list[str], pesos: np.ndarray, i0: int, dias: int, activas: set[str],
            candidatas: list[str] | None = None, r: dict = REGLAS, rebalanceo: int = 0) -> dict:
    """Valor de la cartera de i0 a i0+dias. `activas` vacío = mantener; `rebalanceo` > 0 = volver a `pesos` cada n sesiones."""
    cols = list(dict.fromkeys(ids + (candidatas or [])))
    px = P[cols].values
    R = P[cols].pct_change(fill_method=None).fillna(0.0).values
    val = np.zeros(len(cols))
    val[: len(ids)] = pesos
    costo = px[i0].copy()
    efectivo, curva, pend = 1.0 - pesos.sum(), [1.0], None
    sig = {k: S[k][cols].values for k in S}
    for t in range(i0 + 1, i0 + dias + 1):
        val *= px[t] / px[t - 1]
        if pend is not None:  # orden decidida ayer, ejecutada al cierre de hoy
            total0 = val.sum() + efectivo
            for j, obj in sorted(pend.items(), key=lambda kv: kv[1] * total0 - val[kv[0]]):  # primero las ventas
                total = val.sum() + efectivo
                delta = obj * total - val[j]
                if delta > 0:
                    delta = min(delta, efectivo / (1 + COMISION))
                    costo[j] = px[t, j] if val[j] <= 0 else costo[j]
                efectivo -= delta + abs(delta) * COMISION
                val[j] += delta
            pend = None
        total = val.sum() + efectivo
        curva.append(total)
        if rebalanceo and (t - i0) % rebalanceo == 0:
            pend = {j: pesos[j] for j in range(len(ids))}
            continue
        if not activas:
            continue
        w = val / total
        obj = w.copy()
        for j in np.nonzero(w > 0)[0]:
            perdida = px[t, j] / costo[j] - 1
            if "stop" in activas and sig["stop"][t, j]:
                obj[j] = w[j] / 2 if "suave" in activas else 0.0
            elif "tendencia" in activas and sig["bajista"][t, j]:
                obj[j] = 0.0 if perdida <= -r["perdida_costo"] and "suave" not in activas else w[j] / 2
            if "concentracion" in activas and obj[j] > r["peso_max"]:
                obj[j] = r["peso_max"]
        if "volatilidad" in activas and obj.sum() > 0:
            vol = math.sqrt(max(obj @ (np.cov(R[t - 59: t + 1].T) * DIAS) @ obj, 0.0))
            if vol > r["vol_objetivo"]:
                obj *= r["vol_objetivo"] / vol
        vender = obj < w - 0.005
        orden = {int(j): float(obj[j]) for j in np.nonzero(vender)[0]}
        if "reinversion" in activas and candidatas:
            libre = efectivo / total + float((w - obj)[vender].sum())
            aptas = [j for j in range(len(ids), len(cols)) if sig["alcista"][t, j] and not vender[j]]
            if libre > 0.005 and aptas:
                for j in aptas:
                    nuevo = min(w[j] + libre / len(aptas), r["peso_max"])
                    if nuevo - w[j] > 0.005:
                        orden[j] = nuevo
        pend = orden or None
    c = np.array(curva)
    return {"rendimiento": float(c[-1] - 1), "caida_maxima": float((c / np.maximum.accumulate(c) - 1).min())}


def experimento(P: pd.DataFrame, dias: int, perfil: str, fechas: int = 80, carteras: int = 5, semilla: int = 7) -> dict:
    """Resultados por variante en `fechas` × `carteras` carteras al azar; diferencias pareadas contra mantener con
    intervalo bootstrap por fecha de inicio (las carteras de una misma fecha comparten mercado)."""
    rng = np.random.default_rng(semilla)
    P = P.loc[:CORTE].ffill(limit=3)
    S = senales(P)
    ultimo = len(P) - dias - 1
    filas = []
    for i0 in rng.choice(np.arange(260, ultimo), size=fechas, replace=False):
        completas = [c for c in P.columns if P[c].iloc[i0 - 259: i0 + dias + 1].notna().all()]
        for _ in range(carteras):
            sel = list(rng.choice(completas, size=16, replace=False))
            ids, cand = sel[:8], sel[8:]
            pesos = CONCENTRADA.copy() if perfil == "concentrada" else np.full(8, 1 / 8)
            fila = {"fecha": int(i0), "mantener": simular(P, S, ids, pesos, i0, dias, set()),
                    "1/N mensual": simular(P, S, ids, np.full(8, 1 / 8), i0, dias, set(), rebalanceo=21)}
            for nombre, activas in VARIANTES.items():
                fila[nombre] = simular(P, S, ids, pesos, i0, dias, activas, cand)
            filas.append(fila)
    fechas_u = sorted({f["fecha"] for f in filas})
    out = {}
    for nombre in ["mantener", "1/N mensual", *VARIANTES]:
        x = np.array([f[nombre]["rendimiento"] for f in filas])
        base = np.array([f["mantener"]["rendimiento"] for f in filas])
        d = pd.Series(x - base, index=[f["fecha"] for f in filas]).groupby(level=0).mean()
        boot = [d.loc[rng.choice(fechas_u, size=len(fechas_u))].mean() for _ in range(2000)]
        out[nombre] = {"media": float(x.mean()), "mediana": float(np.median(x)), "p10": float(np.quantile(x, 0.10)),
                       "caida_maxima_media": float(np.mean([f[nombre]["caida_maxima"] for f in filas])),
                       "gana_a_mantener": float((x > base).mean()), "dif_media": float(d.mean()),
                       "dif_ic95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]}
    return {"dias": dias, "perfil": perfil, "pruebas": len(filas), "desde": str(P.index[260].date()),
            "hasta": str(P.index[-1].date()), "variantes": out}


def correr(con, ajustes) -> list[dict]:
    from . import mercado
    ids = [i for i in mercado.instrumentos(con) if not i.startswith("FONDO:")]
    P = mercado.precios_mxn(con, ajustes, ids, ajustados="splits")
    P = P[[c for c in P.columns if P[c].notna().sum() >= 500]]
    return [experimento(P, dias, perfil) for perfil in ("concentrada", "pareja") for dias in (30, 126)]


if __name__ == "__main__":
    from . import db
    from .config import cargar_ajustes
    res = correr(db.conectar(), cargar_ajustes())
    destino = Path("docs/evidencia/validacion-riesgo.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    for e in res:
        print(f"\n{e['perfil']} · {e['dias']} sesiones · {e['pruebas']} carteras ({e['desde']} a {e['hasta']})")
        print(f"{'variante':24}{'media':>8}{'mediana':>9}{'p10':>8}{'caída':>8}{'gana':>7}{'dif':>8}  IC95")
        for n, v in e["variantes"].items():
            print(f"{n:24}{v['media']:>8.1%}{v['mediana']:>9.1%}{v['p10']:>8.1%}{v['caida_maxima_media']:>8.1%}"
                  f"{v['gana_a_mantener']:>7.0%}{v['dif_media']:>+8.1%}  [{v['dif_ic95'][0]:+.1%}, {v['dif_ic95'][1]:+.1%}]")
