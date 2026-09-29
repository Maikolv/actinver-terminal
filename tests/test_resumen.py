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


def test_plan_con_titulos_cambios_y_porque():
    import pandas as pd
    local = pd.Timestamp(MANANA).tz_convert("America/Mexico_City")
    anterior = [{"id": "BMV:ALPEK", "clave": "ALPEK A", "accion": "comprar", "titulos": 4000},
                {"id": "BMV:FUNO", "clave": "FUNO 11", "accion": "comprar", "titulos": 2500}]
    _, texto, ords = resumen.construir(PROP, {"fuente": "local", "posiciones": []}, anterior, local)
    assert [o["clave"] for o in ords] == ["ALPEK A", "AAPL *"] and ords[0]["titulos"] == 5385
    assert "🟢 Comprar ALPEK A: 5,385 títulos a ~$14.98" in texto
    assert "AAPL *: 10 títulos" in texto and "precio de referencia; confirme en el portal" in texto
    assert "Nueva: comprar AAPL *." in texto and "Ya no se sugiere comprar FUNO 11." in texto
    assert "ALPEK A: 4,000 → 5,385 títulos." in texto
    assert "ALPEK A: Relación rendimiento/riesgo histórica 1.85." in texto and "Riesgo principal" in texto
    assert "AMX" not in texto                                                              # «mantener» no es una orden


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
