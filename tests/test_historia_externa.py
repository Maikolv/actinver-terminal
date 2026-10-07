"""Historia externa del usuario: mapeo de claves Yahoo, verificación contra la serie local y extensión hacia atrás."""
import numpy as np
import pandas as pd

from terminal import historia_externa as hx


def _local(con, iid, fechas, precios, moneda):
    con.executemany("INSERT INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, moneda, proveedor, tipo_dato, "
                    "obtenido_en) VALUES (?,?,?,?,?,?,?,?)",
                    [(iid, f.date().isoformat(), p, p, moneda, "tiingo", "cierre", "2026-01-01") for f, p in zip(fechas, precios)])
    con.commit()


def test_mapeo_de_claves_y_homonimo_ac(con):
    m = hx.mapear(con, ["AAPL", "BRK-B", "GMEXICOB.MX", "LIVEPOLC-1.MX", "AC", "ACTI500B.MX", "Moderado", "ZZZZ"])
    assert m["AAPL"]["id"] == "SIC:AAPL" and m["BRK-B"]["id"] == "SIC:BRKB"
    assert m["GMEXICOB.MX"]["id"] == "BMV:GMEXICO" and m["LIVEPOLC-1.MX"]["id"] == "BMV:LIVEPOL"
    assert m["ACTI500B.MX"]["id"] == "FONDO:ACTI500"
    assert m["AC"]["id"] is None and "Associated Capital" in m["AC"]["motivo"]   # no es Arca Continental
    assert m["Moderado"]["id"] is None and m["ZZZZ"]["id"] is None


def test_verifica_igual_rechaza_distinta_y_no_verifica_sin_solape(con):
    f = pd.bdate_range("2024-01-01", periods=60)
    rng = np.random.default_rng(1)
    p = 100 * np.cumprod(1 + rng.normal(0, 0.01, 60))
    _local(con, "SIC:AAPL", f, p, "USD")
    _local(con, "SIC:MSFT", f, p, "USD")
    df = pd.DataFrame({"AAPL": p * 1.01,                                   # mismo rendimiento (otro ajuste de nivel)
                       "MSFT": 100 * np.cumprod(1 + rng.normal(0, 0.01, 60)),  # otra serie
                       "NVDA": p}, index=f)                                 # sin serie local
    inf = hx.verificar(con, df)
    e = {x["columna"]: x["estado"] for x in inf["filas"]}
    assert e == {"AAPL": "verificada", "MSFT": "rechazada", "NVDA": "sin verificar"}
    assert hx.aceptadas(inf) == {"AAPL": "SIC:AAPL"}


def test_extiende_solo_antes_del_primer_dato_local(con, ajustes):
    f = pd.bdate_range("2020-01-01", periods=80)
    con.executemany("INSERT INTO fx (par, fecha, valor, proveedor, tipo_dato, obtenido_en) VALUES ('USDMXN',?,20,'fred','fix','x')",
                    [(d.date().isoformat(),) for d in f])
    rng = np.random.default_rng(2)
    p = 100 * np.cumprod(1 + rng.normal(0, 0.01, 80))
    _local(con, "SIC:AAPL", f[40:], p[40:], "USD")
    df = pd.DataFrame({"AAPL": p}, index=f)
    inf = hx.verificar(con, df)
    R = pd.DataFrame({"SIC:AAPL": pd.Series(p[40:], index=f[40:]).pct_change()})
    R2, info = hx.extender(con, ajustes, R, inf, df)
    assert info[0]["sesiones_agregadas"] == 40 and R2.index.min() == f[0]  # el primer rendimiento local es f[41]
    assert np.allclose(R2.loc[f[1:41], "SIC:AAPL"], pd.Series(p, index=f).pct_change().loc[f[1:41]])
    assert R2.loc[f[41]:, "SIC:AAPL"].equals(R.loc[f[41]:, "SIC:AAPL"])  # lo local no se toca


def test_perfiles_reportan_rendimiento_y_caida():
    f = pd.bdate_range("2004-01-05", periods=600)
    df = pd.DataFrame({"Moderado": np.linspace(100, 150, 600)}, index=f)
    df.iloc[300:, 0] *= 0.8
    r = hx.perfiles(df)["Moderado"]
    assert r["max_caida"] < -0.15 and r["rend_anual"] > 0
