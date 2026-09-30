"""Reglas del Reto Actinver 2026 cargadas de config/reto.yaml y aplicadas a propuestas y simulaciones."""
from datetime import datetime

import pytest
from conftest import sembrar_precios

from terminal import importar, mercado, optimizador, reto, servicios

MX = reto.MX
VACIA = {"valor_total": 0, "posiciones": []}


def test_reglas_oficiales_cargadas():
    c = reto.config()
    assert c["capital"] == 1_000_000
    assert c["fechas"]["competencia_inicio"].startswith("2026-10-05")
    assert c["fechas"]["competencia_fin"].startswith("2026-11-13T15:00")
    assert c["reglas"]["min_emisoras"] == 5 and c["reglas"]["max_peso_emisora"] == 0.5
    assert reto.costo_operacion() == pytest.approx(0.0010 * 1.16)
    assert "reglas.min_operaciones" in reto.reglas_sin_confirmar()  # regla no publicada: visible como sin confirmar


def test_etapas_y_sesiones_restantes():
    assert reto.etapa(datetime(2026, 9, 23, 12, tzinfo=MX)) == "inscripcion"
    assert reto.etapa(datetime(2026, 9, 30, 12, tzinfo=MX)) == "practica"
    assert reto.etapa(datetime(2026, 10, 20, 12, tzinfo=MX)) == "competencia"
    assert reto.etapa(datetime(2026, 11, 13, 16, tzinfo=MX)) == "concluido"
    # del 5 oct al 13 nov: 30 días hábiles menos el 2 de noviembre (festivo BMV) = 29 sesiones
    assert reto.sesiones_restantes(datetime(2026, 9, 23, tzinfo=MX)) == 29
    assert reto.sesiones_restantes(datetime(2026, 11, 14, tzinfo=MX)) == 0


def test_cumplimiento():
    ok = reto.cumplimiento({f"X{i}": 0.2 for i in range(5)})
    assert all(r["cumple"] for r in ok)
    mal = reto.cumplimiento({"A": 0.6, "B": 0.4})
    assert [r["cumple"] for r in mal] == [False, False]


ACC = ["SIC:AAPL", "SIC:MSFT", "SIC:KO", "SIC:JNJ", "BMV:WALMEX", "BMV:GFNORTE", "BMV:AMX", "SIC:XOM", "SIC:PG", "SIC:V"]


def test_lentes_cumplen_reglas_y_difieren(con, ajustes):
    sembrar_precios(con, ACC + ["SIC:IVV", "FONDO:ACTIGOB", "FONDO:ACTIMED"])
    perfil = {**ajustes["perfil"], "capital": 1_000_000}
    r = optimizador.proponer(con, ajustes, perfil, "acciones", VACIA, lente="rendimiento")
    a = optimizador.proponer(con, ajustes, perfil, "acciones", VACIA, lente="ajuste")
    for p in (r, a):
        assert p["estado"] == "calculada" and all(c["cumple"] for c in p["cumplimiento_reto"])
        assert p["reproducibilidad"]["horizonte_origen"].startswith("Reto")
        assert "solo por splits" in p["reproducibilidad"]["precios"]
    assert max(x["peso"] for x in r["pesos"]) <= 0.2 + 1e-6
    assert r["mejora_esperada"]["esperado_propuesta"] >= a["mejora_esperada"]["esperado_propuesta"] - 1e-9
    assert r["reproducibilidad"]["aversion_riesgo_lambda"] < a["reproducibilidad"]["aversion_riesgo_lambda"]


def test_costo_del_reto_en_cambios(con, ajustes):
    ins = mercado.instrumentos(con)
    assert optimizador.costo_unitario(ins["BMV:WALMEX"], ajustes) == pytest.approx(0.00116 + 0.0020)


def test_universo_del_simulador_restringe(con, ajustes):
    sembrar_precios(con, ACC)
    csv = "clave,tipo\nWALMEX *,accion\nAAPL *,accion\nMSFT *,accion\nKO *,accion\nJNJ *,accion\nXYZINVENTADA,accion\n".encode()
    prev = importar.importar(con, csv, "sim.csv", "universo", mercado.instrumentos(con))
    assert prev["aceptables"] == 5 and prev["rechazadas"] == 1 and not prev["confirmado"]
    importar.importar(con, csv, "sim.csv", "universo", mercado.instrumentos(con), confirmar=True)
    p = optimizador.proponer(con, ajustes, ajustes["perfil"], "acciones", VACIA)
    assert set(p["reproducibilidad"]["universo"]) <= {"BMV:WALMEX", "SIC:AAPL", "SIC:MSFT", "SIC:KO", "SIC:JNJ"}
    assert any("simulador" in e["motivo"] for e in p["excluidos"])
    assert "NO CUMPLE SU PERFIL" in p["riesgos"][0]   # 1 emisora en pesos no alcanza el mínimo en MXN: se declara


def test_simular_aplica_costos_y_poder_de_compra(con, ajustes):
    sembrar_precios(con, ACC)
    from terminal import cartera
    cartera.registrar(con, cartera.validar({"fecha": "2024-01-02", "tipo": "aportacion", "monto": 10000},
                                           mercado.instrumentos(con)), "manual")
    con.commit()
    s = servicios.simular(con, ajustes, [{"id": "BMV:WALMEX", "monto": 5000}, {"id": "SIC:AAPL", "monto": 20000}])
    assert s["operaciones"][0]["titulos"] > 0 and s["costo_total"] > 0
    assert any("Poder de compra" in a for a in s["avisos"])
