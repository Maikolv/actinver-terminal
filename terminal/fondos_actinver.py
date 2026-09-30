"""Precios de los fondos Actinver desde su hoja oficial «Reporte Diario» (PDF público de actinver.com).

Fuente: https://actinver.com/documents/d/actinver/reporte-diario, que enlaza «Hoja de precios y rendimientos» en
actinver.com/fondos. El robots.txt del sitio no restringe /documents/. Se descarga como máximo una vez cada pocas
horas hasta obtener la valuación del día; también se puede subir el PDF a mano.

Cada fila guardada es verificable: fondo, serie, moneda, precio y **fecha de valuación**, que se lee del propio
documento («precios de valuación al DD/MM/AA»). Además se guardan la huella SHA-256 y una copia local del PDF en
data/fuentes/actinver/. El precio es el valor por unidad (NAV) publicado por Actinver con datos de GAF y Valmer:
tipo «nav» y nunca tiempo real. Los rendimientos del PDF no se usan: algunas cifras del documento no son
consistentes y solo se toma el precio.
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
import sqlite3
from datetime import UTC, date, datetime, timedelta

import httpx

from . import config, vigencia
from .db import ahora, auditar, transaccion

log = logging.getLogger("terminal.fondos_actinver")
PROVEEDOR = "actinver_pdf"
URL = "https://actinver.com/documents/d/actinver/reporte-diario"
REINTENTO_HORAS = 3
RE_FECHA = re.compile(r"precios de valuaci[oó]n al (\d{2})/(\d{2})/(\d{2})")
RE_FONDO = re.compile(r"^([A-Z][A-Z0-9+&]{2,11})(?:\s+-\s?\S.*)?$")  # «ACTIG+2 -Morningstar…»: el pie se pega a la clave
RE_SERIE = re.compile(r"^([A-Z]{1,3}(?:-\d{1,2})?)(?:;\s*(USD|MXN))?\s+(\d+\.\d{4,8})(?:\s|$)")


class ErrorHoja(ValueError):
    pass


def texto_pdf(contenido: bytes) -> str:
    from pypdf import PdfReader
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(contenido)).pages)
    except Exception as e:  # noqa: BLE001 - PDF dañado o no es PDF
        raise ErrorHoja(f"No se pudo leer el PDF ({type(e).__name__}).") from None


def interpretar(texto: str) -> dict:
    """Filas {fondo, serie, moneda, precio} y la fecha de valuación declarada en el documento."""
    fechas = {f"20{a}-{m}-{d}" for d, m, a in RE_FECHA.findall(texto)}
    if len(fechas) != 1:
        raise ErrorHoja("El documento no declara una única fecha de valuación («precios de valuación al …»); no se importa.")
    fondo, filas = None, []
    for linea in (l.strip() for l in texto.splitlines()):
        if not linea:
            continue
        mf = RE_FONDO.match(linea)
        if mf:
            fondo = mf.group(1)
            continue
        m = RE_SERIE.match(linea)
        if m and fondo:
            filas.append({"fondo": fondo, "serie": m.group(1), "moneda": m.group(2) or "MXN", "precio": float(m.group(3))})
    if not filas:
        raise ErrorHoja("No se encontraron precios por fondo y serie en el documento.")
    return {"fecha_valuacion": fechas.pop(), "filas": filas}


def importar(con: sqlite3.Connection, contenido: bytes, origen: str, confirmar: bool = True) -> dict:
    """Asigna cada fondo del universo (misma clave y serie, precio en MXN) y guarda con su fecha de valuación.
    Un precio de la misma fecha no se sobrescribe con uno distinto sin dejar constancia en la auditoría."""
    if not contenido.startswith(b"%PDF"):
        raise ErrorHoja("El archivo no es un PDF.")
    hoja = interpretar(texto_pdf(contenido))
    sha = hashlib.sha256(contenido).hexdigest()
    fondos = {r["id"]: dict(r) for r in con.execute("SELECT * FROM instrumentos WHERE clase LIKE 'fondo%'")}
    por_clave, ambiguos = {}, set()
    for f in hoja["filas"]:
        k = (f["fondo"], f["serie"], f["moneda"])
        if k in por_clave and abs(por_clave[k] - f["precio"]) > 1e-9:
            ambiguos.add(k)  # dos precios distintos para la misma serie: no se asigna ninguno
        por_clave[k] = f["precio"]
    for k in ambiguos:
        por_clave.pop(k)
    asignados, sin_serie = [], []
    for iid, ins in sorted(fondos.items()):
        precio = por_clave.get((ins["clave"], ins.get("serie") or "B", "MXN"))
        if precio is None:
            sin_serie.append(iid)
        else:
            asignados.append((iid, precio))
    rep = {"fecha_valuacion": hoja["fecha_valuacion"], "sha256": sha, "filas_documento": len(hoja["filas"]),
           "asignados": len(asignados), "sin_serie_en_documento": sin_serie, "origen": origen, "confirmado": False,
           "precios": [{"id": i, "precio": p} for i, p in asignados]}
    if not confirmar or not asignados:
        return rep
    ts = ahora()
    with transaccion(con):
        for iid, precio in asignados:
            previo = con.execute("SELECT cierre FROM precios WHERE instrumento_id=? AND fecha=? AND proveedor=?",
                                 (iid, hoja["fecha_valuacion"], PROVEEDOR)).fetchone()
            if previo and abs(previo["cierre"] - precio) > 1e-9:
                auditar(con, "precio", iid, "correccion_fuente", antes={"precio": previo["cierre"]},
                        despues={"precio": precio, "sha256": sha})
            con.execute("INSERT OR REPLACE INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, "
                        "proveedor, tipo_dato, hora_cotizacion, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (iid, hoja["fecha_valuacion"], precio, precio, None, "MXN", PROVEEDOR, "nav", None, ts))
            from .ingesta import registrar_cobertura
            ins = fondos[iid]
            registrar_cobertura(con, PROVEEDOR, iid, f"{ins['clave']} {ins.get('serie') or 'B'}",
                                f"fondo y serie exactos en la hoja oficial (valuación {hoja['fecha_valuacion']}, sha256 {sha[:12]})")
        con.execute("INSERT INTO importaciones (ts, archivo, sha256, tipo, filas, aceptadas, duplicadas, rechazadas, "
                    "contenido_original) VALUES (?,?,?,?,?,?,?,?,?)",
                    (ts, origen[:100], sha, "hoja_fondos_actinver", len(hoja["filas"]), len(asignados), 0, len(sin_serie),
                     b""))  # el PDF se conserva en data/fuentes/actinver/, no en la base
    carpeta = config.data_dir() / "fuentes" / "actinver"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{hoja['fecha_valuacion']}_{sha[:12]}.pdf").write_bytes(contenido)
    rep["confirmado"] = True
    return rep


def valuacion_esperada(ahora_dt: datetime) -> date:
    """El reporte de cada día publica la valuación de la sesión hábil anterior."""
    import pandas as pd
    cal = vigencia.calendario("XMEX")
    hoy = pd.Timestamp(pd.Timestamp(ahora_dt).tz_convert("America/Mexico_City").date())
    s = cal.date_to_session(hoy, direction="previous")
    return (cal.previous_session(s) if s == hoy else s).date()


def _ultima_valuacion(con) -> str | None:
    return con.execute("SELECT MAX(fecha) FROM precios WHERE proveedor=?", (PROVEEDOR,)).fetchone()[0]


def actualizar(con: sqlite3.Connection, ajustes, cliente: httpx.Client | None = None,
               ahora_dt: datetime | None = None) -> dict:
    """Descarga la hoja si falta la valuación esperada (la sesión anterior) y no hubo intento en las últimas horas."""
    cfg = (ajustes["proveedores"].get("actinver_pdf") or {}) if hasattr(ajustes, "__getitem__") else {}
    if cfg.get("activo") is False:
        return {"estado": "desactivado"}
    ahora_dt = ahora_dt or datetime.now(UTC)
    esperada = valuacion_esperada(ahora_dt)
    ultima = _ultima_valuacion(con)
    if ultima and date.fromisoformat(ultima) >= esperada:
        return {"estado": "al_dia", "fecha_valuacion": ultima}
    intento = con.execute("SELECT MAX(inicio) FROM ingestas WHERE proveedor=?", (PROVEEDOR,)).fetchone()[0]
    if intento and ahora_dt - datetime.fromisoformat(intento) < timedelta(hours=REINTENTO_HORAS):
        return {"estado": "en_espera", "fecha_valuacion": ultima}
    cli = cliente or httpx.Client(timeout=60, follow_redirects=True,
                                  headers={"User-Agent": "actinver-terminal/uso-personal (lectura de la hoja publica)"})
    try:
        r = cli.get(URL)
        if r.status_code != 200:
            raise ErrorHoja(f"HTTP {r.status_code}")
        rep = importar(con, r.content, URL)
        return {"estado": "ok", **{k: rep[k] for k in ("fecha_valuacion", "asignados", "sin_serie_en_documento")}}
    except (httpx.HTTPError, ErrorHoja) as e:
        return {"estado": "error", "mensaje": str(e)[:200]}
