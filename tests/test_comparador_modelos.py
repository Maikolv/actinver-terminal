"""Comparador de modelos: mismas reglas walk-forward y honestidad de datos (sin ganador con datos demo)."""
import pytest
from conftest import sembrar_precios

from terminal import comparador_modelos

ACCIONES = ["SIC:AAPL", "SIC:MSFT", "SIC:KO", "SIC:JNJ", "BMV:WALMEX", "BMV:GFNORTE", "BMV:AMX", "SIC:XOM"]


@pytest.fixture
def perfil(ajustes):
    return {**ajustes["perfil"], "capital": 100000}


def test_compara_todos_los_candidatos(con, ajustes, perfil):
    sembrar_precios(con, ACCIONES)
    r = comparador_modelos.comparar(con, ajustes, perfil, "acciones")
    assert r["estado"] == "calculada"
    nombres = {f["modelo"] for f in r["ranking"]}
    assert {"vigente (media-varianza)", "1/N", "HRP", "paridad de riesgo", "mínimo CVaR 95%"} <= nombres
    assert not [f for f in r["ranking"] if "error" in f]
    sharpes = [f["sharpe"] for f in r["ranking"] if f.get("sharpe") is not None]
    assert sharpes == sorted(sharpes, reverse=True)


def test_sin_datos_suspende_y_demo_no_declara_ganador(con, ajustes, perfil):
    assert comparador_modelos.comparar(con, ajustes, perfil, "acciones")["estado"] == "suspendida"
    sembrar_precios(con, ACCIONES)
    r = comparador_modelos.comparar(con, ajustes, perfil, "acciones")
    if ajustes.modo == "demo":
        assert r["ganador"] is None and r["aviso"]
