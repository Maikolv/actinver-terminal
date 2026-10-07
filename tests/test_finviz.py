"""Finviz Elite: apagado sin token, lote CSV, nunca «tiempo real» sin hora medida y el token no se filtra."""
from datetime import UTC, datetime

import httpx
import pytest

from terminal import finviz

CSV = '"No.","Ticker","Company","Price","Change","Volume"\n"1","AAPL","Apple Inc","254.04","-1.5%","100"\n' \
      '"2","BRK-B","Berkshire","496.74","0.1%","10"\n"3","XYZ","Sin precio","-","0%","0"\n'
ABIERTO = datetime(2026, 10, 7, 15, 0, tzinfo=UTC)  # miércoles 11:00 Nueva York


def test_apagado_sin_token(con, ajustes):
    assert finviz.pendientes({}) and not finviz.pendientes({"FINVIZ_AUTH_TOKEN": "t"})
    assert finviz.actualizar(con, ajustes, ABIERTO, env={})["estado"] == "sin_credencial"


def test_csv_y_simbolos():
    assert finviz.leer_csv(CSV) == {"AAPL": 254.04, "BRK-B": 496.74}
    assert finviz.simbolo("BRK.B") == "BRK-B"


def test_lote_guarda_como_retrasado_y_unknown(con, ajustes):
    vistas = []

    def responder(r):
        vistas.append(r.url)
        return httpx.Response(200, text=CSV)
    cli = httpx.Client(transport=httpx.MockTransport(responder))
    r = finviz.actualizar(con, ajustes, ABIERTO, env={"FINVIZ_AUTH_TOKEN": "secreto"}, cliente=cli)
    assert r["estado"] == "ok" and r["guardados"] >= 2 and "secreto" not in str(r)
    assert all(len(v.params["t"].split(",")) <= finviz.LOTE for v in vistas)
    f = con.execute("SELECT cierre, moneda, tipo_dato FROM precios WHERE instrumento_id='SIC:AAPL' AND proveedor='finviz_vivo'").fetchone()
    assert tuple(f) == (254.04, "USD", "retrasado")
    estados = {x[0] for x in con.execute("SELECT estado_latencia FROM cotizaciones_registro WHERE proveedor='finviz_vivo'")}
    assert estados == {"UNKNOWN"}
    # respeta el intervalo: una segunda llamada inmediata no consulta
    assert finviz.actualizar(con, ajustes, ABIERTO, env={"FINVIZ_AUTH_TOKEN": "secreto"}, cliente=cli)["estado"] == "en_espera"


def test_token_rechazado_no_expone_url():
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="no")))
    with pytest.raises(finviz.FinvizNoDisponible) as e:
        finviz.consultar(["AAPL"], "secreto", cli)
    assert "secreto" not in str(e.value) and "401" in str(e.value)


def test_mercado_cerrado_no_consulta(con, ajustes):
    sabado = datetime(2026, 10, 10, 16, 0, tzinfo=UTC)
    assert finviz.actualizar(con, ajustes, sabado, env={"FINVIZ_AUTH_TOKEN": "t"})["estado"] == "mercado_cerrado"
