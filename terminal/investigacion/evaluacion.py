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
    pasos = [("imputar", SimpleImputer(strategy="median", keep_empty_features=True)), ("escalar", StandardScaler())]
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


SIN_VENTAJA = "SIN VENTAJA DEMOSTRADA"
MULT_COSTOS = (0.0, 1.0, 2.0, 5.0)


def estrategia(df: pd.DataFrame, pred: np.ndarray, H: int, k: int, costo: float, mantener: bool = False,
               iguales: bool = False) -> dict:
    """Top-k por pronóstico (> 0), pesos iguales, rebalanceo cada H fechas sin traslape. Neto de comisión + IVA.
    `mantener`: compra inicial de k emisoras y se conserva. `iguales`: todas las emisoras con el mismo peso."""
    d = df[["fecha", "instrumento_id", "y"]].assign(pred=pred)
    fechas = sorted(d["fecha"].unique())[::H]
    w_prev: dict[str, float] = {}
    valor, rot_total, n = 1.0, 0.0, 0
    brutos, rots, expos = [], [], []
    for f in fechas:
        g = d[d["fecha"] == f]
        if iguales:
            w = {i: 1 / len(g) for i in g["instrumento_id"]} if len(g) else {}
        elif mantener and w_prev:
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
        brutos.append(r)
        rots.append(rot)
        expos.append(sum(w.values()))
        rot_total += rot
        n += 1
        w_prev = w
    br, ro = np.array(brutos), np.array(rots)
    curva = np.cumprod(1 + br - ro * costo) if n else np.array([1.0])
    caida = float(np.min(curva / np.maximum.accumulate(curva) - 1)) if n else 0.0
    sensibilidad = {f"x{m:g}": round(float(np.prod(1 + br - ro * costo * m)) - 1, 6) for m in MULT_COSTOS} if n else {}
    return {"resultado_neto": round(float(valor) - 1, 6), "rotacion_media": round(rot_total / max(n, 1), 4), "rebalanceos": n,
            "caida_maxima": round(caida, 6), "exposicion_media": round(float(np.mean(expos)) if expos else 0.0, 4),
            "sensibilidad_costos": sensibilidad}


def escala(df: pd.DataFrame, H: int) -> np.ndarray:
    """Escala del error por emisora: volatilidad diaria de 60 sesiones (conocida en la fecha base) × √H. Así un bono y
    una acción volátil no reciben el mismo rango."""
    v = pd.to_numeric(df["vol60"], errors="coerce").to_numpy(dtype=float)
    med = np.nanmedian(v) if np.isfinite(v).any() else 0.01
    v = np.where(np.isfinite(v), v, med)
    return np.maximum(v, 1e-4) * np.sqrt(H)


def metricas(df: pd.DataFrame, pred: np.ndarray, residuos_val: np.ndarray, H: int, k: int, costo: float,
             nombre: str) -> dict:
    """`residuos_val`: residuos de validación ESTANDARIZADOS por `escala` (rango y probabilidad por emisora)."""
    y = df["y"].to_numpy()
    s = escala(df, H)
    q10, q90 = np.quantile(residuos_val, [0.10, 0.90]) if len(residuos_val) else (np.nan, np.nan)
    cob = float(np.mean((y >= pred + q10 * s) & (y <= pred + q90 * s))) if len(y) else None
    res_ord = np.sort(residuos_val)
    prob = 1 - np.searchsorted(res_ord, -pred / s, side="right") / max(len(res_ord), 1)  # P(y > 0) con residuos empíricos
    brier = float(np.mean((prob - (y > 0)) ** 2))
    no_cero = pred != 0
    meses = pd.Series(pd.to_datetime(df["fecha"]).dt.to_period("M").astype(str).to_numpy())
    err = pd.DataFrame({"m": meses, "e": (y - pred) ** 2, "e0": y ** 2}).groupby("m").mean()
    return {"modelo": nombre, "n": int(len(y)), "mse": _mse(y, pred), "mae": float(np.mean(np.abs(y - pred))),
            "calibracion": calibracion(prob, y),
            "acierto_direccion": float(np.mean(np.sign(pred[no_cero]) == np.sign(y[no_cero]))) if no_cero.any() else None,
            "r2_vs_sin_cambio": float(1 - _mse(y, pred) / _mse(y, 0 * y)) if _mse(y, 0 * y) > 0 else None,
            "cobertura_intervalo_80": cob, "brier_prob_subida": brier,
            "meses_mejor_que_sin_cambio": f"{int((err['e'] < err['e0']).sum())}/{len(err)}",
            **estrategia(df, pred, H, k, costo, mantener=(nombre == "sin_cambio"))}


def por_mercado(df: pd.DataFrame, pred: np.ndarray, H: int) -> list[dict]:
    """Error y dirección del modelo frente a «sin cambio», separados por mercado (BMV y SIC)."""
    out = []
    mercado = df["instrumento_id"].str.split(":").str[0]
    for m in sorted(mercado.unique()):
        sel = (mercado == m).to_numpy()
        y, p = df["y"].to_numpy()[sel], np.asarray(pred)[sel]
        if not len(y):
            continue
        nz = p != 0
        out.append({"mercado": m, "n": int(len(y)), "instrumentos": int(df.loc[sel, "instrumento_id"].nunique()),
                    "mse": _mse(y, p), "mse_sin_cambio": _mse(y, 0 * y),
                    "acierto_direccion": float(np.mean(np.sign(p[nz]) == np.sign(y[nz]))) if nz.any() else None})
    return out


def calibracion(prob: np.ndarray, y: np.ndarray, cortes=(0.0, 0.3, 0.45, 0.55, 0.7, 1.0)) -> list[dict]:
    """Probabilidad de subida estimada frente a la frecuencia observada, por tramos (calibración)."""
    out = []
    for a, b in zip(cortes[:-1], cortes[1:], strict=True):
        sel = (prob >= a) & ((prob < b) if b < 1 else (prob <= b))
        if sel.any():
            out.append({"tramo": f"{a:.2f}–{b:.2f}", "n": int(sel.sum()), "prob_media": float(prob[sel].mean()),
                        "frecuencia_subida": float((y[sel] > 0).mean())})
    return out


def diebold_mariano(df: pd.DataFrame, pred_a: np.ndarray, pred_b: np.ndarray, H: int) -> dict:
    """Prueba de Diebold-Mariano sobre la pérdida cuadrática, promediada por fecha (panel), con varianza de
    Newey-West de H−1 rezagos (las etiquetas a H sesiones se solapan). d > 0 ⇒ A tiene menos error que B."""
    from math import erf, sqrt
    y = df["y"].to_numpy()
    dif = pd.Series((y - pred_b) ** 2 - (y - pred_a) ** 2).groupby(df["fecha"].to_numpy()).mean().to_numpy()
    n = len(dif)
    if n < 20:
        return {"n": n, "estadistico": None, "p_valor": None}
    d = dif - dif.mean()
    var = float(np.dot(d, d) / n)
    for k in range(1, max(H, 1)):
        var += 2 * (1 - k / H) * float(np.dot(d[k:], d[:-k]) / n)
    if var <= 0:
        return {"n": n, "estadistico": None, "p_valor": None}
    est = float(dif.mean() / sqrt(var / n))
    p = 1 - 0.5 * (1 + erf(est / sqrt(2)))  # unilateral: H1 = A mejor que B
    return {"n": n, "estadistico": round(est, 4), "p_valor": round(float(p), 4)}


def _huella(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def investigar(con: sqlite3.Connection, demo: bool, H: int, T: pd.Timestamp | None = None, config: dict | None = None,
               guardar: bool = True) -> dict:
    cfg = {**CONFIG_BASE, **(config or {}), "H": H}
    T = pd.Timestamp(T if T is not None else datetime.now(UTC))
    T = T.tz_localize("UTC") if T.tzinfo is None else T.tz_convert("UTC")
    precios = datos.precios_hasta(con, demo, T, mxn=bool(cfg.get("mxn")))
    panel = datos.etiquetados_hasta(datos.construir_panel(precios, H, datos.noticias_hasta(con, T)), T)
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
    s_val = escala(val, H)
    residuos = {"modelo": (val["y"].to_numpy() - ajustados[elegido].predict(_X(val))) / s_val}
    for nombre, pr in referencias(val, H).items():
        residuos[nombre] = (val["y"].to_numpy() - pr) / s_val

    # 3) prueba final: modelo fijado, reentrenado con entrenamiento + validación purgados contra la prueba
    m_ev = (panel["fecha"] <= cortes.fechas[cortes.validacion[1] - 1]) & panel["fecha_fin_etiqueta"].notna() & (
        panel["fecha_fin_etiqueta"] < cortes.fechas[cortes.prueba[0]])
    final = modelo(elegido, alfa[elegido], umbral, semilla).fit(_X(panel[m_ev]), panel.loc[m_ev, "y"])
    costo = reto.costo_operacion() or 0.00116
    k = int(cfg["top_k"])
    tabla = [metricas(pru, final.predict(_X(pru)), residuos["modelo"], H, k, costo, f"modelo ({elegido})")]
    for nombre, pr in referencias(pru, H).items():
        tabla.append(metricas(pru, pr, residuos[nombre], H, k, costo, nombre))
    cero = np.zeros(len(pru))
    estrategias_ref = [{"modelo": "pesos_iguales (todas las emisoras)", **estrategia(pru, cero, H, k, costo, iguales=True)},
                       {"modelo": "estrategia_actual (media histórica de 60 sesiones, como el optimizador)",
                        **estrategia(pru, referencias(pru, H)["historico_reciente"], H, k, costo)}]
    mod, refs = tabla[0], tabla[1:]
    pred_mod = final.predict(_X(pru))
    dm = {n: diebold_mariano(pru, pred_mod, pr, H) for n, pr in referencias(pru, H).items()}
    significativo = all((v["p_valor"] is not None and v["p_valor"] < 0.05) for v in dm.values())
    supera_error = mod["mse"] < min(r["mse"] for r in refs) and significativo
    supera_neto = mod["resultado_neto"] > max([r["resultado_neto"] for r in refs] + [e["resultado_neto"] for e in estrategias_ref])

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
        "prueba": tabla, "estrategias_referencia": estrategias_ref, "diebold_mariano_vs_referencias": dm,
        "error_menor_sin_significancia": bool(mod["mse"] < min(r["mse"] for r in refs) and not significativo), "supera_referencias": bool(supera_error and supera_neto),
        "veredicto": "VENTAJA FUERA DE MUESTRA" if (supera_error and supera_neto) else SIN_VENTAJA,
        "nombres_referencias": {"sin_cambio": "cambio cero (y «mantener cartera» en la estrategia)",
                                "historico_reciente": "media histórica de 60 sesiones", "regla_simple": "tendencia simple"},
        "recomendacion_permitida": bool(supera_error and supera_neto),
        "conclusion": ("El modelo supera a las tres referencias fuera de muestra en error y resultado neto de costos."
                       if supera_error and supera_neto else
                       f"{SIN_VENTAJA}: el modelo no supera a las referencias simples fuera de muestra con significancia "
                       "(Diebold-Mariano p < 0.05 frente a cada una) y en resultado neto; no se emite recomendación de cambio."),
        "correlacion_activos_entrenamiento": datos.correlacion_activos(
            precios, cortes.fechas[cortes.entrenamiento[0]:cortes.entrenamiento[1]]),
        "prueba_ya_vista": prueba_ya_vista,
        "aviso": ("El embargo y la purga evitan fugas de información; no garantizan que los pronósticos acierten. "
                  "Los intervalos son estimaciones con error histórico."),
        "historia_insuficiente": datos.historia_insuficiente(precios, H), "moneda": "MXN" if cfg.get("mxn") else "original",
        "por_mercado": por_mercado(pru, pred_mod, H),
        "dias_prueba": int(pru["fecha"].nunique()),
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
