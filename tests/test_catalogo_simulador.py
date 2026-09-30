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


def test_media_robusta_acota_saltos_unicos_sin_tocar_dias_normales():
    import numpy as np
    from skfolio.moments import ShrunkMu
    from terminal import optimizador as op
    rng = np.random.default_rng(5)
    X = rng.normal(0.0005, 0.02, (500, 3))
    X[200, 0] = 1.75                      # salto único, como MRNA el 19-ago-2026
    X[300, 1] = -0.08                     # día malo pero normal: se conserva
    A = op.acotar_saltos(X)
    assert A[200, 0] < 0.2 and A[300, 1] == -0.08 and np.allclose(A[:, 2], X[:, 2])
    mu_simple, mu_rob = ShrunkMu().fit(X).mu_, op.MuRobusto().fit(X).mu_
    assert mu_simple[0] - mu_rob[0] > 0.002  # el salto ya no domina la media del activo
    assert abs(mu_rob[2] - mu_simple[2]) < 1e-3


def test_escenarios_no_son_mas_optimistas_que_la_validacion_fuera_de_muestra():
    """La volatilidad dentro de muestra de pesos optimizados está sesgada a la baja: el escenario usa la mayor entre
    ella y la observada fuera de muestra, y la menor de las medias."""
    import numpy as np
    import pandas as pd
    from terminal import optimizador as op
    rng = np.random.default_rng(9)
    idx = pd.bdate_range("2024-01-01", periods=300)
    X = pd.DataFrame({"A": rng.normal(0.002, 0.005, 300)}, index=idx)          # calma aparente: 8 % anual
    oos = pd.Series(rng.normal(-0.0005, 0.025, 84), index=idx[-84:])           # fuera de muestra: 40 % anual
    el = {"A": {"clase": "accion", "exposicion": "MXN"}}
    base = op._escenarios(X, pd.Series({"A": 1.0}), 29 / op.DIAS, el)
    con = op._escenarios(X, pd.Series({"A": 1.0}), 29 / op.DIAS, el, oos=oos)
    assert con["volatilidad_anual"] > 0.3 > base["volatilidad_anual"]
    assert con["media_anual_usada"] < base["media_anual_usada"]
    assert con["adverso_p10"] < base["adverso_p10"] - 0.05
    assert con["fuente_parametros"]["volatilidad"] == "fuera de muestra"


def test_riesgos_advierten_si_la_propuesta_no_supera_a_1_n():
    import pandas as pd
    from terminal import optimizador as op
    el = {k: {"clase": "accion", "exposicion": "MXN", "ventana_venta": "diaria", "vigencia": "vigente"} for k in "AB"}
    w = pd.Series({"A": 0.6, "B": 0.4})
    m = {"rend_anual": 0.011, "sesiones": 300, "max_caida": -0.05}
    esc = {"peor_trimestre_historico": 0.01}
    r = op._riesgos(w, el, m, esc, [], {"max_exposicion_usd": 1.0}, {"rend_anual": 0.108})
    assert any("No supera a la referencia simple" in x and "10.8%" in x for x in r)
    assert not any("No supera" in x for x in op._riesgos(w, el, m, esc, [], {"max_exposicion_usd": 1.0}, {"rend_anual": 0.0}))
