"""Validación extendida (V1 del preregistro de docs/historia-y-horizonte.md): walk-forward con panel dinámico.

La validación de la propuesta usaba solo la historia COMÚN a todos los elegibles (255 sesiones: el plan gratuito de
EODHD da un año de la BMV), lo que dejaba 84–87 sesiones fuera de muestra. Aquí cada pliegue usa los elegibles con el
entrenamiento completo y dato el primer día de la prueba; un hueco posterior en la prueba cuenta como 0 (efectivo).
Mismo modelo y lente, banda de rebalanceo, costos del Reto y referencia 1/N sobre el mismo universo de cada pliegue.

No cambia pesos ni puntuación: es evidencia. Solo dice «ventaja demostrada» si el exceso frente a 1/N tiene su IC 90 %
(bootstrap de bloques de 21 sesiones) entero por encima de cero.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

ENTRENAMIENTO, PRUEBA = 168, 21          # V1 adoptada (preregistro 6-oct-2026)
MIN_ACTIVOS_PLIEGUE = 10
DIAS, BLOQUE, B, SEMILLA = 252, 21, 1000, 20261113


def pliegues(R: pd.DataFrame, tr: int = ENTRENAMIENTO, te: int = PRUEBA, comun: bool = False):
    """(columnas, X_entrenamiento, X_prueba) en orden cronológico, sin solapar pruebas."""
    s = tr
    while s < len(R):
        train, test = R.iloc[s - tr:s], R.iloc[s:s + te]
        cols = list(R.columns) if comun else [c for c in R.columns if train[c].notna().all() and pd.notna(test[c].iloc[0])]
        if len(cols) >= MIN_ACTIVOS_PLIEGUE:
            yield cols, train[cols], test[cols].fillna(0.0)
        s += te


def walk_forward(ajustar, R: pd.DataFrame, costos: pd.Series, banda: float, tr: int = ENTRENAMIENTO, te: int = PRUEBA,
                 comun: bool = False) -> dict | None:
    """`ajustar(cols, X_train) -> pd.Series de pesos`. Devuelve series netas de costos de la estrategia y de 1/N."""
    out = {"estrategia": [], "iguales": []}
    prev = {"estrategia": pd.Series(dtype=float), "iguales": pd.Series(dtype=float)}
    folds, gana, fallos = 0, 0, 0
    for cols, Xtr, Xte in pliegues(R, tr, te, comun):
        try:
            w_e = ajustar(cols, Xtr).reindex(cols).fillna(0.0)
        except Exception:  # noqa: BLE001 - un pliegue sin solución se cuenta y se omite
            fallos += 1
            continue
        r_fold = {}
        for k, w in (("estrategia", w_e), ("iguales", pd.Series(1.0 / len(cols), index=cols))):
            p = prev[k].reindex(cols).fillna(0.0)
            if len(prev[k]):  # misma regla que la terminal: no mover pesos por diferencias menores a la banda
                w = w.where((w - p).abs() >= banda, p)
                w = w / w.sum() if w.sum() > 0 else w
            todos = w.index.union(prev[k].index)
            giro = (w.reindex(todos).fillna(0) - prev[k].reindex(todos).fillna(0)).abs()
            r = Xte.mul(w, axis=1).sum(axis=1)
            r.iloc[0] -= float((giro * costos.reindex(todos).fillna(costos.mean())).sum())
            out[k].append(r)
            r_fold[k] = float((1 + r).prod() - 1)
            prev[k] = w
        folds += 1
        gana += r_fold["estrategia"] > r_fold["iguales"]
    if not folds:
        return None
    return {"estrategia": pd.concat(out["estrategia"]), "iguales": pd.concat(out["iguales"]), "pliegues": folds,
            "pliegues_gana_1N": gana, "pliegues_sin_solucion": fallos}


def metricas(r: pd.Series) -> dict:
    n = len(r)
    acum = (1 + r).cumprod()
    return {"sesiones": n, "desde": str(r.index[0].date()), "hasta": str(r.index[-1].date()),
            "rend_anual": float(acum.iloc[-1] ** (DIAS / n) - 1), "vol_anual": float(r.std() * math.sqrt(DIAS)),
            "sharpe": float(r.mean() / r.std() * math.sqrt(DIAS)) if r.std() > 0 else None,
            "max_caida": float((acum / acum.cummax() - 1).min())}


def ic_exceso(d: pd.Series) -> list[float]:
    """IC 90 % del exceso anualizado (media diaria × 252), bootstrap de bloques de 21 sesiones."""
    v = d.to_numpy()
    nb = max(len(v) // BLOQUE, 1)
    rng = np.random.default_rng(SEMILLA)
    medias = [v[np.concatenate([np.arange(s, min(s + BLOQUE, len(v)))
                                for s in rng.integers(0, max(len(v) - BLOQUE, 1), nb)])].mean() * DIAS for _ in range(B)]
    return [float(np.quantile(medias, 0.05)), float(np.quantile(medias, 0.95))]


def resumen(wf: dict | None) -> dict | None:
    if not wf:
        return None
    est, ig = wf["estrategia"], wf["iguales"]
    d = (est - ig).dropna()
    ic = ic_exceso(d)
    return {"configuracion": f"panel dinámico {ENTRENAMIENTO}/{PRUEBA} (V1, preregistro 6-oct-2026)",
            "estrategia": metricas(est), "iguales": metricas(ig), "pliegues": wf["pliegues"],
            "pliegues_gana_1N": wf["pliegues_gana_1N"], "pliegues_sin_solucion": wf["pliegues_sin_solucion"],
            "exceso_anual": float(d.mean() * DIAS), "exceso_ic90": ic,
            "veredicto": "VENTAJA DEMOSTRADA frente a 1/N" if ic[0] > 0 else "SIN VENTAJA DEMOSTRADA frente a 1/N"}
