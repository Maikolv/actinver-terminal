"""Walk-forward anidado: en cada frontera la combinación se elige SOLO con las sesiones anteriores (ventana de
selección), se aplica a las siguientes y los tramos se encadenan. El tramo final intacto se evalúa una sola vez."""
from __future__ import annotations

import math

import numpy as np

from . import diseno as dz, estabilidad as es

DIAS = 252


def fronteras(posiciones: np.ndarray, ventana: int = dz.WF["ventana_seleccion"], paso: int = dz.WF["paso"]) -> list[dict]:
    """Índices (en `posiciones`, fechas fuera de muestra antes del tramo intacto) de selección y de aplicación.
    Toda posición de selección es anterior a toda posición de aplicación de su frontera."""
    out = []
    j = ventana
    while j < len(posiciones):
        out.append({"seleccion": posiciones[j - ventana:j], "aplicacion": posiciones[j:j + paso]})
        j += paso
    return out


def _resumen(r: np.ndarray) -> dict:
    if len(r) < 2:
        return {"sesiones": len(r)}
    v = np.cumprod(1 + r)
    return {"sesiones": len(r), "acum": float(v[-1] - 1), "anual": float(v[-1] ** (DIAS / len(r)) - 1),
            "vol": float(r.std() * math.sqrt(DIAS)),
            "caida_max": float((v / np.maximum.accumulate(np.concatenate([[1.0], v]))[1:] - 1).min())}


def seleccionar(netos: dict, netos_1n: dict, pesos: dict, desde: int, hasta: int, respaldo: tuple) -> tuple[tuple, str]:
    """Regla del § 4 con datos en [desde, hasta) únicamente (umbrales 1, 4 y 5)."""
    met = {p: es.metricas(netos[p], netos_1n[p], pesos[p], desde, hasta) for p in netos}
    met = {p: m for p, m in met.items() if "R" in m}
    if not met:
        return respaldo, "sin datos en la ventana: configuración vigente"
    ele = es.elegir(met, es.analizar(met))
    if ele["elegida"] is None:
        return respaldo, "sin meseta en la ventana: configuración vigente"
    return ele["elegida"], f"meseta de {ele['region']['tamano']} combinaciones"


def anidado(netos: dict, netos_1n: dict, pesos: dict, activo_comun: np.ndarray, n: int, actual: tuple) -> dict:
    """`netos[pos]`: serie diaria neta (costos base) de cada combinación sobre el índice completo de fechas."""
    corte = n - dz.INTACTO
    pos_oos = np.flatnonzero(activo_comun[:corte])
    tramos, cadena, cad_act, cad_1n, cad_spp = [], [], [], [], []
    for f in fronteras(pos_oos):
        sel, apl = f["seleccion"], f["aplicacion"]
        elegido, motivo = seleccionar(netos, netos_1n, pesos, int(sel[0]), int(sel[-1]) + 1, actual)
        if not sel[-1] < apl[0]:  # sin filtración: lo elegido solo conoce el pasado
            raise RuntimeError("ventana de selección solapada con la de aplicación")
        cadena.append(netos[elegido][apl])
        cad_act.append(netos[actual][apl])
        cad_1n.append(netos_1n[actual][apl])
        cad_spp.append(np.median(np.vstack([netos[p][apl] for p in netos]), axis=0))
        tramos.append({"seleccion": [int(sel[0]), int(sel[-1])], "aplicacion": [int(apl[0]), int(apl[-1])],
                       "elegida": elegido, "motivo": motivo})
    # tramo intacto: una selección con los datos previos y una sola evaluación
    pos_int = np.flatnonzero(activo_comun[corte:]) + corte
    previo = pos_oos[-dz.WF["ventana_seleccion"]:]
    if len(previo):
        ele_int, mot_int = seleccionar(netos, netos_1n, pesos, int(previo[0]), int(previo[-1]) + 1, actual)
    else:
        ele_int, mot_int = actual, "sin ventana previa"
    unir = (lambda xs: np.concatenate(xs) if xs else np.array([]))
    res = {"tramos": tramos, "fronteras": len(tramos),
           "encadenado": {"anidado": _resumen(unir(cadena)), "actual": _resumen(unir(cad_act)),
                          "iguales_1N": _resumen(unir(cad_1n)), "mediana_SPP": _resumen(unir(cad_spp))},
           "intacto": {"elegida": ele_int, "motivo": mot_int, "sesiones": len(pos_int),
                       "anidado": _resumen(netos[ele_int][pos_int]), "actual": _resumen(netos[actual][pos_int]),
                       "iguales_1N": _resumen(netos_1n[actual][pos_int]),
                       "mediana_SPP": _resumen(np.median(np.vstack([netos[p][pos_int] for p in netos]), axis=0)
                                               if len(pos_int) else np.array([]))}}
    w = dz.WF
    insuf = (res["encadenado"]["anidado"].get("sesiones", 0) < w["min_encadenado"] or len(tramos) < w["min_fronteras"]
             or len(pos_int) < w["min_intacto"])
    res["evidencia"] = "EVIDENCIA INSUFICIENTE" if insuf else "suficiente"
    return res
