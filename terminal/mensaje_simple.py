"""Plan del día en lenguaje sencillo para Telegram: solo qué hacer, en qué orden y con qué tope de precio.

Pensado para quien no conoce la jerga (peso, banda, SIC, p10…). Toma en cuenta las mismas variables que el plan
detallado: cuenta confirmada y su antigüedad, efectivo, ventas antes que compras, precio límite, precios retrasados o
de referencia, reglas del Reto (≥ 5 emisoras, ≤ 50 % por emisora), eventos macro de alto impacto y el rango estimado
al cierre del Reto. El detalle técnico sigue en /detalle, /propuestas y /boletas detalle.

Nada de esto es asesoría ni envía órdenes: el participante captura cada orden a mano en el simulador.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd

ZONA = "America/Mexico_City"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
# Títulos del calendario (ForexFactory) traducidos a palabras de uso diario; el resto sale como «dato económico».
MACRO = [("FOMC Meeting Minutes", "minutas de la Reserva Federal de EE. UU."),
         ("Federal Funds Rate", "decisión de tasa de interés de la Reserva Federal"),
         ("FOMC", "anuncio de la Reserva Federal"), ("Powell", "discurso del presidente de la Reserva Federal"),
         ("Core CPI", "inflación de EE. UU."), ("CPI", "inflación"), ("PPI", "precios al productor de EE. UU."),
         ("Non-Farm", "empleo de EE. UU."), ("Unemployment", "desempleo"), ("JOLTS", "vacantes de empleo de EE. UU."),
         ("GDP", "crecimiento de la economía (PIB)"), ("Retail Sales", "ventas en tiendas"),
         ("ISM", "actividad de las empresas de EE. UU."), ("PCE", "inflación que mira la Reserva Federal"),
         ("Overnight Rate", "decisión de tasa de interés de Banxico"), ("Banxico", "anuncio de Banxico")]


def _dinero(x: float) -> str:
    return f"${x:,.0f}" if abs(x) >= 1000 else f"${x:,.2f}"


def _nombre(clave: str) -> str:
    return clave.replace(" *", "")


def traducir_evento(titulo: str, pais: str) -> str:
    for k, v in MACRO:
        if k.lower() in (titulo or "").lower():
            return v
    return f"dato económico de {'EE. UU.' if pais == 'USD' else 'México' if pais == 'MXN' else pais} ({titulo})"


def eventos_macro(con: sqlite3.Connection, ahora: datetime, horas: int = 48) -> list[dict]:
    """Eventos de alto impacto de EE. UU. y México en las próximas `horas` (calendario ForexFactory ya descargado)."""
    fin = ahora + timedelta(hours=horas)
    out = []
    for e in con.execute("SELECT fecha, pais, titulo FROM eventos_macro WHERE impacto='High' AND pais IN ('USD','MXN')"):
        try:
            t = pd.Timestamp(e["fecha"])
            t = t.tz_localize("UTC") if t.tzinfo is None else t
        except (ValueError, TypeError):
            continue
        if pd.Timestamp(ahora) <= t <= pd.Timestamp(fin):
            out.append({"fecha": t, "pais": e["pais"], "titulo": e["titulo"]})
    out.sort(key=lambda x: x["fecha"])
    vistos, unicos = set(), []
    for e in out:  # el calendario puede repetir el mismo evento en dos versiones
        k = (e["fecha"], traducir_evento(e["titulo"], e["pais"]))
        if k not in vistos:
            vistos.add(k)
            unicos.append(e)
    return unicos


def _cuando(t: pd.Timestamp, hoy: date) -> str:
    local = t.tz_convert(ZONA)
    dia = "hoy" if local.date() == hoy else "mañana" if local.date() == hoy + timedelta(days=1) else DIAS[local.weekday()]
    return f"{dia} a las {local:%H:%M}"


def _horario(sesion: date) -> str:
    try:
        from . import vigencia
        abre = vigencia.apertura_sesion("XMEX", sesion).tz_convert(ZONA)
        cierra = vigencia.cierre_sesion("XMEX", sesion).tz_convert(ZONA)
        return f"Captura tus órdenes entre las {abre:%H:%M} y las {cierra:%H:%M} (hora del centro de México)."
    except Exception:  # noqa: BLE001 - sin calendario el mensaje sigue saliendo
        return "Captura tus órdenes con la bolsa abierta."


def construir(plan: dict | None, propuesta: dict | None, eventos: list[dict], ahora_local: pd.Timestamp,
              sesion: date | None = None, sesiones_restantes: int | None = None) -> str:
    """Texto del plan del día. `plan` es la salida de plan_accion.calcular; `propuesta`, la de referencia."""
    s = sesion or ahora_local.date()
    cab = f"📋 Qué hacer {'hoy' if s == ahora_local.date() else 'en la próxima sesión'}, {DIAS[s.weekday()]} {s:%d-%m}"
    if sesiones_restantes:
        cab += f" (quedan {sesiones_restantes} días de Reto)"
    L = [cab, ""]
    if not plan or not propuesta:
        L += ["⏳ Hoy NO cambies nada todavía: la terminal está recalculando con datos nuevos.",
              "Vuelve a escribir /plan en unos minutos."]
        return "\n".join(L)
    c = plan["cuenta"]
    if not c["confirmada"]:
        L += ["⚠️ Primero mándame una captura de tu portafolio del simulador (pantalla «TU INVERSIÓN»).",
              "Sin ella no sé cuánto dinero tienes y cualquier cantidad sería una adivinanza. No compres ni vendas aún."]
        return "\n".join(L)
    hora = pd.Timestamp(c["hora_portal"]).tz_convert(ZONA) if c.get("hora_portal") else None
    L.append(f"💰 Tu cuenta: {_dinero(c['valor_total'] or 0)} en total, {_dinero(c['efectivo'] or 0)} disponibles para comprar"
             + (f" (según tu captura del {hora:%d-%m %H:%M})." if hora is not None else "."))
    if hora is not None and (ahora_local - hora) > pd.Timedelta(days=3):
        L.append("⚠️ Esa captura es vieja: si compraste o vendiste después, mándame una nueva antes de seguir.")
    acc = plan["acciones"]
    ventas = [a for a in acc if a["decision"] == "vender"]
    compras = [a for a in acc if a["decision"] == "comprar"]
    cond = sorted([a for a in acc if a["decision"] == "pendiente" and a.get("referencia")],
                  key=lambda a: a["referencia"].get("lado_sugerido", "compra") != "venta")  # ventas primero
    espera = [a for a in acc if a["decision"] == "pendiente" and not a.get("referencia")]
    L.append("")
    mm = plan.get("mantener_mejor")
    if mm:
        L.append(f"✅ Hoy no cambies nada. Medidas igual, tu cartera actual espera {mm['mantener']:+.1%} al cierre del Reto "
                 f"y la propuesta {mm['propuesta']:+.1%}: cambiar no mejora la ganancia esperada y cuesta comisiones.")
        L.append(f"   Riesgo en un mal escenario (1 de cada 10): tu cartera {mm['adverso_mantener']:+.1%}, "
                 f"la propuesta {mm['adverso_propuesta']:+.1%}.")
    elif not (ventas or compras or cond):
        L.append("✅ Hoy no tienes que hacer nada: tu cartera ya está como el plan. No pagues comisiones sin necesidad.")
    n = 0
    if ventas:
        L.append("1️⃣ Primero VENDE (orden limitada):")
        for a in ventas:
            n += 1
            todo = " (todas las que tienes)" if a.get("titulos_actuales") and a["cantidad"] >= a["titulos_actuales"] else ""
            L.append(f"  {n}. {_nombre(a['clave'])}: vende {a['cantidad']:,} acciones{todo}, a no menos de "
                     f"${a['precio_limite']:,.2f} cada una (≈ {_dinero(a['monto'])}).")
    if compras:
        L.append(f"{'2️⃣ Después' if ventas else '1️⃣'} COMPRA con el dinero que ya tienes (orden limitada):")
        for a in compras:
            n += 1
            L.append(f"  {n}. {_nombre(a['clave'])}: compra {a['cantidad']:,} acciones, pagando como máximo "
                     f"${a['precio_limite']:,.2f} cada una (≈ {_dinero(a['monto'])}).")
    if cond:
        L.append("🟡 Revisa primero el precio en el portal (no tengo su precio exacto del simulador). "
                 "Si está fuera del rango, no la toques hoy:")
        for a in cond:
            r = a["referencia"]
            if r.get("lado_sugerido", "compra") == "compra":
                L.append(f"  • {_nombre(a['clave'])}: compra unas {r['titulos_aprox']:,} acciones si cuesta entre "
                         f"${r['precio_min']:,.2f} y ${r['precio_max']:,.2f}; precio límite ${r['precio_max']:,.2f}.")
            else:
                L.append(f"  • {_nombre(a['clave'])}: vende unas {r['titulos_aprox']:,} acciones si cuesta entre "
                         f"${r['precio_min']:,.2f} y ${r['precio_max']:,.2f}; precio límite ${r['precio_min']:,.2f}.")
    if cond:
        efectivo = float(c.get("efectivo_tras_compras") if c.get("efectivo_tras_compras") is not None else c.get("efectivo") or 0)
        compra_cond = sum(a["referencia"].get("monto_mxn") or a["referencia"]["titulos_aprox"] * a["referencia"]["precio_max"]
                          for a in cond if a["referencia"].get("lado_sugerido", "compra") == "compra")
        if any(a["referencia"].get("lado_sugerido") == "venta" for a in cond) and compra_cond > efectivo:
            L.append(f"  ➜ Haz primero las ventas: lo que te queda ({_dinero(efectivo)}) no alcanza para estas compras "
                     "sin ese dinero. Si el portal no te deja comprar todo, compra menos acciones.")
    if espera:
        L.append("⏸ No toques hoy (falta un dato para decidir): " + ", ".join(_nombre(a["clave"]) for a in espera[:8])
                 + (" …" if len(espera) > 8 else "") + ".")
    if ventas and not compras and any(a["decision"] == "pendiente" and a["accion_propuesta"] == "comprar" for a in acc):
        L.append("ℹ️ Las compras esperan al dinero de las ventas: cuando aparezca en «Poder de compra», escribe /plan.")
    L += (["", "📌 Antes de capturar:", "• " + _horario(s)] if (ventas or compras or cond) else ["", "📌 Para tener en cuenta:"])
    if ventas or compras or cond:
        retrasado = [a for a in ventas + compras + cond if (a.get("precio") or {}).get("estado") != "vigente"
                     or (a.get("precio") or {}).get("es_referencia")]
        L.append("• Compara cada precio con el del portal. Si se movió más de 1 %, escribe /plan para recalcular."
                 + (" Ojo: " + ", ".join(_nombre(a["clave"]) for a in retrasado[:5])
                    + " tienen precio aproximado." if retrasado else ""))
        L.append("• Si el portal no te deja (precio fuera del máximo o falta dinero), no lo fuerces: déjala para mañana.")
    r = plan.get("reglas") or {}
    if r.get("errores"):
        L += [f"• ⚠️ Regla del Reto: {x}" for x in r["errores"][:2]]
    elif r.get("activo"):
        L.append(f"• Reglas del Reto cumplidas: al menos {r.get('min_emisoras')} empresas distintas y ninguna con más de "
                 f"{float(r.get('max_peso_emisora') or 0.5):.0%} del dinero.")
    if eventos:
        e = eventos[0]
        extra = f" (y {len(eventos) - 1} más)" if len(eventos) > 1 else ""
        L.append(f"• 📰 {_cuando(e['fecha'], ahora_local.date()).capitalize()}: "
                 f"{traducir_evento(e['titulo'], e['pais']).rstrip('.')}{extra}. Puede mover mucho los precios; el plan no cambia por eso, pero no subas tu precio máximo.")
    esc = propuesta.get("escenarios") or {}
    if not mm and esc.get("central_p50") is not None and esc.get("adverso_p10") is not None:
        media = (esc["media_anual_usada"] * esc["horizonte_anios"] if esc.get("media_anual_usada") is not None
                 and esc.get("horizonte_anios") is not None else None)
        L += ["", "📈 Qué esperar al cierre del Reto (estimación, no promesa): "
                  + (f"en promedio {media:+.1%}; " if media is not None else "")
                  + f"lo más común {esc['central_p50']:+.1%}; en un mal escenario (1 de cada 10) {esc['adverso_p10']:+.1%}."]
    L += ["", "Tú capturas cada orden a mano; la terminal no compra ni vende nada. Más detalle: /detalle"]
    return "\n".join(L)


def texto(con: sqlite3.Connection, ajustes, propuesta: dict | None = None, cartera: dict | None = None,
          plan: dict | None = None, ahora: datetime | None = None, sesion: date | None = None) -> str:
    """Arma el mensaje sencillo con la propuesta de referencia y la cuenta actuales."""
    from datetime import UTC

    from . import plan_accion, reto, resumen, servicios
    ahora = ahora or datetime.now(UTC)
    if propuesta is None:
        propuesta = resumen.propuesta_referencia(servicios.propuestas_guardadas(con, ajustes, servicios.perfil_actual(con, ajustes)))
    if propuesta is not None and plan is None:
        plan = plan_accion.calcular(con, ajustes, ahora=ahora, propuesta=propuesta, cartera=cartera)
    local = pd.Timestamp(ahora).tz_convert(ZONA)
    try:
        quedan = reto.sesiones_restantes(local.to_pydatetime()) if reto.activo() else None
    except Exception:  # noqa: BLE001
        quedan = None
    return construir(plan, propuesta, eventos_macro(con, ahora), local, sesion or resumen.sesion_objetivo(ahora), quedan)
