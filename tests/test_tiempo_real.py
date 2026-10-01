"""Flujo en vivo (Alpaca IEX), adaptador de barras de Alpaca y avisos por Telegram, sin red real."""
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from terminal import db, ingesta, notificador, tiempo_real, vigencia
from terminal.adaptadores import Alpaca, Barra
from terminal.tiempo_real import ErrorFatal, ErrorFlujo, FlujoVivo

RAIZ = Path(__file__).resolve().parents[1]
CLAVE, SECRETO = "id-de-prueba", "secreto-de-prueba"  # valores ficticios  # pragma: allowlist secret


def _usd(con, n=3):
    return [r[0] for r in con.execute("SELECT id FROM instrumentos WHERE estado='activo' AND moneda_referencia='USD' "
                                      "AND listado_referencia <> '' ORDER BY id LIMIT ?", (n,))]


def test_simbolos_prioriza_posiciones_y_respeta_limite(con):
    ids = _usd(con, 40)
    ultimo = ids[-1]
    con.execute("INSERT INTO transacciones (fecha, tipo, instrumento_id, cantidad, precio, monto, origen, huella, creado_en) "
                "VALUES ('2026-09-01','compra',?,10,1,10,'prueba','h1','x')", (ultimo,))
    mapa = tiempo_real.simbolos(con, maximo=5)
    assert len(mapa) == 5
    assert ultimo in mapa[next(iter(mapa))]  # la posición va primero aunque alfabéticamente sea la última


def _flujo(ajustes, con, monkeypatch):
    ruta = con.execute("PRAGMA database_list").fetchone()[2]
    original = db.conectar
    monkeypatch.setattr(tiempo_real.db, "conectar", lambda *a, **k: original(ruta))
    f = FlujoVivo(ajustes)
    iid = _usd(con, 1)[0]
    sim = con.execute("SELECT listado_referencia FROM instrumentos WHERE id=?", (iid,)).fetchone()[0]
    f._mapa = {sim: [iid]}
    return f, iid, sim


def test_guarda_cotizacion_en_vivo_y_el_cierre_la_sustituye(ajustes, con, monkeypatch):
    f, iid, sim = _flujo(ajustes, con, monkeypatch)
    f._procesar([{"T": "t", "S": sim, "p": 101.5, "t": "2026-09-22T15:30:00.123456789Z"}])
    f._guardar()
    fila = con.execute("SELECT fecha, cierre, moneda, proveedor, tipo_dato FROM precios WHERE instrumento_id=?", (iid,)).fetchone()
    assert tuple(fila) == ("2026-09-22", 101.5, "USD", "alpaca_vivo", "tiempo_real")
    assert f._nuevos and f.resumen()["mensajes"] == 1

    class Cierre:  # proveedor de cierres ficticio
        tipo_dato = "cierre"
        def configurado(self): return True
        def soporta(self, _): return True
        def historico(self, *_): return [Barra(fecha="2026-09-22", cierre=102.0)]
    ads = {n: Cierre() if n == "tiingo" else type("X", (), {"configurado": lambda s: False})() for n in ingesta.ORDEN_PRECIOS}
    con.execute("DELETE FROM instrumentos WHERE id <> ?", (iid,))
    ingesta.actualizar_precios(con, ads, hoy=date(2026, 9, 22))
    provs = {r[0] for r in con.execute("SELECT proveedor FROM precios WHERE instrumento_id=?", (iid,))}
    assert provs == {"tiingo"}


def test_recalculo_por_movimiento_o_intervalo(ajustes, con, monkeypatch):
    f, _, sim = _flujo(ajustes, con, monkeypatch)
    f.cfg.update(umbral_movimiento=0.01, recalcular_cada_min=5, recalculo_minimo_seg=0)
    f._procesar([{"T": "t", "S": sim, "p": 100.0, "t": "2026-09-22T15:30:00Z"}])
    f._guardar()
    f.marcar_recalculo()
    assert not f.debe_recalcular()  # sin precios nuevos
    f._procesar([{"T": "t", "S": sim, "p": 100.5, "t": "2026-09-22T15:31:00Z"}])
    f._guardar()
    assert not f.debe_recalcular()  # movimiento 0.5 % < 1 % y no pasó el intervalo
    f._procesar([{"T": "t", "S": sim, "p": 101.2, "t": "2026-09-22T15:32:00Z"}])
    f._guardar()
    assert f.debe_recalcular()  # 1.2 % ≥ 1 %
    f.marcar_recalculo()
    assert not f.debe_recalcular()


def test_errores_de_alpaca():
    with pytest.raises(ErrorFatal):
        FlujoVivo._error({"T": "error", "code": 402, "msg": "auth failed"})
    with pytest.raises(ErrorFlujo) as e:
        FlujoVivo._error({"T": "error", "code": 406, "msg": "connection limit exceeded"})
    assert not isinstance(e.value, ErrorFatal)


def test_vigencia_tiempo_real():
    u = {"tiempo_real_segundos_vigente": 120, "retrasado_minutos_vigente": 20, "cierre_sesiones_vigente": 0,
         "cierre_sesiones_retrasado": 1}
    abierto = datetime(2026, 9, 22, 15, 0, tzinfo=UTC)  # martes, NYSE abierta
    assert vigencia.evaluar("tiempo_real", "2026-09-22", "XNYS", u, "2026-09-22T14:59:30Z", abierto)["estado"] == "vigente"
    assert vigencia.evaluar("tiempo_real", "2026-09-22", "XNYS", u, "2026-09-22T14:50:00Z", abierto)["estado"] == "retrasado"
    assert vigencia.evaluar("tiempo_real", "2026-09-22", "XNYS", u, "2026-09-22T14:00:00Z", abierto)["estado"] == "vencido"
    # Mercado cerrado: el último precio de la sesión se evalúa como su cierre.
    noche = datetime(2026, 9, 23, 2, 0, tzinfo=UTC)
    assert vigencia.evaluar("tiempo_real", "2026-09-22", "XNYS", u, "2026-09-22T19:59:00Z", noche)["estado"] == "vigente"
    semana = datetime(2026, 9, 30, 2, 0, tzinfo=UTC)
    assert vigencia.evaluar("tiempo_real", "2026-09-22", "XNYS", u, "2026-09-22T19:59:00Z", semana)["estado"] == "vencido"


def test_alpaca_barras_crudas_y_ajustadas_con_respaldo_iex(con):
    llamadas = []

    def manejar(req: httpx.Request):
        llamadas.append(req)
        q = dict(req.url.params)
        if q["feed"] == "sip":
            return httpx.Response(403, json={"message": "subscription does not permit querying recent SIP data"})
        precio = 100.0 if q["adjustment"] == "raw" else 99.0
        if "page_token" not in q:
            return httpx.Response(200, json={"bars": [{"t": "2026-09-21T04:00:00Z", "c": precio, "v": 5}], "next_page_token": "p2"})
        return httpx.Response(200, json={"bars": [{"t": "2026-09-22T04:00:00Z", "c": precio + 1, "v": 6}], "next_page_token": None})

    a = Alpaca(con, {"peticiones_por_dia": 100}, CLAVE, secreto=SECRETO, cliente=httpx.Client(transport=httpx.MockTransport(manejar)))
    b = a.historico({"listado_referencia": "AAPL", "moneda_referencia": "USD"}, date(2026, 9, 1), date(2026, 9, 22))
    assert [(x.fecha, x.cierre, x.cierre_ajustado) for x in b] == [("2026-09-21", 100.0, 99.0), ("2026-09-22", 101.0, 100.0)]
    assert llamadas[0].headers["apca-api-key-id"] == CLAVE and SECRETO not in str(llamadas[0].url)
    assert all(r.url.host == "data.alpaca.markets" for r in llamadas)


def test_alpaca_requiere_clave_y_secreto(con):
    assert not Alpaca(con, {}, CLAVE).configurado()
    assert Alpaca(con, {}, CLAVE, secreto=SECRETO).configurado()


def test_solo_dominios_de_datos_de_alpaca():
    """Ningún archivo del paquete apunta a la API de operaciones de Alpaca (órdenes, cuentas, posiciones)."""
    codigo = "\n".join(p.read_text(encoding="utf-8") for p in (RAIZ / "terminal").rglob("*.py"))
    assert not re.search(r"(paper-)?api\.alpaca\.markets|/v2/orders|/v2/positions|/v2/account", codigo)
    assert set(re.findall(r"https?://[\w.]*alpaca\.markets", codigo)) == {"https://data.alpaca.markets", "https://alpaca.markets"}


def test_detalle_de_telegram_y_enrutado(monkeypatch):
    txt = notificador.detalle([{"severidad": "aviso", "titulo": "Rebalanceo sugerido", "motivo": "Desviación 6 pp",
                                "accion": "Revisar 3 cambios"}])
    assert "Desviación 6 pp" in txt and "→ Revisar 3 cambios" in txt and "no" in txt.lower()
    enviados = {}
    monkeypatch.setattr(notificador, "telegram", lambda t, x: enviados.setdefault("tg", x) and "enviada")
    monkeypatch.setattr(notificador, "escritorio", lambda t, x: "enviada")
    r = notificador.enviar("T", "resumen", {"notificar_telegram": True}, detalle=txt)
    assert r == {"escritorio": "enviada", "telegram": "enviada"} and enviados["tg"] == txt


def test_telegram_sin_variables_no_envia(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert notificador.telegram("t", "x") == "no_configurado"
    assert notificador.configurados()["telegram"] is False


def test_telegram_detecta_chat(monkeypatch):
    def falso(url, timeout):
        if url.endswith("/getMe"):
            return httpx.Response(200, json={"result": {"username": "mi_bot"}})
        return httpx.Response(200, json={"result": [{"message": {"chat": {"id": 42, "first_name": "Ana"}}}]})
    monkeypatch.setattr(notificador.httpx, "get", falso)
    assert notificador.telegram_chats("t") == ("mi_bot", [{"id": 42, "nombre": "Ana"}])


def test_prueba_de_avisos_exige_csrf_y_responde(monkeypatch):
    from fastapi.testclient import TestClient

    from terminal.app import app
    from terminal.seguridad import TOKEN_CSRF
    monkeypatch.setattr(notificador, "enviar", lambda t, x, cfg, detalle=None: {"escritorio": "enviada", "telegram": "no_configurado"})
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        assert c.post("/api/notificaciones/prueba", json={}).status_code == 403
        r = c.post("/api/notificaciones/prueba", json={}, headers={"X-CSRF-Token": TOKEN_CSRF})
        assert r.json()["resultado"]["escritorio"] == "enviada"
        e = c.get("/api/estado").json()
        assert set(e["notificaciones"]) == {"escritorio", "telegram", "correo"} and "modo" in e["tiempo_real"]
        assert json.dumps(e).count(SECRETO) == 0


def test_simbolos_en_vivo_priorizan_la_cuenta_del_portal_y_la_propuesta_del_plan(con):
    """Con 30 símbolos, las posiciones de la captura del portal y la propuesta del plan no deben quedar fuera."""
    import json as _json
    from terminal import tiempo_real
    con.execute("INSERT INTO capturas_portal (capturado_en, hora_portal, etapa, valor_portafolio, efectivo, fuente, "
                "n_posiciones, tabla_reconocida, huella) VALUES ('x','2026-09-30T21:43:00-06:00','practica',1,0,'p',1,1,'h')")
    cid = con.execute("SELECT MAX(id) FROM capturas_portal").fetchone()[0]
    con.execute("INSERT INTO posiciones_portal (captura_id, instrumento_id, texto, titulos) VALUES (?, 'SIC:MRNA', 'MRNA *', 16)", (cid,))
    otros = [r[0] for r in con.execute("SELECT id FROM instrumentos WHERE moneda_referencia='USD' AND estado='activo' "
                                        "AND id NOT IN ('SIC:MRNA','SIC:MU') LIMIT 40")]
    relleno = {"clave": "acciones_ajuste", "estado": "calculada", "puntuacion": {"total": 50},
               "pesos": [{"id": i, "peso": 0.02} for i in otros]}
    plan = {"clave": "acciones_puntuacion", "estado": "calculada", "puntuacion": {"total": 90},
            "pesos": [{"id": "SIC:MU", "peso": 0.2}]}
    for p in (relleno, plan):
        con.execute("INSERT INTO propuestas (tipo, creado_en, parametros, resultado) VALUES (?,?,?,?)",
                    (p["clave"], "2026-09-30", "{}", _json.dumps(p)))
    con.commit()
    m = tiempo_real.simbolos(con, 5)
    assert list(m)[:2] == ["MRNA", "MU"] and len(m) == 5
