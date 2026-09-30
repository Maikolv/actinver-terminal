"""Respaldo verificado de la base: el motor hace uno al día (antes no existía ninguno) y conserva los más recientes."""
import sqlite3

from terminal import db


def test_respaldo_diario_verificado_y_rotado(tmp_path):
    origen = tmp_path / "terminal.db"
    con = sqlite3.connect(origen)
    con.execute("CREATE TABLE transacciones (id INTEGER)")
    con.execute("INSERT INTO transacciones VALUES (1)")
    con.commit()
    con.close()
    r = db.respaldo_diario(origen, conservar=2)
    c = sqlite3.connect(r)
    n = c.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]
    c.close()
    assert r.exists() and n == 1
    assert db.respaldo_diario(origen, conservar=2) is None          # ya hay uno de menos de 20 h
    for i in range(3):
        db.respaldar(origen, conservar=2)
    assert len(list((tmp_path / "respaldos").glob("terminal-*.db"))) == 2
