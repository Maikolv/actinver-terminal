"""Boleta de decisión, estados de orden, importadores de contexto, versiones macro, estrategias y calidad del precio."""
import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from terminal import boleta, cartera, cotizaciones as cz, fuentes_web, importar, migraciones, registro, vigencia
from terminal.investigacion import estrategias

from conftest import sembrar_precios


def _ins(con):
    return {r["id"]: dict(r) for r in con.execute("SELECT * FROM instrumentos")}


def _cartera_con_precio(con, precio_hoy=None):
    fin = vigencia.ultima_sesion_cerrada("XMEX")
    sembrar_precios(con, ["BMV:AMX"], fin=fin, sesiones=300, proveedor="archivo", con_fx=False)
    if precio_hoy is not None:
        con.execute("UPDATE precios SET cierre=? WHERE instrumento_id='BMV:AMX' AND fecha=?", (precio_hoy, fin.isoformat()))
    migraciones.completar_tiempos(con)
    t = cartera.validar({"fecha": "2026-09-01", "tipo": "aportacion", "monto": 1_000_000, "moneda": "MXN", "tipo_cambio": 1}, _ins(con))
    cartera.registrar(con, t, "prueba")
    con.commit()
    return float(con.execute("SELECT cierre FROM precios WHERE instrumento_id='BMV:AMX' ORDER BY fecha DESC LIMIT 1").fetchone()[0])


def _cart(con, ajustes):
    from terminal import servicios
    return servicios.cartera_actual(con, ajustes)


def test_boleta_cantidad_entera_limite_costos_y_efecto(con, ajustes):
    px = _cartera_con_precio(con)
    b = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 100_000, "delta_pp": 10}, _cart(con, ajustes))
    assert b["tipo"] == "considerar compra" and b["lado"] == "compra" and b["calidad_precio"] == "EOD"
    assert b["precio_limite"] == round(round(px * 1.002 / 0.01) * 0.01, 2)
    assert b["cantidad"] == int(100_000 // b["precio_limite"]) and isinstance(b["cantidad"], int)
    assert b["costos"]["total"] == round(b["importe"] * 0.00116, 2)
    assert [e["deslizamiento"] for e in b["costos"]["escenarios_deslizamiento"]] == [0.0, 0.001, 0.005]
    assert "sin_ejecucion" in b["costos"]
    assert b["efecto"]["efectivo_despues"] == pytest.approx(1_000_000 - b["importe"] - b["costos"]["total"], abs=0.01)
    assert b["rango"]["disponible"] and b["rango"]["p10"] <= b["rango"]["rend_esperado"] <= b["rango"]["p90"]
    assert "no registra órdenes" in b["aviso"]


def test_compra_mayor_al_50_se_advierte(con, ajustes):
    _cartera_con_precio(con)
    b = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 600_000}, _cart(con, ajustes))
    assert b["efecto"]["advertencias_reto"] and b["efecto"]["advertencias_reto"][0]["nivel"] == "critica"


def test_sin_precio_confiable_solo_investigar(con, ajustes):
    t = cartera.validar({"fecha": "2026-09-01", "tipo": "aportacion", "monto": 1_000_000, "moneda": "MXN", "tipo_cambio": 1}, _ins(con))
    cartera.registrar(con, t, "prueba")
    b = boleta.construir(con, ajustes, {"id": "BMV:GFNORTE", "accion": "comprar", "monto_mxn": 100_000}, _cart(con, ajustes))
    assert b["tipo"] == "investigar" and b["cantidad"] == 0 and b["calidad_precio"] == cz.SIN_PRECIO
    assert any("Precio BMV confiable" in f for f in b["datos_faltantes"])


def _guardar(con, b):
    cur = con.execute("INSERT INTO boletas (creada_en, caduca_en, instrumento_id, tipo, contenido, huella_datos) VALUES (?,?,?,?,?,?)",
                      (b["creada_en"], b["caduca_en"], b["instrumento_id"], b["tipo"], json.dumps(b, default=str), b["huella_datos"]))
    con.commit()
    return cur.lastrowid


def test_recalculo_invalida_por_movimiento_y_caducidad(con, ajustes):
    px = _cartera_con_precio(con)
    b = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 100_000}, _cart(con, ajustes))
    bid = _guardar(con, b)
    assert boleta.recalcular(con, ajustes, bid)["estado"] == "vigente"
    fin = vigencia.ultima_sesion_cerrada("XMEX").isoformat()
    con.execute("UPDATE precios SET cierre=? WHERE instrumento_id='BMV:AMX' AND fecha=?", (px * 1.03, fin))
    con.commit()
    r = boleta.recalcular(con, ajustes, bid)
    assert r["estado"] == "invalidada" and "cambió" in r["motivo_estado"]
    b2 = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 100_000}, _cart(con, ajustes))
    bid2 = _guardar(con, b2)
    futuro = datetime.fromisoformat(b2["caduca_en"]) + timedelta(minutes=1)
    assert boleta.recalcular(con, ajustes, bid2, ahora=futuro)["estado"] == "caducada"


def test_marcar_ejecutada_con_folio_registra_operacion_confirmada(con, ajustes):
    _cartera_con_precio(con)
    b = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 100_000}, _cart(con, ajustes))
    bid = _guardar(con, b)
    antes = len(cartera.listar(con))
    with pytest.raises(ValueError):
        boleta.marcar_ejecutada(con, bid, "  ", "2026-09-02", 10, 100)
    tid = boleta.marcar_ejecutada(con, bid, "F-123", "2026-09-02", b["cantidad"], b["precio_limite"])
    assert len(cartera.listar(con)) == antes + 1 and tid
    f = con.execute("SELECT estado, folio, transaccion_id FROM boletas WHERE id=?", (bid,)).fetchone()
    assert tuple(f) == ("marcada_ejecutada", "F-123", tid)


def test_estados_de_orden_solo_ejecutada_con_confirmacion(con):
    oid = registro.registrar_orden_pendiente(con, "BMV:AMX", "compra", "limitada", 100, 17.5)
    registro.cerrar_orden(con, oid, "enviada")
    assert registro.ordenes(con)[0]["estado"] == "enviada"
    with pytest.raises(ValueError, match="CONFIRMADA"):
        registro.cerrar_orden(con, oid, "ejecutada")
    registro.cerrar_orden(con, oid, "cancelada")
    assert registro.ordenes(con) == []


# --- importadores -----------------------------------------------------------------------------------------------
def _csv(tipo, filas):
    import csv
    import io
    from terminal import importar_contexto as ic
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(ic.COLUMNAS[tipo])
    w.writerows(filas)
    return buf.getvalue().encode()


def test_importar_notas_sa_valida_url_y_duplicados(con):
    c = _csv("notas_sa", [["2026-09-20T10:00:00-06:00", "SIC:AAPL", "Titular", "https://seekingalpha.com/news/1", "hecho (noticia)", "A", "tesis"],
                          ["2026-09-20T10:00:00-06:00", "SIC:AAPL", "Titular", "http://inseguro", "", "", ""]])
    r = importar.importar(con, c, "n.csv", "notas_sa", _ins(con), confirmar=False)
    assert r["rechazadas"] == 1 and r["aceptables"] == 1
    c2 = _csv("notas_sa", [["2026-09-20T10:00:00-06:00", "SIC:AAPL", "Titular", "https://seekingalpha.com/news/1", "hecho (noticia)", "A", "tesis"]])
    assert importar.importar(con, c2, "n.csv", "notas_sa", _ins(con), confirmar=True)["aceptadas"] == 1
    assert importar.importar(con, c2, "n.csv", "notas_sa", _ins(con), confirmar=True)["duplicadas"] == 1
    n = con.execute("SELECT fuente, event_time, available_at FROM noticias").fetchone()
    migraciones.completar_tiempos(con)
    n = con.execute("SELECT fuente, event_time, available_at FROM noticias").fetchone()
    assert n[0] == "seekingalpha_manual" and n[1] < n[2]   # disponible al importarse, no al publicarse


def test_importar_insiderfinance_separa_fechas_y_no_asigna_bmv(con):
    c = _csv("insiderfinance", [["SIC:AAPL", "Jane", "CFO", "S", "2026-09-01", "2026-09-03", "100", "200", "20000", "USD", "https://www.sec.gov/x"],
                                ["BMV:AMX", "X", "", "P", "2026-09-01", "2026-09-03", "100", "20", "2000", "USD", ""],
                                ["SIC:KO", "Y", "", "P", "2026-09-05", "2026-09-03", "100", "60", "6000", "USD", ""]])
    r = importar.importar(con, c, "i.csv", "insiderfinance", _ins(con), confirmar=False)
    assert r["rechazadas"] == 2 and r["aceptables"] == 1
    errores = " ".join(" ".join(d["errores"]) for d in r["detalle"])
    assert "NO CUBRE BMV" in errores and "anterior a la operación" in errores


def test_importar_confirmaciones_exige_entero_y_registra(con):
    t = cartera.validar({"fecha": "2026-09-01", "tipo": "aportacion", "monto": 1_000_000, "moneda": "MXN", "tipo_cambio": 1}, _ins(con))
    cartera.registrar(con, t, "prueba")
    malo = _csv("confirmaciones", [["F-1", "2026-09-02", "BMV:AMX", "compra", "10.5", "17", "", ""]])
    assert importar.importar(con, malo, "c.csv", "confirmaciones", _ins(con))["rechazadas"] == 1
    bueno = _csv("confirmaciones", [["F-2", "2026-09-02", "BMV:AMX", "compra", "1000", "17", "", ""]])
    r = importar.importar(con, bueno, "c.csv", "confirmaciones", _ins(con), confirmar=True)
    assert r["aceptadas"] == 1
    tx = [x for x in cartera.listar(con) if x["tipo"] == "compra"][0]
    assert tx["comision"] == 17.0 and tx["impuesto"] == 2.72          # 0.10 % de 17,000 y 16 % de IVA
    assert importar.importar(con, bueno, "c.csv", "confirmaciones", _ins(con), confirmar=True)["duplicadas"] == 1


def test_importar_saldos(con):
    c = _csv("saldos", [["2026-09-20T15:05:00-06:00", "1003250.75", "500000", "portal"]])
    assert importar.importar(con, c, "s.csv", "saldos", _ins(con), confirmar=True)["aceptadas"] == 1
    assert con.execute("SELECT valor_portafolio FROM saldos_portal").fetchone()[0] == 1003250.75


# --- calendario macro ---------------------------------------------------------------------------------------------
def test_versiones_macro_y_dato_efectivo_no_antes_de_publicarse(con):
    ev = {"id": "e1", "fecha": "2026-10-10T08:30:00-04:00", "pais": "USD", "titulo": "CPI", "impacto": "High",
          "pronostico": "0.3%", "previo": "0.2%", "actual": ""}
    fuentes_web.registrar_versiones_macro(con, [ev], "2026-10-08T00:00:00+00:00")
    fuentes_web.registrar_versiones_macro(con, [ev], "2026-10-09T00:00:00+00:00")        # sin cambio: no hay versión nueva
    fuentes_web.registrar_versiones_macro(con, [{**ev, "pronostico": "0.4%"}], "2026-10-09T12:00:00+00:00")  # revisión
    fuentes_web.registrar_versiones_macro(con, [{**ev, "pronostico": "0.4%", "actual": "0.5%"}], "2026-10-10T13:00:00+00:00")
    assert con.execute("SELECT COUNT(*) FROM eventos_macro_versiones").fetchone()[0] == 3
    antes = fuentes_web.macro_conocido_en(con, "e1", "2026-10-09T06:00:00+00:00")
    assert antes["pronostico"] == "0.3%" and antes["actual"] is None     # consenso vigente en T, sin revisión posterior
    despues = fuentes_web.macro_conocido_en(con, "e1", "2026-10-10T14:00:00+00:00")
    assert despues["actual"] == "0.5%" and despues["actual_publicado"]


# --- estrategias -------------------------------------------------------------------------------------------------
def _precios(n=700, semilla=3):
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({k: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))) for k in "ABCD"}, index=idx)


def test_estrategias_sin_mirar_el_futuro_y_tope():
    p = _precios()
    r1 = estrategias.simular(p, "impulso", {"L": 60}, k=2, inicio=0, fin=500)
    p2 = p.copy()
    p2.iloc[500:] *= 5                     # modificar el futuro no cambia el pasado
    r2 = estrategias.simular(p2, "impulso", {"L": 60}, k=2, inicio=0, fin=500)
    assert r1["resultado_neto"] == pytest.approx(r2["resultado_neto"])
    assert estrategias.simular(p, "efectivo")["resultado_neto"] == 0.0
    w = estrategias.pesos_objetivo("impulso", {"L": 20}, p.iloc[:300], 1)
    assert w.max() <= estrategias.TOPE + 1e-12      # tope de 50 % aunque la regla elija un solo activo


def test_experimento_registra_todas_las_configuraciones_y_veredicto():
    res = estrategias.experimento(_precios(900), k=2)
    n_grid = sum(len(v) for v in estrategias.FAMILIAS.values())
    n_prueba = (len(estrategias.REFERENCIAS) + len(estrategias.FAMILIAS)) * len(estrategias.DESLIZAMIENTOS)
    assert len(res["configuraciones_registradas"]) == n_grid + n_prueba
    assert res["veredicto_global"] in ("VENTAJA FUERA DE MUESTRA", estrategias.VENTAJA_NO)
    netos = {r["estrategia"]: r for r in res["resumen"]}
    assert netos["impulso"]["neto_desliz_0.5%"] <= netos["impulso"]["neto_sin_desliz"]   # más deslizamiento, menos neto


# --- calidad y proveedor extranjero --------------------------------------------------------------------------------
def test_stale_y_proveedor_extranjero(con):
    q = {"proveedor": "x", "simbolo_origen": "AMX", "simbolo_normalizado": "BMV:AMX", "instrumento_id": "BMV:AMX", "mercado": "local",
         "bolsa": "BMV", "precio": 17.0, "moneda": "MXN", "hora_evento": "2026-09-01T20:00:00+00:00",
         "hora_recepcion": "2026-09-01T20:30:00+00:00", "latencia_declarada_s": None, "estado_latencia": "EOD", "sintetico": False,
         "detalle": ""}
    assert cz.calidad_actual(q, datetime(2026, 9, 30, tzinfo=UTC)) == "STALE"
    ext = cz.ForeignMarketLicensedProvider(con, {})
    assert not ext.configurado() and ext.entrega_mercado == ("origen_extranjero",)
    assert any("EXT_API_KEY" in p for p in ext.pendientes())


def test_ruptura_de_tesis(con, ajustes):
    from terminal import alertas
    px = _cartera_con_precio(con)
    t = cartera.validar({"fecha": "2026-09-02", "tipo": "compra", "instrumento_id": "BMV:AMX", "cantidad": 100, "precio": px,
                         "comision": 0, "impuesto": 0, "moneda": "MXN", "tipo_cambio": 1}, _ins(con))
    cartera.registrar(con, t, "prueba")
    registro.registrar_decision(con, "tesis", "Mantengo mientras no rompa soporte", "BMV:AMX", tesis="soporte",
                                nivel_invalidacion=px * 1.1, direccion_invalidacion="debajo")
    conds = alertas.reglas_tesis(con, _cart(con, ajustes))
    assert conds and conds[0].activa and "impacto_mxn" in conds[0].datos


def test_plan_inicial_sin_operaciones_usa_capital_supuesto(con, ajustes):
    fin = vigencia.ultima_sesion_cerrada("XMEX")
    sembrar_precios(con, ["BMV:AMX"], fin=fin, sesiones=300, proveedor="archivo", con_fx=False)
    migraciones.completar_tiempos(con)
    cart = _cart(con, ajustes)
    assert not cart["n_operaciones"]
    sin = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 100_000}, cart)
    assert sin["cantidad"] == 0                              # sin efectivo registrado no hay compra posible
    con_plan = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 100_000}, cart,
                                efectivo_supuesto=1_000_000)
    assert con_plan["plan_inicial"] and con_plan["cantidad"] > 0 and con_plan["tipo"] == "considerar compra"
    assert any("aportación inicial" in f for f in con_plan["datos_faltantes"])


def test_sic_sin_cotizacion_confiable_da_referencia_condicional_no_ejecutable(con, ajustes):
    sembrar_precios(con, ["SIC:AAPL"], fin=vigencia.ultima_sesion_cerrada("XNYS"), sesiones=300, proveedor="tiingo")
    migraciones.completar_tiempos(con)
    t = cartera.validar({"fecha": "2026-09-01", "tipo": "aportacion", "monto": 1_000_000, "moneda": "MXN", "tipo_cambio": 1}, _ins(con))
    cartera.registrar(con, t, "prueba")
    con.commit()
    b = boleta.construir(con, ajustes, {"id": "SIC:AAPL", "accion": "comprar", "monto_mxn": 50_000}, _cart(con, ajustes))
    r = b["referencia_condicional"]
    assert b["tipo"] == "investigar" and b["lado"] is None and b["cantidad"] == 0 and b["precio_limite"] is None
    assert r["lado_sugerido"] == "compra" and r["fuente"] == "tiingo" and r["tipo_cambio"]
    assert r["precio_min"] < r["precio_ref_mxn"] < r["precio_max"]
    assert r["titulos_aprox"] == int(50_000 // (r["precio_ref_mxn"] * 1.02)) or abs(r["titulos_aprox"] - 50_000 / r["precio_max"]) < 1
    assert "REFERENCIA" in r["nota"]
    txt = boleta.texto_telegram([{**b, "id": 1, "estado": "vigente"}])
    assert "Condicionales (1)" in txt and "banda" in txt and "Listas" not in txt


def test_recalcular_no_invalida_por_redondeo_de_la_cantidad(con, ajustes):
    """títulos × límite ÷ límite no debe perder un título por punto flotante (7,994 × 14.91 ÷ 14.91 = 7,993.999…)."""
    px = _cartera_con_precio(con)
    b = boleta.construir(con, ajustes, {"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 119_191.0}, _cart(con, ajustes))
    assert b["cantidad"] > 0 and b["monto_objetivo"] == 119_191.0
    bid = _guardar(con, b)
    r = boleta.recalcular(con, ajustes, bid)
    assert r["estado"] == "vigente" and r["cantidad"] == b["cantidad"]


def test_sic_investigar_conserva_referencia_al_recalcular_y_mantener_no_es_investigar(con, ajustes):
    sembrar_precios(con, ["SIC:AAPL"], fin=vigencia.ultima_sesion_cerrada("XNYS"), sesiones=300, proveedor="tiingo")
    migraciones.completar_tiempos(con)
    t = cartera.validar({"fecha": "2026-09-01", "tipo": "aportacion", "monto": 1_000_000, "moneda": "MXN", "tipo_cambio": 1}, _ins(con))
    cartera.registrar(con, t, "prueba")
    con.commit()
    b = boleta.construir(con, ajustes, {"id": "SIC:AAPL", "accion": "comprar", "monto_mxn": 50_000}, _cart(con, ajustes))
    bid = _guardar(con, b)
    r = boleta.recalcular(con, ajustes, bid)
    assert r["tipo"] == "investigar" and r["referencia_condicional"] and r["referencia_condicional"]["lado_sugerido"] == "compra"
    m = boleta.construir(con, ajustes, {"id": "SIC:AAPL", "accion": "mantener", "monto_mxn": 900}, _cart(con, ajustes))
    assert m["tipo"] == "mantener" and m["lado"] is None


def test_venta_sic_condicional_usa_la_tenencia(con, ajustes):
    """Vender toda la posición SIC sin cotización confiable: la guía indica los títulos que se tienen (no 0 por la banda)."""
    sembrar_precios(con, ["SIC:AAPL"], fin=vigencia.ultima_sesion_cerrada("XNYS"), sesiones=300, proveedor="tiingo")
    migraciones.completar_tiempos(con)
    from terminal import mercado
    px = mercado.cotizaciones(con, ajustes, ["SIC:AAPL"])["SIC:AAPL"]["precio_mxn"]
    cart = {"fuente": "portal", "efectivo": 100_000.0, "valor_total": 100_000.0 + px, "n_operaciones": 1,
            "posiciones": [{"instrumento_id": "SIC:AAPL", "cantidad": 1, "valor_mxn": px}]}
    b = boleta.construir(con, ajustes, {"id": "SIC:AAPL", "accion": "vender", "monto_mxn": -px}, cart)
    assert b["tipo"] == "investigar" and b["referencia_condicional"]["titulos_aprox"] == 1
    assert "todos sus títulos (1)" in b["referencia_condicional"]["nota"]


def test_api_boletas_telegram_genera_vista_previa_y_envia(monkeypatch):
    from fastapi.testclient import TestClient

    from terminal import notificador
    from terminal.app import app
    from terminal.seguridad import TOKEN_CSRF
    llamadas, enviados = [], []
    lista = [{"id": 1, "estado": "vigente", "tipo": "considerar compra", "cantidad": 10, "lado": "compra",
              "emisora_serie": "AMX B", "instrumento_id": "BMV:AMX", "precio_limite": 17.5, "importe": 175.0,
              "caduca_en": "2026-10-01T14:45:00+00:00", "fuente_precio": {"proveedor": "eodhd_bmv", "moneda": "MXN",
                                                                         "estado_latencia": "EOD", "hora_evento": None}},
             {"id": 2, "estado": "vigente", "tipo": "investigar", "cantidad": 0, "lado": None, "emisora_serie": "MU *",
              "instrumento_id": "SIC:MU", "caduca_en": "2026-10-01T14:45:00+00:00",
              "referencia_condicional": {"lado_sugerido": "compra", "titulos_aprox": 10, "monto_mxn": 200000,
                                         "precio_min": 1, "precio_max": 2, "fuente": "tiingo", "moneda_origen": "USD",
                                         "precio_origen": 1065.1, "fecha": "2026-09-30", "estado": "vigente",
                                         "tipo_cambio": 18.07, "tipo_cambio_fuente": "banxico", "tipo_cambio_fecha": "2026-09-30"}}]
    monkeypatch.setattr(boleta, "generar", lambda *a, **k: llamadas.append("generar") or [{}])
    monkeypatch.setattr(boleta, "listar", lambda *a, **k: lista)
    monkeypatch.setattr(notificador, "enviar", lambda t, x, c, detalle=None: enviados.append(x) or {"telegram": "enviada"})
    h = {"X-CSRF-Token": TOKEN_CSRF}
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        assert c.post("/api/boletas/telegram", json={"generar": True}).status_code == 403          # sin CSRF
        previa = c.post("/api/boletas/telegram", json={"generar": True, "enviar": False}, headers=h).json()
        assert previa["resultado"] is None and previa["conteo"] == {"listas": 1, "condicionales": 1, "por_investigar": 0}
        assert not enviados and "COMPRA AMX B" in previa["texto"]
        r = c.post("/api/boletas/telegram", json={"generar": True}, headers=h).json()
        assert r["resultado"]["telegram"] == "enviada" and len(enviados) == 1 and llamadas == ["generar", "generar"]
