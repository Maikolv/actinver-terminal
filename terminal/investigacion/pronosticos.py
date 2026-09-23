"""FUTURO: pronósticos emitidos a la hora T con información disponible en T, guardados aparte de las cotizaciones.

- Se entrena con ejemplos cuya etiqueta ya se conocía en T (`disponible_etiqueta <= T`) y se pronostica desde la
  última fecha de cada instrumento con `disponible_en <= T`.
- El registro es inmutable: el resultado observado se añade después, cuando el precio objetivo está disponible.
- Si el último experimento no superó a las referencias, se guarda `recomendacion_permitida = 0`.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from . import datos, evaluacion


def emitir(con: sqlite3.Connection, demo: bool, H: int, T: pd.Timestamp | None = None, max_instrumentos: int = 300) -> dict:
    T = pd.Timestamp(T).tz_convert("UTC") if T is not None else pd.Timestamp(datetime.now(UTC))
    exp = evaluacion.investigar(con, demo, H, T, guardar=True)
    if exp.get("estado") != "ok":
        return {"emitidos": 0, **{k: v for k, v in exp.items() if not k.startswith("_")}}
    precios = datos.precios_hasta(con, demo, T)
    panel = datos.construir_panel(precios, H)
    panel = panel[panel["disponible_en"] <= T]
    entren = datos.etiquetados_hasta(panel, T)
    mdl = evaluacion.modelo(exp["variante_elegida"], exp["alfa_por_variante"][exp["variante_elegida"]],
                            evaluacion.CONFIG_BASE["umbral_correlacion"], exp["semilla"]).fit(entren[datos.VARIABLES], entren["y"])
    base = panel.sort_values("fecha").groupby("instrumento_id").tail(1).head(max_instrumentos)
    pred = mdl.predict(base[datos.VARIABLES])
    res = np.sort(exp["_residuos"])
    q10, q90 = np.quantile(res, [0.10, 0.90])
    prob = 1 - np.searchsorted(res, -pred, side="right") / len(res)
    emitido, datos_hasta = T.isoformat(), base["disponible_en"].max().isoformat()
    version = f"{exp['version_codigo']}+{exp['huella_config']}"
    filas = [(emitido, datos_hasta, r.instrumento_id, H, r.fecha, None, f"{exp['variante_elegida']}", version, exp["semilla"],
              float(p), float(p + q10), float(p + q90), float(pr), int(exp["recomendacion_permitida"]))
             for r, p, pr in zip(base.itertuples(), pred, prob, strict=True)]
    con.executemany("INSERT OR IGNORE INTO pronosticos (emitido_en, datos_hasta, instrumento_id, horizonte, fecha_base, "
                    "fecha_objetivo, modelo, version, semilla, prediccion, p10, p90, prob_subida, recomendacion_permitida) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", filas)
    con.commit()
    return {"emitidos": len(filas), "emitido_en": emitido, "datos_hasta": datos_hasta, "H": H,
            "recomendacion_permitida": exp["recomendacion_permitida"], "conclusion": exp["conclusion"]}


def resolver(con: sqlite3.Connection, demo: bool, ahora: pd.Timestamp | None = None) -> int:
    """Añade el resultado observado a pronósticos cuyo precio objetivo (H sesiones después) ya está disponible."""
    ahora = pd.Timestamp(ahora).tz_convert("UTC") if ahora is not None else pd.Timestamp(datetime.now(UTC))
    pend = con.execute("SELECT id, instrumento_id, horizonte, fecha_base FROM pronosticos WHERE resuelto_en IS NULL").fetchall()
    if not pend:
        return 0
    precios = datos.precios_hasta(con, demo, ahora, sorted({p["instrumento_id"] for p in pend}))
    n = 0
    for p in pend:
        g = precios[precios["instrumento_id"] == p["instrumento_id"]].sort_values("fecha").reset_index(drop=True)
        idx = g.index[g["fecha"] == p["fecha_base"]]
        if not len(idx) or idx[0] + p["horizonte"] >= len(g):
            continue
        j = idx[0] + p["horizonte"]
        y = float(np.log(g.loc[j, "cierre"] / g.loc[idx[0], "cierre"]))
        con.execute("UPDATE pronosticos SET resultado=?, fecha_objetivo=?, resuelto_en=? WHERE id=? AND resuelto_en IS NULL",
                    (y, g.loc[j, "fecha"], ahora.isoformat(), p["id"]))
        n += 1
    con.commit()
    return n


def deterioro(con: sqlite3.Connection, ventana: int = 200) -> dict | None:
    """Error de los pronósticos ya resueltos frente a «sin cambio» y cobertura del intervalo (señal de deterioro)."""
    df = pd.read_sql_query("SELECT prediccion, p10, p90, resultado FROM pronosticos WHERE resultado IS NOT NULL "
                           "ORDER BY resuelto_en DESC LIMIT ?", con, params=(ventana,))
    if len(df) < 30:
        return None
    mse, mse0 = float(((df.resultado - df.prediccion) ** 2).mean()), float((df.resultado ** 2).mean())
    cob = float(((df.resultado >= df.p10) & (df.resultado <= df.p90)).mean())
    return {"n": len(df), "mse": mse, "mse_sin_cambio": mse0, "razon": mse / mse0 if mse0 else None, "cobertura_80": cob}


def listar(con: sqlite3.Connection, limite: int = 300) -> list[dict]:
    """Última emisión de cada horizonte."""
    return [dict(r) for r in con.execute(
        "SELECT p.* FROM pronosticos p JOIN (SELECT horizonte, MAX(emitido_en) AS e FROM pronosticos GROUP BY horizonte) u "
        "ON p.horizonte=u.horizonte AND p.emitido_en=u.e ORDER BY p.horizonte, p.prediccion DESC LIMIT ?", (limite,))]
