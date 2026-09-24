"""Motor de reglas de alertas.

Cada regla produce condiciones (regla, clave, activa). Una alerta se dispara solo en el flanco de subida
(la condición pasa de inactiva a activa), respetando un enfriamiento por (regla, clave). Las reglas de deriva
usan histéresis: se activan al superar `deriva_pp` y solo se rearman al bajar de `deriva_rearme_pp`.
Fuera del horario de la BMV se registran pero no se notifican al escritorio (configurable).
Ninguna alerta ejecuta operaciones: solo informa y ofrece «simular cambio».
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pandas as pd

from . import mercado, notificador, reto, vigencia
from .db import transaccion


@dataclass
class Condicion:
    regla: str
    clave: str
    activa: bool
    severidad: str = "aviso"
    titulo: str = ""
    motivo: str = ""
    datos: dict = field(default_factory=dict)
    fuente: str = ""
    accion: str = ""
    simulacion: list | None = None
    rearme: bool = True  # False: mientras la condición siga activa no se rearma (histéresis la maneja la regla)


def _dt(txt: str | None) -> datetime | None:
    if not txt:
        return None
    try:
        d = datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


# --------------------------------------------------------------------------------------------------------------
def reglas_deriva(con, cfg: dict, cartera: dict, propuestas: dict) -> list[Condicion]:
    out = []
    if not cartera.get("n_operaciones"):
        return out
    for clave, p in propuestas.items():
        if not p or p.get("lente") != "ajuste":
            continue
        activa_prev = _estado(con, "deriva", clave)
        if p.get("estado") not in ("calculada", "demostracion") or p.get("avisos"):
            continue  # propuesta no actual: no se recomienda nada (la regla técnica lo informa)
        filas = p["cambios"]["filas"]
        max_dev = max((abs(f["delta_pp"]) for f in filas), default=0.0)
        mejora = (p.get("mejora_esperada") or {}).get("neta", 0.0)
        umbral = cfg["deriva_rearme_pp"] if activa_prev else cfg["deriva_pp"]
        activa = max_dev >= umbral and (mejora >= cfg["mejora_neta_min"] or activa_prev)
        ops = [{"id": f["id"], "monto": f["monto_mxn"]} for f in filas if f["accion"] != "mantener"]
        out.append(Condicion(
            "deriva", clave, activa, "aviso", f"Posible rebalanceo — {p['nombre']}",
            f"Desviación máxima {max_dev:.1f} pp (umbral {cfg['deriva_pp']} pp) y mejora esperada neta de costos "
            f"{mejora:.2%} (umbral {cfg['mejora_neta_min']:.2%}) en {p['mejora_esperada']['horizonte_sesiones']} sesiones.",
            {"desviacion_pp": max_dev, "mejora_neta": mejora, "operaciones": len(ops), "datos_hasta": p.get("datos_hasta")},
            "propuesta " + p["clave"], f"REVISAR {len(ops)} cambios posibles; costo estimado "
            f"{p['cambios']['costo_total']:,.0f} MXN.", ops))
    return out


def reglas_posicion(con, cfg: dict, cartera: dict, precios_hist: pd.DataFrame, primeras_compras: dict) -> list[Condicion]:
    out = []
    for pos in cartera.get("posiciones", []):
        iid, px, cp = pos["instrumento_id"], pos.get("precio_mxn"), pos.get("costo_promedio")
        if px is None or not cp or pos.get("vigencia") in ("vencido", "sin_datos"):
            continue
        rend = px / cp - 1
        base = {"precio_mxn": px, "costo_promedio": cp, "rendimiento": rend, "fecha_precio": pos.get("fecha_precio")}
        venta = [{"id": iid, "monto": -round(pos["valor_mxn"] or 0, 2)}]
        out.append(Condicion("stop_loss", iid, rend <= cfg["stop_loss"], "critica",
                             f"Stop-loss: {pos.get('clave_operable') or iid} {rend:.1%}",
                             f"El precio ({px:,.2f} MXN) cayó {rend:.1%} frente al costo promedio ({cp:,.2f}); umbral "
                             f"{cfg['stop_loss']:.0%}.", base, pos.get("proveedor") or "", "REVISAR la posición y su tesis; la decisión y la orden son del participante.", venta))
        out.append(Condicion("take_profit", iid, rend >= cfg["take_profit"], "info",
                             f"Toma de utilidad: {pos.get('clave_operable') or iid} +{rend:.1%}",
                             f"Ganancia de {rend:.1%} sobre el costo promedio; umbral {cfg['take_profit']:.0%}.", base,
                             pos.get("proveedor") or "", "REVISAR si la ganancia cambia su plan; la decisión es del participante.",
                             [{"id": iid, "monto": -round((pos["valor_mxn"] or 0) / 2, 2)}]))
        if iid in precios_hist.columns and iid in primeras_compras:
            serie = precios_hist[iid].loc[pd.Timestamp(primeras_compras[iid]):].dropna()
            if len(serie):
                maximo = float(serie.max())
                caida = px / maximo - 1
                out.append(Condicion("caida_maximo", iid, caida <= cfg["caida_desde_maximo"], "aviso",
                                     f"Caída desde máximo: {pos.get('clave_operable') or iid} {caida:.1%}",
                                     f"Precio {px:,.2f} vs máximo {maximo:,.2f} desde la compra; umbral "
                                     f"{cfg['caida_desde_maximo']:.0%}.", {**base, "maximo": maximo, "caida": caida},
                                     pos.get("proveedor") or "", "Revisar tesis de inversión y tamaño de la posición.", venta))
    return out


def reglas_macro(con, cfg: dict, ahora_dt: datetime) -> list[Condicion]:
    out = []
    limite = ahora_dt + timedelta(hours=cfg["macro_horas"])
    for e in con.execute("SELECT * FROM eventos_macro WHERE impacto='High' AND pais IN ('USD','MXN')"):
        f = _dt(e["fecha"])
        if not f:
            continue
        activa = ahora_dt <= f <= limite
        out.append(Condicion("macro", e["id"], activa, "aviso", f"Evento de alto impacto: {e['pais']} {e['titulo']}",
                             f"{e['titulo']} ({e['pais']}) el {f.astimezone(reto.MX):%d-%m %H:%M} CDMX; pronóstico "
                             f"{e['pronostico'] or '—'}, previo {e['previo'] or '—'}.",
                             {"fecha": e["fecha"], "pronostico": e["pronostico"], "previo": e["previo"]}, "ForexFactory",
                             "REVISAR la exposición a USD/MXN y a EE. UU. antes del evento.",
                             rearme=False))
    return out


def reglas_insider(con, cfg: dict, ids: set[str], ahora_dt: datetime) -> list[Condicion]:
    out = []
    desde = (ahora_dt - timedelta(days=14)).date().isoformat()
    for r in con.execute("SELECT * FROM insiders WHERE fecha >= ? AND codigo IN ('P','S')", (desde,)):
        if r["instrumento_id"] not in ids or (r["valor"] or 0) < cfg["insider_valor_min_usd"]:
            continue
        tipo = "compra" if r["codigo"] == "P" else "venta"
        out.append(Condicion("insider", r["id"], True, "info", f"Insider: {tipo} en {r['instrumento_id']}",
                             f"{r['nombre']} ({r['cargo'] or 'insider'}) registró una {tipo} de {r['acciones']:,.0f} acciones "
                             f"a {r['precio']:,.2f} USD (≈ {r['valor']:,.0f} USD) el {r['fecha']}.",
                             {"enlace": r["enlace"], "valor_usd": r["valor"]}, "SEC EDGAR (Formulario 4)",
                             "REVISAR como contexto; una operación de insider no implica por sí sola un cambio.", rearme=False))
    return out


def reglas_noticias(con, cfg: dict, ids: set[str], ahora_dt: datetime) -> list[Condicion]:
    out = []
    desde = (ahora_dt - timedelta(hours=48)).isoformat()
    for n in con.execute("SELECT * FROM noticias WHERE impacto='alto' AND publicado >= ?", (desde,)):
        if n["instrumento_id"] not in ids or abs(n["sentimiento"] or 0) < cfg["noticia_sentimiento_min"]:
            continue
        signo = "negativa" if (n["sentimiento"] or 0) < 0 else "positiva"
        out.append(Condicion("noticia", n["id"], True, "aviso", f"Noticia {signo} de alto impacto: {n['instrumento_id']}",
                             f"«{n['titulo']}» ({n['motivo'] or 'clasificación por léxico'}).",
                             {"enlace": n["enlace"], "publicado": n["publicado"], "sentimiento": n["sentimiento"]},
                             "Seeking Alpha (RSS)", "Leer la nota completa en la fuente antes de decidir.", rearme=False))
    return out


def reglas_tecnicas(con, cfg: dict, cartera: dict, propuestas: dict, fx: dict) -> list[Condicion]:
    out = []
    for pos in cartera.get("posiciones", []):
        mala = pos.get("vigencia") in ("vencido", "sin_datos")
        out.append(Condicion("dato_vencido", pos["instrumento_id"], mala, "critica",
                             f"Dato no vigente: {pos.get('clave_operable') or pos['instrumento_id']}",
                             f"El precio de una posición está {pos.get('etiqueta_vigencia') or 'sin datos'} "
                             f"(último {pos.get('fecha_precio') or '—'}). Las recomendaciones que dependen de él se suspenden.",
                             {"fecha": pos.get("fecha_precio")}, pos.get("proveedor") or "",
                             "Actualizar datos o importar el precio; no decidir con este dato."))
    out.append(Condicion("dato_vencido", "fx", fx.get("estado") in ("vencido", "sin_datos"), "critica",
                         "Tipo de cambio no vigente", f"USD/MXN {fx.get('etiqueta', 'sin datos').lower()} "
                         f"(último {fx.get('fecha') or '—'}): se suspende la valoración de activos en dólares.",
                         {"fecha": fx.get("fecha")}, fx.get("proveedor") or "", "Configurar Banxico o revisar FRED."))
    for clave, p in propuestas.items():
        if not p or p.get("mercado_variante"):  # las variantes por mercado son informativas: no generan alertas críticas
            continue
        mal = p.get("estado") in ("suspendida", "desactualizada")
        out.append(Condicion("propuesta_suspendida", clave, mal, "critica", f"Propuesta sin recomendación: {p['nombre']}",
                             "; ".join(p.get("motivos") or p.get("avisos") or ["no actual"]), {}, "motor",
                             "Resolver la fuente de datos antes de usar la propuesta."))
    for r in con.execute("SELECT proveedor, estado, mensaje FROM ingestas WHERE id IN (SELECT MAX(id) FROM ingestas GROUP BY proveedor)"):
        out.append(Condicion("fuente_caida", r["proveedor"], r["estado"] == "error", "critica",
                             f"Fuente con error: {r['proveedor']}", (r["mensaje"] or "Sin detalle")[:300], {}, r["proveedor"],
                             "Revisar la pestaña Datos; el motor reintentará respetando los límites."))
    return out


# --------------------------------------------------------------------------------------------------------------
def _estado(con, regla: str, clave: str) -> bool:
    f = con.execute("SELECT activa FROM estado_alertas WHERE regla=? AND clave=?", (regla, clave)).fetchone()
    return bool(f and f["activa"])


PRIORIDAD = {"critica": 1, "aviso": 2, "info": 3}
# Horas de vigencia de una alerta antes de marcarse «caducada» (datos y precios cambian rápido; eventos duran más).
CADUCIDAD_H = {"datos_inciertos": 6, "dato_vencido": 6, "cambio_brusco": 8, "stop_loss": 24, "take_profit": 24,
               "deriva": 24, "concentracion": 24, "ruptura_tesis": 24, "macro": 48, "evento_corporativo": 72, "noticia": 48,
               "insider": 72, "cinco_acciones": 24, "diferencia_portal": 24, "deterioro_modelo": 168}

INCERTIDUMBRE = {
    "deriva": "Media: depende del rendimiento esperado estimado (incierto) y de precios posiblemente no vigentes.",
    "stop_loss": "Baja si el precio es vigente; el precio del portal puede diferir.",
    "take_profit": "Baja si el precio es vigente; el precio del portal puede diferir.",
    "caida_maximo": "Baja si el precio es vigente.", "macro": "Alta: el efecto del evento es desconocido.",
    "insider": "Alta: señal de contexto, no predictiva por sí sola.", "noticia": "Alta: clasificación automática del titular.",
}


def _revisar(c: Condicion) -> Condicion:
    """Toda alerta invita a REVISAR; nunca ordena comprar o vender."""
    if not c.titulo.startswith("REVISAR"):
        c.titulo = f"REVISAR: {c.titulo}"
    if c.accion and not c.accion.upper().startswith("REVISAR"):
        c.accion = f"REVISAR — {c.accion}"
    c.datos = {"incertidumbre": INCERTIDUMBRE.get(c.regla, "Ver cálculo y vigencia del dato."), **(c.datos or {})}
    return c


def procesar(con: sqlite3.Connection, condiciones: list[Condicion], cfg: dict, ahora_dt: datetime | None = None,
             notificar: bool = True) -> list[dict]:
    """Aplica flanco de subida + enfriamiento, guarda las alertas nuevas y notifica agrupadas."""
    ahora_dt = ahora_dt or datetime.now(UTC)
    nuevas = []
    condiciones = [_revisar(c) for c in condiciones]
    with transaccion(con):
        for c in condiciones:
            fila = con.execute("SELECT activa, ultimo_disparo FROM estado_alertas WHERE regla=? AND clave=?",
                               (c.regla, c.clave)).fetchone()
            previa = bool(fila and fila["activa"])
            ultimo = _dt(fila["ultimo_disparo"]) if fila else None
            enfriada = ultimo is None or ahora_dt - ultimo >= timedelta(hours=cfg["enfriamiento_horas"])
            dispara = c.activa and not previa and enfriada
            estado_nuevo = c.activa or (previa and not c.rearme)  # eventos puntuales no se rearman
            con.execute("INSERT INTO estado_alertas (regla, clave, activa, ultimo_disparo) VALUES (?,?,?,?) "
                        "ON CONFLICT(regla, clave) DO UPDATE SET activa=excluded.activa, "
                        "ultimo_disparo=COALESCE(excluded.ultimo_disparo, estado_alertas.ultimo_disparo)",
                        (c.regla, c.clave, int(estado_nuevo), ahora_dt.isoformat(timespec="seconds") if dispara else None))
            if dispara:
                cur = con.execute(
                    "INSERT INTO alertas (ts, regla, clave, severidad, titulo, motivo, datos, fuente, accion, simulacion, prioridad, "
                    "caduca_en, impacto_mxn) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ahora_dt.isoformat(timespec="seconds"), c.regla, c.clave, c.severidad, c.titulo[:200], c.motivo[:1000],
                     json.dumps(c.datos, default=str)[:4000], c.fuente[:200], c.accion[:300],
                     json.dumps(c.simulacion) if c.simulacion else None, PRIORIDAD.get(c.severidad, 3),
                     (ahora_dt + timedelta(hours=CADUCIDAD_H.get(c.regla, 24))).isoformat(timespec="seconds"),
                     (c.datos or {}).get("impacto_mxn")))
                nuevas.append({"id": cur.lastrowid, "regla": c.regla, "clave": c.clave, "titulo": c.titulo,
                               "severidad": c.severidad, "motivo": c.motivo, "accion": c.accion})
    reales = list(nuevas)  # lo que devuelve la función: solo alertas nuevas de este ciclo
    abierto = vigencia.mercado_abierto("XMEX", ahora_dt)
    if notificar and abierto:
        # Lo silenciado fuera de horario se entrega al abrir la BMV (no se pierde), si sigue nueva y vigente.
        diferidas = [dict(r) for r in con.execute(
            "SELECT id, regla, clave, titulo, severidad, motivo, accion FROM alertas WHERE notificada='silenciada_fuera_de_horario' "
            "AND estado='nueva' AND (caduca_en IS NULL OR caduca_en > ?)", (ahora_dt.isoformat(timespec="seconds"),))]
        vistas_ids = {a["id"] for a in nuevas}
        nuevas = nuevas + [d for d in diferidas if d["id"] not in vistas_ids]
    if nuevas and notificar:
        if cfg.get("silenciar_fuera_de_horario", True) and not abierto:
            marca = "silenciada_fuera_de_horario"
        else:
            titulo = nuevas[0]["titulo"] if len(nuevas) == 1 else f"{len(nuevas)} alertas nuevas"
            texto = " · ".join(a["titulo"] for a in nuevas[:3]) + (" …" if len(nuevas) > 3 else "")
            marca = json.dumps(notificador.enviar(titulo, texto, cfg, detalle=notificador.detalle(nuevas)))
        with transaccion(con):
            con.executemany("UPDATE alertas SET notificada=? WHERE id=?", [(marca, a["id"]) for a in nuevas])
    return reales


def reglas_reto(con, cfg: dict, cartera: dict, ahora_dt: datetime) -> list[Condicion]:
    """Concentración, cinco acciones operadas, pérdida máxima del participante y diferencia con el saldo del portal."""
    out = []
    total = float(cartera.get("valor_total") or 0)
    tope = float((reto.config().get("reglas") or {}).get("max_peso_emisora") or 0.5)
    for p in cartera.get("posiciones", []):
        w = p.get("peso")
        if w is None:
            continue
        nivel = "critica" if w > tope else "aviso"
        out.append(Condicion("concentracion", p["instrumento_id"], w >= float(cfg.get("concentracion_aviso", 0.45)), nivel,
                             f"Concentración {p.get('clave_operable') or p['instrumento_id']} {w:.1%}",
                             f"La posición vale {w:.1%} del portafolio estimado (tope del Reto {tope:.0%}; aviso desde "
                             f"{cfg.get('concentracion_aviso', 0.45):.0%}).",
                             {"calculo": f"{p.get('valor_mxn') or 0:,.2f} / {total:,.2f} = {w:.4f}", "peso": w,
                              "impacto_mxn": round(float(p.get("valor_mxn") or 0), 2)},
                             p.get("proveedor") or "cartera", "REVISAR la regla del 50 % antes de comprar más de esta emisora."))
    etapa = cartera.get("etapa")
    if etapa == "competencia" and reto.activo():
        tx = [dict(r) for r in con.execute("SELECT * FROM transacciones WHERE anulada=0")]
        ins = {r["id"]: dict(r) for r in con.execute("SELECT id, clase FROM instrumentos")}
        a = reto.acciones_operadas(tx, ins, "competencia")
        ses = reto.sesiones_restantes(ahora_dt)
        out.append(Condicion("cinco_acciones", "competencia", not a["cumple"], "critica" if ses <= 5 else "aviso",
                             f"Faltan {a['faltan']} de {a['minimo']} acciones distintas operadas",
                             f"Llevas {a['n']} acciones distintas con compra confirmada en la competencia; quedan {ses} sesiones. "
                             f"{a['nota']}", {"calculo": f"{a['n']} operadas: {', '.join(a['operadas']) or '—'}"},
                             "operaciones confirmadas", "REVISAR la condición de 5 acciones del reglamento (§6)."))
    base = float(cartera.get("aportacion_neta") or 0)  # en el Reto incluye el saldo inicial de la etapa
    if base > 0 and total > 0 and cartera.get("completa", True):
        rend = total / base - 1
        lim = float(cfg.get("perdida_maxima", -0.10))
        out.append(Condicion("perdida_maxima", etapa or "cartera", rend <= lim, "critica",
                             f"Pérdida del portafolio {rend:.1%} (límite propio {lim:.0%})",
                             f"Valor estimado {total:,.2f} vs base {base:,.2f}.",
                             {"calculo": f"{total:,.2f} / {base:,.2f} − 1 = {rend:.4f}", "impacto_mxn": round(total - base, 2),
                              "incertidumbre": "Estimación con precios de la terminal; compare con el saldo del portal."},
                             "cartera", "REVISAR el plan y el riesgo; el límite lo definió usted."))
    f = con.execute("SELECT * FROM saldos_portal ORDER BY id DESC LIMIT 1").fetchone()
    if f and total > 0:
        dif = total / f["valor_portafolio"] - 1
        umbral = float(cfg.get("diferencia_portal_pct", 0.01))
        out.append(Condicion("diferencia_portal", str(f["id"]), abs(dif) >= umbral, "aviso",
                             f"Diferencia con el portal {dif:+.2%}",
                             f"La terminal estima {total:,.2f}; el portal mostraba {f['valor_portafolio']:,.2f} "
                             f"({f['hora_portal']}).",
                             {"calculo": f"{total:,.2f} / {f['valor_portafolio']:,.2f} − 1 = {dif:.4f}",
                              "incertidumbre": "Horas distintas, precios de referencia y comisiones pueden explicar la diferencia."},
                             "saldo capturado del portal", "REVISAR operaciones registradas y precios; el portal es la valuación oficial."))
    return out


def reglas_cambio_brusco(cfg: dict, cartera: dict, precios_hist: pd.DataFrame) -> list[Condicion]:
    out = []
    umbral = float(cfg.get("cambio_brusco_pct", 0.05))
    for p in cartera.get("posiciones", []):
        iid = p["instrumento_id"]
        if iid not in precios_hist.columns:
            continue
        s = precios_hist[iid].dropna()
        if len(s) < 2:
            continue
        cambio = float(s.iloc[-1] / s.iloc[-2] - 1)
        out.append(Condicion("cambio_brusco", f"{iid}|{s.index[-1].date()}", abs(cambio) >= umbral, "aviso",
                             f"Cambio brusco {p.get('clave_operable') or iid} {cambio:+.1%}",
                             f"De {s.iloc[-2]:,.2f} a {s.iloc[-1]:,.2f} MXN entre {s.index[-2].date()} y {s.index[-1].date()}.",
                             {"calculo": f"{s.iloc[-1]:,.4f} / {s.iloc[-2]:,.4f} − 1 = {cambio:.4f}",
                              "incertidumbre": "Media: puede reflejar un dato de referencia, no la cotización BMV."},
                             p.get("proveedor") or "", "REVISAR noticias y la vigencia del precio.", rearme=False))
    return out


def reglas_evento_corporativo(con, cfg: dict, ids: set[str], ahora_dt: datetime) -> list[Condicion]:
    out = []
    desde = (ahora_dt - timedelta(days=int(cfg.get("evento_corporativo_dias", 10)))).date().isoformat()
    for r in con.execute("SELECT * FROM eventos_corporativos WHERE fecha >= ?", (desde,)):
        if r["instrumento_id"] not in ids:
            continue
        nota = ("El Reto NO paga dividendos (§13)." if r["tipo"] == "dividendo" else "El Reto sí reproduce splits.")
        out.append(Condicion("evento_corporativo", f"{r['instrumento_id']}|{r['fecha']}|{r['tipo']}", True, "info",
                             f"Evento corporativo: {r['tipo']} en {r['instrumento_id']}",
                             f"{r['tipo'].capitalize()} de {r['valor']} el {r['fecha']} reportado por {r['proveedor']}. {nota}",
                             {"calculo": f"valor {r['valor']}", "incertidumbre": "Baja: dato del proveedor; confirme en el portal."},
                             r["proveedor"], "REVISAR la posición en el portal tras el evento.", rearme=False))
    return out


def reglas_tesis(con, cartera: dict) -> list[Condicion]:
    """Ruptura de tesis: el participante registró en la bitácora un nivel que invalida su tesis y el precio lo cruzó."""
    precios = {p["instrumento_id"]: p for p in cartera.get("posiciones", [])}
    out = []
    for b in con.execute("SELECT * FROM bitacora_decisiones WHERE nivel_invalidacion IS NOT NULL AND instrumento_id IS NOT NULL"):
        p = precios.get(b["instrumento_id"])
        if not p or p.get("precio_mxn") is None or p.get("vigencia") in ("vencido", "sin_datos"):
            continue
        px, nivel = float(p["precio_mxn"]), float(b["nivel_invalidacion"])
        rota = px < nivel if (b["direccion_invalidacion"] or "debajo") == "debajo" else px > nivel
        impacto = (px - float(p.get("costo_promedio") or px)) * float(p.get("cantidad") or 0)
        out.append(Condicion("ruptura_tesis", str(b["id"]), rota, "aviso",
                             f"Ruptura de tesis: {p.get('clave_operable') or b['instrumento_id']}",
                             f"El precio {px:,.2f} cruzó el nivel de invalidación {nivel:,.2f} ({b['direccion_invalidacion'] or 'debajo'}) "
                             f"de su tesis: «{(b['tesis'] or '')[:120]}».",
                             {"calculo": f"{px:,.4f} vs {nivel:,.4f}", "impacto_mxn": round(impacto, 2),
                              "incertidumbre": "Depende de la vigencia del precio; confirme en el portal."},
                             "bitácora de decisiones", "REVISAR la tesis registrada y decidir si sigue vigente."))
    return out


def reglas_webhook(con, ahora_dt: datetime) -> list[Condicion]:
    """Alertas que el participante configuró en TradingView y llegaron por webhook (eventos, no precios)."""
    desde = (ahora_dt - timedelta(hours=24)).isoformat()
    out = []
    for e in con.execute("SELECT * FROM eventos_webhook WHERE recibido_en >= ? AND estado IN ('aceptado','atipico')", (desde,)):
        out.append(Condicion("tradingview", e["huella"][:16], True, "aviso" if e["estado"] == "atipico" else "info",
                             f"Alerta de TradingView: {e['alerta'] or e['simbolo_origen']}",
                             f"{e['simbolo_origen']} a {e['precio']:,.4f} {e['moneda']} (hora de la alerta {e['hora_evento']}). "
                             f"{e['motivo'] or ''}",
                             {"calculo": "evento recibido por webhook", "incertidumbre":
                              "Retraso del dato de TradingView no declarado (estado UNKNOWN)."},
                             "TradingView (webhook)", "REVISAR el gráfico y la cotización en el portal.", rearme=False))
    return out


def reglas_modelo(con, cfg: dict) -> list[Condicion]:
    from .investigacion import pronosticos
    d = pronosticos.deterioro(con)
    if not d or d.get("razon") is None:
        return []
    lim = float(cfg.get("deterioro_razon", 1.10))
    return [Condicion("deterioro_modelo", "modelo", d["razon"] > lim or d["cobertura_80"] < 0.65, "aviso",
                      "Deterioro estadístico del modelo",
                      f"Con {d['n']} pronósticos resueltos, su error es {d['razon']:.2f}× el de «sin cambio» y el "
                      f"intervalo 80 % cubrió {d['cobertura_80']:.0%}.",
                      {"calculo": f"MSE {d['mse']:.6f} / MSE sin cambio {d['mse_sin_cambio']:.6f}",
                       "incertidumbre": "Muestra pequeña y dependiente en el tiempo."},
                      "registro de pronósticos", "REVISAR: no use los pronósticos para decidir hasta revalidar el modelo.")]


DIRECCIONALES = {"stop_loss", "take_profit", "caida_maximo", "cambio_brusco", "deriva"}
RIESGOS = {
    "deriva": "Cambiar posiciones cuesta comisión + IVA y el rendimiento esperado es incierto.",
    "stop_loss": "Una venta tras la caída materializa la pérdida; mantener la posición expone a más caída.",
    "take_profit": "Mantener expone a devolver la ganancia; vender genera costos.",
    "caida_maximo": "La caída puede continuar o revertirse; el precio puede no ser el del portal.",
    "concentracion": "Una sola emisora > 50 % viola la regla del Reto (§6/§7) y concentra el riesgo.",
    "cinco_acciones": "Sin 5 acciones distintas operadas no se es elegible por rendimiento (§6).",
    "perdida_maxima": "La pérdida supera el límite que usted definió.",
    "datos_inciertos": "Decidir con un precio no confiable puede llevar a una operación equivocada.",
}


def contradictorias(con, ids: set[str], ahora_dt: datetime, horas: int = 24) -> set[str]:
    """Emisoras con noticias de alto impacto de signo opuesto en la ventana: incertidumbre material."""
    desde = (ahora_dt - timedelta(hours=horas)).isoformat()
    signos: dict[str, set[int]] = {}
    for n in con.execute("SELECT instrumento_id, sentimiento FROM noticias WHERE impacto='alto' AND publicado >= ? "
                         "AND sentimiento IS NOT NULL AND sentimiento <> 0", (desde,)):
        if n[0] in ids:
            signos.setdefault(n[0], set()).add(1 if n[1] > 0 else -1)
    return {i for i, s in signos.items() if len(s) > 1}


def inhibir_direccionales(conds: list[Condicion], sin_precio: set[str], dudosas: set[str]) -> list[Condicion]:
    """Ante incertidumbre material (sin precio confiable o noticias contradictorias) las alertas direccionales de esa
    emisora no se disparan; en su lugar se emite UNA alerta de datos que explica por qué."""
    afectadas: dict[str, str] = {**{i: "sin precio confiable" for i in sin_precio}, **{i: "noticias contradictorias" for i in dudosas}}
    if not afectadas:
        return conds
    out, inhibidas = [], []
    for c in conds:
        iid = c.clave.split("|")[0]
        if c.regla in DIRECCIONALES and c.activa and (iid in afectadas or (c.regla == "deriva" and afectadas)):
            inhibidas.append(f"{c.regla}:{iid}")
            c = Condicion(**{**c.__dict__, "activa": False})
        out.append(c)
    out.append(Condicion("datos_inciertos", "cartera", True, "aviso",
                         f"Datos insuficientes para alertas direccionales ({len(afectadas)} emisoras)",
                         "Se inhiben alertas de compra/venta potencial mientras falte un precio confiable o haya noticias "
                         "contradictorias: " + "; ".join(f"{i}: {m}" for i, m in sorted(afectadas.items())) + ".",
                         {"calculo": f"inhibidas: {', '.join(inhibidas) or 'ninguna activa'}",
                          "incertidumbre": "Alta: el precio o el contexto no permiten una conclusión direccional."},
                         "control de calidad de datos", "REVISAR el precio en el portal o capture un precio confirmado."))
    return out


def ficha_revision(a: dict) -> dict:
    """Ficha para decidir con calma. Nunca incluye un botón para operar el simulador."""
    datos = a.get("datos") or {}
    sim = a.get("simulacion") or []
    importe = sum(abs(float(x.get("monto") or 0)) for x in sim)
    return {
        "que_ocurrio": f"{a.get('titulo')}: {a.get('motivo')}",
        "cuando": a.get("ts"), "prioridad": a.get("prioridad"), "caduca_en": a.get("caduca_en"),
        "impacto_en_portafolio_mxn": a.get("impacto_mxn") if a.get("impacto_mxn") is not None else datos.get("impacto_mxn"),
        "datos_que_lo_sustentan": {"calculo": datos.get("calculo"), "fuente": a.get("fuente"), "hora": a.get("ts"),
                                   **{k: v for k, v in datos.items() if k not in ("calculo", "incertidumbre")}},
        "falta_confirmar": [x for x in (datos.get("incertidumbre"),
                                        "El precio y el saldo en el portal de Actinver (valuación oficial).",
                                        "Que la fuente cite el hecho original (emisora, regulador o dato oficial)."
                                        if a.get("regla") in ("noticia", "insider", "macro", "evento_corporativo") else None) if x],
        "costos": reto.costo_detalle(importe) if importe else None,
        "riesgos": RIESGOS.get(a.get("regla"), "Revise la vigencia del dato y el impacto en su cartera."),
        "opciones_para_revisar": [o for o in (a.get("accion"),
                                              "Simular el efecto (no envía órdenes)." if sim else None,
                                              "Registrar en la bitácora la decisión que tome usted.",
                                              "Descartar la alerta si no aplica.") if o],
    }


def evaluar(con: sqlite3.Connection, ajustes, cartera: dict, propuestas: dict, notificar: bool = True,
            ahora_dt: datetime | None = None) -> list[dict]:
    cfg = ajustes["alertas"]
    ahora_dt = ahora_dt or datetime.now(UTC)
    ids = {p["instrumento_id"] for p in cartera.get("posiciones", [])}
    precios = mercado.precios_mxn(con, ajustes, sorted(ids), ajustados=False) if ids else pd.DataFrame()
    compras = {r[0]: r[1] for r in con.execute(
        "SELECT instrumento_id, MIN(fecha) FROM transacciones WHERE tipo='compra' AND anulada=0 GROUP BY instrumento_id")}
    conds = (reglas_deriva(con, cfg, cartera, propuestas) + reglas_posicion(con, cfg, cartera, precios, compras)
             + reglas_macro(con, cfg, ahora_dt) + reglas_insider(con, cfg, ids, ahora_dt)
             + reglas_noticias(con, cfg, ids, ahora_dt)
             + reglas_tecnicas(con, cfg, cartera, propuestas, mercado.ultimo_fx(con, ajustes))
             + reglas_reto(con, cfg, cartera, ahora_dt) + reglas_cambio_brusco(cfg, cartera, precios)
             + reglas_evento_corporativo(con, cfg, ids, ahora_dt) + reglas_modelo(con, cfg)
             + reglas_webhook(con, ahora_dt) + reglas_tesis(con, cartera))
    if cfg.get("exigir_precio_confiable", True):
        from . import cotizaciones
        provs = cotizaciones.construir(con, ajustes.es_demo)
        prio = ["demo"] if ajustes.es_demo else None
        ins = mercado.instrumentos(con)
        sin_precio = {i for i in ids if i in ins and
                      cotizaciones.precio_confiable(con, provs, ins[i], ahora_dt, prioridad=prio)["estado"] != "confiable"}
        conds = inhibir_direccionales(conds, sin_precio, contradictorias(con, ids, ahora_dt))
    return procesar(con, conds, cfg, ahora_dt, notificar)


def listar(con: sqlite3.Connection, limite: int = 200) -> list[dict]:
    filas = []
    for r in con.execute("SELECT * FROM alertas ORDER BY id DESC LIMIT ?", (min(limite, 1000),)):
        d = dict(r)
        d["datos"] = json.loads(d["datos"] or "{}")
        d["simulacion"] = json.loads(d["simulacion"]) if d["simulacion"] else None
        d["ficha"] = ficha_revision(d)
        filas.append(d)
    return filas


def marcar(con: sqlite3.Connection, aid: int, estado: str) -> None:
    if estado not in ("vista", "descartada", "nueva"):
        raise ValueError("estado no válido")
    with transaccion(con):
        con.execute("UPDATE alertas SET estado=? WHERE id=?", (estado, aid))


def caducar(con: sqlite3.Connection, ahora_dt: datetime | None = None) -> int:
    t = (ahora_dt or datetime.now(UTC)).isoformat(timespec="seconds")
    n = con.execute("UPDATE alertas SET estado='caducada' WHERE estado='nueva' AND caduca_en IS NOT NULL AND caduca_en < ?", (t,)).rowcount
    con.commit()
    return n


def pendientes(con: sqlite3.Connection) -> int:
    caducar(con)
    return int(con.execute("SELECT COUNT(*) FROM alertas WHERE estado='nueva'").fetchone()[0])
