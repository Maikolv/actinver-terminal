"""Auditoría de la probabilidad de subida: Brier frente a la frecuencia base, recalibración y veredicto."""
import numpy as np

from terminal.investigacion import calibracion as cal


def _datos(seed, calibrada):
    rng = np.random.default_rng(seed)
    n_f, por_f = 120, 20
    fechas = np.datetime64("2026-01-01") + np.repeat(np.arange(n_f), por_f).astype("timedelta64[D]")
    verdad = rng.uniform(0.05, 0.95, n_f * por_f)
    y = (rng.uniform(size=verdad.size) < verdad).astype(float)
    p = verdad if calibrada else np.clip(1 - verdad + rng.normal(0, 0.05, verdad.size), 0, 1)  # invertida: mala
    return p, y, fechas


def test_probabilidad_informativa_y_calibrada():
    p, y, f = _datos(1, True)
    r = cal.auditar(p[:800], y[:800], p[800:], y[800:], f[800:], base_rate=float(y[:800].mean()))
    m = r["metodos"][0]
    assert m["brier"] < r["brier_frecuencia_base"] and m["dif_brier_vs_base_ic90"][1] < 0
    assert r["veredicto"] == "calibrada" and m["brier_skill_vs_frecuencia_base"] > 0.1


def test_probabilidad_mal_calibrada_queda_experimental_y_la_recalibracion_se_mide_aparte():
    p, y, f = _datos(2, False)
    r = cal.auditar(p[:800], y[:800], p[800:], y[800:], f[800:], base_rate=float(y[:800].mean()))
    assert r["veredicto"] == "experimental" and not r["metodos"][0]["mejor_que_base"]
    iso = next(m for m in r["metodos"] if m["metodo"].startswith("isotónica"))
    assert iso["brier"] < r["metodos"][0]["brier"]       # la isotónica ajustada en validación corrige la inversión


def test_sin_informacion_no_supera_a_la_frecuencia_base():
    rng = np.random.default_rng(3)
    y = (rng.uniform(size=2400) < 0.55).astype(float)
    p = rng.uniform(0.3, 0.7, 2400)
    f = np.datetime64("2026-01-01") + np.repeat(np.arange(120), 20).astype("timedelta64[D]")
    r = cal.auditar(p[:800], y[:800], p[800:], y[800:], f[800:], base_rate=float(y[:800].mean()))
    assert r["veredicto"] == "experimental"
