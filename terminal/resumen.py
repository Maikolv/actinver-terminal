"""Plan del día por Telegram: cada mañana hábil de la BMV, a la hora configurada, un solo mensaje con las órdenes que
sugiere la propuesta mejor puntuada (emisora, títulos y monto), los cambios frente al plan del día anterior y el porqué.

Solo informativo: la terminal nunca envía órdenes; el participante las captura a mano en el simulador del Reto.
El envío se registra en `ajustes_usuario` (clave «resumen_matutino») para no repetirse el mismo día.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
from datetime import UTC, date, datetime

import pandas as pd

from . import db, notificador, reto, vigencia

log = logging.getLogger("terminal.resumen")
ZONA = "America/Mexico_City"
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


CRITERIOS_PLAN = {"puntuacion": "mayor puntuación", "plusvalia": "mayor plusvalía esperada al cierre del Reto",
                  "ganancia": "mayor ganancia media esperada al cierre del Reto"}


def ganancia_esperada(p: dict) -> float | None:
    """Ganancia media esperada al cierre del Reto: media anual usada × años que faltan (sin el castigo por volatilidad
    de la mediana «central_p50»). Decisión del usuario del 5-oct-2026: prioridad, la mayor ganancia."""
    e = (p or {}).get("escenarios") or {}
    if e.get("media_anual_usada") is None or e.get("horizonte_anios") is None:
        return None
    return float(e["media_anual_usada"]) * float(e["horizonte_anios"])


MARGEN_MANTENER = 0.01  # 1 punto de ganancia al cierre del Reto, además de las comisiones


def mantener_es_mejor(p: dict | None, criterio: str, margen: float = MARGEN_MANTENER) -> dict | None:
    """Con criterio de ganancia: si la propuesta NO supera a mantener la cartera actual (mismo método, después de
    comisiones y por más que el margen de ruido), el plan no sugiere operar. Devuelve las cifras para explicarlo."""
    f = (p or {}).get("frente_a_mantener") or {}
    if criterio not in ("ganancia", "plusvalia") or not f.get("comparable"):
        return None
    k = "media" if criterio == "ganancia" else "central_p50"
    costo = float(((p.get("mejora_esperada") or {}).get("costo_cambio")) or 0)
    neta = f["propuesta"][k] - f["mantener"][k] - costo
    if neta >= margen:
        return None
    return {"propuesta": f["propuesta"][k], "mantener": f["mantener"][k], "costo": costo, "neta": neta, "margen": margen,
            "metrica": "ganancia promedio" if k == "media" else "resultado más común",
            "adverso_propuesta": f["propuesta"]["adverso_p10"], "adverso_mantener": f["mantener"]["adverso_p10"]}


def metrica_plan(p: dict, criterio: str) -> float | None:
    if criterio == "ganancia":
        return ganancia_esperada(p)
    return ((p or {}).get("escenarios") or {}).get("central_p50")


def criterio_plan(propuestas: dict) -> str:
    """Criterio elegido en el perfil («Reto y perfil»): cada propuesta guarda el perfil con que se calculó."""
    for p in propuestas.values():
        if p and p.get("perfil"):
            c = p["perfil"].get("criterio_plan", "puntuacion")
            return c if c in CRITERIOS_PLAN else "puntuacion"
    return "puntuacion"


def propuesta_referencia(propuestas: dict) -> dict | None:
    """La propuesta vigente que alimenta el plan (sin las variantes por mercado, que son informativas).
    Criterio «puntuacion» (por omisión): la mejor puntuada. Criterio «plusvalia»: la de mayor ganancia esperada al cierre
    (escenario central), con su riesgo explícito; desempata la puntuación."""
    cands = [p for p in propuestas.values() if p and not p.get("mercado_variante") and p.get("estado") == "calculada"
             and not p.get("avisos") and p.get("puntuacion")]
    if not cands:
        return None
    no_fragiles = [p for p in cands if (p.get("robustez") or {}).get("estado") != "frágil"]
    cands = no_fragiles or cands  # una estrategia frágil no es la referencia solo por un buen backtest (docs/robustez.md)
    fijada = [p for p in cands if p.get("referencia_fijada")]  # plan del día fijo (servicios._fijar_referencia)
    if fijada:
        return fijada[0]
    crit = criterio_plan(propuestas)
    if crit in ("plusvalia", "ganancia"):
        con_esc = [p for p in cands if metrica_plan(p, crit) is not None]
        if con_esc:
            return max(con_esc, key=lambda x: (metrica_plan(x, crit), x["puntuacion"]["total"]))
    return max(cands, key=lambda x: x["puntuacion"]["total"])


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


def cambios_vs_anterior(hoy: list[dict], ayer: list[dict] | None, con_titulos: bool = True) -> list[str]:
    if ayer is None:
        return ["Primer plan enviado: no hay uno anterior para comparar."]
    a = {(o["id"], o["accion"]): o for o in ayer}
    b = {(o["id"], o["accion"]): o for o in hoy}
    out = []
    for k in b.keys() - a.keys():
        out.append(f"Nueva: {'comprar' if k[1] == 'comprar' else 'vender'} {b[k]['clave']}.")
    for k in a.keys() - b.keys():
        out.append(f"Ya no se sugiere {'comprar' if k[1] == 'comprar' else 'vender'} {a[k]['clave']}.")
    for k in (a.keys() & b.keys()) if con_titulos else ():  # sin cuenta confirmada no se citan títulos
        ta, tb = a[k].get("titulos"), b[k].get("titulos")
        if ta and tb and abs(tb - ta) / ta >= 0.10:
            out.append(f"{b[k]['clave']}: {ta:,} → {tb:,} títulos.")
    return out or ["Sin cambios frente al plan anterior."]


RETIRO_MIN_DESPUES_DEL_CIERRE = 15  # margen para ver la última ejecución y copiar la cuenta del portal


def horario_del_dia(sesion: date) -> str:
    """Horas para el participante según el horario de las bases del Reto (07:30–14:00 hasta el 2-nov; 08:30–15:00 después)."""
    abre = vigencia.apertura_sesion("XMEX", sesion).tz_convert(ZONA)
    cierra = vigencia.cierre_sesion("XMEX", sesion).tz_convert(ZONA)
    retiro = cierra + pd.Timedelta(minutes=RETIRO_MIN_DESPUES_DEL_CIERRE)
    lineas = [f"🕖 Consulta el portal a las {abre:%H:%M} (apertura de la BMV): revisa precios, compáralos con las boletas y "
              "captura las órdenes limitadas del día.",
              f"🕑 Puedes retirarte a las {retiro:%H:%M}: la BMV cierra a las {cierra:%H:%M} y las órdenes limitadas que no se "
              "ejecutaron vencen al cierre. Antes, copia tu cuenta en «Mi portafolio Actinver → Actualizar desde el portal»."]
    fin = (reto.config().get("fechas") or {}).get("competencia_fin") if reto.activo() else None
    if fin and str(fin)[:10] == sesion.isoformat():
        lineas.append(f"🏁 Hoy cierra el Reto a las {str(fin)[11:16]}: después ya no se puede operar.")
    return "\n".join(lineas)


CRITERIOS_CORTOS = {"rendimiento_ajustado": "rend. ajustado", "riesgo": "riesgo", "diversificacion": "diversificación",
                    "liquidez": "liquidez", "costos": "costos", "calidad_datos": "calidad de datos"}


def _vigentes(props: dict | None) -> list[dict]:
    return [x for x in (props or {}).values() if x and x.get("estado") == "calculada" and x.get("puntuacion")
            and not x.get("mercado_variante")]


def _linea_propuesta(x: dict) -> str:
    e = x.get("escenarios") or {}
    c = x.get("comparacion") or []
    partes = [f"«{x['nombre']}» {x['puntuacion']['total']:.1f}/100"]
    if e.get("central_p50") is not None:
        partes.append(f"ESTIMACIÓN del modelo al cierre {e['central_p50']:+.1%} (rango {e['adverso_p10']:+.1%} a {e['favorable_p90']:+.1%}; "
                      f"volatilidad {e.get('volatilidad_anual', 0):.0%})")
    if c and c[0].get("rend_anual") is not None:
        ew = c[1].get("rend_anual") if len(c) > 1 else None
        partes.append(f"HISTÓRICO fuera de muestra {c[0]['rend_anual']:+.1%}/año" + (f" vs pesos iguales {ew:+.1%}" if ew is not None else "")
                      + f" ({c[0].get('sesiones')} sesiones)")
    rb = x.get("robustez") or {}
    if rb.get("estado") in ("robusta", "no aprobada", "frágil"):
        partes.append(f"robustez: {rb['estado'].upper()}" + (f" ({', '.join(rb['motivos'])})" if rb.get("motivos") else "")
                      + f" · SIMULACIÓN al cierre: prob. de pérdida {rb['simulacion_prob_perdida']:.0%}")
    v = x.get("validacion_extendida") or {}
    if v.get("estrategia"):  # historia larga (V1): la evidencia que cuenta para decir «ventaja»
        partes.append(f"HISTÓRICO, validación extendida {v['estrategia']['rend_anual']:+.1%}/año vs pesos iguales "
                      f"{v['iguales']['rend_anual']:+.1%} ({v['estrategia']['sesiones']} sesiones desde "
                      f"{v['estrategia']['desde'][:7]}; exceso IC 90 % {v['exceso_ic90'][0]:+.0%} a {v['exceso_ic90'][1]:+.0%}): "
                      f"{v['veredicto'].lower()}")
    return " · ".join(partes)


def _desglose(x: dict) -> str:
    return ", ".join(f"{CRITERIOS_CORTOS.get(c['criterio'], c['criterio'])} {c['puntos']:.0f}"
                     for c in x["puntuacion"].get("criterios", []))


def bloque_propuestas(props: dict | None, ref: dict, detalle: bool = False) -> list[str]:
    """Propuestas con máxima puntuación, cuál alimenta el plan y por qué, y la de mayor rendimiento esperado si es otra."""
    vig = _vigentes(props) or [ref]
    maxp = [x for x in vig if x.get("lente") == "puntuacion"]
    if ref not in maxp:
        maxp.insert(0, ref)
    out = ["📊 Propuestas con máxima puntuación:"]
    for x in sorted(maxp, key=lambda x: -x["puntuacion"]["total"]):
        marca = " ⬅ alimenta el plan" if x is ref or x.get("clave") == ref.get("clave") else ""
        out.append(f"• {_linea_propuesta(x)}{marca}")
        if detalle or marca:
            out.append(f"   desglose: {_desglose(x)}")
    crit = criterio_plan(props or {})
    plusvalia = crit in ("plusvalia", "ganancia")
    if crit == "ganancia":
        er = ref.get("escenarios") or {}
        out.append(f"Por qué esta: usted eligió el criterio MAYOR GANANCIA; «{ref['nombre']}» tiene la mayor ganancia media "
                   f"esperada al cierre del Reto ({ganancia_esperada(ref) or 0:+.1%}), con escenario adverso "
                   f"{er.get('adverso_p10', 0):+.1%}: más ganancia posible a cambio de más riesgo. No es una promesa.")
    elif plusvalia:
        er = ref.get("escenarios") or {}
        out.append(f"Por qué esta: usted eligió el criterio MAYOR PLUSVALÍA ESPERADA al cierre del Reto; «{ref['nombre']}» espera "
                   f"{er.get('central_p50', 0):+.1%}, pero su escenario adverso es {er.get('adverso_p10', 0):+.1%}: busca más "
                   "ganancia a cambio de más riesgo. No es una promesa.")
    else:
        out.append(f"Por qué esta: el plan usa la propuesta vigente con MAYOR PUNTUACIÓN («{ref['nombre']}», "
                   f"{ref['puntuacion']['total']:.1f}), que pondera rendimiento ajustado, riesgo, diversificación, liquidez, "
                   "costos y calidad de datos; no maximiza solo la ganancia.")
    esp = [x for x in vig if (x.get("escenarios") or {}).get("central_p50") is not None]
    if esp and not plusvalia:
        mayor = max(esp, key=lambda x: x["escenarios"]["central_p50"])
        if mayor.get("clave") != ref.get("clave"):
            em, er = mayor["escenarios"], ref.get("escenarios") or {}
            out.append(f"🚀 Mayor rendimiento esperado: {_linea_propuesta(mayor)}.")
            if er.get("adverso_p10") is not None:
                out.append(f"   Diferencia: espera {em['central_p50'] - er.get('central_p50', 0):+.1%} más, pero su escenario adverso es "
                           f"{em['adverso_p10']:+.1%} frente a {er['adverso_p10']:+.1%} y su puntuación {mayor['puntuacion']['total']:.1f} "
                           f"frente a {ref['puntuacion']['total']:.1f}: más ganancia posible a cambio de más riesgo.")
    if ref.get("riesgos"):
        out.append(f"Riesgo principal: {ref['riesgos'][0]}")
    return out


def _plan_basico(p: dict, cartera: dict, ords: list[dict]) -> dict:
    """Plan mínimo cuando no se calculó el plan de acción: sin cuenta confirmada ni precio confiable, todo es pendiente."""
    conf = cartera.get("fuente") == "portal"
    acciones = []
    for o in ords:
        ok = conf and not o["sic"] and o["titulos"] and o["precio"]
        acciones.append({"clave": o["clave"], "accion_propuesta": o["accion"], "decision": o["accion"] if ok else "pendiente",
                         "cantidad": o["titulos"] if ok else None, "precio_limite": o["precio"] if ok else None,
                         "monto": o["monto"], "peso_actual": None, "peso_objetivo": None, "precio": {},
                         "falta": [] if ok else (["Saldo confirmado del portal"] if not conf else ["Cotización confiable de la serie"])})
    return {"cuenta": {"confirmada": conf}, "acciones": acciones, "reglas": None}


def bloque_acciones(plan: dict, max_lineas: int = 8) -> list[str]:
    acc = plan["acciones"]
    out = ["🧭 Acciones por prioridad:"]
    if not plan["cuenta"]["confirmada"]:
        out.append("⚠️ Cuenta NO confirmada: todo queda como «decisión pendiente» hasta que pegues tu portafolio en la terminal "
                   "(«Mi portafolio Actinver»). Los montos son orientativos.")
    ejec = [a for a in acc if a["decision"] in ("comprar", "vender")]
    for a in ejec[:max_lineas]:
        icono = "🔴 Vender" if a["decision"] == "vender" else "🟢 Comprar"
        pesos = (f" · peso {a['peso_actual']:.0%}→{a['peso_objetivo']:.0%}" if a.get("peso_objetivo") is not None
                 and a.get("peso_actual") is not None else "")
        pr = a.get("precio") or {}
        fuente = f" · precio {pr.get('fuente')} {pr.get('fecha') or ''}".rstrip() if pr.get("fuente") else ""
        out.append(f"{icono} {a['clave']}: {a['cantidad']:,} títulos, límite ${a['precio_limite']:,.2f} ≈ ${a['monto']:,.0f}"
                   f"{pesos}{fuente}")
    if len(ejec) > max_lineas:
        out.append(f"… y {len(ejec) - max_lineas} más (/detalle).")
    pend = [a for a in acc if a["decision"] == "pendiente"]
    if pend:
        faltas = sorted({(a.get("falta") or ["dato"])[0].split(":")[0].split("(")[0].strip() for a in pend})
        out.append(f"⏳ Decisión pendiente ({len(pend)}): "
                   + ", ".join(f"{a['clave']} ({a['accion_propuesta']} ≈${a['monto']:,.0f})" for a in pend[:10])
                   + (" …" if len(pend) > 10 else "") + f". Falta: {'; '.join(faltas)[:220]}.")
    mant = [a for a in acc if a["decision"] == "mantener"]
    if mant:
        out.append(f"⏸ Mantener ({len(mant)}): " + ", ".join(a["clave"] for a in mant[:12]) + (" …" if len(mant) > 12 else ""))
    if not acc:
        out.append("✅ Sin órdenes sugeridas: la cartera ya está dentro de la banda de rebalanceo.")
    compras = [a for a in ejec if a["decision"] == "comprar"]
    ventas = [a for a in ejec if a["decision"] == "vender"]
    out.append(f"Resumen: {len(compras)} compra(s) ≈ ${sum(a['monto'] for a in compras):,.0f} · {len(ventas)} venta(s) ≈ "
               f"${sum(a['monto'] for a in ventas):,.0f} · {len(mant)} mantener · {len(pend)} pendiente(s).")
    return out


def enlace_privado() -> str | None:
    """Dirección de la red privada Tailscale (tailnet only), si está configurada. Nunca un enlace público."""
    hosts = [h.strip() for h in os.environ.get("TERMINAL_HOSTS_REMOTOS", "").split(",") if h.strip().endswith(".ts.net")]
    return f"https://{hosts[0]}/" if hosts else None


def construir(p: dict, cartera: dict, anterior: list[dict] | None, ahora_local: pd.Timestamp,
              sesion: date | None = None, plan: dict | None = None, props: dict | None = None) -> tuple[str, str, list[dict]]:
    """Mensaje del plan del día. Las órdenes ejecutables salen del plan de acción (cuenta confirmada + precio confiable);
    sin ellas, «decisión pendiente». El detalle completo va en /detalle y /propuestas para no alargar el mensaje."""
    ords = ordenes(p, cartera)
    plan = plan or _plan_basico(p, cartera, ords)
    confirmada = plan["cuenta"]["confirmada"]
    etapa = reto.etapa_operativa(ahora_local.to_pydatetime()) if reto.activo() else None
    s = pd.Timestamp(sesion) if sesion else ahora_local
    cab = (f"☀️ Plan del día — {DIAS[s.weekday()]} {s:%d-%m-%Y}" if s.date() == ahora_local.date()
           else f"🌙 Plan para la sesión del {DIAS[s.weekday()]} {s:%d-%m-%Y} (próxima sesión de la BMV)")
    if etapa:
        cab += f" · Reto: {'práctica' if etapa == 'practica' else etapa}, {reto.sesiones_restantes(ahora_local.to_pydatetime())} sesiones restantes"
    if confirmada and cartera.get("captura"):
        k = cartera["captura"]
        cuenta = (f"Cuenta: ✅ confirmada (portal {pd.Timestamp(k['hora_portal']).tz_convert(ZONA):%d-%m %H:%M}): valuación "
                  f"${(k.get('valor_portafolio') or 0):,.0f}, poder de compra ${(k.get('efectivo') or 0):,.0f}.")
    else:
        cuenta = "Cuenta: ⚠️ NO confirmada (registro local de la terminal, no es tu saldo del portal)."
    lineas = [cab, "", cuenta]
    r = plan.get("reglas")
    if r and r.get("activo"):
        lineas.append(f"Reglas verificadas (bases {r['consultado']}): ≥{r['min_emisoras']} emisoras · ≤{float(r['max_peso_emisora']):.0%} "
                      f"por emisora · comisión {r['comision']:.3%} con IVA · catálogo del simulador {r['catalogo']} instrumentos.")
        lineas += [f"⚠️ {x}" for x in r.get("errores", []) + r.get("avisos", [])]
    lineas += ["", horario_del_dia(s.date()), "", *bloque_propuestas(props, p), "", *bloque_acciones(plan), "",
               "Cambios frente al plan anterior:"]
    lineas += [f"• {c}" for c in cambios_vs_anterior(ords, anterior, con_titulos=confirmada)]
    enlace = enlace_privado()
    lineas += ["", "Detalle: /detalle (cada instrumento: cantidad, precio, fuente, motivo e invalidación) · /propuestas "
                   "(puntuación y desglose)" + (f" · terminal: {enlace} (solo tu red privada Tailscale)" if enlace else "") + ".",
               "Solo informativo: verifica cada precio en el portal y captura a mano. El SIC es referencia (origen × tipo de "
               "cambio), no cotización ejecutable."]
    return cab, "\n".join(lineas), ords


def plan_de_accion(con: sqlite3.Connection, ajustes, p: dict, cartera: dict) -> dict | None:
    """Plan de acción para el mensaje; si falla, el mensaje sale con el plan básico (todo pendiente sin cuenta confirmada)."""
    try:
        from . import plan_accion
        return plan_accion.calcular(con, ajustes, propuesta=p, cartera=cartera)
    except Exception:  # noqa: BLE001 - el plan del día nunca deja de enviarse por esto
        log.exception("plan de acción")
        return None


def _estado(con: sqlite3.Connection) -> dict:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='resumen_matutino'").fetchone()
    return json.loads(f["valor"]) if f else {}


REINTENTO_MIN = 10
MAX_INTENTOS = 12
ESPERA_RECALCULO_MIN = 60
MAX_CORRECCIONES = 2  # reenvíos «plan corregido» por sesión, solo antes de la apertura


def ultima_propuesta_id(con: sqlite3.Connection) -> int:
    return int(con.execute("SELECT COALESCE(MAX(id), 0) FROM propuestas").fetchone()[0])


def _firma(ords: list[dict] | None) -> set:
    return {(o["id"], o["accion"]) for o in ords or []}


def puede_corregir(estado: dict, ahora: datetime) -> bool:
    """Tras un plan entregado, un recálculo posterior puede cambiarlo: se admite un reenvío corregido mientras la
    sesión objetivo no haya abierto y no se agoten las correcciones."""
    obj = sesion_objetivo(ahora)
    if estado.get("fecha") != obj.isoformat() or not entregado(estado):
        return False
    if int(estado.get("correcciones", 0)) >= MAX_CORRECCIONES:
        return False
    return pd.Timestamp(ahora) < apertura(obj)


def apertura(sesion: date) -> pd.Timestamp:
    """Apertura según el horario publicado en las bases del Reto (07:30 hasta el 2-nov-2026, 08:30 después)."""
    return vigencia.apertura_sesion("XMEX", sesion)


def _guardar(con: sqlite3.Connection, estado: dict) -> None:
    with db.transaccion(con):
        con.execute("INSERT INTO ajustes_usuario VALUES ('resumen_matutino', ?, ?) ON CONFLICT(clave) DO UPDATE SET "
                    "valor=excluded.valor, actualizado_en=excluded.actualizado_en", (json.dumps(estado), db.ahora()))


def entregado(estado: dict) -> bool:
    """Solo cuenta como enviado si Telegram lo confirmó (o si Telegram no está configurado y otro canal sí)."""
    r = estado.get("resultado") or {}
    return r.get("telegram") == "enviada" or (r.get("telegram") in (None, "no_configurado") and "enviada" in r.values())


def sesion_objetivo(ahora: datetime) -> date:
    """Sesión para la que se arma el plan: la de hoy si aún no cierra; si ya cerró (o no es día hábil), la siguiente."""
    cal = vigencia.calendario("XMEX")
    hoy = pd.Timestamp(pd.Timestamp(ahora).tz_convert(ZONA).date())
    if cal.is_session(hoy) and pd.Timestamp(ahora) < vigencia.cierre_sesion("XMEX", hoy):
        return hoy.date()
    return cal.date_to_session(hoy, direction="next").date() if not cal.is_session(hoy) else cal.next_session(hoy).date()


def toca(ajustes, ahora: datetime, estado: dict, datos_hasta: str | None = None) -> bool:
    """Lo antes posible: en cuanto la propuesta usa los cierres de la última sesión cerrada (normalmente la noche
    anterior). Respaldo: a la hora configurada del día de la sesión, aunque falten datos (el plan lo indica)."""
    cfg = ajustes["alertas"]
    if not cfg.get("resumen_matutino", True):
        return False
    obj = sesion_objetivo(ahora)
    if estado.get("fecha") == obj.isoformat():
        if entregado(estado) or int(estado.get("intentos", 1)) >= MAX_INTENTOS:
            return False
        ultimo = pd.Timestamp(estado.get("enviado_en") or ahora)
        if pd.Timestamp(ahora) - ultimo < pd.Timedelta(minutes=REINTENTO_MIN):
            return False  # reintento tras un fallo de canal, cada 10 minutos
    if datos_hasta and date.fromisoformat(datos_hasta) >= vigencia.ultima_sesion_cerrada("XMEX", ahora):
        return True  # envío anticipado: los cierres de la última sesión ya están en la propuesta
    local = pd.Timestamp(ahora).tz_convert(ZONA)
    h, m = (int(x) for x in str(cfg.get("resumen_matutino_hora", "07:00")).split(":"))
    return obj == local.date() and (local.hour, local.minute) >= (h, m)


def enviar_si_toca(con: sqlite3.Connection, ajustes, cartera: dict, propuestas: dict,
                   ahora: datetime | None = None) -> dict | None:
    """Envía el plan del día una vez por sesión hábil, a partir de la hora configurada."""
    ahora = ahora or datetime.now(UTC)
    estado = _estado(con)
    ref = propuesta_referencia(propuestas)
    correccion = False
    if not toca(ajustes, ahora, estado, (ref or {}).get("datos_hasta")):
        if not (ref and puede_corregir(estado, ahora)) or any(p and p.get("recalcular") for p in propuestas.values()):
            return None
        nuevas = ordenes(ref, cartera)
        if _firma(nuevas) == _firma(estado.get("ordenes")) and ref["clave"] == estado.get("propuesta"):
            if estado.get("propuestas_max_id") != ultima_propuesta_id(con):  # recalculada sin cambios: no se reenvía
                _guardar(con, {**estado, "propuestas_max_id": ultima_propuesta_id(con)})
            return None
        correccion = True
    local = pd.Timestamp(ahora).tz_convert(ZONA)
    obj = sesion_objetivo(ahora)
    h, m = (int(x) for x in str(ajustes["alertas"].get("resumen_matutino_hora", "07:00")).split(":"))
    minutos = (local.hour - h) * 60 + (local.minute - m) if obj == local.date() else 0
    if any(p and p.get("recalcular") for p in propuestas.values()) and minutos < ESPERA_RECALCULO_MIN:
        return None  # las propuestas se están recalculando: se espera para no enviar un plan viejo
    p = ref
    if p is None:
        titulo, texto, ords = (f"☀️ Plan del día — {local:%d-%m-%Y}",
                               "No hay una propuesta vigente (datos no actualizados o propuestas suspendidas). Revise la "
                               "pestaña Datos de la terminal; no se sugieren órdenes hoy.", [])
    else:
        plan = plan_de_accion(con, ajustes, p, cartera)
        titulo, texto, ords = construir(p, cartera, estado.get("ordenes"), local, obj, plan=plan, props=propuestas)
        if str(ajustes["alertas"].get("formato_plan", "sencillo")) == "sencillo" and plan:
            from . import mensaje_simple
            texto = mensaje_simple.texto(con, ajustes, propuesta=p, cartera=cartera, plan=plan, ahora=ahora, sesion=obj)
            if estado.get("ordenes") is not None:  # qué cambió frente al último plan que sí llegó
                texto += "\n\nQué cambió frente al mensaje anterior:\n" + "\n".join(
                    f"• {c}" for c in cambios_vs_anterior(ords, estado.get("ordenes"), con_titulos=plan["cuenta"]["confirmada"]))
    if correccion:
        titulo = "🔁 PLAN CORREGIDO — " + titulo
        texto = ("🔁 PLAN CORREGIDO: la terminal recalculó la propuesta después del envío anterior y las órdenes cambiaron. "
                 "Este mensaje REEMPLAZA al anterior.\n\n" + texto)
    cfg = {**ajustes["alertas"], "notificar_escritorio": False, "notificar_telegram": True}
    res = notificador.enviar(titulo, texto, cfg, detalle=texto)
    ok = entregado({"resultado": res})
    if correccion and not ok:
        return None  # la corrección no llegó: se conserva el estado del plan entregado y se reintenta en otra revisión
    nuevo = {"fecha": obj.isoformat(), "enviado_en": ahora.isoformat(timespec="seconds"), "resultado": res,
             "intentos": (1 if correccion else int(estado.get("intentos", 1)) + 1) if estado.get("fecha") == obj.isoformat() else 1,
             "correcciones": int(estado.get("correcciones", 0)) + (1 if correccion else 0) if estado.get("fecha") == obj.isoformat() else 0,
             "propuestas_max_id": ultima_propuesta_id(con),
             "propuesta": p["clave"] if p else None,
             # base para comparar el próximo plan: el último que SÍ llegó
             "ordenes": [{k: o[k] for k in ("id", "clave", "accion", "titulos")} for o in ords] if (p and ok)
             else estado.get("ordenes")}
    _guardar(con, nuevo)
    log.info("plan del día %s: %s", "corregido" if correccion else "enviado", res)
    return {**nuevo, "texto": texto}


def enviar_muestra(con: sqlite3.Connection, ajustes, cartera: dict, propuestas: dict) -> dict:
    """Envía ahora el plan con los datos actuales, marcado como MUESTRA; no cuenta como el envío del día."""
    ahora = datetime.now(UTC)
    local = pd.Timestamp(ahora).tz_convert(ZONA)
    p = propuesta_referencia(propuestas)
    if p is None:
        return {"resultado": None, "texto": "No hay propuesta vigente para armar el plan."}
    titulo, texto, _ = construir(p, cartera, _estado(con).get("ordenes"), local, sesion_objetivo(ahora),
                                 plan=plan_de_accion(con, ajustes, p, cartera), props=propuestas)
    titulo, texto = "MUESTRA — " + titulo, "MUESTRA (envío de prueba)\n" + texto
    cfg = {**ajustes["alertas"], "notificar_escritorio": False, "notificar_telegram": True}
    return {"resultado": notificador.enviar(titulo, texto, cfg, detalle=texto), "texto": texto}
