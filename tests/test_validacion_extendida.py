"""Validación extendida (panel dinámico): cada instrumento entra solo cuando tiene su entrenamiento completo."""
import numpy as np
import pandas as pd

from terminal import validacion_extendida as ve


def _panel():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2022-01-03", periods=600)
    R = pd.DataFrame(rng.normal(0.0004, 0.01, (600, 12)), index=idx, columns=[f"A{i}" for i in range(12)])
    R.iloc[:400, 11] = np.nan          # «A11» llega tarde (como las emisoras BMV con 1 año)
    return R


def test_el_instrumento_tardio_solo_entra_con_entrenamiento_completo():
    R = _panel()
    vistos = [(Xtr.index[0], "A11" in cols) for cols, Xtr, _ in ve.pliegues(R, tr=168, te=21)]
    assert all(not dentro for inicio, dentro in vistos if inicio < R.index[400])
    assert any(dentro for _, dentro in vistos)
    assert len(vistos) == (600 - 168 + 20) // 21  # usa toda la historia, no solo la común


def test_resumen_y_veredicto_frente_a_pesos_iguales():
    R = _panel()
    costos = pd.Series(0.00116, index=R.columns)
    iguales = ve.walk_forward(lambda cols, X: pd.Series(1 / len(cols), index=cols), R, costos, 0.02)
    r = ve.resumen(iguales)
    assert abs(r["exceso_anual"]) < 1e-9 and r["veredicto"].startswith("SIN VENTAJA")
    mejor = ve.walk_forward(lambda cols, X: X.mean().clip(lower=0).pipe(lambda m: m / m.sum() if m.sum() > 0
                                                                        else pd.Series(1 / len(cols), index=cols)),
                            R.assign(A0=R["A0"] + 0.004), costos, 0.02)
    assert ve.resumen(mejor)["exceso_ic90"][0] > 0      # un activo con ventaja clara y persistente sí se detecta
