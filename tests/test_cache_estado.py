"""29-oct: /api/estado responde con la caché de cotizaciones y recalcula en segundo plano; el Ranking se precalienta."""
import time

from terminal import app as modulo
from terminal import db, mercado, ranking


def _esperar_refresco():
    for _ in range(200):  # el recálculo corre en un hilo; termina al liberar el candado
        if modulo._COT_REFRESCO.acquire(blocking=False):
            modulo._COT_REFRESCO.release()
            return
        time.sleep(0.05)


def test_estado_usa_la_cache_y_recalcula_en_segundo_plano(con, monkeypatch):
    llamadas = []
    original = mercado.cotizaciones
    monkeypatch.setattr(mercado, "cotizaciones", lambda *a, **k: llamadas.append(1) or original(*a, **k))
    ids = ["BMV:AMX"]
    _, hace = modulo.cotizaciones_estado(con, ids)
    assert len(llamadas) == 1 and hace == 0
    _, hace = modulo.cotizaciones_estado(con, ids)
    assert len(llamadas) == 1                              # datos iguales y reciente: no recalcula
    with db.transaccion(con):                              # un precio nuevo cambia la marca de datos
        con.execute("INSERT INTO precios (instrumento_id, fecha, cierre, moneda, proveedor, tipo_dato, obtenido_en) "
                    "VALUES ('BMV:AMX', '2026-10-28', 17.5, 'MXN', 'prueba', 'cierre', 'x')")
    ruta = con.execute("PRAGMA database_list").fetchone()[2]
    t, marca, previa = modulo._COT[(ruta, tuple(ids))]
    modulo._COT[(ruta, tuple(ids))] = (t - 16, marca, previa)   # pasaron más de 15 s desde el último cálculo
    cot, _ = modulo.cotizaciones_estado(con, ids)          # responde de inmediato con lo anterior…
    _esperar_refresco()
    assert len(llamadas) == 2                              # …y lo recalcula en segundo plano
    cot, _ = modulo.cotizaciones_estado(con, ids)
    assert cot["BMV:AMX"]["precio"] == 17.5


def test_estado_no_sirve_una_cache_demasiado_vieja(con, monkeypatch):
    ids = ["BMV:WALMEX"]
    modulo.cotizaciones_estado(con, ids)
    ruta = con.execute("PRAGMA database_list").fetchone()[2]
    t, marca, cot = modulo._COT[(ruta, tuple(ids))]
    modulo._COT[(ruta, tuple(ids))] = (t - modulo.COT_MAX_S - 1, marca, cot)
    _, hace = modulo.cotizaciones_estado(con, ids)
    assert hace == 0                                       # más de 10 min: se recalcula antes de responder


def test_estado_tibio_no_espera_consulta_lenta(con, monkeypatch):
    ids = ["SIC:AAPL"]
    modulo.cotizaciones_estado(con, ids)
    original = mercado.cotizaciones

    def lenta(*args, **kwargs):
        time.sleep(1.2)
        return original(*args, **kwargs)

    monkeypatch.setattr(mercado, "cotizaciones", lenta)
    inicio = time.monotonic()
    modulo.cotizaciones_estado(con, ids)
    assert time.monotonic() - inicio < 1  # aunque la lectura de mercado tarde más de un segundo


def test_precalentar_llena_la_cache_del_ranking(con, monkeypatch):
    ruta = con.execute("PRAGMA database_list").fetchone()[2]
    original = db.conectar
    monkeypatch.setattr(db, "conectar", lambda *a, **k: original(ruta))
    ranking._CACHE.clear()
    modulo.precalentar()
    assert any(k[0] == ruta for k in ranking._CACHE)
