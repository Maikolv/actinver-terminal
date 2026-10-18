"""TSM mensual educativo (sin fuga, holdout de un solo uso) y anomalías de volumen sin repintado."""
import numpy as np
import pandas as pd
import pytest

from terminal import anomalias, tsm_mensual


def _serie(n=3000, deriva=0.0004, semilla=1):
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range("2010-01-01", periods=n)
    return pd.Series(100 * np.cumprod(1 + rng.normal(deriva, 0.01, n)), index=idx)


def test_fin_de_mes_descarta_mes_incompleto():
    s = _serie(n=45)                                     # 2010-01-01 .. 2010-03-04
    m = tsm_mensual.fin_de_mes(s)
    assert [str(x.date()) for x in m.index] == ["2010-01-29", "2010-02-26"]


def test_senal_y_ejecucion_sin_fuga():
    s = _serie()
    df = tsm_mensual.periodos(s, 3, 0.0)
    r = df.iloc[0]
    assert r["fecha_ejecucion"] > r["fecha_senal"]       # se ejecuta la sesión siguiente a la señal
    # Cambiar precios POSTERIORES a la señal no altera la exposición decidida.
    s2 = s.copy()
    s2[s2.index > r["fecha_senal"]] *= 0.5
    assert tsm_mensual.periodos(s2, 3, 0.0).iloc[0]["exposicion"] == r["exposicion"]
    # Largo si subió en L meses, fuera si bajó.
    assert all((f.exposicion == 1.0) == (f.cambio_lookback > 0) for f in df.itertuples())


def test_costos_y_tamano_por_rango():
    s = _serie()
    sin = tsm_mensual.periodos(s, 3, 0.0)["estrategia"].sum()
    con = tsm_mensual.periodos(s, 3, 0.01)["estrategia"].sum()
    assert con < sin
    expo = tsm_mensual.periodos(s, 3, 0.0, riesgo_pct=0.002)["exposicion"]
    assert expo.max() <= 1 and ((expo > 0) & (expo < 1)).any()


def test_preregistro_selecciona_en_entrenamiento_y_holdout_unico(con):
    P = pd.DataFrame({"A": _serie(semilla=1), "B": _serie(semilla=2, deriva=-0.0002)})
    r = tsm_mensual.preregistrar(con, {"mercados": ["A", "B"], "corte": "2016-01", "B": 999})
    v = tsm_mensual.evaluar(con, r["id"], P)
    assert len(v["variantes"]) == 6 and v["holdout_ya_usado"] is False
    assert all(h["elegido"] in tsm_mensual.LOOKBACKS for h in v["holdout"].values())
    assert v["holdout"]["A"]["desde"] >= "2016-02-01"      # embargo de 1 mes tras el corte
    assert v["prueba_permutacion"]["familia_total_holm"] == 6
    v2 = tsm_mensual.evaluar(con, r["id"], P * 2)
    assert v2["holdout_ya_usado"] is True and v2["huella_datos"] == v["huella_datos"]
    with pytest.raises(ValueError):
        tsm_mensual.preregistrar(con, {"igualdad": "corto"})
    with pytest.raises(LookupError):
        tsm_mensual.evaluar(con, 999999, P)


def _barras(n=120, semilla=3):
    rng = np.random.default_rng(semilla)
    c = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    v = rng.lognormal(10, 0.3, n)
    v[60] *= 20                                          # pico de volumen conocido
    return [{"inicio": str(i), "cierre": float(c[i]), "volumen": float(v[i])} for i in range(n)]


def test_anomalia_detecta_pico_y_no_repinta():
    b = _barras()
    m = anomalias.detectar(b)
    assert m[60]["anomalia"] and all(x["z_volumen"] is None for x in m[:20])   # calentamiento nulo
    pref = anomalias.detectar(b[:80])
    assert [x["anomalia"] for x in pref] == [x["anomalia"] for x in m[:80]]     # agregar barras no cambia el pasado
    b2 = [dict(x) for x in b]
    b2[61]["volumen"] *= 50                              # dato futuro no altera la marca en 60
    assert anomalias.detectar(b2)[60]["z_volumen"] == m[60]["z_volumen"]


def test_barra_abierta_no_marca_y_evaluacion():
    b = _barras()
    b[60]["cerrada"] = False
    assert not anomalias.detectar(b)[60]["anomalia"]
    e = anomalias.evaluar(_barras(), h=1)
    assert e["anomalias"] >= 1 and e["media_futura_todas"] is not None
    with pytest.raises(ValueError):
        anomalias.evaluar(_barras(), h=0)


def test_api_tsm_y_anomalias():
    from fastapi.testclient import TestClient

    from terminal import app as modulo
    from terminal.seguridad import TOKEN_CSRF
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        assert c.post("/api/investigacion/tsm/preregistro", json={}).status_code == 403               # CSRF
        assert c.post("/api/investigacion/tsm/preregistro", json={"igualdad": "x"},
                      headers={"X-CSRF-Token": TOKEN_CSRF}).status_code == 422
        assert c.get("/api/investigacion/tsm").json()["lookbacks"] == [3, 6, 12]
        assert c.get("/api/investigacion/anomalias", params={"simbolo": "NADA", "intervalo": "1Min"}).status_code == 404
        assert c.get("/api/investigacion/anomalias", params={"simbolo": "MU", "intervalo": "2Min"}).status_code == 422
