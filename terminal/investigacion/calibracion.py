"""Auditoría de la «probabilidad de subida» (P(y > 0)) por horizonte.

Todo se evalúa en la PRUEBA intacta, con fechas posteriores a la validación:
- Brier del modelo frente a dos referencias: la frecuencia base de subidas conocida al cierre de la validación
  (climatología) y 0.5. Brier skill score = 1 − Brier / Brier(frecuencia base).
- Curva de confiabilidad en 10 tramos de igual ancho, con n por tramo.
- Recalibración ajustada SOLO con la validación (isotónica y Platt/logística) y medida en la prueba.
- Incertidumbre: bootstrap por bloques de fechas (las etiquetas a H sesiones se solapan y las emisoras de un mismo día
  están correlacionadas), intervalo 90 % de la diferencia de Brier frente a la frecuencia base.

Veredicto: «calibrada» solo si el Brier del método es menor que el de la frecuencia base con el intervalo 90 % entero
por debajo de cero y la desviación máxima de la curva (tramos con n ≥ 30) es ≤ 10 puntos. Si no, «experimental».
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRAMOS = 10
N_MIN_TRAMO = 30
DESVIO_MAX = 0.10
B_BOOT = 400


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def confiabilidad(p: np.ndarray, y: np.ndarray, tramos: int = TRAMOS) -> list[dict]:
    p, y = np.asarray(p, float), np.asarray(y, float)
    out = []
    bordes = np.linspace(0, 1, tramos + 1)
    for a, b in zip(bordes[:-1], bordes[1:], strict=True):
        sel = (p >= a) & ((p < b) if b < 1 else (p <= b))
        if sel.any():
            out.append({"tramo": f"{a:.1f}–{b:.1f}", "n": int(sel.sum()), "prob_media": float(p[sel].mean()),
                        "frecuencia_subida": float(y[sel].mean())})
    return out


def desvio_max(curva: list[dict], n_min: int = N_MIN_TRAMO) -> float | None:
    d = [abs(c["prob_media"] - c["frecuencia_subida"]) for c in curva if c["n"] >= n_min]
    return max(d) if d else None


def _isotonica(p_val, y_val):
    from sklearn.isotonic import IsotonicRegression
    m = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p_val, y_val)
    return m.predict


def _platt(p_val, y_val):
    from sklearn.linear_model import LogisticRegression
    x = np.log(np.clip(p_val, 1e-4, 1 - 1e-4) / (1 - np.clip(p_val, 1e-4, 1 - 1e-4))).reshape(-1, 1)
    m = LogisticRegression(C=1e6).fit(x, y_val)

    def f(p):
        q = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
        return m.predict_proba(np.log(q / (1 - q)).reshape(-1, 1))[:, 1]
    return f


def _ic_bloques(err_a: np.ndarray, err_b: np.ndarray, fechas: np.ndarray, semilla: int, b: int = B_BOOT) -> tuple[float, float]:
    """IC 90 % de mean(err_a − err_b) remuestreando FECHAS completas (bloques)."""
    df = pd.DataFrame({"f": fechas, "d": err_a - err_b}).groupby("f")["d"].agg(["sum", "count"])
    if len(df) < 10:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(semilla)
    s, c = df["sum"].to_numpy(), df["count"].to_numpy()
    idx = rng.integers(0, len(df), size=(b, len(df)))
    medias = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    return (float(np.quantile(medias, 0.05)), float(np.quantile(medias, 0.95)))


def auditar(p_val: np.ndarray, y_val: np.ndarray, p_test: np.ndarray, y_test: np.ndarray, fechas_test, base_rate: float,
            semilla: int = 20261113) -> dict:
    """`y_*` binario (1 = subió). `base_rate`: frecuencia de subidas en entrenamiento + validación (conocida antes de la prueba)."""
    p_val, y_val = np.asarray(p_val, float), np.asarray(y_val, float)
    p_test, y_test = np.asarray(p_test, float), np.asarray(y_test, float)
    fechas = np.asarray(pd.to_datetime(pd.Series(fechas_test)).dt.strftime("%Y-%m-%d"))
    clima = np.full(len(y_test), float(base_rate))
    metodos = {"modelo (sin recalibrar)": p_test}
    if len(np.unique(y_val)) == 2 and len(y_val) >= 50:
        metodos["isotónica (ajustada en validación)"] = _isotonica(p_val, y_val)(p_test)
        metodos["Platt (ajustada en validación)"] = _platt(p_val, y_val)(p_test)
    b_clima = brier(clima, y_test)
    filas = []
    for nombre, p in metodos.items():
        e, e0 = (p - y_test) ** 2, (clima - y_test) ** 2
        lo, hi = _ic_bloques(e, e0, fechas, semilla)
        curva = confiabilidad(p, y_test)
        dmax = desvio_max(curva)
        mejor = bool(np.isfinite(hi) and hi < 0)
        filas.append({"metodo": nombre, "brier": brier(p, y_test), "brier_skill_vs_frecuencia_base": 1 - brier(p, y_test) / b_clima
                      if b_clima > 0 else None, "dif_brier_vs_base_ic90": [lo, hi], "mejor_que_base": mejor,
                      "desvio_max_curva": dmax, "curva": curva,
                      "calibrada": bool(mejor and dmax is not None and dmax <= DESVIO_MAX)})
    return {"n_prueba": int(len(y_test)), "fechas_prueba": int(len(np.unique(fechas))), "n_validacion": int(len(y_val)),
            "frecuencia_base": float(base_rate), "frecuencia_subida_prueba": float(y_test.mean()) if len(y_test) else None,
            "brier_frecuencia_base": b_clima, "brier_0_5": brier(np.full(len(y_test), 0.5), y_test),
            "metodos": filas, "algun_metodo_calibrado": any(f["calibrada"] for f in filas),
            "veredicto": ("calibrada" if filas and filas[0]["calibrada"] else "experimental"),
            "criterio": (f"Calibrada = Brier menor que la frecuencia base con IC 90 % (bootstrap por fechas) < 0 y desvío "
                         f"máximo de la curva ≤ {DESVIO_MAX:.0%} en tramos con n ≥ {N_MIN_TRAMO}.")}
