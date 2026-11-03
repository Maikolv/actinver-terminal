"""Respuestas fuera de contrato no deben sobrescribir historia ni hacerse pasar por cierres."""
from datetime import UTC, datetime

import httpx
import pytest

from terminal import ingesta, migraciones
from terminal.adaptadores.base import Adaptador
from terminal.adaptadores.proveedores import Tiingo

CERRADO = datetime(2026, 10, 30, 22, tzinfo=UTC)
ABIERTO = datetime(2026, 10, 30, 17, tzinfo=UTC)
MARCAS = ("2026-10-29T20:00:00+00:00", "2026-10-29T23:02:00+00:00", "2026-10-29T23:05:00+00:00")


def barra(fecha, precio):
    return {"date": fecha, "close": precio, "adjClose": precio, "volume": 10, "divCash": 0, "splitFactor": 1}


def preparar(con, respuestas):
    llamadas = []

    def responder(peticion):
        assert peticion.url.host == "api.tiingo.com"
        llamadas.append(peticion)
        return httpx.Response(200, json=respuestas)

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    adaptadores = {n: Adaptador(con, {"activo": False}, cliente=cliente) for n in ingesta.ORDEN_PRECIOS}
    adaptadores["tiingo"] = Tiingo(con, {}, "ficticia", cliente=cliente)
    con.execute("UPDATE instrumentos SET estado='inactivo' WHERE id!='SIC:AMD'")
    con.commit()
    return adaptadores, llamadas


def test_respuesta_solapada_conserva_valor_y_tres_marcas_conocidas(con, ajustes, monkeypatch):
    con.execute("INSERT INTO precios (instrumento_id,fecha,cierre,moneda,proveedor,tipo_dato,obtenido_en,"
                "event_time,available_at,ingested_at) VALUES ('SIC:AMD','2026-10-29',100,'USD','tiingo','cierre',?,?,?,?)",
                (MARCAS[2], *MARCAS))
    con.commit()
    adaptadores, llamadas = preparar(con, [barra("2026-10-29", 50),
                                         {**barra("2026-10-30", 110), "divCash": 0.25, "splitFactor": 2}])
    monkeypatch.setattr(ingesta, "ahora_db", lambda: CERRADO.isoformat())
    resultado = ingesta.actualizar_precios(con, adaptadores, ahora=CERRADO, ajustes=ajustes)
    vieja = con.execute("SELECT cierre,event_time,available_at,ingested_at,obtenido_en FROM precios "
                        "WHERE instrumento_id='SIC:AMD' AND fecha='2026-10-29'").fetchone()
    assert tuple(vieja) == (100, *MARCAS, MARCAS[2])
    nueva = con.execute("SELECT proveedor,tipo_dato,event_time,available_at,ingested_at FROM precios "
                        "WHERE instrumento_id='SIC:AMD' AND fecha='2026-10-30'").fetchone()
    assert nueva["proveedor"] == "tiingo" and nueva["tipo_dato"] == "cierre"
    assert nueva["event_time"] and nueva["available_at"] and nueva["ingested_at"] == CERRADO.isoformat()
    eventos = con.execute("SELECT tipo,valor,event_time,available_at,ingested_at "
                          "FROM eventos_corporativos ORDER BY tipo").fetchall()
    marcas = tuple(nueva[k] for k in ("event_time", "available_at", "ingested_at"))
    assert [tuple(f) for f in eventos] == [("dividendo", 0.25, *marcas), ("split", 2, *marcas)]
    assert llamadas[0].url.params["startDate"] == "2026-10-30"
    assert resultado["tiingo"]["registros"] == 1


def test_sesion_abierta_no_se_guarda_como_cierre(con):
    adaptadores, llamadas = preparar(con, [barra("2026-10-29", 100), barra("2026-10-30", 110)])
    ingesta.actualizar_precios(con, adaptadores, ahora=ABIERTO)
    assert [r[0] for r in con.execute("SELECT fecha FROM precios")] == ["2026-10-29"]
    assert llamadas[0].url.params["endDate"] == "2026-10-29"


def test_barra_de_sesion_abierta_no_borra_cotizacion_intradia(con, ajustes):
    evento = "2026-10-30T16:59:58+00:00"
    recibido = ABIERTO.isoformat()
    con.execute("INSERT INTO precios (instrumento_id,fecha,cierre,moneda,proveedor,tipo_dato,hora_cotizacion,"
                "obtenido_en,event_time,available_at,ingested_at) "
                "VALUES ('SIC:AMD','2026-10-30',125,'USD','alpaca_vivo','tiempo_real',?,?,?,?,?)",
                (evento, recibido, evento, recibido, recibido))
    con.commit()
    adaptadores, _ = preparar(con, [barra("2026-10-29", 100), barra("2026-10-30", 110)])
    ingesta.actualizar_precios(con, adaptadores, ahora=ABIERTO)
    migraciones.completar_tiempos(con, ajustes)
    vivo = con.execute("SELECT cierre,tipo_dato,event_time,available_at,ingested_at FROM precios "
                       "WHERE instrumento_id='SIC:AMD' AND proveedor='alpaca_vivo'").fetchone()
    assert vivo is not None and tuple(vivo) == (125, "tiempo_real", evento, recibido, recibido)
    assert not con.execute("SELECT 1 FROM precios WHERE fecha='2026-10-30' AND proveedor='tiingo'").fetchone()


@pytest.mark.parametrize("fecha", ["2026-10-00", "20261030", "2026-10-31", "sin-fecha"])
def test_fecha_invalida_o_futura_no_entra_en_la_historia(con, fecha):
    adaptadores, _ = preparar(con, [barra("2026-10-30", 110), barra(fecha, 999)])
    resultado = ingesta.actualizar_precios(con, adaptadores, ahora=CERRADO)
    assert [r[0] for r in con.execute("SELECT fecha FROM precios")] == ["2026-10-30"]
    assert resultado["tiingo"]["registros"] == 1
    corrida = con.execute("SELECT estado,mensaje FROM ingestas WHERE proveedor='tiingo'").fetchone()
    assert corrida["estado"] == "parcial" and "descart" in corrida["mensaje"].lower()
