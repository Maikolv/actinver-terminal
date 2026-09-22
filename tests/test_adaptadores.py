"""Adaptadores con respuestas simuladas: parseo, límites persistentes, reintentos y ocultación de credenciales."""
import json
from datetime import date

import httpx
import pytest

from terminal.adaptadores import Banxico, Eodhd, ErrorProveedor, Fred, LimiteAlcanzado, Tiingo
from terminal.adaptadores.base import limpiar

SECRETO = "clave-super-secreta-123"


def cliente(respuestas):
    llamadas = []

    def manejar(req: httpx.Request):
        llamadas.append(req)
        r = respuestas[min(len(llamadas) - 1, len(respuestas) - 1)]
        return httpx.Response(r[0], content=r[1].encode() if isinstance(r[1], str) else json.dumps(r[1]).encode())

    return httpx.Client(transport=httpx.MockTransport(manejar)), llamadas


def test_fred_csv_ignora_festivos(con):
    c, _ = cliente([(200, "observation_date,DEXMXUS\n2026-09-17,17.1829\n2026-09-18,.\n")])
    b = Fred(con, {"peticiones_por_dia": 5}, cliente=c).historico({"id": "FX:USDMXN"}, date(2026, 9, 1), date(2026, 9, 18))
    assert [(x.fecha, x.cierre) for x in b] == [("2026-09-17", 17.1829)]


def test_tiingo_usa_cabecera_y_devuelve_eventos(con):
    c, llamadas = cliente([(200, [{"date": "2026-09-18T00:00:00Z", "close": 100.0, "adjClose": 99.0, "volume": 10,
                                   "divCash": 0.5, "splitFactor": 1.0}])])
    b = Tiingo(con, {"peticiones_por_dia": 5}, SECRETO, cliente=c).historico(
        {"listado_referencia": "BRK.B", "moneda_referencia": "USD"}, date(2026, 9, 1), date(2026, 9, 18))
    assert b[0].dividendo == 0.5 and b[0].cierre_ajustado == 99.0
    assert "brk-b" in str(llamadas[0].url) and SECRETO not in str(llamadas[0].url)
    assert llamadas[0].headers["authorization"] == f"Token {SECRETO}"


def test_banxico_formato_fecha(con):
    c, _ = cliente([(200, {"bmx": {"series": [{"datos": [{"fecha": "18/09/2026", "dato": "17.2454"}, {"fecha": "19/09/2026", "dato": "N/E"}]}]}})])
    b = Banxico(con, {}, SECRETO, cliente=c).historico({"id": "FX:USDMXN"}, date(2026, 9, 1), date(2026, 9, 19))
    assert [(x.fecha, x.cierre) for x in b] == [("2026-09-18", 17.2454)]


def test_sin_credencial_no_consulta(con):
    a = Tiingo(con, {}, None)
    assert not a.configurado()
    with pytest.raises(ErrorProveedor):
        a.historico({"listado_referencia": "AAPL"}, date(2026, 1, 1), date(2026, 1, 2))


def test_limite_diario_persistente(con):
    c, llamadas = cliente([(200, [])])
    a = Eodhd(con, {"peticiones_por_dia": 2}, SECRETO, cliente=c)
    ins = {"clave": "WALMEX", "serie": "*", "mercado_operable": "BMV", "clase": "accion"}
    a.historico(ins, date(2026, 1, 1), date(2026, 1, 2))
    a.historico(ins, date(2026, 1, 1), date(2026, 1, 2))
    with pytest.raises(LimiteAlcanzado):
        Eodhd(con, {"peticiones_por_dia": 2}, SECRETO, cliente=c).historico(ins, date(2026, 1, 1), date(2026, 1, 2))
    assert len(llamadas) == 2 and a.peticiones_restantes() == 0


def test_reintenta_429_y_oculta_credencial(con, monkeypatch):
    monkeypatch.setattr("terminal.adaptadores.base.time.sleep", lambda s: None)
    c, llamadas = cliente([(429, "lento"), (429, "lento"), (503, "caido")])
    a = Eodhd(con, {"peticiones_por_dia": 10}, SECRETO, cliente=c)
    with pytest.raises(ErrorProveedor) as e:
        a.historico({"clave": "WALMEX", "serie": "*"}, date(2026, 1, 1), date(2026, 1, 2))
    assert len(llamadas) == 3 and SECRETO not in str(e.value)
    assert limpiar(f"https://x/?api_token={SECRETO}&fmt=json") == "https://x/?api_token=***&fmt=json"
