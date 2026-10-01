"""PASADO → conjunto de investigación sin fuga de información.

- Solo se usan filas con `available_at <= T` (hora de corte). Cada ejemplo (instrumento, fecha t) guarda cuándo se
  conocieron sus variables (`disponible_en` = available_at del cierre en t) y cuándo se conoció su etiqueta
  (`disponible_etiqueta` = available_at del cierre en t+H). Para entrenar a la hora T se exige `disponible_etiqueta <= T`.
- Precio: cierre SIN ajustar por dividendos (el Reto no los paga y el ajuste por dividendos se recalcula con
  información futura). Los splits se corrigen solo con eventos cuyo `available_at <= T`.
- Variables calculadas con ventanas hacia atrás (nunca centradas). La ventana máxima es L sesiones.
- No se alteran precios, no se añade ruido y no se fuerza independencia entre periodos.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

# Orden de PRIORIDAD declarado antes de evaluar: ante dos variables casi duplicadas se conserva la que aparece primero
# (las primeras son más simples y estables: retornos y volatilidad antes que osciladores derivados de ellos).
VARIABLES = ["r1", "r5", "r20", "r60", "vol20", "vol60", "rel_r20", "mercado_r5", "dist_ma20", "dist_ma50", "rsi14",
             "vol_rel20", "caida20", "noticias_5d"]
L_MAX = 60  # ventana retrospectiva máxima de las variables (sesiones)
TIPOS_DIARIOS = ("cierre", "nav", "sintetico")


def _utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, format="ISO8601")


FX_MAX_DIAS = 5  # tipo de cambio de la misma fecha o, si falta (festivo en México), de hasta 5 días antes


def fx_hasta(con: sqlite3.Connection, T: pd.Timestamp | None = None) -> pd.DataFrame:
    """USD/MXN conocido a la hora T (available_at <= T); por fecha, la primera publicación conocida."""
    q = "SELECT fecha, valor, available_at FROM fx WHERE par IN ('USDMXN','USD/MXN') AND available_at IS NOT NULL"
    par: list = []
    if T is not None:
        q += " AND available_at <= ?"
        par.append(pd.Timestamp(T).tz_convert("UTC").isoformat())
    df = pd.read_sql_query(q, con, params=par)
    if df.empty:
        return df
    df["available_at"] = _utc(df["available_at"])
    return df.sort_values(["fecha", "available_at"]).drop_duplicates("fecha").reset_index(drop=True)


def a_mxn(precios: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """Convierte a pesos las filas en USD con el tipo de cambio de su fecha (o el previo hasta FX_MAX_DIAS).
    La fila convertida se conoce cuando se conocen AMBOS datos: available_at = máx(precio, tipo de cambio).
    Sin tipo de cambio válido la fila se descarta (nunca se inventa una conversión)."""
    if precios.empty or "moneda" not in precios.columns:
        return precios
    usd = precios["moneda"] == "USD"
    if not usd.any():
        return precios
    if fx.empty:
        return precios[~usd].reset_index(drop=True)
    f = fx.assign(_f=pd.to_datetime(fx["fecha"])).sort_values("_f")
    u = precios[usd].assign(_f=pd.to_datetime(precios.loc[usd, "fecha"])).sort_values("_f")
    m = pd.merge_asof(u, f[["_f", "valor", "available_at"]].rename(columns={"available_at": "fx_disponible"}), on="_f",
                      direction="backward", tolerance=pd.Timedelta(days=FX_MAX_DIAS))
    m = m.dropna(subset=["valor"])
    m["cierre"] = m["cierre"] * m["valor"]
    m["available_at"] = m[["available_at", "fx_disponible"]].max(axis=1)
    m["moneda"] = "MXN"
    out = pd.concat([precios[~usd], m[precios.columns]], ignore_index=True)
    return out.sort_values(["instrumento_id", "fecha"]).reset_index(drop=True)


def precios_hasta(con: sqlite3.Connection, demo: bool, T: pd.Timestamp | None = None,
                  ids: list[str] | None = None, mxn: bool = False) -> pd.DataFrame:
    """Cierres diarios conocidos a la hora T (available_at <= T). Demo y real nunca se mezclan.
    mxn=True: en pesos (el Reto se mide en MXN); el riesgo cambiario queda dentro del rendimiento."""
    cond = "proveedor = 'demo_sintetico'" if demo else "proveedor <> 'demo_sintetico'"
    q = (f"SELECT instrumento_id, fecha, cierre, volumen, moneda, proveedor, available_at FROM precios WHERE {cond} "
         f"AND tipo_dato IN ({','.join('?' * len(TIPOS_DIARIOS))}) AND available_at IS NOT NULL")
    par: list = list(TIPOS_DIARIOS)
    if T is not None:
        q += " AND available_at <= ?"
        par.append(pd.Timestamp(T).tz_convert("UTC").isoformat())
    if ids:
        q += f" AND instrumento_id IN ({','.join('?' * len(ids))})"
        par += ids
    df = pd.read_sql_query(q, con, params=par)
    if df.empty:
        return df
    df["available_at"] = _utc(df["available_at"])
    # Si dos proveedores dan la misma fecha se conserva el que se conoció primero (no se «mejora» con uno posterior).
    df = df.sort_values(["instrumento_id", "fecha", "available_at"]).drop_duplicates(["instrumento_id", "fecha"])
    splits = pd.read_sql_query("SELECT instrumento_id, fecha, valor, available_at FROM eventos_corporativos WHERE tipo='split' "
                               "AND available_at IS NOT NULL", con)
    if not splits.empty:
        splits["available_at"] = _utc(splits["available_at"])
        if T is not None:
            splits = splits[splits["available_at"] <= pd.Timestamp(T).tz_convert("UTC")]
        for r in splits.itertuples():
            m = (df["instrumento_id"] == r.instrumento_id) & (df["fecha"] < r.fecha)
            df.loc[m, "cierre"] = df.loc[m, "cierre"] / float(r.valor)  # precios previos en unidades posteriores al split
    if mxn:
        df = a_mxn(df, fx_hasta(con, T))
        if T is not None:  # la fila convertida puede conocerse después (cuando se publica el tipo de cambio)
            df = df[df["available_at"] <= pd.Timestamp(T).tz_convert("UTC")]
    return df.reset_index(drop=True)


def historia_insuficiente(precios: pd.DataFrame, H: int) -> list[dict]:
    """Instrumentos que quedan fuera del panel por historia corta (se informan, no se ocultan)."""
    if precios.empty:
        return []
    n = precios.groupby("instrumento_id")["fecha"].count()
    minimo = L_MAX + H + 5
    return [{"instrumento_id": i, "sesiones": int(k), "minimo": minimo} for i, k in n.items() if k < minimo]


def noticias_hasta(con: sqlite3.Connection, T: pd.Timestamp | None = None) -> pd.DataFrame:
    """Noticias de alto impacto con su available_at (cuándo las conoció la terminal). Solo las conocidas en T."""
    q = "SELECT instrumento_id, available_at FROM noticias WHERE impacto='alto' AND available_at IS NOT NULL"
    par: list = []
    if T is not None:
        q += " AND available_at <= ?"
        par.append(pd.Timestamp(T).tz_convert("UTC").isoformat())
    df = pd.read_sql_query(q, con, params=par)
    if not df.empty:
        df["available_at"] = _utc(df["available_at"])
    return df


def _conteo_noticias(d: pd.DataFrame, noticias: pd.DataFrame, dias: int = 5) -> pd.Series:
    """Noticias de alto impacto conocidas en (disponible_en − dias, disponible_en]: nunca cuenta una noticia futura."""
    if noticias is None or noticias.empty:
        return pd.Series(0.0, index=d.index)
    tiempos = np.sort(noticias.loc[noticias["instrumento_id"] == d["instrumento_id"].iloc[0], "available_at"].to_numpy())
    if not len(tiempos):
        return pd.Series(0.0, index=d.index)
    fin = d["disponible_en"].to_numpy()
    ini = (d["disponible_en"] - pd.Timedelta(days=dias)).to_numpy()
    return pd.Series(np.searchsorted(tiempos, fin, side="right") - np.searchsorted(tiempos, ini, side="right"),
                     index=d.index, dtype=float)


def _rsi(r: pd.Series, n: int = 14) -> pd.Series:
    sube = r.clip(lower=0).rolling(n).mean()
    baja = (-r.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + sube / baja.replace(0, np.nan))


def construir_panel(precios: pd.DataFrame, H: int, noticias: pd.DataFrame | None = None) -> pd.DataFrame:
    """Un renglón por (instrumento, fecha) con variables, etiqueta a H sesiones y sus horas de disponibilidad."""
    if precios.empty:
        return pd.DataFrame()
    partes = []
    for iid, g in precios.groupby("instrumento_id", sort=True):
        g = g.sort_values("fecha").reset_index(drop=True)
        if len(g) < L_MAX + H + 5:
            continue
        lp = np.log(g["cierre"].astype(float))
        r1 = lp.diff()
        d = pd.DataFrame({"instrumento_id": iid, "fecha": g["fecha"], "disponible_en": g["available_at"]})
        d["r1"], d["r5"], d["r20"], d["r60"] = r1, lp.diff(5), lp.diff(20), lp.diff(60)
        d["vol20"], d["vol60"] = r1.rolling(20).std(), r1.rolling(60).std()
        p = g["cierre"].astype(float)
        d["dist_ma20"] = p / p.rolling(20).mean() - 1
        d["dist_ma50"] = p / p.rolling(50).mean() - 1
        d["rsi14"] = _rsi(r1) / 100
        v = g["volumen"].astype(float).where(g["volumen"] > 0)
        d["vol_rel20"] = np.log(v / v.rolling(20).mean())
        d["caida20"] = p / p.rolling(20).max() - 1                      # drawdown de 20 sesiones
        d["noticias_5d"] = _conteo_noticias(d, noticias)
        d["y"] = lp.shift(-H) - lp
        d["fecha_fin_etiqueta"] = g["fecha"].shift(-H)
        d["disponible_etiqueta"] = g["available_at"].shift(-H)
        partes.append(d.iloc[L_MAX:])  # calentamiento de L sesiones: variables completas
    if not partes:
        return pd.DataFrame()
    panel = pd.concat(partes, ignore_index=True)
    # Variables transversales con información de la MISMA fecha (conocida a la vez que el cierre propio).
    panel["mercado_r5"] = panel.groupby("fecha")["r5"].transform("mean")
    panel["rel_r20"] = panel["r20"] - panel.groupby("fecha")["r20"].transform("mean")
    # La hora de disponibilidad de la fila es la más tardía de los cierres usados en esa fecha (transversales).
    panel["disponible_en"] = panel.groupby("fecha")["disponible_en"].transform("max")
    return panel.sort_values(["fecha", "instrumento_id"]).reset_index(drop=True)


def etiquetados_hasta(panel: pd.DataFrame, T: pd.Timestamp | None) -> pd.DataFrame:
    """Ejemplos cuya etiqueta ya se conocía en T (para entrenar o evaluar sin mirar el futuro)."""
    p = panel.dropna(subset=["y", "disponible_etiqueta"])
    if T is not None:
        p = p[p["disponible_etiqueta"] <= pd.Timestamp(T).tz_convert("UTC")]
    return p


def correlacion_activos(precios: pd.DataFrame, fechas: list[str] | None = None, top: int = 10) -> dict:
    """Correlación de rendimientos diarios entre ACTIVOS (riesgo real: se informa, no se reduce)."""
    if precios.empty:
        return {"media": None, "pares": []}
    ancho = precios.pivot(index="fecha", columns="instrumento_id", values="cierre").sort_index()
    if fechas is not None:
        ancho = ancho.loc[ancho.index.isin(fechas)]
    r = np.log(ancho).diff().dropna(how="all")
    r = r.loc[:, r.notna().sum() > 60]
    if r.shape[1] < 2:
        return {"media": None, "pares": []}
    c = r.corr(min_periods=60)
    tri = c.where(np.triu(np.ones(c.shape, dtype=bool), k=1)).stack()
    pares = tri.abs().sort_values(ascending=False).head(top)
    return {"media": round(float(tri.mean()), 4), "n_activos": int(r.shape[1]),
            "pares": [{"a": a, "b": b, "r": round(float(tri[(a, b)]), 4)} for a, b in pares.index],
            "nota": "Correlación real entre activos: indica riesgo concentrado. No se modifica."}
