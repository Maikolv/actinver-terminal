"""Plan de acción: para cada instrumento, comprar, vender, mantener o «decisión pendiente», listo para revisar y capturar
a mano en el simulador del Reto.

Reglas de honestidad:
- Sin saldo confirmado del portal (captura vigente en «Mi portafolio Actinver»), TODO queda en «decisión pendiente»:
  la terminal no conoce sus títulos ni su efectivo reales y no genera órdenes aparentemente ejecutables.
- Sin cotización confiable de la serie exacta (todas las del SIC y las BMV con cierre atrasado), la decisión queda
  pendiente; a lo sumo se da la referencia (bolsa de origen × tipo de cambio) para comparar con el portal.
- Las compras se financian con el efectivo confirmado (poder de compra), en orden de prioridad; lo «por liquidar» no
  se usa para comprar.
- Las reglas del Reto (fechas, comisión, ≥ 5 emisoras, ≤ 50 % por emisora, catálogo del simulador) se comprueban
  antes de calcular; si no se cumplen, se dice.
Nada de esto envía órdenes ni marca boletas como ejecutadas.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import UTC, date, datetime

import pandas as pd

from . import boleta, mercado, reto, servicios
from .config import Ajustes

ZONA = "America/Mexico_City"
ORDEN = {"vender": 0, "comprar": 1, "mantener": 2}
FALTA_SALDO = ("Saldo confirmado del portal: capture su cuenta en «Mi portafolio Actinver» (posiciones, poder de compra, "
               "valuación total y hora del portal).")


def verificar_reglas(con: sqlite3.Connection, p: dict | None, ahora: datetime) -> dict:
    """Comprobación previa al plan: configuración vigente de las bases y cumplimiento de la propuesta."""
    if not reto.activo():
        return {"activo": False, "avisos": ["El Reto no está activo en la configuración: se usan reglas generales."], "errores": []}
    c = reto.config()
    reglas = c.get("reglas") or {}
    avisos, errores = [], []
    consultado = str(c.get("consultado") or "")
    try:
        dias = (ahora.date() - date.fromisoformat(consultado[:10])).days
        if dias > 7:
            avisos.append(f"Las bases se verificaron hace {dias} días ({consultado}); vuelva a revisarlas.")
    except ValueError:
        avisos.append("No hay fecha de consulta de las bases.")
    catalogo = {r[0] for r in con.execute("SELECT id FROM universo_simulador")}
    if not catalogo:
        errores.append("No hay catálogo del simulador importado: no se puede verificar qué instrumentos se pueden operar.")
    fuera, max_w, n = [], 0.0, 0
    if p:
        pesos = {a["id"]: a["peso"] for a in p.get("pesos") or [] if a.get("peso", 0) > 0}
        fuera = sorted(i for i in pesos if catalogo and i not in catalogo)
        max_w, n = (max(pesos.values()) if pesos else 0.0), len(pesos)
        if fuera:
            errores.append(f"La propuesta usa instrumentos fuera del catálogo del simulador: {', '.join(fuera)}.")
        if max_w > float(reglas.get("max_peso_emisora") or 0.5) + 1e-9:
            errores.append(f"La propuesta pone {max_w:.0%} en una emisora (máximo del Reto {float(reglas.get('max_peso_emisora') or 0.5):.0%}).")
        if n < int(reglas.get("min_emisoras") or 5):
            avisos.append(f"La propuesta tiene {n} emisoras; el Reto exige operar al menos {reglas.get('min_emisoras')}.")
    f = c.get("fechas") or {}
    return {"activo": True, "consultado": consultado, "fuente": c.get("fuente"), "etapa": reto.etapa_operativa(ahora),
            "competencia": f"{str(f.get('competencia_inicio', ''))[:10]} a {str(f.get('competencia_fin', ''))[:16].replace('T', ' ')}",
            "comision": reto.costo_operacion(), "min_emisoras": reglas.get("min_emisoras"),
            "max_peso_emisora": reglas.get("max_peso_emisora"), "catalogo": len(catalogo), "emisoras_propuesta": n,
            "mayor_peso_propuesta": round(max_w, 4), "avisos": avisos, "errores": errores}


def _precio(q: dict | None, iid: str) -> dict:
    q = q or {}
    return {"fuente": q.get("proveedor"), "fecha": q.get("fecha"), "estado": q.get("estado"),
            "precio_mxn": q.get("precio_mxn"), "es_referencia": iid.startswith("SIC:"),
            "nota": ("Referencia: bolsa de origen × tipo de cambio; no es la cotización del SIC." if iid.startswith("SIC:")
                     else "Cierre BMV de la terminal; confirme el precio en el portal.")}


def calcular(con: sqlite3.Connection, ajustes: Ajustes, ahora: datetime | None = None, propuesta: dict | None = None,
             cartera: dict | None = None) -> dict:
    """Plan de acción con la propuesta de referencia (la del plan del día) y la cartera confirmada."""
    from . import resumen
    ahora = ahora or datetime.now(UTC)
    if propuesta is None:
        perfil = servicios.perfil_actual(con, ajustes)
        propuesta = resumen.propuesta_referencia(servicios.propuestas_guardadas(con, ajustes, perfil))
    cart = cartera if cartera is not None else servicios.cartera_actual(con, ajustes)
    p = propuesta
    confirmada = cart.get("fuente") == "portal"
    reglas = verificar_reglas(con, p, ahora)
    faltan = ([] if confirmada else [FALTA_SALDO]) + reglas["errores"]
    if not p:
        faltan.append("Propuesta vigente: se está recalculando o faltan datos (vea «¿En qué puedo confiar hoy?»).")
    banda = float(ajustes["optimizacion"].get("banda_rebalanceo_pp", 2.0))
    ins = mercado.instrumentos(con)
    filas = list((p.get("cambios") or {}).get("filas") or []) if p else []
    vistos = {f["id"] for f in filas}
    actuales = {x["instrumento_id"]: x for x in cart.get("posiciones", []) if (x.get("cantidad") or 0) > 0}
    objetivo = {a["id"]: a.get("peso", 0.0) for a in (p.get("pesos") or [])} if p else {}
    for iid, x in actuales.items():  # posición real que la propuesta no menciona: no se ignora
        if iid not in vistos:
            filas.append({"id": iid, "clave_operable": x.get("clave_operable"), "peso_actual": x.get("peso") or 0,
                          "peso_objetivo": objetivo.get(iid, 0.0), "delta_pp": 0.0, "monto_mxn": 0.0, "accion": "mantener",
                          "nota": "Posición de su cuenta que la propuesta no evalúa: revise antes de operar."})
    mantener_mejor = resumen.mantener_es_mejor(p, (p.get("perfil") or {}).get("criterio_plan", "puntuacion"),
                                                float(ajustes["optimizacion"].get("margen_mejora_mantener", resumen.MARGEN_MANTENER))) if p else None
    if mantener_mejor and confirmada:  # cambiar no mejora la ganancia esperada: se conserva lo que hay, sin operar
        nota = (f"La propuesta no supera a mantener su cartera ({mantener_mejor['metrica']} {mantener_mejor['propuesta']:+.1%} "
                f"frente a {mantener_mejor['mantener']:+.1%}, mismo método, después de comisiones): no se sugiere operar.")
        filas = [{**f, "accion": "mantener", "monto_mxn": 0.0, "delta_pp": 0.0, "nota": nota}
                 for f in filas if f["id"] in actuales]
        objetivo = {}
    ids = sorted({f["id"] for f in filas})
    cot = mercado.cotizaciones(con, ajustes, ids) if ids else {}
    acciones = []
    for f in filas:
        iid = f["id"]
        accion = f.get("accion", "mantener")
        tenencia = (actuales.get(iid) or {}).get("cantidad") or 0
        if accion == "mantener" and not tenencia and not objetivo.get(iid):
            continue
        fila = {"instrumento_id": iid, "clave": f.get("clave_operable") or (ins.get(iid) or {}).get("clave_operable") or iid,
                "mercado": "SIC" if iid.startswith("SIC:") else "BMV" if iid.startswith("BMV:") else "otro",
                "accion_propuesta": accion, "decision": accion, "cantidad": None, "precio_limite": None,
                "monto": round(abs(float(f.get("monto_mxn") or 0)), 2), "titulos_actuales": tenencia,
                "peso_actual": round(float((actuales.get(iid) or {}).get("peso") or f.get("peso_actual") or 0), 4),
                "peso_objetivo": round(float(f.get("peso_objetivo", objetivo.get(iid, 0.0)) or 0), 4),
                "delta_pp": float(f.get("delta_pp") or 0), "motivo": f.get("nota") or "", "precio": _precio(cot.get(iid), iid),
                "invalidacion": "", "falta": [], "referencia": None, "costo": None}
        if accion == "mantener":
            fila["motivo"] = fila["motivo"] or f"Peso dentro de la banda de ±{banda:g} pp frente al objetivo: no conviene pagar comisión."
            fila["invalidacion"] = (f"El peso se aleja más de {banda:g} pp del objetivo, cambia la propuesta de referencia "
                                    "o su cuenta del portal.")
            if not confirmada:
                fila["decision"], fila["falta"] = "pendiente", [FALTA_SALDO]
        else:
            if not fila["motivo"]:
                fila["motivo"] = (f"{'Subir' if accion == 'comprar' else 'Bajar'} el peso de {fila['peso_actual']:.1%} a "
                                  f"{fila['peso_objetivo']:.1%} ({fila['delta_pp']:+.1f} pp) según «{p['nombre']}».")
            if not confirmada:
                fila["decision"], fila["falta"] = "pendiente", [FALTA_SALDO]
                fila["invalidacion"] = "Cambian su cuenta del portal o la propuesta de referencia."
            else:
                b = boleta.construir(con, ajustes, {**f, "nota": fila["motivo"]}, cart, ahora=ahora)
                fila["invalidacion"] = "; ".join(b.get("invalidacion") or [])
                fila["referencia"] = b.get("referencia_condicional")
                if fila["referencia"] and accion == "vender" and not fila["peso_objetivo"] and tenencia:
                    fila["referencia"] = {**fila["referencia"], "titulos_aprox": int(tenencia),
                                          "nota": fila["referencia"]["nota"] + " Objetivo 0 %: vender todos sus títulos."}
                adv = [a for a in (b.get("efecto") or {}).get("advertencias_reto") or [] if a.get("nivel") == "critica"]
                if b.get("lado") and b.get("cantidad") and not adv:
                    fila.update(decision=b["lado"] if b["lado"] in ("comprar", "vender") else
                                ("comprar" if b["lado"] == "compra" else "vender"),
                                cantidad=int(b["cantidad"]), precio_limite=b.get("precio_limite"),
                                monto=round(float(b.get("importe") or 0), 2), costo=(b.get("costos") or {}).get("total"))
                    fp = b.get("fuente_precio") or {}
                    fila["precio"].update(fuente=fp.get("proveedor") or fila["precio"]["fuente"],
                                          hora=fp.get("hora_evento"), latencia=fp.get("estado_latencia"))
                else:
                    fila["decision"] = "pendiente"
                    fila["falta"] = ([a.get("mensaje") or str(a) for a in adv]
                                     + list(b.get("datos_faltantes") or []) + list(b.get("razones") or [])[:1])
        acciones.append(fila)
    acciones.sort(key=lambda a: (ORDEN.get(a["accion_propuesta"], 3), -abs(a["delta_pp"])))
    # Efectivo confirmado para las compras, en orden de prioridad (las ventas no se suponen liquidadas)
    efectivo = float(cart.get("efectivo") or 0) if confirmada else 0.0
    costo_op = float(reto.costo_operacion() or 0)
    for a in acciones:
        if a["decision"] != "comprar":
            continue
        necesario = a["monto"] * (1 + costo_op)
        if necesario > efectivo + 0.01:
            n = math.floor(efectivo / (a["precio_limite"] * (1 + costo_op))) if a["precio_limite"] else 0
            if n <= 0:
                a.update(decision="pendiente", cantidad=None, falta=[
                    f"Efectivo confirmado insuficiente tras las compras de mayor prioridad (quedan ${efectivo:,.2f})."])
                continue
            a.update(cantidad=n, monto=round(n * a["precio_limite"], 2),
                     motivo=a["motivo"] + f" Cantidad reducida al efectivo confirmado disponible (${efectivo:,.2f}).")
        efectivo -= a["monto"] * (1 + costo_op)
    for i, a in enumerate(acciones, 1):
        a["prioridad"] = i
    cuenta = {"confirmada": confirmada, "fuente": "portal" if confirmada else "registro local (no confirmado)",
              "hora_portal": (cart.get("captura") or {}).get("hora_portal"), "efectivo": cart.get("efectivo"),
              "por_liquidar": cart.get("por_liquidar"), "valor_total": cart.get("valor_total"),
              "efectivo_tras_compras": round(efectivo, 2) if confirmada else None}
    cuenta_txt = None
    if cuenta["hora_portal"]:
        cuenta_txt = pd.Timestamp(cuenta["hora_portal"]).tz_convert(ZONA).strftime("%d-%m-%Y %H:%M")
    return {
        "generado_en": ahora.isoformat(timespec="seconds"), "reglas": reglas, "cuenta": cuenta, "cuenta_hora_texto": cuenta_txt,
        "propuesta": ({"clave": p["clave"], "nombre": p["nombre"], "puntuacion": p["puntuacion"]["total"],
                       "datos_hasta": p.get("datos_hasta"),
                       "por_que": ("Mayor ganancia media esperada al cierre del Reto (criterio elegido en su perfil)."
                                   if (p.get("perfil") or {}).get("criterio_plan") == "ganancia"
                                   else "Mayor plusvalía esperada al cierre del Reto (criterio elegido en su perfil)."
                                   if (p.get("perfil") or {}).get("criterio_plan") == "plusvalia"
                                   else "Es la propuesta vigente con mayor puntuación (criterio del plan del día).")} if p else None),
        "acciones": acciones, "faltan": faltan, "mantener_mejor": mantener_mejor if confirmada else None,
        "resumen": {d: sum(1 for a in acciones if a["decision"] == d) for d in ("comprar", "vender", "mantener", "pendiente")}
        | {"monto_compras": round(sum(a["monto"] for a in acciones if a["decision"] == "comprar"), 2),
           "monto_ventas": round(sum(a["monto"] for a in acciones if a["decision"] == "vender"), 2)},
        "aviso": ("Plan para revisión humana: la terminal no envía órdenes ni marca boletas como ejecutadas. Verifique cada "
                  "precio en el portal antes de capturar; el SIC se muestra como referencia, no como cotización ejecutable."),
    }
