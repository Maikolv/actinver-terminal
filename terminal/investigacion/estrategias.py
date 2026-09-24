"""Banco de estrategias simples con parámetros DECLARADOS ANTES de ver datos, comparadas con referencias.

Protocolo (sin fuga):
- La señal usa precios hasta el cierre de t; la operación se ejecuta al cierre de t+1 (un día de retraso).
- Rebalanceo cada 5 sesiones. Solo largos, tope de 50 % por activo (regla del Reto), sin apalancamiento.
- Costo = rotación × (comisión 0.10 % + IVA + deslizamiento); escenarios de deslizamiento 0, 0.1 % y 0.5 %.
- Selección del parámetro de cada familia SOLO con el tramo de entrenamiento (70 %); después de un embargo de 5 sesiones
  se evalúa UNA vez en la prueba. Todas las configuraciones se registran, no solo las ganadoras.
- Veredicto por estrategia: «VENTAJA» solo si en la prueba supera en resultado neto a efectivo y a pesos iguales, es
  positiva frente a pesos iguales en la mayoría de los subperiodos (años) y el bootstrap por bloques del exceso diario
  frente a pesos iguales da p < 0.05. Si no: «VENTAJA NO DEMOSTRADA».
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COSTO = 0.00116
DESLIZAMIENTOS = (0.0, 0.001, 0.005)
TOPE = 0.50
CADA = 5
VENTAJA_NO = "VENTAJA NO DEMOSTRADA"

# Familias y parámetros declarados antes de evaluar
FAMILIAS = {
    "impulso": [{"L": 20}, {"L": 60}, {"L": 120}],
    "reversion": [{"L": 5}, {"L": 10}],
    "inversa_vol": [{"L": 60}],
    "impulso_riesgo": [{"L": 60, "Lv": 60}],
}
REFERENCIAS = ("efectivo", "pesos_iguales", "comprar_y_mantener")


def _topes(w: pd.Series) -> pd.Series:
    """Proyecta a solo largos con tope por activo; el sobrante queda en efectivo."""
    w = w.clip(lower=0)
    if w.sum() > 1:
        w = w / w.sum()
    for _ in range(10):
        exceso = (w - TOPE).clip(lower=0).sum()
        w = w.clip(upper=TOPE)
        if exceso < 1e-12:
            break
        libres = w < TOPE - 1e-12
        if libres.any() and w[libres].sum() > 0:
            w[libres] += exceso * w[libres] / w[libres].sum()
    return w


def pesos_objetivo(familia: str, p: dict, hist: pd.DataFrame, k: int) -> pd.Series:
    """Pesos con información hasta t (hist termina en t)."""
    cols = hist.columns
    n = len(cols)
    if familia == "efectivo":
        return pd.Series(0.0, index=cols)
    if familia in ("pesos_iguales", "comprar_y_mantener"):
        return _topes(pd.Series(1.0 / n, index=cols))
    r = np.log(hist).diff()
    if familia == "impulso":
        s = np.log(hist.iloc[-1] / hist.iloc[-p["L"] - 1])
        sel = s[s > 0].nlargest(k).index
        return _topes(pd.Series(1.0 / max(k, 1), index=sel).reindex(cols, fill_value=0.0))
    if familia == "reversion":
        s = np.log(hist.iloc[-1] / hist.iloc[-p["L"] - 1])
        sel = s.nsmallest(k).index
        return _topes(pd.Series(1.0 / max(k, 1), index=sel).reindex(cols, fill_value=0.0))
    if familia == "inversa_vol":
        v = r.iloc[-p["L"]:].std()
        return _topes((1 / v) / (1 / v).sum())
    if familia == "impulso_riesgo":
        s = np.log(hist.iloc[-1] / hist.iloc[-p["L"] - 1])
        v = r.iloc[-p["Lv"]:].std()
        sel = s[s > 0].nlargest(k).index
        if not len(sel):
            return pd.Series(0.0, index=cols)
        w = (1 / v[sel]) / (1 / v[sel]).sum()
        return _topes(w.reindex(cols, fill_value=0.0))
    raise ValueError(familia)


def simular(precios: pd.DataFrame, familia: str, p: dict | None = None, k: int = 2, desliz: float = 0.001,
            inicio: int = 0, fin: int | None = None) -> dict:
    """Curva neta diaria entre los índices [inicio, fin) del calendario. Señal en t, ejecución al cierre de t+1."""
    p = p or {}
    precios = precios.dropna()
    fin = fin or len(precios)
    L = max([p.get("L", 0), p.get("Lv", 0), 1]) + 1
    ret = precios.pct_change()
    w = pd.Series(0.0, index=precios.columns)
    pendiente, valor = None, 1.0
    diarios, rot_total, n_reb, expos = [], 0.0, 0, []
    costo = COSTO + desliz
    for t in range(max(inicio, L), fin):
        dia = ret.iloc[t].fillna(0)
        r_dia = float((w * dia).sum())
        w = w * (1 + dia) / (1 + r_dia) if (1 + r_dia) else w  # deriva de pesos por precio
        c = 0.0
        if pendiente is not None:  # ejecución al cierre de t de la señal emitida en t-1
            if familia != "comprar_y_mantener" or n_reb == 0:
                rot = float((pendiente - w).abs().sum())
                c = rot * costo
                rot_total += rot
                w = pendiente
                n_reb += 1
            pendiente = None
        valor *= (1 + r_dia - c)
        diarios.append(r_dia - c)
        expos.append(float(w.sum()))
        if (t - max(inicio, L)) % CADA == 0 and t < fin - 1:
            pendiente = pesos_objetivo(familia, p, precios.iloc[: t + 1], k)
    d = pd.Series(diarios, index=precios.index[max(inicio, L):fin])
    curva = (1 + d).cumprod()
    caida = float((curva / curva.cummax() - 1).min()) if len(curva) else 0.0
    vol = float(d.std() * np.sqrt(252)) if len(d) > 1 else 0.0
    return {"familia": familia, "parametros": p, "k": k, "deslizamiento": desliz, "resultado_neto": float(valor - 1),
            "vol_anual": vol, "sharpe": float(d.mean() / d.std() * np.sqrt(252)) if d.std() > 0 else 0.0,
            "caida_maxima": caida, "rotacion_total": rot_total, "rebalanceos": n_reb,
            "exposicion_media": float(np.mean(expos)) if expos else 0.0, "_diarios": d}


def bootstrap_exceso(a: pd.Series, b: pd.Series, bloque: int = 10, n: int = 2000, semilla: int = 20261113) -> float:
    """p-valor unilateral (H1: a > b) del exceso medio diario con bootstrap por bloques (respeta la autocorrelación)."""
    x = (a - b).dropna().to_numpy()
    if len(x) < 2 * bloque:
        return 1.0
    rng = np.random.default_rng(semilla)
    m0 = x.mean()
    xc = x - m0
    nb = int(np.ceil(len(x) / bloque))
    medias = np.empty(n)
    for i in range(n):
        idx = np.concatenate([np.arange(s, s + bloque) for s in rng.integers(0, len(x) - bloque, nb)])[: len(x)]
        medias[i] = xc[idx].mean()
    return float((medias >= m0).mean())


def experimento(precios: pd.DataFrame, k: int = 2, frac_entrenamiento: float = 0.7, embargo: int = 5) -> dict:
    precios = precios.dropna()
    n = len(precios)
    corte = int(n * frac_entrenamiento)
    registro = []  # TODAS las configuraciones
    elegidos = {}
    for fam, grid in FAMILIAS.items():
        mejores = []
        for p in grid:
            r = simular(precios, fam, p, k, 0.001, 0, corte)
            registro.append({"tramo": "entrenamiento", **{kk: v for kk, v in r.items() if not kk.startswith("_")}})
            mejores.append((r["sharpe"], p))
        elegidos[fam] = max(mejores, key=lambda x: x[0])[1]  # elección solo con entrenamiento
    ini_p = corte + embargo
    prueba = {}
    for fam in list(REFERENCIAS) + list(FAMILIAS):
        p = elegidos.get(fam, {})
        res = {d: simular(precios, fam, p, k, d, ini_p, n) for d in DESLIZAMIENTOS}
        prueba[fam] = res
        for d, r in res.items():
            registro.append({"tramo": "prueba", **{kk: v for kk, v in r.items() if not kk.startswith("_")}})
    base = prueba["pesos_iguales"][0.001]["_diarios"]
    efectivo = prueba["efectivo"][0.001]["resultado_neto"]
    resumen = []
    for fam, res in prueba.items():
        r = res[0.001]
        anios = r["_diarios"].groupby(r["_diarios"].index.year).apply(lambda s: (1 + s).prod() - 1)
        anios_b = base.groupby(base.index.year).apply(lambda s: (1 + s).prod() - 1)
        gana = int((anios > anios_b.reindex(anios.index)).sum())
        pval = bootstrap_exceso(r["_diarios"], base) if fam not in REFERENCIAS else None
        supera = (fam not in REFERENCIAS and r["resultado_neto"] > max(efectivo, prueba["pesos_iguales"][0.001]["resultado_neto"])
                  and gana > len(anios) / 2 and pval is not None and pval < 0.05)
        resumen.append({"estrategia": fam, "parametros": elegidos.get(fam, {}), "neto_prueba": r["resultado_neto"],
                        "neto_sin_desliz": res[0.0]["resultado_neto"], "neto_desliz_0.5%": res[0.005]["resultado_neto"],
                        "sharpe": r["sharpe"], "caida_maxima": r["caida_maxima"], "rotacion": r["rotacion_total"],
                        "exposicion_media": r["exposicion_media"],
                        "subperiodos_ganados_vs_pesos_iguales": f"{gana}/{len(anios)}", "p_bootstrap_vs_pesos_iguales": pval,
                        "veredicto": "referencia" if fam in REFERENCIAS else ("VENTAJA FUERA DE MUESTRA" if supera else VENTAJA_NO)})
    return {"n_sesiones": n, "entrenamiento": [str(precios.index[0].date()), str(precios.index[corte - 1].date())],
            "prueba": [str(precios.index[ini_p].date()), str(precios.index[-1].date())], "embargo": embargo, "k": k,
            "parametros_elegidos_con_entrenamiento": elegidos, "resumen": resumen, "configuraciones_registradas": registro,
            "veredicto_global": ("VENTAJA FUERA DE MUESTRA" if any(r["veredicto"].startswith("VENTAJA F") for r in resumen)
                                 else VENTAJA_NO)}
