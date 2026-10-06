"""Diseño fijo del protocolo de robustez (preregistro: docs/robustez.md). Nada de aquí se ajusta después de ver
resultados; una enmienda se documenta con fecha y se marca como exploratoria."""
from __future__ import annotations

import hashlib
import itertools
import json
from datetime import UTC, datetime

GRID = {"aversion": [0.25, 0.5, 1.0, 2.0, 4.0, 8.0],          # λ (escala ×2)
        "tope": [0.10, 0.12, 0.15, 0.175, 0.20],               # ≤ 0.20 ⇒ ≥ 5 emisoras
        "historia": [126, 168, 252, 378, 504]}                 # sesiones de entrenamiento por rebalanceo
INICIO_PRUEBA = 504      # primera sesión de prueba (igual para todas las combinaciones: mismas fechas)
PASO = 21                # rebalanceo cada 21 sesiones
INTACTO = 63             # tramo final intacto (no se usa para elegir nada)
MIN_ACTIVOS = 10
M_SIM = 500              # simulaciones Monte Carlo por combinación (igual para todas)
BLOQUE = 10              # sesiones por bloque del remuestreo
SEMILLA = 20261113
PERTURBACIONES = {"multiplicador_comision": [0.75, 2.0], "deslizamiento_pb": [0.0, 15.0], "diferencial_sic_pb": [0.0, 60.0]}
UMBRALES = {"exceso_vs_1N_min": 0.0, "prob_perdida_max": 0.45, "p5_caida_min": -0.20, "estabilidad_min": 0.60,
            "pico_dif_pp": 0.10, "pico_decil": 0.90, "meseta_min": 5}
TOLERANCIAS_S = {"R": 0.10, "D": 0.10, "V": 0.10, "C": 0.50}
WF = {"ventana_seleccion": 252, "paso": 63, "min_encadenado": 252, "min_fronteras": 4, "min_intacto": 42}
ACTUALES = {"maximo_rendimiento": {"aversion": 0.5, "tope": 0.20, "historia": 168},
            "ajuste_perfil_moderado": {"aversion": 4.0, "tope": 0.12, "historia": 168}}
DIMS = ("aversion", "tope", "historia")


def combinaciones() -> list[dict]:
    out = []
    for idx, (i, j, k) in enumerate(itertools.product(*(range(len(GRID[d])) for d in DIMS))):
        a, t, h = GRID["aversion"][i], GRID["tope"][j], GRID["historia"][k]
        out.append({"idx": idx, "pos": (i, j, k), "aversion": a, "tope": t, "historia": h,
                    "clave": f"a{a:g}_t{t:g}_h{h}", "semilla": SEMILLA + idx})
    return out


def diseno() -> dict:
    return {"grid": GRID, "inicio_prueba": INICIO_PRUEBA, "paso": PASO, "intacto": INTACTO, "min_activos": MIN_ACTIVOS,
            "m_sim": M_SIM, "bloque": BLOQUE, "semilla": SEMILLA, "perturbaciones": PERTURBACIONES, "umbrales": UMBRALES,
            "tolerancias_estabilidad": TOLERANCIAS_S, "walk_forward": WF, "actuales": ACTUALES}


def huella(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def preregistro(tipo: str, el_l: list[dict], R, perfil: dict, horizonte: dict, fuentes: list[dict], fx: dict,
                costos: dict, reglas: dict) -> dict:
    """Todo lo que se fija ANTES de calcular. Su huella identifica la corrida (y permite reanudarla)."""
    universo = sorted(e["id"] for e in el_l)
    datos = {"desde": str(R.index[0].date()), "hasta": str(R.index[-1].date()), "sesiones": len(R),
             "inicio_prueba": str(R.index[INICIO_PRUEBA].date()) if len(R) > INICIO_PRUEBA else None,
             "inicio_intacto": str(R.index[-INTACTO].date()) if len(R) > INTACTO else None}
    base = {"tipo": tipo, "diseno": diseno(), "universo": universo, "datos": datos}
    return {**base, "huella": huella(base), "creado_en": datetime.now(UTC).isoformat(timespec="seconds"),
            "n_universo": len(universo), "horizonte_reto": horizonte, "fuentes_precios": fuentes, "tipo_cambio": fx,
            "costos_base": costos, "reglas_reto": reglas,
            "perfil": {k: perfil.get(k) for k in ("riesgo", "max_exposicion_usd", "capital")},
            "controles": ["precios en MXN con el FIX de la misma fecha (o el previo, con límite); sin tipo de cambio el dato queda vacío",
                          "SIC = precio de la bolsa de origen × tipo de cambio: referencia, no cotización ejecutable del SIC",
                          "ajuste solo por splits (el Reto no reproduce dividendos)",
                          "excluidos: datos vencidos, sin precio, apalancados/inversos y lo que no está en el catálogo del simulador"]}
