"""Catálogo del simulador: la transcripción de las capturas limita el universo y un cambio fuerza el recálculo."""
from pathlib import Path

import pytest

from terminal import importar, mercado, servicios

RAIZ = Path(__file__).resolve().parents[1]


def _catalogo(con, claves):
    csv = "clave,tipo,nombre\n" + "".join(f"{c},accion,prueba\n" for c in claves)
    return importar.importar(con, csv.encode(), "catalogo_simulador.csv", "universo", mercado.instrumentos(con),
                             confirmar=True)


def test_transcripcion_del_simulador_coincide_con_el_universo(con):
    import csv
    filas = [r for r in csv.DictReader((RAIZ / "config" / "pdf_transcripcion.csv").open(encoding="utf-8"))
             if r["seccion_pdf"] in ("Acciones", "Fondos")]
    claves = sorted({f"{r['clave_pdf']} {r['serie_pdf']}".strip() for r in filas})
    rep = _catalogo(con, claves)
    assert rep["rechazadas"] == 0 and rep["aceptadas"] == len(claves)
    assert "SIC:AAPL" in rep["ids"] and "SIC:SHV" not in rep["ids"]  # ETF no visto en el simulador


def test_cambio_de_catalogo_pide_recalcular(con):
    _catalogo(con, ["AMX B"])
    p = {"estado": "calculada", "catalogo_simulador": servicios.huella_catalogo(con), "avisos": []}
    assert not servicios._revisar_catalogo(con, dict(p)).get("recalcular")
    _catalogo(con, ["AMX B", "AAPL *"])
    r = servicios._revisar_catalogo(con, dict(p))
    assert r["recalcular"] and "catálogo del simulador" in r["avisos"][-1]


def test_escenarios_usan_horizonte_real_y_no_extrapolan_saltos_unicos():
    import numpy as np
    import pandas as pd
    from terminal import optimizador as op
    rng = np.random.default_rng(3)
    r = pd.Series(rng.normal(0.0004, 0.01, 500), index=pd.bdate_range("2024-01-01", periods=500))
    r.iloc[250] = 2.0  # salto único (+200 %), como un anuncio de fusión
    X = pd.DataFrame({"A": r})
    e = op._escenarios(X, pd.Series({"A": 1.0}), 29 / op.DIAS, {"A": {"clase": "accion", "exposicion": "MXN"}})
    assert e["sesiones_horizonte"] == 29 and e["saltos_excluidos_de_la_media"][0]["rend"] == 2.0
    assert abs(e["central_p50"]) < 0.02  # sin el salto, la mediana a 29 sesiones es modesta
    assert e["volatilidad_anual_con_saltos"] > 1.0 > e["volatilidad_anual"]  # el salto se informa, no se extrapola


def test_precios_solo_splits_quitan_el_salto_del_split_pero_no_suman_dividendos():
    import pandas as pd
    from terminal import mercado
    # split inverso 1:10 el día 3 y un dividendo de 1 % el día 5 (factores de ajuste hacia atrás, como Tiingo)
    df = pd.DataFrame({"id": ["X"] * 6, "fecha": list("123456"),
                       "p": [1.6, 1.7, 17.0, 17.5, 17.2, 17.4],
                       "aj": [16.0 * 0.99, 17.0 * 0.99, 17.0 * 0.99, 17.5 * 0.99, 17.2, 17.4]})
    s = mercado._solo_splits(df).tolist()
    assert s[0] == pytest.approx(16.0) and s[1] == pytest.approx(17.0)  # antes del split: ×10, sin el 1 % del dividendo
    assert s[2:] == pytest.approx([17.0, 17.5, 17.2, 17.4])             # el último precio es el cierre real
