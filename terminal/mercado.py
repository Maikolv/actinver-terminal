"""Acceso normalizado a precios: moneda base MXN, fuente y vigencia por dato."""
from __future__ import annotations

import sqlite3

import pandas as pd

from . import vigencia
from .config import Ajustes

DEMO = "demo_sintetico"


def _filtro_proveedor(ajustes: Ajustes) -> tuple[str, tuple]:
    return ("proveedor = ?", (DEMO,)) if ajustes.es_demo else ("proveedor <> ?", (DEMO,))


# Prioridad entre fuentes para UNA MISMA fecha (menor = preferida). Entre fechas distintas siempre gana la más reciente,
# así que un precio antiguo nunca sustituye a uno nuevo. Contratos BMV > cierres BMV > NAV oficial de fondos >
# referencias de la bolsa de origen > precio capturado a mano > cotización en vivo del día (la sustituye el cierre).
PRIORIDAD_FUENTE = {"bmv_licenciado": 0, "infosel": 1, "lseg": 2, "ice": 3, "edimex": 4, "eodhd": 10, "twelvedata": 11,
                    "actinver_pdf": 12, "tiingo": 20, "alpaca": 21, "barchart": 22, "archivo": 30, "alpaca_vivo": 40}


def prioridad_fuente(proveedor: str | None) -> int:
    return PRIORIDAD_FUENTE.get(proveedor or "", 35)


def instrumentos(con: sqlite3.Connection) -> dict[str, dict]:
    return {r["id"]: dict(r) for r in con.execute("SELECT * FROM instrumentos")}


def fx_serie(con: sqlite3.Connection, ajustes: Ajustes) -> pd.Series:
    cond, par = _filtro_proveedor(ajustes)
    filas = con.execute(f"SELECT fecha, valor, proveedor FROM fx WHERE par='USDMXN' AND {cond} ORDER BY fecha", par)
    df = pd.DataFrame(filas.fetchall(), columns=["fecha", "valor", "proveedor"])
    if df.empty:
        return pd.Series(dtype=float)
    # Banxico (FIX) tiene prioridad sobre FRED cuando ambos existen para la misma fecha.
    df["prio"] = df["proveedor"].map({"banxico": 0, "fred": 1}).fillna(2)
    df = df.sort_values(["fecha", "prio"]).drop_duplicates("fecha")
    return pd.Series(df["valor"].values, index=pd.to_datetime(df["fecha"]), name="USDMXN")


def ultimo_fx(con: sqlite3.Connection, ajustes: Ajustes) -> dict:
    cond, par = _filtro_proveedor(ajustes)
    f = con.execute(f"SELECT fecha, valor, proveedor, tipo_dato, obtenido_en FROM fx WHERE par='USDMXN' AND {cond} "
                    f"ORDER BY fecha DESC, CASE proveedor WHEN 'banxico' THEN 0 ELSE 1 END LIMIT 1", par).fetchone()
    if not f:
        v = vigencia.evaluar(None, None, "XMEX", ajustes["vigencia"])
        return {"par": "USD/MXN", "valor": None, **v}
    v = vigencia.evaluar(f["tipo_dato"], f["fecha"], "XMEX", ajustes["vigencia"])
    return {"par": "USD/MXN", "valor": f["valor"], "fecha": f["fecha"], "proveedor": f["proveedor"],
            "tipo_dato": f["tipo_dato"], "obtenido_en": f["obtenido_en"], **v}


def precios_mxn(con: sqlite3.Connection, ajustes: Ajustes, ids: list[str], ajustados: bool = True) -> pd.DataFrame:
    """Matriz fecha x instrumento en MXN. USD se convierte con el FX del mismo día (o el previo disponible).
    Si falta el tipo de cambio, las columnas en USD quedan vacías: nunca se inventa una conversión."""
    if not ids:
        return pd.DataFrame()
    cond, par = _filtro_proveedor(ajustes)
    marcas = ",".join("?" * len(ids))
    col = "COALESCE(cierre_ajustado, cierre)" if ajustados else "cierre"
    q = (f"SELECT instrumento_id, fecha, {col} AS p, moneda, proveedor FROM precios "
         f"WHERE instrumento_id IN ({marcas}) AND {cond}")
    df = pd.DataFrame(con.execute(q, (*ids, *par)).fetchall(), columns=["id", "fecha", "p", "moneda", "proveedor"])
    if df.empty:
        return pd.DataFrame()
    df["prio"] = df["proveedor"].map(prioridad_fuente)
    df = df.sort_values(["id", "fecha", "prio"]).drop_duplicates(["id", "fecha"], keep="first")
    ancho = df.pivot(index="fecha", columns="id", values="p")
    ancho.index = pd.to_datetime(ancho.index)
    monedas = df.drop_duplicates("id").set_index("id")["moneda"]
    usd = [c for c in ancho.columns if monedas.get(c) == "USD"]
    if usd:
        fx = fx_serie(con, ajustes)
        if fx.empty:
            ancho[usd] = float("nan")
        else:
            limite = ajustes["vigencia"]["fx_sesiones_retrasado"]
            fx_al = fx.reindex(ancho.index.union(fx.index)).ffill(limit=limite).reindex(ancho.index)
            ancho[usd] = ancho[usd].mul(fx_al, axis=0)
    return ancho.sort_index()


def cotizaciones(con: sqlite3.Connection, ajustes: Ajustes, ids: list[str] | None = None) -> dict[str, dict]:
    """Última cotización por instrumento con proveedor, bolsa, moneda, zona horaria, tipo de dato,
    hora de la cotización, retraso medido y estado de vigencia."""
    ins = instrumentos(con)
    ids = ids or list(ins)
    cond, par = _filtro_proveedor(ajustes)
    fx = ultimo_fx(con, ajustes)
    # Una sola consulta: último registro por instrumento (evita N consultas).
    ultimos = {}
    for r in con.execute(
            f"SELECT p.instrumento_id, p.fecha, p.cierre, p.moneda, p.proveedor, p.tipo_dato, p.hora_cotizacion, p.obtenido_en "
            f"FROM precios p JOIN (SELECT instrumento_id, MAX(fecha) AS f FROM precios WHERE {cond} GROUP BY instrumento_id) m "
            f"ON p.instrumento_id = m.instrumento_id AND p.fecha = m.f WHERE p.{cond}", (*par, *par)):
        previo = ultimos.get(r["instrumento_id"])  # misma fecha en varias fuentes: gana la de mayor prioridad
        if previo is None or prioridad_fuente(r["proveedor"]) < prioridad_fuente(previo["proveedor"]):
            ultimos[r["instrumento_id"]] = r
    out = {}
    for i in ids:
        meta = ins.get(i)
        if not meta:
            continue
        f = ultimos.get(i)
        cal = vigencia.codigo_calendario(meta)
        base = {"id": i, "clave_operable": meta["clave_operable"], "nombre": meta["nombre"], "clase": meta["clase"],
                "bolsa": meta["bolsa_referencia"], "mercado_operable": meta["mercado_operable"],
                "zona_horaria": meta["zona_horaria_referencia"], "estado_instrumento": meta["estado"]}
        if not f:
            out[i] = {**base, "precio": None, "precio_mxn": None, **vigencia.evaluar(None, None, cal, ajustes["vigencia"])}
            continue
        v = vigencia.evaluar(f["tipo_dato"], f["fecha"], cal, ajustes["vigencia"], f["hora_cotizacion"])
        pmxn = f["cierre"]
        if f["moneda"] == "USD":
            pmxn = f["cierre"] * fx["valor"] if fx.get("valor") else None
            if fx.get("estado") in ("vencido", "sin_datos"):
                v = {**v, "estado": vigencia.peor([v["estado"], fx["estado"]]),
                     "etiqueta": vigencia.ETIQUETAS[vigencia.peor([v["estado"], fx["estado"]])],
                     "nota": "Conversión a MXN afectada por tipo de cambio no vigente"}
        out[i] = {**base, "precio": f["cierre"], "moneda": f["moneda"], "precio_mxn": pmxn, "fecha": f["fecha"],
                  "proveedor": f["proveedor"], "tipo_dato": f["tipo_dato"], "obtenido_en": f["obtenido_en"], **v}
    return out
