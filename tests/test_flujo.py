"""Velas, Order Flow y Option Flow: contratos, cálculos, importación CSV, adaptadores simulados y API.
Nada se inventa: sin fuente, las respuestas vienen vacías con su motivo."""
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from terminal.flujo import almacen, calculos, importar_csv, servicio
from terminal.flujo.adaptadores import Alpaca, Cripto
from terminal.flujo.contratos import Barra, Libro, Nivel, instante
from terminal.seguridad import TOKEN_CSRF

AHORA = datetime.now(UTC)
H = (AHORA - timedelta(hours=2)).replace(microsecond=0)


def test_instante_exige_zona_y_rechaza_futuro():
    assert instante("2026-10-12T14:30:00-06:00") == "2026-10-12T20:30:00+00:00"
    with pytest.raises(ValueError, match="zona"):
        instante("2026-10-12T14:30:00")
    with pytest.raises(ValueError, match="futuro"):
        instante((AHORA + timedelta(days=1)).isoformat())


def test_ohlc_inconsistente_y_libro_cruzado_se_rechazan():
    with pytest.raises(ValueError, match="OHLC"):
        Barra("X", "1Day", H.isoformat(), 10, 9, 8, 9.5, 100).validar()
    with pytest.raises(ValueError, match="cruzado"):
        Libro("X", H.isoformat(), [Nivel("bid", 1, 101, 1), Nivel("ask", 1, 100, 1)]).validar()


def test_rsi_wilder_coincide_con_el_ejemplo_clasico():
    cierres = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
               46.00, 46.03, 46.41, 46.22, 45.64]
    r = calculos.rsi_wilder(cierres, 14)
    assert r[13] is None
    # Referencia independiente: promedio simple de 14 cambios y después suavizado de Wilder (alfa = 1/14).
    cambios = [b - a for a, b in zip(cierres, cierres[1:])]
    sub, baj = sum(max(c, 0) for c in cambios[:14]) / 14, sum(max(-c, 0) for c in cambios[:14]) / 14
    esperado = [100 - 100 / (1 + sub / baj)]
    for c in cambios[14:]:
        sub, baj = (sub * 13 + max(c, 0)) / 14, (baj * 13 + max(-c, 0)) / 14
        esperado.append(100 - 100 / (1 + sub / baj))
    assert r[14:] == pytest.approx(esperado)
    assert round(r[14], 2) == 70.46            # valor publicado en el ejemplo de Wilder de StockCharts


def test_sma_bollinger_y_vwap():
    v = [float(i) for i in range(1, 25)]
    assert calculos.sma(v, 20)[18] is None and calculos.sma(v, 20)[19] == pytest.approx(10.5)
    inf, sup = calculos.bollinger(v, 20)[19]
    assert inf < 10.5 < sup and sup - 10.5 == pytest.approx(10.5 - inf)
    barras = [{"maximo": 11, "minimo": 9, "cierre": 10, "volumen": 100}, {"maximo": 21, "minimo": 19, "cierre": 20, "volumen": 300},
              {"maximo": 5, "minimo": 5, "cierre": 5, "volumen": None}]
    assert calculos.vwap_anclado(barras) == [pytest.approx(10), pytest.approx(17.5), None]


def test_libro_y_operaciones_delta_solo_con_lado():
    libro = {"niveles": [{"lado": "bid", "nivel": 1, "precio": 99, "tamano": 3}, {"lado": "bid", "nivel": 2, "precio": 98, "tamano": 1},
                         {"lado": "ask", "nivel": 1, "precio": 101, "tamano": 1}]}
    r = calculos.resumen_libro(libro)
    assert r["diferencial"] == 2 and r["desequilibrio"] == pytest.approx(0.6) and r["profundidad"][1]["acumulado"] == 4
    ops = [{"instante": "a", "precio": 10, "tamano": 5, "lado": "compra"}, {"instante": "b", "precio": 11, "tamano": 2, "lado": "venta"}]
    assert calculos.resumen_operaciones(ops)["delta"] == 3
    sin_lado = [{**o, "lado": None} for o in ops]
    res = calculos.resumen_operaciones(sin_lado)
    assert res["delta"] is None and res["delta_acumulado"] == [] and res["volumen"] == 7   # nunca se infiere el lado


def test_volumen_inusual_es_regla_configurable():
    cad = [{"contrato": str(i), "volumen": v, "interes_abierto": None} for i, v in enumerate([10, 20, 30, 40, 5000])]
    marcados = calculos.volumen_inusual(cad, minimo=100, percentil=0.8)
    assert [c["contrato"] for c in marcados] == ["4"] and "percentil" in marcados[0]["motivo"]
    con_oi = [{"contrato": "a", "volumen": 500, "interes_abierto": 200}, {"contrato": "b", "volumen": 500, "interes_abierto": 2000}]
    assert [c["contrato"] for c in calculos.volumen_inusual(con_oi, ratio_oi=1.0)] == ["a"]


def _csv(tipo, filas):
    return (",".join(importar_csv.COLUMNAS[tipo]) + "\n" + "\n".join(filas) + "\n").encode()


def test_importar_velas_libro_y_opciones_todo_o_nada(con, ajustes):
    t = H.isoformat()
    r = importar_csv.importar(con, "velas", _csv("velas", [f"BMV:GMEXICO,BMV,1Day,{t},240,245,238,242,1000,mi_export,Licencia personal"]))
    assert r["guardados"] == 1
    v = servicio.velas(con, ajustes, "BMV:GMEXICO", "1Day", 30)
    assert v["barras"][0]["calidad"] == "importado" and v["procedencia"][0]["licencia"] == "Licencia personal"
    malo = _csv("velas", [f"BMV:AC,BMV,1Day,{t},10,11,9,10,1,x,y", f"BMV:AC,BMV,1Day,{t},10,9,8,10,1,x,y"])
    with pytest.raises(ValueError, match="fila 3: OHLC"):
        importar_csv.importar(con, "velas", malo)
    assert not almacen.barras(con, "BMV:AC", "1Day")                         # nada se guardó
    libro = _csv("libro", [f"BTCMXN,cripto,{t},bid,1,100,2,x,y", f"BTCMXN,cripto,{t},ask,1,99,1,x,y"])
    with pytest.raises(ValueError, match="cruzado"):
        importar_csv.importar(con, "libro", libro)
    with pytest.raises(ValueError, match="encabezados"):
        importar_csv.importar(con, "opciones", b"contrato,otra\n1,2\n")
    op = _csv("opciones", [f"MU261120C01000000,SIC:MU,OPRA,2026-11-20,1000,call,{t},10,11,10.5,50,,0.45,0.5,,,,x,y"])
    assert importar_csv.importar(con, "opciones", op)["guardados"] == 1
    assert servicio.optionflow(con, ajustes, "SIC:MU")["contratos"][0]["origen_iv"] == "importado"


def test_sin_datos_no_se_simula_nada(con, ajustes):
    v = servicio.velas(con, ajustes, "SIC:MU", "1Day", 30)
    assert v["barras"] == [] and "Sin fuente autorizada" in v["vacio"]
    o = servicio.orderflow(con, ajustes, "BITSO:BTC/MXN")
    assert o["libro"] is None and o["operaciones"] == [] and o["vacio_libro"]
    assert servicio.optionflow(con, ajustes, "SIC:MU")["contratos"] == []


def test_sin_fuga_temporal_por_disponible_desde(con):
    from terminal.flujo.contratos import Procedencia
    almacen.guardar_barras(con, [Barra("SIC:MU", "1Day", H.isoformat(), 1, 2, 0.5, 1.5, 10)], Procedencia("x", "y", "z"))
    con.commit()
    assert almacen.barras(con, "SIC:MU", "1Day")
    assert almacen.barras(con, "SIC:MU", "1Day", hasta=(AHORA - timedelta(days=1)).isoformat()) == []


def test_alpaca_barras_y_opciones_con_respuesta_simulada(con, ajustes):
    vistos = []

    def responder(r):
        vistos.append(r)
        assert r.url.host == "data.alpaca.markets"                     # nunca la API de operaciones
        if "/v2/stocks/bars" in r.url.path:
            assert r.url.params["feed"] == "sip"
            return httpx.Response(200, json={"bars": {"MU": [{"t": H.isoformat().replace("+00:00", "Z"), "o": 10, "h": 12, "l": 9,
                                                                 "c": 11, "v": 1000, "vw": 10.5}]}})
        return httpx.Response(200, json={"snapshots": {
            "MU261120C00010000": {"latestQuote": {"bp": 1.0, "ap": 1.2, "t": H.isoformat()}, "dailyBar": {"v": 300},
                                  "impliedVolatility": 0.4, "greeks": {"delta": 0.5}},
            "MU261120P00010000": {"latestQuote": {"bp": 0.9, "ap": 1.1, "t": H.isoformat()}}}})
    env = {"ALPACA_API_KEY_ID": "id", "ALPACA_API_SECRET_KEY": "secreto"}
    a = Alpaca(ajustes, env, httpx.Client(transport=httpx.MockTransport(responder)))
    barras, p = a.barras("MU", "SIC:MU", "1Day", 30)
    assert barras[0].vwap == 10.5 and p.feed == "sip" and p.retraso_s >= 900
    contratos, p = a.cadena("MU", 10.0, 4.0)
    por = {c.tipo: c for c in contratos}
    assert por["call"].origen_iv == "proveedor" and por["call"].strike == 10.0 and por["call"].vencimiento == "2026-11-20"
    assert por["put"].origen_iv == "calculado" and por["put"].iv > 0               # IV propia, rotulada
    assert all("secreto" not in str(r.url) for r in vistos)                         # la clave va en cabecera


def test_alpaca_sin_claves_dice_que_falta(con, ajustes):
    r = servicio.actualizar(con, ajustes, "velas", "SIC:MU", "1Day", 30, env={})
    assert r["estado"] == "sin_fuente" and "ALPACA_API_KEY_ID" in r["mensaje"]


class ExchangeFalso:
    def fetch_order_book(self, par, limit=50):
        return {"timestamp": int((datetime.now(UTC) - timedelta(seconds=3)).timestamp() * 1000), "bids": [[100, 1], [99, 2]], "asks": [[101, 1.5]]}

    def fetch_trades(self, par, limit=200):
        ts = int((datetime.now(UTC) - timedelta(seconds=30)).timestamp() * 1000)
        return [{"timestamp": ts, "price": 100.5, "amount": 0.2, "side": "buy", "id": "1"},
                {"timestamp": ts, "price": 100.4, "amount": 0.1, "side": "sell", "id": "2"}]


def test_cripto_libro_y_operaciones_con_lado(con, ajustes):
    assert servicio.actualizar(con, ajustes, "libro", "BITSO:BTC/MXN", exchange=ExchangeFalso())["estado"] == "ok"
    assert servicio.actualizar(con, ajustes, "operaciones", "BITSO:BTC/MXN", exchange=ExchangeFalso())["estado"] == "ok"
    o = servicio.orderflow(con, ajustes, "BITSO:BTC/MXN")
    assert o["libro"]["mejor_bid"] == 100 and 0 < o["libro_meta"]["retraso_s"] < 60
    assert o["resumen"]["delta"] == pytest.approx(0.1) and o["libro_meta"]["calidad"] == "proveedor"
    assert servicio.actualizar(con, ajustes, "libro", "BITSO:BTC/MXN", exchange=ExchangeFalso())["estado"] == "en_espera"
    apagado = Cripto(type("A", (), {"get": lambda self, k, d=None: {"cripto": {"activo": False}} if k == "flujo" else d})())
    with pytest.raises(Exception, match="desactivado"):
        apagado.libro("BTC/MXN")


def test_api_flujo_protegida_y_plantillas():
    with TestClient(TestClient.__init__.__globals__.get("app") or __import__("terminal.app", fromlist=["app"]).app,
                    base_url="http://127.0.0.1:8765") as c:
        e = c.get("/api/flujo/estado").json()
        assert {p["id"] for p in e["proveedores"]} >= {"alpaca", "csv"} and e["no_disponible"]
        assert c.get("/api/flujo/plantilla/libro").text.startswith("simbolo,mercado,instante,lado,nivel")
        assert c.get("/api/flujo/plantilla/otro").status_code == 404
        assert c.post("/api/flujo/actualizar", json={"tipo": "velas", "simbolo": "SIC:MU"}).status_code == 403   # sin CSRF
        r = c.post("/api/flujo/importar/velas", files={"archivo": ("x.csv", b"malo\n")}, headers={"X-CSRF-Token": TOKEN_CSRF})
        assert r.status_code == 422
        assert c.get("/api/flujo/velas", params={"simbolo": "SIC:MU", "intervalo": "2Min"}).status_code == 422
        assert c.get("/api/visualizaciones/mercado", params={"ventana": 5}).json()["ventana"] == 5
        assert c.get("/api/visualizaciones/mercado", params={"ventana": 3}).status_code == 422


def test_cadena_une_spot_de_la_misma_referencia_y_el_gex_se_calcula(ajustes):
    """Opción (a) del 28-oct: spot = última operación de la acción en Alpaca a ≤ 60 s de la cotización más reciente."""
    from dataclasses import asdict

    from terminal.flujo import gex
    ref = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=20)
    vistos = []

    def responder(r):
        vistos.append(r)
        if r.url.path == "/v2/stocks/NVDA/trades":
            assert r.url.params["feed"] == "sip" and r.url.params["end"] == ref.isoformat()   # nada posterior a R
            return httpx.Response(200, json={"trades": [{"t": (ref - timedelta(seconds=8)).isoformat(), "p": 190.5}]})
        q = lambda t: {"latestQuote": {"bp": 5.0, "ap": 5.2, "t": t.isoformat()},  # noqa: E731
                       "impliedVolatility": 0.45, "greeks": {"gamma": 0.012}}
        return httpx.Response(200, json={"snapshots": {
            "NVDA261120C00190000": q(ref), "NVDA261120P00190000": q(ref - timedelta(seconds=40)),
            "NVDA261120C00250000": q(ref - timedelta(minutes=5))}})       # cotización vieja: no comparte referencia
    a = Alpaca(ajustes, {"ALPACA_API_KEY_ID": "id", "ALPACA_API_SECRET_KEY": "s"}, httpx.Client(transport=httpx.MockTransport(responder)))
    contratos, p = a.cadena("NVDA", 190.0, 4.0)
    spots = {c.contrato: (c.spot, c.moneda) for c in contratos}
    assert spots["NVDA261120C00190000"] == spots["NVDA261120P00190000"] == (190.5, "USD")
    assert spots["NVDA261120C00250000"] == (None, None) and "unido a 2 de 3" in p.nota
    filas = [{**asdict(c), "interes_abierto": 1000, "multiplicador": 100} for c in contratos]   # OI fechado de Paper
    r = gex.calcular(filas)
    assert r["disponible"] and r["contratos_usados"] == 2 and r["spot"] == 190.5
    assert r["descartados"] == {"sin spot de la misma referencia": 1}
    assert r["totales"]["calls"] == pytest.approx(0.012 * 1000 * 100 * 190.5 ** 2 * 0.01)


def test_cadena_sin_operacion_cercana_no_inventa_spot(ajustes):
    ref = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=20)

    def responder(r):
        if r.url.path.endswith("/trades"):
            return httpx.Response(200, json={"trades": []})
        return httpx.Response(200, json={"snapshots": {"NVDA261120C00190000": {"latestQuote": {"bp": 5.0, "ap": 5.2, "t": ref.isoformat()}}}})
    a = Alpaca(ajustes, {"ALPACA_API_KEY_ID": "id", "ALPACA_API_SECRET_KEY": "s"}, httpx.Client(transport=httpx.MockTransport(responder)))
    contratos, p = a.cadena("NVDA", 190.0, 4.0)
    assert contratos[0].spot is None and "sin spot" in p.nota.lower()


def test_gex_programado_apagado_y_una_vez_por_paso(con, ajustes, monkeypatch):
    llamadas = []
    monkeypatch.setattr(servicio, "actualizar", lambda con, aj, tipo, s: llamadas.append((tipo, s)) or {"estado": "ok"})
    a_las = lambda h, m: datetime(2026, 10, 28, h, m, tzinfo=servicio.NY)  # noqa: E731 - miércoles
    assert servicio.gex_programado(con, ajustes, ["SIC:NVDA"], a_las(10, 5)) == []          # apagado por omisión
    ajustes.datos.setdefault("flujo", {})["gex_programado"] = {"activo": True}
    assert [r["paso"] for r in servicio.gex_programado(con, ajustes, ["SIC:NVDA"], a_las(8, 30))] == ["oi"]
    assert servicio.gex_programado(con, ajustes, ["SIC:NVDA"], a_las(8, 45)) == []          # ya hecho hoy
    assert [r["paso"] for r in servicio.gex_programado(con, ajustes, ["SIC:NVDA"], a_las(10, 1))] == ["cadena_10"]
    assert servicio.gex_programado(con, ajustes, ["SIC:NVDA"], a_las(12, 0)) == []          # entre pasos: nada
    assert [r["paso"] for r in servicio.gex_programado(con, ajustes, ["SIC:NVDA"], a_las(14, 10))] == ["cadena_14"]
    assert llamadas == [("contratos_oi", "SIC:NVDA"), ("opciones", "SIC:NVDA"), ("opciones", "SIC:NVDA")]
