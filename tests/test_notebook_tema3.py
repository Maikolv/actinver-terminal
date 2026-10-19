"""Ejecuta el entregable autocontenido sin red, instalaciones ni archivos en el repo."""
import json
from pathlib import Path

import numpy as np
import pytest


NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks/multiples_estrategias.ipynb"


@pytest.fixture
def ejecutado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    espacio = {}
    celdas = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    for celda in celdas:
        exec(compile(celda, str(NOTEBOOK), "exec"), espacio)
    return espacio, celdas


def test_notebook_sintetico_exporta_y_congela(ejecutado, tmp_path):
    espacio, celdas = ejecutado
    resultado = espacio["resultado_congelado"]
    assert resultado["modo"] == "SINTÉTICO"
    assert resultado["conclusion"].startswith("BLOQUEADA")
    assert sum(resultado["tramos"][k] for k in ("exploracion", "purga", "embargo", "holdout")) == 600
    assert len(resultado["resultados_holdout"]) == 3
    assert all(r["p_holm"] >= r["p"] for r in resultado["resultados_holdout"])
    archivos = list((tmp_path / "resultados_tema3").iterdir())
    assert len(archivos) == 2
    guardado = json.loads(next(p for p in archivos if p.suffix == ".json").read_text(encoding="utf-8"))
    assert guardado == resultado
    exec(celdas[-2], espacio)
    exec(celdas[-1], espacio)
    assert espacio["resultado_congelado"] is resultado
    espacio["datos"].loc[0, "variante_1"] += 0.001
    with pytest.raises(AssertionError, match="consumida"):
        exec(celdas[-2], espacio)


def test_holm_familia_completa_y_casos_nulos(ejecutado):
    espacio, _ = ejecutado
    tabla = espacio["datos"].copy()
    nombres = espacio["CONFIG"]["estrategias"]
    tabla[nombres] = tabla[["benchmark"]].to_numpy() + np.zeros((len(tabla), len(nombres)))
    resultado = espacio["evaluar_familia"](tabla, espacio["CONFIG"])
    assert (resultado.p == 1).all() and (resultado.p_holm == 1).all()
    tabla[nombres] = tabla[["benchmark"]].to_numpy() + np.full((len(tabla), len(nombres)), 0.01)
    config = {**espacio["CONFIG"], "familia_total": 9}
    resultado = espacio["evaluar_familia"](tabla, config)
    # Con exceso constante todos comparten p: Holm multiplica por la familia total.
    np.testing.assert_allclose(resultado.p_holm, np.minimum(1, resultado.p * 9))


@pytest.mark.parametrize("defecto", ["duplicada", "invertida", "faltante", "infinito", "columna", "booleano"])
def test_rechaza_datos_invalidos(ejecutado, defecto):
    espacio, _ = ejecutado
    tabla = espacio["datos"].copy()
    if defecto == "duplicada":
        tabla.loc[1, "fecha"] = tabla.loc[0, "fecha"]
    elif defecto == "invertida":
        tabla = tabla.iloc[::-1]
    elif defecto == "faltante":
        tabla.loc[0, "variante_1"] = np.nan
    elif defecto == "infinito":
        tabla.loc[0, "variante_1"] = np.inf
    elif defecto == "booleano":
        tabla["variante_1"] = True
    else:
        tabla["no_declarada"] = 0
    with pytest.raises((AssertionError, ValueError)):
        espacio["validar_y_separar"](tabla, espacio["CONFIG"])


@pytest.mark.parametrize("cambio", ["configuracion", "seleccion"])
def test_bloquea_cambio_del_experimento(ejecutado, cambio):
    espacio, celdas = ejecutado
    if cambio == "configuracion":
        espacio["CONFIG"]["alpha"] = 0.1
    else:
        espacio["seleccionada"] = "otra"
    with pytest.raises(AssertionError, match="alterada"):
        exec(celdas[-2], espacio)


def test_exportacion_no_sobrescribe_resultado_distinto(ejecutado, tmp_path):
    espacio, celdas = ejecutado
    ruta = next((tmp_path / "resultados_tema3").glob("*.json"))
    ruta.write_text("resultado previo", encoding="utf-8")
    with pytest.raises(AssertionError, match="no se sobrescribe"):
        exec(celdas[-1], espacio)
    assert ruta.read_text(encoding="utf-8") == "resultado previo"


def test_holdout_se_reextrae_de_los_datos_firmados(ejecutado):
    espacio, celdas = ejecutado
    original = espacio.pop("resultado_congelado")
    espacio["reservado"].loc[:, "variante_1"] = 9.0
    exec(celdas[-2], espacio)
    assert espacio["resultado_congelado"] == original
