"""Plan del día y boletas en lenguaje sencillo (Telegram): qué hacer, en qué orden y con qué tope de precio."""
from datetime import UTC, date, datetime

import pandas as pd

from terminal import boleta, mensaje_simple as ms

AHORA = pd.Timestamp(datetime(2026, 10, 6, 12, 0, tzinfo=UTC)).tz_convert(ms.ZONA)  # mar 06-10 06:00 CDMX
PROP = {"clave": "acciones_rendimiento", "escenarios": {"central_p50": 0.031, "adverso_p10": -0.062}}


def _accion(clave, decision, cantidad=None, limite=None, monto=0.0, estado="vigente", referencia=None, tenencia=0,
            propuesta=None):
    return {"clave": clave, "decision": decision, "accion_propuesta": propuesta or decision, "cantidad": cantidad,
            "precio_limite": limite, "monto": monto, "titulos_actuales": tenencia, "referencia": referencia,
            "precio": {"estado": estado, "es_referencia": clave.endswith("*")}}


def _plan(acciones, confirmada=True, hora="2026-10-05T15:08:00-06:00", errores=()):
    return {"cuenta": {"confirmada": confirmada, "hora_portal": hora, "efectivo": 37128.69, "valor_total": 999136.55},
            "acciones": acciones, "reglas": {"activo": True, "min_emisoras": 5, "max_peso_emisora": 0.5,
                                             "errores": list(errores), "avisos": []}}


def test_ventas_antes_que_compras_con_tope_de_precio_y_sin_jerga():
    plan = _plan([_accion("MU *", "comprar", 2, 19400.0, 38800.0),
                  _accion("ALPEK A", "vender", 3394, 14.6, 49552.4, estado="retrasado", tenencia=3394)])
    t = ms.construir(plan, PROP, [], AHORA, date(2026, 10, 6), 29)
    assert t.startswith("📋 Qué hacer hoy, martes 06-10 (quedan 29 días de Reto)")
    assert t.index("VENDE") < t.index("COMPRA")
    assert "ALPEK A: vende 3,394 acciones (todas las que tienes), a no menos de $14.60" in t
    assert "MU: compra 2 acciones, pagando como máximo $19,400.00" in t
    assert "ALPEK A" in t.split("Ojo:")[1]          # precio retrasado señalado
    assert "lo más común +3.1%" in t and "-6.2%" in t   # rango al cierre del Reto, como estimación
    for jerga in ("p10", "p50", "banda", "pp", "SIC", "peso objetivo", "rebalanceo"):
        assert jerga not in t, jerga


def test_sin_cuenta_confirmada_pide_la_captura_y_no_da_cantidades():
    t = ms.construir(_plan([_accion("MU *", "pendiente", propuesta="comprar")], confirmada=False), PROP, [], AHORA)
    assert "captura de tu portafolio" in t and "No compres ni vendas" in t and "MU" not in t


def test_sin_propuesta_dice_que_no_cambie_nada():
    t = ms.construir(None, None, [], AHORA)
    assert "NO cambies nada" in t and "/plan" in t


def test_captura_vieja_y_cartera_al_dia():
    t = ms.construir(_plan([_accion("MU *", "mantener")], hora="2026-09-30T15:00:00-06:00"), PROP, [], AHORA)
    assert "captura es vieja" in t and "no tienes que hacer nada" in t


def test_condicional_y_pendientes_sin_dato():
    ref = {"lado_sugerido": "compra", "titulos_aprox": 3, "precio_min": 900.0, "precio_max": 950.0}
    plan = _plan([_accion("AMD *", "pendiente", referencia=ref, propuesta="comprar"),
                  _accion("FUNO 11", "pendiente", propuesta="comprar")])
    t = ms.construir(plan, PROP, [], AHORA)
    assert "AMD: compra unas 3 acciones si cuesta entre $900.00 y $950.00; precio límite $950.00" in t
    assert "No toques hoy" in t and "FUNO 11" in t
    venta = {"lado_sugerido": "venta", "titulos_aprox": 15, "precio_min": 18900.0, "precio_max": 19700.0}
    compra = {"lado_sugerido": "compra", "titulos_aprox": 93, "precio_min": 2060.0, "precio_max": 2150.0}
    t = ms.construir(_plan([_accion("INTC *", "pendiente", referencia=compra, propuesta="comprar"),
                            _accion("MU *", "pendiente", referencia=venta, propuesta="vender")]), PROP, [], AHORA)
    assert t.index("MU: vende") < t.index("INTC: compra") and "precio límite $18,900.00" in t
    assert "Haz primero las ventas: lo que te queda ($37,129) no alcanza" in t


def test_regla_del_reto_incumplida_se_avisa():
    t = ms.construir(_plan([], errores=["La propuesta tiene 4 emisoras; el mínimo es 5."]), PROP, [], AHORA)
    assert "⚠️ Regla del Reto: La propuesta tiene 4 emisoras" in t


def test_evento_macro_en_palabras_sencillas(con):
    con.execute("INSERT INTO eventos_macro (id, fecha, pais, titulo, impacto, fuente, obtenido_en) VALUES "
                "('e1', '2026-10-07T14:00:00-04:00', 'USD', 'FOMC Meeting Minutes', 'High', 'forexfactory', '2026-10-06'),"
                "('e2', '2026-10-07T08:30:00-04:00', 'EUR', 'German CPI', 'High', 'forexfactory', '2026-10-06'),"
                "('e3', '2026-10-20T08:30:00-04:00', 'USD', 'CPI m/m', 'High', 'forexfactory', '2026-10-06')")
    ev = ms.eventos_macro(con, AHORA.to_pydatetime(), horas=48)
    assert [e["titulo"] for e in ev] == ["FOMC Meeting Minutes"]          # solo EE. UU./México y dentro de 48 h
    t = ms.construir(_plan([_accion("MU *", "comprar", 1, 19400.0, 19400.0)]), PROP, ev, AHORA)
    assert "Mañana a las 12:00: minutas de la Reserva Federal de EE. UU." in t and "no subas tu precio máximo" in t
    assert ms.traducir_evento("Unknown Thing", "MXN") == "dato económico de México (Unknown Thing)"


def test_boletas_sencillas_ventas_primero():
    vence = "2026-10-06T20:00:00+00:00"
    bs = [{"id": 2, "tipo": "considerar compra", "lado": "compra", "cantidad": 2, "precio_limite": 19400.0,
           "emisora_serie": "MU *", "instrumento_id": "SIC:MU", "caduca_en": vence},
          {"id": 1, "tipo": "considerar venta", "lado": "venta", "cantidad": 3394, "precio_limite": 14.6,
           "emisora_serie": "ALPEK A", "instrumento_id": "BMV:ALPEK", "caduca_en": vence}]
    t = boleta.texto_telegram_simple(bs)
    assert t.index("VENDE ALPEK A") < t.index("COMPRA MU") and "Primero las ventas" in t
    assert "(no pagues más)" in t and "(no vendas más barato)" in t and "válidas hasta 06-10 14:00" in t
    assert boleta.texto_telegram_simple([]).startswith("No hay órdenes")


def test_si_mantener_es_mejor_dice_que_no_cambie_nada():
    mm = {"propuesta": 0.070, "mantener": 0.076, "costo": 0.001, "neta": -0.007, "margen": 0.01, "metrica": "ganancia promedio",
          "adverso_propuesta": -0.127, "adverso_mantener": -0.167}
    plan = {**_plan([_accion("MU *", "mantener", tenencia=25)]), "mantener_mejor": mm}
    t = ms.construir(plan, PROP, [], AHORA)
    assert "Hoy no cambies nada" in t and "+7.6%" in t and "+7.0%" in t and "-16.7%" in t
    assert "VENDE" not in t and "COMPRA" not in t and "Qué esperar" not in t
    assert "Antes de capturar" not in t and "Para tener en cuenta" in t
