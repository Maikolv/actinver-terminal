"""Etapa 3: riesgo con supuestos visibles, seguimiento y comparación, y backtesting reproducible sin fuga de información."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from terminal import backtest, riesgo, seguimiento
from terminal.seguridad import TOKEN_CSRF

from conftest import sembrar_precios


def _P(n=300, cols=("A", "B", "C"), semilla=1):
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame({c: 100 * np.cumprod(1 + rng.normal(0.0005, 0.015, n)) for c in cols}, index=idx)


def test_metricas_de_riesgo_y_var():
    r = pd.Series(np.r_[np.full(93, 0.001), np.full(7, -0.05)], index=pd.bdate_range("2025-01-01", periods=100))
    m = riesgo.metricas_serie(r, 1_000_000, horizonte=4)
    v = m["var"]["95"]
    assert v["historico_1d"] == pytest.approx(0.05, abs=0.006) and v["cvar_1d"] >= v["historico_1d"] - 1e-12
    assert v["historico_h"] == pytest.approx(v["historico_1d"] * 2)            # √4
    assert v["historico_1d_mxn"] == pytest.approx(v["historico_1d"] * 1_000_000)
    assert m["max_drawdown"] < -0.2 and riesgo.metricas_serie(r.head(10), 1)["suficiente"] is False


def test_backtest_ejecuta_al_dia_siguiente_sin_fuga():
    P = _P()
    # Precio que salta +50 % un día: si la estrategia viera el futuro compraría antes del salto.
    P.loc[P.index[200]:, "A"] *= 1.5
    r = backtest.correr(P, "comprar_y_mantener", {}, str(P.index[100].date()), str(P.index[-1].date()), 0.0, 0.0)
    primera = r["operaciones"][0]
    assert primera["fecha"] == str(P.index[101].date())        # señal el día 100, ejecución el 101
    assert all(o["fecha"] == primera["fecha"] for o in r["operaciones"])   # comprar y mantener: una sola vez


def test_costos_y_deslizamiento_reducen_el_resultado_y_es_determinista():
    P = _P()
    a = backtest.correr(P, "pesos_iguales", {"rebalanceo": 5}, "2024-03-01", "2025-01-31", 0.0, 0.0)
    b = backtest.correr(P, "pesos_iguales", {"rebalanceo": 5}, "2024-03-01", "2025-01-31", 0.00116, 20)
    assert b["resumen"]["valor_final"] < a["resumen"]["valor_final"] and b["resumen"]["costo_total"] > 0
    assert backtest.correr(P, "pesos_iguales", {"rebalanceo": 5}, "2024-03-01", "2025-01-31", 0.00116, 20) == b


def test_estrategias_y_parametros_validados():
    P = _P(cols=("A", "B", "C", "D"))
    m = backtest.correr(P, "momento", {"lookback": 20, "k": 2, "rebalanceo": 10}, "2024-03-01", "2025-01-31", 0.001, 5)
    assert m["resumen"]["operaciones"] > 0
    c = backtest.correr(P, "cruce_medias", {"rapida": 5, "lenta": 20}, "2024-03-01", "2025-01-31", 0.001, 5)
    assert c["resumen"]["sesiones"] > 200
    with pytest.raises(ValueError, match="rápida"):
        backtest.correr(P, "cruce_medias", {"rapida": 30, "lenta": 20}, "2024-03-01", "2025-01-31", 0, 0)
    with pytest.raises(ValueError, match="desconocida"):
        backtest.correr(P, "magia", {}, "2024-03-01", "2025-01-31", 0, 0)
    with pytest.raises(ValueError, match="k"):
        backtest.correr(P, "momento", {"k": 0}, "2024-03-01", "2025-01-31", 0, 0)


def test_backtest_registrado_y_reproducible(con, ajustes):
    ids = ["SIC:MU", "SIC:AMD", "SIC:NVDA"]
    sembrar_precios(con, ids, sesiones=400)
    desde, hasta = None, None
    r1 = backtest.ejecutar(con, ajustes, ids, "pesos_iguales", {"rebalanceo": 21}, desde, hasta, 5)
    r2 = backtest.ejecutar(con, ajustes, ids, "pesos_iguales", {"rebalanceo": 21}, desde, hasta, 5)
    assert r2["reproducibilidad"]["igual_a_corrida"] == r1["id"]
    assert r1["reproducibilidad"]["huella_datos"] == r2["reproducibilidad"]["huella_datos"]
    assert "referencia_comprar_y_mantener" in r1["resumen"] and r1["supuestos"]
    csv = backtest.exportar_csv(con, r1["id"])
    assert csv.startswith("# backtest") and "fecha,valor_cartera_mxn" in csv
    assert backtest.historial(con)[0]["id"] == r2["id"]
    with pytest.raises(ValueError, match="sin precios"):
        backtest.ejecutar(con, ajustes, ["SIC:AAPL"], "pesos_iguales")


def test_seguimiento_y_comparacion(con, ajustes):
    ids = ["SIC:MU", "SIC:NVDA", "BMV:NAFTRAC"]
    sembrar_precios(con, ids, sesiones=300)
    seguimiento.agregar(con, "SIC:MU", "vigilar resultados")
    with pytest.raises(ValueError, match="desconocido"):
        seguimiento.agregar(con, "SIC:NOEXISTE")
    l = seguimiento.lista(con, ajustes)["instrumentos"]
    assert l[0]["clave"] and l[0]["nota"] == "vigilar resultados" and l[0]["variacion"][5] is not None
    c = seguimiento.comparar(con, ajustes, ["SIC:MU", "SIC:NVDA"], 200)
    ref = next(m for m in c["metricas"] if m["es_referencia"])
    assert ref["beta"] == 1.0 and len(c["correlacion"]["matriz"]) == 3 and c["correlacion"]["matriz"][0][0] == pytest.approx(1)
    with pytest.raises(ValueError, match="al menos 2"):
        seguimiento.comparar(con, ajustes, ["SIC:MU"])
    seguimiento.quitar(con, "SIC:MU")
    assert seguimiento.lista(con, ajustes)["instrumentos"] == []


def test_api_etapa3():
    from terminal import app as modulo
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        assert c.post("/api/backtests", json={"ids": ["SIC:MU"], "estrategia": "pesos_iguales"}).status_code == 403   # CSRF
        r = c.post("/api/backtests", json={"ids": "SIC:MU", "estrategia": "pesos_iguales"}, headers={"X-CSRF-Token": TOKEN_CSRF})
        assert r.status_code == 422
        assert set(c.get("/api/backtests").json()["estrategias"]) >= {"comprar_y_mantener", "momento"}
        assert c.get("/api/backtests/999999").status_code == 404
        assert c.get("/api/riesgo").status_code == 200
        assert c.get("/api/comparar", params={"ids": "SIC:MU"}).status_code == 422
        assert c.post("/api/lista-seguimiento", json={"id": "NADA"}, headers={"X-CSRF-Token": TOKEN_CSRF}).status_code == 422
        assert c.get("/api/ficha/NADA").status_code == 404
