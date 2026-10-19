import pandas as pd
import pytest
from laboratorio import demo, ejecutar, validar


@pytest.mark.parametrize("problema", ["sin_zona", "duplicada", "ohlc", "nulo", "negativo"])
def test_rechaza_datos_inconsistentes(problema):
    t, meta = demo()
    if problema == "sin_zona": t.loc[0, "fecha"] = "2026-01-05 14:30:00"
    if problema == "duplicada": t.loc[1, "fecha"] = t.loc[0, "fecha"]
    if problema == "ohlc": t.loc[0, "High"] = .1
    if problema == "nulo": t.loc[0, "Close"] = float("nan")
    if problema == "negativo": t.loc[0, "Volume"] = -1
    with pytest.raises(ValueError): validar(t, meta)


def test_costes_reducen_pnl_y_no_hay_entradas_antes_del_corte():
    t, meta = demo()
    cero = ejecutar(t, meta, comision=0, spread=0)
    coste = ejecutar(t, meta, comision=3, spread=.001)
    assert cero["operaciones"] > 0 and coste["operaciones"] == cero["operaciones"]
    assert coste["pnl_neto_virtual"] < cero["pnl_neto_virtual"]
    assert pd.Timestamp(coste["primera_entrada"]) >= pd.Timestamp(coste["corte_temporal"])
    assert coste["ordenes_reales"] is False
    assert coste["procedencia"]["calidad"] == "sintetico"


def test_rechaza_costes_negativos_y_falta_de_procedencia():
    t, meta = demo()
    with pytest.raises(ValueError): ejecutar(t, meta, comision=-1)
    with pytest.raises(ValueError): validar(t, {**meta, "licencia": ""})
