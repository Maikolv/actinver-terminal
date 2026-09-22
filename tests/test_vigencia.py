"""Cada dato tiene estado de vigencia; festivos y horarios de mercado se respetan."""
from datetime import UTC, datetime

from terminal import vigencia

U = {"cierre_sesiones_vigente": 0, "cierre_sesiones_retrasado": 1, "nav_sesiones_vigente": 1, "nav_sesiones_retrasado": 3,
     "fx_sesiones_vigente": 1, "fx_sesiones_retrasado": 5, "retrasado_minutos_vigente": 20, "tiempo_real_segundos_vigente": 120}


def test_festivo_bmv_16_septiembre():
    cal = vigencia.calendario("XMEX")
    assert not cal.is_session("2026-09-16") and vigencia.calendario("XNYS").is_session("2026-09-16")


def test_ultima_sesion_cerrada_respeta_horario():
    antes_cierre = datetime(2026, 9, 22, 19, 0, tzinfo=UTC)   # 15:00 NY, mercado abierto
    despues_cierre = datetime(2026, 9, 22, 21, 0, tzinfo=UTC)  # 17:00 NY
    assert vigencia.ultima_sesion_cerrada("XNYS", antes_cierre).isoformat() == "2026-09-21"
    assert vigencia.ultima_sesion_cerrada("XNYS", despues_cierre).isoformat() == "2026-09-22"


def test_estados_de_cierre():
    ahora = datetime(2026, 9, 23, 22, 0, tzinfo=UTC)  # tras el cierre del miércoles 23
    assert vigencia.evaluar("cierre", "2026-09-23", "XNYS", U, ahora=ahora)["estado"] == "vigente"
    assert vigencia.evaluar("cierre", "2026-09-22", "XNYS", U, ahora=ahora)["estado"] == "retrasado"
    r = vigencia.evaluar("cierre", "2026-09-18", "XNYS", U, ahora=ahora)
    assert r["estado"] == "vencido" and r["etiqueta"] == "Dato vencido"
    assert vigencia.evaluar(None, None, "XNYS", U)["etiqueta"] == "Sin datos suficientes"


def test_festivo_no_cuenta_como_atraso():
    # El 16 de septiembre no hay sesión en la BMV: un cierre del 15 sigue vigente al día 16 por la noche
    ahora = datetime(2026, 9, 17, 3, 0, tzinfo=UTC)
    assert vigencia.evaluar("cierre", "2026-09-15", "XMEX", U, ahora=ahora)["estado"] == "vigente"


def test_nav_y_fx_tienen_tolerancias_propias():
    ahora = datetime(2026, 9, 23, 22, 0, tzinfo=UTC)
    assert vigencia.evaluar("nav", "2026-09-22", "XMEX", U, ahora=ahora)["estado"] == "vigente"
    assert vigencia.evaluar("fx", "2026-09-18", "XMEX", U, ahora=ahora)["estado"] in ("retrasado",)


def test_sintetico_nunca_es_actual():
    assert vigencia.evaluar("sintetico", "2026-09-22", "XNYS", U)["estado"] == "sintetico"


def test_retraso_medido_en_horas():
    ahora = datetime(2026, 9, 23, 22, 0, tzinfo=UTC)
    r = vigencia.evaluar("cierre", "2026-09-23", "XNYS", U, ahora=ahora)
    assert r["retraso_horas"] == 2.0  # cierre 20:00 UTC
