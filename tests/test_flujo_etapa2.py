"""Etapa 2: Heston (código propio), exportación a hftbacktest e importación de velas de TradingView/OpenBB/Yahoo."""
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from terminal import modelos_opciones as mo
from terminal.flujo import almacen, externos, heston as hs, servicio
from terminal.flujo.contratos import Libro, Nivel, Operacion, Procedencia
from terminal.seguridad import TOKEN_CSRF

HOY = date(2026, 10, 12)


def test_heston_reproduce_black_scholes_y_paridad():
    for K, T in ((100, 0.5), (80, 1.0), (130, 0.1)):
        h, b = hs.comprobar_contra_bs(K=K, T=T)
        assert h == pytest.approx(b, rel=1e-4, abs=1e-5)
    p = {"v0": 0.04, "kappa": 2.0, "theta": 0.05, "sigma": 0.5, "rho": -0.7}
    c = hs.precio("call", 100, [90, 110], [0.5, 0.5], 0.03, 0.01, p)
    put = hs.precio("put", 100, [90, 110], [0.5, 0.5], 0.03, 0.01, p)
    assert c - put == pytest.approx(100 * np.exp(-0.01 * 0.5) - np.array([90, 110]) * np.exp(-0.03 * 0.5))
    assert c[0] > c[1] > 0


def _cadena_sintetica(verdad, spot=100.0, r=0.04):
    cad = []
    for dias in (30, 60, 120):
        for K in range(75, 126, 5):
            tipo = "call" if K >= spot else "put"
            pr = float(hs.precio(tipo, spot, [K], [dias / 365], r, 0, verdad)[0])
            iv = mo.calcular({"tipo": tipo, "spot": spot, "strike": float(K), "dias": dias, "tasa_pct": r * 100,
                              "dividendo_pct": 0, "prima_mercado": pr})["volatilidad_pct"] / 100
            cad.append({"contrato": f"{tipo}{K}-{dias}", "vencimiento": date.fromordinal(HOY.toordinal() + dias).isoformat(),
                        "strike": float(K), "tipo": tipo, "bid": pr * 0.999, "ask": pr * 1.001, "iv": iv})
    return cad


def test_calibracion_recupera_parametros_conocidos():
    verdad = {"v0": 0.05, "kappa": 1.8, "theta": 0.06, "sigma": 0.6, "rho": -0.6}
    r = hs.calibrar(_cadena_sintetica(verdad), 100.0, 0.04, hoy=HOY)
    for k, v in verdad.items():
        assert r["parametros"][k] == pytest.approx(v, rel=0.05, abs=0.01)
    assert r["rmse_iv"] < 0.002 and r["convergio"]
    assert any("Feller" in a for a in r["avisos"])       # 2·1.8·0.06 < 0.36: se avisa


def test_calibracion_sin_datos_suficientes():
    with pytest.raises(ValueError, match="insuficientes"):
        hs.calibrar(_cadena_sintetica({"v0": 0.04, "kappa": 2, "theta": 0.04, "sigma": 0.3, "rho": -0.5})[:3], 100.0, 0.04, hoy=HOY)


def _flujo(con):
    t = datetime.now(UTC) - timedelta(minutes=5)
    p = Procedencia("bitso", "API pública", "cripto")
    almacen.guardar_libro(con, Libro("BITSO:BTC/MXN", t.isoformat(), [Nivel("bid", 1, 100, 2), Nivel("bid", 2, 99, 1),
                                                                        Nivel("ask", 1, 101, 3)]), p)
    almacen.guardar_operaciones(con, [Operacion("BITSO:BTC/MXN", (t + timedelta(seconds=1)).isoformat(), 100.5, 0.4, "compra", "1"),
                                      Operacion("BITSO:BTC/MXN", (t + timedelta(seconds=2)).isoformat(), 100.4, 0.1, None, "2")], p)
    con.commit()


def test_exportacion_hftbacktest_formato_y_banderas(con, tmp_path):
    _flujo(con)
    r = externos.exportar_hftbacktest(con, "BITSO:BTC/MXN", tmp_path)
    data = np.load(r["archivo"])["data"]
    assert data.dtype == externos.EVENT_DTYPE and len(data) == 7       # 2 clear + 3 snapshot + 2 trades
    assert np.all(np.diff(data["exch_ts"]) >= 0) and np.all(data["local_ts"] >= data["exch_ts"])
    ev = data["ev"]
    base = ev & 0xFF
    assert set(base.tolist()) == {externos.DEPTH_CLEAR_EVENT, externos.DEPTH_SNAPSHOT_EVENT, externos.TRADE_EVENT}
    trades = data[base == externos.TRADE_EVENT]
    assert trades[0]["ev"] & externos.BUY_EVENT and not trades[1]["ev"] & (externos.BUY_EVENT | externos.SELL_EVENT)
    assert all(x["ev"] & externos.EXCH_EVENT and x["ev"] & externos.LOCAL_EVENT for x in data)
    assert any("sin lado" in a for a in r["advertencias"])
    with pytest.raises(ValueError, match="sin libro"):
        externos.exportar_hftbacktest(con, "NADA", tmp_path)


def test_importar_velas_de_tradingview_openbb_y_yahoo(con, ajustes):
    tv = b"time,open,high,low,close,Volume\n1791576000,240,245,238,242,1000\n1791662400,242,246,241,245,1200\n"
    r = externos.importar_velas_externas(con, tv, "BMV:GMEXICO", "BMV", "1Day", "tradingview", "suscripción personal")
    assert r["formato_detectado"] == "tradingview" and r["guardados"] == 2
    obb = b"date,open,high,low,close,volume,vwap\n2026-10-08,10,11,9,10.5,500,10.2\n"
    r = externos.importar_velas_externas(con, obb, "SIC:MU", "EE. UU.", "1Day", "openbb", "proveedor de OpenBB", "America/New_York")
    assert r["formato_detectado"] == "openbb"
    v = servicio.velas(con, ajustes, "SIC:MU", "1Day", 3650)["barras"][0]
    assert v["inicio"] == "2026-10-08T04:00:00+00:00" and v["calidad"] == "importado"   # medianoche de Nueva York
    yahoo = b"Date,Open,High,Low,Close,Adj Close,Volume\n2026-10-07,5,6,4,5.5,5.5,10\n"
    assert externos.importar_velas_externas(con, yahoo, "X:Y", "otro", "1Day", "hoja", "propia")["formato_detectado"] == "generico"
    with pytest.raises(ValueError, match="formato"):
        externos.importar_velas_externas(con, b"a,b\n1,2\n", "X", "m", "1Day", "f", "l")
    with pytest.raises(ValueError, match="OHLC"):     # misma validación que la plantilla propia
        externos.importar_velas_externas(con, b"date,open,high,low,close\n2026-10-07,5,4,3,5\n", "X", "m", "1Day", "f", "l")


def test_api_etapa2_protegida_e_interruptores(monkeypatch):
    from terminal import app as modulo
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        assert c.post("/api/flujo/heston", json={"subyacente": "SIC:MU"}).status_code == 403          # sin CSRF
        r = c.post("/api/flujo/heston", json={"subyacente": "SIC:NADA"}, headers={"X-CSRF-Token": TOKEN_CSRF})
        assert r.status_code == 422 and "cadena" in r.json()["detail"]
        assert c.get("/api/flujo/hftbacktest", params={"simbolo": "NADA"}).status_code == 404
        monkeypatch.setitem(modulo.AJUSTES.datos, "flujo", {"externos": {"activo": False}, "hftbacktest": {"activo": False}})
        r = c.post("/api/flujo/importar-externo", files={"archivo": ("x.csv", b"date,open,high,low,close\n")},
                   data={"simbolo": "X", "mercado": "m", "fuente": "f", "licencia": "l"}, headers={"X-CSRF-Token": TOKEN_CSRF})
        assert r.status_code == 409
        assert c.get("/api/flujo/hftbacktest", params={"simbolo": "NADA"}).status_code == 409
