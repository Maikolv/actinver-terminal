"""Gestión de riesgo del plan de acción: decide, posición por posición, si se mantiene, se reduce o se vende.

Reglas mecánicas y explícitas (se informan con sus cifras; ninguna se aplica a escondidas):
1. Stop dinámico por volatilidad (chandelier sobre cierres) confirmado por tendencia: si el precio cae debajo de
   máximo(últimas 22 sesiones) × (1 − 3 · σ diaria de 20 sesiones) Y debajo de su SMA50, la posición se VENDE. Sin la
   confirmación, una caída general de un día (5-nov: Nasdaq −7 %) vendía también lo que sigue en tendencia alcista.
2. Tendencia bajista (precio < SMA20 < SMA50): se REDUCE a la mitad; si además pierde ≥ 15 % contra su costo, se VENDE.
3. Concentración: ninguna posición por encima de 25 % de la cartera.
4. Volatilidad de la cartera: si la σ anual de lo que queda supera 30 %, todas las posiciones se recortan en la misma
   proporción hasta llegar a ese objetivo.
5. Reglas del Reto: si las ventas dejaran menos de 5 emisoras, se conserva una parte mínima de las de menor volatilidad.
Lo que se libera se reinvierte en las emisoras de la propuesta de referencia que estén en tendencia alcista
(precio > SMA50 y SMA20 > SMA50) y no tengan señal de venta; si ninguna pasa el filtro, queda en efectivo.

Son reglas de control de pérdidas, no un pronóstico: reducen caídas grandes a cambio de vender a veces antes de un
rebote. Ninguna regla garantiza utilidad. La terminal no envía órdenes.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import mercado, reto
from .config import Ajustes

REGLAS = {"ventana_maximo": 22, "ventana_sigma": 20, "k_sigma": 3.0, "sma_corta": 20, "sma_larga": 50,
          "perdida_costo": 0.15, "peso_max": 0.25, "vol_objetivo": 0.30, "peso_minimo_reto": 0.02,
          "modo_venta": "estricta", "afines_sector": True, "afines_max": 3, "efectivo_a_invertir": 0.10}
MODOS_VENTA = {"estricta": "vende todo cuando rompe el stop", "suave": "reduce a la mitad en lugar de vender todo"}
DIAS = 252


def reglas(ajustes: Ajustes, con=None) -> dict:
    """Reglas vigentes: las de fábrica, la configuración y, si hay base, el modo de venta que eligió el usuario."""
    r = {**REGLAS, **(ajustes.get("gestion_riesgo") or {})}
    if con is not None:
        f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='gestion_riesgo'").fetchone()
        if f:
            import json
            r.update({k: v for k, v in json.loads(f[0]).items() if k == "modo_venta" and v in MODOS_VENTA})
    return r


def _serie(P: pd.DataFrame, iid: str, precio: float | None) -> pd.Series:
    """Cierres diarios en MXN con el precio de la valuación de hoy como último punto."""
    s = P[iid].dropna() if iid in P.columns else pd.Series(dtype=float)
    if precio and precio > 0:
        hoy = pd.Timestamp.today().normalize()
        s = pd.concat([s[s.index < hoy], pd.Series([float(precio)], index=[hoy])])
    return s


def indicadores(s: pd.Series, r: dict) -> dict | None:
    if len(s) < r["sma_larga"] + 1:
        return None
    precio = float(s.iloc[-1])
    sigma = float(s.pct_change().tail(r["ventana_sigma"]).std())
    maximo = float(s.tail(r["ventana_maximo"]).max())
    sma_c, sma_l = float(s.tail(r["sma_corta"]).mean()), float(s.tail(r["sma_larga"]).mean())
    return {"precio": precio, "sigma_diaria": sigma, "maximo": maximo, "stop": maximo * (1 - r["k_sigma"] * sigma),
            "sma_corta": sma_c, "sma_larga": sma_l, "bajista": precio < sma_c < sma_l,
            "alcista": precio > sma_l and sma_c > sma_l, "vol_anual": sigma * math.sqrt(DIAS),
            "rend_3m": precio / float(s.iloc[-64]) - 1 if len(s) > 63 else None}


def evaluar(con, ajustes: Ajustes, cartera: dict, propuesta: dict | None = None) -> dict:
    r = reglas(ajustes, con)
    suave = r["modo_venta"] == "suave"  # las señales de venta total reducen a la mitad
    total = float(cartera.get("valor_total") or 0)
    pos = [p for p in cartera.get("posiciones") or [] if (p.get("cantidad") or 0) > 0 and (p.get("valor_mxn") or 0) > 0
           and not str(p["instrumento_id"]).startswith("FONDO:")]
    if total <= 0 or not pos:
        return {"activo": False, "motivo": "sin posiciones valuadas", "posiciones": [], "filas": [], "reglas": r}
    cand = [a["id"] for a in (propuesta or {}).get("pesos") or [] if a.get("peso", 0) > 0]
    afines = _afines([p["instrumento_id"] for p in pos]) if r["afines_sector"] else {}
    ids = list(dict.fromkeys([p["instrumento_id"] for p in pos] + cand + list(afines)))
    P = mercado.precios_mxn(con, ajustes, ids, ajustados="splits")
    filas, sin_dato = [], []
    for p in pos:
        iid, peso = p["instrumento_id"], float(p["valor_mxn"]) / total
        ind = indicadores(_serie(P, iid, p.get("precio_mxn")), r)
        f = {"id": iid, "clave": p.get("clave_operable") or iid, "peso_actual": peso, "peso_objetivo": peso,
             "perdida_costo": p.get("no_realizado_pct"), "motivos": [], "regla": None, **(ind or {})}
        if not ind:
            sin_dato.append(f["clave"])
            f["motivos"].append("Sin historia suficiente para evaluar el riesgo: se mantiene.")
            filas.append(f)
            continue
        perdida = float(p.get("no_realizado_pct") or 0)
        if ind["precio"] < ind["stop"] and ind["precio"] < ind["sma_larga"]:
            f["peso_objetivo"], f["regla"] = (peso / 2 if suave else 0.0), "stop"
            f["motivos"].append(f"Rompió su stop: precio {ind['precio']:,.2f} < {ind['stop']:,.2f} (máximo de "
                                f"{r['ventana_maximo']} sesiones {ind['maximo']:,.2f} − {r['k_sigma']:g}× su volatilidad diaria "
                                f"de {ind['sigma_diaria']:.1%}) y está debajo de su SMA{r['sma_larga']} ({ind['sma_larga']:,.2f})."
                                + (" Modo suave: se reduce a la mitad." if suave else ""))
        elif ind["bajista"] and perdida <= -r["perdida_costo"]:
            f["peso_objetivo"], f["regla"] = (peso / 2 if suave else 0.0), "tendencia_perdida"
            f["motivos"].append(f"Tendencia bajista (precio < SMA{r['sma_corta']} < SMA{r['sma_larga']}) y pierde "
                                f"{abs(perdida):.0%} contra su costo." + (" Modo suave: se reduce a la mitad." if suave else ""))
        elif ind["bajista"]:
            f["peso_objetivo"], f["regla"] = peso / 2, "tendencia"
            f["motivos"].append(f"Tendencia bajista (precio < SMA{r['sma_corta']} < SMA{r['sma_larga']}): se reduce a la mitad.")
        if f["peso_objetivo"] > r["peso_max"]:
            f["peso_objetivo"] = r["peso_max"]
            f["regla"] = f["regla"] or "concentracion"
            f["motivos"].append(f"Concentración: {peso:.0%} de la cartera; el tope de riesgo es {r['peso_max']:.0%}.")
        filas.append(f)

    # 4) volatilidad de la cartera con los pesos que quedan
    R = P[[f["id"] for f in filas if f["id"] in P.columns]].ffill(limit=3).pct_change(fill_method=None).tail(60).dropna(how="all")
    w = pd.Series({f["id"]: f["peso_objetivo"] for f in filas}).reindex(R.columns).fillna(0.0)
    cov = R.fillna(0.0).cov().values * DIAS
    vol_antes = float(math.sqrt(max(w.values @ cov @ w.values, 0.0))) if len(w) else 0.0
    w_actual = pd.Series({f["id"]: f["peso_actual"] for f in filas}).reindex(R.columns).fillna(0.0)
    vol_actual = float(math.sqrt(max(w_actual.values @ cov @ w_actual.values, 0.0))) if len(w_actual) else 0.0
    factor = min(1.0, r["vol_objetivo"] / vol_antes) if vol_antes > 0 else 1.0
    if factor < 0.999:
        for f in filas:
            if f["peso_objetivo"] > 0:
                f["peso_objetivo"] *= factor
                f["motivos"].append(f"La cartera tendría {vol_antes:.0%} de volatilidad anual (objetivo {r['vol_objetivo']:.0%}): "
                                    f"todas las posiciones se recortan al {factor:.0%}.")
                f["regla"] = f["regla"] or "volatilidad"

    # Reinversión: emisoras de la propuesta en tendencia alcista y sin señal de venta
    minimo = int(((reto.config().get("reglas") or {}).get("min_emisoras") or 5)) if reto.activo() else 0
    liberado = sum(f["peso_actual"] - f["peso_objetivo"] for f in filas)
    # 10-nov-2026 (decisión del usuario): además de lo que liberan las ventas, se invierte hasta `efectivo_a_invertir`
    # de la cartera con el efectivo libre, en emisoras que van al alza.
    efectivo_usado = min(max(float(cartera.get("efectivo") or 0) / total, 0.0), r["efectivo_a_invertir"])
    liberado += efectivo_usado
    vender = {f["id"] for f in filas if f["peso_objetivo"] < f["peso_actual"] - 1e-9}
    compras = []
    if liberado > 0.005 and (propuesta or afines):
        objetivo_prop = {a["id"]: float(a["peso"]) for a in (propuesta or {}).get("pesos") or [] if a.get("peso", 0) > 0}
        peso_afin = (sum(objetivo_prop.values()) / len(objetivo_prop)) if objetivo_prop else 0.1
        for iid in afines:
            objetivo_prop.setdefault(iid, peso_afin)
        aptas = {}
        for iid, wp in objetivo_prop.items():
            if iid in vender:
                continue
            ind = indicadores(_serie(P, iid, None), r)
            if ind and ind["alcista"] and not (ind["precio"] < ind["stop"] and ind["precio"] < ind["sma_larga"]):
                aptas[iid] = (wp, ind)
        # De las afines entra la que más subió en 3 meses por cada posición (XOM → la mejor petrolera), y como máximo
        # `afines_max`, priorizando las posiciones que más pesan: menos órdenes diminutas.
        solo_afin = [i for i in aptas if i in afines and i not in {a["id"] for a in (propuesta or {}).get("pesos") or []}]
        mejor = {}
        for i in sorted(solo_afin, key=lambda i: -(aptas[i][1].get("rend_3m") or 0)):
            mejor.setdefault(afines[i]["de"], i)
        peso_de = {f["id"]: f["peso_actual"] for f in filas}
        quedan = set(sorted(mejor.values(), key=lambda i: -peso_de.get(afines[i]["de"], 0))[:r["afines_max"]])
        for i in solo_afin:
            if i not in quedan:
                del aptas[i]
        suma = sum(wp for wp, _ in aptas.values())
        if minimo and len({f["id"] for f in filas if f["peso_objetivo"] > 0} | set(aptas)) < minimo:
            _minimo_reto(filas, minimo, r)
            liberado = sum(f["peso_actual"] - f["peso_objetivo"] for f in filas) + efectivo_usado
        actuales = {f["id"]: f for f in filas}
        for iid, (wp, ind) in aptas.items():
            extra = liberado * wp / suma
            base = actuales[iid]["peso_objetivo"] if iid in actuales else 0.0
            nuevo = min(base + extra, r["peso_max"])
            if nuevo - base > 0.005:
                origen = (f"del mismo sector que {afines[iid]['de']} ({afines[iid]['sector']})" if iid in afines
                          and iid not in {a["id"] for a in (propuesta or {}).get("pesos") or []}
                          else f"de la propuesta «{(propuesta or {}).get('nombre', '')}»")
                compras.append({"id": iid, "peso_actual": actuales[iid]["peso_actual"] if iid in actuales else 0.0,
                                "peso_objetivo": nuevo, "afin": iid in afines and "propuesta" not in origen,
                                "afin_de": (afines.get(iid) or {}).get("de"),
                                "motivo": f"Reinversión en tendencia alcista (precio > SMA{r['sma_larga']} "
                                f"y SMA{r['sma_corta']} > SMA{r['sma_larga']}) {origen}.",
                                **{k: ind[k] for k in ("precio", "sma_corta", "sma_larga", "vol_anual", "rend_3m")}})

    if minimo and not compras and len([f for f in filas if f["peso_objetivo"] > 0]) < minimo:
        _minimo_reto(filas, minimo, r)
    ins = mercado.instrumentos(con)
    salida = []
    for f in filas:
        delta = f["peso_objetivo"] - f["peso_actual"]
        accion = "vender" if delta < -0.005 else "mantener"
        salida.append({"id": f["id"], "clave_operable": f["clave"], "peso_actual": f["peso_actual"],
                       "peso_objetivo": f["peso_objetivo"], "delta_pp": delta * 100, "monto_mxn": delta * total,
                       "accion": accion, "nota": " ".join(f["motivos"]) or "Sin señal de riesgo: se mantiene.",
                       **_corto(f, accion, r), "vol_anual": f.get("vol_anual")})
    for c in compras:
        delta = c["peso_objetivo"] - c["peso_actual"]
        salida.append({"id": c["id"], "clave_operable": (ins.get(c["id"]) or {}).get("clave_operable") or c["id"],
                       "peso_actual": c["peso_actual"], "peso_objetivo": c["peso_objetivo"], "delta_pp": delta * 100,
                       "monto_mxn": delta * total, "accion": "comprar", "nota": c["motivo"],
                       "motivo_corto": "Va al alza" + (f" ({c['rend_3m']:+.0%} en 3 meses)" if c.get("rend_3m") is not None else "")
                                       + (f" y es del mismo sector que {c['afin_de'].split(':')[-1]}." if c.get("afin")
                                          else " y está en la propuesta Markowitz."),
                       "invalida": f"No compres si cae debajo de ${c['sma_larga']:,.2f} (su promedio de 50 días).",
                       "vol_anual": c.get("vol_anual"), "rend_3m": c.get("rend_3m")})
    _emparejar(salida)
    finales = {**{f["id"]: f["peso_objetivo"] for f in filas}, **{c["id"]: c["peso_objetivo"] for c in compras}}
    Rf = P[[i for i in finales if i in P.columns]].ffill(limit=3).pct_change(fill_method=None).tail(60).fillna(0.0)
    w_final = pd.Series(finales).reindex(Rf.columns).fillna(0.0).values
    vol_final = float(math.sqrt(max(w_final @ (Rf.cov().values * DIAS) @ w_final, 0.0))) if len(w_final) else 0.0
    perdida_total = float(cartera.get("resultado_total") or 0) / float(cartera.get("aportacion_neta") or total)
    ventas = [s for s in salida if s["accion"] == "vender"]
    return {"activo": True, "reglas": r, "filas": salida, "posiciones": filas, "sin_dato": sin_dato,
            "ordenes": bool(ventas or compras), "liberado": liberado, "efectivo_usado": efectivo_usado,
            "afines_comprados": [c["id"] for c in compras if c.get("afin")], "efectivo_resultante": liberado - sum(
                c["peso_objetivo"] - c["peso_actual"] for c in compras),
            "cartera": {"vol_actual": vol_actual, "vol_despues": vol_final, "resultado_total": perdida_total,
                        "valor_total": total},
            "nota": "Reglas de control de pérdidas, no un pronóstico: reducen caídas grandes a cambio de vender a veces antes "
                    "de un rebote. Ninguna regla garantiza utilidad."}


def _corto(f: dict, accion: str, r: dict) -> dict:
    """Motivo e invalidación en una línea, con el precio que cambia la decisión."""
    regla, stop = f.get("regla"), f.get("stop")
    if "stop" not in f:
        return {"motivo_corto": "Sin historia suficiente para evaluar el riesgo.", "invalida": "—"}
    motivo = {"stop": f"Cayó debajo de su stop (${stop:,.2f}) y de su promedio de 50 días.",
              "tendencia_perdida": f"Va a la baja y pierde {abs(f.get('perdida_costo') or 0):.0%} contra tu costo.",
              "tendencia": "Va a la baja (debajo de sus promedios de 20 y 50 días): reducir a la mitad.",
              "concentracion": f"Pesa {f['peso_actual']:.0%} de tu cartera; el tope es {r['peso_max']:.0%}.",
              "volatilidad": "Recorte para bajar la volatilidad de la cartera."}.get(regla, "Sin señal de riesgo.")
    if r["modo_venta"] == "suave" and regla in ("stop", "tendencia_perdida") and accion == "vender":
        motivo += " Modo suave: reducir a la mitad."
    if accion == "mantener" and f["peso_objetivo"] > 0 and any("mínimo de" in m for m in f["motivos"]):
        motivo = "Se conserva una parte para cumplir el mínimo de 5 emisoras del Reto."
    if accion == "vender":
        invalida = (f"No vendas si antes de la orden vuelve arriba de ${stop:,.2f}." if regla == "stop"
                    else f"No vendas si vuelve arriba de ${f['sma_corta']:,.2f} (su promedio de 20 días).")
    else:
        invalida = f"Vender si cae debajo de ${stop:,.2f} y de ${f['sma_larga']:,.2f} (promedio de 50 días)."
    return {"motivo_corto": motivo, "invalida": invalida}


def _emparejar(salida: list[dict]) -> None:
    """Qué compra reemplaza a qué venta: el dinero de cada venta (de la mayor a la menor) se asigna a las compras en
    orden, como un flujo de efectivo. Cada fila recibe `reemplazo` con instrumento y porqué."""
    ventas = sorted([s for s in salida if s["accion"] == "vender"], key=lambda s: s["monto_mxn"])
    compras = sorted([s for s in salida if s["accion"] == "comprar"], key=lambda s: -s["monto_mxn"])
    resto = {c["id"]: c["monto_mxn"] for c in compras}
    for v in ventas:
        falta, parejas = -v["monto_mxn"], []
        for c in compras:
            if falta <= 1 or resto[c["id"]] <= 1:
                continue
            m = min(falta, resto[c["id"]])
            resto[c["id"]] -= m
            falta -= m
            parejas.append((c, m))
        if not parejas:
            v["reemplazo"] = "Efectivo (ninguna emisora de la propuesta va al alza hoy)."
            continue
        v["reemplazo"] = "; ".join(
            f"{_clave(c)} (≈ ${m:,.0f}): va al alza" + (f" {c['rend_3m']:+.0%} en 3 meses" if c.get("rend_3m") is not None else "")
            + (f", volatilidad {c['vol_anual']:.0%} frente a {v['vol_anual']:.0%}" if c.get("vol_anual") and v.get("vol_anual") else "")
            for c, m in parejas)
        for c, m in parejas:
            c.setdefault("_reemplaza", []).append(_clave(v))
    for c in compras:
        c["reemplazo"] = ("Reemplaza a " + ", ".join(c.pop("_reemplaza")) + ".") if c.get("_reemplaza") else "Nueva posición."
    for s in salida:
        s.setdefault("reemplazo", "—")


def _afines(tenidos: list[str]) -> dict:
    """Emisoras del mismo grupo SIC de la SEC (2 dígitos, `config/sectores.csv`) que alguna posición; sin BMV (sin sector)."""
    import csv
    from pathlib import Path
    try:
        filas = list(csv.DictReader((Path(__file__).resolve().parent.parent / "config/sectores.csv").open(encoding="utf-8")))
    except OSError:
        return {}
    grupo = {f["id"]: (f["codigo_sic"][:2], f["sector"]) for f in filas if f.get("codigo_sic")}
    out = {}
    for t in tenidos:
        if t not in grupo:
            continue
        for iid, (g2, sector) in grupo.items():
            if g2 == grupo[t][0] and iid not in tenidos:
                out.setdefault(iid, {"de": t, "sector": grupo[t][1]})
    return out


def _clave(s: dict) -> str:
    return str(s.get("clave_operable") or s["id"]).replace(" *", "")


def _minimo_reto(filas: list[dict], minimo: int, r: dict) -> None:
    """Si las ventas dejaran menos emisoras que el mínimo del Reto, se conserva una parte de las de menor volatilidad."""
    for f in sorted([f for f in filas if f["peso_objetivo"] == 0], key=lambda f: f.get("sigma_diaria") or 9):
        if len([x for x in filas if x["peso_objetivo"] > 0]) >= minimo:
            break
        f["peso_objetivo"] = min(f["peso_actual"], r["peso_minimo_reto"])
        f["motivos"].append(f"Se conserva {f['peso_objetivo']:.0%} para cumplir el mínimo de {minimo} emisoras del Reto.")


def lineas(g: dict) -> list[str]:
    """Resumen en lenguaje sencillo para el plan de Telegram."""
    if not g.get("activo"):
        return []
    c = g["cartera"]
    out = [f"🛡️ Gestión de riesgo: tu cartera va {c['resultado_total']:+.1%} desde el inicio; su volatilidad es "
           f"{c['vol_actual']:.0%} al año" + (f" y quedaría en {c['vol_despues']:.0%} con este plan." if g["ordenes"] else ".")]
    for f in g["posiciones"]:
        if f["peso_objetivo"] < f["peso_actual"] - 0.005:
            que = "VENDER TODO" if f["peso_objetivo"] == 0 else f"REDUCIR de {f['peso_actual']:.0%} a {f['peso_objetivo']:.0%}"
            out.append(f"  • {f['clave'].replace(' *', '')}: {que}. {f['motivos'][0]}")
    if g.get("afines_comprados") or g.get("efectivo_usado"):
        out.append("  🔄 Cambio en el plan (desde el 11-11): las compras ya no solo usan el dinero de las ventas; también "
                   f"invierten hasta {g['reglas']['efectivo_a_invertir']:.0%} de tu cuenta con el efectivo libre, y además de la "
                   "propuesta Markowitz pueden incluir emisoras del mismo sector que las que ya tienes (por ejemplo, petroleras "
                   "como XOM) si van al alza y no rompieron su stop."
                   + (f" Hoy entra por sector: {', '.join(i.split(':')[-1] for i in g['afines_comprados'])}."
                      if g.get("afines_comprados") else ""))
    if not g["ordenes"]:
        out.append("  • Ninguna posición rompió su stop ni está en tendencia bajista: mantener es la decisión de riesgo.")
    elif e := evidencia(g["reglas"].get("modo_venta", "estricta")):
        out.append(e)
    return out


def evidencia(modo: str = "estricta") -> str | None:
    """Lo medido fuera de muestra (`terminal.validacion_riesgo`): el plan dice cuánto cuesta y cuánto protege vender."""
    import json
    from pathlib import Path
    try:
        datos = json.loads((Path(__file__).resolve().parent.parent / "docs/evidencia/validacion-riesgo.json").read_text("utf-8"))
        e = next(x for x in datos if x["perfil"] == "concentrada" and x["dias"] == 30)
        m = e["variantes"]["mantener"]
        v = e["variantes"]["reglas suaves + reinversión" if modo == "suave" else "reglas + reinversión"]
    except (OSError, ValueError, KeyError, StopIteration):
        return None
    return (f"  ⚖️ Lo medido en {e['pruebas']} carteras del pasado a {e['dias']} sesiones: seguir estas ventas dejó en promedio "
            f"{v['media']:+.1%} frente a {m['media']:+.1%} de mantener; a cambio, en un mal escenario (1 de cada 10) perdió "
            f"{v['p10']:.1%} en lugar de {m['p10']:.1%}. Vender protege de caídas grandes, no aumenta la ganancia esperada.")
