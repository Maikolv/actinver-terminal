"""Plan del día por Telegram: cada mañana hábil de la BMV, a la hora configurada, un solo mensaje con las órdenes que
sugiere la propuesta mejor puntuada (emisora, títulos y monto), los cambios frente al plan del día anterior y el porqué.

Solo informativo: la terminal nunca envía órdenes; el participante las captura a mano en el simulador del Reto.
El envío se registra en `ajustes_usuario` (clave «resumen_matutino») para no repetirse el mismo día.
"""
from __future__ import annotations

import json
import logging
import math
import sqlite3
from datetime import UTC, datetime

import pandas as pd

from . import db, notificador, reto, vigencia

log = logging.getLogger("terminal.resumen")
ZONA = "America/Mexico_City"
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


def propuesta_referencia(propuestas: dict) -> dict | None:
    """La propuesta vigente con mayor puntuación (sin las variantes por mercado, que son informativas)."""
    cands = [p for p in propuestas.values() if p and not p.get("mercado_variante") and p.get("estado") == "calculada"
             and not p.get("avisos") and p.get("puntuacion")]
    return max(cands, key=lambda x: x["puntuacion"]["total"]) if cands else None


def ordenes(p: dict, cartera: dict) -> list[dict]:
    """Órdenes de la propuesta con títulos enteros. En el SIC el precio es referencia de la bolsa de origen."""
    precios = {a["id"]: a.get("precio_mxn") for a in p.get("pesos") or []}
    precios.update({x["instrumento_id"]: x.get("precio_mxn") for x in cartera.get("posiciones", []) if x.get("precio_mxn")})
    motivos = {a["id"]: (a.get("motivos") or [""])[0] for a in p.get("pesos") or []}
    out = []
    for f in (p.get("cambios") or {}).get("filas", []):
        if f["accion"] == "mantener":
            continue
        px = precios.get(f["id"])
        titulos = math.floor(abs(f["monto_mxn"]) / px) if px else None
        if titulos == 0:
            continue
        out.append({"id": f["id"], "clave": f.get("clave_operable") or f["id"], "accion": f["accion"], "titulos": titulos,
                    "precio": px, "monto": abs(f["monto_mxn"]), "delta_pp": f["delta_pp"], "sic": f["id"].startswith("SIC:"),
                    "motivo": motivos.get(f["id"], "")})
    return sorted(out, key=lambda o: (o["accion"] != "vender", -o["monto"]))


def cambios_vs_anterior(hoy: list[dict], ayer: list[dict] | None) -> list[str]:
    if ayer is None:
        return ["Primer plan enviado: no hay uno anterior para comparar."]
    a = {(o["id"], o["accion"]): o for o in ayer}
    b = {(o["id"], o["accion"]): o for o in hoy}
    out = []
    for k in b.keys() - a.keys():
        out.append(f"Nueva: {'comprar' if k[1] == 'comprar' else 'vender'} {b[k]['clave']}.")
    for k in a.keys() - b.keys():
        out.append(f"Ya no se sugiere {'comprar' if k[1] == 'comprar' else 'vender'} {a[k]['clave']}.")
    for k in a.keys() & b.keys():
        ta, tb = a[k].get("titulos"), b[k].get("titulos")
        if ta and tb and abs(tb - ta) / ta >= 0.10:
            out.append(f"{b[k]['clave']}: {ta:,} → {tb:,} títulos.")
    return out or ["Sin cambios frente al plan anterior."]


def construir(p: dict, cartera: dict, anterior: list[dict] | None, ahora_local: pd.Timestamp) -> tuple[str, str, list[dict]]:
    ords = ordenes(p, cartera)
    etapa = reto.etapa_operativa(ahora_local.to_pydatetime()) if reto.activo() else None
    cab = f"☀️ Plan del día — {DIAS[ahora_local.weekday()]} {ahora_local:%d-%m-%Y}"
    if etapa:
        cab += f" · Reto: {'práctica' if etapa == 'practica' else etapa}, {reto.sesiones_restantes(ahora_local.to_pydatetime())} sesiones restantes"
    base = (f"tu cuenta del Reto (captura del {pd.Timestamp(cartera['captura']['hora_portal']).tz_convert(ZONA):%d-%m %H:%M})"
            if cartera.get("fuente") == "portal" else "el registro local de la terminal (sin captura del portal)")
    lineas = [cab, "",
              f"Propuesta: {p['nombre']} — {p['puntuacion']['total']:.1f}/100 (datos al {p.get('datos_hasta')}).",
              f"Frente a: {base}.", ""]
    if not ords:
        lineas.append("✅ Sin órdenes sugeridas: la cartera ya está dentro de la banda de rebalanceo.")
    else:
        lineas.append(f"Órdenes sugeridas ({len(ords)}):")
        for o in ords:
            icono = "🔴 Vender" if o["accion"] == "vender" else "🟢 Comprar"
            tit = (f"{o['titulos']:,} {'título' if o['titulos'] == 1 else 'títulos'}" if o["titulos"]
                   else "títulos: calcule con el precio del portal")
            px = f" a ~${o['precio']:,.2f}" if o["precio"] else ""
            real = o["titulos"] * o["precio"] if (o["titulos"] and o["precio"]) else o["monto"]
            obj = f" (objetivo ${o['monto']:,.0f})" if real < 0.85 * o["monto"] else ""
            nota = " (precio de referencia; confirme en el portal)" if o["sic"] else ""
            lineas.append(f"{icono} {o['clave']}: {tit}{px} ≈ ${real:,.0f}{obj}{nota}")
        lineas.append(f"Costo estimado (comisión + IVA): ${(p.get('cambios') or {}).get('costo_total', 0):,.0f}.")
    lineas += ["", "Cambios frente al plan anterior:"] + [f"• {c}" for c in cambios_vs_anterior(ords, anterior)]
    crit = sorted(p["puntuacion"].get("criterios", []), key=lambda c: -c["puntos"])
    lineas += ["", "Por qué:"]
    if crit:
        fuertes = ", ".join(f"{c['criterio'].replace('_', ' ')} {c['puntos']:.0f}" for c in crit[:3])
        debil = crit[-1]
        lineas.append(f"• Puntuación: mejor en {fuertes}; lo más débil: {debil['criterio'].replace('_', ' ')} {debil['puntos']:.0f}.")
    for o in [o for o in ords if o["motivo"]][:6]:
        lineas.append(f"• {o['clave']}: {o['motivo']}")
    if p.get("riesgos"):
        lineas.append(f"• Riesgo principal: {p['riesgos'][0]}")
    lineas += ["", "Solo informativo. Genere las boletas en la terminal (precio límite actualizado) y capture cada orden "
                   "a mano en el simulador."]
    return cab, "\n".join(lineas), ords


def _estado(con: sqlite3.Connection) -> dict:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='resumen_matutino'").fetchone()
    return json.loads(f["valor"]) if f else {}


REINTENTO_MIN = 10
MAX_INTENTOS = 12
ESPERA_RECALCULO_MIN = 60


def entregado(estado: dict) -> bool:
    """Solo cuenta como enviado si Telegram lo confirmó (o si Telegram no está configurado y otro canal sí)."""
    r = estado.get("resultado") or {}
    return r.get("telegram") == "enviada" or (r.get("telegram") in (None, "no_configurado") and "enviada" in r.values())


def toca(ajustes, ahora: datetime, estado: dict) -> bool:
    cfg = ajustes["alertas"]
    if not cfg.get("resumen_matutino", True):
        return False
    local = pd.Timestamp(ahora).tz_convert(ZONA)
    h, m = (int(x) for x in str(cfg.get("resumen_matutino_hora", "07:00")).split(":"))
    if (local.hour, local.minute) < (h, m):
        return False
    if estado.get("fecha") == local.date().isoformat():
        if entregado(estado) or int(estado.get("intentos", 1)) >= MAX_INTENTOS:
            return False
        ultimo = pd.Timestamp(estado.get("enviado_en") or ahora)
        if pd.Timestamp(ahora) - ultimo < pd.Timedelta(minutes=REINTENTO_MIN):
            return False  # reintento tras un fallo de canal, cada 10 minutos
    return bool(vigencia.calendario("XMEX").is_session(local.date().isoformat()))


def enviar_si_toca(con: sqlite3.Connection, ajustes, cartera: dict, propuestas: dict,
                   ahora: datetime | None = None) -> dict | None:
    """Envía el plan del día una vez por sesión hábil, a partir de la hora configurada."""
    ahora = ahora or datetime.now(UTC)
    estado = _estado(con)
    if not toca(ajustes, ahora, estado):
        return None
    local = pd.Timestamp(ahora).tz_convert(ZONA)
    h, m = (int(x) for x in str(ajustes["alertas"].get("resumen_matutino_hora", "07:00")).split(":"))
    minutos = (local.hour - h) * 60 + (local.minute - m)
    if any(p and p.get("recalcular") for p in propuestas.values()) and minutos < ESPERA_RECALCULO_MIN:
        return None  # las propuestas se están recalculando: se espera para no enviar un plan viejo
    p = propuesta_referencia(propuestas)
    if p is None:
        titulo, texto, ords = (f"☀️ Plan del día — {local:%d-%m-%Y}",
                               "No hay una propuesta vigente (datos no actualizados o propuestas suspendidas). Revise la "
                               "pestaña Datos de la terminal; no se sugieren órdenes hoy.", [])
    else:
        titulo, texto, ords = construir(p, cartera, estado.get("ordenes"), local)
    cfg = {**ajustes["alertas"], "notificar_escritorio": False, "notificar_telegram": True}
    res = notificador.enviar(titulo, texto, cfg, detalle=texto)
    ok = entregado({"resultado": res})
    nuevo = {"fecha": local.date().isoformat(), "enviado_en": ahora.isoformat(timespec="seconds"), "resultado": res,
             "intentos": int(estado.get("intentos", 1)) + 1 if estado.get("fecha") == local.date().isoformat() else 1,
             "propuesta": p["clave"] if p else None,
             # base para comparar el próximo plan: el último que SÍ llegó
             "ordenes": [{k: o[k] for k in ("id", "clave", "accion", "titulos")} for o in ords] if (p and ok)
             else estado.get("ordenes")}
    with db.transaccion(con):
        con.execute("INSERT INTO ajustes_usuario VALUES ('resumen_matutino', ?, ?) ON CONFLICT(clave) DO UPDATE SET "
                    "valor=excluded.valor, actualizado_en=excluded.actualizado_en", (json.dumps(nuevo), db.ahora()))
    log.info("plan del día enviado: %s", res)
    return {**nuevo, "texto": texto}


def enviar_muestra(con: sqlite3.Connection, ajustes, cartera: dict, propuestas: dict) -> dict:
    """Envía ahora el plan con los datos actuales, marcado como MUESTRA; no cuenta como el envío del día."""
    local = pd.Timestamp(datetime.now(UTC)).tz_convert(ZONA)
    p = propuesta_referencia(propuestas)
    if p is None:
        return {"resultado": None, "texto": "No hay propuesta vigente para armar el plan."}
    titulo, texto, _ = construir(p, cartera, _estado(con).get("ordenes"), local)
    titulo, texto = "MUESTRA — " + titulo, "MUESTRA (envío de prueba)\n" + texto
    cfg = {**ajustes["alertas"], "notificar_escritorio": False, "notificar_telegram": True}
    return {"resultado": notificador.enviar(titulo, texto, cfg, detalle=texto), "texto": texto}
