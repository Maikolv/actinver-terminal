"""Monitor del Reto: proveedores, cobertura, webhook, tiempos de disponibilidad, reglas y separación práctica/competencia."""
import json
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd
import pytest

from terminal import cotizaciones as cz
from terminal import migraciones, reto, servicios, webhook_tv
from terminal.alertas import Condicion, _revisar

from conftest import sembrar_precios


def _ins(con):
    return {r["id"]: dict(r) for r in con.execute("SELECT * FROM instrumentos")}


# --- available_at ------------------------------------------------------------------------------------------------
def test_available_at_de_cierres_operaciones_y_noticias(con):
    ev, disp = migraciones.disponibilidad_precio("2026-09-22", "tiingo", "USD", "cierre", None, None)
    assert pd.Timestamp(ev) == pd.Timestamp("2026-09-22 20:00", tz="UTC")          # cierre NYSE 16:00 ET
    assert pd.Timestamp(disp) - pd.Timestamp(ev) == timedelta(hours=3)                # + retraso de publicación
    # Importado por el usuario ANTES del plazo: no pudo conocerse antes de importarlo, ni antes del cierre.
    _, d2 = migraciones.disponibilidad_precio("2026-09-22", "archivo", "MXN", "cierre", None, "2026-09-22T21:00:00+00:00")
    assert pd.Timestamp(d2) == pd.Timestamp("2026-09-22 21:00", tz="UTC")
    # Cotización en vivo: evento = hora de la operación; disponible = hora de recepción
    ev3, d3 = migraciones.disponibilidad_precio("2026-09-22", "alpaca_vivo", "USD", "tiempo_real", "2026-09-22T15:00:00Z",
                                                "2026-09-22T15:00:12+00:00")
    assert (pd.Timestamp(d3) - pd.Timestamp(ev3)).total_seconds() == 12
    con.execute("INSERT INTO noticias (id, titulo, publicado, fuente, obtenido_en) VALUES ('n','t','2026-09-20T10:00:00+00:00',"
                "'rss','2026-09-22T10:00:00+00:00')")
    migraciones.completar_tiempos(con)
    n = con.execute("SELECT event_time, available_at FROM noticias").fetchone()
    assert n[0] < n[1] and n[1] == "2026-09-22T10:00:00+00:00"   # se conoce cuando la terminal la obtuvo


def test_no_se_sobrescribe_available_at(con):
    sembrar_precios(con, ["SIC:AAPL"], sesiones=80)
    migraciones.completar_tiempos(con)
    antes = con.execute("SELECT available_at FROM precios LIMIT 1").fetchone()[0]
    con.execute("UPDATE precios SET cierre = cierre * 2")  # revisión posterior del dato
    migraciones.completar_tiempos(con)
    assert con.execute("SELECT available_at FROM precios LIMIT 1").fetchone()[0] == antes


# --- conversión de símbolos y monedas -------------------------------------------------------------------------------
def test_normalizacion_de_simbolos_y_mercados(con):
    ins = _ins(con)
    assert cz.normalizar_simbolo("BMV:WALMEX", ins) is None or cz.normalizar_simbolo("BMV:WALMEX", ins)["mercado"] == "local"
    amx = cz.normalizar_simbolo("AMX B", ins)
    assert amx["instrumento_id"] == "BMV:AMX" and amx["mercado"] == "local" and amx["moneda"] == "MXN"
    sic = cz.normalizar_simbolo("BMV:AAPL", ins)
    assert sic["instrumento_id"] == "SIC:AAPL" and sic["mercado"] == "SIC" and sic["moneda"] == "MXN"
    origen = cz.normalizar_simbolo("NASDAQ:AAPL", ins)
    assert origen["instrumento_id"] == "SIC:AAPL" and origen["mercado"] == "origen_extranjero" and origen["moneda"] == "USD"
    alcoa = cz.normalizar_simbolo("NYSE:AA", ins)          # clave SIC «AA1», listado de origen «AA»
    assert alcoa["instrumento_id"] == "SIC:AA1" and alcoa["mercado"] == "origen_extranjero"
    assert cz.normalizar_simbolo("NASDAQ:NOEXISTE", ins) is None


def test_precio_usd_de_origen_nunca_sustituye_al_bmv(con):
    ins = _ins(con)["SIC:AAPL"]
    ahora = pd.Timestamp.now(tz="UTC")
    con.execute("INSERT INTO precios (instrumento_id, fecha, cierre, moneda, proveedor, tipo_dato, hora_cotizacion, obtenido_en) "
                "VALUES ('SIC:AAPL', ?, 230.0, 'USD', 'alpaca_vivo', 'tiempo_real', ?, ?)",
                (ahora.date().isoformat(), ahora.isoformat(), ahora.isoformat()))
    provs = cz.construir(con, False, entorno={})
    ref = provs["referencia_origen"].cotizacion(ins)
    assert ref.moneda == "USD" and ref.mercado == "origen_extranjero"
    r = cz.precio_confiable(con, provs, ins)
    assert r["estado"] == cz.SIN_PRECIO and r["cotizacion"] is None


# --- dato retrasado ---------------------------------------------------------------------------------------------------
def test_estado_por_latencia_medida_y_obsolescencia():
    e = "2026-09-22T15:00:00Z"
    assert cz.clasificar_latencia(e, "2026-09-22T15:00:05Z") == "REAL_TIME"
    assert cz.clasificar_latencia(e, "2026-09-22T15:10:00Z") == "DELAYED"
    assert cz.clasificar_latencia(e, "2026-09-22T17:00:00Z") == "UNKNOWN"
    assert cz.clasificar_latencia(e, "2026-09-22T15:00:01Z", es_cierre=True) == "EOD"
    q = cz.Cotizacion("x", "WALMEX*", "BMV:WALMEX", "BMV:WALMEX", "local", "BMV", 60.0, "MXN", e, "2026-09-22T15:00:05Z",
                      None, "REAL_TIME")
    abierto = datetime(2026, 9, 22, 15, 1, tzinfo=UTC)
    assert not cz.es_obsoleta(q, {}, abierto)
    assert cz.es_obsoleta(q, {}, abierto + timedelta(minutes=10))   # REAL_TIME con 10 min de edad ya no vale
    semana = datetime(2026, 9, 29, 23, 0, tzinfo=UTC)
    assert cz.es_obsoleta(q, {}, semana)                              # cerrado: debe ser de la última sesión


# --- conectores contratados: pendientes exactos, sin endpoints inventados ---------------------------------------------
def test_bmv_licenciado_sin_contrato_dice_lo_pendiente_y_no_consulta(con):
    llamadas = []
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: llamadas.append(r) or httpx.Response(200, json={})))
    p = cz.BmvLicensedProvider(con, {}, cliente=cli)
    pend = p.pendientes()
    assert any("Contrato de datos" in x for x in pend) and any("BMV_API_KEY" in x for x in pend)
    with pytest.raises(cz.ProveedorNoDisponible):
        p.cotizacion(_ins(con)["BMV:AMX"])
    assert llamadas == []
    for clase in (cz.LsegProvider, cz.IceProvider):
        assert not clase(con, {}).configurado()


def test_conector_con_especificacion_verifica_cobertura_exacta(con, tmp_path):
    esp = {"variable_url_base": "BMV_URL_BASE", "autenticacion": {"tipo": "cabecera", "nombre": "X-Clave", "formato": "{clave}"},
           "cotizacion": {"ruta": "/q/{simbolo}", "campos": {"precio": "d.p", "moneda": "d.m", "hora_evento": "d.t", "bolsa": "d.b"}},
           "plantilla_simbolo": "{clave}{serie}", "latencia_declarada_s": 0}
    ruta = tmp_path / "bmv.json"
    ruta.write_text(json.dumps(esp), encoding="utf-8")
    env = {"BMV_ESPECIFICACION": str(ruta), "BMV_API_KEY": "k", "BMV_URL_BASE": "https://datos.ejemplo"}  # pragma: allowlist secret

    def responder(req):
        moneda = "USD" if "AAPL" in req.url.path else "MXN"   # un SIC entregado en dólares: no coincide
        hora = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(seconds=2)).isoformat()
        return httpx.Response(200, json={"d": {"p": 50.5, "m": moneda, "t": hora, "b": "BMV"}})

    p = cz.BmvLicensedProvider(con, env, cliente=httpx.Client(transport=httpx.MockTransport(responder)))
    assert p.configurado()
    ins = _ins(con)
    filas = cz.verificar_cobertura(con, {"bmv_licenciado": p}, [ins["BMV:AMX"], ins["SIC:AAPL"]], ["bmv_licenciado"])
    estados = {f["instrumento_id"]: f for f in filas}
    assert estados["BMV:AMX"]["estado"] == "verificado" and estados["BMV:AMX"]["estado_latencia"] == "REAL_TIME"
    assert estados["SIC:AAPL"]["estado"] == "no_coincide"
    assert cz.cobertura_verificada(con, "bmv_licenciado", "SIC:AAPL") is None


# --- webhook de TradingView ----------------------------------------------------------------------------------------
def _cuerpo(**k):
    base = {"secreto": "s3creto", "simbolo": "BMV:AMX", "precio": 17.25, "hora": datetime.now(UTC).isoformat(),
            "alerta": "cruce"}
    return json.dumps({**base, **k}).encode()


def test_webhook_valida_y_elimina_duplicados(con):
    rx = webhook_tv.TradingViewAlertReceiver(con, {"TRADINGVIEW_WEBHOOK_SECRETO": "s3creto"})  # pragma: allowlist secret
    cuerpo = _cuerpo()
    r1 = rx.recibir(cuerpo)
    assert r1["duplicado"] is False and r1["instrumento_id"] == "BMV:AMX"
    assert rx.recibir(cuerpo)["duplicado"] is True
    assert con.execute("SELECT COUNT(*) FROM eventos_webhook").fetchone()[0] == 1
    reg = con.execute("SELECT estado_latencia, proveedor FROM cotizaciones_registro").fetchone()
    assert tuple(reg) == ("UNKNOWN", "tradingview_webhook")    # evento, no se declara tiempo real
    casos = [(_cuerpo(secreto="otro"), 401), (_cuerpo(simbolo="BMV:NOEXISTE"), 422), (_cuerpo(precio=-1), 422),
             (_cuerpo(precio="NaN"), 422), (_cuerpo(moneda="USD"), 422),
             (_cuerpo(hora=(datetime.now(UTC) - timedelta(hours=2)).isoformat()), 422),
             (_cuerpo(hora=(datetime.now(UTC) + timedelta(hours=1)).isoformat()), 422), (b"no-json", 422)]
    for c, codigo in casos:
        with pytest.raises(webhook_tv.WebhookRechazado) as e:
            rx.recibir(c)
        assert e.value.codigo == codigo
    assert webhook_tv.TradingViewAlertReceiver(con, {}).configurado() is False


def test_webhook_http_sin_csrf_pero_con_secreto(monkeypatch):
    from fastapi.testclient import TestClient

    from terminal.app import app
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_SECRETO", "s3creto")  # pragma: allowlist secret
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        r = c.post("/webhook/tradingview", content=_cuerpo(alerta="http"))
        assert r.status_code == 200 and r.json()["duplicado"] is False
        assert c.post("/webhook/tradingview", content=_cuerpo(alerta="http", secreto="x")).status_code == 401
        assert c.post("/webhook/tradingview", content=b"x" * 20_000).status_code == 413
        assert c.get("/webhook/tradingview").status_code == 405
    with TestClient(app, base_url="http://atacante.example") as c:
        assert c.post("/webhook/tradingview", content=_cuerpo()).status_code == 400


# --- reglas del Reto ------------------------------------------------------------------------------------------------
def test_costo_comision_mas_iva():
    d = reto.costo_detalle(100_000)
    assert (d["comision"], d["iva"], d["total"]) == (100.0, 16.0, 116.0)
    assert abs(d["tasa_efectiva"] - 0.00116) < 1e-12


def test_cinco_acciones_distintas_solo_competencia(con):
    ins = _ins(con)
    tx = [{"tipo": "compra", "instrumento_id": i, "fecha": "2026-10-06", "anulada": 0}
          for i in ("BMV:AMX", "BMV:GFNORTE", "BMV:FUNO", "SIC:AAPL")]
    tx.append({"tipo": "compra", "instrumento_id": "BMV:WALMEX" if "BMV:WALMEX" in ins else "BMV:BIMBO", "fecha": "2026-09-29",
               "anulada": 0})  # práctica: no cuenta
    etf = next(i for i, v in ins.items() if v["clase"] == "etf")
    tx.append({"tipo": "compra", "instrumento_id": etf, "fecha": "2026-10-07", "anulada": 0})  # ETF: no cuenta
    a = reto.acciones_operadas(tx, ins)
    assert a["n"] == 4 and not a["cumple"] and a["faltan"] == 1
    tx.append({"tipo": "compra", "instrumento_id": "BMV:BIMBO", "fecha": "2026-10-08", "anulada": 0})
    assert reto.acciones_operadas(tx, ins)["cumple"]


def test_limite_de_compra_del_cincuenta_por_ciento():
    adv = reto.verificar_compras([{"id": "A", "monto": 510_000}, {"id": "B", "monto": 300_000}, {"id": "C", "monto": 100_000}],
                                 1_000_000, {"B": 250_000})
    niveles = {a["id"]: a["nivel"] for a in adv}
    assert niveles == {"A": "critica", "B": "aviso"}          # A: compra > 50 %; B: posición resultante 55 %
    assert reto.verificar_compras([{"id": "D", "monto": 500_000}], 1_000_000, {}) == []   # exactamente 50 %: permitido


def test_propuesta_advierte_compra_mayor_al_limite():
    p = {"pesos": [{"id": "X", "monto_estimado": 600_000}, {"id": "Y", "monto_estimado": 400_000}], "capital": 1_000_000,
         "cambios": {"filas": []}}
    servicios.advertir_compras(p, {"valor_total": 0, "posiciones": []})
    assert [a["id"] for a in p["advertencias_reto"]] == ["X"]


def test_practica_y_competencia_separadas(con):
    from terminal import cartera
    ins = _ins(con)
    assert ins  # catálogo cargado
    for k, (fecha, iid) in enumerate((("2026-09-29", "BMV:AMX"), ("2026-10-06", "BMV:GFNORTE"))):
        # Fechas futuras respecto al día de hoy (la validación de captura las rechaza): se insertan directo.
        cur = con.execute("INSERT INTO transacciones (fecha, tipo, instrumento_id, cantidad, precio, monto, origen, huella, "
                          "creado_en) VALUES (?, 'compra', ?, 10, 100, 0, 'prueba', ?, ?)", (fecha, iid, f"h{k}", "2026-09-23"))
        cartera.marcar_tiempos(con, cur.lastrowid, fecha)
    etapas = dict(con.execute("SELECT instrumento_id, etapa FROM transacciones").fetchall())
    assert etapas == {"BMV:AMX": "practica", "BMV:GFNORTE": "competencia"}
    en_comp = datetime(2026, 10, 7, 18, 0, tzinfo=UTC)
    tx, etapa = servicios.operaciones_etapa(con, en_comp)
    assert etapa == "competencia"
    assert [t["instrumento_id"] for t in tx if t["tipo"] == "compra"] == ["BMV:GFNORTE"]
    inicial = [t for t in tx if t["origen"] == "reto_saldo_inicial"]
    assert inicial and inicial[0]["monto"] == 1_000_000   # la competencia reinicia el saldo


def test_alertas_invitan_a_revisar_nunca_ordenan():
    c = _revisar(Condicion("stop_loss", "x", True, titulo="Stop-loss: AMX -9%", accion="Vender todo"))
    assert c.titulo.startswith("REVISAR") and c.accion.startswith("REVISAR") and "incertidumbre" in c.datos
    from terminal import alertas
    import inspect
    fuente = inspect.getsource(alertas)
    for imperativo in ('"Vender', '"Comprar', '"Venda', '"Compre', "Evaluar reducir"):
        assert imperativo not in fuente
