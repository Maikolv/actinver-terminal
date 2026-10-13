"""Verifica origen, cálculo y separación de cierres para los gráficos."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from terminal import visualizaciones
from terminal.app import app


def _sembrar(con):
    iid = con.execute("SELECT id FROM instrumentos WHERE estado='activo' LIMIT 1").fetchone()[0]
    filas = [(iid, "2026-10-08", 100.0, "USD", "tiingo", "cierre"),
             (iid, "2026-10-09", 105.0, "USD", "tiingo", "cierre"),
             (iid, "2026-10-09", 999.0, "USD", "archivo", "cierre"),
             (iid, "2026-10-10", 500.0, "USD", "demo_sintetico", "sintetico")]
    con.executemany("INSERT INTO precios (instrumento_id,fecha,cierre,moneda,proveedor,tipo_dato,obtenido_en) "
                    "VALUES (?,?,?,?,?,?,'2026-10-10T10:00:00+00:00')", filas)
    con.commit()
    return iid


def test_mapa_usa_dos_cierres_reales_y_fuente_prioritaria(con, ajustes):
    iid = _sembrar(con)
    resultado = visualizaciones.mapa(con, ajustes)
    celda = next(c for c in resultado["celdas"] if c["id"] == iid)
    assert celda["cierre"] == 105.0 and celda["proveedor"] == "tiingo"
    assert celda["variacion"] == pytest.approx(.05)
    assert celda["fecha"] == "2026-10-09"
    assert "demo_sintetico" not in str(resultado)


def test_serie_no_fabrica_velas_y_calcula_sma_rsi_solo_con_historia(con, ajustes):
    iid = _sembrar(con)
    for dia in range(1, 22):
        con.execute("INSERT OR REPLACE INTO precios (instrumento_id,fecha,cierre,moneda,proveedor,tipo_dato,obtenido_en) "
                    "VALUES (?,?,?,?,?,?,?)", (iid, date(2026, 9, dia).isoformat(), float(dia), "USD",
                                               "tiingo", "cierre", "2026-10-10T10:00:00+00:00"))
    con.commit()
    resultado = visualizaciones.serie(con, ajustes, iid)
    assert resultado["puntos"][0]["media_20"] is None
    assert resultado["puntos"][-1]["media_20"] is not None
    assert resultado["puntos"][-1]["rsi_14"] == 100
    assert all("apertura" not in p and "maximo" not in p for p in resultado["puntos"])


def test_api_visualizaciones_solo_expone_datos_y_rechaza_simbolo_inexistente():
    with TestClient(app, base_url="http://127.0.0.1:8765") as cliente:
        respuesta = cliente.get("/api/visualizaciones/mercado")
        assert respuesta.status_code == 200 and "celdas" in respuesta.json()
        assert cliente.get("/api/visualizaciones/serie/no-existe").status_code == 404
