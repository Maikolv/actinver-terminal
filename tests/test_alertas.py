"""Cada regla de alerta dispara en un escenario simulado; enfriamiento, histéresis y silencio se respetan."""
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from terminal import alertas

CFG = {"deriva_pp": 5.0, "deriva_rearme_pp": 3.0, "mejora_neta_min": 0.005, "stop_loss": -0.08, "take_profit": 0.15,
       "caida_desde_maximo": -0.10, "macro_horas": 24, "insider_valor_min_usd": 250000, "noticia_sentimiento_min": 1.0,
       "enfriamiento_horas": 6, "silenciar_fuera_de_horario": True, "notificar_escritorio": True}
# Martes 13-oct-2026 11:00 CDMX = 17:00 UTC: BMV abierta
ABIERTO = datetime(2026, 10, 13, 17, 0, tzinfo=UTC)
CERRADO = datetime(2026, 10, 13, 23, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def sin_notificaciones(monkeypatch):
    enviados = []
    monkeypatch.setattr(alertas.notificador, "enviar", lambda t, x, c: enviados.append((t, x)) or {"escritorio": "prueba"})
    return enviados


def _prop(dev, mejora, avisos=None):
    return {"clave": "acciones_ajuste", "lente": "ajuste", "nombre": "Solo acciones · Ajuste", "estado": "calculada",
            "avisos": avisos or [], "mejora_esperada": {"neta": mejora, "horizonte_sesiones": 30},
            "cambios": {"costo_total": 100.0, "filas": [{"id": "SIC:KO", "delta_pp": dev, "monto_mxn": 5000.0,
                                                         "accion": "comprar"}]}}


CART = {"n_operaciones": 3, "posiciones": []}


def test_deriva_con_histeresis_y_enfriamiento(con, sin_notificaciones):
    f = lambda dev, mej, t: alertas.procesar(con, alertas.reglas_deriva(con, CFG, CART, {"x": _prop(dev, mej)}), CFG, t)  # noqa: E731
    assert f(4.0, 0.02, ABIERTO) == []                         # bajo el umbral
    assert f(6.0, 0.001, ABIERTO) == []                        # deriva sin mejora neta suficiente
    nuevas = f(6.0, 0.02, ABIERTO)
    assert len(nuevas) == 1 and nuevas[0]["regla"] == "deriva" and len(sin_notificaciones) == 1
    assert f(4.0, 0.02, ABIERTO + timedelta(hours=1)) == []    # sigue activa (> 3 pp): no repite
    assert f(2.0, 0.02, ABIERTO + timedelta(hours=2)) == []    # se rearma al bajar de 3 pp
    assert f(7.0, 0.02, ABIERTO + timedelta(hours=3)) == []    # rearmada pero en enfriamiento (6 h)
    f(2.0, 0.02, ABIERTO + timedelta(hours=4))
    assert len(f(7.0, 0.02, ABIERTO + timedelta(hours=10))) == 1  # fuera del enfriamiento: dispara
    a = alertas.listar(con)[0]
    assert a["simulacion"] == [{"id": "SIC:KO", "monto": 5000.0}] and a["fuente"] and a["accion"]


def test_propuesta_no_actual_no_genera_deriva(con):
    assert alertas.procesar(con, alertas.reglas_deriva(con, CFG, CART, {"x": _prop(9, 0.05, ["no actual"])}), CFG, ABIERTO) == []


def test_stop_take_y_caida_desde_maximo(con):
    pos = [{"instrumento_id": "SIC:KO", "clave_operable": "KO *", "precio_mxn": 90.0, "costo_promedio": 100.0,
            "valor_mxn": 900.0, "vigencia": "vigente", "proveedor": "tiingo", "fecha_precio": "2026-10-12"},
           {"instrumento_id": "SIC:V", "clave_operable": "V *", "precio_mxn": 120.0, "costo_promedio": 100.0,
            "valor_mxn": 1200.0, "vigencia": "vigente", "proveedor": "tiingo", "fecha_precio": "2026-10-12"}]
    hist = pd.DataFrame({"SIC:KO": [100.0, 110.0, 90.0], "SIC:V": [100, 125, 120]},
                        index=pd.to_datetime(["2026-10-01", "2026-10-05", "2026-10-12"]))
    conds = alertas.reglas_posicion(con, CFG, {"posiciones": pos}, hist, {"SIC:KO": "2026-10-01", "SIC:V": "2026-10-01"})
    reglas = {(n["regla"], n["clave"]) for n in alertas.procesar(con, conds, CFG, ABIERTO)}
    assert ("stop_loss", "SIC:KO") in reglas and ("take_profit", "SIC:V") in reglas and ("caida_maximo", "SIC:KO") in reglas


def test_macro_insider_noticia_una_sola_vez(con):
    con.execute("INSERT INTO eventos_macro VALUES ('e1', ?, 'USD', 'FOMC Statement', 'High', '', '', 'forexfactory', ?)",
                ((ABIERTO + timedelta(hours=5)).isoformat(), ABIERTO.isoformat()))
    con.execute("INSERT INTO insiders VALUES ('i1','SIC:KO','2026-10-10','Jane Doe','CEO','S',10000,60,600000,'https://sec.gov/x','sec_edgar',?)",
                (ABIERTO.isoformat(),))
    con.execute("INSERT INTO noticias VALUES ('n1','SIC:KO','Coca-Cola downgraded after guidance cut','https://seekingalpha.com/x',?,"
                "'seekingalpha_rss','alto',-1.0,'léxico',?)", ((ABIERTO - timedelta(hours=2)).isoformat(), ABIERTO.isoformat()))
    con.commit()
    conds = lambda: (alertas.reglas_macro(con, CFG, ABIERTO) + alertas.reglas_insider(con, CFG, {"SIC:KO"}, ABIERTO)  # noqa: E731
                     + alertas.reglas_noticias(con, CFG, {"SIC:KO"}, ABIERTO))
    assert {n["regla"] for n in alertas.procesar(con, conds(), CFG, ABIERTO)} == {"macro", "insider", "noticia"}
    assert alertas.procesar(con, conds(), CFG, ABIERTO + timedelta(hours=8)) == []  # eventos puntuales no se repiten


def test_alerta_tecnica_y_silencio_fuera_de_horario(con, sin_notificaciones):
    cart = {"posiciones": [{"instrumento_id": "SIC:KO", "vigencia": "vencido", "etiqueta_vigencia": "Dato vencido",
                            "fecha_precio": "2026-09-01"}]}
    conds = alertas.reglas_tecnicas(con, CFG, cart, {"x": {"nombre": "P", "estado": "suspendida", "motivos": ["sin datos"]}},
                                    {"estado": "vigente"})
    nuevas = alertas.procesar(con, conds, CFG, CERRADO)
    assert {n["regla"] for n in nuevas} == {"dato_vencido", "propuesta_suspendida"}
    assert sin_notificaciones == []  # fuera de horario: registradas, no notificadas
    assert all(a["notificada"] == "silenciada_fuera_de_horario" for a in alertas.listar(con))


def test_agrupa_notificaciones(con, sin_notificaciones):
    conds = [alertas.Condicion("noticia", f"k{i}", True, titulo=f"t{i}", motivo="m") for i in range(4)]
    alertas.procesar(con, conds, CFG, ABIERTO)
    assert len(sin_notificaciones) == 1 and sin_notificaciones[0][0] == "4 alertas nuevas"
