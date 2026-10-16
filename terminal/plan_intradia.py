"""Plan intradía DEFENSIVO e informativo, separado del plan de acción normal (`plan_accion.py`).

No genera órdenes, no escribe en la cartera ni en las boletas y no marca nada como ejecutado. Muestra el contexto
(concentración, presupuesto de pérdida, liquidez, costos del Reto), las reglas de disciplina y si hay datos para hablar de
una señal ejecutable. Los datos diarios, retrasados, de retraso desconocido o con el mercado cerrado la INHIBEN: con los
proveedores gratuitos actuales (≥ 15 min de retraso) la señal ejecutable queda siempre inhibida.
Los umbrales son parámetros de disciplina editables en `[intradia]` de la configuración, no resultados de un modelo.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime

from . import reto, servicios, vigencia
from .flujo.contratos import INTERVALOS

PARAMETROS = {
    "perdida_diaria_pct": 1.0,        # % del valor de la cartera: al alcanzarla, pausa hasta la siguiente sesión
    "perdida_por_idea_pct": 0.25,     # % del valor de la cartera que puede perder UNA idea antes de salir
    "liquidez_max_pct_volumen": 1.0,  # % del volumen promedio diario (20 sesiones) que puede representar una posición
    "retraso_max_s": 60,              # retraso máximo de un dato intradía para considerarlo apto
}
INTRADIA = tuple(k for k in INTERVALOS if k != "1Day")
REGLAS = [
    "Pausa tras la pérdida límite del día: al alcanzar el presupuesto de pérdida diaria no se abren ideas nuevas hasta la siguiente sesión.",
    "No promediar pérdidas: no se compra más de una posición que está en pérdida para bajar el costo promedio.",
    "Una idea no arriesga más que el presupuesto por idea; si se invalida, se sale, no se espera.",
    "Concentración: umbral de revisión del 50 % por emisora y el tope de su perfil si es menor. La regla del Reto limita la compra; una apreciación posterior no equivale por sí sola a incumplirla.",
    "Costos: cada entrada y salida paga comisión + IVA; un movimiento menor al costo de ida y vuelta pierde dinero aunque acierte la dirección.",
    "Sin datos intradía vigentes (retraso conocido y bajo), no hay señal ejecutable: solo contexto.",
    "Sin ventas en corto ni apalancamiento (Reto §11). Las coberturas con futuros no son elegibles en el Reto y no se consideran.",
    "Esta vista es informativa: la terminal no envía órdenes ni modifica la cartera; cualquier operación la captura usted en el portal.",
]


def _parametros(ajustes) -> dict:
    try:
        cfg = ajustes.get("intradia") or {}
    except AttributeError:
        cfg = {}
    out = dict(PARAMETROS)
    for k in out:
        v = cfg.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0:
            out[k] = float(v)
    return out


def _dato_intradia(con, iid: str, ahora: datetime, retraso_max_s: float) -> dict:
    """Última barra intradía guardada de la posición y si su retraso permite hablar de señal."""
    f = con.execute(f"SELECT intervalo, inicio, retraso_s, capturado_en, calidad FROM flujo_barras WHERE simbolo=? "
                    f"AND intervalo IN ({','.join('?' * len(INTRADIA))}) ORDER BY inicio DESC LIMIT 1", (iid, *INTRADIA)).fetchone()
    if not f:
        return {"instrumento_id": iid, "apto": False, "tipo": "diario",
                "motivo": "solo hay datos diarios (o ninguno): sin barras intradía guardadas"}
    edad = (ahora - datetime.fromisoformat(f["inicio"])).total_seconds() - INTERVALOS[f["intervalo"]]
    r = f["retraso_s"]
    base = {"instrumento_id": iid, "tipo": "intradia", "intervalo": f["intervalo"], "inicio": f["inicio"],
            "retraso_s": r, "edad_barra_s": max(0.0, edad), "calidad": f["calidad"]}
    if f["calidad"] == "sintetico" or edad < -INTERVALOS[f["intervalo"]]:
        return {**base, "apto": False, "motivo": "barra sintética o con fecha futura: solo práctica"}
    if r is None:
        return {**base, "apto": False, "motivo": "retraso desconocido"}
    if r > retraso_max_s:
        return {**base, "apto": False, "motivo": f"dato retrasado {r:.0f} s (máximo {retraso_max_s:.0f} s)"}
    if edad > 2 * INTERVALOS[f["intervalo"]]:
        return {**base, "apto": False, "motivo": "la última barra ya no es reciente"}
    return {**base, "apto": True, "motivo": "dato intradía con retraso aceptable"}


def _liquidez(con, iid: str, cantidad: float, limite_pct: float) -> dict:
    v = [r[0] for r in con.execute("SELECT volumen FROM precios WHERE instrumento_id=? AND volumen IS NOT NULL AND volumen>0 "
                                   "AND proveedor<>'demo_sintetico' ORDER BY fecha DESC LIMIT 20", (iid,))]
    if len(v) < 10:
        return {"instrumento_id": iid, "estado": "sin_datos", "titulos": cantidad,
                "nota": "menos de 10 sesiones con volumen guardado: no se puede medir la liquidez"}
    adv = sum(v) / len(v)
    pct = cantidad / adv * 100
    return {"instrumento_id": iid, "estado": "alerta" if pct > limite_pct else "ok", "titulos": cantidad,
            "volumen_promedio_20": adv, "pct_del_volumen": pct, "limite_pct": limite_pct,
            "nota": "Volumen diario guardado; en emisoras del SIC es el de la bolsa de origen, no la liquidez del SIC."}


def calcular(con, ajustes, perdida_dia_mxn: float | None = None, ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now(UTC)
    par = _parametros(ajustes)
    cart = servicios.cartera_actual(con, ajustes)
    confirmada = cart.get("fuente") == "portal"
    valor = float(cart.get("valor_total") or 0)
    pos = [p for p in cart.get("posiciones") or [] if (p.get("cantidad") or 0) > 0]
    perfil = servicios.perfil_actual(con, ajustes)
    tope_reto = float((reto.config().get("reglas") or {}).get("max_peso_emisora") or 0.5) if reto.activo() else 1.0
    tope = min(tope_reto, float(perfil.get("max_peso_activo") or 1.0))
    pesos = [(p, float(p.get("peso") or 0)) for p in pos]
    mayor = max(pesos, key=lambda x: x[1], default=(None, 0.0))
    concentracion = {"mayor": mayor[0] and (mayor[0].get("clave_operable") or mayor[0]["instrumento_id"]), "peso_mayor": mayor[1],
                     "tope": tope, "hhi": sum(w * w for _, w in pesos) if pesos else None,
                     "excede": [(p.get("clave_operable") or p["instrumento_id"], w) for p, w in pesos if w > tope + 1e-9]}
    presupuesto = {"valor_cartera_mxn": valor or None,
                   "perdida_diaria_mxn": valor * par["perdida_diaria_pct"] / 100 if valor else None,
                   "perdida_por_idea_mxn": valor * par["perdida_por_idea_pct"] / 100 if valor else None,
                   "perdida_diaria_pct": par["perdida_diaria_pct"], "perdida_por_idea_pct": par["perdida_por_idea_pct"],
                   "perdida_del_dia_informada_mxn": perdida_dia_mxn}
    pausa = {"activa": False, "estado": "no_informado",
             "mensaje": "Pérdida del día no informada: indíquela para evaluar la pausa (la terminal no mide su P&L intradía)."}
    if perdida_dia_mxn is not None and presupuesto["perdida_diaria_mxn"]:
        activa = perdida_dia_mxn >= presupuesto["perdida_diaria_mxn"]
        pausa = {"activa": activa, "estado": "pausa" if activa else "dentro_del_limite",
                 "mensaje": ("PAUSA: se alcanzó el presupuesto de pérdida diaria. No abra ideas nuevas hoy ni promedie pérdidas."
                             if activa else f"Dentro del presupuesto: {perdida_dia_mxn / presupuesto['perdida_diaria_mxn']:.0%} usado.")}
    en_perdida = [{"instrumento_id": p["instrumento_id"], "clave": p.get("clave_operable"), "no_realizado_pct": p["no_realizado_pct"]}
                  for p, _ in pesos if (p.get("no_realizado_pct") or 0) < 0]
    datos = [_dato_intradia(con, p["instrumento_id"], ahora, par["retraso_max_s"]) for p, _ in pesos]
    liquidez = [_liquidez(con, p["instrumento_id"], float(p["cantidad"]), par["liquidez_max_pct_volumen"]) for p, _ in pesos]
    c = reto.costo_operacion() if reto.activo() else None
    abierto = vigencia.mercado_abierto("XMEX", ahora) or vigencia.mercado_abierto("XNYS", ahora)
    motivos = []
    if not confirmada:
        motivos.append("Sin captura vigente del portal: no se conocen sus títulos ni su efectivo.")
    if not pos:
        motivos.append("Sin posiciones con las que evaluar datos intradía.")
    if not abierto:
        motivos.append("Mercado cerrado.")
    motivos += [f"{d['instrumento_id']}: {d['motivo']}." for d in datos if not d["apto"]]
    if pausa["activa"]:
        motivos.append("Pausa por pérdida límite del día.")
    inhibida = bool(motivos)
    return {
        "modo": "informativo", "generado_en": ahora.isoformat(timespec="seconds"), "ordenes": [],
        "aviso": ("Plan informativo y separado del plan normal: no genera órdenes ni modifica la cartera. Las coberturas con "
                  "futuros no son elegibles en el Reto y no se recomiendan."),
        "senal_ejecutable": False, "inhibida": inhibida, "motivos_inhibicion": motivos,
        "nota_senal": ("Hay datos aptos, pero esta vista no genera órdenes ni señales de compra o venta; solo contexto."
                       if not inhibida else "Señal inhibida: sin datos intradía vigentes no se plantea ninguna señal ejecutable."),
        "cuenta": {"confirmada": confirmada, "fuente": cart.get("fuente")},
        "concentracion": concentracion, "presupuesto_perdida": presupuesto, "pausa": pausa,
        "no_promediar": {"posiciones_en_perdida": en_perdida,
                         "regla": "No añada títulos a estas posiciones para bajar su costo promedio."},
        "liquidez": liquidez, "datos": datos,
        "costos": {"por_operacion_pct": c, "ida_y_vuelta_pct": None if c is None else 2 * c,
                   "nota": "Comisión 0.10 % + IVA por lado (Reto §8); el spread del simulador no está publicado, así que el costo real puede ser mayor."},
        "reglas": REGLAS, "parametros": par,
        "disponibilidad": [
            {"dato": "Barras intradía con retraso conocido ≤ " + f"{par['retraso_max_s']:.0f} s",
             "estado": "ok" if datos and all(d["apto"] for d in datos) else "falta",
             "requiere": "Proveedor de tiempo real (p. ej. SIP/OPRA en vivo) o importación de barras con retraso declarado; "
                         "el feed gratuito de Alpaca llega con ≥ 15 min de retraso."},
            {"dato": "Captura vigente del portal", "estado": "ok" if confirmada else "falta",
             "requiere": "Capture su cuenta en «Mi portafolio Actinver»."},
            {"dato": "P&L intradía del día", "estado": "ok" if perdida_dia_mxn is not None else "falta",
             "requiere": "Indique manualmente la pérdida del día; la terminal no accede al portal ni a su cuenta."},
        ],
    }
