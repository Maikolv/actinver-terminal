"""Avisos escalonados de pérdida del día con precios en vivo: solo informan, nunca operan."""
from datetime import UTC, datetime

import pandas as pd

from terminal import alertas

AHORA = datetime(2026, 10, 19, 16, 0, tzinfo=UTC)          # 10:00 CDMX
CFG = {"perdida_dia_cartera_pct": 0.005, "perdida_dia_posicion_pct": 0.01, "enfriamiento_horas": 4,
       "silenciar_fuera_de_horario": True}


def _cartera(px_mu, fecha_mu="2026-10-19", px_gm=100.0):
    return {"efectivo": 1000.0, "posiciones": [
        {"instrumento_id": "SIC:MU", "clave_operable": "MU *", "cantidad": 10, "precio_mxn": px_mu, "fecha_precio": fecha_mu,
         "proveedor": "alpaca_vivo"},
        {"instrumento_id": "BMV:GMEXICO", "clave_operable": "GMEXICO B", "cantidad": 10, "precio_mxn": px_gm,
         "fecha_precio": "2026-10-16", "proveedor": "eodhd"}]}


HIST = pd.DataFrame({"SIC:MU": [990.0, 1000.0], "BMV:GMEXICO": [99.0, 100.0]},
                    index=pd.to_datetime(["2026-10-15", "2026-10-16"]))


def test_variacion_usa_solo_precios_de_hoy():
    v = alertas.variacion_dia(_cartera(970.0), HIST, AHORA)
    mu = next(f for f in v["posiciones"] if f["clave"] == "MU *")
    assert abs(mu["variacion"] + 0.03) < 1e-12 and mu["impacto_mxn"] == -300
    assert v["sin_dato_hoy"] == ["GMEXICO B"]                      # la BMV sin precio de hoy no se inventa
    assert abs(v["variacion"] - (-300 / (10000 + 1000 + 1000))) < 1e-12


def test_escalones_de_cartera_y_posicion():
    c = alertas.reglas_perdida_dia(CFG, _cartera(970.0), HIST, AHORA)
    claves = {x.clave for x in c}
    assert "cartera|2026-10-19|5" in claves                        # −2.5 % / 0.5 % = escalón 5
    assert "SIC:MU|2026-10-19|3" in claves                         # −3 % / 1 % = escalón 3
    assert all(x.regla == "perdida_dia" and "tuyas" in x.accion for x in c)
    assert alertas.reglas_perdida_dia(CFG, _cartera(1000.0), HIST, AHORA) == []          # sin pérdida
    assert alertas.reglas_perdida_dia(CFG, _cartera(970.0, fecha_mu="2026-10-16"), HIST, AHORA) == []  # precio viejo
    assert alertas.reglas_perdida_dia({**CFG, "perdida_dia_activa": False}, _cartera(970.0), HIST, AHORA) == []


def test_cada_escalon_avisa_una_vez(con, monkeypatch):
    enviados = []
    monkeypatch.setattr(alertas.notificador, "enviar", lambda t, x, cfg, detalle=None: enviados.append(t) or {"telegram": "enviada"})
    n1 = alertas.procesar(con, alertas.reglas_perdida_dia(CFG, _cartera(985.0), HIST, AHORA), CFG, AHORA)
    n2 = alertas.procesar(con, alertas.reglas_perdida_dia(CFG, _cartera(985.0), HIST, AHORA), CFG, AHORA)
    n3 = alertas.procesar(con, alertas.reglas_perdida_dia(CFG, _cartera(975.0), HIST, AHORA), CFG, AHORA)
    assert len(n1) == 2 and n2 == [] and len(n3) == 2              # mismo escalón: silencio; escalón nuevo: aviso
    assert len(enviados) == 2                                      # se notifica (perdida_dia no se silencia)
