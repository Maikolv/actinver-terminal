"""Historia sustituta con ADR: solo splits, validación por correlación y extensión SOLO hacia atrás."""
import csv

import numpy as np
import pandas as pd

from terminal import proxy_adr as pa


def _csv(tmp_path, adr, fechas, precios, splits=None):
    with (tmp_path / f"{adr}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["fecha", "cierre", "factor_split", "volumen"])
        for i, (f, p) in enumerate(zip(fechas, precios, strict=True)):
            w.writerow([f.date().isoformat(), p, (splits or {}).get(i, 1.0), 1000])


def test_split_del_adr_no_aparece_como_rendimiento(tmp_path):
    f = pd.bdate_range("2024-01-01", periods=6)
    _csv(tmp_path, "XX", f, [10, 10.5, 11, 5.6, 5.7, 5.8], splits={3: 2.0})   # split 2:1 el día 4
    r = pa.serie_adr("XX", tmp_path).pct_change().dropna()
    assert abs(r.iloc[2] - (5.6 * 2 / 11 - 1)) < 1e-12 and r.abs().max() < 0.06


def test_valida_por_correlacion_y_extiende_solo_antes_del_primer_dato_local(tmp_path, monkeypatch):
    rng = np.random.default_rng(1)
    f = pd.bdate_range("2023-01-02", periods=500)
    adr = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 500)))
    _csv(tmp_path, "AMX", f, adr)
    fx = pd.Series(17.0, index=f)
    monkeypatch.setattr(pa.mercado, "fx_serie", lambda con, a: fx)
    prox = pa.retornos_mxn("AMX", fx, tmp_path)
    local = prox + rng.normal(0, 0.002, len(prox))            # la acción local sigue al ADR
    local.iloc[:300] = np.nan                                  # pero solo hay un año local
    R = pd.DataFrame({"BMV:AMX": local, "SIC:X": rng.normal(0, 0.01, len(prox))}, index=prox.index)
    R2, inf = pa.extender(None, {}, R, tmp_path)
    fila = inf[0]
    assert fila["aceptado"] and fila["correlacion"] > 0.9 and fila["sesiones_agregadas"] == 300
    assert R2["BMV:AMX"].iloc[300:].equals(R["BMV:AMX"].iloc[300:])          # lo local no se toca
    R["BMV:AMX"] = rng.normal(0, 0.01, len(prox))                            # sin relación ⇒ se rechaza
    R.iloc[:300, 0] = np.nan
    assert not pa.extender(None, {}, R, tmp_path)[1][0]["aceptado"]
