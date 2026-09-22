"""Importación de archivos locales validados.

Tipos:
  transacciones -> libro de operaciones (con detección de duplicados por huella)
  posiciones    -> saldo inicial: cada fila se registra como aportación en especie + compra al costo promedio
  precios       -> cierres o valor liquidativo (NAV) aportados por el usuario

Límites: solo .csv (texto UTF-8), máximo 1 MB y 5 000 filas. El archivo original se conserva
íntegro en la tabla «importaciones» para trazabilidad.
"""
from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from collections import Counter
from datetime import date

from . import cartera
from .db import ahora, auditar, transaccion

MAX_BYTES = 1_000_000
MAX_FILAS = 5000
COLUMNAS = {
    "transacciones": ["fecha", "tipo", "instrumento_id", "cantidad", "precio", "monto", "comision", "impuesto",
                      "moneda", "tipo_cambio", "nota"],
    "posiciones": ["fecha", "instrumento_id", "cantidad", "costo_promedio", "moneda", "tipo_cambio"],
    "precios": ["fecha", "instrumento_id", "precio", "moneda", "tipo_dato", "fuente"],
}
OBLIGATORIAS = {"transacciones": {"fecha", "tipo"}, "posiciones": {"fecha", "instrumento_id", "cantidad", "costo_promedio"},
                "precios": {"fecha", "instrumento_id", "precio"}}


class ErrorArchivo(ValueError):
    pass


def plantilla(tipo: str) -> str:
    ejemplos = {
        "transacciones": ["2025-01-10,aportacion,,,,50000,,,MXN,1,Depósito inicial",
                          "2025-01-13,compra,SIC:IVV,5,10250.50,,31.25,5.00,MXN,1,",
                          "2025-03-20,dividendo,SIC:IVV,,,85.40,,8.54,MXN,1,Dividendo trimestral"],
        "posiciones": ["2025-01-01,FONDO:ACTIGOB,1000,5.123456,MXN,1"],
        "precios": ["2026-09-18,FONDO:ACTIGOB,5.234567,MXN,nav,Estado de cuenta"],
    }
    return ",".join(COLUMNAS[tipo]) + "\n" + "\n".join(ejemplos[tipo]) + "\n"


def leer(contenido: bytes, nombre: str, tipo: str) -> list[dict]:
    if tipo not in COLUMNAS:
        raise ErrorArchivo("Tipo de importación no reconocido")
    if not nombre.lower().endswith(".csv"):
        raise ErrorArchivo("Solo se aceptan archivos .csv")
    if len(contenido) > MAX_BYTES:
        raise ErrorArchivo("El archivo supera 1 MB")
    if b"\x00" in contenido:
        raise ErrorArchivo("El archivo no parece ser texto CSV")
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            texto = contenido.decode("latin-1")
        except UnicodeDecodeError:
            raise ErrorArchivo("Codificación no reconocida; guarde el archivo como CSV UTF-8") from None
    muestra = texto[:2048]
    delim = ";" if muestra.count(";") > muestra.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=delim)
    if not lector.fieldnames:
        raise ErrorArchivo("El archivo está vacío")
    encabezados = {h.strip().lower(): h for h in lector.fieldnames if h}
    faltan = OBLIGATORIAS[tipo] - set(encabezados)
    if faltan:
        raise ErrorArchivo(f"Faltan columnas obligatorias: {', '.join(sorted(faltan))}. Descargue la plantilla.")
    filas = []
    for i, fila in enumerate(lector, start=2):
        if i - 1 > MAX_FILAS:
            raise ErrorArchivo(f"Máximo {MAX_FILAS} filas por archivo")
        norm = {k: (fila.get(v) or "").strip() for k, v in encabezados.items() if k in COLUMNAS[tipo]}
        if any(norm.values()):
            filas.append({"_linea": i, **norm})
    return filas


def importar(con: sqlite3.Connection, contenido: bytes, nombre: str, tipo: str, instrumentos: dict,
             confirmar: bool = False) -> dict:
    """Valida todo el archivo. Con confirmar=False solo devuelve la vista previa (no escribe nada)."""
    filas = leer(contenido, nombre, tipo)
    reporte = {"archivo": nombre[:100], "tipo": tipo, "filas": len(filas), "aceptadas": 0, "duplicadas": 0,
               "rechazadas": 0, "detalle": [], "confirmado": False}
    validas: list[tuple[int, dict, int]] = []
    vistos: Counter = Counter()
    for f in filas:
        try:
            if tipo == "transacciones":
                t = cartera.validar(f, instrumentos)
                clave = cartera.huella(t)
                vistos[clave] += 1
                validas.append((f["_linea"], t, vistos[clave]))
            elif tipo == "posiciones":
                validas.append((f["_linea"], _posicion(f, instrumentos), 1))
            else:
                validas.append((f["_linea"], _precio(f, instrumentos), 1))
        except cartera.ErrorValidacion as e:
            reporte["rechazadas"] += 1
            reporte["detalle"].append({"linea": f["_linea"], "estado": "rechazada", "errores": e.errores})
    if tipo != "precios":
        for linea, t, oc in validas:
            ts = t if tipo == "transacciones" else t["compra"]
            if con.execute("SELECT 1 FROM transacciones WHERE huella=?", (cartera.huella(ts, oc),)).fetchone():
                reporte["duplicadas"] += 1
                reporte["detalle"].append({"linea": linea, "estado": "duplicada", "errores": []})
    if not confirmar or reporte["rechazadas"]:
        reporte["aceptables"] = len(validas) - reporte["duplicadas"]
        if reporte["rechazadas"] and confirmar:
            reporte["mensaje"] = "Corrija las filas rechazadas; no se importó nada."
        return reporte

    sha = hashlib.sha256(contenido).hexdigest()
    origen = f"importacion:{sha[:12]}"
    with transaccion(con):
        for linea, t, oc in sorted(validas, key=lambda x: (x[1]["fecha"] if "fecha" in x[1] else x[1]["compra"]["fecha"], x[0])):
            if tipo == "transacciones":
                if cartera.registrar(con, t, origen, oc) is not None:
                    reporte["aceptadas"] += 1
            elif tipo == "posiciones":
                if cartera.registrar(con, t["aportacion"], origen, oc) is not None:
                    cartera.registrar(con, t["compra"], origen, oc)
                    reporte["aceptadas"] += 1
            else:
                con.execute("INSERT OR REPLACE INTO precios VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (t["instrumento_id"], t["fecha"], t["precio"], None, None, t["moneda"], "archivo",
                             t["tipo_dato"], None, ahora()))
                reporte["aceptadas"] += 1
        cur = con.execute("INSERT INTO importaciones (ts, archivo, sha256, tipo, filas, aceptadas, duplicadas, rechazadas,"
                          " contenido_original) VALUES (?,?,?,?,?,?,?,?,?)",
                          (ahora(), nombre[:100], sha, tipo, reporte["filas"], reporte["aceptadas"],
                           reporte["duplicadas"], reporte["rechazadas"], contenido))
        auditar(con, "importacion", cur.lastrowid, "alta", despues={k: v for k, v in reporte.items() if k != "detalle"})
        cartera.calcular(cartera.listar(con), {})  # la cartera resultante debe ser coherente
    reporte["confirmado"] = True
    return reporte


def _posicion(f: dict, instrumentos: dict) -> dict:
    compra = cartera.validar({"fecha": f.get("fecha"), "tipo": "compra", "instrumento_id": f.get("instrumento_id"),
                              "cantidad": f.get("cantidad"), "precio": f.get("costo_promedio"),
                              "moneda": f.get("moneda"), "tipo_cambio": f.get("tipo_cambio"),
                              "nota": "Saldo inicial importado"}, instrumentos)
    aport = {**compra, "tipo": "aportacion", "instrumento_id": None, "cantidad": 0.0, "precio": 0.0,
             "monto": compra["cantidad"] * compra["precio"], "nota": f"Aportación en especie ({compra['instrumento_id']})"}
    return {"fecha": compra["fecha"], "aportacion": aport, "compra": compra}


def _precio(f: dict, instrumentos: dict) -> dict:
    e = []
    iid = (f.get("instrumento_id") or "").strip().upper()
    if iid not in instrumentos:
        e.append(f"instrumento_id: «{iid[:30]}» no está en el universo verificado")
    try:
        fecha = date.fromisoformat(f.get("fecha", "")[:10])
        if fecha > date.today():
            e.append("fecha: no puede estar en el futuro")
    except ValueError:
        e.append("fecha: use el formato AAAA-MM-DD")
        fecha = None
    precio = cartera._num(f.get("precio"), "precio", e)
    if precio <= 0:
        e.append("precio: debe ser mayor que cero")
    tipo_dato = (f.get("tipo_dato") or "cierre").lower()
    if tipo_dato not in ("cierre", "nav"):
        e.append("tipo_dato: use «cierre» o «nav»")
    moneda = (f.get("moneda") or (instrumentos.get(iid, {}).get("moneda_referencia") or "MXN")).upper()
    if iid in instrumentos and moneda != (instrumentos[iid].get("moneda_referencia") or "MXN"):
        e.append(f"moneda: el precio de {iid} debe estar en {instrumentos[iid].get('moneda_referencia')}")
    if e:
        raise cartera.ErrorValidacion(e)
    return {"fecha": fecha.isoformat(), "instrumento_id": iid, "precio": precio, "moneda": moneda, "tipo_dato": tipo_dato}
