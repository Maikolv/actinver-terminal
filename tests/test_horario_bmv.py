"""Horario BMV del Reto: 07:30–14:00 hasta el 2-nov-2026 y 08:30–15:00 desde el 3-nov (bases §8).

exchange_calendars fija XMEX en 08:30–15:00 todo el año; sin corregirlo, entre las 14:00 y las 15:00 la terminal creía
abierta la bolsa (cierres de hoy «pendientes») y de 07:30 a 08:30 la creía cerrada."""
from datetime import UTC, date, datetime

from terminal import vigencia


def _utc(y, m, d, h, mi):  # hora de la Ciudad de México (UTC−6, sin horario de verano)
    return datetime(y, m, d, h + 6, mi, tzinfo=UTC)


def test_bmv_cierra_a_las_14_hasta_el_2_de_noviembre():
    assert vigencia.ultima_sesion_cerrada("XMEX", _utc(2026, 9, 30, 14, 30)) == date(2026, 9, 30)
    assert vigencia.ultima_sesion_cerrada("XMEX", _utc(2026, 9, 30, 13, 59)) == date(2026, 9, 29)
    assert not vigencia.mercado_abierto("XMEX", _utc(2026, 9, 30, 14, 30))
    assert vigencia.mercado_abierto("XMEX", _utc(2026, 9, 30, 7, 45))
    assert vigencia.cierre_de_sesion("XMEX", date(2026, 9, 30)) == _utc(2026, 9, 30, 14, 0)


def test_bmv_desde_el_3_de_noviembre_opera_de_8_30_a_15():
    assert not vigencia.mercado_abierto("XMEX", _utc(2026, 11, 4, 8, 0))
    assert vigencia.mercado_abierto("XMEX", _utc(2026, 11, 4, 14, 30))
    assert vigencia.ultima_sesion_cerrada("XMEX", _utc(2026, 11, 4, 14, 30)) == date(2026, 11, 3)


def test_festivos_siguen_del_calendario():
    assert not vigencia.mercado_abierto("XMEX", _utc(2026, 11, 16, 10, 0))  # día de la Revolución (tercer lunes)
