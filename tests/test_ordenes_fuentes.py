"""Plan de órdenes ejecutable, conectores contratados nuevos (Infosel, Edimex) y calificaciones de Seeking Alpha."""
import pandas as pd
import pytest

from terminal import cotizaciones as cz, importar, mercado, optimizador, ranking, servicios

from conftest import sembrar_precios


def test_consolidar_ordenes_elimina_posiciones_menores_a_la_banda():
    w = pd.Series({"A": 0.30, "B": 0.25, "C": 0.20, "D": 0.12, "E": 0.105, "F": 0.015, "G": 0.01})
    c, info = optimizador.consolidar_ordenes(w, 0.02, 0.50, 5)
    assert c["G"] == 0 and c["F"] == 0 and abs(c.sum() - 1) < 1e-9
    assert (c[c > 0] >= 0.02).all() and info["posiciones"] == 5 and len(info["eliminadas"]) == 2
    # respeta el mínimo de emisoras y los topes: si el peso no cabe, se conserva
    c2, info2 = optimizador.consolidar_ordenes(pd.Series({"A": .12, "B": .12, "C": .12, "D": .12, "E": .12, "F": .12,
                                                         "G": .12, "H": .12, "I": .04}), 0.05, 0.12, 5)
    assert c2["I"] > 0 and info2["eliminadas"] == []


def test_propuesta_informa_el_numero_de_ordenes(con, ajustes):
    ids = [r[0] for r in con.execute("SELECT id FROM instrumentos WHERE id LIKE 'BMV:%' AND estado='activo' "
                                     "AND clase='accion' ORDER BY id LIMIT 12")]
    sembrar_precios(con, ids, sesiones=300)
    perfil = servicios.perfil_actual(con, ajustes)
    p = optimizador.proponer(con, ajustes, perfil, "acciones", servicios.cartera_actual(con, ajustes))
    o = p["ordenes"]
    assert o["total"] == o["compras"] + o["ventas"] == len(p["pesos"]) == o["posiciones"]
    assert min(a["peso"] for a in p["pesos"]) >= float(ajustes["optimizacion"]["banda_rebalanceo_pp"]) / 100 - 1e-4


def test_infosel_y_edimex_quedan_pendientes_sin_contrato(con):
    ps = cz.construir(con, False, entorno={})
    for n in ("infosel", "edimex"):
        assert not ps[n].configurado() and any("Contrato" in x for x in ps[n].pendientes())
    assert cz.PRIORIDAD.index("infosel") < cz.PRIORIDAD.index("eodhd_bmv")


def test_calificaciones_sa_se_importan_y_aparecen_en_el_ranking(con, ajustes):
    ids = [r[0] for r in con.execute("SELECT id FROM instrumentos WHERE id LIKE 'SIC:%' AND estado='activo' "
                                     "AND clase='accion' ORDER BY id LIMIT 12")]
    sembrar_precios(con, ids, sesiones=120)
    txt = ("fecha,instrumento_id,quant,autores,wall_street,valuacion,crecimiento,rentabilidad,momentum,revisiones\n"
           f"2026-09-20,{ids[0]},4.5,3.2,4.1,C,B+,A,A-,B\n2026-09-20,{ids[1]},7,,,,,,,\n")
    ins = mercado.instrumentos(con)
    r = importar.importar(con, txt.encode(), "sa.csv", "calificaciones_sa", ins, confirmar=False)
    assert r["aceptables"] == 1 and r["rechazadas"] == 1                       # escala 1–5
    ok = ("fecha,instrumento_id,quant,autores,wall_street,valuacion,crecimiento,rentabilidad,momentum,revisiones\n"
          f"2026-09-20,{ids[0]},4.5,3.2,4.1,C,B+,A,A-,B\n")
    assert importar.importar(con, ok.encode(), "sa.csv", "calificaciones_sa", ins, confirmar=True)["aceptadas"] == 1
    fila = next(f for f in ranking.calcular(con, ajustes)["filas"] if f["id"] == ids[0])
    assert fila["calificacion_sa"]["quant"] == 4.5


def _infosel(con, responder, env=None):
    import httpx
    env = env or {"INFOSEL_API_KEY": "token-de-prueba", "INFOSEL_URL_BASE": "https://infosel.test"}
    return cz.InfoselProvider(con, env, cliente=httpx.Client(transport=httpx.MockTransport(responder)))


def test_infosel_consulta_el_ultimo_hecho_bmv_y_sic(con):
    llamadas = []

    def responder(req):
        llamadas.append(req)
        clave = req.url.params["instrumentKey"]
        emisora, serie = ("AMX", "B") if "AMX" in clave else ("AAPL", "*")
        return __import__("httpx").Response(200, json={"data": [{
            "uniqueKey": clave, "emisora": emisora, "serie": serie, "precioActual": 17.25,
            "fechaPrecioActual": "29-09-2026", "hora": "10:15:30", "posturaPrecioCompra": 17.24, "posturaPrecioVenta": 17.26}]})

    p = _infosel(con, responder)
    q = p.cotizacion({"id": "BMV:AMX", "clave": "AMX", "serie": "B", "mercado_operable": "BMV"})
    r = llamadas[0]
    assert r.url.path == "/api/v3/instruments/last" and r.url.params["instrumentKey"] == "1/12576/0/AMXB"
    assert r.headers["Authorization"] == "Bearer token-de-prueba"
    assert q.precio == 17.25 and q.moneda == "MXN" and q.mercado == "local"
    assert q.hora_evento.startswith("2026-09-29T16:15:30")                    # 10:15:30 en CDMX = 16:15:30 UTC
    s = p.cotizacion({"id": "SIC:AAPL", "clave": "AAPL", "serie": "*", "mercado_operable": "BMV-SIC"})
    assert llamadas[1].url.params["instrumentKey"] == "1/12609/0/AAPL*" and s.mercado == "SIC"


def test_infosel_rechaza_serie_distinta_y_token_invalido(con):
    import httpx
    otra = _infosel(con, lambda r: httpx.Response(200, json={"data": [{"uniqueKey": "1/12576/0/AMXL", "emisora": "AMX",
                    "serie": "L", "precioActual": 1.0, "fechaPrecioActual": "29-09-2026", "hora": "10:00:00"}]}))
    with pytest.raises(cz.ProveedorNoDisponible):
        otra.cotizacion({"id": "BMV:AMX", "clave": "AMX", "serie": "B", "mercado_operable": "BMV"})
    malo = _infosel(con, lambda r: httpx.Response(401, json={"message": "Access token is missing or invalid"}))
    with pytest.raises(cz.ProveedorNoDisponible, match="token rechazado"):
        malo.cotizacion({"id": "BMV:AMX", "clave": "AMX", "serie": "B", "mercado_operable": "BMV"})
    assert cz.InfoselProvider(con, {}).pendientes()
