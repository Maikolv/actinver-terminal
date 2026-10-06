"""Serie fuera de muestra de cada combinación (panel dinámico, causal) y su referencia 1/N, por lotes y reanudable.

Cada combinación se guarda en `<directorio>/combos/<clave>.npz` al terminar. Una corrida interrumpida retoma
donde quedó: las combinaciones ya guardadas con la misma huella de preregistro no se recalculan.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .. import optimizador as op
from . import diseno as dz


def pliegues(R: pd.DataFrame, historia: int, inicio: int = dz.INICIO_PRUEBA, paso: int = dz.PASO):
    """(i_inicio_prueba, columnas, X_entrenamiento, X_prueba). Entrenamiento = las `historia` sesiones ANTERIORES a la
    prueba (nunca incluye la prueba). Entran los activos con entrenamiento completo y dato el primer día de prueba."""
    s = inicio
    while s < len(R):
        train, test = R.iloc[s - historia:s], R.iloc[s:s + paso]
        cols = [c for c in R.columns if train[c].notna().all() and pd.notna(test[c].iloc[0])]
        if len(cols) >= dz.MIN_ACTIVOS:
            yield s, cols, train[cols], test[cols].fillna(0.0)
        s += paso


def evaluar(combo: dict, tipo: str, perfil: dict, ajustes, el: dict, R: pd.DataFrame, costos: pd.Series,
            usd: set[str], ajustar=None) -> dict:
    """Pesos por pliegue con los parámetros de la combinación; rendimiento bruto, costo base y giro por fecha.
    `ajustar(cols, X)` permite inyectar el modelo (pruebas); por omisión, el optimizador de la terminal."""
    if ajustar is None:
        base = float(ajustes["perfiles"][perfil["riesgo"]]["aversion_riesgo"])
        p_mod = {**perfil, "max_peso_activo": combo["tope"]}

        def ajustar(cols, X):
            m = op._modelo(tipo, p_mod, ajustes, [el[c] for c in cols], {}, aversion_mult=combo["aversion"] / base,
                           lente="ajuste").fit(X)
            o = m.named_steps["optimizacion"]
            return pd.Series(o.weights_, index=list(o.feature_names_in_))
    banda = float(ajustes["optimizacion"]["banda_rebalanceo_pp"]) / 100
    n = len(R)
    bruto = {k: np.zeros(n) for k in ("estrategia", "iguales")}
    costo = {k: np.zeros(n) for k in ("estrategia", "iguales")}
    giro = {k: np.zeros(n) for k in ("estrategia", "iguales")}
    giro_sic = {k: np.zeros(n) for k in ("estrategia", "iguales")}
    activo = np.zeros(n, dtype=bool)
    prev = {"estrategia": pd.Series(dtype=float), "iguales": pd.Series(dtype=float)}
    pesos, fallos = [], 0
    for s, cols, Xtr, Xte in pliegues(R, combo["historia"]):
        try:
            w_e = ajustar(cols, Xtr).reindex(cols).fillna(0.0)
        except Exception:  # noqa: BLE001 - un pliegue sin solución se cuenta (y se informa), no se oculta
            fallos += 1
            continue
        for k, w in (("estrategia", w_e), ("iguales", pd.Series(1.0 / len(cols), index=cols))):
            p = prev[k].reindex(cols).fillna(0.0)
            if len(prev[k]):  # misma regla que la terminal: no mover pesos por diferencias menores a la banda
                w = w.where((w - p).abs() >= banda, p)
                w = w / w.sum() if w.sum() > 0 else w
            todos = w.index.union(prev[k].index)
            d = (w.reindex(todos).fillna(0) - prev[k].reindex(todos).fillna(0)).abs()
            sl = slice(s, s + len(Xte))
            bruto[k][sl] = Xte.mul(w, axis=1).sum(axis=1).to_numpy()
            costo[k][s] = float((d * costos.reindex(todos).fillna(costos.mean())).sum())
            giro[k][s] = float(d.sum())
            giro_sic[k][s] = float(d[[c for c in todos if c in usd]].sum())
            prev[k] = w
            if k == "estrategia":
                pesos.append((s, w[w > 1e-6].round(5).to_dict()))
        activo[s:s + len(Xte)] = True
    return {"bruto": bruto, "costo": costo, "giro": giro, "giro_sic": giro_sic, "activo": activo, "pesos": pesos,
            "fallos": fallos}


def guardar(ruta: Path, combo: dict, r: dict, huella: str, segundos: float) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ruta, activo=r["activo"], **{f"{v}_{k}": r[v][k].astype(np.float64)
                                                    for v in ("bruto", "costo", "giro", "giro_sic") for k in ("estrategia", "iguales")})
    ruta.with_suffix(".json").write_text(json.dumps({"combo": combo, "huella": huella, "pesos": r["pesos"], "fallos": r["fallos"],
                                                     "segundos": round(segundos, 2)}), encoding="utf-8")


def cargar(ruta: Path) -> dict:
    z = np.load(ruta)
    meta = json.loads(ruta.with_suffix(".json").read_text(encoding="utf-8"))
    r = {v: {k: z[f"{v}_{k}"] for k in ("estrategia", "iguales")} for v in ("bruto", "costo", "giro", "giro_sic")}
    return {**r, "activo": z["activo"], **meta}


def correr(directorio: Path, combos: list[dict], huella: str, tipo, perfil, ajustes, el, R, costos, usd,
           progreso=print) -> dict:
    """Calcula las combinaciones que falten (las ya guardadas con la misma huella se reutilizan)."""
    hechas = nuevas = 0
    t0 = time.time()
    for c in combos:
        ruta = directorio / "combos" / f"{c['clave']}.npz"
        if ruta.exists() and json.loads(ruta.with_suffix(".json").read_text(encoding="utf-8")).get("huella") == huella:
            hechas += 1
            continue
        t = time.time()
        guardar(ruta, c, evaluar(c, tipo, perfil, ajustes, el, R, costos, usd), huella, time.time() - t)
        nuevas += 1
        progreso(f"  {tipo} {c['clave']:<22} {nuevas + hechas}/{len(combos)} · {time.time() - t:.1f} s")
    return {"reutilizadas": hechas, "calculadas": nuevas, "segundos": round(time.time() - t0, 1)}
