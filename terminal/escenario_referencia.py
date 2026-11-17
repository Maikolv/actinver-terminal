"""Escenario de referencia: cartera demo con rendimientos sintéticos fijos (semilla 2026), calculada con el mismo
motor de la terminal (Ledoit-Wolf, optimizador de máximo Sharpe, VaR/CVaR histórico). La vigila
tests/test_escenario_referencia.py y la usan los documentos generados (scripts/reporte_ejecutivo.cjs).
`uv run python -m terminal.escenario_referencia` imprime las cifras en JSON."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import markowitz, riesgo

IDS = ["SIC:IVV", "FONDO:ACTIGOB", "BMV:WALMEX", "SIC:MSFT"]  # instrumentos de data/demo/cartera_demo.csv
PESOS_DEMO = np.array([0.40, 0.35, 0.10, 0.15])  # cartera demo de referencia
RF = 0.10  # CETES 28 de referencia


def rendimientos() -> pd.DataFrame:
    rng = np.random.default_rng(2026)
    mercado = rng.normal(0.0004, 0.009, 504)
    cols = {"SIC:IVV": 0.00045 + 0.95 * mercado + rng.normal(0, 0.004, 504),
            "FONDO:ACTIGOB": 0.00038 + rng.normal(0, 0.0008, 504),
            "BMV:WALMEX": 0.0002 + 0.6 * mercado + rng.normal(0, 0.014, 504),
            "SIC:MSFT": 0.0007 + 1.1 * mercado + rng.normal(0, 0.012, 504)}
    return pd.DataFrame(cols, index=pd.bdate_range("2024-01-02", periods=504))[IDS]


def cifras() -> dict:
    R = rendimientos()
    mu, cov = markowitz._estimar(R, "ledoit_wolf")
    w_tan = markowitz._pesos({"rf": RF, "metodo": "max_sharpe"}, mu, cov, 0.0, 0.6, [])[0]
    serie = R @ PESOS_DEMO
    m = riesgo.metricas_serie(serie, 1_000_000)
    return {"rend_esperado": float(PESOS_DEMO @ mu), "volatilidad": markowitz._vol(PESOS_DEMO, cov),
            "var95_1d": m["var"]["95"]["historico_1d"], "cvar95_1d": m["var"]["95"]["cvar_1d"],
            "max_sharpe": dict(zip(IDS, np.round(w_tan, 4).tolist()))}



if __name__ == "__main__":
    print(json.dumps({**cifras(), "pesos_demo": dict(zip(IDS, PESOS_DEMO.tolist())), "rf": RF}, ensure_ascii=False))
