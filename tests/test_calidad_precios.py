"""La cuarentena conserva originales y revierte cualquier escritura inesperada."""
import json
import sqlite3

import pytest

from terminal.calidad_precios import auditar, poner_en_cuarentena


@pytest.fixture
def base():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE precios (instrumento_id TEXT, fecha TEXT, proveedor TEXT, tipo_dato TEXT, "
                "obtenido_en TEXT, event_time TEXT, cierre REAL, available_at TEXT, "
                "PRIMARY KEY(instrumento_id,fecha,proveedor))")
    filas = [
        ("AMD", "2026-10-30", "alpaca", "cierre", "2026-10-30T17:00:00Z", "2026-10-30T20:00:00Z", 100, None),
        ("AMD", "2026-10-30", "tiingo", "cierre", "2026-10-30T21:00:00Z", "2026-10-30T20:00:00Z", 101, None),
        ("MU", "2026-10-30", "alpaca", "cierre", "2026-10-30T17:00:00Z", None, 102, None),
        ("AMD", "2026-10-30", "alpaca_vivo", "tiempo_real", "2026-10-30T17:00:00Z", "2026-10-30T20:00:00Z", 103, None),
    ]
    con.executemany("INSERT INTO precios VALUES (?,?,?,?,?,?,?,?)", filas)
    con.commit()
    yield con
    con.close()


def test_preserva_todos_los_campos_y_solo_retira_candidato(base):
    cur = base.execute("SELECT * FROM precios WHERE proveedor='alpaca' AND instrumento_id='AMD'")
    original = dict(zip([c[0] for c in cur.description], cur.fetchone()))
    assert auditar(base) == {"candidatos": 1, "por_proveedor": {"alpaca": 1}, "sin_marcas_evaluables": 1}
    assert poner_en_cuarentena(base, 1)["retirados_de_precios"] == 1
    assert json.loads(base.execute("SELECT datos_originales FROM precios_cuarentena").fetchone()[0]) == original
    assert base.execute("SELECT COUNT(*) FROM precios").fetchone()[0] == 3
    assert poner_en_cuarentena(base, 0)["archivados_nuevos"] == 0
    assert auditar(base)["sin_marcas_evaluables"] == 1


def test_recuento_distinto_no_crea_archivo_ni_borra(base):
    with pytest.raises(ValueError, match="Cambió"):
        poner_en_cuarentena(base, 2)
    assert base.execute("SELECT COUNT(*) FROM precios").fetchone()[0] == 4
    assert not base.execute("SELECT name FROM sqlite_master WHERE name='precios_cuarentena'").fetchall()


def test_no_confirma_transaccion_del_llamador(base):
    base.execute("UPDATE precios SET cierre=99")
    with pytest.raises(ValueError, match="transacción pendiente"):
        poner_en_cuarentena(base, 1)
    assert base.in_transaction
    base.rollback()
    assert base.execute("SELECT MIN(cierre) FROM precios").fetchone()[0] == 100


def test_compara_instantes_con_zonas_y_no_confunde_igualdad(base):
    base.execute("UPDATE precios SET obtenido_en='2026-10-30T15:00:00-05:00' WHERE instrumento_id='AMD'")
    base.commit()
    assert auditar(base)["candidatos"] == 0


def test_trigger_adicional_revierte_todas_las_escrituras(base):
    base.execute("CREATE TABLE traza (valor TEXT)")
    base.execute("CREATE TRIGGER extra AFTER DELETE ON precios BEGIN INSERT INTO traza VALUES ('extra'); END")
    base.commit()
    with pytest.raises(RuntimeError, match="escrituras adicionales"):
        poner_en_cuarentena(base, 1)
    assert base.execute("SELECT COUNT(*) FROM precios").fetchone()[0] == 4
    assert base.execute("SELECT COUNT(*) FROM traza").fetchone()[0] == 0
    assert not base.execute("SELECT name FROM sqlite_master WHERE name='precios_cuarentena'").fetchall()
