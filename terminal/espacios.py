"""Tres espacios de tiempo separados: PASADO (hechos observados), PRESENTE (estado observable ahora) y FUTURO
(estimaciones). Un pronóstico nunca se guarda ni se muestra como cotización, y el precio externo nunca se presenta
como el precio o saldo de Actinver."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from . import alertas, cotizaciones as cz, mercado, reto, servicios, vigencia
from .config import Ajustes
from .investigacion import evaluacion, pronosticos


def pasado(con: sqlite3.Connection, ajustes: Ajustes) -> dict:
    cond, par = ("proveedor = ?", ("demo_sintetico",)) if ajustes.es_demo else ("proveedor <> ?", ("demo_sintetico",))
    fuentes = [dict(r) for r in con.execute(
        f"SELECT proveedor, tipo_dato, COUNT(*) AS filas, COUNT(DISTINCT instrumento_id) AS instrumentos, MIN(fecha) AS desde, "
        f"MAX(fecha) AS hasta, MAX(available_at) AS ultimo_disponible FROM precios WHERE {cond} GROUP BY proveedor, tipo_dato", par)]
    ops = [dict(r) for r in con.execute(
        "SELECT id, fecha, tipo, instrumento_id, cantidad, precio, monto, comision, impuesto, etapa, confirmada, available_at "
        "FROM transacciones WHERE anulada=0 ORDER BY fecha DESC, id DESC LIMIT 100")]
    noticias = [dict(r) for r in con.execute(
        "SELECT instrumento_id, titulo, fuente, event_time AS publicado, available_at, impacto FROM noticias "
        "ORDER BY publicado DESC LIMIT 20")]
    eventos = [dict(r) for r in con.execute(
        "SELECT instrumento_id, fecha, tipo, valor, proveedor, available_at FROM eventos_corporativos ORDER BY fecha DESC LIMIT 20")]
    exps = []
    for H in (1, 5):
        e = evaluacion.ultimo(con, H, ajustes.es_demo)
        if e:
            exps.append({k: e.get(k) for k in ("H", "L", "hora_corte", "cortes", "n_ejemplos", "purgados", "variante_elegida",
                                               "alfa_por_variante", "filtro_correlacion_por_pliegue", "variables_eliminadas_final",
                                               "correlacion_activos_entrenamiento", "huella_config", "huella_datos", "semilla",
                                               "version_codigo", "prueba_ya_vista", "datos")})
    return {"espacio": "PASADO", "descripcion": "Hechos observados con su fecha real y su hora de disponibilidad (available_at).",
            "fuentes": fuentes, "operaciones_confirmadas": ops, "noticias": noticias, "eventos_corporativos": eventos,
            "experimentos": exps, "demo": ajustes.es_demo}


def _referencia_mxn(q: dict | None, fx: dict) -> dict | None:
    if not q:
        return None
    return {**q, "precio_mxn_estimado": (q["precio"] * fx["valor"]) if fx.get("valor") else None,
            "tipo_cambio": fx.get("valor"), "fecha_tipo_cambio": fx.get("fecha"),
            "etiqueta": "Referencia externa (bolsa de origen × tipo de cambio). NO es el precio del SIC en la BMV."}


def presente(con: sqlite3.Connection, ajustes: Ajustes) -> dict:
    ahora = datetime.now(UTC)
    cart = servicios.cartera_actual(con, ajustes)
    ins = mercado.instrumentos(con)
    provs = cz.construir(con, ajustes.es_demo)
    fx = mercado.ultimo_fx(con, ajustes)
    prioridad = ["demo"] if ajustes.es_demo else None
    filas = []
    for p in cart["posiciones"]:
        i = ins.get(p["instrumento_id"]) or {"id": p["instrumento_id"]}
        conf = cz.precio_confiable(con, provs, i, ahora, prioridad=prioridad)
        ref = None
        if i.get("moneda_referencia") == "USD":
            try:
                ref = provs["referencia_origen"].cotizacion(i).a_dict()
            except cz.ProveedorNoDisponible:
                ref = None
        filas.append({"instrumento_id": i["id"], "clave_operable": i.get("clave_operable"), "cantidad": p["cantidad"],
                      "costo_promedio": p["costo_promedio"], "precio_bmv": conf, "referencia_externa": _referencia_mxn(ref, fx),
                      "precio_usado_para_estimar": p.get("precio_mxn"), "fuente_estimacion": p.get("proveedor"),
                      "valor_estimado": p.get("valor_mxn"), "peso": p.get("peso"), "vigencia": p.get("vigencia")})
    tx = [dict(r) for r in con.execute("SELECT * FROM transacciones WHERE anulada=0")]
    portal = con.execute("SELECT * FROM saldos_portal ORDER BY id DESC LIMIT 1").fetchone()
    portal = dict(portal) if portal else None
    etapa = cart.get("etapa") or reto.etapa_operativa()
    return {
        "espacio": "PRESENTE", "hora": ahora.isoformat(timespec="seconds"), "zona_horaria": "America/Mexico_City",
        "etapa_reto": reto.etapa(), "cartera_de": cart.get("etapa") or "historial completo (fuera de etapa del Reto)",
        "mercado_bmv_abierto": vigencia.mercado_abierto("XMEX"), "efectivo": cart["efectivo"],
        "valor_estimado": cart["valor_total"], "completa": cart["completa"], "sin_precio": cart["sin_precio"],
        "posiciones": filas,
        "exposicion": [{"instrumento_id": f["instrumento_id"], "peso": f["peso"]} for f in filas],
        "ganancia": reto.ganancia(cart["valor_total"], float(cart["aportacion_neta"] or 0), float(cart["comisiones"] or 0)),
        "acciones_operadas": reto.acciones_operadas(tx, ins, etapa or "competencia"),
        "saldo_portal": portal, "diferencia_portal": (cart["valor_total"] / portal["valor_portafolio"] - 1) if portal else None,
        "alertas_activas": [a for a in alertas.listar(con, 50) if a["estado"] == "nueva"],
        "proveedores": [p.estado() for p in provs.values()], "tipo_cambio": fx,
        "nota": ("«Valor estimado» usa los precios que tiene la terminal (cierres o referencias externas). La valuación "
                 "oficial es la del portal de Actinver: capture su saldo para comparar. La terminal no entra al portal."),
    }


def futuro(con: sqlite3.Connection, ajustes: Ajustes) -> dict:
    lista = pronosticos.listar(con)
    ids = {p["instrumento_id"] for p in lista}
    ins = mercado.instrumentos(con)
    for p in lista:
        p["clave_operable"] = (ins.get(p["instrumento_id"]) or {}).get("clave_operable")
    exps = []
    for H in (1, 5):
        e = evaluacion.ultimo(con, H, ajustes.es_demo)
        if e:
            exps.append({k: e.get(k) for k in ("H", "hora_corte", "prueba", "supera_referencias", "recomendacion_permitida",
                                               "conclusion", "prueba_ya_vista", "aviso", "datos", "variante_elegida")})
    permitido = bool(exps) and all(e["recomendacion_permitida"] for e in exps)
    return {"espacio": "FUTURO", "etiqueta": "ESTIMACIONES — no son cotizaciones ni hechos",
            "pronosticos": lista, "n_instrumentos": len(ids), "experimentos": exps, "recomendacion_permitida": permitido,
            "deterioro": pronosticos.deterioro(con),
            "aviso": ("Probabilidades y rangos estimados con datos disponibles a la hora de emisión. Un embargo evita fugas "
                      "de información, pero no hace acertado un pronóstico. "
                      + ("" if permitido else "El modelo no superó a las referencias simples: no se emite recomendación de cambio."))}

