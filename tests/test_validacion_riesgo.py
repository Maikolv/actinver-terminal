"""El simulador de validación usa las mismas señales que el plan y no mira al futuro."""
import numpy as np
import pandas as pd

from terminal import validacion_riesgo as v
from terminal.gestion_riesgo import REGLAS, indicadores


def _precios(n=400, k=16, semilla=1):
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.02, (n, k)), axis=0)), index=idx,
                        columns=[f"X{i}" for i in range(k)])


def test_senales_iguales_a_las_del_plan():
    P = _precios()
    S = v.senales(P)
    for t in (60, 200, 399):
        for c in P.columns[:5]:
            ind = indicadores(P[c].iloc[: t + 1], REGLAS)
            assert bool(S["stop"][c].iloc[t]) == (ind["precio"] < ind["stop"] and ind["precio"] < ind["sma_larga"])
            assert bool(S["bajista"][c].iloc[t]) == ind["bajista"]
            assert bool(S["alcista"][c].iloc[t]) == ind["alcista"]


def test_sin_fuga_temporal_y_mantener_exacto():
    P = _precios()
    ids, pesos = list(P.columns[:8]), np.full(8, 1 / 8)
    base = v.simular(P, v.senales(P), ids, pesos, 260, 30, {"stop", "tendencia", "concentracion", "volatilidad"})
    P2 = P.copy()
    P2.iloc[291:] *= 3  # cambiar el futuro posterior a la ventana no altera el resultado
    assert v.simular(P2, v.senales(P2), ids, pesos, 260, 30, {"stop", "tendencia", "concentracion", "volatilidad"}) == base
    m = v.simular(P, v.senales(P), ids, pesos, 260, 30, set())
    assert abs(m["rendimiento"] - float((P[ids].iloc[290] / P[ids].iloc[260] - 1).mean())) < 1e-12


def test_una_venta_cobra_comision_y_se_ejecuta_al_dia_siguiente():
    P = _precios(k=8)
    P.iloc[:, 0] = 100.0
    P.iloc[261:, 0] = 60.0  # desplome el día 261: señal ese cierre, venta al cierre del 262 (mismo precio)
    S = v.senales(P)
    pesos = np.array([1.0] + [0.0] * 7)
    r = v.simular(P, S, list(P.columns), pesos, 260, 5, {"stop"})
    assert abs(r["rendimiento"] - (0.6 * (1 - v.COMISION) - 1)) < 1e-9
