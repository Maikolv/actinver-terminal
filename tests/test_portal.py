"""Captura del portal del Reto (copiar y pegar), cartera basada en ella y alertas de cambio y de plan (sin duplicados)."""
from datetime import UTC, datetime

import pytest

from terminal import alertas, cartera, mercado, notificador, portal, servicios
from terminal.alertas import Condicion

from conftest import sembrar_precios

TEXTO = ("Mi posición\n"
         "Emisora\tSerie\tTítulos\tCosto promedio\tPrecio actual\tValor de mercado\n"
         "AMX\tB\t5,000\t17.20\t17.55\t87,750.00\n"
         "AAPL\t*\t10\t4,100.00\t4,200.00\t42,000.00\n"
         "Total\t\t\t\t\t129,750.00\n"
         "Efectivo disponible:\t$870,250.00\n"
         "Valor del portafolio:\t$1,000,000.00\n")


def _ins(con):
    return mercado.instrumentos(con)


def test_interpreta_la_tabla_copiada_del_portal(con):
    r = portal.interpretar(TEXTO, _ins(con))
    assert r["valor_portafolio"] == 1_000_000 and r["efectivo"] == 870_250
    ids = {p["instrumento_id"]: p for p in r["posiciones"]}
    assert set(ids) == {"BMV:AMX", "SIC:AAPL"} and ids["BMV:AMX"]["titulos"] == 5000
    assert ids["SIC:AAPL"]["costo_promedio"] == 4100 and not r["advertencias"]


def test_advierte_si_no_cuadra_y_no_adivina_emisoras(con):
    t = TEXTO.replace("870,250.00", "800,000.00").replace("AAPL\t*", "NOEXISTE\t*")
    r = portal.interpretar(t, _ins(con))
    assert any("no cuadran" in a for a in r["advertencias"]) and r["no_reconocidas"] == ["NOEXISTE *"]
    with pytest.raises(portal.ErrorCaptura):
        portal.interpretar("texto sin tabla ni saldo", _ins(con))


def test_no_guarda_capturas_incompletas_o_incoherentes(con):
    hora = "2026-09-28T14:05"
    casos = (
        (TEXTO.replace("AAPL\t*", "NOEXISTE\t*"), None, None, "emisoras sin reconocer"),
        (TEXTO.replace("870,250.00", "800,000.00"), None, None, "no cuadran"),
        (TEXTO.replace("Efectivo disponible:\t$870,250.00\n", ""), None, None, "efectivo"),
        ("", 800_000, 1_000_000, "faltan posiciones"),
    )
    for texto, efectivo, total, mensaje in casos:
        r = portal.guardar(con, texto, hora, _ins(con), efectivo=efectivo,
                           valor_portafolio=total, confirmar=True)
        assert not r["confirmado"] and any(mensaje in e for e in r["errores"])
    assert con.execute("SELECT COUNT(*) FROM capturas_portal").fetchone()[0] == 0


def test_no_retrocede_a_una_captura_anterior(con):
    portal.guardar(con, TEXTO, "2026-09-28T15:00", _ins(con), confirmar=True)
    r = portal.guardar(con, TEXTO, "2026-09-28T14:05", _ins(con), confirmar=True)
    assert not r["confirmado"] and any("anterior" in e for e in r["errores"])
    assert con.execute("SELECT COUNT(*) FROM capturas_portal").fetchone()[0] == 1


def test_conserva_valor_copiado_si_falta_precio_de_la_terminal(con):
    texto = TEXTO.replace("Precio actual\t", "").replace("17.55\t", "").replace("4,200.00\t", "")
    r = portal.guardar(con, texto, "2026-09-28T14:05", _ins(con), confirmar=True)
    assert r["confirmado"]
    c = portal.cartera(con, {}, portal.captura(con))
    assert c["valor_total"] == 1_000_000 and c["sin_precio"] == []
    assert all(p["origen_precio"] == "valor_portal" for p in c["posiciones"])


def test_vista_previa_guardado_y_duplicado(con):
    prev = portal.guardar(con, TEXTO, "2026-09-28T14:05", _ins(con))
    assert not prev["confirmado"] and not prev["errores"]
    assert con.execute("SELECT COUNT(*) FROM capturas_portal").fetchone()[0] == 0          # la vista previa no guarda
    r = portal.guardar(con, TEXTO, "2026-09-28T14:05", _ins(con), confirmar=True)
    assert r["confirmado"] and con.execute("SELECT COUNT(*) FROM posiciones_portal").fetchone()[0] == 2
    assert con.execute("SELECT COUNT(*) FROM saldos_portal").fetchone()[0] == 1           # conciliación existente
    assert portal.guardar(con, TEXTO, "2026-09-28T14:05", _ins(con), confirmar=True)["errores"]
    assert portal.guardar(con, TEXTO, "2099-01-01T10:00", _ins(con))["errores"]            # hora en el futuro


def test_la_cartera_usa_la_cuenta_del_reto_y_la_distingue_del_registro_local(con, ajustes):
    sembrar_precios(con, ["BMV:AMX", "SIC:AAPL"], sesiones=80)
    cartera.registrar(con, cartera.validar({"fecha": "2026-09-28", "tipo": "aportacion", "monto": 1_000_000}, _ins(con)), "manual")
    con.commit()
    assert servicios.cartera_actual(con, ajustes)["fuente"] == "local"
    portal.guardar(con, TEXTO, "2026-09-28T14:05", _ins(con), confirmar=True)
    c = servicios.cartera_actual(con, ajustes)
    assert c["fuente"] == "portal" and c["efectivo"] == 870_250
    assert {p["instrumento_id"]: p["cantidad"] for p in c["posiciones"]} == {"BMV:AMX": 5000, "SIC:AAPL": 10}
    s = servicios.seguimiento(con, ajustes)
    assert s["registro_local"]["valor_total"] == 1_000_000                               # el local se conserva aparte


def _cfg():
    return {"enfriamiento_horas": 6, "silenciar_fuera_de_horario": True, "notificar_telegram": True}


def test_alerta_de_cambio_en_el_portal_una_sola_vez_y_fuera_de_horario(con, monkeypatch):
    enviados = []
    monkeypatch.setattr(notificador, "enviar", lambda t, x, c, detalle=None: enviados.append(detalle) or {"telegram": "enviada"})
    noche = datetime(2026, 9, 29, 3, 0, tzinfo=UTC)                                      # lunes 21:00 CDMX: BMV cerrada
    portal.guardar(con, TEXTO, "2026-09-28T14:05", _ins(con), confirmar=True)
    alertas.procesar(con, alertas.reglas_portal(con, noche), _cfg(), noche)
    assert len(enviados) == 1 and "Primera captura" in enviados[0]                        # se entrega aunque sea de noche
    assert "fuente: captura manual del portal" in enviados[0] and "detectada 28-09-2026 21:00 (CDMX)" in enviados[0]
    alertas.procesar(con, alertas.reglas_portal(con, noche), _cfg(), noche)
    assert len(enviados) == 1                                                              # sin duplicados
    t2 = TEXTO.replace("5,000\t17.20\t17.55\t87,750.00", "3,000\t17.20\t17.55\t52,650.00").replace("870,250.00", "905,350.00")
    portal.guardar(con, t2, "2026-09-28T15:00", _ins(con), confirmar=True)
    alertas.procesar(con, alertas.reglas_portal(con, noche), _cfg(), noche)
    assert len(enviados) == 2 and "AMX: 5,000 → 3,000 títulos" in enviados[1] and "Efectivo: 870,250.00 → 905,350.00" in enviados[1]


def test_alerta_de_plan_de_propuesta_solo_cuando_cambia_el_plan(con, monkeypatch):
    enviados = []
    monkeypatch.setattr(notificador, "enviar", lambda t, x, c, detalle=None: enviados.append(detalle) or {})
    def prop(filas, total=80.0):
        return {"mixta_puntuacion": {"clave": "mixta_puntuacion", "nombre": "Mixta · Máxima puntuación", "estado": "calculada",
                                     "avisos": [], "puntuacion": {"total": total}, "datos_hasta": "2026-09-28",
                                     "cambios": {"filas": filas, "costo_total": 100.0}}}
    compra = {"id": "BMV:AMX", "clave_operable": "AMX B", "accion": "comprar", "monto_mxn": 50000.0, "delta_pp": 5.0}
    hora = datetime(2026, 9, 29, 16, 0, tzinfo=UTC)
    for _ in range(2):
        alertas.procesar(con, alertas.reglas_plan_propuesta({"fuente": "local"}, prop([compra])), _cfg(), hora)
    assert len(enviados) == 1 and "Comprar AMX B ≈ 50,000 MXN" in enviados[0] and "registro local" in enviados[0]
    venta = {**compra, "id": "SIC:AAPL", "clave_operable": "AAPL *", "accion": "vender", "monto_mxn": -20000.0, "delta_pp": -2.0}
    alertas.procesar(con, alertas.reglas_plan_propuesta({"fuente": "portal"}, prop([compra, venta])), _cfg(), hora)
    assert len(enviados) == 2 and "Vender AAPL *" in enviados[1] and "tu cuenta del Reto" in enviados[1]


def test_recordatorio_de_captura_al_cierre(con):
    despues = datetime(2026, 9, 28, 21, 30, tzinfo=UTC)                                  # 15:30 CDMX, lunes de práctica
    conds = [c for c in alertas.reglas_portal(con, despues) if c.regla == "captura_pendiente"]
    assert conds and conds[0].activa
    portal.guardar(con, TEXTO, "2026-09-28T14:05", _ins(con), confirmar=True)
    conds = [c for c in alertas.reglas_portal(con, despues) if c.regla == "captura_pendiente"]
    assert not conds[0].activa


def test_nuevo_plan_reemplaza_la_alerta_de_plan_anterior(con, monkeypatch):
    """Cada recálculo con otras órdenes crea un aviso nuevo; el anterior ya no aplica y no debe seguir como «nueva»."""
    monkeypatch.setattr(notificador, "enviar", lambda *a, **k: {})
    def prop(filas):
        return {"mixta_puntuacion": {"clave": "mixta_puntuacion", "nombre": "Mixta", "estado": "calculada", "avisos": [],
                                     "puntuacion": {"total": 80.0}, "cambios": {"filas": filas, "costo_total": 1.0}}}
    compra = {"id": "BMV:AMX", "clave_operable": "AMX B", "accion": "comprar", "monto_mxn": 50000.0, "delta_pp": 5.0}
    otra = {**compra, "id": "BMV:WALMEX", "clave_operable": "WALMEX *"}
    hora = datetime(2026, 9, 29, 16, 0, tzinfo=UTC)
    alertas.procesar(con, alertas.reglas_plan_propuesta({"fuente": "local"}, prop([compra])), _cfg(), hora)
    alertas.procesar(con, alertas.reglas_plan_propuesta({"fuente": "local"}, prop([otra])), _cfg(), hora)
    vivas = con.execute("SELECT clave FROM alertas WHERE regla='plan_propuesta' AND estado='nueva'").fetchall()
    assert len(vivas) == 1 and "mixta_puntuacion:" in vivas[0][0]
    assert con.execute("SELECT COUNT(*) FROM alertas WHERE regla='plan_propuesta' AND estado='caducada'").fetchone()[0] == 1
