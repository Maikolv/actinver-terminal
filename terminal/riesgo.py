"""Riesgo de la cartera actual con supuestos visibles: exposición, concentración, volatilidad, drawdown, VaR, CVaR y
escenarios de estrés. Todo se calcula con precios de cierre en MXN ajustados solo por splits (como el simulador) y con
los PESOS ACTUALES mantenidos constantes hacia atrás. Es una descripción del riesgo histórico, no una predicción.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import escenarios, mercado, reto, servicios

DIAS = 252
NIVELES = (0.95, 0.99)


def _supuestos(ventana: int, n: int, desde: str | None, hasta: str | None, horizonte: int) -> list[str]:
    return [f"Ventana: últimas {ventana} sesiones con datos ({n} rendimientos usados, {desde} a {hasta}).",
            "Pesos actuales constantes en toda la ventana, sin rebalanceo ni nuevas operaciones.",
            "Precios de cierre en MXN, ajustados solo por splits (el Reto no paga dividendos); el SIC se valúa con el "
            "precio de origen × tipo de cambio del día.",
            "VaR/CVaR históricos: cuantiles empíricos de los rendimientos observados. VaR paramétrico: supone normalidad "
            "(subestima colas gruesas).",
            f"Horizonte de {horizonte} sesiones escalado por √h (supone rendimientos independientes).",
            "El efectivo no tiene riesgo de precio. Rendimientos pasados no garantizan resultados futuros."]


def metricas_serie(r: pd.Series, valor: float, horizonte: int = 1) -> dict:
    r = r.dropna()
    if len(r) < 30:
        return {"n": len(r), "suficiente": False}
    acum = (1 + r).cumprod()
    dd = acum / acum.cummax() - 1
    vol_d = float(r.std())
    out = {"n": int(len(r)), "suficiente": True, "vol_diaria": vol_d, "vol_anual": vol_d * math.sqrt(DIAS),
           "rend_anual": float(acum.iloc[-1] ** (DIAS / len(r)) - 1), "max_drawdown": float(dd.min()),
           "fecha_max_drawdown": str(dd.idxmin().date()), "drawdown_actual": float(dd.iloc[-1]),
           "peor_dia": float(r.min()), "fecha_peor_dia": str(r.idxmin().date()), "mejor_dia": float(r.max()), "var": {}}
    for nivel in NIVELES:
        q = float(np.quantile(r, 1 - nivel))
        cvar = float(r[r <= q].mean())
        z = {0.95: 1.6448536, 0.99: 2.3263479}[nivel]
        param = z * vol_d - float(r.mean())
        esc = math.sqrt(horizonte)
        out["var"][f"{int(nivel * 100)}"] = {
            "historico_1d": -q, "cvar_1d": -cvar, "parametrico_1d": param,
            "historico_h": -q * esc, "cvar_h": -cvar * esc,
            "historico_1d_mxn": -q * valor, "cvar_1d_mxn": -cvar * valor, "historico_h_mxn": -q * esc * valor}
    return out


def calcular(con, ajustes, ventana: int = 252, horizonte: int | None = None) -> dict:
    cart = servicios.cartera_actual(con, ajustes)
    pos = [p for p in cart.get("posiciones") or [] if p.get("valor_mxn")]
    valor = float(cart.get("valor_total") or 0)
    if not pos or valor <= 0:
        return {"suficiente": False, "motivo": "Sin posiciones valuadas: registre una captura del portal."}
    ins = mercado.instrumentos(con)
    pesos = pd.Series({p["instrumento_id"]: p["valor_mxn"] / valor for p in pos})
    efectivo = max(0.0, 1 - float(pesos.sum()))
    h = horizonte or max(1, reto.sesiones_restantes() if reto.activo() else 20)
    precios = mercado.precios_mxn(con, ajustes, list(pesos.index), ajustados="splits")
    R = precios.ffill(limit=3).pct_change(fill_method=None).iloc[1:].tail(ventana)
    faltan = [i for i in pesos.index if i not in R.columns or R[i].notna().sum() < 30]
    usables = [i for i in pesos.index if i not in faltan]
    R = R[usables].dropna()
    r_cart = R.mul(pesos[usables], axis=1).sum(axis=1)     # el efectivo aporta 0 %
    m = metricas_serie(r_cart, valor, h)

    def grupo(campo, tr=lambda x: x):
        g: dict[str, float] = {}
        for i, w in pesos.items():
            k = tr(ins.get(i, {}).get(campo) or "sin dato")
            g[k] = g.get(k, 0.0) + float(w)
        return dict(sorted(g.items(), key=lambda kv: -kv[1]))
    expo = {"emisora": {(ins.get(i, {}).get("clave_operable") or i): float(w) for i, w in pesos.sort_values(ascending=False).items()},
            "mercado": grupo("mercado_operable"), "clase": grupo("clase"),
            "moneda_subyacente": grupo("moneda_referencia"), "efectivo": efectivo}
    contrib = {}
    if len(R) >= 30:
        cov = R.cov()
        w = pesos[usables]
        var_c = float(w @ cov @ w)
        if var_c > 0:
            mrc = cov @ w
            contrib = {(ins.get(i, {}).get("clave_operable") or i): float(w[i] * mrc[i] / var_c) for i in usables}
    hhi = float((pesos ** 2).sum())
    mayor = pesos.idxmax()
    est = [_choque(f"{ins.get(mayor, {}).get('clave_operable') or mayor} −{int(c * 100)} %", {mayor: -c}, pesos, valor)
           for c in (0.10, 0.20)]
    usd = [i for i in pesos.index if ins.get(i, {}).get("moneda_referencia") == "USD"]
    est.append(_choque("Peso se aprecia 5 % frente al dólar (afecta al SIC)", {i: -0.05 for i in usd}, pesos, valor))
    est.append(_choque("Todas las posiciones −10 %", {i: -0.10 for i in pesos.index}, pesos, valor))
    if m.get("suficiente"):
        for n in (5, 20):
            acum = (1 + r_cart).rolling(n).apply(np.prod, raw=True) - 1
            peor = acum.dropna()
            if len(peor):
                est.append({"escenario": f"Peor tramo histórico de {n} sesiones (hasta {peor.idxmin().date()})",
                            "cambio": float(peor.min()), "cambio_mxn": float(peor.min()) * valor, "tipo": "histórico"})
        vol = escenarios.estres_volatilidad(r_cart, 2.0, 0.95)
        if vol.get("var_estres") is not None:
            est.append({"escenario": "Volatilidad ×2 (VaR 95 % de un día)", "cambio": -vol["var_estres"],
                        "cambio_mxn": -vol["var_estres"] * valor, "tipo": "estrés"})
    return {"suficiente": bool(m.get("suficiente")), "valor_mxn": valor, "fuente_cartera": cart.get("fuente"),
            "metricas": m, "exposicion": expo, "contribucion_riesgo": contrib,
            "concentracion": {"hhi": hhi, "emisoras_efectivas": 1 / hhi if hhi else None, "mayor": ins.get(mayor, {}).get("clave_operable") or mayor,
                              "peso_mayor": float(pesos.max())},
            "escenarios": est, "horizonte_sesiones": h, "sin_historia": faltan,
            "supuestos": _supuestos(ventana, int(m.get("n", 0)), str(R.index[0].date()) if len(R) else None,
                                    str(R.index[-1].date()) if len(R) else None, h),
            "nota": "Descripción del riesgo con datos pasados; no es una recomendación ni una promesa."}


def _choque(nombre: str, choques: dict[str, float], pesos: pd.Series, valor: float) -> dict:
    cambio = float(sum(pesos.get(i, 0.0) * c for i, c in choques.items()))
    return {"escenario": nombre, "cambio": cambio, "cambio_mxn": cambio * valor, "tipo": "hipotético"}
