"""Fuentes de contexto con respuestas simuladas (sin red)."""
import json

import httpx
import pytest

from terminal import fuentes_web as fw
from terminal.adaptadores import SinCredencial

RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Apple beats estimates, raises guidance</title><link>https://seekingalpha.com/news/1</link>
<pubDate>Tue, 22 Sep 2026 14:00:00 -0400</pubDate></item>
<item><title>Script <b>no</b></title><link>javascript:alert(1)</link></item>
</channel></rss>"""
FF = [{"title": "Federal Funds Rate", "country": "USD", "date": "2026-10-28T14:00:00-04:00", "impact": "High",
       "forecast": "3.75%", "previous": "4.00%"}]
F4 = b"""<ownershipDocument><reportingOwner><reportingOwnerId><rptOwnerName>Doe Jane</rptOwnerName></reportingOwnerId>
<reportingOwnerRelationship><isDirector>0</isDirector><officerTitle>CFO</officerTitle></reportingOwnerRelationship></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction><transactionDate><value>2026-09-18</value></transactionDate>
<transactionCoding><transactionCode>P</transactionCode></transactionCoding><transactionAmounts>
<transactionShares><value>5000</value></transactionShares><transactionPricePerShare><value>100</value></transactionPricePerShare>
</transactionAmounts></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""


def cliente(cuerpos):
    def h(req):
        for clave, cuerpo in cuerpos.items():
            if clave in str(req.url):
                return httpx.Response(200, content=cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode())
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(h))


def test_rss_solo_enlaces_https(con):
    t = fw.SeekingAlphaRSS(con, {}, cliente=cliente({"AAPL.xml": RSS})).titulares("AAPL")
    assert len(t) == 1 and t[0]["publicado"].startswith("2026-09-22T18:00")


def test_clasificacion_de_titulares():
    assert fw.clasificar_titular("Apple beats estimates, raises guidance")["sentimiento"] > 0
    c = fw.clasificar_titular("Boeing downgraded amid SEC investigation")
    assert c["impacto"] == "alto" and c["sentimiento"] < 0


def test_macro_y_limite_por_hora(con):
    ad = {"forexfactory": {"peticiones_por_hora": 2}}
    r = fw.actualizar_macro(con, ad, cliente(cliente_ff := {"ff_calendar": FF}))
    assert r == {"estado": "ok", "registros": 1}
    assert fw.actualizar_macro(con, ad, cliente(cliente_ff))["estado"] == "al_dia"  # caché de 1 h
    fila = con.execute("SELECT * FROM eventos_macro").fetchone()
    assert fila["impacto"] == "High" and fila["pais"] == "USD"


def test_formulario4_parseo():
    ops = fw.SecEdgar._parsear_f4(F4, "https://www.sec.gov/x.xml", "2026-09-19")
    assert ops == [{"fecha": "2026-09-18", "nombre": "Doe Jane", "cargo": "CFO", "codigo": "P", "acciones": 5000.0,
                    "precio": 100.0, "valor": 500000.0, "enlace": "https://www.sec.gov/x.xml"}]


def test_sec_requiere_user_agent(con):
    with pytest.raises(SinCredencial):
        fw.SecEdgar(con, {}, None).formularios4("AAPL")
    assert fw.actualizar_insiders(con, {}, [])["estado"] == "requiere_configuracion"
