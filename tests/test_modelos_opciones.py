"""Comprobaciones numéricas para el panel hipotético de opciones europeas."""

import math

import pytest
from fastapi.testclient import TestClient

from terminal.app import app
from terminal.modelos_opciones import calcular
from terminal.seguridad import TOKEN_CSRF


def parametros(tipo="call", **cambios):
    base = {"tipo": tipo, "spot": 100, "strike": 100, "dias": 365,
            "volatilidad_pct": 20, "tasa_pct": 5, "dividendo_pct": 0}
    return base | cambios


def test_precio_y_griegas_referencia_europea():
    call = calcular(parametros())
    put = calcular(parametros("put"))
    assert call["precio_teorico"] == pytest.approx(10.450583572, abs=1e-8)
    assert put["precio_teorico"] == pytest.approx(5.573526022, abs=1e-8)
    assert call["delta"] == pytest.approx(0.636830651, abs=1e-8)
    assert put["delta"] == pytest.approx(-0.363169349, abs=1e-8)
    assert call["gamma"] == pytest.approx(put["gamma"])
    assert call["vega_por_1pct"] == pytest.approx(put["vega_por_1pct"])


def test_paridad_con_dividendo_y_recuperacion_de_volatilidad():
    call = calcular(parametros(dividendo_pct=2))
    put = calcular(parametros("put", dividendo_pct=2))
    esperado = 100 * math.exp(-0.02) - 100 * math.exp(-0.05)
    assert call["precio_teorico"] - put["precio_teorico"] == pytest.approx(esperado, abs=1e-9)
    recuperada = calcular(parametros(dividendo_pct=2, prima_mercado=call["precio_teorico"]))
    assert recuperada["volatilidad_implicita"] is True
    assert recuperada["volatilidad_pct"] == pytest.approx(20, abs=1e-7)


@pytest.mark.parametrize("cambio", [
    {"spot": 0}, {"spot": float("nan")}, {"dias": 0},
    {"volatilidad_pct": 0}, {"prima_mercado": 200},
])
def test_rechaza_valores_invalidos_y_premios_fuera_de_arbitraje(cambio):
    with pytest.raises(ValueError):
        calcular(parametros(**cambio))


def test_api_local_calcula_y_rechaza_entradas_incorrectas():
    cliente = TestClient(app, base_url="http://127.0.0.1:8765")
    cabeceras = {"X-CSRF-Token": TOKEN_CSRF}
    valido = cliente.post("/api/modelos/opciones", json=parametros(), headers=cabeceras)
    assert valido.status_code == 200
    assert valido.json()["precio_teorico"] == pytest.approx(10.450583572, abs=1e-8)
    invalido = cliente.post("/api/modelos/opciones", json=parametros(spot=0), headers=cabeceras)
    assert invalido.status_code == 422
