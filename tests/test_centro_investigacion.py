"""APIs de investigación: datos honestos, límites, revisiones y aislamiento de cartera."""
import csv
import io
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from terminal import centro_investigacion as centro
from terminal.app import app
from terminal.centro_conectores import AlphaVantage, BLS, CoinGecko, EIA, FredMacro
from terminal.seguridad import TOKEN_CSRF

AHORA = datetime(2026, 10, 11, 15, 0, tzinfo=UTC)


def csv_registros(*filas):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=centro.COLUMNAS)
    w.writeheader()
    for f in filas:
        w.writerow({"fuente": "roic_ai", "simbolo": "MU", "serie": "ROIC", "titulo": "Retorno sobre capital",
                    "periodo": "2026-Q2", "valor": "0.12", "unidad": "fracción", "texto": "Dato de prueba",
                    "url": "https://www.roic.ai/quote/MU", **f})
    return s.getvalue().encode()


def bls_respuesta():
    return {"status": "REQUEST_SUCCEEDED", "Results": {"series": [
        {"seriesID": sid, "data": [{"year": "2026", "period": "M09", "value": "330", "footnotes": []},
                                    {"year": "2025", "period": "M09", "value": "300", "footnotes": []},
                                    {"year": "2026", "period": "M13", "value": "99999"}]}
        for sid in BLS.SERIES]}}


def test_importacion_no_cambia_precios_cartera_y_no_fuga_temporal(con):
    antes = con.execute("SELECT COUNT(*) FROM precios").fetchone()[0]
    assert centro.importar_csv(con, csv_registros({}), AHORA)["nuevos"] == 1
    assert con.execute("SELECT COUNT(*) FROM precios").fetchone()[0] == antes
    assert centro.observaciones(con, hasta=AHORA-timedelta(seconds=1)) == []
    fila = centro.observaciones(con, "MU", AHORA)[0]
    assert fila["origen"] == "manual" and fila["valor"] == 0.12
    assert datetime.fromisoformat(fila["disponible_desde"]) == AHORA
    assert centro.observaciones(con, "AMD", AHORA) == []


def test_revisiones_incluso_retorno_a_valor_anterior(con):
    for i, valor in enumerate(("0.12", "0.15", "0.12", "0.12")):
        centro.importar_csv(con, csv_registros({"valor": valor}), AHORA+timedelta(hours=i))
    assert con.execute("SELECT COUNT(*) FROM investigacion_observaciones").fetchone()[0] == 3
    assert centro.observaciones(con, hasta=AHORA+timedelta(hours=1))[0]["valor"] == 0.15
    actual = centro.observaciones(con, hasta=AHORA+timedelta(hours=3))[0]
    assert actual["valor"] == 0.12
    assert datetime.fromisoformat(actual["disponible_desde"]) == AHORA+timedelta(hours=2)


@pytest.mark.parametrize("cambio", [
    {"valor": "nan"}, {"valor": "Infinity"}, {"periodo": "2030-01"}, {"periodo": "2026-13"},
    {"url": "https://malicioso.example/"}, {"url": "https://roic.ai.evil.test"},
    {"url": "https://roic.ai/?apikey=secreto"}, {"fuente": "inventada"},
    {"url": "https://roic.ai:credencial-no-revelar/"},
    {"valor": "", "texto": ""}, {"simbolo": "<script>"}, {"unidad": ""},
])
def test_csv_invalido_se_rechaza_atomicamente(con, cambio):
    with pytest.raises(ValueError):
        centro.importar_csv(con, csv_registros({}, cambio), AHORA)
    assert con.execute("SELECT COUNT(*) FROM investigacion_observaciones").fetchone()[0] == 0


def test_notas_y_exportacion_no_ejecuta_formulas(con):
    centro.importar_csv(con, csv_registros({"valor": "", "unidad": "", "texto": "=HYPERLINK(\"example\")"}), AHORA)
    assert "'=HYPERLINK" in centro.exportar(con)


def test_clave_no_puede_importarse(con, monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "credencial-de-prueba-123")
    with pytest.raises(ValueError, match="credencial"):
        centro.importar_csv(con, csv_registros({"texto": "credencial-de-prueba-123"}), AHORA)


def test_bls_publico_cache_y_yoy(con, ajustes):
    vistos = []
    def responder(r):
        vistos.append(r)
        assert r.method == "POST" and "registrationkey" not in r.content.decode()
        return httpx.Response(200, json=bls_respuesta())
    cli = httpx.Client(transport=httpx.MockTransport(responder))
    r = centro.actualizar(con, ajustes, AHORA, env={}, cliente=cli)
    assert r["fuentes"]["bls"]["estado"] == "ok" and r["nuevos"] == 7
    assert r["fuentes"]["fred_macro"]["estado"] == "sin_credencial"
    obs = centro.observaciones(con, hasta=AHORA)
    assert all(x["periodo"] != "2026-13" for x in obs)
    assert next(x for x in obs if x["serie"] == "CPI_YOY")["valor"] == pytest.approx(10)
    assert centro.actualizar(con, ajustes, AHORA+timedelta(minutes=1), env={}, cliente=cli)["nuevos"] == 0
    assert len(vistos) == 1


def test_demo_no_red(con, ajustes):
    from terminal.config import fijar_modo
    fijar_modo("demo")
    try:
        cli = httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("No debe consultar red")))
        assert centro.actualizar(con, ajustes, AHORA, env={}, cliente=cli)["estado"] == "demo_sin_consultas"
    finally:
        fijar_modo("real")


def test_error_fuente_no_filtra_clave_ni_impide_bls(con, ajustes):
    def responder(r):
        return httpx.Response(200, json=bls_respuesta()) if r.url.host == "api.bls.gov" else httpx.Response(403, text="secreto123")
    cli = httpx.Client(transport=httpx.MockTransport(responder))
    r = centro.actualizar(con, ajustes, AHORA, env={"ALPHAVANTAGE_API_KEY": "secreto123"}, cliente=cli)
    assert r["fuentes"]["alpha_vantage"]["estado"] == "error" and r["fuentes"]["bls"]["estado"] == "ok"
    assert "secreto123" not in str(r)
    assert "secreto123" not in str(centro.resumen(con, ajustes, ahora=AHORA, env={"ALPHAVANTAGE_API_KEY": "secreto123"}))


def test_presupuesto_diario_se_conserva_entre_llamadas(con, ajustes):
    ajustes.datos["centro_investigacion"] = {"bls": {"peticiones_por_dia": 1}}
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    assert centro.actualizar(con, ajustes, AHORA, env={}, cliente=cli)["fuentes"]["bls"]["estado"] == "error"
    assert centro.actualizar(con, ajustes, AHORA+timedelta(hours=2), env={}, cliente=cli)["fuentes"]["bls"]["estado"] == "limite"
    assert con.execute("SELECT peticiones FROM uso_proveedor WHERE proveedor='bls'").fetchone()[0] == 1


def test_conector_alpha_confirma_simbolo_y_limite_semantico(con):
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"Information": "secreto"})))
    a = AlphaVantage(con, {"simbolos": ["MU"]}, "clave", cli)
    with pytest.raises(Exception, match="límite"):
        a.consultar(AHORA)
    def respuesta(r):
        assert r.url.params["function"] == "INCOME_STATEMENT"
        return httpx.Response(200, json={"symbol": "MU", "annualReports": [{"fiscalDateEnding": "2025-12-31",
            "reportedCurrency": "USD", "totalRevenue": "100", "netIncome": "15", "operatingIncome": "25"}]})
    cli = httpx.Client(transport=httpx.MockTransport(respuesta))
    out = AlphaVantage(con, {"simbolos": ["MU"]}, "clave", cli).consultar(AHORA)
    assert len(out) == 5 and all(o["periodo"] == "2025-12-31" and o["simbolo"] == "MU" for o in out)
    assert next(o for o in out if o["serie"] == "net_margin")["valor"] == pytest.approx(0.15)


def test_fred_conserva_periodos_y_ignora_ausentes(con):
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"observations": [
        {"date": "2026-10-09", "value": "4.2"}, {"date": "2026-10-08", "value": "."}]})))
    filas = FredMacro(con, {}, "clave", cli).consultar(AHORA)
    assert len(filas) == 4 and all(f["periodo"] == "2026-10-09" for f in filas)


def test_eia_v2_seriesid(con):
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"response": {"data": [
        {"period": "2026-10-09", "value": "70.5"}]}})))
    filas = EIA(con, {}, "clave", cli).consultar(AHORA)
    assert len(filas) == 3 and filas[0]["valor"] == 70.5


def test_coingecko_conserva_hora_atrasada(con, ajustes):
    hora = int((AHORA-timedelta(days=2)).timestamp())
    def responder(r):
        assert r.headers["x-cg-demo-api-key"] == "clave"
        return httpx.Response(200, json={m: {"usd": 10, "last_updated_at": hora} for m in ("bitcoin", "ethereum")})
    cli = httpx.Client(transport=httpx.MockTransport(responder))
    out = CoinGecko(con, {}, "clave", cli).consultar(AHORA)
    fuente = next(f for f in centro.fuentes() if f["id"] == "coingecko")
    with centro.db.transaccion(con):
        centro._guardar(con, [centro._validar(f, fuente, AHORA, "api") for f in out], AHORA)
    assert all(f["referencia_atrasada"] for f in centro.resumen(con, ajustes, ahora=AHORA, env={})["observaciones"])
    assert con.execute("SELECT COUNT(*) FROM instrumentos WHERE id IN ('BTC','ETH')").fetchone()[0] == 0


def test_api_local_protegida_y_catalogo_completo(con):
    from terminal.app import con_db
    app.dependency_overrides[con_db] = lambda: con
    try:
        with TestClient(app, base_url="http://127.0.0.1:8765") as c:
            d = c.get("/api/centro-investigacion").json()
            assert len(d["fuentes"]) == 16 and sum(f["conector"] for f in d["fuentes"]) == 5
            assert next(f for f in d["fuentes"] if f["id"] == "ssrn")["estado"] == "consulta_manual"
            assert c.post("/api/centro-investigacion/actualizar", json={}).status_code == 403
            r = c.post("/api/centro-investigacion/importar", headers={"X-CSRF-Token": TOKEN_CSRF},
                       files={"archivo": ("hallazgos.csv", csv_registros({}), "text/csv")})
            assert r.status_code == 200 and r.json()["nuevos"] == 1
            assert c.get("/api/centro-investigacion/exportar").headers["content-type"].startswith("text/csv")
            assert c.get("/api/centro-investigacion?simbolo=%3Cscript%3E").status_code == 422
            assert c.get("/api/centro-investigacion/exportar?simbolo=%3Cscript%3E").status_code == 422
            r = c.post("/api/centro-investigacion/importar", headers={"X-CSRF-Token": TOKEN_CSRF},
                       files={"archivo": ("mal.csv", csv_registros({"valor": "nan"}), "text/csv")})
            assert r.status_code == 422 and "finito" in r.json()["detail"]
    finally:
        app.dependency_overrides.pop(con_db, None)


def test_ssrn_se_importa_como_nota_sin_modificar_precios(con):
    antes = con.execute("SELECT COUNT(*) FROM precios").fetchone()[0]
    csv = csv_registros({"fuente": "ssrn", "serie": "microestructura", "titulo": "Hipótesis de flujo de órdenes",
                         "periodo": "2026-10-10", "valor": "", "unidad": "", "texto": "Referencia académica; pendiente de evaluación.",
                         "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=123456"})
    assert centro.importar_csv(con, csv, AHORA)["nuevos"] == 1
    assert con.execute("SELECT COUNT(*) FROM precios").fetchone()[0] == antes
    assert centro.observaciones(con, "MU", AHORA)[0]["fuente"] == "ssrn"
    with pytest.raises(ValueError):
        centro.importar_csv(con, csv_registros({"fuente": "ssrn", "url": "https://ssrn.com.evil.test/paper"}), AHORA)


def test_alpha_guarda_simbolos_que_responden_y_para_ante_el_limite(con):
    """Un aviso de límite en el 2.º símbolo ya no anula el 1.º, y no se gastan peticiones en los siguientes."""
    vistos = []

    def respuesta(r):
        s = r.url.params["symbol"]
        vistos.append(s)
        if s == "AMD":
            return httpx.Response(200, json={"Information": "rate limit"})
        return httpx.Response(200, json={"symbol": s, "annualReports": [{"fiscalDateEnding": "2025-12-31",
            "reportedCurrency": "USD", "totalRevenue": "100", "netIncome": "15", "operatingIncome": "25"}]})
    cli = httpx.Client(transport=httpx.MockTransport(respuesta))
    out = AlphaVantage(con, {"simbolos": ["MU", "AMD", "NVDA"], "pausa_s": 0}, "clave", cli).consultar(AHORA)
    assert {o["simbolo"] for o in out} == {"MU"} and vistos == ["MU", "AMD"]
