"""Movimientos públicos con documentos reales de SEC EDGAR (tests/fixtures/sec, descargados el 1-oct-2026):
13F corregido (NEW HOLDINGS), split, símbolo ambiguo, Form 4 no discrecional, 4/A duplicada y publicación posterior."""
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from terminal import alertas
from terminal.movimientos import almacen as alm
from terminal.movimientos import sec, servicio

F = Path(__file__).parent / "fixtures" / "sec"
TICKERS = json.loads((F / "company_tickers_extracto.json").read_text(encoding="utf-8"))
BRK = "1067983"
APA = "1656456"


def _13f(con, prefijo, acceso, cik, fecha, aceptado):
    p = sec.parsear_portada_13f((F / f"{prefijo}_primary.xml").read_bytes())
    filas = sec.parsear_tabla_13f((F / f"{prefijo}_infotable.xml").read_bytes())
    alm.guardar_13f(con, acceso=acceso, cik=cik, gestor="prueba", fecha_presentacion=fecha, aceptado_en=aceptado, portada=p,
                    filas=filas, url=sec.url_documento(cik, acceso, "primary_doc.xml"), url_indice=sec.url_indice(cik, acceso))
    for f in filas:
        alm.mapear_cusip(con, f["cusip"], f["emisor"], TICKERS)


def _f4(con, archivo, acceso, cik, fecha, aceptado):
    f4 = sec.parsear_form4((F / archivo).read_bytes())
    alm.guardar_form4(con, acceso=acceso, cik_presentador=cik, fecha_presentacion=fecha, aceptado_en=aceptado, f4=f4,
                      url=sec.url_documento(cik, acceso, "form4.xml"), url_indice=sec.url_indice(cik, acceso))


@pytest.fixture
def mov(con):
    alm.asegurar(con)
    return con


def test_13f_corregido_new_holdings_y_publicacion_posterior(mov):
    """Berkshire 1T-2025: el original (15-may-2025) y la enmienda NEW HOLDINGS (14-ago-2025, tratamiento confidencial
    vencido) que añade D.R. Horton y Lennar. Antes del 14-ago esas posiciones no se conocían: no se usan."""
    _13f(mov, "brk_2025q1", "0000950123-25-005701", BRK, "2025-05-15", "2025-05-15T20:06:43.000Z")
    _13f(mov, "brk_2025q1_A", "0000950123-25-008361", BRK, "2025-08-14", "2025-08-14T20:10:02.000Z")
    antes, docs_antes = alm.cartera_13f(mov, BRK, "2025-03-31", hasta="2025-06-01T00:00:00+00:00")
    despues, docs_despues = alm.cartera_13f(mov, BRK, "2025-03-31", hasta="2025-09-01T00:00:00+00:00")
    assert ("23331A109", "SH") not in antes and ("23331A109", "SH") in despues       # D.R. Horton
    assert len(docs_antes) == 1 and {d["tipo_enmienda"] for d in docs_despues} == {None, "NEW HOLDINGS"}
    # La enmienda añade D.R. Horton, Lennar A y Nucor (nuevas) y más Lennar B (ya estaba en el original: se suma)
    assert len(despues) == len(antes) + 3
    assert despues[("526057302", "SH")]["titulos"] > antes[("526057302", "SH")]["titulos"]
    assert len(despues[("526057302", "SH")]["accesos"]) == 2


def test_split_real_nvidia_appaloosa(mov):
    """442,000 NVDA (1T-2024) → 690,000 (2T-2024) parece un aumento; con el split 10:1 del 10-jun-2024 es una reducción."""
    _13f(mov, "appaloosa_2024-03", "0001656456-24-000002", APA, "2024-05-15", "2024-05-15T16:00:00Z")
    _13f(mov, "appaloosa_2024-06", "0001656456-24-000003", APA, "2024-08-14", "2024-08-14T16:00:00Z")
    con_split = alm.cambios_13f(mov, APA, factor_split=lambda c, d, h: 10.0 if c == "67066G104" else 1.0)
    nvda = next(f for f in con_split["filas"] if f["cusip"] == "67066G104")
    assert nvda["titulos_previo_ajustado"] == 4_420_000 and nvda["clasificacion"] == "reduccion"
    sin_split = alm.cambios_13f(mov, APA)
    nvda2 = next(f for f in sin_split["filas"] if f["cusip"] == "67066G104")
    assert nvda2["clasificacion"] == "no_comparable" and "split" in nvda2["nota"]   # nunca «aumento»


def test_split_desde_eventos_corporativos_de_la_terminal(mov):
    mov.execute("INSERT OR REPLACE INTO eventos_corporativos (instrumento_id, fecha, tipo, valor, proveedor) "
                "VALUES ('SIC:NVDA','2024-06-10','split',10,'prueba')")
    _13f(mov, "appaloosa_2024-03", "0001656456-24-000002", APA, "2024-05-15", "2024-05-15T16:00:00Z")
    _13f(mov, "appaloosa_2024-06", "0001656456-24-000003", APA, "2024-08-14", "2024-08-14T16:00:00Z")
    assert servicio.factor_split(mov)("67066G104", "2024-03-31", "2024-06-30") == 10.0


def test_valor_declarado_en_miles_se_reescala_y_se_anota():
    """Duquesne y Baupost declaran VALUE en miles aun después de 2023 (precio implícito ≈ 0.09 USD por acción)."""
    filas = [{"emisor": f"E{i}", "clase": "COM", "cusip": f"00000000{i}", "valor": 100.0, "titulos": 1000.0, "tipo_titulos": "SH",
              "put_call": None} for i in range(5)]
    escala, nota = sec.escala_valor(filas, "2026-08-14")
    assert escala == 1000.0 and "miles" in nota
    assert sec.agregar_tabla(filas, "2026-08-14")[("000000000", "SH")]["valor_usd"] == 100_000.0
    reales = sec.parsear_tabla_13f((F / "brk_2026q2_infotable.xml").read_bytes())
    assert sec.escala_valor(reales, "2026-08-14") == (1.0, None)        # Berkshire sí declara en dólares


def test_simbolo_ambiguo_varias_clases_no_se_atribuye(mov):
    len_a = alm.mapear_cusip(mov, "526057104", "LENNAR CORP", TICKERS)       # CL A
    dhi = alm.mapear_cusip(mov, "23331A109", "D R HORTON INC", TICKERS)       # la SEC lo llama «HORTON D R INC /DE/»
    nada = alm.mapear_cusip(mov, "999999999", "EMPRESA INEXISTENTE SA", TICKERS)
    assert len_a["simbolo"] is None and len_a["ambiguo"] == 1 and len_a["candidatos"] == "LEN,LEN-B"
    assert dhi["simbolo"] == "DHI" and nada["metodo"] == "sin_coincidencia"
    forzado = alm.mapear_cusip(mov, "02079K305", "ALPHABET INC", TICKERS, {"02079K305": "GOOGL"})
    assert forzado["simbolo"] == "GOOGL" and forzado["metodo"] == "manual"


def test_form4_no_discrecional_y_plan_10b5_1():
    a = sec.parsear_form4((F / "f4_AF_AAPL_0001140361-26-038028.xml").read_bytes())
    assert {t["clasificacion"] for t in a.transacciones} == {"adjudicacion"} and not any(t["discrecional"] for t in a.transacciones)
    k = sec.parsear_form4((F / "f4_10b5_KO_0000021344-26-000156.xml").read_bytes())
    assert k.plan_10b5_1 and {t["clasificacion"] for t in k.transacciones if t["codigo"] == "S"} == {"venta_plan_10b5_1"}
    p = sec.parsear_form4((F / "f4_P_KO_0000021344-25-000075.xml").read_bytes())
    assert p.declarantes[0]["relacion"] == "consejero"
    assert all(t["clasificacion"] == "compra_mercado" and t["discrecional"] and t["titularidad"] == "D" for t in p.transacciones)


def test_venta_tras_ejercicio_no_es_senal_material(mov):
    _f4(mov, "f4_A_o_M_o_F_KO_0000021344-26-000167.xml", "0000021344-26-000167", "21344", "2026-08-24", "2026-08-24T20:00:00Z")
    ventas = [r for r in alm.form4(mov) if r["codigo"] == "S"]
    assert ventas and all(r["tras_ejercicio"] == 1 for r in ventas)


def test_4a_sin_duplicar_y_original_marcado_como_corregido(mov):
    _f4(mov, "f4_original_JNJ_0001193125-25-303876.xml", "0001193125-25-303876", "200406", "2025-12-01", "2025-12-01T21:00:00Z")
    _f4(mov, "f4_4A_JNJ_0001193125-26-007679.xml", "0001193125-26-007679", "200406", "2026-01-08", "2026-01-08T21:00:00Z")
    filas = alm.form4(mov)
    assert sorted((r["fecha_operacion"], r["titulos"]) for r in filas) == [("2025-11-25", 16000.0), ("2025-11-26", 6337.0)]
    original = next(r for r in filas if r["acceso"] == "0001193125-25-303876")
    assert original["corregido_por"] == "0001193125-26-007679" and original["tambien_en"] == ["0001193125-26-007679"]
    assert original["titularidad"] == "I" and len(original["declarantes"]) == 2
    # Antes de publicarse la 4/A, solo se conocía la venta del 26-nov
    antes = alm.form4(mov, hasta="2025-12-15T00:00:00+00:00")
    assert [(r["fecha_operacion"], r.get("corregido_por")) for r in antes] == [("2025-11-26", None)]
    # Guardar otra vez el mismo documento no duplica nada
    _f4(mov, "f4_4A_JNJ_0001193125-26-007679.xml", "0001193125-26-007679", "200406", "2026-01-08", "2026-01-08T21:00:00Z")
    assert len(alm.form4(mov)) == 2


def test_fecha_limite_13f_del_tercer_trimestre_es_posterior_al_reto():
    assert servicio.fecha_limite_13f("2026-09-30") == "2026-11-16"


def test_alerta_material_una_sola_vez_y_solo_contexto(mov, ajustes, monkeypatch):
    _f4(mov, "f4_P_KO_0000021344-25-000075.xml", "0000021344-25-000075", "21344", "2025-10-27", "2025-10-27T20:30:00Z")
    _f4(mov, "f4_AF_AAPL_0001140361-26-038028.xml", "0001140361-26-038028", "320193", "2025-10-27", "2025-10-27T20:31:00Z")
    mov.execute("INSERT INTO seguimiento (instrumento_id, agregado_en) VALUES ('SIC:KO', '2025-10-01')")
    mov.execute("INSERT INTO seguimiento (instrumento_id, agregado_en) VALUES ('SIC:AAPL', '2025-10-01')")
    ahora = datetime(2025, 10, 28, 15, tzinfo=UTC)
    conds = servicio.condiciones(mov, ajustes, ahora)
    assert len(conds) == 3 and all(c.regla == "movimiento_publico" for c in conds)            # 3 compras de KO; AAPL (adjudicación) no
    assert all("no es una recomendación" in c.accion for c in conds) and all("sec.gov" in c.datos["enlace"] for c in conds)
    monkeypatch.setattr(alertas.notificador, "enviar", lambda *a, **k: {"telegram": "enviada"})
    cfg = {**ajustes["alertas"], "silenciar_fuera_de_horario": False}
    primera = alertas.procesar(mov, conds, cfg, ahora)
    segunda = alertas.procesar(mov, servicio.condiciones(mov, ajustes, ahora), cfg, ahora)
    assert len(primera) == 3 and segunda == []                                                  # sin duplicados
    # Publicado hace más de 3 días: ya no es «nuevo»
    assert servicio.condiciones(mov, ajustes, datetime(2025, 11, 5, tzinfo=UTC)) == []


def test_listado_separa_operables_y_conserva_evidencia(mov, ajustes):
    _f4(mov, "f4_P_KO_0000021344-25-000075.xml", "0000021344-25-000075", "21344", "2025-10-27", "2025-10-27T20:30:00Z")
    _f4(mov, "f4_4A_JNJ_0001193125-26-007679.xml", "0001193125-26-007679", "200406", "2026-01-08", "2026-01-08T21:00:00Z")
    d = servicio.listar(mov, ajustes)
    ko = next(r for r in d["form4"] if r["simbolo"] == "KO")
    cvrx = next(r for r in d["form4"] if r["simbolo"] == "CVRX")
    assert ko["instrumento_id"] == "SIC:KO" and cvrx["grupo"] == "fuera del catálogo" and not cvrx["operable"]
    assert ko["url"].startswith("https://www.sec.gov/Archives/") and ko["fecha_operacion"] and ko["aceptado_en"] and ko["conocido_en"]
    assert "no es cotización del SIC" in (ko["referencia_mxn"] or {"etiqueta": "no es cotización del SIC"})["etiqueta"]
    solo_compras = servicio.listar(mov, ajustes, tipo="compra_mercado")["form4"]
    assert solo_compras and all(r["clasificacion"] == "compra_mercado" for r in solo_compras)


def test_cliente_sec_exige_identificacion_y_reintenta_429():
    with pytest.raises(sec.ErrorSEC):
        sec.ClienteSEC(None)
    llamadas = []

    def manejar(req):
        llamadas.append(req.headers["User-Agent"])
        return httpx.Response(429, headers={"Retry-After": "0"}) if len(llamadas) == 1 else httpx.Response(200, json={"ok": 1})

    c = sec.ClienteSEC("Prueba prueba@ejemplo.com", cliente=httpx.Client(transport=httpx.MockTransport(manejar)), dormir=lambda s: None)
    assert c.get("https://data.sec.gov/x").json() == {"ok": 1} and len(llamadas) == 2 and c.consultas == 2


def test_actualizacion_incremental_no_vuelve_a_pedir_documentos(mov, ajustes, monkeypatch):
    """Con la SEC simulada (respuestas reales guardadas), la segunda pasada no descarga documentos ya procesados."""
    sub = {"filings": {"recent": {"form": ["4"], "accessionNumber": ["0000021344-25-000075"], "primaryDocument": ["xslF345X05/form4.xml"],
                                   "filingDate": [datetime.now(UTC).date().isoformat()], "acceptanceDateTime": ["2025-10-27T20:30:00.000Z"]}}}
    pedidas = []

    def manejar(req):
        u = str(req.url)
        pedidas.append(u)
        if u.endswith("company_tickers.json"):
            return httpx.Response(200, json={str(i): t for i, t in enumerate(TICKERS)})
        if "submissions" in u:
            return httpx.Response(200, json=sub)
        return httpx.Response(200, content=(F / "f4_P_KO_0000021344-25-000075.xml").read_bytes())

    monkeypatch.setattr(servicio.config, "data_dir", lambda *a: Path(mov.execute("PRAGMA database_list").fetchone()[2]).parent)
    cli = sec.ClienteSEC("Prueba prueba@ejemplo.com", cliente=httpx.Client(transport=httpx.MockTransport(manejar)), dormir=lambda s: None)
    ko = [dict(mov.execute("SELECT * FROM instrumentos WHERE id='SIC:KO'").fetchone())]
    r1 = servicio.actualizar_form4(mov, ajustes, cli, emisoras=ko)
    r2 = servicio.actualizar_form4(mov, ajustes, cli, emisoras=ko)
    assert r1["documentos_nuevos"] == 1 and r2["documentos_nuevos"] == 0
    assert sum("form4.xml" in u for u in pedidas) == 1


def test_los_modulos_de_decision_no_usan_movimientos_publicos():
    raiz = Path(__file__).resolve().parents[1] / "terminal"
    for m in ("plan_accion.py", "boleta.py", "optimizador.py", "resumen.py", "ranking.py"):
        assert "movimientos" not in (raiz / m).read_text(encoding="utf-8"), m
