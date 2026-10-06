"""Casos de uso compartidos por la API y el motor automático."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import sqlite3
import threading
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import alertas, cartera, db, ingesta, mercado, optimizador, reto, vigencia
from .config import Ajustes

log = logging.getLogger("terminal.servicios")
COMBINACIONES = [(t, lente) for t in ("acciones", "mixta") for lente in ("rendimiento", "ajuste", "puntuacion")]
# Con el perfil en «ambos», la lente de máxima puntuación se calcula además por separado para cada mercado
VARIANTES_MERCADO = {"nacionales": "Solo nacionales (BMV)", "extranjeras": "Solo extranjeras (SIC)"}


def claves_variantes(perfil: dict) -> list[tuple[str, str]]:
    if perfil.get("mercado_acciones", "ambos") != "ambos":
        return []
    return [(t, m) for t in ("acciones", "mixta") for m in VARIANTES_MERCADO]
bloqueo = threading.Lock()  # un solo cálculo/actualización a la vez (API y motor)


# --------------------------------------------------------------------------------------------------------------
def perfil_actual(con, ajustes: Ajustes) -> dict:
    fila = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='perfil'").fetchone()
    base = dict(ajustes["perfil"])
    return {**base, **json.loads(fila["valor"])} if fila else base


def operaciones_etapa(con, ahora=None) -> tuple[list[dict], str | None]:
    """Operaciones CONFIRMADAS de la cartera que se monitorea. En la práctica o la competencia del Reto se usan solo las
    de esa etapa, con el saldo inicial de 1,000,000 actipesos si no se registró una aportación (la competencia reinicia
    el saldo). Si la etapa aún no tiene operaciones, se muestra el historial completo (seguimiento personal)."""
    tx = [t for t in cartera.listar(con) if t.get("confirmada", 1)]
    etapa = reto.etapa_operativa(ahora) if reto.activo() else None
    propias = [t for t in tx if etapa and (t.get("etapa") or reto.etapa_de_fecha(t["fecha"])) == etapa]
    if not propias:
        return tx, None
    if not any(t["tipo"] == "aportacion" for t in propias):
        capital = float(reto.config().get("capital") or 0)
        propias = [{"id": 0, "fecha": reto.inicio_etapa(etapa), "tipo": "aportacion", "instrumento_id": None,
                    "cantidad": 0, "precio": 0, "monto": capital, "comision": 0, "impuesto": 0, "moneda": "MXN",
                    "tipo_cambio": 1, "nota": "Saldo inicial del Reto (implícito)", "origen": "reto_saldo_inicial"}] + propias
    return propias, etapa


def captura_vigente(con) -> dict | None:
    """Última captura del portal de la etapa actual, si es posterior a la última operación registrada a mano.
    Si después de capturar se registró una operación local, manda el registro local hasta la siguiente captura."""
    from . import portal
    c = portal.captura(con)
    if not c:
        return None
    etapa = reto.etapa_operativa() if reto.activo() else None
    if etapa and c.get("etapa") and c["etapa"] != etapa:
        return None
    ultima_local = con.execute("SELECT MAX(creado_en) FROM transacciones WHERE anulada=0 AND tipo IN ('compra','venta')").fetchone()[0]
    return None if (ultima_local and ultima_local > c["capturado_en"]) else c


def cartera_actual(con, ajustes: Ajustes, solo_local: bool = False) -> dict:
    from . import portal
    tx, etapa_cartera = operaciones_etapa(con)
    c = None if solo_local else captura_vigente(con)
    ids = sorted({t["instrumento_id"] for t in tx if t["instrumento_id"]} | {p["instrumento_id"] for p in (c or {}).get("posiciones", [])})
    cot = mercado.cotizaciones(con, ajustes, ids) if ids else {}
    precios = {i: (q["precio_mxn"] if q.get("estado") not in ("sin_datos",) else None) for i, q in cot.items()}
    if c:
        res = portal.cartera(con, cot, c)
        res.update(fuente="portal", captura={k: c.get(k) for k in ("id", "hora_portal", "capturado_en", "valor_portafolio",
                                                                    "efectivo", "por_liquidar", "invertido", "fuente",
                                                                    "n_posiciones")})
    else:
        res = cartera.calcular(tx, precios)
        res.update(fuente="local", captura=None, por_liquidar=0.0)
    for p in res["posiciones"] + res["cerradas"]:
        q = cot.get(p["instrumento_id"], {})
        p.update({"clave_operable": q.get("clave_operable"), "clase": q.get("clase"), "vigencia": q.get("estado"),
                  "etiqueta_vigencia": q.get("etiqueta"), "fecha_precio": q.get("fecha"), "proveedor": q.get("proveedor"),
                  "tipo_dato": q.get("tipo_dato"), "bolsa": q.get("bolsa")})
    estados = [p["vigencia"] for p in res["posiciones"] if p.get("vigencia")]
    res["vigencia"] = vigencia.peor(estados) if estados else ("sin_datos" if res["posiciones"] else "vigente")
    res["n_operaciones"] = len([t for t in tx if t.get("origen") != "reto_saldo_inicial"]) + (1 if c else 0)
    res["etapa"] = etapa_cartera
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
    tx, _ = operaciones_etapa(con)
    if res.get("fuente") == "portal":  # el registro local se muestra aparte, rotulado como tal
        loc = cartera_actual(con, ajustes, solo_local=True)
        res["registro_local"] = {k: loc.get(k) for k in ("valor_total", "efectivo", "aportacion_neta", "n_operaciones")}
        return {**res, "historia": [], "referencias": [], "max_caida": None}
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
# Código y configuración que determinan una propuesta. Si cambian, las propuestas guardadas dejan de ser actuales.
ARCHIVOS_CALCULO = ("optimizador.py", "servicios.py", "mercado.py", "portal.py", "reto.py", "vigencia.py")
SECCIONES_CALCULO = ("optimizacion", "perfiles", "costos", "puntuacion", "vigencia")
_huella_codigo: str | None = None


def huella_calculo(ajustes: Ajustes) -> str:
    """Huella (sha256 corta) del código del cálculo, las reglas del Reto y la configuración que lo afecta."""
    global _huella_codigo
    if _huella_codigo is None:  # el código no cambia mientras el proceso vive: se lee una vez
        h = hashlib.sha256()
        base = Path(__file__).parent
        for nombre in ARCHIVOS_CALCULO:
            h.update((base / nombre).read_bytes())
        reglas = base.parent / "config" / "reto.yaml"
        if reglas.exists():
            h.update(reglas.read_bytes())
        _huella_codigo = h.hexdigest()
    conf = json.dumps({k: ajustes.get(k) for k in SECCIONES_CALCULO}, sort_keys=True, default=str)
    return hashlib.sha256((_huella_codigo + conf).encode()).hexdigest()[:16]


def huella_catalogo(con) -> str:
    """Huella del catálogo importado del simulador: al cambiar, las propuestas se recalculan con el universo nuevo."""
    ids = [r[0] for r in con.execute("SELECT id FROM universo_simulador ORDER BY id")]
    return hashlib.sha256("|".join(ids).encode()).hexdigest()[:16] if ids else "sin_catalogo"


def _revisar_catalogo(con, p: dict | None) -> dict | None:
    if p and p.get("estado") == "calculada" and p.get("catalogo_simulador", "sin_catalogo") != huella_catalogo(con):
        p["avisos"] = [*p.get("avisos", []), "El catálogo del simulador cambió desde el cálculo: se recalculará en el próximo ciclo."]
        p["recalcular"] = True
    return p


def revalidar(p: dict, perfil: dict, ajustes: Ajustes) -> dict:
    """Una propuesta guardada nunca se presenta como actual si cambiaron sus datos, el perfil, el código o la
    configuración del cálculo. «recalcular» indica que un nuevo cálculo lo resuelve (el motor lo hace solo)."""
    avisos, recalcular = [], False
    if p.get("estado") in ("calculada", "demostracion"):
        if p.get("huella_calculo") != huella_calculo(ajustes):
            avisos.append("El cálculo de la terminal se actualizó desde esta propuesta: se recalculará en el próximo ciclo.")
            recalcular = True
        if p.get("perfil") != perfil:
            avisos.append("El perfil cambió desde el cálculo: se recalculará en el próximo ciclo.")
            recalcular = True
        if p["estado"] == "calculada" and p.get("datos_hasta"):
            atraso = vigencia.sesiones_de_atraso("XNYS", date.fromisoformat(p["datos_hasta"]),
                                                 vigencia.ultima_sesion_cerrada("XNYS"))
            if atraso > ajustes["vigencia"]["cierre_sesiones_retrasado"]:
                avisos.append(f"Calculada con datos al {p['datos_hasta']} ({atraso} sesiones de atraso): no es actual.")
                p = {**p, "estado": "desactualizada"}
                recalcular = True
    return {**p, "avisos": avisos, "recalcular": recalcular}


def bloqueo_cartera(actual: dict) -> str | None:
    """Motivo para no usar una propuesta: la cuenta del Reto capturada tiene posiciones sin precio."""
    if actual.get("fuente") == "portal" and not actual.get("completa", True):
        return (f"Bloqueada: la captura del portal tiene posiciones sin precio ({', '.join(actual.get('sin_precio') or [])}); "
                "los cambios sugeridos no se pueden verificar. Pegue una captura con precio o espere a que se carguen.")
    return None


MARGEN_CAMBIO_CENTRAL = 0.02    # criterio «plusvalía»: la nueva debe mejorar el escenario central ≥ 2 puntos
MARGEN_CAMBIO_PUNTUACION = 5.0  # criterio «puntuación»: ≥ 5 puntos de puntuación


def _valida(p: dict | None) -> bool:
    return bool(p and not p.get("mercado_variante") and p.get("estado") == "calculada" and not p.get("avisos")
                and p.get("puntuacion"))


def _fijar_referencia(con, ajustes: Ajustes, perfil: dict, out: dict) -> str | None:
    """Plan del día estable. Las estimaciones cambian con cada precio en vivo; elegir siempre el máximo hacía saltar el
    plan entre carteras distintas por diferencias de ruido (5-oct-2026: +0.9 % vs +1.3 % de escenario central).
    - Misma sesión: se conserva la propuesta (la misma versión guardada) elegida al inicio, mientras siga siendo válida
      y no cambie el criterio del perfil.
    - Sesión nueva (o la misma antes de la apertura, cuando aún no se pudo operar): se cambia de propuesta solo si la
      mejor supera a la anterior por un margen claro (2 puntos de escenario central o 5 de puntuación) o si la domina
      (más escenario central y al menos 2 puntos menos de pérdida en el escenario adverso; 6-oct-2026: +0.9 %/−19.7 %
      frente a +1.6 %/−5.9 %); si no, se conserva la anterior con su versión más reciente."""
    from . import resumen
    nueva = resumen.propuesta_referencia(out)
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='referencia_plan'").fetchone()
    previa = json.loads(f[0]) if f else None
    sesion = resumen.sesion_objetivo(datetime.now(UTC)).isoformat()
    criterio = resumen.criterio_plan(out)
    elegido, motivo = None, None
    if previa and previa.get("criterio") == criterio and previa.get("clave") in out:
        abierta = datetime.now(UTC) >= resumen.apertura(date.fromisoformat(sesion))
        if previa.get("sesion") == sesion and not abierta:
            if not _valida(out.get(previa["clave"])) and (out.get(previa["clave"]) or {}).get("recalcular"):
                return None
        if previa.get("sesion") == sesion and abierta:
            fila = con.execute("SELECT resultado FROM propuestas WHERE id=?", (previa.get("id"),)).fetchone()
            p = _revisar_catalogo(con, revalidar({**json.loads(fila[0]), "id_registro": previa["id"]}, perfil, ajustes)) if fila else None
            if _valida(p):
                out[previa["clave"]] = p
                elegido, motivo = previa["clave"], "Plan del día fijado al inicio de la sesión (no cambia con cada precio en vivo)."
            elif _valida(out.get(previa["clave"])):  # la versión fijada caducó (p. ej. recálculo): misma propuesta, versión nueva
                elegido, motivo = previa["clave"], ("Plan del día: misma propuesta de la sesión, recalculada (la versión anterior "
                                                    "dejó de ser válida).")
            elif (out.get(previa["clave"]) or {}).get("recalcular"):
                return None  # se está recalculando: el plan espera a esa misma propuesta en vez de saltar a otra
        elif _valida(out.get(previa["clave"])) and nueva:
            ant, nva = out[previa["clave"]], nueva
            if criterio in ("plusvalia", "ganancia"):
                ea, en = ant.get("escenarios") or {}, nva.get("escenarios") or {}
                mejora = (resumen.metrica_plan(nva, criterio) or 0) - (resumen.metrica_plan(ant, criterio) or 0)
                domina = (mejora > 0 and en.get("adverso_p10") is not None and ea.get("adverso_p10") is not None
                          and en["adverso_p10"] - ea["adverso_p10"] >= MARGEN_CAMBIO_CENTRAL)
                cambia = mejora >= MARGEN_CAMBIO_CENTRAL or domina
            else:
                cambia = nva["puntuacion"]["total"] - ant["puntuacion"]["total"] >= MARGEN_CAMBIO_PUNTUACION
            if not cambia:
                elegido, motivo = previa["clave"], ("Se conserva la propuesta anterior: ninguna otra la supera por un margen "
                                                    "claro (diferencias menores son ruido de estimación).")
    if elegido is None and nueva:
        elegido = next(k for k, v in out.items() if v is nueva)
        motivo = "Propuesta elegida por el criterio del perfil al inicio de la sesión."
    if elegido is None:
        return None
    p = out[elegido]
    p["referencia_fijada"], p["motivo_referencia"] = True, motivo
    estado = {"sesion": sesion, "clave": elegido, "id": p.get("id_registro"), "criterio": criterio,
              "central": (p.get("escenarios") or {}).get("central_p50"), "puntuacion": p["puntuacion"]["total"]}
    if not previa or any(previa.get(k) != estado[k] for k in ("sesion", "clave", "id", "criterio")):
        with db.transaccion(con):
            con.execute("INSERT INTO ajustes_usuario VALUES ('referencia_plan', ?, ?) ON CONFLICT(clave) DO UPDATE SET "
                        "valor=excluded.valor, actualizado_en=excluded.actualizado_en", (json.dumps(estado), db.ahora()))
    return elegido


def propuestas_guardadas(con, ajustes: Ajustes, perfil: dict) -> dict:
    out = {}
    actual = None
    for tipo, lente in COMBINACIONES:
        clave = f"{tipo}_{lente}"
        f = con.execute("SELECT id, resultado FROM propuestas WHERE tipo=? ORDER BY id DESC LIMIT 1", (clave,)).fetchone()
        out[clave] = _revisar_catalogo(con, revalidar({**json.loads(f["resultado"]), "id_registro": f["id"]}, perfil, ajustes)
                                       if f else None)
        if out[clave] and "advertencias_reto" not in out[clave]:
            actual = actual or cartera_actual(con, ajustes)
            advertir_compras(out[clave], actual)
    fija = _fijar_referencia(con, ajustes, perfil, out)
    if fija and "advertencias_reto" not in out[fija]:
        actual = actual or cartera_actual(con, ajustes)
        advertir_compras(out[fija], actual)
    for tipo, m in claves_variantes(perfil):
        clave = f"{tipo}_puntuacion_{m}"
        f = con.execute("SELECT resultado FROM propuestas WHERE tipo=? ORDER BY id DESC LIMIT 1", (clave,)).fetchone()
        out[clave] = _revisar_catalogo(con, revalidar(json.loads(f["resultado"]), perfil, ajustes) if f else None)
        if out[clave] and "advertencias_reto" not in out[clave]:
            actual = actual or cartera_actual(con, ajustes)
            advertir_compras(out[clave], actual)
    actual = actual or cartera_actual(con, ajustes)
    motivo = bloqueo_cartera(actual)
    if motivo:
        for p in out.values():
            if p and motivo not in p.get("avisos", []):
                p["avisos"] = [*p.get("avisos", []), motivo]
    return out


def calcular_propuestas(con, ajustes: Ajustes) -> dict:
    perfil = perfil_actual(con, ajustes)
    actual = cartera_actual(con, ajustes)
    ids = [i for i, v in mercado.instrumentos(con).items() if v["estado"] == "activo"]
    cot = mercado.cotizaciones(con, ajustes, ids)
    res = {}
    for tipo, lente in COMBINACIONES:
        p = optimizador.proponer(con, ajustes, perfil, tipo, actual, cot, lente=lente)
        p["huella_calculo"] = huella_calculo(ajustes)
        p["catalogo_simulador"] = huella_catalogo(con)
        js = json.dumps(p, default=str)
        with db.transaccion(con):
            con.execute("INSERT INTO propuestas (tipo, creado_en, parametros, resultado) VALUES (?,?,?,?)",
                        (p["clave"], p["calculado_en"], json.dumps(perfil), js))
        res[p["clave"]] = revalidar(json.loads(js), perfil, ajustes)
    for tipo, m in claves_variantes(perfil):
        p = optimizador.proponer(con, ajustes, {**perfil, "mercado_acciones": m}, tipo, actual, cot, lente="puntuacion")
        p.update({"clave": f"{tipo}_puntuacion_{m}", "nombre": f"{p['nombre']} · {VARIANTES_MERCADO[m]}",
                  "mercado_variante": m, "perfil": perfil})  # el perfil del usuario sigue en «ambos»
        p["huella_calculo"] = huella_calculo(ajustes)
        p["catalogo_simulador"] = huella_catalogo(con)
        js = json.dumps(p, default=str)
        with db.transaccion(con):
            con.execute("INSERT INTO propuestas (tipo, creado_en, parametros, resultado) VALUES (?,?,?,?)",
                        (p["clave"], p["calculado_en"], json.dumps(perfil), js))
        res[p["clave"]] = revalidar(json.loads(js), perfil, ajustes)
    for p in res.values():
        advertir_compras(p, actual)
    return res


def advertir_compras(p: dict, actual: dict) -> dict:
    """Antes de presentar una propuesta: ¿alguna compra de una sola acción excede el 50 % del portafolio?"""
    if not p or not reto.activo():
        return p
    filas = ((p.get("cambios") or {}).get("filas")) or []
    compras = [{"id": f["id"], "monto": f.get("monto_mxn") or 0} for f in filas if (f.get("monto_mxn") or 0) > 0]
    if not filas:  # sin cartera registrada: la compra inicial es toda la asignación
        compras = [{"id": a["id"], "monto": a.get("monto_estimado") or a.get("monto_objetivo") or 0} for a in p.get("pesos") or []]
    valor = float(actual.get("valor_total") or 0) or float(p.get("capital") or 0)
    pos = {x["instrumento_id"]: float(x.get("valor_mxn") or 0) for x in actual.get("posiciones", [])}
    p["advertencias_reto"] = reto.verificar_compras(compras, valor, pos)
    return p


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
            "avisos": avisos, "advertencias_reto": reto.verificar_compras(
                [{"id": c["id"], "monto": c["monto"]} for c in cambios if float(c["monto"]) > 0],
                float(actual["valor_total"] or 0), {p["instrumento_id"]: float(p["valor_mxn"] or 0) for p in actual["posiciones"]})
            if reto.activo() else [],
            "costos_detalle": [reto.costo_detalle(d["importe"]) | {"id": d["id"]} for d in detalle],
            "nota": "Simulación con el último precio disponible y costos estimados; no envía órdenes."}


# --------------------------------------------------------------------------------------------------------------
def estado_motor(con) -> dict:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='motor'").fetchone()
    return json.loads(f["valor"]) if f else {}


def ids_propuestas(props: dict) -> list[str]:
    """Instrumentos de las propuestas guardadas, primero los de la mejor puntuada y por peso."""
    from . import resumen
    ref = resumen.propuesta_referencia(props)
    orden = [a["id"] for a in sorted((ref or {}).get("pesos") or [], key=lambda a: -a["peso"])]
    for p in props.values():
        orden += [a["id"] for a in (p or {}).get("pesos") or []]
    return list(dict.fromkeys(orden))


def ciclo(con: sqlite3.Connection, ajustes: Ajustes, forzar: bool = False, notificar: bool = True,
          en_vivo: bool = False) -> dict:
    """Adquisición → propuesta → alertas. Recalcula solo si hay datos nuevos, cambió el perfil o se fuerza.
    `en_vivo`: lo dispara el flujo de precios en vivo; no consulta proveedores (los precios nuevos ya están en la base)."""
    inicio = datetime.now(UTC)
    cart = cartera_actual(con, ajustes)
    prio = [p["instrumento_id"] for p in cart["posiciones"]]
    perfil = perfil_actual(con, ajustes)
    props = propuestas_guardadas(con, ajustes, perfil)
    ids_prop = ids_propuestas(props)
    act = {"nuevos": 0} if en_vivo else ingesta.actualizar_todo(con, ajustes, prio, forzar_demo=False, contexto=True,
                                                                ids_propuesta=ids_prop)
    motivo = ("precios en vivo" if en_vivo else "forzado" if forzar else "datos nuevos" if act.get("nuevos") else
              "sin propuestas" if any(v is None for v in props.values()) else
              "código, configuración, perfil o datos cambiaron" if any(v and v.get("recalcular") for v in props.values())
              else "")
    if motivo:
        props = calcular_propuestas(con, ajustes)
    cart = cartera_actual(con, ajustes)
    try:
        from .investigacion import pronosticos
        pronosticos.resolver(con, ajustes.es_demo)  # añade resultados observados a pronósticos vencidos
        if not en_vivo and (ajustes.get("investigacion") or {}).get("emitir_diario", True):
            from .investigacion import reto_pronostico
            reto_pronostico.emitir_si_toca(ajustes, (ajustes.get("investigacion") or {}).get("horizontes", [1, 5]))
    except Exception:  # noqa: BLE001 - la investigación nunca detiene el monitor
        log.exception("no se pudieron resolver pronósticos")
    nuevas = alertas.evaluar(con, ajustes, cart, props, notificar=notificar)
    estado = {"ultimo_ciclo": inicio.isoformat(timespec="seconds"), "duracion_s": round((datetime.now(UTC) - inicio).total_seconds(), 1),
              "recalculo": motivo or "no necesario", "nuevos_datos": act.get("nuevos", 0), "alertas_nuevas": len(nuevas),
              "contexto": {k: v.get("estado") for k, v in (act.get("contexto") or {}).items()}}
    with db.transaccion(con):
        con.execute("INSERT INTO ajustes_usuario VALUES ('motor', ?, ?) ON CONFLICT(clave) DO UPDATE SET "
                    "valor=excluded.valor, actualizado_en=excluded.actualizado_en", (json.dumps(estado), db.ahora()))
    return estado


_ultima_revision_plan: datetime | None = None


def resumen_seguro(ajustes: Ajustes) -> dict | None:
    """Plan del día por Telegram (una vez por sesión hábil, desde la hora configurada). Lo revisa el programador."""
    from . import resumen
    try:
        con = db.conectar()
        try:
            ahora = datetime.now(UTC)
            estado = resumen._estado(con)
            obj = resumen.sesion_objetivo(ahora).isoformat()
            if estado.get("fecha") == obj and (resumen.entregado(estado) or int(estado.get("intentos", 1)) >= resumen.MAX_INTENTOS):
                if not (resumen.puede_corregir(estado, ahora)
                        and estado.get("propuestas_max_id") != resumen.ultima_propuesta_id(con)):
                    return None  # ya enviado y sin recálculo posterior: comprobación barata cada 15 s
            global _ultima_revision_plan
            if _ultima_revision_plan and (ahora - _ultima_revision_plan).total_seconds() < 120:
                return None  # a lo sumo una evaluación completa cada 2 minutos mientras se espera
            _ultima_revision_plan = ahora
            with bloqueo:  # no convive con un cálculo en curso
                perfil = perfil_actual(con, ajustes)
                return resumen.enviar_si_toca(con, ajustes, cartera_actual(con, ajustes),
                                              propuestas_guardadas(con, ajustes, perfil))
        finally:
            con.close()
    except Exception:  # noqa: BLE001 - el resumen nunca detiene el monitor
        log.exception("no se pudo enviar el plan del día")
        return None


def ciclo_seguro(ajustes: Ajustes, forzar: bool = False, en_vivo: bool = False) -> dict | None:
    """Ejecuta un ciclo si no hay otro en curso (lo usan el programador y los disparadores de la API)."""
    if not bloqueo.acquire(blocking=False):
        return None
    try:
        con = db.conectar()
        try:
            db.inicializar(con)
            if not ajustes.es_demo:
                try:
                    db.respaldo_diario()  # un respaldo verificado al día (data/respaldos, 14 copias)
                except Exception:  # noqa: BLE001 - un respaldo fallido se registra, no detiene el ciclo
                    log.exception("respaldo diario")
            return ciclo(con, ajustes, forzar=forzar, en_vivo=en_vivo)
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        log.exception("fallo en ciclo del motor")
        return None
    finally:
        bloqueo.release()
