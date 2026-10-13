"""Lista de seguimiento, comparación de instrumentos, noticias por símbolo y estados financieros guardados.

La lista es la misma tabla `seguimiento` que usa «Movimientos públicos» (SEC EDGAR): un solo lugar para los
instrumentos que el usuario vigila. Solo guarda claves y notas (no órdenes). Las comparaciones usan cierres en MXN
ajustados por splits; son descriptivas.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from . import db, mercado
from .flujo import calculos

REFERENCIAS = ("BMV:NAFTRAC", "SIC:SPY")
MAX_LISTA = 60
MAX_COMPARAR = 8


def _existe(con, iid: str) -> bool:
    return con.execute("SELECT 1 FROM instrumentos WHERE id=?", (iid,)).fetchone() is not None


def agregar(con, iid: str, nota: str = "") -> None:
    if not _existe(con, iid):
        raise ValueError("instrumento desconocido")
    if len(nota) > 300:
        raise ValueError("nota: máximo 300 caracteres")
    n = con.execute("SELECT COUNT(*) FROM seguimiento").fetchone()[0]
    if n >= MAX_LISTA and not con.execute("SELECT 1 FROM seguimiento WHERE instrumento_id=?", (iid,)).fetchone():
        raise ValueError(f"la lista admite {MAX_LISTA} instrumentos")
    with db.transaccion(con):
        con.execute("INSERT INTO seguimiento (instrumento_id, agregado_en, nota) VALUES (?,?,?) "
                    "ON CONFLICT(instrumento_id) DO UPDATE SET nota=excluded.nota",
                    (iid, datetime.now(UTC).isoformat(), nota.strip()))


def quitar(con, iid: str) -> None:
    with db.transaccion(con):
        con.execute("DELETE FROM seguimiento WHERE instrumento_id=?", (iid,))


def lista(con, ajustes) -> dict:
    filas = [dict(r) for r in con.execute("SELECT * FROM seguimiento ORDER BY agregado_en")]
    ins = mercado.instrumentos(con)
    ids = [f["instrumento_id"] for f in filas]
    P = mercado.precios_mxn(con, ajustes, ids, ajustados="splits") if ids else pd.DataFrame()
    cot = mercado.cotizaciones(con, ajustes, ids) if ids else {}
    out = []
    for f in filas:
        iid = f["instrumento_id"]
        s = P[iid].dropna() if iid in P.columns else pd.Series(dtype=float)
        var = {n: (float(s.iloc[-1] / s.iloc[-1 - n] - 1) if len(s) > n else None) for n in (1, 5, 20)}
        rsi = calculos.rsi_wilder(list(s.tail(120)), 14)
        noticias = con.execute("SELECT COUNT(*) FROM noticias WHERE instrumento_id=? AND publicado >= date('now','-7 day')",
                               (iid,)).fetchone()[0]
        c = cot.get(iid) or {}
        out.append({**f, "nota": f.get("nota") or "", "clave": ins.get(iid, {}).get("clave_operable") or iid, "nombre": ins.get(iid, {}).get("nombre"),
                    "ultimo_mxn": float(s.iloc[-1]) if len(s) else None, "fecha": str(s.index[-1].date()) if len(s) else None,
                    "variacion": var, "rsi14": rsi[-1] if rsi else None, "noticias_7d": noticias,
                    "vigencia": c.get("vigencia") or c.get("estado"), "proveedor": c.get("proveedor")})
    return {"instrumentos": out, "nota": "Cierres en MXN ajustados por splits; el SIC = precio de origen × tipo de cambio. "
                                         "RSI de Wilder. Descriptivo: no son señales."}


def comparar(con, ajustes, ids: list[str], ventana: int = 252, referencia: str = "BMV:NAFTRAC") -> dict:
    ids = [i for i in dict.fromkeys(ids) if i][:MAX_COMPARAR]
    if len(ids) < 2:
        raise ValueError("elija al menos 2 instrumentos")
    desconocidos = [i for i in ids + [referencia] if not _existe(con, i)]
    if desconocidos:
        raise ValueError("instrumento desconocido: " + ", ".join(desconocidos))
    todos = list(dict.fromkeys(ids + [referencia]))
    P = mercado.precios_mxn(con, ajustes, todos, ajustados="splits").ffill(limit=3)
    P = P.dropna(subset=[i for i in todos if i in P.columns], how="any").tail(ventana + 1)
    sin = [i for i in todos if i not in P.columns]
    if len(P) < 30 or sin:
        raise ValueError("historia común insuficiente" + (f" (sin precios: {', '.join(sin)})" if sin else ""))
    R = P.pct_change().iloc[1:]
    base = (P / P.iloc[0] * 100)
    ins = mercado.instrumentos(con)
    filas = []
    for i in todos:
        r = R[i]
        acum = (1 + r).cumprod()
        cov = float(np.cov(r, R[referencia])[0, 1])
        beta = cov / float(R[referencia].var()) if i != referencia and R[referencia].var() > 0 else (1.0 if i == referencia else None)
        filas.append({"id": i, "clave": ins.get(i, {}).get("clave_operable") or i, "es_referencia": i == referencia,
                      "rend_total": float(acum.iloc[-1] - 1), "rend_anual": float(acum.iloc[-1] ** (252 / len(r)) - 1),
                      "vol_anual": float(r.std() * math.sqrt(252)), "max_drawdown": float((acum / acum.cummax() - 1).min()),
                      "beta": beta, "sharpe_sin_tasa": float(r.mean() / r.std() * math.sqrt(252)) if r.std() > 0 else None})
    corr = R[todos].corr().round(3)
    return {"desde": str(P.index[0].date()), "hasta": str(P.index[-1].date()), "sesiones": len(R), "referencia": referencia,
            "metricas": filas, "correlacion": {"ids": todos, "matriz": corr.values.tolist()},
            "serie": {"fechas": [str(d.date()) for d in base.index], **{i: base[i].round(3).tolist() for i in todos}},
            "nota": "Fechas comunes a todos (cierres en MXN ajustados por splits). Sharpe sin restar tasa libre de riesgo. "
                    "Beta frente a la referencia elegida. Rendimientos pasados no garantizan resultados futuros."}


def noticias(con, iid: str, limite: int = 50) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT titulo, enlace, publicado, fuente, impacto, sentimiento, motivo FROM noticias WHERE instrumento_id=? "
        "ORDER BY publicado DESC LIMIT ?", (iid, limite))]


def financieros(con, iid: str) -> list[dict]:
    """Observaciones de estados financieros del centro de investigación (Alpha Vantage o importadas) del símbolo de origen."""
    f = con.execute("SELECT listado_referencia FROM instrumentos WHERE id=?", (iid,)).fetchone()
    simbolo = (f[0] if f and f[0] else iid.split(":")[-1]).replace("BMV:", "").upper()
    return [dict(r) for r in con.execute(
        "SELECT fuente, serie, titulo, periodo, valor, unidad, texto, origen, disponible_desde FROM investigacion_observaciones "
        "WHERE simbolo=? ORDER BY periodo DESC, serie LIMIT 60", (simbolo,))]


def ficha(con, ajustes, iid: str) -> dict:
    if not _existe(con, iid):
        raise ValueError("instrumento desconocido")
    ins = mercado.instrumentos(con).get(iid, {})
    return {"id": iid, "clave": ins.get("clave_operable"), "nombre": ins.get("nombre"), "noticias": noticias(con, iid),
            "financieros": financieros(con, iid),
            "en_lista": con.execute("SELECT 1 FROM seguimiento WHERE instrumento_id=?", (iid,)).fetchone() is not None,
            "nota": "Noticias: titulares de las fuentes RSS configuradas (hecho reportado u opinión de un autor; no son "
                    "señales). Financieros: centro de investigación (Alpha Vantage o importación manual)."}
