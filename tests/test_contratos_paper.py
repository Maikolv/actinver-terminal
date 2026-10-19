"""Contratos Paper: solo lectura, metadatos fechados y sin fuga temporal. HTTP siempre simulado."""
import sqlite3

import httpx
import pytest

from terminal.flujo import almacen, gex, servicio
from terminal.flujo.adaptadores import Alpaca, FuenteNoDisponible, URL_CONTRATOS_PAPER
from terminal.flujo.contratos import Procedencia

CFG = {"flujo": {"alpaca": {"contratos_oi": True}}}
ENV = {"ALPACA_PAPER_API_KEY_ID": "clave-prueba", "ALPACA_PAPER_API_SECRET_KEY": "secreto-prueba"}
CONTRATO = "SPY261218C00600000"


def cliente(respuesta, llamadas):
    def atender(req):
        llamadas.append(req)
        return respuesta(req) if callable(respuesta) else httpx.Response(200, json=respuesta)
    return httpx.Client(transport=httpx.MockTransport(atender), follow_redirects=True)


def test_solo_paper_get_y_normalizacion_sin_inventar():
    llamadas = []
    with cliente({"option_contracts": [
            {"symbol": CONTRATO, "underlying_symbol": "SPY", "open_interest": "0", "open_interest_date": "2026-10-15", "size": "100"},
            {"symbol": "SPY261218P00600000", "underlying_symbol": "SPY"}]}, llamadas) as cli:
        filas, proc = Alpaca(CFG, ENV, cli).contratos_opciones("SPY", 2, 1)
    assert len(llamadas) == 1
    assert llamadas[0].method == "GET"
    assert str(llamadas[0].url).split("?")[0] == URL_CONTRATOS_PAPER
    assert filas[0]["interes_abierto"] == 0
    assert filas[0]["fecha_oi"] == "2026-10-15"
    assert filas[0]["multiplicador"] == 100
    assert filas[1]["interes_abierto"] is filas[1]["multiplicador"] is filas[1]["fecha_oi"] is None
    assert proc.feed == "contracts-paper"


def test_apagado_no_red_y_solo_rangos_acotados():
    llamadas = []
    with cliente({}, llamadas) as cli:
        with pytest.raises(FuenteNoDisponible, match="desactivada"):
            Alpaca({}, ENV, cli).contratos_opciones("SPY")
        for args in [("SPY/../accounts", 1, 1), ("SPY", 1001, 1), ("SPY", 1, 4)]:
            with pytest.raises(ValueError):
                Alpaca(CFG, ENV, cli).contratos_opciones(*args)
    assert llamadas == []


@pytest.mark.parametrize("codigo", [301, 302, 401, 403, 429, 500])
def test_sin_redireccion_ni_secretos_en_error(codigo):
    llamadas = []
    with cliente(lambda req: httpx.Response(codigo, headers={"location": "https://example.com"}, text="secreto-prueba"), llamadas) as cli:
        with pytest.raises(FuenteNoDisponible) as error:
            Alpaca(CFG, ENV, cli).contratos_opciones("SPY")
    assert len(llamadas) == 1
    assert "secreto-prueba" not in str(error.value)


def test_paginacion_acotada_y_respuesta_invalida_sanitizada():
    llamadas = []
    with cliente({"option_contracts": [], "next_page_token": "repetido"}, llamadas) as cli:
        filas, proc = Alpaca(CFG, ENV, cli).contratos_opciones("SPY", 1, 3)
    assert len(llamadas) == 2 and not filas
    assert "parcial" in proc.nota
    with cliente(lambda req: httpx.Response(200, text="secreto-prueba"), []) as cli:
        with pytest.raises(FuenteNoDisponible, match="respuesta de contratos inválida") as error:
            Alpaca(CFG, ENV, cli).contratos_opciones("SPY")
    assert "secreto-prueba" not in str(error.value)


def conexion():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    almacen.inicializar(con)
    return con


def snapshot():
    return {"contrato": CONTRATO, "subyacente": "SPY", "instante": "2026-10-16T15:00:00+00:00",
            "interes_abierto": None, "multiplicador": None, "gamma": .01, "spot": None, "moneda": "USD",
            "tipo": "call", "strike": 600, "vencimiento": "2026-12-18"}


def guardar(con, fecha="2026-10-15", disponible="2026-10-16T14:00:00+00:00"):
    almacen.guardar_contratos_opciones(con, [{"contrato": CONTRATO, "subyacente": "SPY", "interes_abierto": 12,
                                              "fecha_oi": fecha, "multiplicador": 100}],
                                      Procedencia("alpaca_paper", "personal", "EEUU"))
    con.execute("UPDATE flujo_opciones_contratos SET disponible_desde=?", (disponible,))


def test_union_con_fecha_y_procedencia_separada_sin_fabricar_spot():
    con = conexion()
    guardar(con)
    original = snapshot()
    fila = almacen.enriquecer_contratos(con, [original], hasta="2026-10-16T16:00:00+00:00")[0]
    assert original["interes_abierto"] is None
    assert fila["interes_abierto"] == 12 and fila["multiplicador"] == 100
    assert fila["fecha_oi"] == "2026-10-15" and fila["gamma"] == .01 and fila["spot"] is None
    resultado = gex.calcular([fila])
    assert not resultado["disponible"]
    assert resultado["descartados"] == {"sin spot de la misma referencia": 1}
    assert resultado["fechas_oi"] == ["2026-10-15"]
    assert resultado["procedencia_contratos"][0]["fuente"] == "alpaca_paper"


@pytest.mark.parametrize("fecha,disponible,corte", [
    ("2026-10-16", "2026-10-16T14:00:00+00:00", "2026-10-16T16:00:00+00:00"),
    ("2026-10-17", "2026-10-16T14:00:00+00:00", "2026-10-16T16:00:00+00:00"),
    ("2026-10-15", "2026-10-17T14:00:00+00:00", "2026-10-16T16:00:00+00:00"),
    (None, "2026-10-16T14:00:00+00:00", "2026-10-16T16:00:00+00:00")])
def test_oi_no_filtra_futuro_ni_fecha_ausente(fecha, disponible, corte):
    con = conexion()
    guardar(con, fecha, disponible)
    fila = almacen.enriquecer_contratos(con, [snapshot()], hasta=corte)[0]
    assert fila["interes_abierto"] is None


def test_union_respeta_dia_nueva_york_y_conserva_valores_existentes():
    con = conexion()
    guardar(con)
    fila = snapshot()
    fila["instante"] = "2026-10-16T01:00:00+00:00"  # todavía 15-oct en NY
    assert almacen.enriquecer_contratos(con, [fila])[0]["interes_abierto"] is None
    fila = snapshot()
    fila.update(interes_abierto=9, multiplicador=10, spot=123)
    unido = almacen.enriquecer_contratos(con, [fila])[0]
    assert (unido["interes_abierto"], unido["multiplicador"], unido["spot"]) == (9, 10, 123)
    assert servicio.ESPERA_S["contratos_oi"] == 3600


def test_credenciales_mercado_no_autorizan_contratos():
    llamadas = []
    with cliente({}, llamadas) as cli:
        with pytest.raises(FuenteNoDisponible, match="credenciales específicas"):
            Alpaca(CFG, {"ALPACA_API_KEY_ID": "mercado", "ALPACA_API_SECRET_KEY": "mercado"}, cli).contratos_opciones("SPY")
    assert llamadas == []


def test_metadatos_posteriores_al_snapshot_no_se_unen_aunque_corte_sea_actual():
    con = conexion()
    guardar(con, disponible="2026-10-16T15:01:00+00:00")
    fila = almacen.enriquecer_contratos(con, [snapshot()], hasta="2026-10-18T16:00:00+00:00")[0]
    assert fila["interes_abierto"] is None and fila["multiplicador"] is None


def test_solo_completar_multiplicador_no_atribuye_oi_existente_a_paper():
    con = conexion()
    guardar(con)
    fila = snapshot()
    fila.update(interes_abierto=9, fecha_oi="2026-10-14")
    unido = almacen.enriquecer_contratos(con, [fila])[0]
    assert unido["interes_abierto"] == 9 and unido["fecha_oi"] == "2026-10-14"
    assert unido["multiplicador"] == 100
    assert unido["procedencia_contratos"]["campos"] == ["multiplicador"]
    assert gex.calcular([unido])["aviso_oi"] is None
