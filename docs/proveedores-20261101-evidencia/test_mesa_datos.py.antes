"""Paneles nativos de la Mesa: deduplicación de noticias, SIN DATO en macro, resumen trazable y reacción sin fuga."""
import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from terminal import app as modulo
from terminal import centro_investigacion, mesa_datos

AHORA = datetime(2026, 10, 30, 23, 0, tzinfo=UTC)


def _noticia(con, nid, iid, titulo, enlace, publicado):
    con.execute("INSERT INTO noticias (id, instrumento_id, titulo, enlace, publicado, fuente, impacto, sentimiento, motivo, obtenido_en) "
                "VALUES (?,?,?,?,?, 'seekingalpha_rss', 'normal', 0.9, '', '2026-10-30T21:00:00+00:00')",
                (nid, iid, titulo, enlace, publicado))


def test_noticias_deduplica_por_enlace_y_titulo_sin_sentimiento(con):
    _noticia(con, "1", "SIC:NVDA", "Chips caen", "https://x.test/a?utm=1", "2026-10-30T12:00:00+00:00")
    _noticia(con, "2", "SIC:AMD", "Chips caen", "https://x.test/a", "2026-10-30T12:00:00+00:00")
    _noticia(con, "3", "SIC:MU", "CHIPS  caen!", "https://x.test/b", "2026-10-30T11:00:00+00:00")
    _noticia(con, "4", "SIC:MU", "Otra cosa", "https://x.test/c", "2026-10-30T10:00:00+00:00")
    r = mesa_datos.noticias(con)
    assert [n["titulo"] for n in r["noticias"]] == ["Chips caen", "Otra cosa"]
    assert sorted(r["noticias"][0]["instrumentos"]) == ["SIC:AMD", "SIC:MU", "SIC:NVDA"]
    assert all("sentimiento" not in n for n in r["noticias"])
    assert r["noticias"][0]["publicado"] and r["noticias"][0]["ingesta"]
    assert [n["titulo"] for n in mesa_datos.noticias(con, "SIC:MU")["noticias"]] == ["CHIPS  caen!", "Otra cosa"]


def test_macro_declara_sin_dato_y_fechas_distintas(con, ajustes):
    centro_investigacion.inicializar(con)
    for serie, periodo, valor in [("DGS10", "2026-10-29", 4.98), ("DGS2", "2026-10-28", 4.61)]:
        con.execute("INSERT INTO investigacion_observaciones (fuente, simbolo, serie, titulo, periodo, valor, unidad, texto, url, origen, "
                    "hora_fuente, disponible_desde, confirmado_en, huella) VALUES ('fred_macro','',?,?,?,?,'%','','https://fred.stlouisfed.org/',"
                    "'api',NULL,'2026-10-30T05:00:00+00:00','2026-10-30T05:00:00+00:00',?)", (serie, serie, periodo, valor, serie + periodo))
    r = mesa_datos.macro(con, ajustes, AHORA)
    por = {s["serie"]: s for s in r["series"]}
    assert por["DGS10"]["valor"] == 4.98 and por["DGS10"]["periodo"] == "2026-10-29" and por["DGS10"]["frecuencia"]
    assert por["DGS30"]["estado"] == "SIN DATO" and "DGS30" in por["DGS30"]["requisito"]
    assert por["CETES28"]["estado"] == "SIN DATO"
    assert por["USDMXN"]["estado"] == "SIN DATO"          # base vacía: no se inventa tipo de cambio
    assert "fechas distintas" in r["curva"]["aviso"]       # 2 y 10 años de días distintos
    assert r["aviso"]


def test_macro_no_ve_observaciones_posteriores_al_corte(con, ajustes):
    centro_investigacion.inicializar(con)
    con.execute("INSERT INTO investigacion_observaciones (fuente, simbolo, serie, titulo, periodo, valor, unidad, texto, url, origen, "
                "hora_fuente, disponible_desde, confirmado_en, huella) VALUES ('fred_macro','','DGS10','DGS10','2026-10-31',5.0,'%','',"
                "'https://fred.stlouisfed.org/','api',NULL,'2026-10-31T05:00:00+00:00','2026-10-31T05:00:00+00:00','h')")
    por = {s["serie"]: s for s in mesa_datos.macro(con, ajustes, AHORA)["series"]}
    assert por["DGS10"]["estado"] == "SIN DATO"


def test_resumen_trazable_sin_cotizacion_actual(con, ajustes):
    con.execute("INSERT INTO ajustes_usuario (clave, valor, actualizado_en) VALUES ('cetes28', ?, '2026-10-30')",
                (json.dumps({"valor": 0.0622, "fecha": "2026-10-29", "fuente": "Banxico SIE SF43936", "aviso": None,
                             "consultado_en": "2026-10-30T05:00:00+00:00"}),))
    r = mesa_datos.resumen(con, ajustes, AHORA, cot={"SIC:A": {"estado": "vigente"}, "SIC:B": {"estado": "retrasado"}})
    assert r["datos"]["por_estado"] == {"vigente": 1, "retrasado": 1}
    cetes = next(c for c in r["cifras"] if c["serie"] == "CETES28")
    assert cetes["valor"] == pytest.approx(6.22) and cetes["periodo"] == "2026-10-29" and cetes["fuente"]
    assert r["corte"].startswith("2026-10-30T23:00") and r["ultima_sesion"]["NYSE"] == "2026-10-30"
    assert all({"periodo", "fuente"} <= set(c) for c in r["cifras"])


@pytest.mark.parametrize("momento,base,fin", [("antes", "2026-10-28", "2026-10-29"), ("despues", "2026-10-29", "2026-10-30")])
def test_reaccion_resultados_sin_fuga(momento, base, fin):
    cierres = [("2026-10-27", 100), ("2026-10-28", 101), ("2026-10-29", 110), ("2026-10-30", 99)]
    r = mesa_datos.reaccion_resultados(cierres, "2026-10-29", momento)
    assert (r["base"], r["fin"]) == (base, fin)
    assert r["reaccion"] == pytest.approx(dict(cierres)[fin] / dict(cierres)[base] - 1)


def test_reaccion_resultados_faltantes_y_validacion():
    assert mesa_datos.reaccion_resultados([("2026-10-29", 1)], "2026-10-29", "despues")["estado"] == "SIN DATO"
    assert mesa_datos.reaccion_resultados([("2026-10-30", 1)], "2026-10-29", "antes")["estado"] == "SIN DATO"
    with pytest.raises(ValueError):
        mesa_datos.reaccion_resultados([], "2026-10-29", "durante")


def test_rutas_mesa_solo_lectura():
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        assert c.get("/api/mesa/noticias").status_code == 200
        assert c.get("/api/mesa/noticias?simbolo=<script>").status_code == 422
        assert c.get("/api/mesa/macro").json()["series"][0]["serie"] == "USDMXN"
        assert "corte" in c.get("/api/mesa/resumen").json()
        assert c.get("/api/mesa/resultados").json()["estado"] == "bloqueado"
        assert c.post("/api/mesa/macro").status_code in (403, 405)  # sin rutas de escritura
