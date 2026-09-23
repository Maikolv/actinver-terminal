"""Comparación de modelos de optimización con la misma validación walk-forward de la propuesta.

Candidatos (skfolio): el modelo vigente (media-varianza con utilidad), 1/N, inversa de la volatilidad,
mínimo CVaR, paridad de riesgo y HRP. Todos usan el mismo universo, los mismos topes por activo, la
misma ventana walk-forward y la misma regla de costos/banda de rebalanceo (`optimizador._walk_forward`).

Honestidad de datos (límite 6): con datos sintéticos del modo demo se calcula y se muestra, pero NO se
declara ganador; el ranking solo es concluyente con precios reales.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from skfolio import RiskMeasure
from skfolio.optimization import (
    EqualWeighted,
    HierarchicalRiskParity,
    InverseVolatility,
    MeanRisk,
    ObjectiveFunction,
    RiskBudgeting,
)

from . import optimizador as opt
from .config import Ajustes, data_dir


def _candidatos(tipo: str, perfil: dict, ajustes: Ajustes, elegibles_l: list[dict], lente: str) -> dict:
    _, tope = opt._parametros_lente(lente, perfil, ajustes)
    tope = max(tope, 1.0 / max(len(elegibles_l), 1) + 0.01)  # que exista solución con universos chicos
    return {
        "vigente (media-varianza)": opt._modelo(tipo, perfil, ajustes, elegibles_l, {}, lente=lente),
        "1/N": EqualWeighted(),
        "inversa de volatilidad": InverseVolatility(),
        "mínimo CVaR 95%": MeanRisk(objective_function=ObjectiveFunction.MINIMIZE_RISK,
                                    risk_measure=RiskMeasure.CVAR, max_weights=tope),
        "paridad de riesgo": RiskBudgeting(risk_measure=RiskMeasure.VARIANCE, max_weights=tope),
        "HRP": HierarchicalRiskParity(max_weights=tope),
    }


def comparar(con: sqlite3.Connection, ajustes: Ajustes, perfil: dict, tipo: str = "acciones",
             lente: str = "ajuste") -> dict:
    perfil = opt.perfil_efectivo(perfil)
    elegibles_l, _, precios = opt.universo(con, ajustes, perfil, tipo, None)
    base = {"tipo": tipo, "lente": lente, "modo": ajustes.modo, "concluyente": ajustes.modo != "demo",
            "calculado_en": datetime.now(UTC).isoformat(timespec="seconds")}
    o = ajustes["optimizacion"]
    minimo = int(o["walk_forward_entrenamiento"]) + int(o["walk_forward_prueba"])
    if len(elegibles_l) < opt.MIN_ACTIVOS:
        return {**base, "estado": "suspendida", "motivos": [f"Sin datos suficientes: {len(elegibles_l)} instrumentos elegibles."]}
    elegibles = {e["id"]: e for e in elegibles_l}
    X = opt.rendimientos(precios, list(elegibles))
    if len(X) < minimo:
        return {**base, "estado": "suspendida", "motivos": [f"{len(X)} sesiones comunes; se requieren {minimo}."]}

    filas = []
    for nombre, modelo in _candidatos(tipo, perfil, ajustes, elegibles_l, lente).items():
        try:
            oos, rot = opt._walk_forward(modelo, X, ajustes, elegibles)
        except Exception as exc:  # un candidato que no converge no debe tumbar la comparación
            filas.append({"modelo": nombre, "error": f"{type(exc).__name__}: {exc}"[:160]})
            continue
        m = opt._metricas(oos)
        filas.append({"modelo": nombre, **m, "giro_medio": float(np.mean(rot)) if rot else None})

    validas = sorted((f for f in filas if f.get("sharpe") is not None), key=lambda f: f["sharpe"], reverse=True)
    ganador = validas[0]["modelo"] if validas and base["concluyente"] else None
    return {**base, "estado": "calculada", "criterio": "Sharpe fuera de muestra, neto de costos",
            "ranking": validas + [f for f in filas if f.get("sharpe") is None], "ganador": ganador,
            "aviso": None if base["concluyente"] else
            "Datos sintéticos (modo demo): resultado solo funcional, no se declara ganador."}


def guardar(resultado: dict) -> Path:
    d = data_dir(resultado["modo"]) / "comparacion_modelos"
    d.mkdir(parents=True, exist_ok=True)
    ruta = d / f"{datetime.now(UTC):%Y-%m-%d}_{resultado['tipo']}_{resultado['lente']}.json"
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
