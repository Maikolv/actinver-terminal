"""Conciliación con el portal: efectivo e invertido, no solo el total; y horario del día en el plan de Telegram."""
from datetime import UTC, date, datetime

import pandas as pd

from terminal import alertas, resumen

CARTERA_LOCAL = {"valor_total": 1_000_000.0, "efectivo": 1_000_000.0, "valor_posiciones": 0.0, "posiciones": [], "etapa": "practica"}
AHORA = datetime(2026, 9, 30, 21, 0, tzinfo=UTC)


def _saldo(con, efectivo=229_883.38, invertido=611_625.09, por_liquidar=153_608.34):
    con.execute("INSERT INTO saldos_portal (capturado_en, hora_portal, etapa, valor_portafolio, efectivo, invertido, "
                "por_liquidar, nota) VALUES (?,?,?,?,?,?,?,?)",
                ("2026-09-30T20:50:00+00:00", "2026-09-30T14:45:00-06:00", "practica", 995_116.81, efectivo, invertido,
                 por_liquidar, "captura del usuario"))
    con.commit()


def _cond(con):
    cfg = {"diferencia_portal_pct": 0.01, "concentracion_aviso": 0.45}
    return next(c for c in alertas.reglas_reto(con, cfg, CARTERA_LOCAL, AHORA) if c.regla == "diferencia_portal")


def test_total_parecido_pero_efectivo_e_invertido_distintos_dispara(con):
    _saldo(con)  # total: −0.49 % (antes no alertaba); efectivo e invertido difieren ~77 % y ~61 % del valor
    c = _cond(con)
    assert c.activa and "efectivo" in c.motivo and "invertido" in c.motivo
    assert "1,000,000.00" in c.motivo and "229,883.38" in c.motivo and "611,625.09" in c.motivo


def test_sin_desglose_se_compara_solo_lo_disponible(con):
    _saldo(con, efectivo=None, invertido=None, por_liquidar=None)
    assert not _cond(con).activa  # solo el total (−0.49 %) por debajo del umbral


def test_plan_trae_hora_para_consultar_el_portal_y_para_retirarse():
    antes = resumen.horario_del_dia(date(2026, 10, 1))
    assert "07:30" in antes and "14:15" in antes and "14:00" in antes
    despues = resumen.horario_del_dia(date(2026, 11, 4))
    assert "08:30" in despues and "15:15" in despues
    assert "cierra el Reto" in resumen.horario_del_dia(date(2026, 11, 13))


def test_el_horario_aparece_en_el_mensaje():
    p = {"clave": "x", "nombre": "X", "puntuacion": {"total": 70, "criterios": []}, "datos_hasta": "2026-09-30",
         "pesos": [], "cambios": {"filas": []}}
    _, texto, _ = resumen.construir(p, {"fuente": "local", "posiciones": []}, None,
                                    pd.Timestamp("2026-09-30 21:00", tz="America/Mexico_City"), date(2026, 10, 1))
    assert "Consulta el portal" in texto and "Puedes retirarte" in texto
