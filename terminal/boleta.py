"""Boleta de decisión: todo lo que el participante necesita para CAPTURAR A MANO una orden en el simulador.

Una boleta NO es una orden. La terminal no inicia sesión ni envía nada (reglamento §17). Ciclo de vida:
  vigente → (recalcular antes de presentar) → invalidada | caducada | descartada | marcada_ejecutada
Solo «marcar ejecutada» con los datos de la CONFIRMACIÓN (folio, cantidad y precio reales) registra la operación que
cambia posiciones y efectivo.

Contenido de cada boleta: emisora y serie exactas, tipo (mantener / investigar / considerar compra / considerar venta /
considerar rebalanceo), cantidad entera, precio límite propuesto, costo (comisión + IVA) con escenarios de deslizamiento
y de falta de ejecución, efecto en efectivo y concentración, valor esperado estimado con intervalo y pérdida plausible,
liquidez, alternativa (mantener efectivo), impacto en las reglas del Reto, condiciones de invalidación, caducidad,
datos que faltan y razones.

Las estimaciones de rendimiento son HISTÓRICAS (media contraída a la mitad y volatilidad de 250 sesiones): el modelo
predictivo no ha demostrado ventaja fuera de muestra (docs/model-card.md), por lo que no se usa para las boletas.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import UTC, datetime, timedelta

import numpy as np

from . import cartera, cotizaciones as cz, mercado, registro, reto, servicios, vigencia
from .config import Ajustes

MOVIMIENTO_INVALIDA = 0.01          # un cambio de precio > 1 % invalida la boleta
MARGEN_LIMITE = 0.002               # precio límite: ±0.2 % sobre el último precio confiable
DESLIZAMIENTOS = (0.0, 0.001, 0.005)
CONTRACCION_MEDIA = 0.5             # declarada antes de evaluar: la media histórica se reduce a la mitad
VIGENCIA_MIN_ABIERTO = 15
BANDA_REFERENCIA = 0.02             # SIC sin cotización confiable: solo capturar si el portal está a ±2 % de la referencia


def _tick(precio: float) -> float:
    return round(round(precio / 0.01) * 0.01, 2)


def estimacion_historica(serie, h: int) -> dict:
    """Rango de resultados a h sesiones con la historia (no es pronóstico validado)."""
    r = np.diff(np.log(np.asarray(serie, dtype=float)))[-250:]
    if len(r) < 60:
        return {"disponible": False, "motivo": "menos de 60 sesiones de historia"}
    mu, sd = float(r.mean()) * CONTRACCION_MEDIA, float(r.std())
    m, s = mu * h, sd * math.sqrt(h)
    return {"disponible": True, "rend_esperado": math.expm1(m), "p10": math.expm1(m - 1.2816 * s),
            "p90": math.expm1(m + 1.2816 * s), "perdida_plausible_p05": math.expm1(m - 1.6449 * s), "sesiones": h,
            "supuesto": "media histórica de 250 sesiones contraída 50 % y volatilidad histórica; distribución normal"}


def costos(importe: float, lado: str) -> dict:
    base = reto.costo_detalle(importe)
    esc = []
    for d in DESLIZAMIENTOS:
        extra = importe * d
        esc.append({"deslizamiento": d, "costo_total": round(base["total"] + extra, 2),
                    "precio_efectivo_relativo": (1 + d) if lado == "compra" else (1 - d)})
    return {**base, "escenarios_deslizamiento": esc,
            "sin_ejecucion": "Si la orden limitada no se ejecuta en su vigencia (1 día), el efectivo queda sin invertir o la "
                             "posición sin reducir; la propuesta deja de cumplirse y debe recalcularse."}


def _vol_media(con, iid: str) -> float | None:
    f = con.execute("SELECT AVG(volumen) FROM (SELECT volumen FROM precios WHERE instrumento_id=? AND volumen > 0 "
                    "ORDER BY fecha DESC LIMIT 20)", (iid,)).fetchone()
    return float(f[0]) if f and f[0] else None


def _caducidad(ahora: datetime) -> datetime:
    if vigencia.mercado_abierto("XMEX", ahora):
        return ahora + timedelta(minutes=VIGENCIA_MIN_ABIERTO)
    cal = vigencia.calendario("XMEX")
    import pandas as pd
    siguiente = cal.next_open(pd.Timestamp(ahora))
    return siguiente.to_pydatetime() + timedelta(minutes=VIGENCIA_MIN_ABIERTO)


def construir(con: sqlite3.Connection, ajustes: Ajustes, fila: dict, cart: dict, ahora: datetime | None = None,
              efectivo_supuesto: float | None = None) -> dict:
    """Boleta para una fila de cambios de una propuesta (id, accion, monto_mxn). Recalcula todo con datos actuales."""
    ahora = ahora or datetime.now(UTC)
    ins = mercado.instrumentos(con)
    i = ins.get(fila["id"]) or {"id": fila["id"]}
    provs = cz.construir(con, ajustes.es_demo)
    conf = cz.precio_confiable(con, provs, i, ahora, prioridad=["demo"] if ajustes.es_demo else None)
    faltan, razones = [], []
    q = conf.get("cotizacion")
    calidad = cz.calidad_actual(q, ahora) if q else "SIN PRECIO CONFIABLE"
    total = float(cart.get("valor_total") or 0)
    efectivo = float(cart.get("efectivo") or 0)
    plan_inicial = bool(efectivo_supuesto) and not cart.get("n_operaciones")
    if plan_inicial:  # sin operaciones registradas: se planea con el capital del perfil, marcado como supuesto
        efectivo = total = float(efectivo_supuesto)
        faltan.append("Registrar la aportación inicial en «Mi portafolio Actinver» (la boleta supone efectivo = capital del perfil)")
    pos_valor = {p["instrumento_id"]: float(p.get("valor_mxn") or 0) for p in cart.get("posiciones", [])}
    pos_tit = {p["instrumento_id"]: float(p.get("cantidad") or 0) for p in cart.get("posiciones", [])}
    monto = float(fila.get("monto_mxn") or 0)
    direccional = fila.get("accion") in ("comprar", "vender")  # «mantener» trae un monto chico dentro de la banda
    lado = ("compra" if monto > 0 else "venta" if monto < 0 else None) if direccional else None
    tipo = {"comprar": "considerar compra", "vender": "considerar venta"}.get(fila.get("accion"), "mantener")
    if lado is None:
        tipo = "mantener"
    if not q and lado:
        tipo = "investigar"  # sin precio confiable se inhibe cualquier propuesta direccional
        faltan.append("Precio BMV confiable de la serie exacta (" + "; ".join(conf.get("motivos", [])[:2]) + ")")
    precio = float(q["precio"]) if q else None
    condicional = None
    if not q and lado:
        condicional = referencia_condicional(con, ajustes, i["id"], monto, lado)
        if condicional and lado == "venta":  # vender: con el precio de referencia y nunca más de lo que se tiene
            tiene = int(pos_tit.get(i["id"], 0))
            condicional["titulos_aprox"] = min(tiene, round(abs(monto) / condicional["precio_ref_mxn"]))
            if condicional["titulos_aprox"] == tiene:
                condicional["nota"] += f" Equivale a vender todos sus títulos ({tiene})."
        if condicional:
            faltan.append(f"Confirmar en el portal que el precio esté entre ${condicional['precio_min']:,.2f} y "
                          f"${condicional['precio_max']:,.2f} MXN; con él, títulos = monto ÷ precio del portal")
        lado = None  # sin precio confiable no hay orden: la referencia condicional es solo una guía
    cantidad, limite, importe = 0, None, 0.0
    if q and lado:
        limite = _tick(precio * (1 + MARGEN_LIMITE) if lado == "compra" else precio * (1 - MARGEN_LIMITE))
        cantidad = math.floor(abs(monto) / limite + 1e-9)  # sin perder un título por punto flotante
        if lado == "venta":
            cantidad = min(cantidad, int(pos_tit.get(i["id"], 0)))
        if lado == "compra":
            cantidad = min(cantidad, math.floor(efectivo / (limite * (1 + (reto.costo_operacion() or 0)))))
        importe = cantidad * limite
        if cantidad <= 0:
            tipo, lado = "mantener", None
            razones.append("La cantidad entera resultante es 0 (efectivo, posición o monto insuficiente).")
    c = costos(importe, lado or "compra") if importe else None
    signo = 1 if lado == "compra" else -1
    efectivo_post = efectivo - signo * importe - (c["total"] if c else 0)
    valor_emisora_post = pos_valor.get(i["id"], 0) + signo * importe
    peso_post = valor_emisora_post / total if total > 0 else None
    advert = reto.verificar_compras([{"id": i["id"], "monto": importe}], total, pos_valor) if lado == "compra" and importe else []
    serie = mercado.precios_mxn(con, ajustes, [i["id"]], ajustados="splits")
    h = max(reto.sesiones_restantes(ahora), 1)
    est = estimacion_historica(serie[i["id"]].dropna().values, h) if i["id"] in serie.columns else {"disponible": False,
                                                                                                    "motivo": "sin historia"}
    if not est.get("disponible"):
        faltan.append(f"Historia de precios suficiente ({est.get('motivo')})")
    ev = (importe * est["rend_esperado"] if est.get("disponible") and importe else None)
    vol = _vol_media(con, i["id"])
    liquidez = ({"volumen_medio_20": vol, "fraccion_del_volumen": (cantidad / vol) if vol else None}
                if vol else {"volumen_medio_20": None, "nota": "liquidez no verificada (sin volumen de la serie BMV)"})
    if not vol:
        faltan.append("Volumen negociado de la serie en la BMV (liquidez)")
    if efectivo_post < -0.01:
        faltan.append("Efectivo suficiente: la compra excede el efectivo disponible")
    razones.append(fila.get("nota") or f"Diferencia de {fila.get('delta_pp', 0)} pp frente al peso objetivo de la propuesta.")
    caduca = _caducidad(ahora)
    b = {
        "instrumento_id": i["id"], "emisora_serie": i.get("clave_operable"), "mercado": cz.normalizar_mercado(i),
        "tipo": tipo, "lado": lado, "cantidad": cantidad, "precio_referencia": precio, "precio_limite": limite,
        "tipo_orden": "limitada" if lado else None, "vigencia_orden": "día" if lado else None,
        "calidad_precio": calidad, "fuente_precio": q and {k: q[k] for k in ("proveedor", "hora_evento", "estado_latencia", "moneda", "mercado")},
        "importe": round(importe, 2), "costos": c,
        "efecto": {"efectivo_antes": round(efectivo, 2), "efectivo_despues": round(efectivo_post, 2),
                   "peso_emisora_despues": peso_post, "advertencias_reto": advert},
        "valor_esperado_estimado": ev, "rango": est, "liquidez": liquidez,
        "alternativa": {"descripcion": "Mantener efectivo o no cambiar la posición", "valor_esperado": 0.0},
        "invalidacion": [f"El precio se mueve más de {MOVIMIENTO_INVALIDA:.0%} respecto a {precio}" if precio else
                         "Aparece un precio confiable (la boleta se regenera)",
                         "El dato pasa a STALE o SIN PRECIO CONFIABLE", "Cambian la cartera confirmada o las reglas del Reto",
                         f"Llega la caducidad ({caduca.isoformat(timespec='minutes')})"],
        "datos_faltantes": faltan, "razones": razones,
        "aviso": "Propuesta para revisión humana. La terminal no registra órdenes; usted la captura en el portal si decide.",
        "creada_en": ahora.isoformat(timespec="seconds"), "caduca_en": caduca.isoformat(timespec="seconds"),
        "version_reglas": registro.estado_reglas(con).get("version"),
        "referencia_condicional": condicional,
        "accion_propuesta": fila.get("accion"), "monto_objetivo": round(monto, 2),  # para recalcular sin deriva
        "plan_inicial": plan_inicial, "efectivo_supuesto": efectivo_supuesto if plan_inicial else None,
    }
    b["huella_datos"] = huella(b, cart)
    return b


def huella(b: dict, cart: dict) -> str:
    base = [b["instrumento_id"], b["precio_referencia"], (b.get("fuente_precio") or {}).get("hora_evento"), b["cantidad"],
            round(float(cart.get("efectivo") or 0), 2),
            sorted((p["instrumento_id"], p.get("cantidad")) for p in cart.get("posiciones", [])), b["version_reglas"]]
    return hashlib.sha256(json.dumps(base, default=str).encode()).hexdigest()[:16]


PLAN_DEL_DIA = "plan_del_dia"


def generar(con: sqlite3.Connection, ajustes: Ajustes, clave: str = "acciones_ajuste") -> list[dict]:
    """Boletas de una propuesta. Con clave «plan_del_dia» usa la misma propuesta que el plan de Telegram (la vigente
    mejor puntuada) y reemplaza las boletas vigentes anteriores para no duplicar órdenes."""
    perfil = servicios.perfil_actual(con, ajustes)
    props = servicios.propuestas_guardadas(con, ajustes, perfil)
    reemplazadas = 0
    if clave == PLAN_DEL_DIA:
        from . import resumen
        p = resumen.propuesta_referencia(props)
        if not p:
            avisos = sorted({a for v in props.values() if v for a in v.get("avisos") or []})
            raise ValueError("No hay una propuesta vigente para el plan del día" + (": " + "; ".join(avisos) if avisos else "."))
        clave = p["clave"]
        cur = con.execute("UPDATE boletas SET estado='descartada', motivo_estado='reemplazada por las boletas del plan del día' "
                          "WHERE estado='vigente'")
        reemplazadas = cur.rowcount
    p = props.get(clave)
    if not p:
        raise ValueError("No hay propuesta calculada con esa clave")
    if p.get("estado") != "calculada" or p.get("avisos"):
        raise ValueError("No se generan boletas con esta propuesta: " + ("; ".join(p.get("avisos") or [])
                         or f"estado «{p.get('estado')}»") + ".")
    cart = servicios.cartera_actual(con, ajustes)
    filas = (p.get("cambios") or {}).get("filas") or []
    if not filas:  # sin cartera registrada: la asignación inicial completa
        filas = [{"id": a["id"], "accion": "comprar", "monto_mxn": a.get("monto_estimado") or a.get("monto_objetivo"),
                  "delta_pp": round(a["peso"] * 100, 2), "nota": "Asignación inicial de la propuesta"} for a in p.get("pesos") or []]
    sup = float(p.get("capital") or perfil.get("capital") or 0) if not cart.get("n_operaciones") else None
    boletas = [construir(con, ajustes, f, cart, efectivo_supuesto=sup) for f in filas]
    direccionales = [b for b in boletas if b["tipo"] in ("considerar compra", "considerar venta")]
    ahora = datetime.now(UTC).isoformat(timespec="seconds")
    ids = []
    for b in boletas:
        cur = con.execute("INSERT INTO boletas (creada_en, caduca_en, instrumento_id, tipo, contenido, huella_datos) VALUES (?,?,?,?,?,?)",
                          (ahora, b["caduca_en"], b["instrumento_id"], b["tipo"], json.dumps(b, default=str), b["huella_datos"]))
        ids.append(cur.lastrowid)
    con.commit()
    resumen = {"tipo": "considerar rebalanceo" if len(direccionales) >= 2 else None, "boletas": ids, "propuesta": clave,
               "nombre_propuesta": p["nombre"], "puntuacion": p["puntuacion"]["total"], "reemplazadas": reemplazadas,
               "numero_ordenes": len(direccionales),
               "ordenes_compra": sum(b["tipo"] == "considerar compra" for b in boletas),
               "ordenes_venta": sum(b["tipo"] == "considerar venta" for b in boletas),
               "por_investigar": sum(b["tipo"] == "investigar" for b in boletas),
               "costo_total": round(sum((b["costos"] or {}).get("total", 0) for b in boletas), 2)}
    return [resumen] + [{**b, "id": i} for b, i in zip(boletas, ids, strict=True)]


def recalcular(con: sqlite3.Connection, ajustes: Ajustes, bid: int, ahora: datetime | None = None) -> dict:
    """Se ejecuta JUSTO ANTES de presentar la boleta. Invalida si caducó, si el precio cambió materialmente, si el dato
    ya no es confiable o si la cartera o las reglas cambiaron."""
    ahora = ahora or datetime.now(UTC)
    f = con.execute("SELECT * FROM boletas WHERE id=?", (bid,)).fetchone()
    if not f:
        raise ValueError("boleta inexistente")
    b = json.loads(f["contenido"])
    if f["estado"] != "vigente":
        return {**b, "id": bid, "estado": f["estado"], "motivo_estado": f["motivo_estado"]}
    motivo = None
    if ahora >= datetime.fromisoformat(f["caduca_en"]):
        estado, motivo = "caducada", "Pasó su caducidad"
    else:
        cart = servicios.cartera_actual(con, ajustes)
        if b.get("monto_objetivo") is not None:  # misma acción y monto que al crearla (no títulos × límite)
            fila = {"id": b["instrumento_id"], "accion": b.get("accion_propuesta"), "monto_mxn": b["monto_objetivo"],
                    "nota": b["razones"][-1] if b["razones"] else ""}
        else:  # boletas anteriores a este cambio
            fila = {"id": b["instrumento_id"], "accion": {"considerar compra": "comprar", "considerar venta": "vender"}.get(b["tipo"]),
                    "monto_mxn": (b["importe"] if b["lado"] == "compra" else -b["importe"]) if b["lado"] else 0,
                    "nota": b["razones"][-1] if b["razones"] else ""}
        nueva = construir(con, ajustes, fila, cart, ahora, efectivo_supuesto=b.get("efectivo_supuesto"))
        estado = "vigente"
        if b["precio_referencia"] and not nueva["precio_referencia"]:
            estado, motivo = "invalidada", "El precio dejó de ser confiable"
        elif b["precio_referencia"] and abs(nueva["precio_referencia"] / b["precio_referencia"] - 1) > MOVIMIENTO_INVALIDA:
            estado, motivo = "invalidada", (f"El precio cambió {nueva['precio_referencia'] / b['precio_referencia'] - 1:+.2%} "
                                            f"(> {MOVIMIENTO_INVALIDA:.0%})")
        elif nueva["calidad_precio"] in ("STALE", "SIN PRECIO CONFIABLE") and b["tipo"] != "investigar":
            estado, motivo = "invalidada", f"Calidad del precio: {nueva['calidad_precio']}"
        elif nueva["version_reglas"] != b["version_reglas"]:
            estado, motivo = "invalidada", "Cambiaron las reglas del Reto"
        elif nueva["cantidad"] != b["cantidad"] and b["lado"]:
            estado, motivo = "invalidada", "Cambió la cantidad posible (efectivo o posición)"
        if estado == "vigente":
            b = {**nueva, "creada_en": b["creada_en"], "caduca_en": f["caduca_en"]}
            con.execute("UPDATE boletas SET contenido=?, huella_datos=? WHERE id=?", (json.dumps(b, default=str), b["huella_datos"], bid))
    if estado != "vigente":
        con.execute("UPDATE boletas SET estado=?, motivo_estado=? WHERE id=?", (estado, motivo, bid))
    con.commit()
    return {**b, "id": bid, "estado": estado, "motivo_estado": motivo, "recalculada_en": ahora.isoformat(timespec="seconds")}


def descartar(con, bid: int, motivo: str = "") -> None:
    con.execute("UPDATE boletas SET estado='descartada', motivo_estado=? WHERE id=? AND estado='vigente'", (motivo[:200], bid))
    con.commit()


def marcar_ejecutada(con: sqlite3.Connection, bid: int, folio: str, fecha: str, cantidad: float, precio: float,
                     comision: float | None = None, impuesto: float | None = None) -> int:
    """El participante declara que EJECUTÓ la operación en el portal y copia los datos de la confirmación.
    Solo así se registra la operación confirmada (cambia posiciones y efectivo)."""
    f = con.execute("SELECT * FROM boletas WHERE id=?", (bid,)).fetchone()
    if not f:
        raise ValueError("boleta inexistente")
    b = json.loads(f["contenido"])
    if not b.get("lado"):
        raise ValueError("una boleta sin lado (mantener/investigar) no se ejecuta")
    if not str(folio).strip():
        raise ValueError("folio de la confirmación: obligatorio")
    importe = float(cantidad) * float(precio)
    cd = reto.costo_detalle(importe)
    t = cartera.validar({"fecha": fecha, "tipo": b["lado"], "instrumento_id": b["instrumento_id"], "cantidad": cantidad,
                         "precio": precio, "comision": cd["comision"] if comision is None else comision,
                         "impuesto": cd["iva"] if impuesto is None else impuesto, "moneda": "MXN", "tipo_cambio": 1,
                         "nota": f"folio {str(folio).strip()[:40]} (boleta {bid})"}, mercado.instrumentos(con))
    tid = cartera.registrar(con, t, f"confirmacion:{str(folio).strip()[:40]}")
    if tid is None:
        raise ValueError("operación duplicada: ya existe una operación idéntica")
    con.execute("UPDATE boletas SET estado='marcada_ejecutada', folio=?, marcada_en=?, transaccion_id=? WHERE id=?",
                (str(folio).strip()[:40], datetime.now(UTC).isoformat(timespec="seconds"), tid, bid))
    con.commit()
    return tid


def listar(con: sqlite3.Connection, ajustes: Ajustes, recalcular_vigentes: bool = True) -> list[dict]:
    out = []
    for f in con.execute("SELECT id, estado FROM boletas ORDER BY id DESC LIMIT 100").fetchall():
        if recalcular_vigentes and f["estado"] == "vigente":
            out.append(recalcular(con, ajustes, f["id"]))
        else:
            g = con.execute("SELECT * FROM boletas WHERE id=?", (f["id"],)).fetchone()
            out.append({**json.loads(g["contenido"]), "id": g["id"], "estado": g["estado"], "motivo_estado": g["motivo_estado"],
                        "folio": g["folio"]})
    return out


def referencia_condicional(con, ajustes: Ajustes, iid: str, monto: float, lado: str) -> dict | None:
    """Guía para una emisora sin cotización confiable (típicamente SIC): cierre de la bolsa de origen convertido a MXN.

    NO es la cotización del SIC ni habilita la boleta: da títulos aproximados y una banda de ±2 % fuera de la cual el
    participante no debe capturar sin regenerar. Solo con referencia vigente o retrasada (nunca vencida ni ausente)."""
    q = mercado.cotizaciones(con, ajustes, [iid]).get(iid) or {}
    ref = q.get("precio_mxn")
    if not ref or q.get("estado") not in ("vigente", "retrasado"):
        return None
    fx = mercado.ultimo_fx(con, ajustes) if q.get("moneda") != "MXN" else {}
    return {"lado_sugerido": lado, "monto_mxn": round(abs(monto), 2), "precio_ref_mxn": round(float(ref), 2),
            "precio_min": round(ref * (1 - BANDA_REFERENCIA), 2), "precio_max": round(ref * (1 + BANDA_REFERENCIA), 2),
            "titulos_aprox": math.floor(abs(monto) / (ref * (1 + BANDA_REFERENCIA))),
            "fuente": q.get("proveedor"), "fecha": q.get("fecha"), "tipo_dato": q.get("tipo_dato"),
            "estado": q.get("estado"), "moneda_origen": q.get("moneda"), "precio_origen": q.get("precio"),
            "tipo_cambio": fx.get("valor"), "tipo_cambio_fecha": fx.get("fecha"), "tipo_cambio_fuente": fx.get("proveedor"),
            "nota": ("REFERENCIA, no cotización del SIC: cierre de la bolsa de origen × tipo de cambio. " if q.get("moneda") != "MXN"
                     else f"REFERENCIA: último cierre disponible ({q.get('fecha')}, {q.get('estado')}), no cotización actual. ")
                    + "Verifique el precio en el portal; si está fuera de la banda, no capture y regenere las boletas."}


def texto_telegram(boletas: list[dict]) -> str:
    """Boletas vigentes en texto para Telegram: lo necesario para capturar cada orden a mano en el simulador."""
    import pandas as pd
    vig = [b for b in boletas if b.get("estado", "vigente") == "vigente"]
    if not vig:
        return "No hay boletas vigentes. Genere nuevas en la terminal («Generar boletas del plan del día»)."
    vence = min(b["caduca_en"] for b in vig)
    listas = [b for b in vig if b["tipo"] in ("considerar compra", "considerar venta") and b.get("cantidad")]
    otras = [b for b in vig if b not in listas and b["tipo"] != "mantener"]
    lineas = [f"🧾 Boletas para capturar a mano — vencen {pd.Timestamp(vence).tz_convert('America/Mexico_City'):%d-%m %H:%M} (CDMX)", ""]
    if listas:
        lineas.append(f"Listas ({len(listas)}), orden limitada del día:")
        for b in listas:
            icono = "🟢 COMPRA" if b.get("lado") == "compra" else "🔴 VENTA"
            f = b.get("fuente_precio") or {}
            tipo = {"REAL_TIME": "tiempo real", "DELAYED": "retrasado", "EOD": "cierre diario"}.get(f.get("estado_latencia"), "sin clasificar")
            cuando = pd.Timestamp(f["hora_evento"]).tz_convert("America/Mexico_City").strftime("%d-%m") if f.get("hora_evento") else "—"
            lineas.append(f"{icono} {b.get('emisora_serie') or b['instrumento_id']}: {int(b['cantidad']):,} títulos, "
                          f"límite ${b['precio_limite']:,.2f} (≈ ${b.get('importe') or 0:,.0f}) · boleta #{b['id']}\n"
                          f"   precio: {f.get('proveedor', '—')}, {f.get('moneda', 'MXN')}, {tipo} del {cuando}")
        costo = sum(((b.get("costos") or {}).get("total") or 0) for b in listas)
        lineas.append(f"Costo estimado (comisión + IVA): ${costo:,.2f}.")
    if otras:
        cond = [b for b in otras if b.get("referencia_condicional")]
        resto = [b for b in otras if not b.get("referencia_condicional")]
        if cond:
            lineas += ["", f"Condicionales ({len(cond)}) — sin cotización confiable (SIC: cierre de origen × tipo de cambio; "
                           "BMV: último cierre). Capture SOLO si el precio del portal está dentro de la banda; títulos = monto ÷ "
                           "precio del portal:"]
            for b in cond:
                r = b["referencia_condicional"]
                icono = "🟡 COMPRA" if r["lado_sugerido"] == "compra" else "🟠 VENTA"
                lineas.append(f"{icono} {b.get('emisora_serie') or b['instrumento_id']}: ≈ {r['titulos_aprox']:,} títulos "
                              f"(≈ ${r['monto_mxn']:,.0f}), banda ${r['precio_min']:,.2f}–${r['precio_max']:,.2f} · #{b['id']}\n"
                              + (f"   referencia: {r['fuente']} {r['moneda_origen']} {r['precio_origen']} del {r['fecha']} × "
                                 f"USD/MXN {r['tipo_cambio']} ({r['tipo_cambio_fuente']}, {r['tipo_cambio_fecha']})"
                                 if r.get("tipo_cambio") else f"   referencia: {r['fuente']} MXN {r['precio_origen']} del "
                                 f"{r['fecha']} ({r['estado']})"))
        if resto:
            lineas += ["", f"Por investigar ({len(resto)}): sin precio confiable ni referencia vigente; no capture sin revisar:"]
            lineas.append(", ".join(f"{b.get('emisora_serie') or b['instrumento_id']} (#{b['id']})" for b in resto))
    lineas += ["", "Antes de capturar: revise el precio en el portal; si se movió más de 1 %, genere boletas nuevas. "
                   "Después, márquela como ejecutada con su folio. La terminal no envía órdenes."]
    return "\n".join(lineas)


def enviar_telegram(con: sqlite3.Connection, ajustes: Ajustes) -> dict:
    """Envía por Telegram las boletas vigentes (recalculadas justo antes de enviar)."""
    from . import notificador
    texto = texto_telegram(listar(con, ajustes, recalcular_vigentes=True))
    cfg = {**ajustes["alertas"], "notificar_escritorio": False, "notificar_telegram": True, "notificar_correo": False}
    return {"resultado": notificador.enviar("🧾 Boletas para capturar", texto, cfg, detalle=texto), "texto": texto}
