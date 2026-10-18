"""Investigación EDUCATIVA de momentum temporal (TSM) mensual, largo/efectivo, separada de la estrategia activa.

Pasos públicos del reel (DejEnwmBclA, docs/instagram-2026-10-17.md): chequeo mensual; comparar el último cierre
mensual con el de L ∈ {3, 6, 12} meses antes; L elegido por mercado SOLO con entrenamiento; largo si subió, fuera si
bajó (corto solo en forex, que aquí no se usa); sin stop ni target; tamaño por rango diario medio.
Lo que el reel NO publica y aquí se completa como ADAPTACIÓN PROPIA (no es reproducción fiel): periodo del rango,
importe de riesgo, igualdad, datos, ejecución/fills y costos. Ver docs/tsm-mensual.md.

Sin fuga temporal: la señal usa el cierre de la última sesión del mes k y se ejecuta al cierre de la sesión siguiente;
el rendimiento del periodo va de esa ejecución a la siguiente. El holdout se evalúa una sola vez por preregistro.
Nada de esto modifica propuestas, plan ni cartera, ni se traslada a operación intradía.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from . import laboratorio, reto

VERSION = "tsm-mensual 1.0"
LOOKBACKS = (3, 6, 12)
MERCADOS_DEFECTO = ["SPY", "QQQ", "DIA", "EEM", "GLD", "NAFTRACISHRS.MX"]
PENDIENTES_DEL_AUTOR = [
    "Periodo del rango diario medio y el importe monetario de riesgo por operación.",
    "Tratamiento de la igualdad (cierre actual = cierre de L meses antes).",
    "Dataset, licencia, instrumento/contrato exacto (US100/US500 no son NQ/ES) y fechas exactas de entrenamiento.",
    "Precio y hora de entrada/salida (fills) y costos completos (comisión, swap, deslizamiento).",
]


def _huella(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def fin_de_mes(P: pd.Series) -> pd.Series:
    """Cierre de la última sesión de cada mes calendario COMPLETO (descarta el mes en curso del último dato)."""
    P = P.dropna()
    ultimos = P.groupby(P.index.to_period("M")).tail(1)
    if len(ultimos) and ultimos.index[-1] < (ultimos.index[-1] + pd.offsets.BMonthEnd(0)).normalize():
        ultimos = ultimos.iloc[:-1]                      # mes incompleto: su último dato no es fin de mes
    return ultimos


def periodos(P: pd.Series, L: int, costo: float, riesgo_pct: float | None = None, ventana_rango: int = 20,
             igualdad: str = "fuera") -> pd.DataFrame:
    """Un renglón por mes k con señal: fecha_senal, fecha_ejecucion, exposición y rendimientos del periodo
    (estrategia neta y comprar-y-mantener) hasta la ejecución siguiente."""
    P = P.dropna().astype(float)
    M = fin_de_mes(P)
    idx = P.index
    filas, previa = [], 0.0
    for k in range(L, len(M) - 1):
        t_sen, t_sig = M.index[k], M.index[k + 1]
        cambio = M.iloc[k] / M.iloc[k - L] - 1
        largo = cambio > 0 or (cambio == 0 and igualdad == "largo")
        i_ej, i_sig = idx.get_loc(t_sen) + 1, idx.get_loc(t_sig) + 1
        if i_sig >= len(idx):
            break                                         # aún no existe la ejecución del periodo siguiente
        expo = 1.0 if largo else 0.0
        if largo and riesgo_pct:
            r = P.iloc[: idx.get_loc(t_sen) + 1].pct_change().abs().tail(ventana_rango)
            rango = float(r.mean()) if len(r) == ventana_rango else math.nan
            expo = min(1.0, riesgo_pct / rango) if rango and math.isfinite(rango) else 0.0
        bruto = P.iloc[i_sig] / P.iloc[i_ej] - 1
        neto = expo * bruto - costo * abs(expo - previa)
        filas.append({"fecha_senal": t_sen, "fecha_ejecucion": idx[i_ej], "cambio_lookback": float(cambio),
                      "exposicion": expo, "estrategia": float(neto), "comprar_y_mantener": float(bruto)})
        previa = expo
    return pd.DataFrame(filas)


def _metricas(r: pd.Series) -> dict:
    if not len(r):
        return {"meses": 0}
    acum = (1 + r).cumprod()
    return {"meses": int(len(r)), "media_mensual": float(r.mean()), "rend_total": float(acum.iloc[-1] - 1),
            "vol_anual": float(r.std(ddof=1) * math.sqrt(12)) if len(r) > 1 else None,
            "max_drawdown": float((acum / acum.cummax() - 1).min())}


def _config(d: dict) -> dict:
    mercados = d.get("mercados") or MERCADOS_DEFECTO
    if not isinstance(mercados, list) or not 1 <= len(mercados) <= 12 or any(not isinstance(m, str) for m in mercados):
        raise ValueError("mercados: lista de 1 a 12 columnas de la historia externa")
    try:
        c = {"version": VERSION, "mercados": mercados, "corte": str(pd.Period(str(d.get("corte") or "2018-01"), "M")),
             "embargo_meses": int(d.get("embargo_meses", 1)), "deslizamiento_pb": float(d.get("deslizamiento_pb", 5)),
             "riesgo_pct": None if d.get("riesgo_pct") in (None, "") else float(d["riesgo_pct"]) / 100,
             "ventana_rango": int(d.get("ventana_rango", 20)), "igualdad": str(d.get("igualdad") or "fuera"),
             "B": int(d.get("B", 4999)), "semilla": int(d.get("semilla", 2026)), "bloque": int(d.get("bloque", 3)),
             "alpha": float(d.get("alpha", 0.05))}
    except (TypeError, ValueError):
        raise ValueError("parámetros inválidos (corte AAAA-MM, números en los demás)") from None
    if c["igualdad"] not in ("fuera", "largo") or not 0 <= c["embargo_meses"] <= 12 or not 0 <= c["deslizamiento_pb"] <= 200 \
            or not 5 <= c["ventana_rango"] <= 250 or (c["riesgo_pct"] is not None and not 0 < c["riesgo_pct"] <= 0.1):
        raise ValueError("igualdad fuera|largo, embargo 0–12, deslizamiento 0–200 pb, ventana 5–250, riesgo 0–10 %")
    return c


def correr(precios: pd.DataFrame, c: dict) -> dict:
    """Selecciona L por mercado con el entrenamiento y evalúa el holdout con la configuración congelada."""
    costo = (reto.costo_operacion() or 0.0) + c["deslizamiento_pb"] / 1e4
    corte = pd.Period(c["corte"], "M")
    inicio_hold = (corte + c["embargo_meses"]).to_timestamp()
    variantes, holdout, excesos = [], {}, {}
    for m in c["mercados"]:
        if m not in precios.columns:
            raise ValueError(f"mercado sin historia: {m}")
        mejor = None
        for L in LOOKBACKS:
            df = periodos(precios[m], L, costo, c["riesgo_pct"], c["ventana_rango"], c["igualdad"])
            ent = df[df["fecha_ejecucion"] < corte.to_timestamp()]
            met = _metricas(ent["estrategia"])
            variantes.append({"mercado": m, "lookback": L, "entrenamiento": met})
            if met["meses"] >= 24 and (mejor is None or met["media_mensual"] > mejor[1]):
                mejor = (L, met["media_mensual"], df)
        if mejor is None:
            holdout[m] = {"elegido": None, "motivo": "menos de 24 meses de entrenamiento"}
            continue
        L, _, df = mejor
        h = df[df["fecha_ejecucion"] >= inicio_hold]
        holdout[m] = {"elegido": L, "estrategia": _metricas(h["estrategia"]), "comprar_y_mantener": _metricas(h["comprar_y_mantener"]),
                      "exposicion_media": float(h["exposicion"].mean()) if len(h) else None,
                      "desde": str(h["fecha_ejecucion"].min().date()) if len(h) else None,
                      "hasta": str(h["fecha_ejecucion"].max().date()) if len(h) else None}
        excesos[m] = (h["estrategia"].tolist(), h["comprar_y_mantener"].tolist())
    prueba = None
    usables = {m: v for m, v in excesos.items() if len(v[0]) >= laboratorio.MIN_N}
    if usables:
        n = min(len(v[0]) for v in usables.values())     # mismos meses finales para toda la familia
        bench = [0.0] * n                                # exceso ya restado: se contrasta contra 0
        est = {m: [a - b for a, b in zip(v[0][-n:], v[1][-n:])] for m, v in usables.items()}
        try:
            prueba = laboratorio.permutacion(bench, est, c["bloque"], c["B"], c["semilla"], c["alpha"],
                                             exploradas=len(variantes))
        except ValueError as e:
            prueba = {"error": str(e)}
    return {"variantes": variantes, "holdout": holdout, "prueba_permutacion": prueba, "costo_por_cambio": costo}


def _tabla(con) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS tsm_experimentos (id INTEGER PRIMARY KEY, creado_en TEXT NOT NULL,
      config TEXT NOT NULL, huella_config TEXT NOT NULL, evaluado_en TEXT, huella_datos TEXT, resultado TEXT)""")


def preregistrar(con, d: dict) -> dict:
    c = _config(d if isinstance(d, dict) else {})
    _tabla(con)
    ahora = datetime.now(UTC).isoformat()
    h = _huella({**c, "creado_en": ahora})
    cur = con.execute("INSERT INTO tsm_experimentos (creado_en, config, huella_config) VALUES (?,?,?)", (ahora, json.dumps(c), h))
    con.commit()
    return {"id": cur.lastrowid, "creado_en": ahora, "huella_config": h, "config": c}


def evaluar(con, eid: int, precios: pd.DataFrame) -> dict:
    _tabla(con)
    f = con.execute("SELECT * FROM tsm_experimentos WHERE id=?", (eid,)).fetchone()
    if f is None:
        raise LookupError("experimento no encontrado")
    if f["resultado"]:
        return {**json.loads(f["resultado"]), "holdout_ya_usado": True}
    c = json.loads(f["config"])
    datos = precios[[m for m in c["mercados"] if m in precios.columns]].dropna(how="all")
    hd = _huella({"i": [str(x.date()) for x in datos.index], "c": list(datos.columns),
                  "v": np.nan_to_num(datos.round(6).values, nan=-1).tolist()})
    res = {"id": eid, "config": c, "huella_config": f["huella_config"], "huella_datos": hd, **correr(datos, c),
           "pendientes_del_autor": PENDIENTES_DEL_AUTOR,
           "lectura": "Adaptación propia de los pasos públicos del reel; no reproduce su backtest de ticks. El holdout se "
                      "evaluó una vez con L elegido en entrenamiento. Un exceso no significativo o negativo es un resultado "
                      "válido. No cambia la estrategia activa ni se traslada a intradía; no es recomendación."}
    res["evaluado_en"] = datetime.now(UTC).isoformat()
    con.execute("UPDATE tsm_experimentos SET evaluado_en=?, huella_datos=?, resultado=? WHERE id=? AND resultado IS NULL",
                (res["evaluado_en"], hd, json.dumps(res, default=str), eid))
    con.commit()
    return {**res, "holdout_ya_usado": False}


def historia() -> pd.DataFrame:
    """Cierres diarios en moneda de origen de la historia externa del usuario (docs/historia-externa.md)."""
    from . import historia_externa
    return historia_externa.cargar()


def experimentos(con) -> list[dict]:
    _tabla(con)
    return [{"id": r["id"], "creado_en": r["creado_en"], "evaluado_en": r["evaluado_en"], "huella_config": r["huella_config"],
             "config": json.loads(r["config"])} for r in con.execute("SELECT * FROM tsm_experimentos ORDER BY id DESC LIMIT 50")]
