"""Importadores de contexto y conciliación (CSV) con vista previa, validación y detección de duplicados.

- notas_sa: notas o tesis del participante sobre artículos de Seeking Alpha (titular, URL, fecha de publicación). Se
  guardan como noticias con fuente «seekingalpha_manual»; available_at = hora de importación (nunca antes).
- insiderfinance: exportación CSV del plan del usuario (si su plan la incluye). Fecha de operación y de divulgación
  separadas; cobertura «NO CUBRE BMV»; conviene confirmarlas con SEC EDGAR (Formulario 4).
- calificaciones_sa: calificaciones que el participante exporta de su cuenta de Seeking Alpha (Quant, autores, Wall
  Street de 1 a 5 y notas por factor A+…F). Se muestran en el Ranking como contexto fechado; no alimentan el optimizador.
- saldos: valor del portafolio y efectivo que muestra el portal, con su fecha y hora (conciliación).
- confirmaciones: ejecuciones CONFIRMADAS del simulador con su folio; registran operaciones y enlazan boletas.
Ninguna importación se etiqueta como cotización actual.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import UTC, datetime

import pandas as pd

from . import cartera, reto
from .db import ahora, auditar, transaccion

COLUMNAS = {
    "notas_sa": ["fecha_publicacion", "instrumento_id", "titulo", "url", "tipo_contenido", "autor", "tesis_usuario"],
    "insiderfinance": ["instrumento_id", "insider", "cargo", "codigo", "fecha_operacion", "fecha_divulgacion", "acciones",
                       "precio", "valor", "moneda", "url"],
    "calificaciones_sa": ["fecha", "instrumento_id", "quant", "autores", "wall_street", "valuacion", "crecimiento",
                          "rentabilidad", "momentum", "revisiones"],
    "saldos": ["fecha_hora_portal", "valor_portafolio", "efectivo", "nota"],
    "confirmaciones": ["folio", "fecha", "instrumento_id", "lado", "cantidad", "precio", "comision", "iva"],
}
OBLIGATORIAS = {"notas_sa": {"fecha_publicacion", "titulo", "url"},
                "insiderfinance": {"instrumento_id", "fecha_operacion", "fecha_divulgacion", "acciones", "precio"},
                "calificaciones_sa": {"fecha", "instrumento_id"},
                "saldos": {"fecha_hora_portal", "valor_portafolio"},
                "confirmaciones": {"folio", "fecha", "instrumento_id", "lado", "cantidad", "precio"}}
EJEMPLOS = {
    "notas_sa": ["2026-10-06T13:00:00-06:00,SIC:AAPL,Apple reporta ventas trimestrales,https://seekingalpha.com/news/000000,"
                 "hecho (noticia),Autor ejemplo,EJEMPLO: revisar margen bruto en el reporte oficial"],
    "insiderfinance": ["SIC:AAPL,Jane Doe,CFO,S,2026-10-01,2026-10-03,10000,230.5,2305000,USD,https://www.sec.gov/ejemplo"],
    "calificaciones_sa": ["2026-10-06,SIC:AAPL,3.45,3.20,4.10,D,C+,A+,B,C"],
    "saldos": ["2026-10-06T15:05:00-06:00,1003250.75,501200.10,EJEMPLO: copiado del portal"],
    "confirmaciones": ["F-EJEMPLO-001,2026-10-06,BMV:AMX,compra,5000,17.50,87.50,14.00"],
}


NOTAS_FACTOR = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"}


class ErrorImportacion(ValueError):
    pass


def plantilla(tipo: str) -> str:
    return ",".join(COLUMNAS[tipo]) + "\n" + "\n".join(EJEMPLOS[tipo]) + "\n"


def _fecha(v: str, campo: str, errores: list[str], con_hora: bool = False) -> str | None:
    try:
        t = pd.Timestamp(v)
    except (ValueError, TypeError):
        errores.append(f"{campo}: fecha inválida")
        return None
    if con_hora and t.tzinfo is None:
        t = t.tz_localize("America/Mexico_City")
    if t.tzinfo is not None and t.tz_convert("UTC") > pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=5):
        errores.append(f"{campo}: está en el futuro")
        return None
    return t.isoformat() if con_hora or t.tzinfo is not None else t.date().isoformat()


def _num(v, campo: str, errores: list[str], positivo: bool = True) -> float | None:
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        errores.append(f"{campo}: número inválido")
        return None
    if not math.isfinite(x) or (positivo and x <= 0):
        errores.append(f"{campo}: debe ser positivo")
        return None
    return x


def validar(tipo: str, f: dict, instrumentos: dict) -> dict:
    e: list[str] = []
    iid = (f.get("instrumento_id") or "").strip() or None
    if iid and iid not in instrumentos:
        e.append("instrumento_id: no está en el universo")
    if tipo == "notas_sa":
        url = (f.get("url") or "").strip()
        if not url.startswith("https://"):
            e.append("url: debe ser https")
        r = {"publicado": _fecha(f.get("fecha_publicacion"), "fecha_publicacion", e, con_hora=True), "instrumento_id": iid,
             "titulo": (f.get("titulo") or "").strip()[:300], "url": url[:500],
             "tipo_contenido": (f.get("tipo_contenido") or "sin clasificar")[:40], "autor": (f.get("autor") or "")[:120],
             "tesis": (f.get("tesis_usuario") or "")[:2000]}
        if not r["titulo"]:
            e.append("titulo: obligatorio")
    elif tipo == "insiderfinance":
        moneda = (f.get("moneda") or "USD").upper()
        if moneda != "USD":
            e.append("moneda: InsiderFinance cubre emisoras de EE. UU. (USD)")
        if iid and instrumentos[iid].get("moneda_referencia") != "USD":
            e.append("instrumento_id: una operación de insiders de EE. UU. no se asigna a una emisora mexicana (NO CUBRE BMV)")
        op = _fecha(f.get("fecha_operacion"), "fecha_operacion", e)
        di = _fecha(f.get("fecha_divulgacion"), "fecha_divulgacion", e)
        if op and di and di < op:
            e.append("fecha_divulgacion: no puede ser anterior a la operación")
        acc, px = _num(f.get("acciones"), "acciones", e), _num(f.get("precio"), "precio", e)
        r = {"instrumento_id": iid, "nombre": (f.get("insider") or "")[:120], "cargo": (f.get("cargo") or "")[:80],
             "codigo": (f.get("codigo") or "")[:4].upper(), "fecha": op, "fecha_presentacion": di, "acciones": acc,
             "precio": px, "valor": (acc or 0) * (px or 0), "enlace": (f.get("url") or "")[:500]}
    elif tipo == "calificaciones_sa":
        if not iid:
            e.append("instrumento_id: obligatorio")
        r = {"instrumento_id": iid, "fecha": _fecha(f.get("fecha"), "fecha", e)}
        for k in ("quant", "autores", "wall_street"):
            v = (f.get(k) or "").strip()
            x = None if not v else _num(v, k, e)
            if x is not None and not 1 <= x <= 5:
                e.append(f"{k}: escala de 1 a 5")
            r[k] = x
        for k in ("valuacion", "crecimiento", "rentabilidad", "momentum", "revisiones"):
            v = (f.get(k) or "").strip().upper()
            if v and v not in NOTAS_FACTOR:
                e.append(f"{k}: nota A+ … F")
            r[k] = v or None
        if all(r[k] is None for k in ("quant", "autores", "wall_street")):
            e.append("al menos una calificación (quant, autores o wall_street)")
    elif tipo == "saldos":
        r = {"hora_portal": _fecha(f.get("fecha_hora_portal"), "fecha_hora_portal", e, con_hora=True),
             "valor_portafolio": _num(f.get("valor_portafolio"), "valor_portafolio", e),
             "efectivo": None if not (f.get("efectivo") or "").strip() else _num(f.get("efectivo"), "efectivo", e, positivo=False),
             "nota": (f.get("nota") or "")[:200]}
    else:  # confirmaciones
        lado = (f.get("lado") or "").strip().lower()
        if lado not in ("compra", "venta"):
            e.append("lado: compra o venta")
        cant, px = _num(f.get("cantidad"), "cantidad", e), _num(f.get("precio"), "precio", e)
        if cant is not None and cant != int(cant):
            e.append("cantidad: debe ser entera (títulos)")
        importe = (cant or 0) * (px or 0)
        cd = reto.costo_detalle(importe)
        com = cd["comision"] if not (f.get("comision") or "").strip() else _num(f.get("comision"), "comision", e, positivo=False)
        iva = cd["iva"] if not (f.get("iva") or "").strip() else _num(f.get("iva"), "iva", e, positivo=False)
        r = {"folio": (f.get("folio") or "").strip()[:40], "fecha": _fecha(f.get("fecha"), "fecha", e), "instrumento_id": iid,
             "lado": lado, "cantidad": cant, "precio": px, "comision": com, "impuesto": iva}
        if not r["folio"]:
            e.append("folio: obligatorio")
    if e:
        raise ErrorImportacion("; ".join(e))
    return r


def importar(con: sqlite3.Connection, filas: list[dict], contenido: bytes, nombre: str, tipo: str, instrumentos: dict,
             confirmar: bool = False) -> dict:
    rep = {"archivo": nombre[:100], "tipo": tipo, "filas": len(filas), "aceptadas": 0, "duplicadas": 0, "rechazadas": 0,
           "detalle": [], "confirmado": False}
    validas = []
    vistos = set()
    for f in filas:
        try:
            r = validar(tipo, f, instrumentos)
        except ErrorImportacion as ex:
            rep["rechazadas"] += 1
            rep["detalle"].append({"linea": f["_linea"], "estado": "rechazada", "errores": str(ex).split("; ")})
            continue
        clave = hashlib.sha256(json.dumps(r, sort_keys=True, default=str).encode()).hexdigest()[:16]
        dup = clave in vistos or _existe(con, tipo, r, clave)
        vistos.add(clave)
        if dup:
            rep["duplicadas"] += 1
            rep["detalle"].append({"linea": f["_linea"], "estado": "duplicada", "errores": []})
            continue
        validas.append((f["_linea"], r, clave))
    rep["aceptables"] = len(validas)
    if not confirmar or rep["rechazadas"]:
        if confirmar and rep["rechazadas"]:
            rep["mensaje"] = "Corrija las filas rechazadas; no se importó nada."
        return rep
    ts = ahora()
    sha = hashlib.sha256(contenido).hexdigest()
    with transaccion(con):
        for _, r, clave in validas:
            if tipo == "notas_sa":
                con.execute("INSERT INTO noticias (id, instrumento_id, titulo, enlace, publicado, fuente, impacto, motivo, obtenido_en, "
                            "autor, tipo_contenido) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (f"sam-{clave}", r["instrumento_id"], r["titulo"], r["url"], r["publicado"], "seekingalpha_manual",
                             "normal", r["tesis"] or "nota del participante", ts, r["autor"], r["tipo_contenido"]))
            elif tipo == "insiderfinance":
                con.execute("INSERT INTO insiders (id, instrumento_id, fecha, nombre, cargo, codigo, acciones, precio, valor, enlace, "
                            "fuente, obtenido_en, fecha_presentacion, cobertura) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (f"if-{clave}", r["instrumento_id"], r["fecha"], r["nombre"], r["cargo"], r["codigo"], r["acciones"],
                             r["precio"], r["valor"], r["enlace"], "insiderfinance_csv", ts, r["fecha_presentacion"],
                             "EE. UU.; NO CUBRE BMV; confirmar con SEC Form 4"))
            elif tipo == "calificaciones_sa":
                con.execute("INSERT INTO calificaciones (id, instrumento_id, fecha, fuente, quant, autores, wall_street, valuacion, "
                            "crecimiento, rentabilidad, momentum, revisiones, importado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (f"sa-{clave}", r["instrumento_id"], r["fecha"], "seekingalpha_export", r["quant"], r["autores"],
                             r["wall_street"], r["valuacion"], r["crecimiento"], r["rentabilidad"], r["momentum"],
                             r["revisiones"], ts))
            elif tipo == "saldos":
                con.execute("INSERT INTO saldos_portal (capturado_en, hora_portal, etapa, valor_portafolio, efectivo, nota) "
                            "VALUES (?,?,?,?,?,?)", (ts, r["hora_portal"], reto.etapa_de_fecha(r["hora_portal"][:10]),
                                                     r["valor_portafolio"], r["efectivo"], r["nota"]))
            else:
                t = cartera.validar({"fecha": r["fecha"], "tipo": r["lado"], "instrumento_id": r["instrumento_id"],
                                     "cantidad": r["cantidad"], "precio": r["precio"], "comision": r["comision"],
                                     "impuesto": r["impuesto"], "moneda": "MXN", "tipo_cambio": 1, "nota": f"folio {r['folio']}"},
                                    instrumentos)
                tid = cartera.registrar(con, t, f"confirmacion:{r['folio']}")
                con.execute("UPDATE boletas SET estado='marcada_ejecutada', folio=?, marcada_en=?, transaccion_id=? "
                            "WHERE folio=? AND transaccion_id IS NULL", (r["folio"], ts, tid, r["folio"]))
                con.execute("UPDATE ordenes_pendientes SET estado='ejecutada', transaccion_id=? WHERE folio=?", (tid, r["folio"]))
            rep["aceptadas"] += 1
        cur = con.execute("INSERT INTO importaciones (ts, archivo, sha256, tipo, filas, aceptadas, duplicadas, rechazadas, "
                          "contenido_original) VALUES (?,?,?,?,?,?,?,?,?)",
                          (ts, nombre[:100], sha, tipo, rep["filas"], rep["aceptadas"], rep["duplicadas"], rep["rechazadas"], contenido))
        auditar(con, "importacion", cur.lastrowid, "alta", despues={k: v for k, v in rep.items() if k != "detalle"})
    rep["confirmado"] = True
    return rep


def _existe(con, tipo: str, r: dict, clave: str) -> bool:
    if tipo == "notas_sa":
        return bool(con.execute("SELECT 1 FROM noticias WHERE id=? OR enlace=?", (f"sam-{clave}", r["url"])).fetchone())
    if tipo == "insiderfinance":
        return bool(con.execute("SELECT 1 FROM insiders WHERE id=?", (f"if-{clave}",)).fetchone())
    if tipo == "calificaciones_sa":
        return bool(con.execute("SELECT 1 FROM calificaciones WHERE id=? OR (instrumento_id=? AND fecha=? AND fuente=?)",
                                (f"sa-{clave}", r["instrumento_id"], r["fecha"], "seekingalpha_export")).fetchone())
    if tipo == "saldos":
        return bool(con.execute("SELECT 1 FROM saldos_portal WHERE hora_portal=? AND valor_portafolio=?",
                                (r["hora_portal"], r["valor_portafolio"])).fetchone())
    return bool(con.execute("SELECT 1 FROM transacciones WHERE origen=?", (f"confirmacion:{r['folio']}",)).fetchone())


def ahora_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
