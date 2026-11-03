"""Espera del proveedor con HTTP simulado, reloj fijo y cuota persistente."""
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from terminal.adaptadores.base import Adaptador, ErrorProveedor, LimiteAlcanzado


@pytest.mark.parametrize("codigo", [429, 503])
@pytest.mark.parametrize("cabecera", ["120", "Mon, 02 Nov 2026 20:02:00 GMT"])
@pytest.mark.parametrize("intentos", [1, 3])
def test_pausa_persiste_entre_instancias_sin_consumir_cupo(con, monkeypatch, codigo, cabecera, intentos):
    hora = [datetime(2026, 11, 2, 20, tzinfo=UTC)]

    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return hora[0]

    monkeypatch.setattr("terminal.adaptadores.base.datetime", Reloj)
    vistos = []

    def responder(peticion):
        vistos.append(peticion)
        return httpx.Response(codigo, headers={"Retry-After": cabecera}) if len(vistos) == 1 else httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        ajustes = {"peticiones_por_dia": 4}
        primero = Adaptador(con, ajustes, cliente=cliente)
        with pytest.raises(ErrorProveedor, match="Retry-After"):
            primero._get("https://ejemplo.invalid/datos", intentos=intentos)
        segundo = Adaptador(con, ajustes, cliente=cliente)
        hora[0] += timedelta(seconds=60)
        with pytest.raises(LimiteAlcanzado, match="Retry-After"):
            segundo._get("https://ejemplo.invalid/otro-instrumento")
        assert len(vistos) == 1
        assert segundo.peticiones_restantes() == 3
        hora[0] += timedelta(seconds=61)
        assert segundo._get("https://ejemplo.invalid/datos").status_code == 200
        assert len(vistos) == 2 and segundo.peticiones_restantes() == 2


@pytest.mark.parametrize("cabecera", ["inválida", "NaN", "Infinity", "-10"])
def test_cabecera_invalida_deja_pausa_conservadora_sin_dormir(con, monkeypatch, cabecera):
    vistos = []
    monkeypatch.setattr("terminal.adaptadores.base.time.sleep", lambda _: pytest.fail("No debe dormir ni reintentar"))

    def responder(peticion):
        vistos.append(peticion)
        return httpx.Response(429, headers={"Retry-After": cabecera.encode("utf-8")})

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        adaptador = Adaptador(con, {}, cliente=cliente)
        with pytest.raises(ErrorProveedor, match="Retry-After"):
            adaptador._get("https://ejemplo.invalid/datos", intentos=1)
        with pytest.raises(LimiteAlcanzado):
            adaptador._get("https://ejemplo.invalid/datos")
    assert len(vistos) == 1


def test_eodhd_diferido_comparte_pausa_con_cierres(con, monkeypatch):
    from terminal import config, cotizaciones
    from terminal.adaptadores.base import ErrorProveedor
    from terminal.adaptadores.proveedores import Eodhd

    ajustes = {"peticiones_por_dia": 20}
    monkeypatch.setattr(config, "cargar_ajustes", lambda: {"proveedores": {"eodhd": ajustes}})
    peticiones = []

    def responder(request):
        peticiones.append(request)
        return httpx.Response(429, headers={"Retry-After": "60"})

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        diferido = cotizaciones.EodhdDiferidoProvider(con, {"EODHD_API_KEY": "ficticia"}, cliente=cliente)
        cierres = Eodhd(con, ajustes, "ficticia", cliente=cliente)
        with pytest.raises(cotizaciones.ProveedorNoDisponible, match="Retry-After"):
            diferido._pedir("GET", "https://example.test/diferido", {}, {})
        with pytest.raises(ErrorProveedor, match="Retry-After"):
            cierres._get("https://example.test/cierres")
    assert len(peticiones) == 1


def test_eodhd_diferido_comparte_cupo_con_cierres(con, monkeypatch):
    from terminal import config, cotizaciones
    from terminal.adaptadores.base import LimiteAlcanzado
    from terminal.adaptadores.proveedores import Eodhd

    ajustes = {"peticiones_por_dia": 1}
    monkeypatch.setattr(config, "cargar_ajustes", lambda: {"proveedores": {"eodhd": ajustes}})
    peticiones = []

    def responder(request):
        peticiones.append(request)
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        diferido = cotizaciones.EodhdDiferidoProvider(con, {"EODHD_API_KEY": "ficticia"}, cliente=cliente)
        cierres = Eodhd(con, ajustes, "ficticia", cliente=cliente)
        diferido._pedir("GET", "https://example.test/diferido", {}, {})
        with pytest.raises(LimiteAlcanzado):
            cierres._get("https://example.test/cierres")
    assert len(peticiones) == 1


@pytest.mark.parametrize("codigo", [429, 503])
def test_bls_post_respeta_retry_after(con, codigo):
    from terminal.centro_conectores import BLS

    vistos = []

    def responder(peticion):
        vistos.append(peticion.method)
        return httpx.Response(codigo, headers={"Retry-After": "120"})

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        bls = BLS(con, {"peticiones_por_dia": 4}, cliente=cliente)
        ahora = datetime.now(UTC)
        with pytest.raises(ErrorProveedor, match=f"HTTP {codigo}"):
            bls.consultar(ahora)
        with pytest.raises(LimiteAlcanzado, match="Retry-After"):
            bls.consultar(ahora)
    assert vistos == ["POST"]
