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
            "deriva", clave, activa, "aviso", f"Rebalanceo sugerido — {p['nombre']}",
            f"Desviación máxima {max_dev:.1f} pp (umbral {cfg['deriva_pp']} pp) y mejora esperada neta de costos "
            f"{mejora:.2%} (umbral {cfg['mejora_neta_min']:.2%}) en {p['mejora_esperada']['horizonte_sesiones']} sesiones.",
            {"desviacion_pp": max_dev, "mejora_neta": mejora, "operaciones": len(ops), "datos_hasta": p.get("datos_hasta")},
            "propuesta " + p["clave"], f"Revisar {len(ops)} cambios sugeridos; costo estimado "
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
                             f"{cfg['stop_loss']:.0%}.", base, pos.get("proveedor") or "", "Evaluar reducir o cerrar la posición.", venta))
        out.append(Condicion("take_profit", iid, rend >= cfg["take_profit"], "info",
                             f"Toma de utilidad: {pos.get('clave_operable') or iid} +{rend:.1%}",
                             f"Ganancia de {rend:.1%} sobre el costo promedio; umbral {cfg['take_profit']:.0%}.", base,
                             pos.get("proveedor") or "", "Evaluar realizar parte de la ganancia.",
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
                             "Revisar exposición a USD/MXN y a EE. UU. antes del evento; evitar operar en la publicación.",
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
                             "Considerar como contexto; una operación de insider no implica por sí sola un cambio.", rearme=False))
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
        if not p:
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


def procesar(con: sqlite3.Connection, condiciones: list[Condicion], cfg: dict, ahora_dt: datetime | None = None,
             notificar: bool = True) -> list[dict]:
    """Aplica flanco de subida + enfriamiento, guarda las alertas nuevas y notifica agrupadas."""
    ahora_dt = ahora_dt or datetime.now(UTC)
    nuevas = []
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
                    "INSERT INTO alertas (ts, regla, clave, severidad, titulo, motivo, datos, fuente, accion, simulacion) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (ahora_dt.isoformat(timespec="seconds"), c.regla, c.clave, c.severidad, c.titulo[:200], c.motivo[:1000],
                     json.dumps(c.datos, default=str)[:4000], c.fuente[:200], c.accion[:300],
                     json.dumps(c.simulacion) if c.simulacion else None))
                nuevas.append({"id": cur.lastrowid, "regla": c.regla, "clave": c.clave, "titulo": c.titulo,
                               "severidad": c.severidad, "motivo": c.motivo, "accion": c.accion})
    if nuevas and notificar:
        abierto = vigencia.mercado_abierto("XMEX", ahora_dt)
        if cfg.get("silenciar_fuera_de_horario", True) and not abierto:
            marca = "silenciada_fuera_de_horario"
        else:
            titulo = nuevas[0]["titulo"] if len(nuevas) == 1 else f"{len(nuevas)} alertas nuevas"
            texto = " · ".join(a["titulo"] for a in nuevas[:3]) + (" …" if len(nuevas) > 3 else "")
            marca = json.dumps(notificador.enviar(titulo, texto, cfg, detalle=notificador.detalle(nuevas)))
        with transaccion(con):
            con.executemany("UPDATE alertas SET notificada=? WHERE id=?", [(marca, a["id"]) for a in nuevas])
    return nuevas


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
             + reglas_tecnicas(con, cfg, cartera, propuestas, mercado.ultimo_fx(con, ajustes)))
    return procesar(con, conds, cfg, ahora_dt, notificar)


def listar(con: sqlite3.Connection, limite: int = 200) -> list[dict]:
    filas = []
    for r in con.execute("SELECT * FROM alertas ORDER BY id DESC LIMIT ?", (min(limite, 1000),)):
        d = dict(r)
        d["datos"] = json.loads(d["datos"] or "{}")
        d["simulacion"] = json.loads(d["simulacion"]) if d["simulacion"] else None
        filas.append(d)
    return filas


def marcar(con: sqlite3.Connection, aid: int, estado: str) -> None:
    if estado not in ("vista", "descartada", "nueva"):
        raise ValueError("estado no válido")
    with transaccion(con):
        con.execute("UPDATE alertas SET estado=? WHERE id=?", (estado, aid))


def pendientes(con: sqlite3.Connection) -> int:
    return int(con.execute("SELECT COUNT(*) FROM alertas WHERE estado='nueva'").fetchone()[0])
