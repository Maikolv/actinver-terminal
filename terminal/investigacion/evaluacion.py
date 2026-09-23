"""Experimento reproducible: selección con walk-forward (solo entrenamiento) → validación → prueba final intacta.

1. Walk-forward purgado dentro del entrenamiento elige α de cada variante (filtro de correlación + Ridge, solo Ridge,
   PCA + Ridge). Imputación, escalado, filtro y PCA se ajustan dentro de cada pliegue con su entrenamiento.
2. La validación elige la variante y calibra el intervalo 10–90 % con sus residuos (conformal por partición).
3. La prueba se evalúa UNA vez con el modelo ya fijado (reentrenado con entrenamiento + validación purgados).
   Si ya existe un experimento con los mismos cortes y datos y OTRA configuración, el resultado se marca
   «prueba_ya_vista»: no sirve para elegir modelo.
4. Referencias simples: sin cambio (0), retorno histórico reciente (media de 60 sesiones × H) y una regla predefinida
   (momento de 20 sesiones solo si el precio está sobre su media de 50).
5. Si el modelo no supera a TODAS las referencias fuera de muestra (error y resultado neto de costos), no se emite
   recomendación de cambio.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .. import __version__, reto
from . import datos, division
from .seleccion import FiltroCorrelacion

VARIANTES = ("filtro_correlacion", "ridge", "pca")
REFERENCIAS = ("sin_cambio", "historico_reciente", "regla_simple")
CONFIG_BASE = {"proporciones": [0.70, 0.15, 0.15], "embargo_min": 0, "umbral_correlacion": 0.95,
               "alfas": [1.0, 10.0, 100.0, 1000.0], "pliegues": 4, "top_k": 5, "semilla": 20261113}


def modelo(variante: str, alfa: float, umbral: float, semilla: int) -> Pipeline:
    pasos = [("imputar", SimpleImputer(strategy="median")), ("escalar", StandardScaler())]
    if variante == "filtro_correlacion":
        pasos.append(("filtro", FiltroCorrelacion(umbral, datos.VARIABLES)))
    elif variante == "pca":
        pasos.append(("pca", PCA(n_components=0.95, svd_solver="full", random_state=semilla)))
    pasos.append(("ridge", Ridge(alpha=alfa)))
    return Pipeline(pasos).set_output(transform="pandas")


def referencias(df: pd.DataFrame, H: int) -> dict[str, np.ndarray]:
    return {"sin_cambio": np.zeros(len(df)),
            "historico_reciente": (df["r60"].fillna(0) / 60 * H).to_numpy(),
            "regla_simple": np.where(df["dist_ma50"].fillna(0) > 0, df["r20"].fillna(0) / 20 * H, 0.0)}


def _X(df):
    return df[datos.VARIABLES]


def _mse(y, p):
    return float(np.mean((np.asarray(y) - np.asarray(p)) ** 2))


def estrategia(df: pd.DataFrame, pred: np.ndarray, H: int, k: int, costo: float, mantener: bool = False) -> dict:
    """Top-k por pronóstico (> 0), pesos iguales, rebalanceo cada H fechas sin traslape. Neto de comisión + IVA."""
    d = df[["fecha", "instrumento_id", "y"]].assign(pred=pred)
    fechas = sorted(d["fecha"].unique())[::H]
    w_prev: dict[str, float] = {}
    valor, rot_total, n = 1.0, 0.0, 0
    for f in fechas:
        g = d[d["fecha"] == f]
        if mantener and w_prev:
            w = {i: w_prev.get(i, 0.0) for i in w_prev if i in set(g["instrumento_id"])}
        elif mantener:
            sel = g.sort_values("instrumento_id").head(k)
            w = {i: 1 / len(sel) for i in sel["instrumento_id"]} if len(sel) else {}
        else:
            sel = g[g["pred"] > 0].nlargest(k, "pred")
            w = {i: 1 / k for i in sel["instrumento_id"]}
        rot = sum(abs(w.get(i, 0) - w_prev.get(i, 0)) for i in set(w) | set(w_prev))
        r = sum(w[i] * (np.exp(float(g.loc[g["instrumento_id"] == i, "y"].iloc[0])) - 1) for i in w)
        valor *= (1 + r - rot * costo)
        rot_total += rot
        n += 1
        w_prev = w
    return {"resultado_neto": round(float(valor) - 1, 6), "rotacion_media": round(rot_total / max(n, 1), 4), "rebalanceos": n}


def metricas(df: pd.DataFrame, pred: np.ndarray, residuos_val: np.ndarray, H: int, k: int, costo: float,
             nombre: str) -> dict:
    y = df["y"].to_numpy()
    q10, q90 = np.quantile(residuos_val, [0.10, 0.90]) if len(residuos_val) else (np.nan, np.nan)
    cob = float(np.mean((y >= pred + q10) & (y <= pred + q90))) if len(y) else None
    res_ord = np.sort(residuos_val)
    prob = 1 - np.searchsorted(res_ord, -pred, side="right") / max(len(res_ord), 1)  # P(y > 0) con residuos empíricos
    brier = float(np.mean((prob - (y > 0)) ** 2))
    no_cero = pred != 0
    meses = pd.Series(pd.to_datetime(df["fecha"]).dt.to_period("M").astype(str).to_numpy())
    err = pd.DataFrame({"m": meses, "e": (y - pred) ** 2, "e0": y ** 2}).groupby("m").mean()
    return {"modelo": nombre, "n": int(len(y)), "mse": _mse(y, pred), "mae": float(np.mean(np.abs(y - pred))),
            "acierto_direccion": float(np.mean(np.sign(pred[no_cero]) == np.sign(y[no_cero]))) if no_cero.any() else None,
            "r2_vs_sin_cambio": float(1 - _mse(y, pred) / _mse(y, 0 * y)) if _mse(y, 0 * y) > 0 else None,
            "cobertura_intervalo_80": cob, "brier_prob_subida": brier,
            "meses_mejor_que_sin_cambio": f"{int((err['e'] < err['e0']).sum())}/{len(err)}",
            **estrategia(df, pred, H, k, costo, mantener=(nombre == "sin_cambio"))}


def _huella(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def investigar(con: sqlite3.Connection, demo: bool, H: int, T: pd.Timestamp | None = None, config: dict | None = None,
               guardar: bool = True) -> dict:
    cfg = {**CONFIG_BASE, **(config or {}), "H": H}
    T = pd.Timestamp(T if T is not None else datetime.now(UTC))
    T = T.tz_localize("UTC") if T.tzinfo is None else T.tz_convert("UTC")
    precios = datos.precios_hasta(con, demo, T)
    panel = datos.etiquetados_hasta(datos.construir_panel(precios, H), T)
    if panel.empty:
        return {"estado": "sin_datos", "H": H, "mensaje": "No hay historia suficiente con available_at <= T para investigar."}
    try:
        cortes = division.dividir(panel["fecha"].tolist(), H, tuple(cfg["proporciones"]), cfg["embargo_min"])
    except ValueError as e:
        return {"estado": "sin_datos", "H": H, "mensaje": str(e)}
    m_ent, m_val, m_pru = (division.mascara(panel, cortes, n) for n in ("entrenamiento", "validacion", "prueba"))
    ent, val, pru = panel[m_ent], panel[m_val], panel[m_pru]
    semilla, umbral = int(cfg["semilla"]), float(cfg["umbral_correlacion"])

    # 1) walk-forward dentro del entrenamiento
    fechas_ent = sorted(ent["fecha"].unique())
    pliegues = division.pliegues_walk_forward(fechas_ent, H, cfg["pliegues"])
    wf, filtros = {}, []
    for v in VARIANTES:
        for a in cfg["alfas"]:
            errores = []
            for p in pliegues:
                me, mv = division.mascaras_pliegue(ent, p)
                if me.sum() < 50 or mv.sum() < 10:
                    continue
                mdl = modelo(v, a, umbral, semilla).fit(_X(ent[me]), ent.loc[me, "y"])
                errores.append(_mse(ent.loc[mv, "y"], mdl.predict(_X(ent[mv]))))
                if v == "filtro_correlacion" and a == cfg["alfas"][0]:
                    filtros.append({"pliegue_hasta": p["fin_entrenamiento"], "eliminadas": mdl.named_steps["filtro"].eliminadas_})
            wf[(v, a)] = float(np.mean(errores)) if errores else np.inf
    alfa = {v: min(cfg["alfas"], key=lambda a, v=v: wf[(v, a)]) for v in VARIANTES}

    # 2) validación: elegir variante y calibrar intervalos
    val_mse, ajustados = {}, {}
    for v in VARIANTES:
        mdl = modelo(v, alfa[v], umbral, semilla).fit(_X(ent), ent["y"])
        ajustados[v] = mdl
        val_mse[v] = _mse(val["y"], mdl.predict(_X(val)))
    elegido = min(VARIANTES, key=lambda v: val_mse[v])
    residuos = {"modelo": val["y"].to_numpy() - ajustados[elegido].predict(_X(val))}
    for nombre, pr in referencias(val, H).items():
        residuos[nombre] = val["y"].to_numpy() - pr

    # 3) prueba final: modelo fijado, reentrenado con entrenamiento + validación purgados contra la prueba
    m_ev = (panel["fecha"] <= cortes.fechas[cortes.validacion[1] - 1]) & panel["fecha_fin_etiqueta"].notna() & (
        panel["fecha_fin_etiqueta"] < cortes.fechas[cortes.prueba[0]])
    final = modelo(elegido, alfa[elegido], umbral, semilla).fit(_X(panel[m_ev]), panel.loc[m_ev, "y"])
    costo = reto.costo_operacion() or 0.00116
    k = int(cfg["top_k"])
    tabla = [metricas(pru, final.predict(_X(pru)), residuos["modelo"], H, k, costo, f"modelo ({elegido})")]
    for nombre, pr in referencias(pru, H).items():
        tabla.append(metricas(pru, pr, residuos[nombre], H, k, costo, nombre))
    mod, refs = tabla[0], tabla[1:]
    supera_error = mod["mse"] < min(r["mse"] for r in refs)
    supera_neto = mod["resultado_neto"] > max(r["resultado_neto"] for r in refs)

    huella_datos = _huella([demo, len(panel), cortes.a_dict(), round(float(panel["y"].sum()), 8)])
    config_reg = {k2: v2 for k2, v2 in cfg.items()}
    previos = con.execute("SELECT huella_config FROM experimentos WHERE huella_datos=?", (huella_datos,)).fetchall()
    prueba_ya_vista = any(r[0] != _huella(config_reg) for r in previos)
    res = {
        "estado": "ok", "H": H, "L": datos.L_MAX, "hora_corte": T.isoformat(), "demo": demo,
        "datos": "SINTÉTICOS (demostración): no dicen nada del mercado real" if demo else "reales",
        "n_ejemplos": {"entrenamiento": int(m_ent.sum()), "validacion": int(m_val.sum()), "prueba": int(m_pru.sum())},
        "purgados": {n: division.purgadas(panel, cortes, n) for n in ("entrenamiento", "validacion")},
        "cortes": cortes.a_dict(), "pliegues_walk_forward": pliegues,
        "walk_forward_mse": {f"{v}|{a}": (None if not np.isfinite(e) else e) for (v, a), e in wf.items()},
        "alfa_por_variante": alfa, "validacion_mse": val_mse, "variante_elegida": elegido,
        "filtro_correlacion_por_pliegue": filtros,
        "variables_eliminadas_final": (final.named_steps["filtro"].eliminadas_ if elegido == "filtro_correlacion" else []),
        "prueba": tabla, "supera_referencias": bool(supera_error and supera_neto),
        "recomendacion_permitida": bool(supera_error and supera_neto),
        "conclusion": ("El modelo supera a las tres referencias fuera de muestra en error y resultado neto de costos."
                       if supera_error and supera_neto else
                       "El modelo NO supera a las referencias simples fuera de muestra: no se emite recomendación de cambio."),
        "correlacion_activos_entrenamiento": datos.correlacion_activos(
            precios, cortes.fechas[cortes.entrenamiento[0]:cortes.entrenamiento[1]]),
        "prueba_ya_vista": prueba_ya_vista,
        "aviso": ("El embargo y la purga evitan fugas de información; no garantizan que los pronósticos acierten. "
                  "Los intervalos son estimaciones con error histórico."),
        "version_codigo": __version__, "semilla": semilla, "huella_config": _huella(config_reg)[:16],
        "huella_datos": huella_datos[:16],
    }
    if guardar:
        con.execute("INSERT INTO experimentos (ts, configuracion, huella_config, huella_datos, semilla, cortes, resultados, "
                    "prueba_ya_vista, version_codigo) VALUES (?,?,?,?,?,?,?,?,?)",
                    (datetime.now(UTC).isoformat(timespec="seconds"), json.dumps(config_reg, default=str), _huella(config_reg),
                     huella_datos, semilla, json.dumps(cortes.a_dict()), json.dumps(res, default=str), int(prueba_ya_vista),
                     __version__))
        con.commit()
    res["_modelo"] = final
    res["_residuos"] = residuos["modelo"]
    return res


def ultimo(con: sqlite3.Connection, H: int, demo: bool) -> dict | None:
    for (txt,) in con.execute("SELECT resultados FROM experimentos ORDER BY id DESC LIMIT 50"):
        r = json.loads(txt)
        if r.get("H") == H and r.get("demo") == demo:
            return r
    return None
