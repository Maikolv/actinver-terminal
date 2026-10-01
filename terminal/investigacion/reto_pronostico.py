"""Pronóstico al cierre del Reto (además de 1 y 5 sesiones) y su barrera frente a las decisiones.

- Horizonte dinámico: sesiones de la BMV desde la última sesión cerrada hasta el cierre de la competencia.
- Todo en pesos: los precios del SIC se convierten con el tipo de cambio ya publicado a la hora de emisión
  (`datos.precios_hasta(..., mxn=True)`), así que el rendimiento estimado incluye el riesgo cambiario.
- Barrera: el pronóstico solo puede influir en compras, ventas o boletas si, en la prueba final intacta y después de
  costos, supera a «sin cambio», a pesos iguales y a la estrategia actual (media histórica, como el optimizador), con
  error significativamente menor. Si no, se muestra «señal experimental: sin ventaja demostrada» y el plan sigue el
  método actual. Ningún módulo de decisión (plan, boletas, optimizador) lee esta tabla mientras la barrera esté cerrada.
- Los rangos son estimaciones con el error histórico de validación; no son cotizaciones ni hechos.
"""
from __future__ import annotations

import logging
import math
import os
import sqlite3
import threading
from datetime import UTC, date, datetime

import pandas as pd

from . import evaluacion, pronosticos

log = logging.getLogger("terminal.pronostico")

LEYENDA_SIN_VENTAJA = "señal experimental: sin ventaja demostrada"
LEYENDA_CON_VENTAJA = "ventaja fuera de muestra verificada (después de costos)"
SESIONES_VENCIDO = 2        # base con más sesiones de atraso: el pronóstico de esa emisora no se usa
MIN_REBALANCEOS = 3         # la prueba final debe tener al menos 3 periodos sin traslape del horizonte
AVISO = ("ESTIMACIONES con incertidumbre, emitidas con datos disponibles a la hora de emisión. El precio base es el último "
         "cierre observado (no una cotización en vivo); en el SIC es la bolsa de EE. UU. × tipo de cambio, una referencia y "
         "nunca un precio ejecutable del SIC.")


def horizonte_reto(desde: date | None = None, ahora: datetime | None = None) -> dict:
    """Sesiones de la BMV después de `desde` (por omisión, la última sesión cerrada) hasta el cierre del Reto, inclusive."""
    from .. import reto, vigencia
    fin_txt = (reto.config().get("fechas") or {}).get("competencia_fin")
    if not reto.activo() or not fin_txt:
        return {"H": 0, "desde": None, "hasta": None, "motivo": "No hay un Reto activo configurado."}
    fin = pd.Timestamp(fin_txt).date()
    desde = desde or vigencia.ultima_sesion_cerrada("XMEX", ahora)
    if desde >= fin:
        return {"H": 0, "desde": desde.isoformat(), "hasta": fin.isoformat(), "motivo": "El Reto ya cerró."}
    cal = vigencia.calendario("XMEX")
    H = len(cal.sessions_in_range(pd.Timestamp(desde) + pd.Timedelta(days=1), pd.Timestamp(fin)))
    return {"H": int(H), "desde": desde.isoformat(), "hasta": fin.isoformat(), "motivo": None}


def barrera(exp: dict | None, det: dict | None = None) -> dict:
    """Criterios verificables para que el pronóstico pueda influir en decisiones. Todos deben cumplirse."""
    crit: list[dict] = []

    def agregar(nombre: str, ok: bool, detalle: str) -> None:
        crit.append({"criterio": nombre, "cumple": bool(ok), "detalle": detalle})

    if not exp or exp.get("estado") != "ok":
        agregar("Experimento fuera de muestra", False, "No hay experimento válido para este horizonte.")
        return {"permitida": False, "leyenda": LEYENDA_SIN_VENTAJA, "criterios": crit}
    tabla = exp.get("prueba") or []
    mod = tabla[0] if tabla else {}
    refs = {m["modelo"]: m for m in tabla[1:]}
    estr = {e["modelo"].split(" ")[0]: e for e in exp.get("estrategias_referencia") or []}
    dm = exp.get("diebold_mariano_vs_referencias") or {}
    reb = int(mod.get("rebalanceos") or 0)
    agregar("Prueba final suficiente", reb >= MIN_REBALANCEOS,
            f"{reb} periodos sin traslape en la prueba (mínimo {MIN_REBALANCEOS}); {exp.get('dias_prueba', '—')} fechas.")
    agregar("Prueba final intacta", not exp.get("prueba_ya_vista"),
            "La prueba final ya se usó con otra configuración: el resultado no vale para decidir." if exp.get("prueba_ya_vista")
            else "Primera vez que se evalúa esta configuración en esta prueba.")
    for nombre, r in refs.items():
        p = (dm.get(nombre) or {}).get("p_valor")
        ok = mod.get("mse") is not None and r.get("mse") is not None and mod["mse"] < r["mse"] and p is not None and p < 0.05
        agregar(f"Menor error que «{nombre}»", ok,
                f"MSE {mod.get('mse', float('nan')):.3e} vs {r.get('mse', float('nan')):.3e}; Diebold-Mariano p = "
                f"{'—' if p is None else f'{p:.3f}'} (se exige < 0.05).")
    neto = mod.get("resultado_neto")
    objetivos = [("sin cambio (mantener)", (refs.get("sin_cambio") or {}).get("resultado_neto")),
                 ("pesos iguales", (estr.get("pesos_iguales") or {}).get("resultado_neto")),
                 ("estrategia actual", (estr.get("estrategia_actual") or {}).get("resultado_neto"))]
    for nombre, v in objetivos:
        ok = neto is not None and v is not None and neto > v
        agregar(f"Mejor resultado neto de costos que {nombre}", ok,
                "Referencia no evaluada en este experimento." if v is None else f"modelo {neto:+.2%} vs {v:+.2%}")
    if det and det.get("razon") is not None:
        agregar("Sin deterioro en pronósticos ya resueltos", det["razon"] < 1,
                f"error/«sin cambio» = {det['razon']:.2f} en {det['n']} pronósticos; cobertura 80 % = {det['cobertura_80']:.0%}")
    permitida = all(c["cumple"] for c in crit)
    return {"permitida": permitida, "leyenda": LEYENDA_CON_VENTAJA if permitida else LEYENDA_SIN_VENTAJA, "criterios": crit}


def emitir_todo(con: sqlite3.Connection, demo: bool, horizontes: list[int] | tuple[int, ...] = (1, 5),
                T: pd.Timestamp | None = None) -> list[dict]:
    """Emite 1 y 5 sesiones y el horizonte al cierre del Reto con la misma hora de corte T."""
    T = pd.Timestamp(T).tz_convert("UTC") if T is not None else pd.Timestamp(datetime.now(UTC))
    hr = horizonte_reto(ahora=T.to_pydatetime())
    out = []
    for H in horizontes:
        if hr["H"] and H == hr["H"]:
            continue  # mismo horizonte que el del Reto: se emite una vez, con la etiqueta «reto»
        out.append(pronosticos.emitir(con, demo, H, T))
    if hr["H"]:
        out.append(pronosticos.emitir(con, demo, hr["H"], T, etiqueta="reto", objetivo=hr["hasta"]))
    else:
        out.append({"emitidos": 0, "etiqueta": "reto", "mensaje": hr["motivo"]})
    return out


_bloqueo = threading.Lock()
HORAS_MIN_ENTRE_EMISIONES = 6


def toca_emitir(con: sqlite3.Connection, ahora: datetime | None = None) -> bool:
    """Una emisión por sesión: hay una sesión cerrada más reciente que el último cierre usado y la emisión previa tiene
    más de 6 horas (evita repetirla mientras el cierre nuevo aún no llega)."""
    from .. import vigencia
    ahora = ahora or datetime.now(UTC)
    f = con.execute("SELECT MAX(fecha_base) AS b, MAX(emitido_en) AS e FROM pronosticos WHERE etiqueta='reto'").fetchone()
    if not f or not f[1]:
        return True
    ultima = max(vigencia.ultima_sesion_cerrada("XMEX", ahora), vigencia.ultima_sesion_cerrada("XNYS", ahora))
    edad_h = (pd.Timestamp(ahora).tz_convert("UTC") - pd.Timestamp(f[1]).tz_convert("UTC")).total_seconds() / 3600
    return f[0] < ultima.isoformat() and edad_h >= HORAS_MIN_ENTRE_EMISIONES


def emitir_si_toca(ajustes, horizontes=(1, 5)) -> bool:
    """La llama el ciclo del monitor: emite en un hilo aparte (≈2–3 min, <0.5 GB) para no detener el monitor."""
    from .. import db
    if os.environ.get("TERMINAL_SIN_MOTOR"):  # pruebas y ejecuciones sin motor: nunca en segundo plano
        return False
    con = db.conectar()
    try:
        if not toca_emitir(con) or not _bloqueo.acquire(blocking=False):
            return False
    finally:
        con.close()

    def _correr():
        c = db.conectar()
        try:
            emitir_todo(c, ajustes.es_demo, list(horizontes))
        except Exception:  # noqa: BLE001 - la investigación nunca detiene el monitor
            log.exception("no se pudo emitir el pronóstico")
        finally:
            c.close()
            _bloqueo.release()
    threading.Thread(target=_correr, daemon=True, name="pronostico").start()
    return True


def _exp(con: sqlite3.Connection, H: int, demo: bool) -> dict | None:
    return evaluacion.ultimo(con, H, demo)


def por_emisora(con: sqlite3.Connection, filas: list[dict], ahora: datetime | None = None) -> list[dict]:
    """Cada emisora: precio base observado, precio estimado al objetivo y rango 10–90 % en pesos, con su vigencia."""
    from .. import mercado, vigencia
    ins = mercado.instrumentos(con)
    ultima = {c: vigencia.ultima_sesion_cerrada(c, ahora) for c in ("XMEX", "XNYS")}
    out = []
    for f in filas:
        iid = f["instrumento_id"]
        cal = pronosticos._calendario(iid)
        atraso = vigencia.sesiones_de_atraso(cal, date.fromisoformat(f["fecha_base"]), ultima[cal])
        vencido = atraso > SESIONES_VENCIDO
        pb = f.get("precio_base")
        precio = (lambda r: round(pb * math.exp(r), 4) if pb else None)  # noqa: E731
        out.append({
            "instrumento_id": iid, "clave": (ins.get(iid) or {}).get("clave_operable") or iid, "mercado": iid.split(":")[0],
            "rend_central": math.expm1(f["prediccion"]), "rend_p10": math.expm1(f["p10"]), "rend_p90": math.expm1(f["p90"]),
            "prob_subida": f["prob_subida"], "precio_base": pb, "moneda": f.get("moneda") or "original",
            "precio_central": precio(f["prediccion"]), "precio_p10": precio(f["p10"]), "precio_p90": precio(f["p90"]),
            "fecha_base": f["fecha_base"], "fecha_objetivo": f.get("fecha_objetivo"), "horizonte": f["horizonte"],
            "emitido_en": f["emitido_en"], "datos_hasta": f["datos_hasta"], "version": f["version"], "modelo": f["modelo"],
            "atraso_sesiones": atraso, "vencido": vencido,
            "estado": (f"VENCIDO: último cierre con {atraso} sesiones de atraso; no se usa" if vencido else "estimación"),
            "fuente_precio_base": ("cierre EE. UU. × tipo de cambio (referencia, no precio SIC)" if iid.startswith("SIC:")
                                   else "cierre observado"),
        })
    return sorted(out, key=lambda x: -x["rend_central"])


def cartera(cart: dict, emisoras: list[dict], capital: float | None = None) -> dict:
    """Cartera al cierre: posiciones confirmadas del portal (o el registro local, marcado como NO conciliado).
    El rango suma los percentiles de cada posición (supone que todas se mueven juntas): es conservador, no la
    distribución de la cartera. Las posiciones sin pronóstico utilizable se mantienen a su valor actual y se listan."""
    mapa = {e["instrumento_id"]: e for e in emisoras if not e["vencido"]}
    conciliada = cart.get("fuente") == "portal"
    pos_total = sum(float(p.get("valor_mxn") or 0) for p in cart.get("posiciones") or [])
    resto = float(cart.get("valor_total") or 0) - pos_total  # efectivo + movimientos por liquidar
    c50 = c10 = c90 = resto
    filas, sin = [], []
    for p in cart.get("posiciones") or []:
        v = p.get("valor_mxn")
        iid = p["instrumento_id"]
        if v is None:
            sin.append({"instrumento_id": iid, "motivo": "sin precio para valuar la posición"})
            continue
        e = mapa.get(iid)
        if not e:
            sin.append({"instrumento_id": iid, "motivo": "sin pronóstico utilizable (historia insuficiente o dato vencido)"})
            c50, c10, c90 = c50 + v, c10 + v, c90 + v
            continue
        a, b, m = v * (1 + e["rend_p10"]), v * (1 + e["rend_p90"]), v * (1 + e["rend_central"])
        c50, c10, c90 = c50 + m, c10 + a, c90 + b
        filas.append({"instrumento_id": iid, "clave": e["clave"], "valor_actual": round(v, 2), "central": round(m, 2),
                      "p10": round(a, 2), "p90": round(b, 2), "prob_subida": e["prob_subida"]})
    valor = float(cart.get("valor_total") or 0)
    cap = capital if capital is not None else valor
    return {
        "conciliada": conciliada, "fuente": cart.get("fuente"),
        "hora_portal": (cart.get("captura") or {}).get("hora_portal"),
        "aviso": (None if conciliada else "Cartera NO conciliada con el portal de Actinver: se usa el registro local de la "
                  "terminal. Capture su portafolio en «Mi portafolio Actinver» para usar sus posiciones y efectivo reales."),
        "valor_actual": round(valor, 2), "efectivo_y_por_liquidar": round(resto, 2),
        "central": round(c50, 2), "p10": round(c10, 2), "p90": round(c90, 2),
        "ganancia_central": round(c50 - cap, 2), "capital": cap, "posiciones": filas, "sin_pronostico": sin,
        "nota": "Rango conservador: suma los extremos de cada posición como si todas se movieran juntas.",
    }


def comparar_propuestas(props: dict | None, emisoras: list[dict], cart: dict) -> dict:
    """Cada propuesta vigente frente al pronóstico: rendimiento estimado neto de comisiones (+IVA) del rebalanceo, peso con
    pronóstico, exposición al SIC (incluye tipo de cambio), reglas del Reto y disponibilidad en el catálogo del simulador."""
    from .. import reto, resumen
    mapa = {e["instrumento_id"]: e for e in emisoras if not e["vencido"]}
    filas = []
    valor = float(cart.get("valor_total") or 0)
    actual = {p["instrumento_id"]: (p.get("valor_mxn") or 0) / valor for p in cart.get("posiciones") or [] if valor > 0}
    candidatos = [("Mantener mi cartera", actual, 0.0, None, [], False)]
    for p in resumen._vigentes(props):
        w = {a["id"]: float(a.get("peso") or 0) for a in p.get("pesos") or []}
        candidatos.append((p["nombre"], w, float((p.get("cambios") or {}).get("costo_pct") or 0), p,
                           p.get("cumplimiento_reto") or reto.cumplimiento(w), bool(p.get("recalcular"))))
    for nombre, w, costo, p, cumpl, recalc in candidatos:
        cub = sum(v for i, v in w.items() if i in mapa)
        r50 = sum(v * mapa[i]["rend_central"] for i, v in w.items() if i in mapa)
        r10 = sum(v * mapa[i]["rend_p10"] for i, v in w.items() if i in mapa)
        r90 = sum(v * mapa[i]["rend_p90"] for i, v in w.items() if i in mapa)
        filas.append({
            "nombre": nombre, "puntuacion": ((p or {}).get("puntuacion") or {}).get("total"),
            "rend_estimado_bruto": r50, "costo_rebalanceo": costo, "rend_estimado_neto": r50 - costo,
            "rango_p10": r10 - costo, "rango_p90": r90 - costo, "peso_con_pronostico": cub,
            "peso_sic": sum(v for i, v in w.items() if i.startswith("SIC:")),
            "cumple_reto": all(c.get("cumple") for c in cumpl) if cumpl else None,
            "simulador": ("catálogo cambió: revisar" if recalc else "en el catálogo del simulador importado") if p else "posiciones actuales",
            "escenario_optimizador": ((p or {}).get("escenarios") or {}).get("central_p50"),
        })
    props_f = [f for f in filas if f["puntuacion"] is not None]
    max_punt = max(props_f, key=lambda f: f["puntuacion"], default=None)
    max_rend = max(props_f, key=lambda f: f["rend_estimado_neto"], default=None)
    if not max_punt:
        expl = "No hay propuestas vigentes para comparar."
    elif max_punt["nombre"] == max_rend["nombre"]:
        expl = f"La propuesta de máxima puntuación («{max_punt['nombre']}») es también la de mayor rendimiento estimado neto."
    else:
        expl = (f"La máxima puntuación es «{max_punt['nombre']}» ({max_punt['rend_estimado_neto']:+.2%} estimado neto) y el mayor "
                f"rendimiento estimado es «{max_rend['nombre']}» ({max_rend['rend_estimado_neto']:+.2%}). Difieren porque la "
                "puntuación también pesa riesgo, diversificación, liquidez, costos y calidad de datos, y el pronóstico no "
                "tiene ventaja demostrada: no se usa para cambiar la propuesta.")
    return {"filas": filas, "max_puntuacion": max_punt and max_punt["nombre"], "max_rendimiento": max_rend and max_rend["nombre"],
            "explicacion": expl,
            "nota": ("Los costos son comisión + IVA del rebalanceo calculados por el optimizador. Las emisoras del SIC usan el "
                     "precio de EE. UU. (Alpaca/Tiingo) × tipo de cambio: es una referencia, no una cotización ejecutable del SIC.")}


def cambios(actual: list[dict], anterior: list[dict], n: int = 5) -> dict:
    """Mayores cambios de la estimación central frente a la emisión anterior con la misma etiqueta."""
    if not anterior:
        return {"hay_anterior": False, "filas": [], "texto": "Primera emisión: no hay pronóstico anterior para comparar."}
    prev = {f["instrumento_id"]: f for f in anterior}
    filas = []
    for f in actual:
        a = prev.get(f["instrumento_id"])
        if a:
            filas.append({"instrumento_id": f["instrumento_id"], "antes": math.expm1(a["prediccion"]),
                          "ahora": math.expm1(f["prediccion"]), "delta": math.expm1(f["prediccion"]) - math.expm1(a["prediccion"]),
                          "prob_antes": a["prob_subida"], "prob_ahora": f["prob_subida"]})
    filas.sort(key=lambda x: -abs(x["delta"]))
    nuevas = sorted(set(f["instrumento_id"] for f in actual) - set(prev))
    return {"hay_anterior": True, "emitido_anterior": anterior[0]["emitido_en"],
            "version_cambio": anterior[0]["version"] != (actual[0]["version"] if actual else None),
            "filas": filas[:n], "nuevas": nuevas, "salieron": sorted(set(prev) - {f["instrumento_id"] for f in actual})}


def calidad(exp: dict | None, det: dict | None) -> dict | None:
    """Calidad histórica fuera de muestra del horizonte y del registro de pronósticos ya resueltos."""
    if not exp or exp.get("estado") != "ok":
        return None
    t = exp.get("prueba") or []
    mod = t[0] if t else {}
    sc = next((m for m in t if m["modelo"] == "sin_cambio"), {})
    cal = [c for c in (mod.get("calibracion") or []) if c["n"] >= 30]
    peor = max(cal, key=lambda c: abs(c["prob_media"] - c["frecuencia_subida"]), default=None)
    desvio = abs(peor["prob_media"] - peor["frecuencia_subida"]) if peor else None
    return {"H": exp.get("H"), "hora_corte": exp.get("hora_corte"), "veredicto": exp.get("veredicto"),
            "calibracion_desvio": desvio, "calibracion_aviso": (
                f"Probabilidad de subida mal calibrada: en la prueba, cuando estimaba {peor['prob_media']:.0%} subió el "
                f"{peor['frecuencia_subida']:.0%} de las veces ({peor['n']} casos). No la lea como probabilidad real."
                if desvio is not None and desvio > 0.10 else None),
            "razon_error_vs_sin_cambio": (mod["mse"] / sc["mse"]) if mod.get("mse") and sc.get("mse") else None,
            "acierto_direccion": mod.get("acierto_direccion"), "cobertura_80": mod.get("cobertura_intervalo_80"),
            "brier": mod.get("brier_prob_subida"), "calibracion": mod.get("calibracion"),
            "resultado_neto": mod.get("resultado_neto"), "rotacion_media": mod.get("rotacion_media"),
            "caida_maxima": mod.get("caida_maxima"), "prueba": t, "estrategias_referencia": exp.get("estrategias_referencia"),
            "por_mercado": exp.get("por_mercado") or [], "historia_insuficiente": exp.get("historia_insuficiente") or [],
            "cortes": exp.get("cortes"), "dias_prueba": exp.get("dias_prueba"), "moneda": exp.get("moneda"),
            "version": f"{exp.get('version_codigo')}+{exp.get('huella_config')}", "variante": exp.get("variante_elegida"),
            "deterioro": det}


def construir(con: sqlite3.Connection, ajustes, props: dict | None = None, cart: dict | None = None,
              ahora: datetime | None = None) -> dict:
    """Vista completa para «Pasado · Presente · Futuro», el reporte y Telegram."""
    from .. import reto, servicios
    filas = pronosticos.emision(con, "reto")
    etiqueta = "reto"
    if not filas:  # sin emisión al cierre del Reto: se muestra la de 5 sesiones, con su etiqueta
        filas, etiqueta = pronosticos.emision(con, "5s"), "5s"
    H = filas[0]["horizonte"] if filas else horizonte_reto(ahora=ahora)["H"]
    det = pronosticos.deterioro(con)
    exp = _exp(con, H, ajustes.es_demo) if filas else None
    bar = barrera(exp, det)
    emis = por_emisora(con, filas, ahora)
    cart = cart if cart is not None else servicios.cartera_actual(con, ajustes)
    capital = float(reto.config().get("capital") or 0) if reto.activo() else None
    if props is None:
        props = servicios.propuestas_guardadas(con, ajustes, servicios.perfil_actual(con, ajustes))
    from .. import mercado
    q = calidad(exp, det)
    cortos = {x["instrumento_id"] for x in (q or {}).get("historia_insuficiente") or []}
    activos = {i for i, v in mercado.instrumentos(con).items() if v.get("estado") == "activo"}
    sin_datos = sorted(activos - {e["instrumento_id"] for e in emis} - cortos)
    utiles = [e for e in emis if not e["vencido"]]
    en_cartera = {p["instrumento_id"] for p in cart.get("posiciones") or []}
    riesgos = sorted([e for e in utiles if e["instrumento_id"] in en_cartera] or utiles, key=lambda e: e["rend_p10"])[:3]
    return {
        "etiqueta": etiqueta, "horizonte": {"H": H, "hasta": filas[0]["fecha_objetivo"] if filas else None,
                                            **({"actual": horizonte_reto(ahora=ahora)} if etiqueta == "reto" else {})},
        "emision": ({**{k: filas[0][k] for k in ("emitido_en", "datos_hasta", "version", "modelo", "moneda")},
                     "ultimo_cierre": max(f["fecha_base"] for f in filas)} if filas else None),
        "barrera": bar, "uso_en_decisiones": ("El pronóstico puede informar el plan (barrera superada)." if bar["permitida"] else
                                              f"{LEYENDA_SIN_VENTAJA.capitalize()}: el plan, las propuestas y las boletas siguen el "
                                              "método actual; el pronóstico no cambia ninguna orden."),
        "emisoras": emis, "mayor_potencial": utiles[:5], "riesgos": riesgos,
        "vencidos": [e["clave"] for e in emis if e["vencido"]],
        "cartera": cartera(cart, emis, capital), "propuestas": comparar_propuestas(props, emis, cart),
        "cambios": cambios(filas, pronosticos.emision(con, etiqueta, previa=True)),
        "calidad": q, "sin_datos": sin_datos, "aviso": AVISO,
    }


def _p(x: float | None) -> str:
    return "—" if x is None else f"{x:+.1%}"


def _m(x: float | None) -> str:
    return "—" if x is None else f"${x:,.0f}"


def texto(r: dict) -> str:
    """Resumen corto para Telegram y el reporte diario."""
    if not r.get("emision"):
        return ("Pronóstico: aún no hay emisión. Desde la terminal: Futuro → «Emitir pronósticos», o "
                "`uv run terminal investigar --reto`.")
    e, h, b = r["emision"], r["horizonte"], r["barrera"]
    tit = (f"Pronóstico al cierre del Reto ({h['hasta']}, {h['H']} sesiones)" if r["etiqueta"] == "reto"
           else f"Pronóstico a {h['H']} sesiones")
    out = [f"🔮 {tit} — ESTIMACIÓN en pesos, no cotización",
           f"Emitido {e['emitido_en'][:16].replace('T', ' ')} UTC · último cierre usado {e['ultimo_cierre']} · modelo {e['version']}",
           f"{'✅' if b['permitida'] else '⚠️'} {b['leyenda']}" + ("" if b["permitida"] else " — el plan sigue el método actual."),
           "", "Mayor potencial estimado:"]
    out += [f"• {x['clave']} {_p(x['rend_central'])} (rango {_p(x['rend_p10'])} a {_p(x['rend_p90'])}; "
            f"prob. subida {x['prob_subida']:.0%})" for x in r["mayor_potencial"]] or ["• sin estimaciones utilizables"]
    out += ["", "Riesgos principales (peor escenario 10 %):"]
    out += [f"• {x['clave']} {_p(x['rend_p10'])}" for x in r["riesgos"]] or ["• —"]
    falta = len((r.get("calidad") or {}).get("historia_insuficiente") or []) + len(r.get("sin_datos") or [])
    if falta:
        out.append(f"• Sin pronóstico por falta de datos o historia corta: {falta} instrumentos (se listan en la terminal)")
    if r["vencidos"]:
        out.append(f"• Datos vencidos, sin pronóstico: {', '.join(r['vencidos'][:6])}")
    c = r["cartera"]
    out += ["", ("Cartera del portal" + (f" ({str(c['hora_portal'])[:16].replace('T', ' ')})" if c.get("hora_portal") else "")
                 if c["conciliada"]
                 else "Cartera NO conciliada con el portal (registro local)")
            + f": hoy {_m(c['valor_actual'])}; estimado al objetivo {_m(c['central'])} (rango conservador {_m(c['p10'])} a {_m(c['p90'])})."]
    ch = r["cambios"]
    if ch["hay_anterior"] and ch["filas"]:
        out.append("Cambios vs. pronóstico anterior: " + "; ".join(f"{f['instrumento_id'].split(':')[-1]} {_p(f['antes'])}→{_p(f['ahora'])}"
                                                                   for f in ch["filas"][:3]))
    else:
        out.append(ch.get("texto") or "Sin cambios relevantes frente al pronóstico anterior.")
    q = r.get("calidad")
    if q:
        out.append(f"Calidad histórica (prueba fuera de muestra): error/«sin cambio» {q['razon_error_vs_sin_cambio']:.2f}, "
                   f"dirección {q['acierto_direccion'] or 0:.0%}, cobertura 80 % {q['cobertura_80'] or 0:.0%}, "
                   f"neto de costos {_p(q['resultado_neto'])}. {q['veredicto']}.")
        if q.get("calibracion_aviso"):
            out.append("⚠️ " + q["calibracion_aviso"])
    out += ["", r["propuestas"]["explicacion"]]
    return "\n".join(out)
