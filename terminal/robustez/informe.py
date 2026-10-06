"""Ejecuta el protocolo de robustez para un universo («acciones» o «mixta») y guarda el resumen.

Uso: uv run terminal robustez [--tipo acciones|mixta|ambos] [--max-combos N]
Resultados: data/robustez/<tipo>_<huella>/ (preregistro.json, combos/*.npz, resumen.json). Reanudable.
"""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config, mercado, optimizador as op, reto, servicios
from . import calculo, diseno as dz, estabilidad as es, montecarlo as mc, walkforward as wf


def directorio_base() -> Path:
    return config.data_dir() / "robustez"


def _pos(params: dict) -> tuple:
    return tuple(dz.GRID[d].index(params[d]) for d in dz.DIMS)


def _params(pos: tuple) -> dict:
    return {d: dz.GRID[d][i] for d, i in zip(dz.DIMS, pos, strict=True)}


def _pico_mb() -> float | None:
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t)] + [(f"x{i}", ctypes.c_size_t) for i in range(6)]
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return round(c.PeakWorkingSetSize / 2**20)
    except Exception:  # noqa: BLE001
        return None


def preparar(con, ajustes, tipo: str) -> dict:
    perfil = op.perfil_efectivo(servicios.perfil_actual(con, ajustes))
    el_l, excluidos, precios = op.universo(con, ajustes, perfil, tipo, None)
    el = {e["id"]: e for e in el_l}
    ids = list(el)
    R = precios[ids].ffill(limit=3).pct_change(fill_method=None)
    R = R.loc[R.notna().sum(axis=1) >= dz.MIN_ACTIVOS]
    costos = pd.Series({c: op.costo_unitario(el[c], ajustes) for c in ids})
    sic = {c for c in ids if el[c].get("mercado_operable") == "BMV-SIC"}
    marcas = ",".join("?" * len(ids))
    fuentes = [{"proveedor": r[0], "instrumentos": r[1], "desde": r[2], "hasta": r[3]} for r in con.execute(
        f"SELECT proveedor, COUNT(DISTINCT instrumento_id), MIN(fecha), MAX(fecha) FROM precios WHERE instrumento_id IN "
        f"({marcas}) GROUP BY proveedor", ids)]
    ahora = datetime.now(UTC)
    horizonte = {"hasta": "2026-11-13 15:00 (cierre del Reto)", "sesiones": reto.sesiones_restantes(ahora),
                 "calculado_en": ahora.isoformat(timespec="seconds")}
    rc = reto.config() if reto.activo() else {}
    pre = dz.preregistro(tipo, el_l, R, perfil, horizonte, fuentes, mercado.ultimo_fx(con, ajustes),
                         {"comision_con_iva": reto.costo_operacion(), "por_clase": sorted({round(float(x), 6) for x in costos})},
                         {"reglas": rc.get("reglas"), "fechas": rc.get("fechas")})
    pre["excluidos"] = len(excluidos)
    return {"perfil": perfil, "el": el, "R": R, "costos": costos, "sic": sic, "pre": pre}


def ejecutar(con, ajustes, tipo: str = "acciones", max_combos: int | None = None, progreso=print,
             base: Path | None = None) -> dict:
    t0 = time.time()
    d = preparar(con, ajustes, tipo)
    pre, R = d["pre"], d["R"]
    carpeta = (base or directorio_base()) / f"{tipo}_{pre['huella']}"
    carpeta.mkdir(parents=True, exist_ok=True)
    if not (carpeta / "preregistro.json").exists():  # se fija antes de calcular cualquier resultado
        (carpeta / "preregistro.json").write_text(json.dumps(pre, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    combos = dz.combinaciones()[:max_combos] if max_combos else dz.combinaciones()
    lote = calculo.correr(carpeta, combos, pre["huella"], tipo, d["perfil"], ajustes, d["el"], R, d["costos"], d["sic"],
                          progreso)
    n = len(R)
    datos = {tuple(c["pos"]): calculo.cargar(carpeta / "combos" / f"{c['clave']}.npz") for c in combos}
    netos = {p: x["bruto"]["estrategia"] - x["costo"]["estrategia"] for p, x in datos.items()}
    netos_1n = {p: x["bruto"]["iguales"] - x["costo"]["iguales"] for p, x in datos.items()}
    pesos = {p: [(s, w) for s, w in x["pesos"]] for p, x in datos.items()}
    activo = np.logical_and.reduce([x["activo"] for x in datos.values()])
    corte = n - dz.INTACTO
    pos_oos = np.flatnonzero(activo[:corte])
    if len(pos_oos) < dz.BLOQUE * 3:
        return {"estado": "EVIDENCIA INSUFICIENTE", "motivo": f"{len(pos_oos)} sesiones fuera de muestra", "preregistro": pre}
    desde = int(pos_oos[0])
    met = {p: es.metricas(netos[p], netos_1n[p], pesos[p], desde, corte) for p in datos}
    H = int(pre["horizonte_reto"]["sesiones"]) or 1
    sims = {}
    for c in combos:  # Monte Carlo en TODAS las combinaciones, con el mismo M
        p, x = tuple(c["pos"]), datos[tuple(c["pos"])]
        sims[p] = mc.simular(*(x[k]["estrategia"][pos_oos] for k in ("bruto", "costo", "giro", "giro_sic")), H, c["semilla"])
    ana = es.analizar(met, sims)
    ele = es.elegir(met, ana)
    actual = _pos(dz.ACTUALES["maximo_rendimiento"]) if _pos(dz.ACTUALES["maximo_rendimiento"]) in datos else next(iter(datos))
    anid = wf.anidado(netos, netos_1n, pesos, activo, n, actual)
    pos_int = np.flatnonzero(activo[corte:]) + corte
    Rs = np.array([m["R"] for m in met.values()])

    def ficha(p):
        return {"params": _params(p), "oos": {k: met[p][k] for k in ("R", "D", "V", "exceso_1N", "acum", "n")},
                "montecarlo": sims[p], "S": ana[p]["S"], "R_robusto": ana[p]["R_robusto"], "pico_aislado": ana[p]["pico_aislado"],
                "criterios": ana[p]["criterios"], "aprobada": ana[p]["aprobada"],
                "motivos_rechazo": [k for k, v in ana[p]["criterios"].items() if not v]}
    elegida = ele["elegida"]
    res = {
        "estado": "ok", "tipo": tipo, "huella": pre["huella"], "creado_en": datetime.now(UTC).isoformat(timespec="seconds"),
        "fechas": {"datos": pre["datos"], "oos_desde": str(R.index[desde].date()), "oos_hasta": str(R.index[corte - 1].date()),
                   "intacto_desde": str(R.index[corte].date()), "intacto_hasta": str(R.index[-1].date())},
        "cobertura": {"universo": pre["n_universo"], "excluidos": pre["excluidos"], "sesiones_oos": len(pos_oos),
                      "sesiones_intacto": len(pos_int)},
        "combinaciones": len(combos), "simulaciones_por_combinacion": sorted({s.get("m", 0) for s in sims.values()}),
        "horizonte_sesiones": H, "lote": lote,
        "spp": {"mediana_R": float(np.median(Rs)), "p25_R": float(np.quantile(Rs, 0.25)), "p75_R": float(np.quantile(Rs, 0.75)),
                "pct_supera_1N": float(np.mean([m["exceso_1N"] > 0 for m in met.values()])),
                "mediana_prob_perdida": float(np.median([s["prob_perdida"] for s in sims.values()]))},
        "regiones": [{**{k: v for k, v in r.items() if k != "posiciones"}, "combinaciones": [_params(p) for p in r["posiciones"]]}
                     for r in ele["regiones"]],
        "pct_aprobadas": ele["pct_aprobadas"], "veredicto": ele["veredicto"],
        "elegida": ficha(elegida) if elegida else None, "distancia_borde": ele.get("distancia_borde"),
        "elegida_en_intacto": wf._resumen(netos[elegida][pos_int]) if elegida else None,
        "actuales": {k: ficha(_pos(v)) for k, v in dz.ACTUALES.items() if _pos(v) in datos},
        "walk_forward": {**anid, "tramos": [{**t, "elegida": _params(t["elegida"])} for t in anid["tramos"]],
                         "intacto": {**anid["intacto"], "elegida": _params(anid["intacto"]["elegida"])}},
        "combos": [ficha(tuple(c["pos"])) for c in combos],
        "mapas": es.mapas(met, ana, sims),
        "recursos": {"segundos": round(time.time() - t0, 1), "pico_memoria_mb": _pico_mb()},
        "aviso": ("Histórico fuera de muestra y simulación Monte Carlo (remuestreo del pasado con costos perturbados); no son "
                  "pronósticos ni garantías. SIC = referencia de origen × tipo de cambio, no cotización ejecutable."),
    }
    (carpeta / "resumen.json").write_text(json.dumps(res, ensure_ascii=False, default=str), encoding="utf-8")
    (directorio_base() if base is None else base).joinpath(f"ultimo_{tipo}.json").write_text(
        json.dumps({"carpeta": str(carpeta)}), encoding="utf-8")
    return res


def ultimo(tipo: str = "acciones", base: Path | None = None) -> dict | None:
    f = (base or directorio_base()) / f"ultimo_{tipo}.json"
    if not f.exists():
        return None
    r = Path(json.loads(f.read_text(encoding="utf-8"))["carpeta"]) / "resumen.json"
    return json.loads(r.read_text(encoding="utf-8")) if r.exists() else None


# ---------------------------------------------------------------------------------------------------------------
# Estado de robustez de una propuesta: sus parámetros efectivos llevados al punto más cercano de la cuadrícula
_cache: dict[str, tuple[float, dict | None]] = {}


def _resumen_vigente(tipo: str) -> dict | None:
    f = directorio_base() / f"ultimo_{tipo}.json"
    try:
        r = Path(json.loads(f.read_text(encoding="utf-8"))["carpeta"]) / "resumen.json"
        m = r.stat().st_mtime
    except (OSError, ValueError, KeyError):
        return None
    if tipo not in _cache or _cache[tipo][0] != m:
        _cache[tipo] = (m, json.loads(r.read_text(encoding="utf-8")))
    return _cache[tipo][1]


def parametros_propuesta(p: dict) -> dict | None:
    """λ efectivo, tope por activo e historia de estimación de una propuesta guardada (None si no aplica)."""
    rep = p.get("reproducibilidad") or {}
    if not rep.get("aversion_riesgo_lambda"):
        return None
    tope = {"rendimiento": 0.20, "puntuacion": ((p.get("busqueda_puntuacion") or {}).get("elegido") or {}).get("tope")}.get(
        p.get("lente"), (p.get("perfil_efectivo") or {}).get("max_peso_activo"))
    historia = (rep.get("ventana_estimacion") or {}).get("sesiones")
    if tope is None or historia is None:
        return None
    return {"aversion": float(rep["aversion_riesgo_lambda"]), "tope": float(tope), "historia": int(historia)}


def _cercano(params: dict) -> dict:
    import math
    return {"aversion": min(dz.GRID["aversion"], key=lambda v: abs(math.log(v) - math.log(max(params["aversion"], 1e-6)))),
            "tope": min(dz.GRID["tope"], key=lambda v: abs(v - params["tope"])),
            "historia": min(dz.GRID["historia"], key=lambda v: abs(v - params["historia"]))}


MOTIVOS_SENCILLOS = {
    "exceso_vs_1N": "en el histórico no superó a repartir el dinero en partes iguales",
    "prob_perdida": "en la simulación pierde en más del 45 % de los casos",
    "caida_p5": "en la simulación, 1 de cada 20 casos cae más del 20 % antes del cierre",
    "estabilidad": "cambia mucho con ajustes pequeños de sus parámetros",
    "no_pico_aislado": "su buen resultado es un pico aislado: sus vecinos rinden mucho menos"}


def motivos_sencillos(motivos: list[str]) -> list[str]:
    return [MOTIVOS_SENCILLOS.get(m, m) for m in motivos]


def estado_propuesta(p: dict | None) -> dict:
    """robusta / no aprobada / frágil / sin evaluar, con motivos.
    Frágil = pico aislado o estabilidad S bajo el umbral (no puede ser la referencia del plan si hay alternativa).
    No aprobada = estable, pero falla un umbral de rendimiento o de riesgo (exceso vs 1/N, prob. de pérdida, caída p5):
    se informa con sus motivos y la decisión queda en el usuario (enmienda 1 de docs/robustez.md, 6-oct-2026)."""
    if not p or p.get("mercado_variante"):
        return {"estado": "sin evaluar", "motivo": "variante por mercado (universo distinto al del protocolo)"}
    r = _resumen_vigente(p.get("tipo", ""))
    params = parametros_propuesta(p)
    if not r or r.get("estado") != "ok" or not params:
        return {"estado": "sin evaluar", "motivo": "sin corrida del protocolo de robustez para este universo"}
    c = _cercano(params)
    f = next((x for x in r["combos"] if x["params"] == c), None)
    if not f:
        return {"estado": "sin evaluar", "motivo": "combinación fuera de la cuadrícula evaluada"}
    fragil = f["pico_aislado"] or not f["criterios"].get("estabilidad", True)
    return {"estado": "robusta" if f["aprobada"] else "frágil" if fragil else "no aprobada", "combinacion": c,
            "parametros_efectivos": params, "motivos": f["motivos_rechazo"], "pico_aislado": f["pico_aislado"], "S": f["S"],
            "historico_R": f["oos"]["R"], "simulacion_prob_perdida": f["montecarlo"].get("prob_perdida"),
            "simulacion_p5": f["montecarlo"].get("ret_p5"), "simulacion_caida_p5": f["montecarlo"].get("caida_p5"),
            "corrida": r["huella"], "fecha": r["creado_en"]}
