"""Compara las configuraciones de validación PRERREGISTRADAS en docs/historia-y-horizonte.md (V0–V3).

Walk-forward con los mismos modelos y lentes de la terminal, banda de rebalanceo, costos del Reto y la referencia 1/N
sobre el mismo universo de cada pliegue. Universo dinámico (V1–V3): en cada pliegue entran los elegibles con el
entrenamiento completo y dato el primer día de la prueba; un hueco posterior en la prueba cuenta como 0 (efectivo). Así
no se exige saber de antemano que el instrumento seguirá cotizando.

Uso: uv run python scripts/comparar_historia.py [--salida data/referencias/historia.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal import db, servicios  # noqa: E402
from terminal import optimizador as op
from terminal.config import cargar_ajustes  # noqa: E402

CONFIGS = {"V0 vigente (común, 168/21)": ("comun", 168, 21), "V1 panel dinámico 168/21": ("dinamico", 168, 21),
           "V2 panel dinámico 252/21": ("dinamico", 252, 21), "V3 panel dinámico 504/21": ("dinamico", 504, 21)}
COMBOS = [("acciones", "rendimiento"), ("acciones", "ajuste"), ("mixta", "rendimiento"), ("mixta", "ajuste")]
DIAS, BLOQUE, B, SEMILLA = 252, 21, 1000, 20261113
MIN_ACTIVOS_PLIEGUE = 10


def pliegues(R: pd.DataFrame, modo: str, tr: int, te: int):
    """(fecha_inicio_prueba, columnas, X_entrenamiento, X_prueba) en orden cronológico, sin solapar pruebas."""
    s = tr
    while s < len(R):
        train, test = R.iloc[s - tr:s], R.iloc[s:s + te]
        if modo == "comun":
            cols = list(R.columns)
        else:
            cols = [c for c in R.columns if train[c].notna().all() and pd.notna(test[c].iloc[0])]
        if len(cols) >= MIN_ACTIVOS_PLIEGUE:
            yield test.index[0], cols, train[cols], test[cols].fillna(0.0)
        s += te


def correr(tipo, lente, modo, tr, te, perfil, ajustes, el_l, R):
    el = {e["id"]: e for e in el_l}
    costos = pd.Series({c: op.costo_unitario(el[c], ajustes) for c in R.columns})
    banda = float(ajustes["optimizacion"]["banda_rebalanceo_pp"]) / 100
    out = {"estrategia": [], "iguales": []}
    prev = {"estrategia": pd.Series(dtype=float), "iguales": pd.Series(dtype=float)}
    folds, gana = 0, 0
    for inicio, cols, Xtr, Xte in pliegues(R, modo, tr, te):
        sub = [el[c] for c in cols]
        try:
            m = op._modelo(tipo, perfil, ajustes, sub, {}, lente=lente).fit(Xtr)
            o = m.named_steps["optimizacion"]
            w_e = pd.Series(o.weights_, index=list(o.feature_names_in_)).reindex(cols).fillna(0.0)
        except Exception as e:  # noqa: BLE001 - se informa
            print(f"  pliegue {inicio.date()} sin solución: {str(e)[:80]}", flush=True)
            continue
        w_n = pd.Series(1.0 / len(cols), index=cols)
        r_fold = {}
        for k, w in (("estrategia", w_e), ("iguales", w_n)):
            p = prev[k].reindex(cols).fillna(0.0)
            if len(prev[k]):  # misma regla que la terminal: no mover pesos por diferencias menores a la banda
                w = w.where((w - p).abs() >= banda, p)
                w = w / w.sum() if w.sum() > 0 else w
            todos = w.index.union(prev[k].index)
            giro = (w.reindex(todos).fillna(0) - prev[k].reindex(todos).fillna(0)).abs()
            costo = float((giro * costos.reindex(todos).fillna(costos.mean())).sum())
            r = Xte.mul(w, axis=1).sum(axis=1)
            r.iloc[0] -= costo
            out[k].append(r)
            r_fold[k] = float((1 + r).prod() - 1)
            prev[k] = w
        folds += 1
        gana += r_fold["estrategia"] > r_fold["iguales"]
    if not folds:
        return None
    return pd.concat(out["estrategia"]), pd.concat(out["iguales"]), folds, gana


def metricas(r: pd.Series) -> dict:
    n = len(r)
    acum = (1 + r).cumprod()
    return {"sesiones": n, "desde": str(r.index[0].date()), "hasta": str(r.index[-1].date()),
            "rend_anual": float(acum.iloc[-1] ** (DIAS / n) - 1), "vol_anual": float(r.std() * math.sqrt(DIAS)),
            "sharpe": float(r.mean() / r.std() * math.sqrt(DIAS)) if r.std() > 0 else None,
            "max_caida": float((acum / acum.cummax() - 1).min())}


def ic_exceso(d: pd.Series) -> list[float]:
    """IC 90 % del exceso anualizado (media diaria × 252) por bootstrap de bloques de 21 sesiones."""
    v = d.to_numpy()
    nb = max(len(v) // BLOQUE, 1)
    rng = np.random.default_rng(SEMILLA)
    medias = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, min(s + BLOQUE, len(v))) for s in rng.integers(0, max(len(v) - BLOQUE, 1), nb)])
        medias.append(v[idx].mean() * DIAS)
    return [float(np.quantile(medias, 0.05)), float(np.quantile(medias, 0.95))]


def periodos(r: pd.Series, d: pd.Series) -> dict:
    v = (1 + r).rolling(63).apply(np.prod, raw=True) - 1
    x = d.rolling(63).sum()
    if v.dropna().empty:
        return {}
    return {"mejor_63": {"hasta": str(v.idxmax().date()), "rend": float(v.max())},
            "peor_63": {"hasta": str(v.idxmin().date()), "rend": float(v.min())},
            "mejor_exceso_63": {"hasta": str(x.idxmax().date()), "exceso": float(x.max())},
            "peor_exceso_63": {"hasta": str(x.idxmin().date()), "exceso": float(x.min())}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="data/referencias/historia_ventanas.json")
    args = ap.parse_args()
    ajustes = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con, ajustes)
    perfil = op.perfil_efectivo(servicios.perfil_actual(con, ajustes))
    res = {"preregistro": "docs/historia-y-horizonte.md", "horizonte_decision_anios": perfil.get("horizonte_anios"), "filas": []}
    series = {}
    for tipo, lente in COMBOS:
        el_l, _, precios = op.universo(con, ajustes, perfil, tipo, None)
        ids = [e["id"] for e in el_l]
        R_todo = precios[ids].ffill(limit=3).pct_change(fill_method=None)
        R_comun = op.rendimientos(precios, ids)
        for nombre, (modo, tr, te) in CONFIGS.items():
            t0 = time.time()
            R = R_comun if modo == "comun" else R_todo.loc[R_todo.notna().sum(axis=1) >= MIN_ACTIVOS_PLIEGUE]
            r = correr(tipo, lente, modo, tr, te, perfil, ajustes, el_l, R)
            if r is None:
                res["filas"].append({"combo": f"{tipo}_{lente}", "config": nombre, "estado": "sin pliegues"})
                continue
            est, ig, folds, gana = r
            d = (est - ig).dropna()
            series[(f"{tipo}_{lente}", nombre)] = (est, ig)
            fila = {"combo": f"{tipo}_{lente}", "config": nombre, "pliegues": folds, "pliegues_gana_1N": gana,
                    "estrategia": metricas(est), "iguales": metricas(ig), "exceso_anual": float(d.mean() * DIAS),
                    "exceso_ic90": ic_exceso(d), **periodos(est, d), "segundos": round(time.time() - t0)}
            res["filas"].append(fila)
            print(f"{tipo}_{lente:<12} {nombre:<28} ses {fila['estrategia']['sesiones']:>4} pl {folds:>3} "
                  f"rend {fila['estrategia']['rend_anual']:+.1%} 1/N {fila['iguales']['rend_anual']:+.1%} exceso "
                  f"{fila['exceso_anual']:+.1%} IC [{fila['exceso_ic90'][0]:+.1%}, {fila['exceso_ic90'][1]:+.1%}] "
                  f"({fila['segundos']} s)", flush=True)
    # periodo común: las fechas fuera de muestra de V0 (las más recientes)
    v0 = list(CONFIGS)[0]
    for (combo, nombre), (est, ig) in series.items():
        if (combo, v0) not in series:
            continue
        fechas = series[(combo, v0)][0].index
        e2, i2 = est.reindex(fechas).dropna(), ig.reindex(fechas).dropna()
        d0 = (series[(combo, v0)][0] - est.reindex(fechas)).dropna()
        res.setdefault("periodo_comun", []).append({
            "combo": combo, "config": nombre, "sesiones": len(e2), "rend_acum": float((1 + e2).prod() - 1),
            "rend_acum_1N": float((1 + i2).prod() - 1),
            "dif_vs_V0_anual": float(-d0.mean() * DIAS) if len(d0) else 0.0,
            "dif_vs_V0_ic90": [-x for x in reversed(ic_exceso(d0))] if len(d0) > BLOQUE else None})
    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("guardado en", args.salida)


if __name__ == "__main__":
    main()
