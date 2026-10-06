"""Estabilidad de parámetros, picos aislados, aprobación, regiones contiguas (SPP y clústeres) y mapas de calor.
Fórmulas y umbrales: docs/robustez.md (§ 2 y § 4)."""
from __future__ import annotations

import math
from collections import deque

import numpy as np

from . import diseno as dz

DIAS = 252


def forma() -> tuple[int, int, int]:
    return tuple(len(dz.GRID[d]) for d in dz.DIMS)


def vecinas(pos: tuple, shape: tuple | None = None) -> list[tuple]:
    """Vecindad de von Neumann: un paso en una sola dimensión."""
    shape = shape or forma()
    out = []
    for d in range(len(pos)):
        for s in (-1, 1):
            q = list(pos)
            q[d] += s
            if 0 <= q[d] < shape[d]:
                out.append(tuple(q))
    return out


def metricas(neto: np.ndarray, neto_1n: np.ndarray, pesos: list[tuple[int, dict]], desde: int, hasta: int) -> dict:
    """Rendimiento anual (R), caída máxima (D), volatilidad (V), exceso frente a 1/N y pesos promedio en [desde, hasta)."""
    r, r1 = neto[desde:hasta], neto_1n[desde:hasta]
    if len(r) < 2:
        return {"n": len(r)}
    v = np.cumprod(1 + r)
    caida = float((v / np.maximum.accumulate(np.concatenate([[1.0], v]))[1:] - 1).min())
    w = {}
    sel = [p for s, p in pesos if desde <= s < hasta]
    for p in sel:
        for k, x in p.items():
            w[k] = w.get(k, 0.0) + x / len(sel)
    return {"n": len(r), "R": float(v[-1] ** (DIAS / len(r)) - 1), "D": caida, "V": float(r.std() * math.sqrt(DIAS)),
            "exceso_1N": float((r.mean() - r1.mean()) * DIAS), "acum": float(v[-1] - 1), "w": w}


def composicion(a: dict, b: dict) -> float:
    """½·Σ|w_a − w_b|: 0 = misma cartera, 1 = carteras disjuntas."""
    return 0.5 * sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in set(a) | set(b))


def indice(c: dict, vs: list[dict]) -> float:
    """S(c) = 1 − ¼·[min(1, sd(R)/τR) + min(1, sd(D)/τD) + min(1, sd(V)/τV) + min(1, C/τC)] sobre c y sus vecinas."""
    t = dz.TOLERANCIAS_S
    grupo = [c, *vs]
    comp = float(np.mean([composicion(c["w"], v["w"]) for v in vs])) if vs else 0.0
    partes = [min(1.0, float(np.std([g[k] for g in grupo])) / t[k]) for k in ("R", "D", "V")] + [min(1.0, comp / t["C"])]
    return 1 - sum(partes) / 4


def analizar(met: dict[tuple, dict], mc: dict[tuple, dict] | None = None) -> dict[tuple, dict]:
    """Por combinación: S, rendimiento robusto (mediana de la vecindad), pico aislado, umbrales y aprobación.
    Sin `mc` (dentro de una ventana del walk-forward) se usan solo los umbrales 1, 4 y 5."""
    u = dz.UMBRALES
    Rs = np.array([m["R"] for m in met.values()])
    decil = float(np.quantile(Rs, u["pico_decil"]))
    out = {}
    for pos, m in met.items():
        vs = [met[q] for q in vecinas(pos) if q in met]
        med_v = float(np.median([v["R"] for v in vs])) if vs else m["R"]
        pico = bool(m["R"] - med_v > u["pico_dif_pp"] and m["R"] >= decil)
        s = indice(m, vs)
        crit = {"exceso_vs_1N": m["exceso_1N"] > u["exceso_vs_1N_min"], "estabilidad": s >= u["estabilidad_min"],
                "no_pico_aislado": not pico}
        if mc is not None:
            x = mc.get(pos) or {}
            crit["prob_perdida"] = x.get("prob_perdida", 1.0) <= u["prob_perdida_max"]
            crit["caida_p5"] = x.get("caida_p5", -1.0) >= u["p5_caida_min"]
        out[pos] = {"S": s, "R_robusto": float(np.median([m["R"], *[v["R"] for v in vs]])), "pico_aislado": pico,
                    "criterios": crit, "aprobada": all(crit.values())}
    return out


def regiones(aprobadas: set[tuple]) -> list[list[tuple]]:
    """Componentes conexas (búsqueda en anchura, vecindad de von Neumann) de las combinaciones aprobadas."""
    vistas, out = set(), []
    for p in sorted(aprobadas):
        if p in vistas:
            continue
        cola, comp = deque([p]), []
        vistas.add(p)
        while cola:
            x = cola.popleft()
            comp.append(x)
            for q in vecinas(x):
                if q in aprobadas and q not in vistas:
                    vistas.add(q)
                    cola.append(q)
        out.append(sorted(comp))
    return sorted(out, key=len, reverse=True)


def distancia_borde(pos: tuple, region: set[tuple]) -> int:
    """Pasos hasta la celda más cercana fuera de la región (salir de la cuadrícula cuenta como borde)."""
    shape = forma()
    cola, vistas = deque([(pos, 0)]), {pos}
    while cola:
        x, d = cola.popleft()
        for dim in range(len(x)):
            for s in (-1, 1):
                q = list(x)
                q[dim] += s
                q = tuple(q)
                if not (0 <= q[dim] < shape[dim]) or q not in region:
                    return d + 1
                if q not in vistas:
                    vistas.add(q)
                    cola.append((q, d + 1))
    return 0


def elegir(met: dict, ana: dict) -> dict:
    """Regla preregistrada: meseta más grande (≥ meseta_min); dentro, mayor R robusto; empate → más lejos del borde."""
    regs = regiones({p for p, a in ana.items() if a["aprobada"]})
    info = [{"tamano": len(r), "posiciones": r, "R_media": float(np.mean([met[p]["R"] for p in r])),
             "R_desv": float(np.std([met[p]["R"] for p in r])), "R_rango": [float(min(met[p]["R"] for p in r)),
                                                                          float(max(met[p]["R"] for p in r))],
             "tipo": "meseta" if len(r) >= dz.UMBRALES["meseta_min"] else "máximo aislado"} for r in regs]
    mesetas = [r for r in info if r["tipo"] == "meseta"]
    base = {"regiones": info, "pct_aprobadas": sum(a["aprobada"] for a in ana.values()) / max(len(ana), 1)}
    if not mesetas:
        return {**base, "elegida": None, "veredicto": "SIN REGIÓN ROBUSTA"}
    r = set(mesetas[0]["posiciones"])
    p = max(r, key=lambda x: (ana[x]["R_robusto"], distancia_borde(x, r)))
    return {**base, "elegida": p, "region": mesetas[0], "distancia_borde": distancia_borde(p, r), "veredicto": "MESETA"}


def mapas(met: dict, ana: dict, mc: dict) -> list[dict]:
    """Mapas de calor por pares de parámetros; la tercera dimensión se filtra por valor o por la mediana (SPP)."""
    out = []
    campos = {"R": lambda p: met[p]["R"], "exceso_1N": lambda p: met[p]["exceso_1N"], "S": lambda p: ana[p]["S"],
              "prob_perdida": lambda p: mc[p].get("prob_perdida"), "ret_p5": lambda p: mc[p].get("ret_p5"),
              "caida_p5": lambda p: mc[p].get("caida_p5"), "aprobada": lambda p: float(ana[p]["aprobada"])}
    shape = forma()
    for a, b in ((0, 1), (0, 2), (1, 2)):
        c = 3 - a - b
        for filtro in [*range(shape[c]), "mediana"]:
            celdas = {}
            for nombre, f in campos.items():
                mat = np.full((shape[a], shape[b]), np.nan)
                for i in range(shape[a]):
                    for j in range(shape[b]):
                        vals = []
                        for k in (range(shape[c]) if filtro == "mediana" else [filtro]):
                            pos = [0, 0, 0]
                            pos[a], pos[b], pos[c] = i, j, k
                            v = f(tuple(pos)) if tuple(pos) in met else None
                            if v is not None:
                                vals.append(v)
                        mat[i, j] = float(np.median(vals)) if vals else np.nan
                celdas[nombre] = [[None if np.isnan(x) else round(float(x), 4) for x in fila] for fila in mat]
            out.append({"x": dz.DIMS[b], "y": dz.DIMS[a], "filtro_dim": dz.DIMS[c],
                        "filtro_valor": "mediana" if filtro == "mediana" else dz.GRID[dz.DIMS[c]][filtro],
                        "eje_x": dz.GRID[dz.DIMS[b]], "eje_y": dz.GRID[dz.DIMS[a]], "celdas": celdas})
    return out
