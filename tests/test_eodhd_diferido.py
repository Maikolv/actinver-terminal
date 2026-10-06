"""Conector de precio diferido EODHD (candidato BMV): apagado por omisión, símbolo .MX, retraso medido con la hora del evento."""
import time

import httpx

from terminal import cotizaciones as cz

GMEXICO = {"id": "BMV:GMEXICO", "clave": "GMEXICO", "serie": "B", "mercado_operable": "BMV"}
ENV = {"EODHD_API_KEY": "clave-de-prueba", "EODHD_DIFERIDO_ESPECIFICACION": "config/proveedores/eodhd_diferido.json"}


def test_apagado_sin_especificacion_y_sin_clave():
    assert not cz.EodhdDiferidoProvider(None, {"EODHD_API_KEY": "x"}).configurado()    # falta activarlo
    p = cz.EodhdDiferidoProvider(None, {"EODHD_DIFERIDO_ESPECIFICACION": ENV["EODHD_DIFERIDO_ESPECIFICACION"]})
    assert any("EODHD_API_KEY" in x for x in p.pendientes())
    assert cz.EodhdDiferidoProvider(None, ENV).configurado()


def test_respuesta_simulada_queda_como_retrasada_con_su_hora_y_en_pesos():
    vistas = []
    hace_16_min = int(time.time()) - 16 * 60

    def responder(r):
        vistas.append(r.url)
        return httpx.Response(200, json={"code": "GMEXICOB.MX", "timestamp": hace_16_min, "gmtoffset": 0,
                                         "close": 233.10, "previousClose": 231.0})
    p = cz.EodhdDiferidoProvider(None, ENV, cliente=httpx.Client(transport=httpx.MockTransport(responder)))
    q = p._consultar(GMEXICO)
    assert vistas[0].path == "/api/real-time/GMEXICOB.MX" and vistas[0].params["api_token"] == "clave-de-prueba"
    assert q.precio == 233.10 and q.moneda == "MXN" and q.bolsa == "BMV"
    assert q.estado_latencia == "DELAYED"                      # ni «tiempo real» ni un cierre: lo dice la hora medida
    assert 15 * 60 <= q.latencia_medida_s <= 17 * 60


def test_sin_hora_del_evento_no_hay_cotizacion():
    import pytest
    p = cz.EodhdDiferidoProvider(None, ENV, cliente=httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"code": "GMEXICOB.MX", "close": 233.1}))))
    with pytest.raises(cz.ProveedorNoDisponible, match="hora"):
        p._consultar(GMEXICO)
