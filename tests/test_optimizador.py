"""Propuestas: separación de clases, reproducibilidad, sensibilidad a criterios y suspensión por datos."""
import pandas as pd
import pytest
from conftest import sembrar_precios

from terminal import mercado, optimizador

ACCIONES = ["SIC:AAPL", "SIC:MSFT", "SIC:KO", "SIC:JNJ", "BMV:WALMEX", "BMV:GFNORTE", "BMV:AMX", "SIC:XOM"]
OTROS = ["SIC:IVV", "SIC:AGG", "FONDO:ACTIGOB", "FONDO:ACTIMED", "FONDO:ACTI500", "BMV:FUNO", "FONDO:ACTIG+2"]
VACIA = {"valor_total": 0, "posiciones": []}


@pytest.fixture
def perfil(ajustes):
    return {**ajustes["perfil"], "capital": 100000}


@pytest.fixture
def con_datos(con, ajustes):
    sembrar_precios(con, ACCIONES + OTROS)
    return con


def test_solo_acciones_no_mezcla_clases(con_datos, ajustes, perfil):
    p = optimizador.proponer(con_datos, ajustes, perfil, "acciones", VACIA)
    assert p["estado"] == "calculada"
    clases = {x["clase"] for x in p["pesos"]}
    assert clases <= {"accion", "reit"}
    assert set(p["reproducibilidad"]["universo"]) <= set(ACCIONES)


def test_mixta_incluye_etf_y_fondos_con_restricciones(con_datos, ajustes, perfil):
    p = optimizador.proponer(con_datos, ajustes, perfil, "mixta", VACIA)
    assert p["estado"] == "calculada"
    univ = set(p["reproducibilidad"]["universo"])
    assert {"SIC:IVV", "FONDO:ACTIGOB", "BMV:FUNO"} <= univ
    deuda = sum(x["peso"] for x in p["pesos"] if x["clase"] == "fondo_deuda")
    assert deuda >= ajustes["perfiles"]["moderado"]["min_deuda_mixta"] - 0.02  # tolerancia por redondeo/umbral
    assert abs(sum(x["peso"] for x in p["pesos"]) - 1) < 1e-6
    assert all(x["motivos"] for x in p["pesos"])


def test_reproducible(con_datos, ajustes, perfil):
    a = optimizador.proponer(con_datos, ajustes, perfil, "mixta", VACIA)
    b = optimizador.proponer(con_datos, ajustes, perfil, "mixta", VACIA)
    assert [(x["id"], x["peso"]) for x in a["pesos"]] == [(x["id"], x["peso"]) for x in b["pesos"]]
    assert a["puntuacion"] == b["puntuacion"]
    assert a["reproducibilidad"]["huella_datos"] == b["reproducibilidad"]["huella_datos"]


def test_cambia_con_riesgo_horizonte_y_restricciones(con_datos, ajustes, perfil):
    base = optimizador.proponer(con_datos, ajustes, perfil, "mixta", VACIA)
    cons = optimizador.proponer(con_datos, ajustes, {**perfil, "riesgo": "conservador"}, "mixta", VACIA)
    deuda = lambda p: sum(x["peso"] for x in p["pesos"] if x["clase"] == "fondo_deuda")  # noqa: E731
    assert deuda(cons) > deuda(base)
    corto = optimizador.proponer(con_datos, ajustes, {**perfil, "horizonte_anios": 1}, "mixta", VACIA)
    assert any(e["id"] == "FONDO:ACTIG+2" and "anual" in e["motivo"] for e in corto["excluidos"])
    excl = optimizador.proponer(con_datos, ajustes, {**perfil, "excluir": ["SIC:IVV"]}, "mixta", VACIA)
    assert "SIC:IVV" not in excl["reproducibilidad"]["universo"]
    assert any(e["motivo"] == "Excluido por el usuario" for e in excl["excluidos"])
    # misma entrada modificada -> mismo resultado (reproducible también tras el cambio)
    cons2 = optimizador.proponer(con_datos, ajustes, {**perfil, "riesgo": "conservador"}, "mixta", VACIA)
    assert [(x["id"], x["peso"]) for x in cons["pesos"]] == [(x["id"], x["peso"]) for x in cons2["pesos"]]


def test_dato_vencido_se_excluye_y_suspende(con, ajustes, perfil):
    viejo = pd.Timestamp.today().normalize() - pd.Timedelta(days=40)
    sembrar_precios(con, ACCIONES, fin=viejo)
    p = optimizador.proponer(con, ajustes, perfil, "acciones", VACIA)
    assert p["estado"] == "suspendida"
    assert any("vencido" in e["motivo"].lower() for e in p["excluidos"])
    assert "pesos" not in p


def test_sin_tipo_de_cambio_no_se_valoran_activos_en_dolares(con, ajustes, perfil):
    sembrar_precios(con, ACCIONES, con_fx=False)
    p = optimizador.proponer(con, ajustes, perfil, "acciones", VACIA)
    assert p["estado"] == "suspendida"
    assert any("tipo de cambio" in m.lower() for m in p["motivos"])


def test_walk_forward_sin_informacion_futura(con_datos, ajustes, perfil):
    elegibles, _, precios = optimizador.universo(con_datos, ajustes, perfil, "acciones")
    X = optimizador.rendimientos(precios, [e["id"] for e in elegibles])
    from skfolio.model_selection import WalkForward
    for train, test in WalkForward(train_size=504, test_size=63).split(X):
        assert max(train) < min(test)


def test_cambios_respetan_banda(con_datos, ajustes, perfil):
    p = optimizador.proponer(con_datos, ajustes, perfil, "acciones", VACIA)
    pesos = pd.Series({x["id"]: x["peso"] for x in p["pesos"]})
    obj = pesos.idxmax()
    actual = {"valor_total": 100000, "posiciones": [{"instrumento_id": obj, "valor_mxn": pesos[obj] * 100000 - 500,
                                                     "cantidad": 1, "costo_promedio": 1, "precio_mxn": 1}]}
    cambios = optimizador.cambios(pesos, {e: {"clase": "accion", "mercado_operable": "BMV-SIC"} for e in pesos.index},
                                  actual, 100000, ajustes, mercado.instrumentos(con_datos))
    fila = next(f for f in cambios["filas"] if f["id"] == obj)
    assert fila["accion"] == "mantener"  # diferencia de 0.5 pp < banda de 2 pp


def test_clasificacion_no_puntua_suspendidas():
    filas = optimizador.clasificar([{"nombre": "A", "tipo": "acciones", "estado": "suspendida", "motivos": ["x"]},
                                    {"nombre": "B", "tipo": "mixta", "estado": "calculada", "puntuacion": {"total": 50}}], {})
    assert filas[0]["alternativa"] == "B" and filas[0]["posicion"] == 1 and filas[1]["posicion"] is None
