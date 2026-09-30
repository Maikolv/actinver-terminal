"""El ranking del Reto solo muestra lo que el simulador permite operar (catálogo importado)."""
from terminal import ranking, reto, vigencia

from conftest import sembrar_precios


def test_ranking_excluye_lo_que_no_esta_en_el_catalogo_del_simulador(con, ajustes):
    ids = ["BMV:AMX", "SIC:AAPL", "SIC:QQQ"]
    sembrar_precios(con, ids, fin=vigencia.ultima_sesion_cerrada("XNYS"), sesiones=200, proveedor="archivo")
    con.executemany("INSERT INTO universo_simulador VALUES (?,?,?)",
                    [("BMV:AMX", "AMX B", "2026-09-22"), ("SIC:AAPL", "AAPL *", "2026-09-22")])
    con.commit()
    r = ranking.calcular(con, ajustes)
    vistos = {f["id"] for f in r["filas"]}
    assert "SIC:QQQ" not in vistos and reto.activo()
    assert r["fuera_del_catalogo"] >= 1
