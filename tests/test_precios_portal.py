"""Precios de la pestaña «Acciones» del simulador (PDF del participante): BMV se importa, el SIC solo se compara."""
import pytest

from terminal import precios_portal as pp

TEXTO = """Reto Actinver | Acciones
Portal del simulador · 5 de octubre de 2026 · Precios en MXN
#
Emisora
Precio
Variación
Vol. compra
Precio compra
Vol. venta
Precio venta
10
ALPEK A
$14.56
-1.29%
105,600
$14.54
85,900
$14.64
13
AMD *
$11,392.74
-1.02%
398
$11,355.94
400
$11,484.86
99
ZZZZ *
$1.00
0.00%
1
$1.00
1
$1.00
"""


def test_interpretar_fecha_y_filas():
    d = pp.interpretar(TEXTO)
    assert d["fecha"] == "2026-10-05"
    assert [f["emisora"] for f in d["filas"]] == ["ALPEK A", "AMD *", "ZZZZ *"]
    assert d["filas"][1]["precio"] == 11392.74 and d["filas"][0]["precio_venta"] == 14.64


def test_sin_fecha_unica_se_rechaza():
    with pytest.raises(pp.ErrorDocumento):
        pp.interpretar(TEXTO.replace("5 de octubre de 2026", ""))


def test_importa_bmv_en_mxn_y_no_mezcla_el_sic(con, ajustes, monkeypatch):
    monkeypatch.setattr(pp, "texto_pdf", lambda b: TEXTO)
    vista = pp.importar(con, ajustes, b"%PDF-1.4 prueba", "acciones.pdf")
    assert not vista["confirmado"] and vista["bmv"] == 1 and vista["sic"] == 1 and vista["fuera_del_universo"] == ["ZZZZ *"]
    assert not con.execute("SELECT 1 FROM precios WHERE proveedor='archivo'").fetchone()   # la vista previa no escribe
    rep = pp.importar(con, ajustes, b"%PDF-1.4 prueba", "acciones.pdf", confirmar=True)
    assert rep["confirmado"]
    filas = con.execute("SELECT instrumento_id, fecha, cierre, moneda FROM precios WHERE proveedor='archivo'").fetchall()
    assert [tuple(f) for f in filas] == [("BMV:ALPEK", "2026-10-05", 14.56, "MXN")]          # AMD (USD) no se toca
