"""Ficha técnica por emisora: precio con su vigencia, análisis técnico, velas, Order Flow, Option Flow, fundamentales,
noticias, la posición del usuario y los widgets disponibles, en una sola consulta.

Reúne lo que ya calculan otros módulos; no inventa nada: si un bloque no tiene fuente, viene con `disponible: False` y
su motivo. «Tiempo real» solo se dice cuando el precio viene del flujo en vivo (IEX); lo demás lleva su fecha y retraso.
"""
from __future__ import annotations

import csv
import math
from functools import lru_cache

import pandas as pd

from . import gestion_riesgo, mercado
from .config import CONFIG_DIR
from .flujo import calculos

WIDGETS = [("grafica", "Gráfica avanzada"), ("info", "Precio y rango del día"), ("tecnico", "Análisis técnico (osciladores)"),
           ("perfil", "Perfil de la empresa"), ("finanzas", "Estados financieros"), ("panorama", "Panorama del precio"),
           ("noticias-emisora", "Noticias de la emisora")]
SIN_WIDGET_BMV = {"grafica", "info", "panorama", "noticias-emisora"}  # = app.BMV_SIN_WIDGET: sin precio BMV en widgets gratis


@lru_cache(maxsize=1)
def _sectores() -> dict[str, str]:
    """El mismo `config/sectores.csv` que `markowitz.sectores`, sin cargar scipy (4.6 s) para una lectura."""
    archivo = CONFIG_DIR / "sectores.csv"
    if not archivo.exists():
        return {}
    with archivo.open(encoding="utf-8") as f:
        return {r["id"]: r["grupo"] for r in csv.DictReader(f) if r.get("grupo")}


def _ultimo(x: list) -> float | None:
    return next((v for v in reversed(x) if v is not None), None)


def tecnico(s: pd.Series) -> dict:
    """Indicadores sobre cierres diarios en MXN (ajustados por splits)."""
    if len(s) < 2:
        return {"disponible": False, "motivo": "menos de dos cierres guardados"}
    c = [float(v) for v in s.values]
    precio = c[-1]

    def var(n):
        return precio / c[-1 - n] - 1 if len(c) > n else None
    sma20, sma50, sma200 = (_ultimo(calculos.sma(c, n)) for n in (20, 50, 200))
    ema20, ema50 = _ultimo(calculos.ema(c, 20)), _ultimo(calculos.ema(c, 50))
    rsi = _ultimo(calculos.rsi_wilder(c, 14))
    m = calculos.macd(c)
    macd, senal = _ultimo(m["macd"]), _ultimo(m["senal"])
    bol = _ultimo(calculos.bollinger(c))
    r = pd.Series(c).pct_change().dropna()
    vol = float(r.tail(20).std() * math.sqrt(252)) if len(r) >= 5 else None
    ano = c[-252:]
    riesgo = gestion_riesgo.indicadores(s, gestion_riesgo.REGLAS) or {}
    senales = []
    if sma50 and sma200:
        senales.append(("Tendencia de largo plazo", "alcista" if sma50 > sma200 else "bajista",
                        f"SMA50 {sma50:,.2f} {'>' if sma50 > sma200 else '<'} SMA200 {sma200:,.2f}"))
    if riesgo:
        senales.append(("Tendencia de corto plazo", "alcista" if riesgo["alcista"] else "bajista" if riesgo["bajista"] else "lateral",
                        f"precio {precio:,.2f} · SMA20 {riesgo['sma_corta']:,.2f} · SMA50 {riesgo['sma_larga']:,.2f}"))
        senales.append(("Stop por volatilidad", "roto" if precio < riesgo["stop"] else "respetado", f"stop {riesgo['stop']:,.2f}"))
    if rsi is not None:
        senales.append(("RSI 14", "sobrecompra" if rsi >= 70 else "sobreventa" if rsi <= 30 else "neutral", f"{rsi:.1f}"))
    if macd is not None and senal is not None:
        senales.append(("MACD", "alcista" if macd > senal else "bajista", f"MACD {macd:,.2f} · señal {senal:,.2f}"))
    if bol:
        senales.append(("Bollinger (20, 2)", "arriba de la banda" if precio > bol[1] else "debajo de la banda" if precio < bol[0]
                        else "dentro de las bandas", f"{bol[0]:,.2f} – {bol[1]:,.2f}"))
    alcistas = sum(1 for _, e, _ in senales if e in ("alcista", "respetado", "sobreventa"))
    bajistas = sum(1 for _, e, _ in senales if e in ("bajista", "roto", "sobrecompra"))
    return {"disponible": True, "precio": precio, "fecha": str(s.index[-1].date()), "sesiones": len(c),
            "variacion": {"1d": var(1), "5d": var(5), "1m": var(21), "3m": var(63), "1a": var(252)},
            "maximo_52s": max(ano), "minimo_52s": min(ano), "desde_maximo": precio / max(ano) - 1,
            "sma20": sma20, "sma50": sma50, "sma200": sma200, "ema20": ema20, "ema50": ema50, "rsi14": rsi,
            "macd": macd, "macd_senal": senal, "bollinger": list(bol) if bol else None, "volatilidad_anual": vol,
            "stop": riesgo.get("stop"), "senales": [{"indicador": a, "estado": b, "detalle": d} for a, b, d in senales],
            "lectura": ("mayoría de señales alcistas" if alcistas > bajistas else "mayoría de señales bajistas" if bajistas > alcistas
                        else "señales mixtas") + f" ({alcistas} a favor, {bajistas} en contra)",
            "serie": [{"fecha": str(i.date()), "cierre": float(v)} for i, v in s.tail(260).items()]}


def ficha(con, ajustes, iid: str, cartera: dict | None = None, flujo: bool = True) -> dict:
    """Ficha completa. Con `flujo=False` omite el resumen de Order Flow y Option Flow (los más pesados): la interfaz muestra
    esos paneles completos dentro de la ficha."""
    from . import capitalizacion, seguimiento
    from .flujo import servicio
    ins = mercado.instrumentos(con).get(iid)
    if not ins:
        raise KeyError(iid)
    cot = mercado.cotizaciones(con, ajustes, [iid]).get(iid) or {}
    P = mercado.precios_mxn(con, ajustes, [iid], ajustados="splits")
    s = P[iid].dropna() if iid in P.columns else pd.Series(dtype=float)
    vivo = cot.get("tipo_dato") == "tiempo_real"
    precio = {"precio_mxn": cot.get("precio_mxn"), "precio_origen": cot.get("precio"), "moneda_origen": cot.get("moneda"),
              "fecha": cot.get("fecha"), "hora": cot.get("hora_cotizacion"), "proveedor": cot.get("proveedor"),
              "vigencia": cot.get("estado"), "tiempo_real": vivo,
              "etiqueta": ("Tiempo real (IEX, flujo en vivo)" if vivo else
                           f"{(cot.get('estado') or 'sin datos').capitalize()} · cierre del {cot.get('fecha') or '—'}")}
    try:
        cap = (capitalizacion.para_precios(con, ajustes, {iid: float(cot["precio_mxn"])}).get(iid)
               if cot.get("precio_mxn") else None)
    except Exception:  # noqa: BLE001 - la capitalización es complementaria
        cap = None
    sic = iid.startswith("SIC:")
    velas = servicio.velas(con, ajustes, iid, "1Day", 365) if sic else {"barras": []}
    pos = next((p for p in (cartera or {}).get("posiciones") or [] if p["instrumento_id"] == iid), None)
    if pos and pos.get("origen_precio") == "portal":  # la captura del portal es más reciente que el precio de la terminal
        hora = str(((cartera or {}).get("captura") or {}).get("hora_portal") or "")
        precio.update(precio_mxn=pos["precio_mxn"], fecha=hora[:10], proveedor="portal del Reto (captura)", vigencia="vigente",
                      etiqueta=f"Portal del Reto · captura del {hora[:10]} {hora[11:16]}")
        if len(s) and str(s.index[-1].date()) < hora[:10]:
            s = pd.concat([s, pd.Series([float(pos["precio_mxn"])], index=[pd.Timestamp(hora[:10])])])
    return {
        "id": iid, "clave": ins.get("clave_operable"), "nombre": (ins.get("nombre") or "").strip(),
        "perfil": {"mercado": ins.get("mercado_operable"), "clase": ins.get("clase"), "moneda": ins.get("moneda_referencia"),
                   "bolsa_origen": ins.get("bolsa_referencia"), "listado": ins.get("listado_referencia"),
                   "sector": _sectores().get(iid), "capitalizacion": cap},
        "precio": precio, "tecnico": tecnico(s),
        "velas": {"disponible": bool(velas["barras"]), "barras": len(velas["barras"]),
                  "ultima": velas["barras"][-1]["inicio"][:10] if velas["barras"] else None,
                  "motivo": None if velas["barras"] else ("Sin velas OHLCV: la BMV y los fondos no tienen fuente gratuita; "
                                                          "se usan los cierres diarios." if not sic else "sin velas guardadas")},
        **(resumen_flujo(con, ajustes, iid, cot) if flujo else {}),
        "fundamentales": seguimiento.financieros(con, iid)[:16],
        "noticias": seguimiento.noticias(con, iid, 8),
        "posicion": ({"titulos": pos.get("cantidad"), "costo_promedio": pos.get("costo_promedio"), "valor": pos.get("valor_mxn"),
                      "peso": pos.get("peso"), "plusvalia": pos.get("no_realizado"), "plusvalia_pct": pos.get("no_realizado_pct")}
                     if pos else None),
        "widgets": [{"tipo": t, "nombre": n, "disponible": not (iid.startswith("BMV:") and t in SIN_WIDGET_BMV)}
                    for t, n in WIDGETS] if not ins.get("clase", "").startswith("fondo") else [],
        "nota": "Precios en MXN ajustados por splits. Indicadores descriptivos sobre cierres diarios; no son una recomendación. "
                "La terminal no envía órdenes.",
    }


def resumen_flujo(con, ajustes, iid: str, cot: dict | None = None) -> dict:
    """Order Flow y Option Flow de la ficha."""
    from .flujo import servicio
    if not iid.startswith("SIC:"):
        return {"orderflow": {"disponible": False, "motivo": "Sin libro ni operaciones gratuitas para la BMV o fondos."},
                "optionflow": {"disponible": False, "motivo": "Sin cadena de opciones (solo emisoras de EE. UU. vía Alpaca)."}}
    cot = cot if cot is not None else (mercado.cotizaciones(con, ajustes, [iid]).get(iid) or {})
    of, opc = _orderflow(con, ajustes, iid), servicio.optionflow(con, ajustes, iid)
    return {"orderflow": {"disponible": bool(of["libro"] or of["operaciones"]), "libro": of["libro"],
                          "libro_hora": (of.get("libro_meta") or {}).get("instante"), "operaciones": of["resumen"].get("n"),
                          "volumen": of["resumen"].get("volumen"), "con_lado": of["resumen"].get("con_lado")},
            "optionflow": (_opciones(opc, cot) if opc["total"] else
                           {"disponible": False, "motivo": "Sin cadena de opciones guardada para esta emisora."})}


def _orderflow(con, ajustes, iid: str) -> dict:
    """Libro y resumen de las últimas operaciones guardadas, sin el footprint ni la historia del libro que arma el panel
    de Order Flow (con 10 000 operaciones costaba ~8 s con el motor ocupado)."""
    from .flujo import almacen
    libro = almacen.ultimo_libro(con, iid, demo=ajustes.es_demo)
    ultima = almacen.operaciones(con, iid, None, demo=ajustes.es_demo, limite=1)
    ops = []
    if ultima:
        from datetime import datetime, timedelta
        fin = datetime.fromisoformat(ultima[-1]["instante"])
        ops = almacen.operaciones(con, iid, (fin - timedelta(minutes=240)).isoformat(), demo=ajustes.es_demo)
    return {"libro": calculos.resumen_libro(libro, 10), "libro_meta": {"instante": libro["instante"]} if libro else None,
            "operaciones": ops, "resumen": calculos.resumen_operaciones(ops)}


def _opciones(opc: dict, cot: dict) -> dict:
    """Resumen de la cadena. El GEX (el cálculo más pesado) lo pide la interfaz aparte a /api/flujo/gex."""
    cs = opc["contratos"]
    vol = {t: sum(c.get("volumen") or 0 for c in cs if c["tipo"] == t) for t in ("call", "put")}
    oi = {t: sum(c.get("interes_abierto") or 0 for c in cs if c["tipo"] == t) for t in ("call", "put")}
    spot = cot.get("precio")
    atm = None
    # IV «at the money» del primer vencimiento a 7 días o más: los de 0–6 días dan IV extremas (MU: 404 % a 1 día)
    vencs = [v for v in opc["vencimientos"] if any(c["vencimiento"] == v and (c.get("dias") or 0) >= 7 for c in cs)]
    if spot and vencs:
        cerca = [c for c in cs if c["vencimiento"] == vencs[0] and c.get("iv")]
        if cerca:
            atm = min(cerca, key=lambda c: abs(c["strike"] - spot)).get("iv")
    return {"disponible": True, "contratos": opc["total"], "vencimientos": len(opc["vencimientos"]),
            "proximo_vencimiento": opc["vencimientos"][0] if opc["vencimientos"] else None, "iv_atm": atm,
            "vencimiento_iv": vencs[0] if vencs else None,
            "put_call_volumen": vol["put"] / vol["call"] if vol["call"] else None,
            "put_call_oi": oi["put"] / oi["call"] if oi["call"] else None, "volumen_inusual": len(opc["inusual"])}
