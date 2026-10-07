"""Precios de EE. UU. desde Finviz Elite (exportación CSV con token). APAGADO hasta que exista FINVIZ_AUTH_TOKEN.

Qué se comprobó (7-oct-2026):
- Finviz gratuito: cotizaciones diferidas y SIN exportación; su robots.txt prohíbe a los programas las páginas de
  exportación y la API CSV del screener. Por eso no se extrae nada de la versión gratuita.
- Finviz Elite (de pago: USD 39.50/mes o 299.50/año) incluye tiempo real y exportación/API con un token personal.
  Contratarlo es decisión del usuario (mandato, sección 7): la terminal no lo activa sola.

Reglas:
- Solo emisoras con listado de origen en EE. UU. (las del SIC). Es la bolsa de ORIGEN en USD: nunca sustituye al
  precio del SIC en la BMV en pesos; se guarda como precio del día (`finviz_vivo`) y el cierre oficial lo reemplaza.
- La exportación no trae la hora del último hecho, así que la latencia no se puede medir: se registra como
  «retrasado» y estado UNKNOWN, aunque Elite declare tiempo real. Nunca se etiqueta «tiempo real» sin medirlo.
- El token vive solo en .env y nunca se registra: los errores informan el tipo, no la URL.
- La dirección y los parámetros vienen de config/proveedores/finviz_elite.json; hay que confirmarlos con el botón
  «Export» de la cuenta Elite antes del primer uso.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import time
from datetime import UTC, datetime

import httpx
import pandas as pd

from . import vigencia
from .config import RAIZ

log = logging.getLogger("terminal.finviz")
PROVEEDOR = "finviz_vivo"
VARIABLE = "FINVIZ_AUTH_TOKEN"
ESPEC = RAIZ / "config" / "proveedores" / "finviz_elite.json"
LOTE = 100


class FinvizNoDisponible(Exception):
    pass


def especificacion() -> dict:
    return json.loads(ESPEC.read_text(encoding="utf-8"))


def pendientes(env: dict | None = None) -> list[str]:
    env = os.environ if env is None else env
    return [] if env.get(VARIABLE) else [f"suscripción Finviz Elite (de pago; decisión del usuario) y su token en .env como {VARIABLE}"]


def simbolo(listado: str) -> str:
    return listado.upper().replace(".", "-")  # BRK.B → BRK-B, como lo escribe Finviz


def leer_csv(texto: str) -> dict[str, float]:
    """Ticker → precio. Ignora filas sin precio numérico positivo."""
    out = {}
    for f in csv.DictReader(io.StringIO(texto.lstrip("﻿"))):
        try:
            p = float(str(f.get("Price", "")).replace(",", ""))
        except ValueError:
            continue
        if p > 0 and f.get("Ticker"):
            out[f["Ticker"].strip().upper()] = p
    return out


def consultar(simbolos: list[str], token: str, cliente: httpx.Client | None = None, espec: dict | None = None) -> dict[str, float]:
    e = espec or especificacion()
    cli = cliente or httpx.Client(timeout=20)
    out: dict[str, float] = {}
    for i in range(0, len(simbolos), LOTE):
        params = {**e["parametros"], e["parametro_simbolos"]: ",".join(simbolos[i:i + LOTE]), e["parametro_token"]: token}
        try:
            r = cli.get(e["url"], params=params)
        except httpx.HTTPError as ex:
            raise FinvizNoDisponible(f"sin conexión ({type(ex).__name__})") from None
        if r.status_code in (401, 403):
            raise FinvizNoDisponible(f"token rechazado (HTTP {r.status_code})")
        if r.status_code == 429:
            raise FinvizNoDisponible("límite de peticiones de Finviz (HTTP 429)")
        if r.status_code != 200 or "Ticker" not in r.text[:500]:
            raise FinvizNoDisponible(f"respuesta inesperada (HTTP {r.status_code})")
        out.update(leer_csv(r.text))
    return out


def actualizar(con, ajustes, ahora: datetime | None = None, env: dict | None = None,
               cliente: httpx.Client | None = None) -> dict:
    """Una consulta en lote de todas las emisoras SIC activas, como máximo cada `intervalo_min`, con la bolsa abierta."""
    env = os.environ if env is None else env
    cfg = dict(ajustes.get("finviz") or {})
    falta = pendientes(env)
    if falta:
        return {"estado": "sin_credencial", "pendientes": falta}
    if not cfg.get("activo", True):
        return {"estado": "desactivado"}
    ahora = ahora or datetime.now(UTC)
    if not vigencia.mercado_abierto("XNYS", ahora):
        return {"estado": "mercado_cerrado"}
    previo = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='finviz'").fetchone()
    if previo:
        ultimo = json.loads(previo[0]).get("ultima_consulta")
        if ultimo and (ahora - datetime.fromisoformat(ultimo)).total_seconds() < float(cfg.get("intervalo_min", 5)) * 60:
            return {"estado": "en_espera"}
    mapa: dict[str, list[str]] = {}
    for r in con.execute("SELECT id, listado_referencia FROM instrumentos WHERE estado='activo' AND moneda_referencia='USD' "
                         "AND listado_referencia IS NOT NULL AND listado_referencia <> ''"):
        mapa.setdefault(simbolo(r[1]), []).append(r[0])
    t0 = time.monotonic()
    try:
        precios = consultar(sorted(mapa), env[VARIABLE], cliente)
        estado = {"estado": "ok", "simbolos": len(mapa), "precios": len(precios)}
    except FinvizNoDisponible as e:
        precios, estado = {}, {"estado": "error", "mensaje": str(e)}
        log.warning("Finviz: %s", e)
    recep = datetime.now(UTC).isoformat()
    fecha = pd.Timestamp(ahora).tz_convert("America/New_York").date().isoformat()  # sesión de Nueva York en curso
    filas, registro = [], []
    for s, p in precios.items():
        for iid in mapa.get(s, []):
            filas.append((iid, fecha, p, None, None, "USD", PROVEEDOR, "retrasado", recep, recep))
            registro.append((PROVEEDOR, s, f"US:{s}", iid, "origen_extranjero", "EE. UU.", p, "USD", recep, recep, 0.0,
                             None, "UNKNOWN", 0, "Finviz Elite: sin hora del último hecho; latencia no medible"))
    with con:
        con.executemany("INSERT OR REPLACE INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, "
                        "proveedor, tipo_dato, hora_cotizacion, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)", filas)
        con.executemany("INSERT INTO cotizaciones_registro (proveedor, simbolo_origen, simbolo_normalizado, instrumento_id, "
                        "mercado, bolsa, precio, moneda, hora_evento, hora_recepcion, latencia_declarada_s, "
                        "latencia_medida_s, estado_latencia, sintetico, detalle) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        registro)
        estado.update(ultima_consulta=ahora.isoformat(), duracion_s=round(time.monotonic() - t0, 1), guardados=len(filas))
        con.execute("INSERT INTO ajustes_usuario VALUES ('finviz', ?, ?) ON CONFLICT(clave) DO UPDATE SET "
                    "valor=excluded.valor, actualizado_en=excluded.actualizado_en", (json.dumps(estado), recep))
    return estado
