"""Construcción, validación y explicación de las dos propuestas de portafolio.

Función objetivo (documentada y reproducible):
    maximizar  μᵀw − λ·wᵀΣw − Σ c_i·|w_i − w_actual_i| − γ·‖w‖²
    sujeto a   Σw = 1, 0 ≤ w_i ≤ tope_i, restricciones de grupo (deuda mínima, exposición USD máxima)
  μ: media de rendimientos diarios en MXN con contracción James-Stein (ShrunkMu), ajustada por escenario.
  Σ: covarianza Ledoit-Wolf.   λ: aversión al riesgo del perfil.   c_i: comisión + IVA + spread estimado
  (amortizado en el horizonte).   γ: regularización L2 que reduce la sensibilidad de los pesos al ruido.

Validación: walk-forward (entrenamiento 504 sesiones, prueba 63) sin información futura, con la
preselección de acciones dentro de cada ventana y costos de rotación descontados. Se compara contra
una cartera simple 1/N del mismo universo y contra mantener la cartera actual.

Nada de esto es una predicción: los rendimientos esperados son estimaciones inciertas.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata as md
import math
import sqlite3
from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import sklearn.base as skb
import sklearn.feature_selection as skf
import sklearn.utils.validation as skv
from skfolio import Portfolio, RiskMeasure
from skfolio.model_selection import WalkForward, cross_val_predict
from skfolio.moments import BaseMu, LedoitWolf, ShrunkMu
from skfolio.optimization import EqualWeighted, MeanRisk, ObjectiveFunction
from skfolio.prior import EmpiricalPrior
from sklearn.pipeline import Pipeline

from . import mercado, reto, vigencia
from .config import CONFIG_DIR, Ajustes

CLASES_ACCIONES = ("accion", "reit")
CLASES_MIXTA = ("accion", "reit", "etf", "fibra", "fondo_deuda", "fondo_renta_variable", "fondo_multiactivo")
RENTA_VARIABLE = ("accion", "reit", "fibra", "fondo_renta_variable")
DIAS = 252
MIN_ACTIVOS = 5
ESCENARIOS = {  # ajuste anual al rendimiento esperado por tipo de activo (supuesto explícito)
    "base": {"rv": 0.0, "deuda": 0.0},
    "adverso": {"rv": -0.05, "deuda": -0.01},
    "favorable": {"rv": 0.03, "deuda": 0.0},
}


class PreseleccionAcciones(skf.SelectorMixin, skb.BaseEstimator):
    """Conserva las k acciones con mayor razón rendimiento/volatilidad de la ventana de entrenamiento
    y todos los instrumentos que no son acciones. Se ajusta dentro de cada ventana (sin mirar el futuro)."""

    def __init__(self, k: int = 30, acciones: tuple = (), mxn: tuple = (), min_mxn: int = 0):
        self.k = k
        self.acciones = acciones
        self.mxn = mxn          # acciones con exposición en pesos
        self.min_mxn = min_mxn  # mínimo de ellas a conservar para que el tope de exposición USD sea alcanzable

    def fit(self, X, y=None):
        nombres = list(X.columns) if hasattr(X, "columns") else None
        X = skv.validate_data(self, X)
        nombres = nombres or [str(i) for i in range(X.shape[1])]
        es_acc = np.array([n in set(self.acciones) for n in nombres])
        razon = X.mean(axis=0) / np.maximum(X.std(axis=0), 1e-12)
        keep = ~es_acc
        idx = np.where(es_acc)[0]
        if len(idx):
            orden = idx[np.argsort(-razon[idx])]
            keep[orden[: int(self.k)]] = True
            en_mxn = [i for i in orden if nombres[i] in set(self.mxn)]
            faltan = int(self.min_mxn) - sum(1 for i in en_mxn if keep[i])
            for i in en_mxn:  # las mejores en pesos que no entraron, hasta cubrir el mínimo
                if faltan <= 0:
                    break
                if not keep[i]:
                    keep[i] = True
                    faltan -= 1
        self.to_keep_ = keep
        return self

    def _get_support_mask(self):
        skv.check_is_fitted(self)
        return self.to_keep_


def _fondos_meta() -> dict[str, dict]:
    ruta = CONFIG_DIR / "fondos_actinver.csv"
    return {f"FONDO:{r['clave']}": r for r in csv.DictReader(ruta.open(encoding="utf-8"))}


def _moneda_exposicion(ins: dict, fondos: dict) -> str:
    if ins["id"] in fondos:
        e = fondos[ins["id"]]["exposicion_divisa"]
        return "USD" if e.startswith(("USD", "EUR", "Global")) else "MXN"
    return ins.get("moneda_referencia") or "MXN"


def _clase_costo(ins: dict) -> str:
    if ins["clase"].startswith("fondo"):
        return "fondo"
    if ins["clase"] in ("accion", "reit"):
        return "accion_sic" if ins["mercado_operable"] == "BMV-SIC" else "accion_bmv"
    return ins["clase"] if ins["clase"] in ("etf", "fibra") else "accion_bmv"


def costo_unitario(ins: dict, ajustes: Ajustes) -> float:
    """Costo de operar un peso: comisión con IVA + spread estimado. Con el Reto activo, la comisión es la del
    simulador (0.10 % + IVA sobre toda orden, reglamento §8)."""
    c = ajustes["costos"]
    spread = c["spread_pct"].get(_clase_costo(ins), 0.003)
    if reto.activo() and reto.costo_operacion() is not None:
        return reto.costo_operacion() + spread
    if ins["clase"].startswith("fondo"):
        return 0.0  # compra/venta de fondos sin comisión explícita; el costo va implícito en el NAV
    return c["comision_pct"] * (1 + c["iva"]) + spread


def universo(con: sqlite3.Connection, ajustes: Ajustes, perfil: dict, tipo: str,
             cotiz: dict | None = None) -> tuple[list[dict], list[dict], pd.DataFrame]:
    """Aplica los filtros en orden y devuelve (elegibles, excluidos con motivo, precios MXN)."""
    clases = CLASES_ACCIONES if tipo == "acciones" else CLASES_MIXTA
    ins = mercado.instrumentos(con)
    fondos = _fondos_meta()
    candidatos, excluidos = [], []
    excl_usuario = set(perfil.get("excluir") or []) | set((reto.config().get("reglas") or {}).get("instrumentos_prohibidos") or [])
    simulador = {r[0] for r in con.execute("SELECT id FROM universo_simulador")} if reto.activo() else set()
    for i in ins.values():
        if i["clase"] not in clases:
            continue
        motivo = None
        if simulador and i["id"] not in simulador:
            motivo = "No aparece en la lista importada del simulador del Reto"
        elif i["estado"] == "excluido":
            motivo = "Excluido por regla (apalancado o inverso)"
        elif i["estado"] != "activo":
            motivo = f"Estado del instrumento: {i['estado']} — {i['detalle_verificacion']}"
        elif i["id"] in excl_usuario:
            motivo = "Excluido por el usuario"
        elif perfil.get("mercado_acciones", "ambos") == "nacionales" and i["mercado_operable"] == "BMV-SIC":
            motivo = "Excluido por su elección de mercado: solo emisoras nacionales"
        elif perfil.get("mercado_acciones", "ambos") == "extranjeras" and i["mercado_operable"] != "BMV-SIC":
            motivo = "Excluido por su elección de mercado: solo emisoras extranjeras (SIC)"
        elif i["clase"] == "etf" and "por confirmar" in (i["detalle_verificacion"] or "") and not perfil.get(
                "incluir_etf_por_confirmar", True):
            motivo = "ETF con disponibilidad en el SIC por confirmar"
        elif i["id"] in fondos:
            v = fondos[i["id"]]["ventana_venta"]
            if v == "anual" and float(perfil["horizonte_anios"]) < 1.5:
                motivo = "Fondo con ventana de venta anual: incompatible con el horizonte"
            elif v == "trimestral" and float(perfil["horizonte_anios"]) < 1:
                motivo = "Fondo con ventana de venta trimestral: incompatible con el horizonte"
        if motivo:
            excluidos.append({"id": i["id"], "motivo": motivo})
        else:
            candidatos.append(i)
    ids = [c["id"] for c in candidatos]
    # El Reto no paga dividendos (reglamento §13): se estima con precio sin ajustar, que es lo que valúa el simulador.
    ajustados = not (reto.activo() and not (reto.config().get("reglas") or {}).get("dividendos_reproducidos", True))
    precios = mercado.precios_mxn(con, ajustes, ids, ajustados=ajustados)
    cotiz = cotiz if cotiz is not None else mercado.cotizaciones(con, ajustes, ids)
    minimo = int(ajustes["optimizacion"]["historia_min_sesiones"])
    elegibles = []
    for c in candidatos:
        q = cotiz.get(c["id"], {})
        n = int(precios[c["id"]].notna().sum()) if c["id"] in precios.columns else 0
        if q.get("estado") in ("sin_datos", None) or n == 0:
            excluidos.append({"id": c["id"], "motivo": "Sin datos suficientes (sin precios)"})
        elif q.get("estado") == "vencido":
            excluidos.append({"id": c["id"], "motivo": f"Dato vencido (último {q.get('fecha')}); se suspende su uso"})
        elif n < minimo:
            excluidos.append({"id": c["id"], "motivo": f"Sin datos suficientes ({n} de {minimo} sesiones)"})
        else:
            elegibles.append({**c, "exposicion": _moneda_exposicion(c, fondos), "sesiones": n,
                              "vigencia": q.get("estado"), "precio_mxn": q.get("precio_mxn"),
                              "fecha_dato": q.get("fecha"), "ventana_venta": fondos.get(c["id"], {}).get("ventana_venta", "diaria"),
                              "liquidacion": fondos.get(c["id"], {}).get("liquidacion", "T+2 (mercado)")})
    return elegibles, excluidos, precios


def rendimientos(precios: pd.DataFrame, ids: list[str], ventana: int | None = None) -> pd.DataFrame:
    p = precios[ids].ffill(limit=3)
    r = p.pct_change(fill_method=None)
    inicio = max(p[c].first_valid_index() for c in ids)
    r = r.loc[r.index > inicio].dropna(how="any")
    return r.iloc[-ventana:] if ventana else r


def _min_mxn(perfil: dict, elegibles: list[dict], tope: float) -> int:
    """Acciones en pesos que la preselección debe conservar para que «USD <= máximo» tenga solución con el tope."""
    usd_max = float(perfil.get("max_exposicion_usd", 1.0))
    if usd_max >= 1 or tope <= 0:
        return 0
    otras_mxn = [e for e in elegibles if e["exposicion"] != "USD" and e["clase"] not in CLASES_ACCIONES]
    if otras_mxn:  # fondos/ETF en pesos también cubren la parte en MXN
        return 0
    return math.ceil((1 - usd_max) / tope) + 2


def _grupos(elegibles: list[dict]) -> dict[str, list[str]]:
    g = {}
    for e in elegibles:
        grupos = ["USD" if e["exposicion"] == "USD" else "MXN"]
        grupos.append("Deuda" if e["clase"] == "fondo_deuda" else "NoDeuda")
        grupos.append("Iliquido" if e["ventana_venta"] in ("anual", "trimestral") else "Liquido")
        g[e["id"]] = grupos
    return g


def _restricciones(tipo: str, perfil: dict, ajustes: Ajustes, elegibles: list[dict], lente: str = "ajuste") -> list[str]:
    params = ajustes["perfiles"][perfil["riesgo"]]
    r = []
    usd_max = float(perfil.get("max_exposicion_usd", 1.0))
    hay_mxn = any(e["exposicion"] != "USD" for e in elegibles)
    hay_usd = any(e["exposicion"] == "USD" for e in elegibles)
    if usd_max < 1 and hay_mxn and hay_usd:
        r.append(f"USD <= {usd_max}")
    if tipo == "mixta" and lente == "ajuste":  # la lente de máximo rendimiento no impone deuda mínima
        min_deuda = float(params["min_deuda_mixta"])
        h = float(perfil["horizonte_anios"])
        if h < 3 and not reto.activo():  # horizonte corto fuera del Reto: más estabilidad
            min_deuda = max(min_deuda, 0.5 if h < 1.5 else 0.35)
        if min_deuda > 0 and any(e["clase"] == "fondo_deuda" for e in elegibles):
            r.append(f"Deuda >= {min_deuda}")
        if any(e["ventana_venta"] != "diaria" for e in elegibles):
            r.append("Iliquido <= 0.15")
    return r


def _parametros_lente(lente: str, perfil: dict, ajustes: Ajustes) -> tuple[float, float]:
    """(aversión al riesgo λ, tope por activo) de cada lente.
    ajuste      -> perfil del inversionista (λ del perfil, tope del perfil, limitado por la regla del Reto).
    rendimiento -> máximo rendimiento esperado (λ bajo explícito; tope que garantiza ≥ 5 emisoras)."""
    rc = reto.config() if reto.activo() else {}
    tope_reto = (rc.get("reglas") or {}).get("max_peso_emisora") or 1.0
    if lente == "rendimiento":
        p = rc.get("propuestas") or {}
        return float(p.get("aversion_lente_rendimiento", 0.5)), min(float(p.get("tope_lente_rendimiento", 0.20)), tope_reto)
    return float(ajustes["perfiles"][perfil["riesgo"]]["aversion_riesgo"]), min(float(perfil.get("max_peso_activo", 0.12)), tope_reto)


class MuFijo(BaseMu):
    """μ precalculado (contracción James-Stein sobre TODO el universo) para que la propuesta final, su
    rendimiento esperado y la comparación con la cartera actual usen exactamente el mismo estimador."""

    def __init__(self, mu=None):
        self.mu = mu

    def fit(self, X, y=None, **_):
        X = np.asarray(X)
        self.mu_ = np.asarray(self.mu, dtype=float)
        if self.mu_.shape[0] != X.shape[1]:
            raise ValueError("MuFijo: dimensión de μ distinta al número de activos")
        return self


def mu_global(X: pd.DataFrame) -> pd.Series:
    return pd.Series(ShrunkMu().fit(X.values).mu_, index=X.columns)


def _ajuste_final(tipo: str, perfil: dict, ajustes: Ajustes, elegibles_l: list[dict], previos: dict, X: pd.DataFrame,
                  lente: str, aversion_mult: float = 1.0) -> tuple[pd.Series, pd.Series]:
    """Preselección y optimización con μ global. Devuelve (pesos, μ usado)."""
    mu = mu_global(X)
    sd = X.std().replace(0, np.nan)
    acciones = [e["id"] for e in elegibles_l if e["clase"] in CLASES_ACCIONES]
    k = int(ajustes["optimizacion"]["max_activos"]) * 2
    razon = (mu[acciones] / sd[acciones]).dropna() if acciones else pd.Series(dtype=float)
    top = set(razon.nlargest(k).index)
    mxn = [i for i in razon.sort_values(ascending=False).index if not any(
        e["id"] == i and e["exposicion"] == "USD" for e in elegibles_l)]
    faltan = _min_mxn(perfil, elegibles_l, _parametros_lente(lente, perfil, ajustes)[1]) - sum(1 for i in mxn if i in top)
    for i in mxn:  # conservar suficientes acciones en pesos para respetar el tope de exposición en dólares
        if faltan <= 0:
            break
        if i not in top:
            top.add(i)
            faltan -= 1
    cols = [c for c in X.columns if c not in acciones or c in top]
    sub = [e for e in elegibles_l if e["id"] in cols]
    modelo = _modelo(tipo, perfil, ajustes, sub, {k2: v for k2, v in previos.items() if k2 in cols},
                     aversion_mult=aversion_mult, k_acciones=len(cols), lente=lente, mu_fijo=mu[cols].values)
    modelo.fit(X[cols])
    opt = modelo.named_steps["optimizacion"]
    return pd.Series(opt.weights_, index=list(opt.feature_names_in_)), mu


def _modelo(tipo: str, perfil: dict, ajustes: Ajustes, elegibles: list[dict], previos: dict[str, float],
            aversion_mult: float = 1.0, k_acciones: int | None = None, lente: str = "ajuste",
            mu_fijo: np.ndarray | None = None) -> Pipeline:
    aversion, tope = _parametros_lente(lente, perfil, ajustes)
    topes = {e["id"]: (min(tope, 0.10) if e["ventana_venta"] != "diaria" else tope) for e in elegibles}
    if tipo == "mixta" and lente == "ajuste":  # los fondos de deuda son vehículos diversificados: tope mayor
        tope_reto = (reto.config().get("reglas") or {}).get("max_peso_emisora") or 1.0 if reto.activo() else 1.0
        for e in elegibles:
            if e["clase"] == "fondo_deuda" and e["ventana_venta"] == "diaria":
                topes[e["id"]] = min(max(tope, 0.35), tope_reto)
            elif e["clase"] in ("etf", "fondo_renta_variable", "fondo_multiactivo"):
                topes[e["id"]] = min(max(tope, 0.25), tope_reto)
    n = len(elegibles)
    if sum(topes.values()) < 1:  # universo pequeño: relajar topes para que exista solución
        topes = {k: max(v, 1.0 / max(n, 1) + 0.01) for k, v in topes.items()}
    acciones = tuple(e["id"] for e in elegibles if e["clase"] in CLASES_ACCIONES)
    k = k_acciones or int(ajustes["optimizacion"]["max_activos"]) * 2
    opt = MeanRisk(
        objective_function=ObjectiveFunction.MAXIMIZE_UTILITY,
        risk_measure=RiskMeasure.VARIANCE,
        risk_aversion=aversion * aversion_mult,  # misma unidad que μ y Σ diarios
        prior_estimator=EmpiricalPrior(mu_estimator=MuFijo(mu_fijo) if mu_fijo is not None else ShrunkMu(),
                                       covariance_estimator=LedoitWolf()),
        max_weights=topes,
        # costo único amortizado en el horizonte (skfolio lo descuenta por observación diaria)
        transaction_costs={e["id"]: costo_unitario(e, ajustes) / (max(float(perfil["horizonte_anios"]), 5 / DIAS) * DIAS)
                           for e in elegibles},
        previous_weights=(previos or None) if lente == "ajuste" else None,
        groups=_grupos(elegibles),
        # estabiliza pesos ante ruido en μ; la lente de máximo rendimiento no penaliza concentración
        l2_coef=float(ajustes["optimizacion"].get("l2_regularizacion", 0.0)) if lente == "ajuste" else 0.0,
        linear_constraints=_restricciones(tipo, perfil, ajustes, elegibles, lente) or None,
        # el respaldo conserva las restricciones del perfil: nunca se relajan en silencio
        # el respaldo conserva las restricciones del perfil; solo si el universo las hace imposibles se relajan, y la
        # propuesta lo declara en «riesgos» como NO CUMPLE SU PERFIL
        fallback=[MeanRisk(objective_function=ObjectiveFunction.MINIMIZE_RISK, max_weights=topes, groups=_grupos(elegibles),
                           linear_constraints=_restricciones(tipo, perfil, ajustes, elegibles, lente) or None),
                  MeanRisk(objective_function=ObjectiveFunction.MINIMIZE_RISK, max_weights=topes)],
        raise_on_failure=True,
    )
    # set_output por instancia: la configuración global de sklearn es por hilo y el servidor calcula en otro hilo
    mxn = tuple(e["id"] for e in elegibles if e["clase"] in CLASES_ACCIONES and e["exposicion"] != "USD")
    return Pipeline([("preseleccion", PreseleccionAcciones(k=k, acciones=acciones, mxn=mxn,
                                                           min_mxn=_min_mxn(perfil, elegibles, tope))),
                     ("optimizacion", opt)]).set_output(transform="pandas")


def _ajustar_escenario(X: pd.DataFrame, elegibles: dict, escenario: str) -> pd.DataFrame:
    a = ESCENARIOS.get(escenario, ESCENARIOS["base"])
    X = X.copy()
    for c in X.columns:
        cl = elegibles[c]["clase"]
        delta = a["rv"] if cl in RENTA_VARIABLE or cl == "etf" else (a["deuda"] if cl == "fondo_deuda" else 0.0)
        X[c] = X[c] + delta / DIAS
    return X


def _metricas(ret: pd.Series) -> dict:
    ret = ret.dropna()
    if len(ret) < 20:
        return {}
    ra = float((1 + ret).prod() ** (DIAS / len(ret)) - 1)
    vol = float(ret.std() * math.sqrt(DIAS))
    acum = (1 + ret).cumprod()
    dd = float((acum / acum.cummax() - 1).min())
    cvar = float(-ret[ret <= ret.quantile(0.05)].mean())
    return {"rend_anual": ra, "volatilidad": vol, "sharpe": (ra / vol) if vol > 0 else None,
            "max_caida": dd, "cvar95_diario": cvar, "sesiones": int(len(ret)),
            "desde": ret.index[0].date().isoformat(), "hasta": ret.index[-1].date().isoformat()}


def _walk_forward(modelo: Pipeline, X: pd.DataFrame, ajustes: Ajustes, elegibles: dict) -> tuple[pd.Series, list]:
    o = ajustes["optimizacion"]
    cv = WalkForward(train_size=int(o["walk_forward_entrenamiento"]), test_size=int(o["walk_forward_prueba"]))
    pred = cross_val_predict(modelo, X, cv=cv)
    series, previo, rotaciones = [], None, []
    costos = pd.Series({c: costo_unitario(elegibles[c], ajustes) for c in X.columns})
    banda = float(o["banda_rebalanceo_pp"]) / 100
    for p in pred.portfolios:
        w = pd.Series(p.weights, index=list(p.assets)).reindex(X.columns).fillna(0)
        if previo is not None:  # misma regla que en la propuesta: no mover pesos por diferencias menores a la banda
            w = w.where((w - previo).abs() >= banda, previo)
            w = w / w.sum()
        obs = pd.to_datetime(p.observations)
        r = X.loc[obs].mul(w, axis=1).sum(axis=1)  # rendimiento bruto; los costos se descuentan abajo una sola vez
        giro = float((w - previo).abs().sum()) if previo is not None else float(w.abs().sum())
        costo = float(((w - (previo if previo is not None else 0)).abs() * costos).sum())
        r.iloc[0] -= costo
        rotaciones.append(giro)
        series.append(r)
        previo = w
    return pd.concat(series), rotaciones


def _serie_pesos(X: pd.DataFrame, pesos: pd.Series) -> pd.Series:
    w = pesos.reindex(X.columns).fillna(0)
    return X.mul(w, axis=1).sum(axis=1)


def _explicar_activo(i: str, w: float, X: pd.DataFrame, pesos: pd.Series, elegibles: dict, contrib: float) -> list[str]:
    e = elegibles[i]
    motivos = []
    r = X[i]
    ra, vol = r.mean() * DIAS, r.std() * math.sqrt(DIAS)
    otros = [c for c in pesos.index if c != i and pesos[c] > 0]
    corr = float(X[otros].corrwith(r).mean()) if otros else float("nan")
    if e["clase"] == "fondo_deuda":
        motivos.append(f"Estabiliza la cartera: volatilidad histórica {vol:.1%} anual ({e['categoria']}).")
    elif not math.isnan(corr) and corr < 0.35:
        motivos.append(f"Diversifica: correlación media {corr:.2f} con el resto de la propuesta.")
    if ra > 0 and vol > 0:
        motivos.append(f"Relación rendimiento/riesgo histórica {ra / vol:.2f} (rendimiento {ra:.1%}, volatilidad {vol:.1%}; "
                       f"no es una promesa).")
    motivos.append(f"Aporta {contrib:.0%} del riesgo total con {w:.0%} del peso.")
    if e["exposicion"] == "USD":
        motivos.append("Exposición al dólar: diversifica frente al peso, añade riesgo cambiario.")
    return motivos[:3]


def _contribucion_riesgo(X: pd.DataFrame, pesos: pd.Series) -> pd.Series:
    w = pesos.reindex(X.columns).fillna(0).values
    cov = np.cov(X.values, rowvar=False)
    var = float(w @ cov @ w)
    if var <= 0:
        return pd.Series(0.0, index=X.columns)
    return pd.Series(w * (cov @ w) / var, index=X.columns)


def _escenarios(X: pd.DataFrame, pesos: pd.Series, horizonte: float, elegibles: dict) -> dict:
    rp = _serie_pesos(X, pesos)
    mu, sig = float(rp.mean() * DIAS), float(rp.std() * math.sqrt(DIAS))
    h = max(horizonte, 0.25)
    z = 1.2816
    g = (mu - sig ** 2 / 2) * h
    peor21 = float((1 + rp).rolling(21).apply(np.prod, raw=True).min() - 1)
    peor63 = float((1 + rp).rolling(63).apply(np.prod, raw=True).min() - 1)
    acum = (1 + rp).cumprod()
    rv = sum(w for k, w in pesos.items() if elegibles[k]["clase"] in RENTA_VARIABLE or elegibles[k]["clase"] == "etf")
    usd = sum(w for k, w in pesos.items() if elegibles[k]["exposicion"] == "USD")
    return {
        "horizonte_anios": h,
        "favorable_p90": math.exp(g + z * sig * math.sqrt(h)) - 1,
        "central_p50": math.exp(g) - 1,
        "adverso_p10": math.exp(g - z * sig * math.sqrt(h)) - 1,
        "peor_mes_historico": peor21, "peor_trimestre_historico": peor63,
        "max_caida_historica": float((acum / acum.cummax() - 1).min()),
        "estres_hipotetico": {
            "supuesto": "Renta variable −30 %, deuda 0 %, peso se deprecia 15 % frente al dólar",
            "impacto": _estres(pesos, elegibles),
            "renta_variable": rv, "exposicion_usd": usd,
        },
        "nota": "Percentiles bajo supuesto log-normal con parámetros históricos; no son pronósticos.",
    }


def _estres(pesos: pd.Series, elegibles: dict, choque_rv: float = -0.30, choque_fx: float = 0.15) -> float:
    """Σ w_i·[(1 + choque del activo)·(1 + choque cambiario si está expuesto al dólar) − 1]."""
    total = 0.0
    for k, w in pesos.items():
        e = elegibles[k]
        activo = choque_rv if (e["clase"] in RENTA_VARIABLE or e["clase"] == "etf") else 0.0
        fx = choque_fx if e["exposicion"] == "USD" else 0.0
        total += w * ((1 + activo) * (1 + fx) - 1)
    return float(total)


def _puntuar(m: dict, pesos: pd.Series, elegibles: dict, ajustes: Ajustes, perfil: dict, costo_cambio: float,
             rotacion: float) -> dict:
    pp = ajustes["puntuacion"]
    vol_obj = float(ajustes["perfiles"][perfil["riesgo"]]["vol_objetivo"])
    w = pesos[pesos > 0]
    n_eff = 1 / float((w ** 2).sum()) if len(w) else 0
    liquida = sum(v for k, v in w.items() if elegibles[k]["ventana_venta"] == "diaria")
    calidad_map = {"vigente": 1.0, "retrasado": 0.7, "sintetico": 0.0}
    calidad = sum(v * calidad_map.get(elegibles[k]["vigencia"], 0) for k, v in w.items())
    sharpe = m.get("sharpe") or 0.0
    vol = m.get("volatilidad") or vol_obj * 2
    costo_total = costo_cambio + rotacion * 0.004
    c = {
        "rendimiento_ajustado": (np.clip((sharpe + 0.5) / 2.0, 0, 1) * 100,
                                 f"Sharpe fuera de muestra {sharpe:.2f} (sin tasa libre de riesgo)"),
        "riesgo": (np.clip(2 - vol / vol_obj, 0, 1) * 100,
                   f"Volatilidad fuera de muestra {vol:.1%} vs objetivo del perfil {vol_obj:.0%}"),
        "diversificacion": (min(n_eff / 10, 1) * 100, f"Número efectivo de posiciones {n_eff:.1f}; mayor peso {w.max():.0%}"),
        "liquidez": (liquida * 100, f"{liquida:.0%} del peso con liquidez diaria"),
        "costos": (np.clip(1 - costo_total / 0.02, 0, 1) * 100,
                   f"Costo estimado de ajuste {costo_cambio:.2%} + rotación histórica {rotacion:.0%} por rebalanceo"),
        "calidad_datos": (calidad * 100, f"{calidad:.0%} del peso con datos vigentes"),
    }
    total_w = sum(pp[k] for k in c)
    total = sum(pp[k] * c[k][0] for k in c) / total_w
    return {"total": round(float(total), 1),
            "criterios": [{"criterio": k, "puntos": round(float(v[0]), 1), "peso": round(pp[k] / total_w, 3),
                           "explicacion": v[1]} for k, v in c.items()]}


def _riesgos(pesos: pd.Series, elegibles: dict, m: dict, esc: dict, excluidos: list, perfil: dict) -> list[str]:
    w = pesos[pesos > 0].sort_values(ascending=False)
    out = []
    top3 = float(w.iloc[:3].sum())
    out.append(f"Concentración: las 3 mayores posiciones suman {top3:.0%} (mayor: {w.index[0]} {w.iloc[0]:.0%}).")
    usd = sum(v for k, v in w.items() if elegibles[k]["exposicion"] == "USD")
    out.append(f"Riesgo cambiario: {usd:.0%} expuesto al dólar u otras divisas; una apreciación del peso reduce su valor en MXN.")
    usd_max = float(perfil.get("max_exposicion_usd", 1.0))
    if usd > usd_max + 0.005 and perfil.get("mercado_acciones", "ambos") != "extranjeras":
        out.insert(0, f"NO CUMPLE SU PERFIL: {usd:.0%} en dólares frente al máximo de {usd_max:.0%}; el universo disponible no "
                      "tiene suficientes instrumentos en pesos con precio. Amplíe el universo o ajuste el máximo en «Reto y perfil».")
    if m.get("sesiones") and m["sesiones"] < 126:
        out.append(f"Validación corta: solo {m['sesiones']} sesiones fuera de muestra (menos de medio año); la puntuación "
                   "no se puede verificar bien con los datos actuales.")
    if m.get("max_caida") is not None:
        out.append(f"Caída máxima en la validación fuera de muestra: {m['max_caida']:.0%}; "
                   f"peor trimestre histórico con estos pesos: {esc['peor_trimestre_historico']:.0%}.")
    ilq = sum(v for k, v in w.items() if elegibles[k]["ventana_venta"] != "diaria")
    if ilq > 0:
        out.append(f"Liquidez: {ilq:.0%} en fondos con ventana de venta no diaria.")
    retr = [k for k in w.index if elegibles[k]["vigencia"] == "retrasado"]
    if retr:
        out.append(f"Datos retrasados en {len(retr)} instrumento(s): {', '.join(retr[:5])}.")
    out.append("Modelo: el rendimiento esperado se estima con historia reciente y es muy incierto; "
               "pequeños cambios en los datos pueden mover los pesos.")
    return out


def consolidar_ordenes(pesos: pd.Series, peso_minimo: float, tope: float, min_emisoras: int) -> tuple[pd.Series, dict]:
    """Plan de órdenes ejecutable: una posición con menos peso que la banda de rebalanceo nunca llegaría a operarse (la
    boleta la dejaría en «mantener»), así que se elimina y su peso se reparte entre las demás en proporción a su peso,
    sin que ninguna pase de su límite (el tope por emisora, o su propio peso si el optimizador ya le dio más, como a un
    fondo de deuda obligatorio). Se conservan al menos las emisoras mínimas del Reto. Si el peso no cabe, no se elimina."""
    w = pesos[pesos > 0].astype(float).copy()
    w = w / w.sum()
    limite = np.maximum(w, tope)
    eliminadas = []
    while len(w) > int(min_emisoras) and w.min() < peso_minimo:
        k = w.idxmin()
        resto, lim = w.drop(k), limite.drop(k)
        if float((lim - resto).sum()) < float(w[k]) - 1e-12:
            break  # no cabe sin romper topes: se conserva
        extra = float(w[k])
        for _ in range(100):  # llenado por niveles con límites individuales
            libres = resto < lim - 1e-12
            if extra < 1e-12 or not libres.any():
                break
            add = extra * resto[libres] / resto[libres].sum()
            nuevo = np.minimum(resto[libres] + add, lim[libres])
            extra -= float((nuevo - resto[libres]).sum())
            resto[libres] = nuevo
        eliminadas.append({"id": k, "peso": round(float(w[k]), 4)})
        w, limite = resto / resto.sum(), lim
    info = {"posiciones": int(len(w)), "eliminadas": eliminadas, "peso_minimo": peso_minimo, "tope": tope,
            "criterio": (f"Cada posición pesa al menos {peso_minimo:.0%} (la banda de rebalanceo), porque una orden menor "
                         f"no se ejecutaría; mínimo {min_emisoras} emisoras y tope de {tope:.0%} por emisora.")}
    return w.reindex(pesos.index).fillna(0.0), info


def respetar_usd(pesos: pd.Series, usd: set, usd_max: float, tope: float) -> pd.Series:
    """Si el reparto posterior (consolidación de órdenes) dejó la exposición en dólares sobre el máximo del perfil,
    reduce en proporción las posiciones en USD y pasa el excedente a las de pesos sin rebasar su tope."""
    w = pesos.copy()
    en_usd = [k for k in w.index if k in usd and w[k] > 0]
    en_mxn = [k for k in w.index if k not in usd and w[k] > 0]
    exceso = float(w[en_usd].sum()) - usd_max
    if exceso <= 1e-9 or not en_mxn:
        return w
    capacidad = (np.maximum(w[en_mxn], tope) - w[en_mxn]).clip(lower=0)
    mover = min(exceso, float(capacidad.sum()))
    if mover <= 0:
        return w
    w[en_usd] *= 1 - mover / float(w[en_usd].sum())
    w[en_mxn] += mover * capacidad / float(capacidad.sum())
    return w


def _asignacion_discreta(pesos: pd.Series, elegibles: dict, capital: float) -> tuple[list[dict], float]:
    filas, usado = [], 0.0
    for k, w in pesos[pesos > 0].sort_values(ascending=False).items():
        px = elegibles[k].get("precio_mxn")
        monto = w * capital
        if px and px > 0:
            titulos = math.floor(monto / px)
            real = titulos * px
        else:
            titulos, real = None, monto
        usado += real
        filas.append({"id": k, "clave_operable": elegibles[k]["clave_operable"], "clase": elegibles[k]["clase"],
                      "peso": round(float(w), 4), "monto_objetivo": round(monto, 2), "precio_mxn": px,
                      "fecha_precio": elegibles[k].get("fecha_dato"), "titulos": titulos, "monto_estimado": round(real, 2)})
    return filas, round(capital - usado, 2)


def cambios(pesos: pd.Series, elegibles: dict, cartera_actual: dict, capital: float, ajustes: Ajustes,
            instrumentos: dict) -> dict:
    """Cambios sugeridos frente a las posiciones registradas, con banda de no-rebalanceo."""
    o, c = ajustes["optimizacion"], ajustes["costos"]
    total = max(float(cartera_actual.get("valor_total") or 0), 0)
    base = capital if capital > 0 else total
    actuales = {p["instrumento_id"]: p for p in cartera_actual.get("posiciones", [])}
    ids = sorted(set(actuales) | set(pesos[pesos > 0].index))
    filas, costo, impuesto = [], 0.0, 0.0
    for i in ids:
        pa = actuales.get(i)
        monto_act = float(pa["valor_mxn"] or 0) if pa else 0.0
        w_act = monto_act / base if base else 0.0
        w_obj = float(pesos.get(i, 0.0))
        delta_w = w_obj - w_act
        delta = w_obj * base - monto_act
        if abs(delta_w) * 100 < float(o["banda_rebalanceo_pp"]) or abs(delta) < float(o["monto_minimo_operacion"]):
            accion = "mantener"
            nota = "Diferencia dentro de la banda: no se sugiere operar"
        else:
            accion = "comprar" if delta > 0 else "vender"
            nota = ""
        ins = elegibles.get(i) or instrumentos.get(i, {"clase": "accion", "mercado_operable": "BMV"})
        cu = costo_unitario(ins, ajustes) if accion != "mantener" else 0.0
        imp = 0.0
        if accion == "vender" and pa and pa["cantidad"]:
            ganancia = abs(delta) - pa["costo_promedio"] * (abs(delta) / (pa["precio_mxn"] or 1))
            imp = max(ganancia, 0) * float(c["impuesto_ganancia"])
        costo += abs(delta) * cu
        impuesto += imp
        filas.append({"id": i, "clave_operable": (instrumentos.get(i) or {}).get("clave_operable", i),
                      "peso_actual": round(w_act, 4), "peso_objetivo": round(w_obj, 4), "delta_pp": round(delta_w * 100, 2),
                      "monto_mxn": round(delta, 2), "accion": accion, "costo_estimado": round(abs(delta) * cu, 2),
                      "impuesto_estimado": round(imp, 2), "nota": nota or ("No está en el universo elegible de esta propuesta"
                                                                           if i not in elegibles and w_obj == 0 else "")})
    filas.sort(key=lambda f: -abs(f["monto_mxn"]))
    return {"base_mxn": round(base, 2), "filas": filas, "costo_total": round(costo, 2),
            "impuesto_estimado": round(impuesto, 2), "costo_pct": (costo + impuesto) / base if base else 0.0,
            "operaciones": sum(1 for f in filas if f["accion"] != "mantener")}


def _huella_datos(X: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(X.round(10), index=True).values.tobytes()).hexdigest()[:16]


NOMBRES = {"acciones": "Solo acciones", "mixta": "Acciones + ETF + fondos"}
LENTES = {"rendimiento": "Máximo rendimiento esperado", "ajuste": "Ajuste a su perfil y cartera",
          "puntuacion": "Máxima puntuación"}
# Candidatos declarados ANTES de evaluar para la lente «Máxima puntuación»: multiplicador de aversión × tope por emisora.
CANDIDATOS_PUNTUACION = [(m, t) for t in (0.12, 0.20, 0.30) for m in (1.0, 3.0, 10.0, 30.0)]


def _buscar_puntuacion(tipo, perfil, ajustes, elegibles_l, elegibles, previos, X_esc, X_todo, cartera_actual, capital,
                       instrumentos) -> dict:
    """Elige la cartera candidata con mayor puntuación en la PRIMERA mitad de la validación fuera de muestra y reporta
    la puntuación de la SEGUNDA mitad, que no se usó para elegir (así la cifra no queda inflada por la selección)."""
    tope_reto = ((reto.config().get("reglas") or {}).get("max_peso_emisora") or 1.0) if reto.activo() else 1.0
    ids = list(elegibles)
    filas = []
    for mult, tope in CANDIDATOS_PUNTUACION:
        t = min(tope, tope_reto)
        pc = {**perfil, "max_peso_activo": t}
        try:
            modelo = _modelo(tipo, pc, ajustes, elegibles_l, {}, aversion_mult=mult, lente="ajuste")
            oos, rot = _walk_forward(modelo, X_todo, ajustes, elegibles)
            w, _ = _ajuste_final(tipo, pc, ajustes, elegibles_l, previos, X_esc, "ajuste", mult)
        except Exception as e:  # noqa: BLE001 - un candidato que no converge se informa y se descarta
            filas.append({"aversion_mult": mult, "tope": t, "error": str(e)[:100]})
            continue
        w = w.reindex(ids).fillna(0.0)
        w[w < 0.005] = 0.0
        w = w / w.sum()
        cmb = cambios(w, elegibles, cartera_actual, capital, ajustes, instrumentos)
        mitad = len(oos) // 2
        r_rot = float(np.mean(rot[1:]) if len(rot) > 1 else 0)
        sel = _puntuar(_metricas(oos.iloc[:mitad]), w, elegibles, ajustes, perfil, cmb["costo_pct"], r_rot)["total"]
        ver = _puntuar(_metricas(oos.iloc[mitad:]), w, elegibles, ajustes, perfil, cmb["costo_pct"], r_rot)["total"]
        filas.append({"aversion_mult": mult, "tope": t, "puntuacion_seleccion": sel, "puntuacion_verificacion": ver})
    validas = [f for f in filas if "error" not in f]
    if not validas:
        raise ValueError("Ningún candidato de la lente «Máxima puntuación» convergió")
    mejor = max(validas, key=lambda f: f["puntuacion_seleccion"])
    return {"elegido": mejor, "candidatos": filas,
            "nota": "Se eligió con la primera mitad de la validación; la puntuación de verificación (segunda mitad) no se "
                    "usó para elegir y es la cifra honesta. Una puntuación alta no garantiza rendimiento."}


def perfil_efectivo(perfil: dict) -> dict:
    """Con el Reto activo y horizonte automático, el horizonte son las sesiones que faltan para el cierre."""
    p = dict(perfil)
    if reto.activo() and (reto.config().get("propuestas") or {}).get("horizonte_auto") and p.get("horizonte_reto", True):
        p["horizonte_anios"] = round(reto.horizonte_anios(), 4)
        p["horizonte_origen"] = f"Reto: {reto.sesiones_restantes()} sesiones hasta el cierre"
    return p


def proponer(con: sqlite3.Connection, ajustes: Ajustes, perfil: dict, tipo: str, cartera_actual: dict,
             cotiz: dict | None = None, lente: str = "ajuste") -> dict:
    """Calcula una propuesta completa. Si los datos no alcanzan, devuelve estado «suspendida» con motivos."""
    creado = datetime.now(UTC).isoformat(timespec="seconds")
    perfil_usuario = perfil
    perfil = perfil_efectivo(perfil)
    elegibles_l, excluidos, precios = universo(con, ajustes, perfil, tipo, cotiz)
    fx = mercado.ultimo_fx(con, ajustes)
    base = {"tipo": tipo, "lente": lente, "clave": f"{tipo}_{lente}",
            "nombre": f"{NOMBRES[tipo]} · {LENTES[lente]}", "universo_nombre": NOMBRES[tipo], "lente_nombre": LENTES[lente],
            "calculado_en": creado, "perfil": perfil_usuario, "perfil_efectivo": perfil, "modo": ajustes.modo,
            "excluidos": excluidos, "fx": fx, "reto": reto.activo()}
    motivos_susp = []
    clases = CLASES_ACCIONES if tipo == "acciones" else CLASES_MIXTA
    hay_usd = any(i["moneda_referencia"] == "USD" and i["clase"] in clases and i["estado"] == "activo"
                  for i in mercado.instrumentos(con).values())
    if hay_usd and fx.get("estado") in ("vencido", "sin_datos"):
        motivos_susp.append(f"Tipo de cambio USD/MXN {fx.get('etiqueta', 'sin datos').lower()}: no se pueden valorar en MXN los activos en dólares.")
        elegibles_l = [e for e in elegibles_l if e["moneda_referencia"] != "USD"]
    if len(elegibles_l) < MIN_ACTIVOS:
        motivos_susp.append(f"Sin datos suficientes: {len(elegibles_l)} instrumentos elegibles (mínimo {MIN_ACTIVOS}). "
                            "Configure un proveedor de precios (pestaña Datos; ver README) o importe precios/valor "
                            "liquidativo desde «Mi cartera → Importar», y pulse «Actualizar datos».")
    if motivos_susp:
        return {**base, "estado": "suspendida", "motivos": motivos_susp}

    elegibles = {e["id"]: e for e in elegibles_l}
    ids = list(elegibles)
    o = ajustes["optimizacion"]
    X_todo = rendimientos(precios, ids)
    if len(X_todo) < int(o["walk_forward_entrenamiento"]) + int(o["walk_forward_prueba"]):
        return {**base, "estado": "suspendida",
                "motivos": [f"Sin datos suficientes: {len(X_todo)} sesiones comunes; se requieren "
                            f"{int(o['walk_forward_entrenamiento']) + int(o['walk_forward_prueba'])} para validar fuera de muestra."]}
    X = X_todo.iloc[-int(o["ventana_estimacion"]):]
    total_act = float(cartera_actual.get("valor_total") or 0)
    previos = {p["instrumento_id"]: (p["valor_mxn"] or 0) / total_act
               for p in cartera_actual.get("posiciones", []) if total_act > 0 and p["instrumento_id"] in elegibles}

    # 1) propuesta final (con escenario)
    X_esc = _ajustar_escenario(X, elegibles, perfil.get("escenario", "base"))
    lente_calc, mult_base, busqueda = lente, 1.0, None
    if lente == "puntuacion":
        busqueda = _buscar_puntuacion(tipo, perfil, ajustes, elegibles_l, elegibles, previos, X_esc, X_todo, cartera_actual,
                                      float(perfil.get("capital") or 0), mercado.instrumentos(con))
        perfil = {**perfil, "max_peso_activo": busqueda["elegido"]["tope"]}
        lente_calc, mult_base = "ajuste", busqueda["elegido"]["aversion_mult"]
    pesos, mu_esc = _ajuste_final(tipo, perfil, ajustes, elegibles_l, previos, X_esc, lente_calc, mult_base)
    pesos[pesos < 0.005] = 0.0
    maxa = int(o["max_activos"]) if tipo == "acciones" else int(o["max_activos"]) + 5
    if (pesos > 0).sum() > maxa:
        pesos[pesos.rank(ascending=False) > maxa] = 0.0
    pesos = pesos / pesos.sum()
    pesos = pesos.reindex(ids).fillna(0.0)
    min_emisoras = int(((reto.config() if reto.activo() else {}).get("reglas") or {}).get("min_emisoras") or 5)
    tope_lente = _parametros_lente(lente_calc, perfil, ajustes)[1]
    pesos, plan_ordenes = consolidar_ordenes(pesos, float(o["banda_rebalanceo_pp"]) / 100, tope_lente, min_emisoras)
    if any(e["exposicion"] != "USD" for e in elegibles_l):
        pesos = respetar_usd(pesos, {e["id"] for e in elegibles_l if e["exposicion"] == "USD"},
                             float(perfil.get("max_exposicion_usd", 1.0)), tope_lente)

    # 2) validación fuera de muestra (siempre con datos reales, sin ajuste de escenario)
    modelo_v = _modelo(tipo, perfil, ajustes, elegibles_l, {}, aversion_mult=mult_base, lente=lente_calc)
    oos, rot = _walk_forward(modelo_v, X_todo, ajustes, elegibles)
    m_modelo = _metricas(oos)
    ew = cross_val_predict(EqualWeighted(), X_todo, cv=WalkForward(train_size=int(o["walk_forward_entrenamiento"]),
                                                                   test_size=int(o["walk_forward_prueba"])))
    m_ew = _metricas(pd.Series(np.asarray(ew.returns), index=pd.to_datetime(ew.observations)))
    comparacion = [{"cartera": "Propuesta (validación fuera de muestra, neta de costos)", **m_modelo},
                   {"cartera": "Referencia simple 1/N (mismo universo)", **m_ew}]
    pesos_act = pd.Series(previos)
    if len(pesos_act) and pesos_act.sum() > 0:
        pa = pesos_act / pesos_act.sum()
        m_act = _metricas(_serie_pesos(X_todo.loc[oos.index], pa))  # mismo periodo que la validación
        comparacion.append({"cartera": "Mantener cartera actual (parte con historia en este universo)", **m_act,
                            "cobertura": round(float(pesos_act.sum()), 3)})

    # 3) sensibilidad: ventana y aversión al riesgo
    sens = []
    for etiqueta, ventana, mult in (("Ventana 2 años", 504, 1.0), ("Ventana 4 años", 1008, 1.0),
                                    ("Aversión ×0.5", None, 0.5), ("Aversión ×2", None, 2.0)):
        Xs = X_todo.iloc[-ventana:] if ventana else X
        if ventana and len(X_todo) < ventana:
            continue
        try:
            ps, _ = _ajuste_final(tipo, perfil, ajustes, elegibles_l, previos,
                                  _ajustar_escenario(Xs, elegibles, perfil.get("escenario", "base")), lente_calc, mult * mult_base)
            ps = ps.reindex(ids).fillna(0)
            dif = float((ps - pesos).abs().sum() / 2)
            sens.append({"variante": etiqueta, "cambio_pesos": round(dif, 3),
                         "top": [{"id": k, "peso": round(float(v), 3)} for k, v in ps.nlargest(5).items()]})
        except Exception as e:  # noqa: BLE001 - se informa, no se oculta
            sens.append({"variante": etiqueta, "error": str(e)[:120]})
    estabilidad = 1 - float(np.mean([s["cambio_pesos"] for s in sens if "cambio_pesos" in s] or [1]))

    contrib = _contribucion_riesgo(X, pesos)
    esc = _escenarios(X, pesos[pesos > 0], float(perfil["horizonte_anios"]), elegibles)
    capital = float(perfil.get("capital") or 0)
    asignacion, residuo = _asignacion_discreta(pesos, elegibles, capital)
    for a in asignacion:
        a["motivos"] = _explicar_activo(a["id"], a["peso"], X, pesos, elegibles, float(contrib.get(a["id"], 0)))
        a["contribucion_riesgo"] = round(float(contrib.get(a["id"], 0)), 4)
        a["vigencia"] = elegibles[a["id"]]["vigencia"]
    cmb = cambios(pesos, elegibles, cartera_actual, capital, ajustes, mercado.instrumentos(con))
    ops = [f for f in cmb["filas"] if f["accion"] != "mantener"]
    plan_ordenes.update({"total": len(ops), "compras": sum(f["accion"] == "comprar" for f in ops),
                         "ventas": sum(f["accion"] == "vender" for f in ops),
                         # SIC: el precio es referencia de la bolsa de origen; la boleta pide el del portal
                         "sin_precio": sum(1 for f in ops if f["accion"] != "mantener" and (not elegibles.get(f["id"])
                                           or elegibles[f["id"]].get("mercado_operable") == "BMV-SIC"
                                           or not elegibles[f["id"]].get("precio_mxn"))),
                         "costo_total": cmb["costo_total"]})
    punt = _puntuar(m_modelo, pesos, elegibles, ajustes, perfil, cmb["costo_pct"], float(np.mean(rot[1:]) if len(rot) > 1 else 0))
    if busqueda:
        punt["verificacion"] = busqueda["elegido"]["puntuacion_verificacion"]
        punt["seleccion"] = busqueda["elegido"]["puntuacion_seleccion"]
    fechas_dato = [elegibles[k]["fecha_dato"] for k in pesos[pesos > 0].index if elegibles[k]["fecha_dato"]]
    vig = [elegibles[k]["vigencia"] for k in pesos[pesos > 0].index]
    # Mejora esperada neta de costos frente a mantener la cartera actual (insumo de la alerta de deriva).
    mu = mu_esc  # el mismo μ (con escenario) que usó el optimizador
    h_dias = float(perfil["horizonte_anios"]) * DIAS
    esperado_obj = float((pesos * mu).sum() * h_dias)
    w_act = pd.Series(previos).reindex(ids).fillna(0.0)
    esperado_act = float((w_act * mu).sum() * h_dias)
    mejora = {"esperado_propuesta": esperado_obj, "esperado_actual": esperado_act,
              "costo_cambio": float(cmb["costo_pct"]), "neta": esperado_obj - esperado_act - float(cmb["costo_pct"]),
              "horizonte_sesiones": round(h_dias), "nota": "Estimación con μ contraída; incierta, no es una promesa."}
    aversion, tope = _parametros_lente(lente_calc, perfil, ajustes)
    aversion *= mult_base
    return {
        **base, "estado": "demostracion" if ajustes.es_demo else "calculada",
        "mejora_esperada": mejora,
        "cumplimiento_reto": reto.cumplimiento(dict(pesos)) if reto.activo() else [],
        "vigencia_datos": vigencia.peor(vig), "datos_hasta": max(fechas_dato) if fechas_dato else None,
        "datos_desde_mas_antiguo": min(fechas_dato) if fechas_dato else None,
        "pesos": asignacion, "efectivo_residual": residuo, "capital": capital,
        "metricas_estimacion": _metricas(_serie_pesos(X, pesos)),
        "comparacion": comparacion, "sensibilidad": sens, "estabilidad": round(estabilidad, 3),
        "escenarios": esc, "riesgos": _riesgos(pesos, elegibles, m_modelo, esc, excluidos, perfil),
        "cambios": cmb, "ordenes": plan_ordenes, "puntuacion": punt, "busqueda_puntuacion": busqueda,
        "mercado_acciones": perfil.get("mercado_acciones", "ambos"),
        "n_elegibles": len(elegibles), "n_excluidos": len(excluidos),
        "reproducibilidad": {
            "funcion_objetivo": "max μᵀw − λ·wᵀΣw − Σc|Δw| − γ·‖w‖² ; μ James-Stein, Σ Ledoit-Wolf, varianza como riesgo",
            "regularizacion_l2_gamma": float(o.get("l2_regularizacion", 0.0)),
            "lente": lente, "aversion_riesgo_lambda": aversion,
            "horizonte_anios": float(perfil["horizonte_anios"]), "horizonte_origen": perfil.get("horizonte_origen", "perfil"),
            "precios": "sin ajustar por dividendos (el Reto no los paga)" if reto.activo() else "ajustados por dividendos y splits",
            "restricciones": _restricciones(tipo, perfil, ajustes, elegibles_l, lente_calc) + [f"tope por activo {tope:.0%}",
                                                                                          "sin ventas en corto, sin apalancamiento"],
            "ventana_estimacion": {"desde": X.index[0].date().isoformat(), "hasta": X.index[-1].date().isoformat(), "sesiones": len(X)},
            "walk_forward": {"entrenamiento": int(o["walk_forward_entrenamiento"]), "prueba": int(o["walk_forward_prueba"]),
                             "ventanas": len(rot)},
            "escenario": perfil.get("escenario", "base"), "ajuste_escenario": ESCENARIOS.get(perfil.get("escenario", "base")),
            "huella_datos": _huella_datos(X_todo), "semilla": int(o["semilla"]),
            "versiones": {p: md.version(p) for p in ("skfolio", "numpy", "pandas", "scikit-learn", "cvxpy-base", "clarabel")},
            "universo": ids,
        },
        "aviso": "Estimación informativa basada en datos históricos. No es una recomendación personalizada ni una promesa "
                 "de rendimiento. La terminal no envía órdenes.",
    }


def clasificar(propuestas: list[dict], cartera_actual: dict) -> list[dict]:
    """Ordena las alternativas por puntuación total. Se presenta como resultado de criterios, no como certeza."""
    filas = []
    for p in propuestas:
        clave = p.get("clave", p["tipo"])
        if p.get("estado") in ("calculada", "demostracion"):
            filas.append({"alternativa": p["nombre"], "tipo": p["tipo"], "clave": clave, "puntuacion": p["puntuacion"]["total"],
                          "estado": p["estado"]})
        else:
            filas.append({"alternativa": p["nombre"], "tipo": p["tipo"], "clave": clave, "puntuacion": None,
                          "estado": p.get("estado"), "motivo": "; ".join(p.get("motivos", []))})
    filas.sort(key=lambda f: -(f["puntuacion"] if f["puntuacion"] is not None else -1))
    for i, f in enumerate(filas, 1):
        f["posicion"] = i if f["puntuacion"] is not None else None
    return filas


def dias_desde(fecha: str | None) -> int | None:
    return (date.today() - date.fromisoformat(fecha[:10])).days if fecha else None
