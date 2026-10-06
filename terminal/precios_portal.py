"""Precios de la pestaña «Acciones» del simulador del Reto, a partir del PDF que arma el participante con sus capturas.

Vía legal: la terminal nunca entra al portal; solo lee el documento que el participante entrega (como la cartera).
- BMV (moneda MXN): el precio del portal se guarda como cierre del día del documento con proveedor «archivo» (precio
  capturado por el participante). Un documento armado tras el cierre muestra el último precio de la sesión; el del
  5-oct-2026 coincide con la captura de la cartera de las 15:08 (ALPEK 14.56, AMAT 9,800, AMD 11,392.74).
- SIC: la serie de la terminal está en USD (bolsa de origen) y no se mezcla con un precio en MXN; se informa la
  diferencia entre el precio del portal y la referencia origen × tipo de cambio.
"""
from __future__ import annotations

import hashlib
import io
import re
import sqlite3
from datetime import date

from .db import ahora, auditar, transaccion

MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                     "septiembre", "octubre", "noviembre", "diciembre"], 1)}
RE_FECHA = re.compile(r"(\d{1,2}) de ([a-záéíóú]+) de (\d{4})", re.I)


class ErrorDocumento(ValueError):
    pass


def _num(s: str) -> float:
    return float(s.replace("$", "").replace(",", "").strip())


def interpretar(texto: str) -> dict:
    """Filas {n, emisora, precio, variacion, precio_compra, precio_venta} y la fecha declarada en el encabezado."""
    fechas = {date(int(a), MESES[m.lower()], int(d)).isoformat() for d, m, a in RE_FECHA.findall(texto) if m.lower() in MESES}
    if len(fechas) != 1:
        raise ErrorDocumento("El documento no declara una única fecha («Portal del simulador · D de mes de AAAA»).")
    L = [x.strip() for x in texto.splitlines() if x.strip()]
    filas, i = [], 0
    while i + 7 < len(L):
        if (re.fullmatch(r"\d{1,3}", L[i]) and L[i + 2].startswith("$") and L[i + 3].endswith("%")
                and L[i + 5].startswith("$") and L[i + 7].startswith("$")):
            filas.append({"n": int(L[i]), "emisora": " ".join(L[i + 1].upper().split()), "precio": _num(L[i + 2]),
                          "variacion": L[i + 3], "precio_compra": _num(L[i + 5]), "precio_venta": _num(L[i + 7])})
            i += 8
        else:
            i += 1
    if not filas:
        raise ErrorDocumento("No se encontraron filas de emisoras con precio.")
    return {"fecha": fechas.pop(), "filas": filas}


def texto_pdf(contenido: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages)


def importar(con: sqlite3.Connection, ajustes, contenido: bytes, nombre: str, confirmar: bool = False) -> dict:
    """Vista previa (confirmar=False) o importación de los precios BMV; compara los del SIC con la referencia."""
    from . import mercado
    if not contenido.startswith(b"%PDF"):
        raise ErrorDocumento("El archivo no es un PDF.")
    doc = interpretar(texto_pdf(contenido))
    if date.fromisoformat(doc["fecha"]) > date.today():
        raise ErrorDocumento("La fecha del documento está en el futuro.")
    ins = mercado.instrumentos(con)
    por_clave: dict[str, str] = {}
    for iid, x in sorted(ins.items()):
        por_clave.setdefault(" ".join((x.get("clave_operable") or "").upper().split()), iid)
    bmv, sic, fuera = [], [], []
    for f in doc["filas"]:
        iid = por_clave.get(f["emisora"])
        if not iid:
            fuera.append(f["emisora"])
        elif (ins[iid].get("moneda_referencia") or "MXN") == "MXN" and f["precio"] > 0:
            bmv.append({**f, "id": iid})
        elif f["precio"] > 0:
            sic.append({**f, "id": iid})
    cot = mercado.cotizaciones(con, ajustes, [f["id"] for f in sic]) if sic else {}
    comparacion = []
    for f in sic:
        ref = (cot.get(f["id"]) or {}).get("precio_mxn")
        if ref:
            comparacion.append({"emisora": f["emisora"], "portal": f["precio"], "referencia": round(ref, 2),
                                "fecha_referencia": cot[f["id"]].get("fecha"), "dif": f["precio"] / ref - 1})
    comparacion.sort(key=lambda c: -abs(c["dif"]))
    rep = {"archivo": nombre[:100], "fecha": doc["fecha"], "filas": len(doc["filas"]), "bmv": len(bmv), "sic": len(sic),
           "fuera_del_universo": fuera, "sic_comparacion": comparacion,
           "sic_dif_mediana": (sorted(abs(c["dif"]) for c in comparacion)[len(comparacion) // 2] if comparacion else None),
           "precios_bmv": [{"id": f["id"], "precio": f["precio"]} for f in bmv], "confirmado": False}
    if not confirmar or not bmv:
        return rep
    sha = hashlib.sha256(contenido).hexdigest()
    ts = ahora()
    with transaccion(con):
        for f in bmv:
            con.execute("INSERT OR REPLACE INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, "
                        "proveedor, tipo_dato, hora_cotizacion, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (f["id"], doc["fecha"], f["precio"], None, None, "MXN", "archivo", "cierre", None, ts))
        cur = con.execute("INSERT INTO importaciones (ts, archivo, sha256, tipo, filas, aceptadas, duplicadas, rechazadas, "
                          "contenido_original) VALUES (?,?,?,?,?,?,?,?,?)",
                          (ts, nombre[:100], sha, "precios_portal_pdf", len(doc["filas"]), len(bmv), 0, len(fuera), contenido))
        auditar(con, "importacion", cur.lastrowid, "alta",
                despues={"tipo": "precios_portal_pdf", "fecha": doc["fecha"], "bmv": len(bmv), "sha256": sha[:12]})
    rep["confirmado"] = True
    return rep
