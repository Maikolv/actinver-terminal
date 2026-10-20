"""Respaldo del cierre BMV con el precio de una captura del portal tomada después del cierre."""
from terminal import mercado, portal


def _pos():
    return [{"instrumento_id": "BMV:ALPEK", "precio": 16.42}, {"instrumento_id": "SIC:MU", "precio": 16541.0},
            {"instrumento_id": "BMV:GMEXICO", "precio": None}]


def test_despues_del_cierre_guarda_solo_bmv(con):
    ins = mercado.instrumentos(con)
    assert portal.cierres_desde_captura(con, "2026-10-20T14:10:00-06:00", _pos(), ins) == 1      # SIC y sin precio: no
    f = con.execute("SELECT fecha, cierre, proveedor, tipo_dato FROM precios WHERE instrumento_id='BMV:ALPEK'").fetchone()
    assert tuple(f) == ("2026-10-20", 16.42, "actinver_portal", "cierre")
    assert con.execute("SELECT COUNT(*) FROM precios WHERE instrumento_id='SIC:MU'").fetchone()[0] == 0


def test_antes_del_cierre_o_sin_sesion_no_guarda(con):
    ins = mercado.instrumentos(con)
    assert portal.cierres_desde_captura(con, "2026-10-20T10:05:00-06:00", _pos(), ins) == 0      # BMV abierta
    assert portal.cierres_desde_captura(con, "2026-10-18T12:00:00-06:00", _pos(), ins) == 0      # domingo
    assert con.execute("SELECT COUNT(*) FROM precios").fetchone()[0] == 0


def test_el_proveedor_gana_sobre_el_portal(con, ajustes):
    ins = mercado.instrumentos(con)
    portal.cierres_desde_captura(con, "2026-10-20T14:10:00-06:00", _pos(), ins)
    con.execute("INSERT INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, proveedor, tipo_dato, "
                "hora_cotizacion, obtenido_en) VALUES ('BMV:ALPEK','2026-10-20',16.40,16.40,1,'MXN','eodhd','cierre',NULL,'x')")
    assert mercado.precios_mxn(con, ajustes, ["BMV:ALPEK"], ajustados="splits")["BMV:ALPEK"].iloc[-1] == 16.40
    assert mercado.cotizaciones(con, ajustes, ["BMV:ALPEK"])["BMV:ALPEK"]["proveedor"] == "eodhd"
