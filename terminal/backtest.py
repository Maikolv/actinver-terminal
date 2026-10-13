"""Backtesting reproducible de estrategias simples sobre cierres diarios (solo simulación; nunca envía órdenes).

Reglas contra la fuga de información:
- La señal del día t usa solo cierres hasta t; la operación se ejecuta al CIERRE DEL DÍA HÁBIL SIGUIENTE (t+1).
- Calendario: las sesiones con precio en la matriz (BMV y EE. UU. combinadas); un instrumento sin precio ese día no
  se opera ni se valúa con un precio inventado (se arrastra el último hasta 3 sesiones).
- Costos: comisión del Reto (comisión + IVA, `config/reto.yaml`) + deslizamiento en puntos base sobre cada importe operado.

Reproducibilidad: cada corrida se guarda con la estrategia y su versión, los parámetros, la huella de los datos de
entrada (sha256 de la matriz de precios usada), la versión del código y el resultado. Repetir los mismos parámetros sobre
los mismos datos da la misma huella y el mismo resultado.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from . import __version__, db, mercado, reto

ESTRATEGIAS = {
    "comprar_y_mantener": {"version": "1.0", "nombre": "Comprar y mantener (pesos iguales al inicio)", "parametros": {}},
    "pesos_iguales": {"version": "1.0", "nombre": "Pesos iguales con rebalanceo periódico", "parametros": {"rebalanceo": 21}},
    "cruce_medias": {"version": "1.0", "nombre": "Cruce de medias (largo si SMA rápida > SMA lenta; si no, efectivo)",
                     "parametros": {"rapida": 20, "lenta": 50, "rebalanceo": 1}},
    "momento": {"version": "1.0", "nombre": "Momento: los k mejores por rendimiento de N sesiones",
                "parametros": {"lookback": 126, "k": 3, "rebalanceo": 21}},
}
LIMITES = {"rebalanceo": (1, 252), "rapida": (2, 200), "lenta": (3, 400), "lookback": (5, 504), "k": (1, 30)}
CAPITAL = 1_000_000.0


def inicializar(con) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS backtests (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
                "estrategia TEXT NOT NULL, version TEXT NOT NULL, parametros TEXT NOT NULL, huella_config TEXT NOT NULL, "
                "huella_datos TEXT NOT NULL, version_codigo TEXT NOT NULL, resumen TEXT NOT NULL, resultado TEXT NOT NULL)")


def _parametros(estrategia: str, p: dict) -> dict:
    if estrategia not in ESTRATEGIAS:
        raise ValueError("estrategia desconocida: " + ", ".join(ESTRATEGIAS))
    out = dict(ESTRATEGIAS[estrategia]["parametros"])
    for k, v in (p or {}).items():
        if k not in out:
            continue
        try:
            x = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"{k}: entero inválido") from None
        lo, hi = LIMITES[k]
        if not lo <= x <= hi:
            raise ValueError(f"{k}: de {lo} a {hi}")
        out[k] = x
    if estrategia == "cruce_medias" and out["rapida"] >= out["lenta"]:
        raise ValueError("la media rápida debe ser menor que la lenta")
    return out


def _objetivo(estrategia: str, p: dict, hist: pd.DataFrame, disponibles: list[str], i: int) -> pd.Series | None:
    """Pesos objetivo con datos hasta el cierre de hoy (hist termina hoy). None = no rebalancear hoy."""
    if estrategia == "comprar_y_mantener":
        return pd.Series(1 / len(disponibles), index=disponibles) if i == 0 else None
    if i % p["rebalanceo"]:
        return None
    if estrategia == "pesos_iguales":
        return pd.Series(1 / len(disponibles), index=disponibles)
    if estrategia == "cruce_medias":
        largos = [c for c in disponibles if hist[c].notna().sum() >= p["lenta"]
                  and hist[c].tail(p["rapida"]).mean() > hist[c].tail(p["lenta"]).mean()]
        return pd.Series(1 / len(disponibles), index=largos) if largos else pd.Series(dtype=float)
    # momento
    rend = {c: hist[c].iloc[-1] / hist[c].iloc[-1 - p["lookback"]] - 1 for c in disponibles
            if hist[c].notna().sum() > p["lookback"] and pd.notna(hist[c].iloc[-1 - p["lookback"]])}
    mejores = sorted(rend, key=rend.get, reverse=True)[:p["k"]]
    return pd.Series(1 / len(mejores), index=mejores) if mejores else pd.Series(dtype=float)


def _huella(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def correr(P: pd.DataFrame, estrategia: str, parametros: dict, desde: str, hasta: str, comision: float,
           deslizamiento_pb: float, capital: float = CAPITAL, banda_pp: float = 1.0) -> dict:
    """Simulación sobre una matriz de precios (fechas × instrumentos, MXN). Determinista."""
    p = _parametros(estrategia, parametros)
    P = P.sort_index().ffill(limit=3)
    fechas = P.loc[desde:hasta].index
    if len(fechas) < 20:
        raise ValueError("menos de 20 sesiones en el periodo")
    costo_u = comision + deslizamiento_pb / 1e4
    titulos = pd.Series(0.0, index=P.columns)
    efectivo, pendiente = capital, None
    curva, ops, costo_total, girado = [], [], 0.0, 0.0
    for i, t in enumerate(fechas):
        precio = P.loc[t]
        valor = efectivo + float((titulos * precio.fillna(0)).sum())
        if pendiente is not None:                                   # ejecución al cierre de t de la señal de t−1
            objetivo = pendiente.reindex(P.columns).fillna(0.0)
            operables = precio.notna()
            deseado = (objetivo * valor / precio).where(operables, titulos)
            delta = (deseado - titulos).where(operables, 0.0)
            # banda de rebalanceo (como la terminal): no se operan ajustes menores a `banda_pp` puntos del valor,
            # salvo cerrar por completo una posición que sale del objetivo
            chico = (delta * precio).abs() < banda_pp / 100 * valor
            delta = delta.where(~chico | (objetivo == 0) & (titulos != 0), 0.0)
            for c in delta.index[delta.abs() > 1e-9]:
                importe = abs(float(delta[c] * precio[c]))
                costo = importe * costo_u
                efectivo -= float(delta[c] * precio[c]) + costo
                costo_total += costo
                girado += importe
                ops.append({"fecha": str(t.date()), "id": c, "titulos": float(delta[c]), "precio": float(precio[c]),
                            "importe": float(delta[c] * precio[c]), "costo": costo})
            titulos = titulos + delta
            pendiente = None
            valor = efectivo + float((titulos * precio.fillna(0)).sum())
        curva.append((t, valor))
        hist = P.loc[:t]
        disponibles = [c for c in P.columns if pd.notna(precio[c])]
        if disponibles and i < len(fechas) - 1:
            obj = _objetivo(estrategia, p, hist, disponibles, i)
            if obj is not None:
                pendiente = obj
    eq = pd.Series(dict(curva))
    r = eq.pct_change().dropna()
    anios = len(r) / 252
    acum = eq / eq.iloc[0]
    resumen = {"estrategia": estrategia, "version": ESTRATEGIAS[estrategia]["version"], "parametros": p,
               "desde": str(fechas[0].date()), "hasta": str(fechas[-1].date()), "sesiones": len(fechas),
               "capital_inicial": capital, "valor_final": float(eq.iloc[-1]), "rend_total": float(acum.iloc[-1] - 1),
               "rend_anual": float(acum.iloc[-1] ** (1 / anios) - 1) if anios > 0 else None,
               "vol_anual": float(r.std() * math.sqrt(252)) if len(r) > 1 else None,
               "sharpe_sin_tasa": float(r.mean() / r.std() * math.sqrt(252)) if len(r) > 1 and r.std() > 0 else None,
               "max_drawdown": float((acum / acum.cummax() - 1).min()), "operaciones": len(ops), "costo_total": costo_total,
               "giro_anual": girado / float(eq.mean()) / anios if anios > 0 else None,
               "comision": comision, "deslizamiento_pb": deslizamiento_pb, "banda_pp": banda_pp}
    return {"resumen": resumen, "curva": [{"fecha": str(d.date()), "valor": float(v)} for d, v in eq.items()], "operaciones": ops}


def ejecutar(con, ajustes, ids: list[str], estrategia: str, parametros: dict | None = None, desde: str | None = None,
             hasta: str | None = None, deslizamiento_pb: float = 5.0) -> dict:
    ids = [i for i in dict.fromkeys(ids) if i]
    if not 1 <= len(ids) <= 30:
        raise ValueError("elija de 1 a 30 instrumentos")
    if not 0 <= float(deslizamiento_pb) <= 200:
        raise ValueError("deslizamiento: de 0 a 200 puntos base")
    hasta = hasta or (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    desde = desde or (date.fromisoformat(hasta) - timedelta(days=730)).isoformat()
    if desde >= hasta:
        raise ValueError("la fecha inicial debe ser anterior a la final")
    P = mercado.precios_mxn(con, ajustes, ids, ajustados="splits")
    faltan = [i for i in ids if i not in P.columns]
    if faltan:
        raise ValueError("sin precios para: " + ", ".join(faltan))
    P = P.loc[:hasta]
    comision = reto.costo_operacion() or 0.0
    datos = P.round(6)
    huella_datos = _huella({"index": [str(x.date()) for x in datos.index], "cols": list(datos.columns),
                            "valores": np.nan_to_num(datos.values, nan=-1).tolist()})
    p = _parametros(estrategia, parametros or {})
    config = {"ids": ids, "estrategia": estrategia, "version": ESTRATEGIAS[estrategia]["version"], "parametros": p,
              "desde": desde, "hasta": hasta, "deslizamiento_pb": float(deslizamiento_pb), "comision": comision}
    huella_config = _huella(config)
    res = correr(P, estrategia, p, desde, hasta, comision, float(deslizamiento_pb))
    ref = correr(P, "comprar_y_mantener", {}, desde, hasta, comision, float(deslizamiento_pb))["resumen"]
    previo = con.execute("SELECT id, resumen FROM backtests WHERE huella_config=? AND huella_datos=? ORDER BY id DESC LIMIT 1",
                         (huella_config, huella_datos)).fetchone()
    res["resumen"]["referencia_comprar_y_mantener"] = {k: ref[k] for k in ("rend_total", "rend_anual", "vol_anual", "max_drawdown")}
    res["supuestos"] = [
        "Señal con cierres hasta el día t; ejecución al cierre de la sesión siguiente (sin fuga de información).",
        f"Costos: comisión del Reto {comision:.4%} por importe operado + deslizamiento {float(deslizamiento_pb):g} pb.",
        "Banda de rebalanceo de 1 punto: no se operan ajustes menores (salvo cerrar una posición que sale del objetivo).",
        "Precios de cierre en MXN ajustados solo por splits; el SIC = precio de origen × tipo de cambio del día.",
        "Sin dividendos (el Reto no los paga), sin impuestos, sin límites de liquidez ni restricciones del Reto (5 emisoras, 50 %).",
        "Universo elegido hoy: los instrumentos ya existen y sobrevivieron (sesgo de supervivencia).",
        "Los cierres guardados pueden incluir correcciones posteriores del proveedor (no se versiona cada precio)."]
    res["reproducibilidad"] = {"huella_config": huella_config, "huella_datos": huella_datos, "version_codigo": __version__,
                               "igual_a_corrida": previo["id"] if previo and json.loads(previo["resumen"]) == res["resumen"] else None}
    with db.transaccion(con):
        cur = con.execute("INSERT INTO backtests (ts, estrategia, version, parametros, huella_config, huella_datos, version_codigo, "
                          "resumen, resultado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (datetime.now(UTC).isoformat(), estrategia, config["version"], json.dumps(config), huella_config,
                           huella_datos, __version__, json.dumps(res["resumen"]), json.dumps(res)))
    res["id"] = cur.lastrowid
    return res


def historial(con, limite: int = 30) -> list[dict]:
    return [{"id": r["id"], "ts": r["ts"], "estrategia": r["estrategia"], "version": r["version"],
             "parametros": json.loads(r["parametros"]), "resumen": json.loads(r["resumen"]), "huella_datos": r["huella_datos"][:12]}
            for r in con.execute("SELECT * FROM backtests ORDER BY id DESC LIMIT ?", (limite,))]


def obtener(con, bid: int) -> dict:
    r = con.execute("SELECT * FROM backtests WHERE id=?", (bid,)).fetchone()
    if not r:
        raise ValueError("corrida no encontrada")
    return {"id": r["id"], "ts": r["ts"], "configuracion": json.loads(r["parametros"]), **json.loads(r["resultado"])}


def exportar_csv(con, bid: int) -> str:
    d = obtener(con, bid)
    s = io.StringIO()
    w = csv.writer(s, lineterminator="\n")
    w.writerow(["# backtest", bid, d["resumen"]["estrategia"], d["resumen"]["version"], json.dumps(d["configuracion"])])
    w.writerow(["# huella_datos", d["reproducibilidad"]["huella_datos"], "version_codigo", d["reproducibilidad"]["version_codigo"]])
    w.writerow(["fecha", "valor_cartera_mxn"])
    w.writerows([[c["fecha"], round(c["valor"], 2)] for c in d["curva"]])
    w.writerow([])
    w.writerow(["fecha", "instrumento", "titulos", "precio_mxn", "importe_mxn", "costo_mxn"])
    w.writerows([[o["fecha"], o["id"], round(o["titulos"], 6), round(o["precio"], 4), round(o["importe"], 2), round(o["costo"], 2)]
                 for o in d["operaciones"]])
    return s.getvalue()
