"""Gestión de riesgo del plan: stop por volatilidad confirmado por tendencia, reducción en tendencia bajista,
concentración, volatilidad objetivo, mínimo de emisoras y reinversión en tendencia alcista."""
import numpy as np
import pandas as pd
import pytest

from terminal import gestion_riesgo as g, mercado, reto

R = dict(g.REGLAS)


def serie(tramos, ruido=0.005):
    """Precios a partir de 100 con tramos (sesiones, rendimiento diario) y un poco de ruido determinista."""
    rng = np.random.default_rng(1)
    p, out = 100.0, []
    for n, mu in tramos:
        for _ in range(n):
            p *= 1 + mu + rng.normal(0, ruido)
            out.append(p)
    return pd.Series(out, index=pd.bdate_range(end=pd.Timestamp.today().normalize() - pd.Timedelta(days=1), periods=len(out)))


def bajista_sin_stop():
    """Tendencia bajista suave con oscilación de ±2 %: precio < SMA20 < SMA50 pero arriba de su stop."""
    niv = [100 * (1 + 0.002 * k) for k in range(60)] + [112 * (1 - 0.002 * k) for k in range(30)]
    v = [x * (1 + 0.02 * (-1) ** k) for k, x in enumerate(niv)]
    v[-1] = niv[-1] * 0.99
    return pd.Series(v, index=pd.bdate_range(end=pd.Timestamp.today().normalize() - pd.Timedelta(days=1), periods=len(v)))


def test_indicadores_stop_y_tendencias():
    cae = g.indicadores(serie([(80, 0.004), (10, -0.03)]), R)
    assert cae["precio"] < cae["stop"] and cae["precio"] < cae["sma_larga"] and cae["bajista"]
    sube = g.indicadores(serie([(90, 0.004)]), R)
    assert sube["alcista"] and not sube["bajista"] and sube["precio"] > sube["stop"]
    assert g.indicadores(serie([(30, 0.0)]), R) is None  # sin SMA50 no se decide


def _cartera(pesos, costo=None):
    total = 100_000.0
    pos = [{"instrumento_id": i, "clave_operable": i.split(":")[1], "cantidad": 10, "valor_mxn": w * total,
            "precio_mxn": None, "no_realizado_pct": (costo or {}).get(i, 0.0)} for i, w in pesos.items()]
    return {"valor_total": total, "posiciones": pos, "resultado_total": -20_000, "aportacion_neta": 100_000}


def test_evaluar_vende_lo_roto_reduce_concentracion_y_reinvierte(monkeypatch):
    series = {"SIC:CAE": serie([(80, 0.004), (10, -0.03)]), "SIC:BAJA": bajista_sin_stop(),
              "SIC:SUBE": serie([(90, 0.004)]), "SIC:OTRA": serie([(90, 0.003)]), "SIC:NUEVA": serie([(90, 0.005)]),
              "SIC:PLANA": serie([(90, 0.001)])}
    P = pd.DataFrame(series)
    monkeypatch.setattr(mercado, "precios_mxn", lambda con, aj, ids, ajustados=True: P[[i for i in ids if i in P]])
    monkeypatch.setattr(mercado, "instrumentos", lambda con: {})
    monkeypatch.setattr(reto, "activo", lambda: True)
    monkeypatch.setattr(reto, "config", lambda: {"reglas": {"min_emisoras": 5}})
    cart = _cartera({"SIC:CAE": 0.40, "SIC:BAJA": 0.20, "SIC:SUBE": 0.20, "SIC:OTRA": 0.10, "SIC:PLANA": 0.10},
                    {"SIC:BAJA": -0.05})
    prop = {"nombre": "P", "pesos": [{"id": "SIC:NUEVA", "peso": 0.5}, {"id": "SIC:CAE", "peso": 0.5}]}
    r = g.evaluar(None, {"gestion_riesgo": {"vol_objetivo": 5.0}}, cart, prop)
    pos = {f["id"]: f for f in r["posiciones"]}
    assert pos["SIC:CAE"]["peso_objetivo"] == 0 and pos["SIC:CAE"]["regla"] == "stop"
    assert pos["SIC:BAJA"]["peso_objetivo"] == pytest.approx(0.10) and pos["SIC:BAJA"]["regla"] == "tendencia"
    assert pos["SIC:SUBE"]["peso_objetivo"] == pytest.approx(0.20)
    compras = [f for f in r["filas"] if f["accion"] == "comprar"]
    assert [c["id"] for c in compras] == ["SIC:NUEVA"]          # nunca recompra lo que vende
    assert compras[0]["peso_objetivo"] <= R["peso_max"] + 1e-9   # tope de concentración también al comprar
    assert r["ordenes"] and r["cartera"]["vol_despues"] >= 0
    assert any("VENDER TODO" in x for x in g.lineas(r))


def test_minimo_de_emisoras_y_volatilidad_objetivo(monkeypatch):
    P = pd.DataFrame({f"SIC:C{k}": serie([(80, 0.004), (10, -0.03)]) for k in range(5)}
                     | {"SIC:OK": serie([(90, 0.004)])})
    monkeypatch.setattr(mercado, "precios_mxn", lambda con, aj, ids, ajustados=True: P[[i for i in ids if i in P]])
    monkeypatch.setattr(mercado, "instrumentos", lambda con: {})
    monkeypatch.setattr(reto, "activo", lambda: True)
    monkeypatch.setattr(reto, "config", lambda: {"reglas": {"min_emisoras": 5}})
    cart = _cartera({**{f"SIC:C{k}": 0.15 for k in range(5)}, "SIC:OK": 0.25})
    r = g.evaluar(None, {}, cart, None)                         # sin propuesta: nada que comprar
    assert len([f for f in r["posiciones"] if f["peso_objetivo"] > 0]) == 5
    assert all(f["peso_objetivo"] <= 0.02 + 1e-9 for f in r["posiciones"] if f["id"] != "SIC:OK")
    r2 = g.evaluar(None, {"gestion_riesgo": {"vol_objetivo": 0.0001}}, _cartera({"SIC:OK": 0.25}), None)
    assert r2["posiciones"][0]["regla"] == "volatilidad" and r2["posiciones"][0]["peso_objetivo"] < 0.25
