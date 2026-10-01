"""Plan del día por Telegram: hora, días hábiles, una vez por sesión, títulos, cambios frente al día anterior y porqué."""
from datetime import UTC, datetime

from terminal import notificador, resumen

PROP = {"clave": "mixta_puntuacion", "nombre": "Mixta · Máxima puntuación", "estado": "calculada", "avisos": [],
        "datos_hasta": "2026-09-29",
        "puntuacion": {"total": 87.1, "criterios": [{"criterio": "diversificacion", "puntos": 100},
                                                    {"criterio": "liquidez", "puntos": 100},
                                                    {"criterio": "rendimiento_ajustado", "puntos": 84.7},
                                                    {"criterio": "costos", "puntos": 71.7}]},
        "pesos": [{"id": "BMV:ALPEK", "precio_mxn": 14.98, "motivos": ["Relación rendimiento/riesgo histórica 1.85."]},
                  {"id": "SIC:AAPL", "precio_mxn": 4200.0, "motivos": ["Diversifica: correlación media 0.21."]}],
        "cambios": {"costo_total": 180.0, "filas": [
            {"id": "BMV:ALPEK", "clave_operable": "ALPEK A", "accion": "comprar", "monto_mxn": 80682.0, "delta_pp": 8.1},
            {"id": "SIC:AAPL", "clave_operable": "AAPL *", "accion": "comprar", "monto_mxn": 42500.0, "delta_pp": 4.3},
            {"id": "BMV:AMX", "clave_operable": "AMX B", "accion": "mantener", "monto_mxn": 900.0, "delta_pp": 0.1}]},
        "riesgos": ["Concentración: las 3 mayores posiciones suman 36%."]}
MANANA = datetime(2026, 9, 30, 13, 5, tzinfo=UTC)          # miércoles 07:05 en la Ciudad de México


def test_toca_solo_en_sesion_habil_desde_la_hora_y_una_vez(ajustes):
    assert resumen.toca(ajustes, MANANA, {})
    assert not resumen.toca(ajustes, datetime(2026, 9, 30, 12, 55, tzinfo=UTC), {})       # 06:55: todavía no
    assert not resumen.toca(ajustes, MANANA, {"fecha": "2026-09-30"})                     # ya se envió hoy
    assert not resumen.toca(ajustes, datetime(2026, 10, 3, 14, 0, tzinfo=UTC), {})        # sábado


def test_plan_sin_cuenta_confirmada_no_da_ordenes_ejecutables():
    import pandas as pd
    local = pd.Timestamp(MANANA).tz_convert("America/Mexico_City")
    anterior = [{"id": "BMV:ALPEK", "clave": "ALPEK A", "accion": "comprar", "titulos": 4000},
                {"id": "BMV:FUNO", "clave": "FUNO 11", "accion": "comprar", "titulos": 2500}]
    _, texto, ords = resumen.construir(PROP, {"fuente": "local", "posiciones": []}, anterior, local)
    assert [o["clave"] for o in ords] == ["ALPEK A", "AAPL *"] and ords[0]["titulos"] == 5385   # firma interna
    assert "Cuenta NO confirmada" in texto and "⏳ Decisión pendiente (2): ALPEK A (comprar" in texto
    assert "5,385" not in texto and "🟢 Comprar" not in texto                     # nada aparentemente ejecutable
    assert "Nueva: comprar AAPL *." in texto and "Ya no se sugiere comprar FUNO 11." in texto
    assert "ALPEK A: 4,000 → 5,385" not in texto                                  # sin cuenta no se citan títulos
    assert "alimenta el plan" in texto and "desglose: diversificación 100" in texto and "Riesgo principal" in texto
    assert "/detalle" in texto and "AMX" not in texto                             # «mantener» de la propuesta sin posición


def test_plan_con_cuenta_confirmada_bmv_ejecutable_y_sic_pendiente():
    import pandas as pd
    local = pd.Timestamp(MANANA).tz_convert("America/Mexico_City")
    cart = {"fuente": "portal", "posiciones": [], "captura": {"hora_portal": "2026-09-30T14:45:00-06:00",
                                                                 "valor_portafolio": 995116.81, "efectivo": 229883.38}}
    _, texto, _ = resumen.construir(PROP, cart, None, local)
    assert "✅ confirmada (portal 30-09 14:45)" in texto and "poder de compra $229,883" in texto
    assert "🟢 Comprar ALPEK A: 5,385 títulos, límite $14.98" in texto
    assert "⏳ Decisión pendiente (1): AAPL *" in texto and "Cotización confiable" in texto


def test_propuestas_mayor_puntuacion_y_mayor_rendimiento_esperado():
    esc = lambda c, a, f: {"central_p50": c, "adverso_p10": a, "favorable_p90": f, "volatilidad_anual": 0.2}
    cmp_ = lambda r, e: [{"rend_anual": r, "sesiones": 84}, {"rend_anual": e}]
    ref = {**PROP, "lente": "puntuacion", "escenarios": esc(0.001, -0.05, 0.055), "comparacion": cmp_(0.011, 0.108)}
    agresiva = {**PROP, "clave": "mixta_rendimiento", "nombre": "Mixta · Máximo rendimiento", "lente": "rendimiento",
                "puntuacion": {"total": 63.5, "criterios": []}, "escenarios": esc(0.046, -0.161, 0.304),
                "comparacion": cmp_(1.135, 0.102)}
    b = "\n".join(resumen.bloque_propuestas({"a": ref, "b": agresiva}, ref))
    assert "«Mixta · Máxima puntuación» 87.1/100" in b and "alimenta el plan" in b
    assert "fuera de muestra +1.1%/año vs pesos iguales +10.8% (84 sesiones)" in b
    assert "🚀 Mayor rendimiento esperado: «Mixta · Máximo rendimiento»" in b and "más riesgo" in b


def test_envia_una_sola_vez_por_dia(con, ajustes, monkeypatch):
    enviados = []
    monkeypatch.setattr(notificador, "enviar", lambda t, x, c, detalle=None: enviados.append((c, detalle)) or {"telegram": "enviada"})
    props = {"mixta_puntuacion": PROP}
    r = resumen.enviar_si_toca(con, ajustes, {"fuente": "local", "posiciones": []}, props, MANANA)
    assert r and len(enviados) == 1 and enviados[0][0]["notificar_telegram"] and not enviados[0][0]["notificar_escritorio"]
    assert resumen.enviar_si_toca(con, ajustes, {"fuente": "local", "posiciones": []}, props, MANANA) is None
    siguiente = datetime(2026, 10, 1, 13, 5, tzinfo=UTC)
    resumen.enviar_si_toca(con, ajustes, {"fuente": "local", "posiciones": []}, props, siguiente)
    assert len(enviados) == 2 and "Sin cambios frente al plan anterior." in enviados[1][1]


def test_telegram_parte_mensajes_largos(monkeypatch):
    import httpx
    enviados = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(httpx, "post", lambda url, timeout, data: enviados.append(data["text"]) or httpx.Response(200))
    texto = "\n".join(f"línea {i} " + "x" * 90 for i in range(100))
    assert notificador.telegram("Plan", texto) == "enviada"
    assert len(enviados) == 3 and all(len(t) <= 4096 for t in enviados) and enviados[-1].endswith("(3/3)")


def test_un_envio_fallido_se_reintenta_y_no_cuenta_como_enviado(con, ajustes, monkeypatch):
    resultados = iter([{"telegram": "error"}, {"telegram": "enviada"}])
    enviados = []
    monkeypatch.setattr(notificador, "enviar", lambda t, x, c, detalle=None: enviados.append(detalle) or next(resultados))
    props = {"mixta_puntuacion": PROP}
    cart = {"fuente": "local", "posiciones": []}
    assert resumen.enviar_si_toca(con, ajustes, cart, props, MANANA)["resultado"] == {"telegram": "error"}
    assert resumen.enviar_si_toca(con, ajustes, cart, props, datetime(2026, 9, 30, 13, 10, tzinfo=UTC)) is None  # < 10 min
    r = resumen.enviar_si_toca(con, ajustes, cart, props, datetime(2026, 9, 30, 13, 16, tzinfo=UTC))
    assert r["resultado"] == {"telegram": "enviada"} and r["intentos"] == 2 and len(enviados) == 2
    assert resumen.enviar_si_toca(con, ajustes, cart, props, datetime(2026, 9, 30, 14, 0, tzinfo=UTC)) is None  # ya llegó


def test_espera_si_las_propuestas_se_estan_recalculando(con, ajustes, monkeypatch):
    monkeypatch.setattr(notificador, "enviar", lambda *a, **k: {"telegram": "enviada"})
    props = {"mixta_puntuacion": {**PROP, "recalcular": True, "avisos": ["se recalculará"]}}
    cart = {"fuente": "local", "posiciones": []}
    assert resumen.enviar_si_toca(con, ajustes, cart, props, MANANA) is None                       # 07:05: espera
    tarde = datetime(2026, 9, 30, 14, 5, tzinfo=UTC)                                                # 08:05: no espera más
    assert "No hay una propuesta vigente" in resumen.enviar_si_toca(con, ajustes, cart, props, tarde)["texto"]


def test_boletas_del_plan_del_dia_usan_la_propuesta_de_referencia_y_reemplazan(con, ajustes):
    from terminal import boleta, servicios
    from conftest import sembrar_precios
    ids = [r[0] for r in con.execute("SELECT id FROM instrumentos WHERE id LIKE 'BMV:%' AND clase='accion' AND estado='activo' LIMIT 8")]
    sembrar_precios(con, ids, sesiones=300)
    servicios.calcular_propuestas(con, ajustes)
    props = servicios.propuestas_guardadas(con, ajustes, servicios.perfil_actual(con, ajustes))
    ref = resumen.propuesta_referencia(props)
    r1 = boleta.generar(con, ajustes, boleta.PLAN_DEL_DIA)
    assert r1[0]["propuesta"] == ref["clave"] and r1[0]["numero_ordenes"] + r1[0]["por_investigar"] >= 5 and r1[0]["reemplazadas"] == 0
    r2 = boleta.generar(con, ajustes, boleta.PLAN_DEL_DIA)
    assert r2[0]["reemplazadas"] == len(r1) - 1                                  # no se duplican órdenes vigentes
    vigentes = con.execute("SELECT COUNT(*) FROM boletas WHERE estado='vigente'").fetchone()[0]
    assert vigentes == len(r2) - 1


def test_texto_de_boletas_para_telegram():
    from terminal import boleta
    bs = [{"id": 84, "estado": "vigente", "tipo": "considerar compra", "lado": "compra", "cantidad": 5418, "precio_limite": 14.87,
           "importe": 80566.0, "costos": {"total": 93.4}, "emisora_serie": "ALPEK A", "instrumento_id": "BMV:ALPEK",
           "caduca_en": "2026-09-29T19:10:00+00:00"},
          {"id": 83, "estado": "vigente", "tipo": "investigar", "lado": "compra", "cantidad": 0, "precio_limite": None,
           "emisora_serie": "FUBO *", "instrumento_id": "SIC:FUBO", "caduca_en": "2026-09-29T19:10:00+00:00"},
          {"id": 80, "estado": "caducada", "tipo": "considerar compra", "emisora_serie": "CAT *", "caduca_en": "x"}]
    t = boleta.texto_telegram(bs)
    assert "vencen 29-09 13:10 (CDMX)" in t and "🟢 COMPRA ALPEK A: 5,418 títulos, límite $14.87" in t
    assert "FUBO * (#83)" in t and "CAT" not in t and "no envía órdenes" in t


def test_envio_anticipado_al_tener_los_cierres(con, ajustes, monkeypatch):
    enviados = []
    monkeypatch.setattr(notificador, "enviar", lambda t, x, c, detalle=None: enviados.append((t, detalle)) or {"telegram": "enviada"})
    cart = {"fuente": "local", "posiciones": []}
    noche = datetime(2026, 9, 30, 3, 0, tzinfo=UTC)                       # martes 29-sep 21:00 CDMX, BMV cerrada
    viejo = {"mixta_puntuacion": {**PROP, "datos_hasta": "2026-09-28"}}
    assert resumen.enviar_si_toca(con, ajustes, cart, viejo, noche) is None   # aún sin los cierres del 29: espera
    r = resumen.enviar_si_toca(con, ajustes, cart, {"mixta_puntuacion": PROP}, noche)   # datos al 29-sep
    assert r and r["fecha"] == "2026-09-30" and "Plan para la sesión del mié 30-09-2026" in enviados[0][0]
    assert resumen.enviar_si_toca(con, ajustes, cart, {"mixta_puntuacion": PROP}, MANANA) is None   # 07:05: ya enviado


def test_sesion_objetivo():
    assert resumen.sesion_objetivo(datetime(2026, 9, 29, 16, 0, tzinfo=UTC)).isoformat() == "2026-09-29"  # sesión abierta
    assert resumen.sesion_objetivo(datetime(2026, 9, 30, 3, 0, tzinfo=UTC)).isoformat() == "2026-09-30"   # tras el cierre
    assert resumen.sesion_objetivo(datetime(2026, 10, 3, 18, 0, tzinfo=UTC)).isoformat() == "2026-10-05"  # sábado → lunes


def test_plan_corregido_si_el_recalculo_cambia_las_ordenes_antes_de_la_apertura(con, ajustes, monkeypatch):
    enviados = []
    monkeypatch.setattr(notificador, "enviar", lambda t, x, c, detalle=None: enviados.append(t) or {"telegram": "enviada"})
    cart = {"fuente": "local", "posiciones": []}
    noche = datetime(2026, 9, 30, 3, 0, tzinfo=UTC)
    assert resumen.enviar_si_toca(con, ajustes, cart, {"mixta_puntuacion": PROP}, noche)
    otra = {**PROP, "cambios": {"costo_total": 90.0, "filas": [PROP["cambios"]["filas"][0]]}}  # ya no compra AAPL
    r = resumen.enviar_si_toca(con, ajustes, cart, {"mixta_puntuacion": otra}, datetime(2026, 9, 30, 6, 0, tzinfo=UTC))
    assert r and r["correcciones"] == 1 and enviados[-1].startswith("🔁 PLAN CORREGIDO")
    assert "AAPL" in r["texto"]  # «Cambios frente al plan anterior» menciona lo que salió
    # sin cambios nuevos no se reenvía; tras la apertura (07:30) tampoco
    assert resumen.enviar_si_toca(con, ajustes, cart, {"mixta_puntuacion": otra}, datetime(2026, 9, 30, 7, 0, tzinfo=UTC)) is None
    assert resumen.enviar_si_toca(con, ajustes, cart, {"mixta_puntuacion": PROP}, datetime(2026, 9, 30, 14, 0, tzinfo=UTC)) is None
    assert len(enviados) == 2


def test_plan_pedido_despues_del_cierre_muestra_la_proxima_sesion(con, ajustes, monkeypatch):
    """/plan después de las 14:00 (o en fin de semana) es para la PRÓXIMA sesión, no para la de hoy."""
    from terminal import bot_telegram, servicios
    tarde = datetime(2026, 9, 30, 21, 30, tzinfo=UTC)                       # mié 30-sep 15:30 CDMX, BMV cerrada
    assert resumen.sesion_objetivo(tarde).isoformat() == "2026-10-01"
    monkeypatch.setattr(servicios, "propuestas_guardadas", lambda *a, **k: {"mixta_puntuacion": PROP})
    monkeypatch.setattr(bot_telegram, "_ahora", lambda: tarde)
    texto = bot_telegram.texto_plan(con, ajustes)
    assert texto.startswith("🌙 Plan para la sesión del jue 01-10-2026") and "mié 30-09-2026" not in texto.splitlines()[0]


def test_criterio_del_plan_mayor_plusvalia_esperada():
    """Con criterio «plusvalia» el plan usa la propuesta con mayor ganancia esperada al cierre, no la mejor puntuada."""
    esc = lambda c: {"central_p50": c, "adverso_p10": c - 0.1, "favorable_p90": c + 0.1, "volatilidad_anual": 0.3}
    a = {**PROP, "clave": "a", "puntuacion": {"total": 87.0, "criterios": []}, "escenarios": esc(0.007)}
    b = {**PROP, "clave": "b", "nombre": "Agresiva", "puntuacion": {"total": 69.9, "criterios": []}, "escenarios": esc(0.043)}
    assert resumen.propuesta_referencia({"a": a, "b": b})["clave"] == "a"                       # por omisión: puntuación
    perfil = {"criterio_plan": "plusvalia"}
    a2, b2 = {**a, "perfil": perfil}, {**b, "perfil": perfil}
    assert resumen.propuesta_referencia({"a": a2, "b": b2})["clave"] == "b"
    texto = "\n".join(resumen.bloque_propuestas({"a": a2, "b": b2}, b2))
    assert "MAYOR PLUSVALÍA ESPERADA" in texto and "«Agresiva»" in texto
