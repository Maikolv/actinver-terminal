from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from terminal import aprendizaje
from terminal.flujo import almacen, calculos, microestructura, servicio
from terminal.flujo.contratos import Libro, Nivel, Procedencia


def op(t, precio, cantidad, lado, fuente="feed-a"):
    return {"instante": t, "precio": precio, "tamano": cantidad, "lado": lado, "fuente": fuente, "feed": "ticks", "mercado": "X"}


def test_footprint_volumen_delta_y_porcentaje_independientes():
    t = "2026-10-16T14:01:00+00:00"
    r = microestructura.footprint([op(t, 100, 3, "venta"), op(t, 100, 7, "compra"), op(t, 101, 2, "compra")])
    assert len(r["barras"]) == 1
    assert r["barras"][0]["inicio"] == "2026-10-16T14:00:00+00:00"
    assert r["barras"][0]["volumen"] == 12 and r["barras"][0]["delta"] == 6
    assert r["barras"][0]["delta_pct"] == 50
    c = next(c for c in r["celdas"] if c["precio"] == 100)
    assert (c["bid"], c["ask"], c["volumen"], c["delta"]) == (3, 7, 10, 4)


def test_footprint_no_infiere_agresor_ni_mezcla_fuentes():
    t = "2026-10-16T08:01:00-06:00"
    r = microestructura.footprint([op(t, 100, 3, None), op(t, 100, 7, "compra"), op(t, 100, 9, "venta", "otro")])
    assert len(r["barras"]) == 2
    b = next(b for b in r["barras"] if b["fuente"] == "feed-a")
    c = next(c for c in r["celdas"] if c["fuente"] == "feed-a")
    assert b["volumen"] == 10 and b["delta"] is None and b["delta_pct"] is None
    assert c["bid"] is None and c["ask"] is None
    assert microestructura.footprint([])["celdas"] == []
    with pytest.raises(ValueError, match="zona"):
        microestructura.footprint([op("2026-10-16T14:01:00", 100, 1, "compra")])
    with pytest.raises(ValueError, match="intervalo"):
        microestructura.footprint([], segundos=0)


def test_footprint_limites_de_cobertura():
    t = datetime(2026, 10, 16, tzinfo=UTC)
    ops = [op((t + timedelta(minutes=5 * i)).isoformat(), 100, 1, "compra") for i in range(75)]
    r = microestructura.footprint(ops)
    assert len(r["barras"]) == 60 and r["parcial"] and r["barras_totales"] == 75


def test_historial_liquidez_no_interpela_huecos_ni_suma_otros_feeds():
    libros = [
        {"id": 1, "instante": "2026-10-16T14:00:00+00:00", "fuente": "a", "niveles": [{"precio": 100, "tamano": 10, "lado": "bid"}]},
        {"id": 2, "instante": "2026-10-16T14:10:00+00:00", "fuente": "a", "niveles": [{"precio": 101, "tamano": 8, "lado": "ask"}]},
        {"id": 0, "instante": "2026-10-16T13:59:00+00:00", "fuente": "b", "niveles": [{"precio": 100, "tamano": 999, "lado": "bid"}]},
    ]
    r = microestructura.liquidez(libros)
    assert len(r["instantes"]) == 2 and len(r["celdas"]) == 2 and r["parcial"]
    assert all(c["tamano"] != 999 for c in r["celdas"])
    assert not any(c["instante"].endswith("14:10:00+00:00") and c["precio"] == 100 for c in r["celdas"])
    assert microestructura.liquidez([])["celdas"] == []


def test_historia_almacen_y_servicio_excluyen_sinteticos(con, ajustes):
    t = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
    l = Libro("SIC:MU", t, [Nivel("bid", 1, 99, 10), Nivel("ask", 1, 101, 8)])
    almacen.guardar_libro(con, l, Procedencia("real", "autorizado", "X"))
    almacen.guardar_libro(con, l, Procedencia("demo", "fixture", "X", calidad="sintetico"))
    con.commit()
    r = servicio.orderflow(con, ajustes, "SIC:MU")
    assert r["liquidez_historica"]["fuente"] == "real"
    assert r["footprint"]["celdas"] == []


def test_pdf_ema_ponderacion_y_macd_histograma():
    assert 2 / 51 * 100 == pytest.approx(3.92156862745)
    assert calculos.ema([10, 10, 10, 20], 3) == [None, None, 10, 15]
    m = calculos.macd([100 + i for i in range(60)])
    assert m["macd"][-1] == pytest.approx(7)
    assert m["hist"][-1] == pytest.approx(0, abs=1e-10)


def test_catalogo_y_captura_no_se_convierten_en_precio(tmp_path, monkeypatch):
    monkeypatch.setattr(aprendizaje, "data_dir", lambda modo: tmp_path / modo)
    d = tmp_path / "real" / "recursos"
    d.mkdir(parents=True)
    (d / "captura-referencia.json").write_text('{"apto_para_valorar": false, "filas": []}')
    assert aprendizaje.catalogo()["captura_referencia"]["apto_para_valorar"] is False
    assert aprendizaje.catalogo(demo=True)["captura_referencia"] is None
    (d / "captura-referencia.json").write_text('incompleto')
    assert "captura_aviso" in aprendizaje.catalogo()


def test_api_aprendizaje_solo_informacion(con, monkeypatch):
    from terminal import app as modulo
    modulo.app.dependency_overrides[modulo.con_db] = lambda: con
    antes = con.total_changes
    try:
        with TestClient(modulo.app, base_url='http://127.0.0.1') as cliente:
            r = cliente.get('/api/aprendizaje')
            assert r.status_code == 200 and len(r.json()["indicadores"]) == 4
            assert all(not c["url"] or c["url"].startswith('https://') for c in r.json()["cursos"])
    finally:
        modulo.app.dependency_overrides.clear()
    assert con.total_changes == antes
