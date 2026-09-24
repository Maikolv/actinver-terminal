"""Lente «Máxima puntuación», filtro de mercado (nacionales/extranjeras), ranking y entrega de alertas diferidas."""
from datetime import UTC, datetime

from terminal import alertas, optimizador, ranking, servicios
from terminal.alertas import Condicion

from conftest import sembrar_precios


def _preparar(con):
    ids = [r[0] for pref in ("BMV:%", "SIC:%") for r in con.execute(
        "SELECT id FROM instrumentos WHERE id LIKE ? AND estado='activo' AND clase='accion' ORDER BY id LIMIT 8", (pref,))]
    sembrar_precios(con, ids, sesiones=300)
    return ids


def test_lente_maxima_puntuacion_elige_con_una_mitad_y_verifica_con_otra(con, ajustes):
    _preparar(con)
    perfil = servicios.perfil_actual(con, ajustes)
    cart = servicios.cartera_actual(con, ajustes)
    p = optimizador.proponer(con, ajustes, perfil, "acciones", cart, lente="puntuacion")
    assert p["estado"] == "calculada" and p["clave"] == "acciones_puntuacion"
    b = p["busqueda_puntuacion"]
    assert len(b["candidatos"]) == len(optimizador.CANDIDATOS_PUNTUACION)
    validos = [c for c in b["candidatos"] if "error" not in c]
    assert b["elegido"]["puntuacion_seleccion"] == max(c["puntuacion_seleccion"] for c in validos)  # se elige solo con la 1.ª mitad
    assert p["puntuacion"]["verificacion"] == b["elegido"]["puntuacion_verificacion"]
    assert all(c["tope"] <= 0.5 for c in b["candidatos"])                                          # regla del Reto
    assert len(p["pesos"]) >= 5


def test_filtro_de_mercado(con, ajustes):
    _preparar(con)
    cart = servicios.cartera_actual(con, ajustes)
    for merc, prefijo in (("nacionales", "BMV:"), ("extranjeras", "SIC:")):
        perfil = {**servicios.perfil_actual(con, ajustes), "mercado_acciones": merc}
        p = optimizador.proponer(con, ajustes, perfil, "acciones", cart, lente="ajuste")
        assert p["estado"] == "calculada" and all(a["id"].startswith(prefijo) for a in p["pesos"])
        assert any("elección de mercado" in e["motivo"] for e in p["excluidos"])


def test_ranking_ordena_y_filtra(con, ajustes):
    _preparar(con)
    r = ranking.calcular(con, ajustes)
    assert r["n"] >= 10 and [f["posicion"] for f in r["filas"]] == list(range(1, r["n"] + 1))
    punt = [f["puntuacion"] for f in r["filas"]]
    assert punt == sorted(punt, reverse=True) and 0 <= min(punt) and max(punt) <= 100
    assert all(f["mercado"].startswith("nacional") for f in ranking.calcular(con, ajustes, "nacionales")["filas"])
    ext = ranking.calcular(con, ajustes, "extranjeras")["filas"]
    assert ext and all(f["precio_es_referencia"] for f in ext)          # SIC: precio de referencia, rotulado


def test_alertas_silenciadas_se_entregan_al_abrir(con, monkeypatch):
    enviados = []
    monkeypatch.setattr(alertas.notificador, "enviar", lambda t, x, c, detalle=None: enviados.append(t) or {"escritorio": "ok"})
    cfg = {"enfriamiento_horas": 6, "silenciar_fuera_de_horario": True}
    cerrado = datetime(2026, 10, 9, 3, 0, tzinfo=UTC)           # jueves 21:00 en la Ciudad de México (BMV cerrada)
    alertas.procesar(con, [Condicion("concentracion", "BMV:AMX", True, "aviso", "Concentración AMX", "m")], cfg, cerrado)
    assert enviados == [] and con.execute("SELECT notificada FROM alertas").fetchone()[0] == "silenciada_fuera_de_horario"
    abierto = datetime(2026, 10, 9, 16, 0, tzinfo=UTC)           # viernes 10:00 con la BMV abierta (antes de caducar)
    nuevas = alertas.procesar(con, [], cfg, abierto)
    assert nuevas == [] and len(enviados) == 1                     # la diferida se entrega; no cuenta como nueva
    assert con.execute("SELECT notificada FROM alertas").fetchone()[0] != "silenciada_fuera_de_horario"
