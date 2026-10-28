"""Capitalización bursátil (market cap) y su clasificación: mega, large, mid, small y micro caps.

capitalización = acciones en circulación × precio. Se clasifica en dólares con los cortes más usados en EE. UU.
(no hay una norma oficial; cada índice usa los suyos):
  mega ≥ 200 000 M USD · large 10 000–200 000 M · mid 2 000–10 000 M · small 300–2 000 M · micro < 300 M

Fuentes (nunca se inventa el número de acciones):
* Emisoras de EE. UU. del SIC: SEC EDGAR, concepto `dei:EntityCommonStockSharesOutstanding` de su último 10-K/10-Q
  (API oficial gratuita; exige SEC_USER_AGENT en .env). Emisores extranjeros (20-F/40-F) reportan acciones
  ordinarias, no ADR: su capitalización no se clasifica porque la razón ADR/acción la distorsionaría.
* Emisoras de la BMV: no hay API gratuita con acciones en circulación. Se leen de `config/capitalizacion_bmv.csv`
  (clave, acciones en circulación, fecha y fuente que usted anote, p. ej. el reporte trimestral en bmv.com.mx).
"""
from __future__ import annotations

import csv
import os
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from . import db, mercado
from .config import Ajustes

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_BMV = RAIZ / "config" / "capitalizacion_bmv.csv"
TICKERS_SEC = "https://www.sec.gov/files/company_tickers.json"
CONCEPTO_SEC = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/{concepto}.json"
# Con varias series (p. ej. Berkshire A/B, Visa A/B/C) la SEC solo publica sin dimensión una serie: si acciones × precio
# queda muy por debajo del capital flotante del 10-K (valor de mercado en manos del público), se usa el flotante.
UMBRAL_FLOTANTE = 0.6
ANTIGUEDAD_MAX_DIAS = 548  # un dato sin series de hace más de 18 meses indica que la emisora ya reporta por series
FORMULARIOS_EEUU = ("10-K", "10-Q", "10-K/A", "10-Q/A", "10-KT")
VIGENCIA_DIAS = 30
CLASES_ACCION = ("accion", "reit", "fibra")

# (clave, nombre, mínimo USD, descripción) en orden descendente
CATEGORIAS = [
    ("mega", "Mega cap", 200e9, "Empresas gigantes (≥ 200 000 millones de dólares). Líderes globales, muy líquidas y "
     "seguidas por muchos analistas; suelen moverse menos que las pequeñas, pero su peso domina los índices."),
    ("large", "Large cap", 10e9, "Grandes empresas (10 000 a 200 000 millones). Negocios consolidados, con acceso a "
     "financiamiento y, muchas veces, dividendos. Riesgo y potencial de crecimiento moderados."),
    ("mid", "Mid cap", 2e9, "Empresas medianas (2 000 a 10 000 millones). En expansión: más crecimiento posible que "
     "las grandes y más volatilidad; menos cobertura de analistas."),
    ("small", "Small cap", 300e6, "Empresas pequeñas (300 a 2 000 millones). Mayor potencial y mayor riesgo: más "
     "sensibles a la economía local y a las tasas, y con menos liquidez."),
    ("micro", "Micro cap", 0.0, "Empresas muy pequeñas (menos de 300 millones). Muy volátiles, poco líquidas y con "
     "poca información pública; diferencias de compra-venta amplias y mayor riesgo de pérdida."),
]
EXPLICACION = ("La capitalización bursátil es el valor de mercado de todas las acciones de una empresa: acciones en "
               "circulación × precio. Clasifica el tamaño, no la calidad: una mega cap puede caer y una small cap "
               "puede ser sólida. Los cortes son convenciones de mercado en dólares y cambian con el precio diario.")


def categoria(cap_usd: float | None) -> str | None:
    if cap_usd is None or cap_usd <= 0:
        return None
    return next(c for c, _, minimo, _ in CATEGORIAS if cap_usd >= minimo)


def guia() -> dict:
    return {"explicacion": EXPLICACION, "categorias": [
        {"clave": c, "nombre": n, "minimo_usd": m, "descripcion": d} for c, n, m, d in CATEGORIAS]}


def flotante_sec(datos: dict) -> tuple[float | None, str | None]:
    """Último dei:EntityPublicFloat (USD) de un companyconcept de la SEC: (monto, fecha)."""
    filas = [f for f in datos.get("units", {}).get("USD", []) if f.get("val") and f.get("end")]
    if not filas:
        return None, None
    u = max(filas, key=lambda f: (f.get("filed", ""), f["end"]))
    return float(u["val"]), u["end"]


def acciones_sec(datos: dict) -> tuple[float | None, str | None, str | None]:
    """Último dato de acciones en circulación de un companyconcept de la SEC: (acciones, fecha, formulario).
    Si varias filas comparten la última fecha y el mismo reporte (varias series), se suman."""
    filas = [f for f in datos.get("units", {}).get("shares", []) if f.get("val") and f.get("end")]
    if not filas:
        return None, None, None
    ultimo = max(filas, key=lambda f: (f.get("filed", ""), f["end"]))
    mismas = [f for f in filas if f.get("accn") == ultimo.get("accn") and f["end"] == ultimo["end"]]
    total = sum({float(f["val"]) for f in mismas})  # la SEC repite la misma cifra con y sin «frame»
    return total, ultimo["end"], ultimo.get("form")


def leer_bmv(ruta: Path = ARCHIVO_BMV) -> dict[str, dict]:
    """Acciones en circulación de emisoras BMV anotadas por el usuario. Filas incompletas se ignoran."""
    if not ruta.exists():
        return {}
    out = {}
    with ruta.open(encoding="utf-8") as f:
        for r in csv.DictReader(l for l in f if not l.lstrip().startswith("#")):
            try:
                acciones = float(str(r.get("acciones_circulacion", "")).replace(",", ""))
            except ValueError:
                continue
            clave = (r.get("clave") or "").strip().upper()
            if clave and acciones > 0:
                out[clave] = {"acciones": acciones, "fecha": (r.get("fecha") or "").strip() or None,
                              "fuente": (r.get("fuente") or "").strip() or "archivo del usuario"}
    return out


def _guardar(con, iid: str, acciones, fecha, formulario, fuente: str, estado: str, detalle: str,
             flotante: float | None = None, fecha_flotante: str | None = None) -> None:
    con.execute("INSERT OR REPLACE INTO capitalizacion VALUES (?,?,?,?,?,?,?,?,?,?)",
                (iid, acciones, fecha, formulario, fuente, estado, detalle, db.ahora(), flotante, fecha_flotante))


def actualizar(con: sqlite3.Connection, ajustes: Ajustes, limite: int = 150, forzar: bool = False,
               cliente: httpx.Client | None = None, env: dict | None = None) -> dict:
    """Consulta la SEC para las acciones del SIC sin dato reciente y carga el archivo BMV. Respeta ≤ 10 peticiones/s."""
    env = os.environ if env is None else env
    ins = mercado.instrumentos(con)
    bmv = leer_bmv()
    with db.transaccion(con):
        for iid, v in ins.items():
            if v["mercado_operable"] == "BMV" and v["clase"] in CLASES_ACCION and v["clave"].upper() in bmv:
                b = bmv[v["clave"].upper()]
                _guardar(con, iid, b["acciones"], b["fecha"], None, b["fuente"], "verificado", "config/capitalizacion_bmv.csv")
    ua = env.get("SEC_USER_AGENT", "")
    if not ua:
        return {"estado": "sin_credencial", "bmv": len(bmv), "sec": 0,
                "mensaje": "Defina SEC_USER_AGENT (nombre y correo) en .env para consultar la SEC."}
    hace = (datetime.now(UTC) - timedelta(days=VIGENCIA_DIAS)).isoformat(timespec="seconds")
    recientes = set() if forzar else {r[0] for r in con.execute("SELECT instrumento_id FROM capitalizacion WHERE consultado_en > ?", (hace,))}
    pendientes = [(i, v) for i, v in ins.items() if v["mercado_operable"] == "BMV-SIC" and v["clase"] in CLASES_ACCION
                  and v["estado"] == "activo" and v.get("moneda_referencia") == "USD" and i not in recientes][:limite]
    if not pendientes:
        return {"estado": "ok", "bmv": len(bmv), "sec": 0, "mensaje": "Sin emisoras pendientes (datos de menos de 30 días)."}
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=20, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    hechos = 0
    try:
        mapa = {v["ticker"].upper(): int(v["cik_str"]) for v in cliente.get(TICKERS_SEC).raise_for_status().json().values()}
        for iid, v in pendientes:
            ticker = (v.get("listado_referencia") or v["clave"]).replace(".", "-").upper()
            cik = mapa.get(ticker)
            if cik is None:
                estado, acc, fecha, form, det = "sin_dato", None, None, None, f"{ticker} no aparece en el índice de la SEC"
                flot = fflot = None
            else:
                time.sleep(0.12)
                r = cliente.get(CONCEPTO_SEC.format(cik=cik, concepto="EntityCommonStockSharesOutstanding"))
                time.sleep(0.12)
                rf = cliente.get(CONCEPTO_SEC.format(cik=cik, concepto="EntityPublicFloat"))
                flot, fflot = flotante_sec(rf.json()) if rf.status_code == 200 else (None, None)
                if r.status_code == 404:
                    estado, acc, fecha, form, det = "sin_dato", None, None, None, "la SEC no publica acciones en circulación para esta emisora"
                else:
                    r.raise_for_status()
                    acc, fecha, form = acciones_sec(r.json())
                    if acc is None:
                        estado, det = "sin_dato", "sin filas de acciones en circulación"
                    elif fecha < (datetime.now(UTC) - timedelta(days=ANTIGUEDAD_MAX_DIAS)).date().isoformat():
                        estado, det = "sin_dato", f"último dato sin series de {fecha}: la emisora reporta por series"
                    elif form in FORMULARIOS_EEUU:
                        estado, det = "verificado", f"SEC {form} al {fecha}"
                    else:
                        estado, det = "extranjero", (f"Emisor extranjero ({form}): la SEC reporta acciones ordinarias, no ADR; "
                                                     "no se clasifica para no distorsionar la capitalización")
            with db.transaccion(con):
                _guardar(con, iid, acc, fecha, form, "sec_edgar", estado, det, flot, fflot)
            hechos += 1
    except httpx.HTTPError as e:
        return {"estado": "error", "bmv": len(bmv), "sec": hechos, "mensaje": f"SEC no respondió: {e}"}
    finally:
        if propio:
            cliente.close()
    return {"estado": "ok", "bmv": len(bmv), "sec": hechos,
            "mensaje": f"{hechos} emisoras consultadas en la SEC; quedan {max(0, len(pendientes) - hechos)} en esta tanda."}


def para_precios(con: sqlite3.Connection, ajustes: Ajustes, precios_mxn: dict[str, float]) -> dict[str, dict]:
    """Capitalización y categoría con el último precio (MXN) de cada instrumento."""
    fx = mercado.ultimo_fx(con, ajustes).get("valor")
    out = {}
    for r in con.execute("SELECT * FROM capitalizacion"):
        iid, p = r["instrumento_id"], precios_mxn.get(r["instrumento_id"])
        if p is None:
            continue
        cap_mxn = r["acciones"] * p if r["acciones"] and r["estado"] == "verificado" else None
        cap_usd = cap_mxn / fx if cap_mxn and fx else None
        estado, detalle = r["estado"], r["detalle"]
        flot = r["flotante_usd"]
        if flot and fx and estado != "extranjero" and (cap_usd is None or cap_usd < UMBRAL_FLOTANTE * flot):
            cap_usd, cap_mxn, estado = flot, flot * fx, "aproximado"
            detalle = (f"Aproximada con el capital flotante del 10-K al {r['fecha_flotante']} (cota inferior: excluye "
                       f"acciones de insiders y no incluye el cambio de precio posterior). Motivo: {r['detalle']}")
        out[iid] = {"cap_mxn": cap_mxn, "cap_usd": cap_usd, "cap_categoria": categoria(cap_usd),
                    "cap_estado": estado, "cap_detalle": detalle, "cap_fecha": r["fecha_dato"], "cap_fuente": r["fuente"]}
    return out
