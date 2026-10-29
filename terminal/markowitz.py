"""Constructor de portafolios del usuario con la teoría media-varianza de Markowitz.

Sigue el método del Taller de Construcción de Portafolios de Acelera Academy:
  E(r_p) = Σ w_i E(r_i)        σ_p = √(wᵀ Σ w)        Sharpe = (E(r_p) − r_f) / σ_p
  E(r_i) y Σ salen de rendimientos diarios simples × 252 (promedio histórico; no es un pronóstico).
  Frontera eficiente: mínima varianza para cada rendimiento objetivo. Portafolio tangente: máximo Sharpe.
  Utilidad: U = E(r) − ½ A σ²  (A = aversión al riesgo). Asignación al activo riesgoso: y* = (E(r_p) − r_f) / (A σ_p²).

Cada perfil (conservador → agresivo) propone método, tope por activo y aversión; el usuario puede cambiarlos.
`generar()` arma la propuesta completa a partir de las especificaciones del usuario: completa sus instrumentos con
los mejores del Ranking que no se muevan igual, optimiza y devuelve sugerencias de la terminal para mejorarla.
Es una simulación educativa: no envía órdenes ni es una recomendación personalizada. Los portafolios se guardan en
`portafolios_usuario`.
"""
from __future__ import annotations

import csv
import json
import math
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from . import db, mercado, ranking, reto
from .config import Ajustes, credencial

ANUAL = 252
VENTANAS = (126, 252, 504, 756)

# Tasa libre de riesgo inicial del generador: CETES a 28 días, subasta semanal (Banxico SIE SF43936, «Valores
# gubernamentales, Resultados de la subasta semanal, Tasa de rendimiento, Cetes a 28 días», porcentaje; clave
# confirmada en el catálogo SIE el 28-oct-2026). Se guarda en la base y se vuelve a consultar cada 12 h.
SERIE_CETES28 = "SF43936"
URL_SIE = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/{s}/datos/oportuno"
RF_RESPALDO = 0.07


def tasa_libre(con: sqlite3.Connection, ajustes: Ajustes, cliente: httpx.Client | None = None) -> dict:
    """{valor, fecha, fuente, aviso}. Si Banxico no responde, la última guardada; si nunca hubo, 7 % y lo dice."""
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='cetes28'").fetchone()
    previo = json.loads(f[0]) if f else None
    if previo and datetime.now(UTC) - datetime.fromisoformat(previo["consultado_en"]) < timedelta(hours=12):
        return previo
    token = None if ajustes.es_demo else credencial("banxico")
    error = "sin BANXICO_TOKEN" if not token else None
    if token:
        try:
            r = (cliente or httpx.Client(timeout=15)).get(URL_SIE.format(s=SERIE_CETES28),
                                                         headers={"Bmx-Token": token, "Accept": "application/json"})
            r.raise_for_status()
            d = r.json()["bmx"]["series"][0]["datos"][-1]
            dd, mm, aa = d["fecha"].split("/")
            nuevo = {"valor": round(float(d["dato"].replace(",", "")) / 100, 6), "fecha": f"{aa}-{mm}-{dd}",
                     "fuente": f"Banxico SIE {SERIE_CETES28} (CETES 28 días, subasta semanal)", "aviso": None,
                     "consultado_en": datetime.now(UTC).isoformat(timespec="seconds")}
            db.escribir(con, "INSERT INTO ajustes_usuario VALUES ('cetes28', ?, ?) ON CONFLICT(clave) DO UPDATE SET "
                             "valor=excluded.valor, actualizado_en=excluded.actualizado_en", (json.dumps(nuevo), db.ahora()))
            return nuevo
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            error = f"Banxico no respondió ({type(e).__name__})"
    if previo:
        return {**previo, "aviso": f"{error}: se usa la última tasa guardada"}
    return {"valor": RF_RESPALDO, "fecha": None, "fuente": "valor fijo", "aviso": f"{error}: se usa 7 % fijo"}


# Sector (config/sectores.csv, columna «grupo»): acciones de EE. UU. por grupo mayor SIC de la SEC (2 dígitos;
# scripts/sectores_sec.py); ETF por el sector que declara el nombre oficial del fondo. BMV y ETF amplios quedan sin
# grupo: no cuentan para el tope por sector (se dice en el resultado). Las taxonomías no se mezclan entre sí.
ARCHIVO_SECTORES = Path(__file__).resolve().parent.parent / "config" / "sectores.csv"
COVARIANZAS = {"muestral": "Muestral", "ledoit_wolf": "Ledoit-Wolf (contracción)"}
PASO_REBALANCEO = 21  # sesiones: rebalanceo mensual en la prueba fuera de muestra


def sectores() -> dict[str, str]:
    if not ARCHIVO_SECTORES.exists():
        return {}
    with ARCHIVO_SECTORES.open(encoding="utf-8") as f:
        return {r["id"]: r["grupo"] for r in csv.DictReader(f) if r.get("grupo")}


MAX_ACTIVOS = 40
METODOS = {
    "max_sharpe": "Máximo Sharpe (portafolio tangente)",
    "min_varianza": "Mínima varianza",
    "rend_objetivo": "Rendimiento objetivo con el menor riesgo",
    "riesgo_objetivo": "Riesgo objetivo con el mayor rendimiento",
    "utilidad": "Máxima utilidad U = E(r) − ½·A·σ²",
    "equiponderado": "Pesos iguales (1/N), referencia",
}
OBJETIVOS = {
    "conservador": {"nombre": "Conservador", "metodo": "min_varianza", "peso_max": 0.20, "min_activos": 8, "aversion": 10.0,
                    "horizonte_anios": 1, "riesgo_ref": 0.12,
                    "descripcion": "Prioriza que el valor caiga poco: menor volatilidad, más instrumentos y topes bajos."},
    "moderado": {"nombre": "Moderado", "metodo": "utilidad", "peso_max": 0.25, "min_activos": 6, "aversion": 6.0,
                 "horizonte_anios": 3, "riesgo_ref": 0.18,
                 "descripcion": "Equilibra rendimiento y riesgo con una aversión al riesgo alta."},
    "crecimiento": {"nombre": "Crecimiento", "metodo": "max_sharpe", "peso_max": 0.30, "min_activos": 5, "aversion": 4.0,
                    "horizonte_anios": 5, "riesgo_ref": 0.25,
                    "descripcion": "Busca el mejor rendimiento por unidad de riesgo (Sharpe)."},
    "agresivo": {"nombre": "Agresivo", "metodo": "max_sharpe", "peso_max": 0.40, "min_activos": 5, "aversion": 2.0,
                 "horizonte_anios": 10, "riesgo_ref": None,
                 "descripcion": "Acepta más volatilidad a cambio de crecimiento; aun así diversifica."},
}
# Portafolios guardados antes del 28-oct-2026 usaban otros nombres de objetivo; se leen con su equivalente.
ALIAS = {"seguridad": "conservador", "pertenencia": "moderado", "estima": "crecimiento", "autorrealizacion": "agresivo"}
CLASES_GEN = {"acciones": ("acciones",), "etf": ("etf",), "fondos": ("fondos",), "mixto": ("acciones", "etf")}
AVISO = ("Simulación educativa con rendimientos históricos: no es un pronóstico ni una recomendación de compra o venta. "
         "La terminal no envía órdenes; usted decide y opera.")


class ErrorPortafolio(ValueError):
    pass


def _num(spec: dict, k: str, defecto: float, lo: float, hi: float) -> float:
    v = spec.get(k, defecto)
    try:
        v = float(defecto if v in (None, "") else v)
    except (TypeError, ValueError):
        raise ErrorPortafolio(f"{k}: debe ser un número") from None
    if not (lo <= v <= hi) or math.isnan(v):
        raise ErrorPortafolio(f"{k}: debe estar entre {lo} y {hi}")
    return v


def normalizar(spec: dict, ins: dict) -> dict:
    """Valida la especificación que llega del navegador (frontera de confianza) y completa valores por defecto."""
    if not isinstance(spec, dict):
        raise ErrorPortafolio("especificación inválida")
    objetivo = spec.get("objetivo") or "crecimiento"
    objetivo = ALIAS.get(objetivo, objetivo)
    if objetivo not in OBJETIVOS:
        raise ErrorPortafolio("objetivo desconocido")
    base = OBJETIVOS[objetivo]
    metodo = spec.get("metodo") or base["metodo"]
    if metodo not in METODOS:
        raise ErrorPortafolio("método desconocido")
    activos = spec.get("activos")
    if not isinstance(activos, list) or not all(isinstance(a, str) for a in activos):
        raise ErrorPortafolio("activos: lista de identificadores")
    activos = list(dict.fromkeys(activos))
    desconocidos = [a for a in activos if a not in ins]
    if desconocidos:
        raise ErrorPortafolio(f"instrumentos desconocidos: {', '.join(desconocidos[:5])}")
    if not 2 <= len(activos) <= MAX_ACTIVOS:
        raise ErrorPortafolio(f"elija de 2 a {MAX_ACTIVOS} instrumentos")
    nombre = str(spec.get("nombre") or "").strip()[:80] or "Portafolio sin nombre"
    ventana = int(_num(spec, "ventana", 252, 60, 1260))
    out = {
        "nombre": nombre, "descripcion": str(spec.get("descripcion") or "").strip()[:500], "objetivo": objetivo,
        "metodo": metodo, "activos": activos, "ventana": ventana,
        "capital": _num(spec, "capital", 100_000, 0, 1e11), "rf": _num(spec, "rf", 0.07, -0.05, 0.5),
        "peso_max": _num(spec, "peso_max", base["peso_max"], 0.01, 1), "peso_min": _num(spec, "peso_min", 0, 0, 0.5),
        "aversion": _num(spec, "aversion", base["aversion"], 0.1, 50),
        "rend_objetivo": _num(spec, "rend_objetivo", 0.12, -1, 5), "riesgo_objetivo": _num(spec, "riesgo_objetivo", 0.18, 0.001, 5),
        "horizonte_anios": _num(spec, "horizonte_anios", base["horizonte_anios"], 0.1, 60),
        "covarianza": spec.get("covarianza") or "muestral",
        "usd_max": None if spec.get("usd_max") in (None, "") else _num(spec, "usd_max", 1, 0, 1),
        "sector_max": None if spec.get("sector_max") in (None, "") else _num(spec, "sector_max", 1, 0.01, 1),
    }
    if out["covarianza"] not in COVARIANZAS:
        raise ErrorPortafolio("covarianza: muestral o ledoit_wolf")
    if out["peso_min"] > out["peso_max"]:
        raise ErrorPortafolio("el peso mínimo no puede superar el máximo")
    vistas = spec.get("vistas") or []
    if not isinstance(vistas, list) or len(vistas) > len(activos):
        raise ErrorPortafolio("vistas: lista de hasta una vista por instrumento")
    normalizadas = []
    for vista in vistas:
        if not isinstance(vista, dict) or vista.get("activo") not in activos:
            raise ErrorPortafolio("vista: activo desconocido o fuera del portafolio")
        contra = vista.get("contra") or None
        if contra is not None and (contra not in activos or contra == vista["activo"]):
            raise ErrorPortafolio("vista: comparación inválida")
        normalizadas.append({"activo": vista["activo"], "contra": contra,
                            "rend": _num(vista, "rend", 0, -1, 5),
                            "confianza": _num(vista, "confianza", 0.5, 0.01, 1)})
    if len({(v["activo"], v["contra"]) for v in normalizadas}) != len(normalizadas):
        raise ErrorPortafolio("vistas duplicadas")
    out["vistas"] = normalizadas
    return out


def _datos(con, ajustes, ids: list[str], ventana: int, base: pd.DataFrame | None = None) -> tuple[pd.DataFrame, list[dict]]:
    """Precios en MXN (ajustados por dividendos y splits) en fechas comunes. Excluye lo que tiene huecos.
    `base`: matriz de `mercado.precios_mxn` ya leída que contiene estos ids (cada columna es independiente)."""
    p = mercado.precios_mxn(con, ajustes, ids) if base is None else base[[i for i in ids if i in base.columns]]
    excluidos = [{"id": i, "motivo": "sin precios"} for i in ids if i not in p.columns]
    p = p[[i for i in ids if i in p.columns]].dropna(how="all").iloc[-(ventana + 1):]
    cobertura = p.notna().mean()
    for i in cobertura[cobertura < 0.8].index:
        excluidos.append({"id": i, "motivo": f"historia insuficiente ({cobertura[i]:.0%} de la ventana)"})
    p = p[[c for c in p.columns if cobertura[c] >= 0.8]].ffill(limit=3).dropna()
    return p, excluidos


def _vol(w, cov):
    return float(np.sqrt(max(w @ cov @ w, 0.0)))


def _optimizar(objetivo, n, lo, hi, extra=(), w0=None):
    """`objetivo(w)` devuelve (valor, gradiente): con derivadas exactas SLSQP no aproxima por diferencias (10× menos CPU)."""
    w0 = np.full(n, 1 / n) if w0 is None else w0
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones_like(w)}, *extra]
    r = minimize(objetivo, w0, jac=True, method="SLSQP", bounds=[(lo, hi)] * n, constraints=cons,
                 options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(r.x, lo, hi)
    return w / w.sum(), bool(r.success)


def _estimar(R: pd.DataFrame, metodo: str) -> tuple[np.ndarray, np.ndarray]:
    """Rendimiento y covarianza anuales. Ledoit-Wolf contrae la covarianza muestral hacia un blanco estructurado:
    menos error de estimación con pocas sesiones y muchos instrumentos (los pesos dependen menos del ruido)."""
    mu = R.mean().values * ANUAL
    if metodo == "ledoit_wolf":
        from sklearn.covariance import ledoit_wolf
        return mu, ledoit_wolf(R.values)[0] * ANUAL
    return mu, R.cov().values * ANUAL


def _black_litterman(ids: list[str], cov: np.ndarray, vistas: list[dict], aversion: float) -> np.ndarray:
    """Posterior de rendimientos anuales con prior de equilibrio equiponderado y vistas explícitas.

    La confianza controla la varianza de cada vista; sin vistas, el prior no se modifica.
    No usa rendimientos posteriores a la fecha de entrenamiento.
    """
    n = len(ids)
    prior = aversion * cov @ np.full(n, 1 / n)
    if not vistas:
        return prior
    filas, valores, incertidumbre = [], [], []
    for vista in vistas:
        if vista["activo"] not in ids or (vista["contra"] and vista["contra"] not in ids):
            continue  # un activo excluido por falta de historia no aporta una vista
        p = np.zeros(n)
        p[ids.index(vista["activo"])] = 1
        if vista["contra"]:
            p[ids.index(vista["contra"])] = -1
        filas.append(p)
        valores.append(vista["rend"])
        incertidumbre.append(max(float(p @ (0.05 * cov) @ p), 1e-12) *
                             (1 - vista["confianza"]) / vista["confianza"] + 1e-12)
    if not filas:
        return prior
    P = np.array(filas)
    tau_cov = 0.05 * cov
    sistema = P @ tau_cov @ P.T + np.diag(incertidumbre)
    return prior + tau_cov @ P.T @ np.linalg.solve(sistema, np.array(valores) - P @ prior)


def _grupos(ids: list[str], ins: dict, s: dict) -> list[tuple[str, np.ndarray, float]]:
    """(nombre, máscara, tope) de las restricciones opcionales: moneda USD (SIC) y cada sector conocido."""
    out = []
    if s.get("usd_max") is not None:
        out.append(("USD (SIC)", np.array([ins[i].get("moneda_referencia") == "USD" for i in ids], float), s["usd_max"]))
    if s.get("sector_max") is not None:
        sec = sectores()
        for nombre in sorted({sec[i] for i in ids if i in sec}):
            out.append((nombre, np.array([sec.get(i) == nombre for i in ids], float), s["sector_max"]))
    return out


def _restricciones(grupos) -> list[dict]:
    return [{"type": "ineq", "fun": (lambda w, m=m, t=t: t - m @ w), "jac": (lambda w, m=m: -m)} for _, m, t in grupos]


def _pesos(s: dict, mu: np.ndarray, cov: np.ndarray, lo: float, hi: float, extra: list, w_min=None, w_tan=None):
    """Pesos del método elegido. Devuelve (w, avisos, w_min, w_tan)."""
    n, rf = len(mu), s["rf"]
    var = lambda w: (w @ cov @ w, 2 * cov @ w)  # noqa: E731

    def sharpe_neg(w):
        v = max(_vol(w, cov), 1e-12)
        exceso = w @ mu - rf
        return -exceso / v, -(mu * v - exceso * (cov @ w) / v) / v ** 2

    m, avisos = s["metodo"], []
    if w_min is None and m in ("min_varianza", "rend_objetivo", "riesgo_objetivo"):
        w_min, _ = _optimizar(var, n, lo, hi, extra)
    if w_tan is None and m == "max_sharpe":
        w_tan, _ = _optimizar(sharpe_neg, n, lo, hi, extra)
    if m == "min_varianza":
        w = w_min
    elif m == "max_sharpe":
        w = w_tan
    elif m == "equiponderado":
        w = np.full(n, 1 / n)
    elif m == "utilidad":
        w, _ = _optimizar(lambda w: (-(w @ mu - 0.5 * s["aversion"] * (w @ cov @ w)), -(mu - s["aversion"] * (cov @ w))),
                          n, lo, hi, extra)
    elif m == "rend_objetivo":
        r_lo, r_hi = float(w_min @ mu), _rend_max(mu, lo, hi)
        e = min(max(s["rend_objetivo"], r_lo), r_hi)
        if abs(e - s["rend_objetivo"]) > 1e-9:
            avisos.append(f"El rendimiento objetivo {s['rend_objetivo']:.1%} no es alcanzable con estos topes; se usó {e:.1%}.")
        w, _ = _optimizar(var, n, lo, hi, [*extra, {"type": "eq", "fun": lambda w: w @ mu - e, "jac": lambda w: mu}], w_min)
    else:  # riesgo_objetivo
        t = s["riesgo_objetivo"]
        if t < _vol(w_min, cov):
            avisos.append(f"El riesgo objetivo {t:.1%} es menor que el mínimo posible ({_vol(w_min, cov):.1%}); se usó el de mínima varianza.")
            w = w_min
        else:
            w, _ = _optimizar(lambda w: (-(w @ mu), -mu), n, lo, hi,
                              [*extra, {"type": "ineq", "fun": lambda w: t - _vol(w, cov),
                                        "jac": lambda w: -(cov @ w) / max(_vol(w, cov), 1e-12)}], w_min)
    return w, avisos, w_min, w_tan


def fuera_de_muestra(P: pd.DataFrame, s: dict, lo: float, hi: float, extra: list, costo: float | None) -> dict:
    """Walk-forward: con las sesiones previas se estiman los pesos del método; se mantienen un mes (21 sesiones, sin
    rebalanceo diario) y se paga comisión sobre lo que se compra y vende. Frente a 1/N, igual.
    Entrenamiento = la ventana elegida, acortada si hace falta para dejar al menos 6 meses de prueba (mínimo 60)."""
    R = P.pct_change().dropna()
    ent = min(s["ventana"], len(R) - 6 * PASO_REBALANCEO)
    if ent < 60:
        return {"disponible": False, "motivo": f"Se necesitan al menos {60 + 6 * PASO_REBALANCEO} sesiones comunes "
                                               f"(60 para estimar y 6 meses de prueba); hay {len(R)}."}
    c = costo or 0.0
    n = R.shape[1]
    series: dict[str, list] = {"propuesta": [], "1/N": []}
    previos: dict = {"propuesta": None, "1/N": None}
    rotacion = {"propuesta": 0.0, "1/N": 0.0}
    for t in range(ent, len(R), PASO_REBALANCEO):
        mu, cov = _estimar(R.iloc[t - ent:t], s["covarianza"])
        if s.get("vistas"):
            mu = _black_litterman(list(R.columns), cov, s["vistas"], s["aversion"])
        w, *_ = _pesos(s, mu, cov, lo, hi, extra)
        crec = np.cumprod(1 + R.iloc[t:t + PASO_REBALANCEO].values, axis=0)
        for k, pesos in (("propuesta", w), ("1/N", np.full(n, 1 / n))):
            rot = float(np.abs(pesos - previos[k]).sum()) if previos[k] is not None else 1.0  # la primera compra también cuesta
            rotacion[k] += rot
            valor = np.concatenate([[1.0], (pesos * crec).sum(axis=1)])
            diarios = valor[1:] / valor[:-1] - 1
            diarios[0] -= rot * c
            series[k].extend(diarios.tolist())
            previos[k] = pesos * crec[-1] / float((pesos * crec[-1]).sum())

    def resumen(x):
        x = np.array(x)
        valor = np.cumprod(1 + x)
        anual, vol = float(valor[-1] ** (ANUAL / len(x)) - 1), float(x.std(ddof=1) * np.sqrt(ANUAL))
        return {"rend_anual": anual, "riesgo": vol, "sharpe": (anual - s["rf"]) / vol if vol > 0 else None,
                "rend_total": float(valor[-1] - 1), "caida_maxima": float((valor / np.maximum.accumulate(valor) - 1).min())}

    meses = len(range(ent, len(R), PASO_REBALANCEO))
    out = {k: resumen(v) | {"rotacion_mensual": rotacion[k] / meses} for k, v in series.items()}
    gana = out["propuesta"]["rend_total"] > out["1/N"]["rend_total"]
    return {"disponible": True, **out, "meses": meses, "inicio": R.index[ent].date().isoformat(),
            "fin": R.index[-1].date().isoformat(), "comision": c, "entrenamiento": ent,
            "lectura": ("La propuesta superó a 1/N fuera de muestra" if gana else "1/N superó a la propuesta fuera de muestra")
                       + f" en {meses} meses; un solo periodo no demuestra ventaja (sin prueba de significancia).",
            "nota": f"Rebalanceo cada {PASO_REBALANCEO} sesiones; pesos estimados con las {ent} sesiones previas y el mismo "
                    "método" + ("" if ent == s["ventana"] else f" (ventana acortada de {s['ventana']} por historia disponible)")
                    + "; comisión del Reto "
                    + (f"{c:.3%} por peso operado (con IVA)" if costo else "no configurada: 0 %") + "."
                    + (" Las vistas de Black-Litterman son las de hoy y se aplican a todos los meses: si se formaron viendo "
                       "el pasado reciente, esta prueba favorece a la propuesta." if s.get("vistas") else "")}


def _rend_max(mu: np.ndarray, lo: float, hi: float) -> float:
    """Rendimiento máximo alcanzable con los topes: llena primero los activos de mayor rendimiento."""
    w = np.full(len(mu), lo)
    resto = 1 - w.sum()
    for i in np.argsort(-mu):
        a = min(hi - lo, resto)
        w[i] += a
        resto -= a
    return float(w @ mu)


def calcular(con: sqlite3.Connection, ajustes: Ajustes, spec: dict, base: pd.DataFrame | None = None) -> dict:
    ins = mercado.instrumentos(con)
    s = normalizar(spec, ins)
    base = mercado.precios_mxn(con, ajustes, s["activos"]) if base is None else base
    precios, excluidos = _datos(con, ajustes, s["activos"], s["ventana"], base)
    ids = list(precios.columns)
    if len(ids) < 2 or len(precios) < 61:
        raise ErrorPortafolio("No hay historia común suficiente (mínimo 2 instrumentos y 60 sesiones). "
                              + "; ".join(f"{e['id']}: {e['motivo']}" for e in excluidos))
    n, lo, hi = len(ids), s["peso_min"], s["peso_max"]
    if hi * n < 1 - 1e-9:
        raise ErrorPortafolio(f"Con {n} instrumentos y un tope de {hi:.0%} no se llega a 100 %: agregue instrumentos o suba el tope.")
    if lo * n > 1 + 1e-9:
        raise ErrorPortafolio(f"Con {n} instrumentos y un mínimo de {lo:.0%} se supera 100 %: baje el mínimo.")
    R = precios.pct_change().dropna()
    mu, cov = _estimar(R, s["covarianza"])
    if s.get("vistas"):
        mu = _black_litterman(ids, cov, s["vistas"], s["aversion"])
    sig = np.sqrt(np.diag(cov))
    rf = s["rf"]
    rend = lambda w: float(w @ mu)  # noqa: E731
    var = lambda w: (w @ cov @ w, 2 * cov @ w)  # noqa: E731
    grupos = _grupos(ids, ins, s)
    extra = _restricciones(grupos)

    def sharpe_neg(w):
        v = max(_vol(w, cov), 1e-12)
        exceso = w @ mu - rf
        return -exceso / v, -(mu * v - exceso * (cov @ w) / v) / v ** 2

    w_min, _ = _optimizar(var, n, lo, hi, extra)
    w_tan, _ = _optimizar(sharpe_neg, n, lo, hi, extra)
    r_lo, r_hi = rend(w_min), _rend_max(mu, lo, hi)
    frontera, w_prev = [], w_min
    for objetivo in np.linspace(r_lo, r_hi, 25):
        w, ok = _optimizar(var, n, lo, hi, [*extra, {"type": "eq", "fun": lambda w, e=objetivo: w @ mu - e, "jac": lambda w: mu}],
                           w_prev)
        if ok:
            frontera.append({"rend": rend(w), "riesgo": _vol(w, cov), "pesos": dict(zip(ids, np.round(w, 6).tolist()))})
            w_prev = w
    m = s["metodo"]
    w, avisos, *_ = _pesos(s, mu, cov, lo, hi, extra, w_min, w_tan)
    excedidos = [f"{nombre} {float(mk @ w):.0%} > {t:.0%}" for nombre, mk, t in grupos if float(mk @ w) > t + 1e-4]
    if excedidos:
        raise ErrorPortafolio("Con esos topes por moneda o sector no se llega a 100 % (" + "; ".join(excedidos)
                              + "): súbalos o agregue instrumentos en pesos o de otros sectores.")
    if s.get("sector_max") is not None:
        sin = [ins[i]["clave_operable"] for i in ids if i not in sectores()]
        if sin:
            avisos.append(f"Sin sector conocido (no cuentan para el tope por sector): {', '.join(sin[:8])}"
                          + (" y otros" if len(sin) > 8 else "") + ". Fuente: clasificación SIC de la SEC.")
    serie = (R.values @ w)
    valor = np.cumprod(1 + serie)
    caida = float((valor / np.maximum.accumulate(valor) - 1).min())
    eqw = np.full(n, 1 / n)

    def metricas(x):
        r, v = rend(x), _vol(x, cov)
        return {"rend": r, "riesgo": v, "sharpe": (r - rf) / v if v > 0 else None,
                "utilidad": r - 0.5 * s["aversion"] * v * v}

    met = metricas(w)
    y = (met["rend"] - rf) / (s["aversion"] * met["riesgo"] ** 2) if met["riesgo"] > 0 else None
    contrib = w * (cov @ w) / max(w @ cov @ w, 1e-18)
    ultimo = precios.iloc[-1]
    filas = []
    for k, i in enumerate(ids):
        monto = s["capital"] * w[k]
        titulos = math.floor(monto / ultimo[i]) if ultimo[i] > 0 else 0
        filas.append({"id": i, "clave": ins[i]["clave_operable"], "nombre": (ins[i]["nombre"] or "").strip()[:60],
                      "clase": ins[i]["clase"], "mercado": ins[i]["mercado_operable"], "peso": float(w[k]),
                      "rend": float(mu[k]), "riesgo": float(sig[k]), "sharpe": float((mu[k] - rf) / sig[k]) if sig[k] > 0 else None,
                      "contribucion_riesgo": float(contrib[k]), "precio_mxn": float(ultimo[i]), "monto": float(monto),
                      "titulos": titulos, "invertido": float(titulos * ultimo[i])})
    activos_con_peso = sum(1 for x in w if x >= 0.005)
    if activos_con_peso < OBJETIVOS[s["objetivo"]]["min_activos"]:
        avisos.append(f"Solo {activos_con_peso} instrumentos reciben peso; para «{OBJETIVOS[s['objetivo']]['nombre']}» se "
                      f"sugieren al menos {OBJETIVOS[s['objetivo']]['min_activos']} (baje el tope o agregue instrumentos).")
    if len(precios) < 250:
        avisos.append(f"Ventana corta ({len(precios) - 1} sesiones): las estimaciones de rendimiento son poco estables.")
    corr = np.corrcoef(R.values.T)
    return {
        "especificacion": s, "metodo_nombre": METODOS[m], "objetivo_nombre": OBJETIVOS[s["objetivo"]]["nombre"],
        "metricas": met, "metricas_1n": metricas(eqw), "min_varianza": metricas(w_min), "tangente": metricas(w_tan),
        "pesos_tangente": dict(zip(ids, np.round(w_tan, 6).tolist())), "pesos_min_varianza": dict(zip(ids, np.round(w_min, 6).tolist())),
        "asignacion_riesgosa": y, "caida_maxima": caida, "peor_dia": float(serie.min()),
        "activos": filas, "frontera": frontera, "correlacion": {"ids": ids, "matriz": np.round(corr, 4).tolist()},
        "fuera_de_muestra": fuera_de_muestra(base[ids].ffill(limit=3).dropna(), s, lo, hi, extra, reto.costo_operacion()),
        "covarianza_nombre": COVARIANZAS[s["covarianza"]],
        "restricciones": [{"grupo": nombre, "tope": t, "peso": float(mk @ w)} for nombre, mk, t in grupos],
        "efectivo_restante": float(s["capital"] - sum(f["invertido"] for f in filas)),
        "reglas_reto": {"emisoras": activos_con_peso, "peso_max": float(w.max()),
                        "cumple": activos_con_peso >= 5 and float(w.max()) <= 0.5},
        "datos": {"inicio": precios.index[0].date().isoformat(), "fin": precios.index[-1].date().isoformat(),
                  "sesiones": len(R), "excluidos": excluidos, "precios": "MXN ajustados por dividendos y splits"},
        "avisos": avisos, "aviso": AVISO, "calculado_en": db.ahora(),
    }


# ---------- persistencia ----------
def listar(con: sqlite3.Connection) -> list[dict]:
    out = []
    for r in con.execute("SELECT * FROM portafolios_usuario ORDER BY actualizado_en DESC"):
        res = json.loads(r["resultado"]) if r["resultado"] else None
        spec = json.loads(r["especificacion"])
        spec["objetivo"] = ALIAS.get(spec.get("objetivo"), spec.get("objetivo"))
        if res and spec.get("objetivo") in OBJETIVOS:
            res["objetivo_nombre"] = OBJETIVOS[spec["objetivo"]]["nombre"]
        out.append({"id": r["id"], "nombre": r["nombre"], "especificacion": spec,
                    "resultado": res, "creado_en": r["creado_en"], "actualizado_en": r["actualizado_en"]})
    return out


def obtener(con: sqlite3.Connection, pid: int) -> dict:
    r = next((p for p in listar(con) if p["id"] == pid), None)
    if r is None:
        raise KeyError(pid)
    return r


def guardar(con: sqlite3.Connection, ajustes: Ajustes, spec: dict, pid: int | None = None) -> dict:
    res = calcular(con, ajustes, spec)
    s, t = res["especificacion"], db.ahora()
    with db.transaccion(con):
        if pid is None:
            pid = con.execute("INSERT INTO portafolios_usuario (nombre, especificacion, resultado, creado_en, actualizado_en) "
                              "VALUES (?,?,?,?,?)", (s["nombre"], json.dumps(s), json.dumps(res), t, t)).lastrowid
        elif not con.execute("UPDATE portafolios_usuario SET nombre=?, especificacion=?, resultado=?, actualizado_en=? WHERE id=?",
                             (s["nombre"], json.dumps(s), json.dumps(res), t, pid)).rowcount:
            raise KeyError(pid)
    return {"id": pid, **res}


def eliminar(con: sqlite3.Connection, pid: int) -> bool:
    with db.transaccion(con):
        return con.execute("DELETE FROM portafolios_usuario WHERE id=?", (pid,)).rowcount > 0


# ---------- ayuda para construir y generador de propuestas ----------
_PRECIOS: dict = {}


def _precios_cache(con: sqlite3.Connection, ajustes: Ajustes, ids: list[str]) -> pd.DataFrame:
    """`mercado.precios_mxn` con la misma regla de caché que el Ranking (marca de datos y tolerancia): leer la matriz de
    precios es lo más lento del generador y solo cambia cuando entran precios o tipo de cambio."""
    clave = (con.execute("PRAGMA database_list").fetchone()[2], tuple(ids))
    marca, ahora = ranking._marca(con), time.monotonic()
    previo = _PRECIOS.get(clave)
    if previo and ahora - previo[0] < ranking.VIGENCIA_S and (previo[1] == marca or ahora - previo[0] < ranking.TOLERANCIA_S):
        return previo[2]
    if len(_PRECIOS) >= 16:  # pocas combinaciones de filtros a la vez; se descarta la más vieja
        _PRECIOS.pop(min(_PRECIOS, key=lambda k: _PRECIOS[k][0]))
    p = mercado.precios_mxn(con, ajustes, ids)
    _PRECIOS[clave] = (ahora, marca, p)
    return p


def _filas_ranking(con: sqlite3.Connection, ajustes: Ajustes, mercado_filtro: str, clase: str) -> list[dict]:
    """Filas del Ranking (con su caché: cambia solo cuando llegan datos nuevos)."""
    return ranking.calcular_cache(con, ajustes, mercado_filtro, clase)["filas"]


def _candidatos(con, ajustes, objetivo: str, mercado_filtro: str, clase: str, caps: list[str] | None) -> list[dict]:
    if clase not in CLASES_GEN:
        raise ErrorPortafolio("clase: acciones, etf, fondos o mixto")
    if mercado_filtro not in ("ambos", "nacionales", "extranjeras"):
        raise ErrorPortafolio("mercado: ambos, nacionales o extranjeras")
    listas = [_filas_ranking(con, ajustes, mercado_filtro, c) for c in CLASES_GEN[clase]]
    if len(listas) == 1:
        filas = list(listas[0])
    else:  # intercala acciones y ETF para que ninguna clase acapare los primeros lugares
        corto = min(map(len, listas))
        filas = [f for grupo in zip(*listas) for f in grupo] + [f for lista in listas for f in lista[corto:]]
    if caps:
        filas = [f for f in filas if f.get("cap_categoria") in caps]
    if objetivo == "conservador":  # primero lo más estable
        filas = sorted(filas, key=lambda f: f["vol_60"])
    return filas


def _elegir(R: pd.DataFrame, filas: list[dict], n: int, ya: list[str], excluir: set[str], corr_max: float):
    """Recorre las filas en orden y toma las que no se muevan casi igual que lo ya elegido."""
    elegidos, motivos, sobrantes = list(ya), {}, []
    for f in filas:
        i = f["id"]
        if i in elegidos or i in excluir or i not in R.columns:
            continue
        cmax = max((abs(R[i].corr(R[j])) for j in elegidos if j in R.columns), default=0.0)
        motivo = (f"#{f['posicion']} del Ranking · volatilidad {f['vol_60']:.0%}"
                  + (f" · {f['cap_categoria']} cap" if f.get("cap_categoria") else ""))
        if len(elegidos) < n and cmax <= corr_max:
            elegidos.append(i)
            motivos[i] = motivo + (f" · correlación máx. {cmax:.2f} con lo elegido" if len(elegidos) > 1 else "")
        elif len(sobrantes) < 5 and cmax <= corr_max:
            sobrantes.append({"id": i, "clave": f["clave_operable"], "motivo": motivo})
        if len(elegidos) >= n and len(sobrantes) >= 5:
            break
    return elegidos[len(ya):], motivos, sobrantes


def sugerir(con: sqlite3.Connection, ajustes: Ajustes, objetivo: str = "crecimiento", n: int = 8, mercado_filtro: str = "ambos",
            clase: str = "acciones", caps: list[str] | None = None, corr_max: float = 0.85) -> dict:
    """Propone instrumentos: los mejor ordenados del Ranking que no estén muy correlacionados entre sí."""
    objetivo = ALIAS.get(objetivo, objetivo)
    if objetivo not in OBJETIVOS:
        raise ErrorPortafolio("perfil desconocido")
    n = max(2, min(int(n), MAX_ACTIVOS))
    candidatos = _candidatos(con, ajustes, objetivo, mercado_filtro, clase, caps)[: max(n * 4, 30)]
    precios = mercado.precios_mxn(con, ajustes, [f["id"] for f in candidatos])
    R = precios.iloc[-253:].pct_change(fill_method=None)
    elegidos, motivos, _ = _elegir(R, candidatos, n, [], set(), corr_max)
    return {"activos": elegidos, "motivos": motivos, "objetivo": objetivo, "parametros": OBJETIVOS[objetivo],
            "criterio": f"Mejores del Ranking ({clase}, {mercado_filtro}) con correlación entre sí ≤ {corr_max:.2f}"
                        + (" ordenados por menor volatilidad" if objetivo == "conservador" else "") + ". No es una recomendación."}


def _ids(valor, ins: dict, campo: str) -> list[str]:
    if valor in (None, ""):
        return []
    if not isinstance(valor, list) or not all(isinstance(a, str) for a in valor):
        raise ErrorPortafolio(f"{campo}: lista de identificadores")
    desconocidos = [a for a in valor if a not in ins]
    if desconocidos:
        raise ErrorPortafolio(f"{campo}: instrumentos desconocidos ({', '.join(desconocidos[:5])})")
    return list(dict.fromkeys(valor))


def generar(con: sqlite3.Connection, ajustes: Ajustes, g: dict) -> dict:
    """Propuesta completa a partir de las especificaciones del usuario más las sugerencias de la terminal.

    `g`: objetivo (perfil), clase, mercado_filtro, caps, n (instrumentos en total), fijos (los elige el usuario),
    excluir, completar (si la terminal completa con el Ranking), metodo ("auto" = el del perfil) y los parámetros
    de `normalizar`. Devuelve el resultado de `calcular`, sugerencias accionables y alternativas listas.
    """
    if not isinstance(g, dict):
        raise ErrorPortafolio("especificación inválida")
    ins = mercado.instrumentos(con)
    objetivo = g.get("objetivo") or "crecimiento"
    objetivo = ALIAS.get(objetivo, objetivo)
    if objetivo not in OBJETIVOS:
        raise ErrorPortafolio("perfil desconocido")
    perfil = OBJETIVOS[objetivo]
    caps = g.get("caps") or []
    if not isinstance(caps, list) or any(c not in ("mega", "large", "mid", "small", "micro") for c in caps):
        raise ErrorPortafolio("caps: mega, large, mid, small o micro")
    clase, mercado_filtro = g.get("clase") or "acciones", g.get("mercado_filtro") or "ambos"
    n = int(_num(g, "n", perfil["min_activos"], 2, MAX_ACTIVOS))
    excluir = set(_ids(g.get("excluir"), ins, "excluir"))
    fijos = [f for f in _ids(g.get("fijos"), ins, "fijos") if f not in excluir]
    ventana = int(_num(g, "ventana", 252, 60, 1260))
    sugeridos, motivos, alternativas, criterio = [], {}, [], "Solo los instrumentos que usted eligió."
    base = None
    if g.get("completar", True) is not False and len(fijos) < n:
        filas = _candidatos(con, ajustes, objetivo, mercado_filtro, clase, caps)[: max(n * 4, 40)]
        base = _precios_cache(con, ajustes, list(dict.fromkeys(fijos + [f["id"] for f in filas])))
        precios, fuera = _datos(con, ajustes, list(base.columns), ventana, base)
        sin_historia = {e["id"] for e in fuera}
        R = precios.pct_change().dropna()
        sugeridos, motivos, alternativas = _elegir(R, [f for f in filas if f["id"] not in sin_historia], n,
                                                   [f for f in fijos if f in R.columns], excluir, 0.85)
        criterio = (f"La terminal completó con los mejores del Ranking ({clase}, {mercado_filtro}"
                    + (f", {', '.join(caps)} cap" if caps else "") + ") que no se mueven casi igual (correlación ≤ 0.85)"
                    + (", empezando por los más estables" if objetivo == "conservador" else "") + ".")
    activos = fijos + sugeridos
    if len(activos) < 2:
        raise ErrorPortafolio("No hay suficientes instrumentos con historia para esos filtros: amplíe la clase, el mercado "
                              "o la capitalización, o agregue instrumentos propios.")
    metodo = g.get("metodo") or "auto"
    spec = {**{k: g[k] for k in ("nombre", "descripcion", "capital", "rf", "peso_min", "rend_objetivo", "riesgo_objetivo",
                                  "horizonte_anios", "covarianza", "usd_max", "sector_max", "vistas") if k in g},
            "objetivo": objetivo, "metodo": perfil["metodo"] if metodo == "auto" else metodo, "activos": activos,
            "ventana": ventana, "peso_max": g.get("peso_max", perfil["peso_max"]), "aversion": g.get("aversion", perfil["aversion"])}
    consejos = []
    peso_max = _num(spec, "peso_max", perfil["peso_max"], 0.01, 1)
    if peso_max * len(activos) < 1 - 1e-9:
        spec["peso_max"] = math.ceil(100 / len(activos)) / 100
        consejos.append({"tipo": "aviso", "texto": f"Con {len(activos)} instrumentos un tope de {peso_max:.0%} no llega a 100 %: "
                                                   f"la terminal lo subió a {spec['peso_max']:.0%}. Agregue instrumentos si "
                                                   "prefiere un tope más bajo."})
    res = calcular(con, ajustes, spec, base)
    consejos += _consejos(res, perfil)
    return {"resultado": res, "sugerencias": consejos, "alternativas": alternativas, "motivos": motivos,
            "fijos": [f for f in fijos if f in activos], "sugeridos": sugeridos, "criterio": criterio,
            "perfil": {"clave": objetivo, **perfil}}


def _consejos(res: dict, perfil: dict) -> list[dict]:
    """Reglas sencillas y explicables sobre el resultado; cada una puede traer una acción que la interfaz aplica."""
    out = []
    s, m, act = res["especificacion"], res["metricas"], res["activos"]
    por_id = {a["id"]: a for a in act}
    for a in sorted(act, key=lambda a: a["peso"]):
        if a["peso"] < 0.005:
            out.append({"texto": f"{a['clave']} no recibe peso: con estos datos no mejora el portafolio. Quítelo y la terminal "
                                 "pondrá otro en su lugar.", "accion": {"excluir": a["id"]}, "etiqueta": f"Quitar {a['clave']}"})
    tope = [a for a in act if a["peso"] >= s["peso_max"] - 1e-3]
    if len(tope) >= 2 and s["peso_max"] < 0.5:
        nuevo = round(min(0.5, s["peso_max"] + 0.10), 2)
        out.append({"texto": f"{len(tope)} instrumentos llegaron al tope de {s['peso_max']:.0%}. Con un tope de {nuevo:.0%} el "
                             "optimizador concentra más en los mejores: más rendimiento esperado y menos diversificación.",
                    "accion": {"peso_max": nuevo}, "etiqueta": f"Probar tope de {nuevo:.0%}"})
    t, eq = res["tangente"], res["metricas_1n"]
    if s["metodo"] != "max_sharpe" and t["sharpe"] is not None and m["sharpe"] is not None and t["sharpe"] > m["sharpe"] + 0.15:
        out.append({"texto": f"El portafolio de máximo Sharpe rinde más por unidad de riesgo ({t['sharpe']:.2f} contra "
                             f"{m['sharpe']:.2f}), con un riesgo de {t['riesgo']:.0%}.",
                    "accion": {"metodo": "max_sharpe"}, "etiqueta": "Usar máximo Sharpe"})
    if eq["sharpe"] is not None and m["sharpe"] is not None and eq["sharpe"] >= m["sharpe"] - 0.05:
        out.append({"tipo": "info", "texto": f"Repartir en partes iguales (1/N) da un Sharpe parecido ({eq['sharpe']:.2f}): aquí "
                                             "la optimización casi no agrega valor, y 1/N depende menos de estimaciones históricas."})
    ref = perfil.get("riesgo_ref")
    if ref and m["riesgo"] > ref and s["metodo"] != "min_varianza":
        out.append({"texto": f"El riesgo ({m['riesgo']:.1%} anual) supera lo habitual para un perfil {perfil['nombre'].lower()} "
                             f"(hasta {ref:.0%}). Mínima varianza o agregar ETF lo bajan.",
                    "accion": {"metodo": "min_varianza"}, "etiqueta": "Usar mínima varianza"})
    ids, C = res["correlacion"]["ids"], res["correlacion"]["matriz"]
    pares = sorted(((C[i][j], ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))
                    if C[i][j] > 0.8 and por_id[ids[i]]["peso"] >= 0.005 and por_id[ids[j]]["peso"] >= 0.005), reverse=True)
    for c, a, b in pares[:2]:
        menor = min((a, b), key=lambda x: por_id[x]["peso"])
        out.append({"texto": f"{por_id[a]['clave']} y {por_id[b]['clave']} se mueven casi igual (correlación {c:.2f}): juntos "
                             "diversifican poco.", "accion": {"excluir": menor}, "etiqueta": f"Quitar {por_id[menor]['clave']}"})
    if res["caida_maxima"] < -0.30:
        out.append({"tipo": "info", "texto": f"En la ventana analizada este portafolio llegó a caer {res['caida_maxima']:.0%} desde "
                                             "su máximo. Asegúrese de poder tolerar una caída así."})
    if not res["reglas_reto"]["cumple"]:
        out.append({"tipo": "aviso", "texto": f"Para las reglas del Reto harían falta 5 o más emisoras con peso y ninguna arriba "
                                              f"de 50 % (hoy: {res['reglas_reto']['emisoras']} emisoras, máximo "
                                              f"{res['reglas_reto']['peso_max']:.0%})."})
    return out
