"""Ficha técnica por emisora: indicadores sobre cierres, bloques sin fuente con su motivo y ruta de la API."""
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from conftest import sembrar_precios
from terminal import ficha_tecnica


def test_tecnico_senales_y_variaciones():
    s = pd.Series(100 * np.cumprod(np.full(260, 1.002)), index=pd.bdate_range(end="2026-11-04", periods=260))
    t = ficha_tecnica.tecnico(s)
    assert t["disponible"] and t["variacion"]["1d"] > 0 and t["maximo_52s"] == t["precio"] and t["desde_maximo"] == 0
    estados = {x["indicador"]: x["estado"] for x in t["senales"]}
    assert estados["Tendencia de largo plazo"] == "alcista" and estados["RSI 14"] == "sobrecompra"
    assert "a favor" in t["lectura"] and len(t["serie"]) == 260
    assert ficha_tecnica.tecnico(s.iloc[:1]) == {"disponible": False, "motivo": "menos de dos cierres guardados"}


def test_ficha_bmv_sin_flujo_dice_por_que(con, ajustes):
    sembrar_precios(con, ["BMV:AMX"], sesiones=300, proveedor="archivo", con_fx=False)
    f = ficha_tecnica.ficha(con, ajustes, "BMV:AMX")
    assert f["tecnico"]["disponible"] and not f["velas"]["disponible"] and "BMV" in f["velas"]["motivo"]
    assert not f["orderflow"]["disponible"] and not f["optionflow"]["disponible"] and f["posicion"] is None
    assert {w["tipo"] for w in f["widgets"] if w["disponible"]} == {"tecnico", "perfil", "finanzas"}


def test_api_ficha_tecnica():
    from terminal.app import app
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        assert c.get("/api/ficha-tecnica?simbolo=NO:EXISTE").status_code == 404
        r = c.get("/api/ficha-tecnica?simbolo=SIC:MU")
        assert r.status_code == 200 and r.json()["id"] == "SIC:MU" and "precio" in r.json() and "optionflow" in r.json()
        base = c.get("/api/ficha-tecnica?simbolo=SIC:MU&flujo=false").json()
        assert "orderflow" not in base and "tecnico" in base                 # lo pesado llega aparte

