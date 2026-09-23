"""Casos de uso compartidos por la API y el motor automático."""
from __future__ import annotations

import json
import logging
import math
import sqlite3
import threading
from datetime import UTC, date, datetime

import numpy as np
import pandas as pd

from . import alertas, cartera, db, ingesta, mercado, optimizador, reto, vigencia
from .config import Ajustes

log = logging.getLogger("terminal.servicios")
COMBINACIONES = [(t, lente) for t in ("acciones", "mixta") for lente in ("rendimiento", "ajuste")]
bloqueo = threading.Lock()  # un solo cálculo/actualización a la vez (API y motor)


# --------------------------------------------------------------------------------------------------------------
def perfil_actual(con, ajustes: Ajustes) -> dict:
    fila = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='perfil'").fetchone()
    base = dict(ajustes["perfil"])
    return {**base, **json.loads(fila["valor"])} if fila else base


def cartera_actual(con, ajustes: Ajustes) -> dict:
    tx = cartera.listar(con)
    ids = sorted({t["instrumento_id"] for t in tx if t["instrumento_id"]})
    cot = mercado.cotizaciones(con, ajustes, ids) if ids else {}
    precios = {i: (q["precio_mxn"] if q.get("estado") not in ("sin_datos",) else None) for i, q in cot.items()}
    res = cartera.calcular(tx, precios)
    for p in res["posiciones"] + res["cerradas"]:
        q = cot.get(p["instrumento_id"], {})
        p.update({"clave_operable": q.get("clave_operable"), "clase": q.get("clase"), "vigencia": q.get("estado"),
                  "etiqueta_vigencia": q.get("etiqueta"), "fecha_precio": q.get("fecha"), "proveedor": q.get("proveedor"),
                  "tipo_dato": q.get("tipo_dato"), "bolsa": q.get("bolsa")})
    estados = [p["vigencia"] for p in res["posiciones"] if p.get("vigencia")]
    res["vigencia"] = vigencia.peor(estados) if estados else ("sin_datos" if res["posiciones"] else "vigente")
    res["n_operaciones"] = len(tx)
    res["costo_comisiones_con_iva"] = res["comisiones"]
    if reto.activo():
        res["cumplimiento_reto"] = reto.cumplimiento({p["instrumento_id"]: (p["peso"] or 0) for p in res["posiciones"]})
    return res


def _serie_referencia(con, ajustes: Ajustes, iid: str, indice: pd.DatetimeIndex) -> pd.Series | None:
    p = mercado.precios_mxn(con, ajustes, [iid])
    if iid not in p.columns:
        return None
    s = p[iid].reindex(p.index.union(indice)).ffill(limit=5).reindex(indice)
    return None if s.notna().sum() < 2 else s


def seguimiento(con, ajustes: Ajustes) -> dict:
    """Cartera + curva de valor, rendimiento ponderado por tiempo, caída desde máximo y referencias."""
    res = cartera_actual(con, ajustes)
    tx = cartera.listar(con)
    ids = sorted({t["instrumento_id"] for t in tx if t["instrumento_id"]})
    res.update(historia=[], referencias=[], max_caida=None)
    if not tx:
        return res
    precios = mercado.precios_mxn(con, ajustes, ids, ajustados=False) if ids else pd.DataFrame()
    if precios.empty:
        fechas = vigencia.calendario("XMEX").sessions_in_range(pd.Timestamp(tx[0]["fecha"]), pd.Timestamp(date.today()))
        precios = pd.DataFrame(index=pd.DatetimeIndex(fechas))
    serie = cartera.serie_historica(tx, precios)
    if serie.empty:
        return res
    indice = (1 + serie["twr_acumulado"])
    serie["caida"] = indice / indice.cummax() - 1
    ref_cfg = ajustes.get("referencias") or {}
    refs = {}
    for nombre, iid in (("S&P/BMV IPC (ACTIVAR)", ref_cfg.get("ipc")), ("S&P 500 (IVV en MXN)", ref_cfg.get("sp500"))):
        s = _serie_referencia(con, ajustes, iid, serie.index) if iid else None
        refs[nombre] = (iid, s)
    ipc, deuda = refs["S&P/BMV IPC (ACTIVAR)"][1], _serie_referencia(con, ajustes, ref_cfg.get("deuda", ""), serie.index)
    if ipc is not None and deuda is not None:
        w = ref_cfg.get("pesos_60_40", [0.6, 0.4])
        r = w[0] * ipc.pct_change(fill_method=None) + w[1] * deuda.pct_change(fill_method=None)
        refs["60/40 (IPC + deuda gubernamental)"] = ("60/40", (1 + r.fillna(0)).cumprod())
    else:
        refs["60/40 (IPC + deuda gubernamental)"] = ("60/40", None)
    for nombre, (iid, s) in refs.items():
        if s is None:
            res["referencias"].append({"nombre": nombre, "id": iid, "rend_acumulado": None,
                                       "nota": "Sin datos suficientes (importe NAV o configure proveedor)"})
            continue
        base = s.dropna().iloc[0]
        serie[nombre] = s / base - 1
        res["referencias"].append({"nombre": nombre, "id": iid, "rend_acumulado": float(serie[nombre].dropna().iloc[-1])})
    res["historia"] = [{"fecha": d.date().isoformat(), "valor": round(float(f["valor"]), 2),
                        "twr": round(float(f["twr_acumulado"]), 6), "caida": round(float(f["caida"]), 6),
                        "completo": bool(f["completo"]),
                        "referencias": {n: (None if pd.isna(f.get(n, np.nan)) else round(float(f[n]), 6))
                                        for n in refs}} for d, f in serie.iterrows()][-1500:]
    res["twr_acumulado"] = float(serie["twr_acumulado"].iloc[-1])
    res["max_caida"] = float(serie["caida"].min())
    flujos = [(pd.Timestamp(t["fecha"]), -(1 if t["tipo"] == "aportacion" else -1) * t["monto"] * t["tipo_cambio"])
              for t in tx if t["tipo"] in ("aportacion", "retiro")]
    if res["completa"] and flujos:
        flujos.append((serie.index[-1], float(serie["valor"].iloc[-1])))
        res["tir_anual"] = cartera.xirr(sorted(flujos, key=lambda x: x[0]))
    return res


# --------------------------------------------------------------------------------------------------------------
def revalidar(p: dict, perfil: dict, ajustes: Ajustes) -> dict:
    """Una propuesta guardada nunca se presenta como actual si sus datos o el perfil cambiaron."""
    avisos = []
    if p.get("estado") in ("calculada", "demostracion"):
        if p.get("perfil") != perfil:
            avisos.append("El perfil cambió desde el cálculo: se recalculará en el próximo ciclo.")
        if p["estado"] == "calculada" and p.get("datos_hasta"):
            atraso = vigencia.sesiones_de_atraso("XNYS", date.fromisoformat(p["datos_hasta"]),
                                                 vigencia.ultima_sesion_cerrada("XNYS"))
            if atraso > ajustes["vigencia"]["cierre_sesiones_retrasado"]:
                avisos.append(f"Calculada con datos al {p['datos_hasta']} ({atraso} sesiones de atraso): no es actual.")
                p = {**p, "estado": "desactualizada"}
    return {**p, "avisos": avisos}


def propuestas_guardadas(con, ajustes: Ajustes, perfil: dict) -> dict:
    out = {}
    for tipo, lente in COMBINACIONES:
        clave = f"{tipo}_{lente}"
        f = con.execute("SELECT resultado FROM propuestas WHERE tipo=? ORDER BY id DESC LIMIT 1", (clave,)).fetchone()
        out[clave] = revalidar(json.loads(f["resultado"]), perfil, ajustes) if f else None
    return out


def calcular_propuestas(con, ajustes: Ajustes) -> dict:
    perfil = perfil_actual(con, ajustes)
    actual = cartera_actual(con, ajustes)
    ids = [i for i, v in mercado.instrumentos(con).items() if v["estado"] == "activo"]
    cot = mercado.cotizaciones(con, ajustes, ids)
    res = {}
    for tipo, lente in COMBINACIONES:
        p = optimizador.proponer(con, ajustes, perfil, tipo, actual, cot, lente=lente)
        js = json.dumps(p, default=str)
        with db.transaccion(con):
            con.execute("INSERT INTO propuestas (tipo, creado_en, parametros, resultado) VALUES (?,?,?,?)",
                        (p["clave"], p["calculado_en"], json.dumps(perfil), js))
        res[p["clave"]] = revalidar(json.loads(js), perfil, ajustes)
    return res


def respuesta_propuestas(props: dict) -> dict:
    presentes = [v for v in props.values() if v]
    return {"propuestas": props, "clasificacion": optimizador.clasificar(presentes, {}) if presentes else []}


# --------------------------------------------------------------------------------------------------------------
def simular(con, ajustes: Ajustes, cambios: list[dict]) -> dict:
    """Aplica en memoria compras (+MXN) y ventas (−MXN) a la cartera actual. No guarda ni envía nada."""
    actual = cartera_actual(con, ajustes)
    ins = mercado.instrumentos(con)
    ids = sorted({c["id"] for c in cambios} | {p["instrumento_id"] for p in actual["posiciones"]})
    cot = mercado.cotizaciones(con, ajustes, ids)
    valores = {p["instrumento_id"]: float(p["valor_mxn"] or 0) for p in actual["posiciones"]}
    efectivo = float(actual["efectivo"])
    detalle, avisos, costo_total = [], [], 0.0
    for c in cambios:
        iid, monto = c["id"], float(c["monto"])
        if iid not in ins:
            avisos.append(f"{iid}: no está en el universo")
            continue
        q = cot.get(iid, {})
        px = q.get("precio_mxn")
        if q.get("estado") in ("vencido", "sin_datos") or not px:
            avisos.append(f"{iid}: precio {q.get('etiqueta', 'sin datos').lower()}; no se simula")
            continue
        titulos = math.floor(abs(monto) / px)
        if monto < 0:
            titulos = min(titulos, math.floor(valores.get(iid, 0) / px + 1e-9))
        importe = titulos * px
        costo = importe * optimizador.costo_unitario(ins[iid], ajustes)
        costo_total += costo
        if monto >= 0:
            efectivo -= importe + costo
            valores[iid] = valores.get(iid, 0) + importe
        else:
            efectivo += importe - costo
            valores[iid] = valores.get(iid, 0) - importe
        detalle.append({"id": iid, "clave_operable": ins[iid]["clave_operable"], "operacion": "compra" if monto >= 0 else "venta",
                        "titulos": titulos, "precio_mxn": px, "fecha_precio": q.get("fecha"), "importe": round(importe, 2),
                        "costo": round(costo, 2)})
    total = efectivo + sum(valores.values())
    pesos = {k: v / total for k, v in valores.items() if total > 0 and v > 0.5}  # < 0.5 MXN = residuo de redondeo
    if efectivo < -1e-6:
        avisos.append("Poder de compra insuficiente: el efectivo resultante es negativo (el simulador del Reto lo rechazaría).")
    return {"operaciones": detalle, "efectivo_resultante": round(efectivo, 2), "valor_total": round(total, 2),
            "costo_total": round(costo_total, 2), "pesos": {k: round(v, 4) for k, v in sorted(pesos.items(), key=lambda x: -x[1])},
            "emisoras": len(pesos), "cumplimiento_reto": reto.cumplimiento(pesos) if reto.activo() else [],
            "avisos": avisos, "nota": "Simulación con el último precio disponible y costos estimados; no envía órdenes."}


# --------------------------------------------------------------------------------------------------------------
def estado_motor(con) -> dict:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='motor'").fetchone()
    return json.loads(f["valor"]) if f else {}


def ciclo(con: sqlite3.Connection, ajustes: Ajustes, forzar: bool = False, notificar: bool = True,
          en_vivo: bool = False) -> dict:
    """Adquisición → propuesta → alertas. Recalcula solo si hay datos nuevos, cambió el perfil o se fuerza.
    `en_vivo`: lo dispara el flujo de precios en vivo; no consulta proveedores (los precios nuevos ya están en la base)."""
    inicio = datetime.now(UTC)
    cart = cartera_actual(con, ajustes)
    prio = [p["instrumento_id"] for p in cart["posiciones"]]
    act = {"nuevos": 0} if en_vivo else ingesta.actualizar_todo(con, ajustes, prio, forzar_demo=False, contexto=True)
    perfil = perfil_actual(con, ajustes)
    props = propuestas_guardadas(con, ajustes, perfil)
    motivo = ("precios en vivo" if en_vivo else "forzado" if forzar else "datos nuevos" if act.get("nuevos") else
              "sin propuestas" if any(v is None for v in props.values()) else
              "perfil o datos cambiaron" if any(v and v.get("avisos") for v in props.values()) else "")
    if motivo:
        props = calcular_propuestas(con, ajustes)
    cart = cartera_actual(con, ajustes)
    nuevas = alertas.evaluar(con, ajustes, cart, props, notificar=notificar)
    estado = {"ultimo_ciclo": inicio.isoformat(timespec="seconds"), "duracion_s": round((datetime.now(UTC) - inicio).total_seconds(), 1),
              "recalculo": motivo or "no necesario", "nuevos_datos": act.get("nuevos", 0), "alertas_nuevas": len(nuevas),
              "contexto": {k: v.get("estado") for k, v in (act.get("contexto") or {}).items()}}
    with db.transaccion(con):
        con.execute("INSERT INTO ajustes_usuario VALUES ('motor', ?, ?) ON CONFLICT(clave) DO UPDATE SET "
                    "valor=excluded.valor, actualizado_en=excluded.actualizado_en", (json.dumps(estado), db.ahora()))
    return estado


def ciclo_seguro(ajustes: Ajustes, forzar: bool = False, en_vivo: bool = False) -> dict | None:
    """Ejecuta un ciclo si no hay otro en curso (lo usan el programador y los disparadores de la API)."""
    if not bloqueo.acquire(blocking=False):
        return None
    try:
        con = db.conectar()
        try:
            db.inicializar(con)
            return ciclo(con, ajustes, forzar=forzar, en_vivo=en_vivo)
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        log.exception("fallo en ciclo del motor")
        return None
    finally:
        bloqueo.release()
