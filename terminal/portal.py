"""Captura del portal del Reto Actinver: saldo, efectivo y posiciones que el PARTICIPANTE copia de su cuenta.

Por qué así: el simulador no ofrece API ni exportación pública, y el reglamento (§17) prohíbe robots, scripts, macros y
programas en el portal (descalificación incluso por el intento). La terminal nunca entra al portal ni lee su sesión: el
participante selecciona la tabla de su cuenta, la copia (Ctrl+C) y la pega aquí. La terminal la interpreta, muestra una
vista previa y solo la guarda al confirmarla.

Lo guardado es la «cuenta del Reto según el portal», con su hora del portal y la hora de captura. Mientras no haya
captura, la cartera de la terminal es un registro LOCAL (aportación y operaciones capturadas a mano) y así se rotula.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import sqlite3
import unicodedata
from datetime import UTC, datetime

import pandas as pd

from . import cotizaciones, reto
from .db import auditar, transaccion

FUENTE = "captura manual del portal del Reto (copiar y pegar)"
TOLERANCIA_CUADRE = 0.01  # 1 %: posiciones + efectivo frente al valor total del portal

COLUMNAS = {
    "emisora": ("emisora", "instrumento", "pizarra", "clave", "simbolo", "ticker", "valor/serie", "emisora/serie"),
    "serie": ("serie",),
    "titulos": ("titulos", "no. titulos", "num. titulos", "cantidad", "acciones", "posicion", "titulos disponibles",
                "tenencia"),
    "costo_promedio": ("costo promedio", "precio promedio", "costo prom", "costo prom.", "precio de compra",
                       "costo unitario", "precio costo"),
    "precio": ("precio actual", "ultimo precio", "precio de mercado", "precio mercado", "ultimo", "precio"),
    "valor": ("valor de mercado", "valor mercado", "valuacion", "importe", "valor actual", "monto", "valor"),
}
ETIQUETAS_EFECTIVO = ("efectivo disponible", "saldo en efectivo", "efectivo", "saldo disponible", "disponible")
ETIQUETAS_TOTAL = ("valor del portafolio", "valor total", "total del portafolio", "valuacion total", "saldo total",
                   "valor de la cartera", "total cartera", "portafolio total")
NUMERO = re.compile(r"-?\$?\s*\(?\d[\d,]*(?:\.\d+)?\)?")


class ErrorCaptura(ValueError):
    pass


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t.replace("*", " * ")).strip(" :")


def _numero(t) -> float | None:
    if t is None:
        return None
    s = str(t).strip()
    m = NUMERO.search(s)
    if not m:
        return None
    x = m.group(0)
    neg = x.startswith("-") or (x.startswith("(") or "(" in x)
    x = re.sub(r"[^\d.]", "", x)
    try:
        v = float(x)
    except ValueError:
        return None
    return -v if neg else v


def _filas(texto: str) -> list[list[str]]:
    lineas = [l for l in texto.replace("\r", "").split("\n") if l.strip()]
    if any("\t" in l for l in lineas):  # lo que produce copiar una tabla del navegador
        return [[c.strip() for c in l.split("\t")] for l in lineas]
    if sum(";" in l for l in lineas) >= max(2, len(lineas) // 2):
        return [[c.strip() for c in l.split(";")] for l in lineas]
    if sum("," in l for l in lineas) >= max(2, len(lineas) // 2) and not any(re.search(r"\d,\d{3}", l) for l in lineas):
        return [[c.strip() for c in r] for r in csv.reader(io.StringIO("\n".join(lineas)))]
    return [[c.strip() for c in re.split(r"\s{2,}", l.strip())] for l in lineas]


def _mapa_encabezado(fila: list[str]) -> dict[str, int] | None:
    mapa = {}
    celdas = [_norm(c) for c in fila]
    for campo, sinonimos in COLUMNAS.items():
        for sin in sinonimos:  # los sinónimos más específicos van primero
            idx = next((i for i, c in enumerate(celdas) if c == sin and i not in mapa.values()), None)
            if idx is None:
                idx = next((i for i, c in enumerate(celdas) if c.startswith(sin) and i not in mapa.values()), None)
            if idx is not None:
                mapa[campo] = idx
                break
    return mapa if "emisora" in mapa and "titulos" in mapa else None


def _etiqueta(linea: str, etiquetas: tuple) -> float | None:
    """Número que acompaña a una etiqueta al inicio de la línea («Efectivo disponible: $12,345.67»)."""
    n = _norm(linea)
    for e in etiquetas:
        if n.startswith(e):
            nums = [x for x in (_numero(p) for p in re.split(r"	|:| {2,}", linea)[1:]) if x is not None]
            if nums:
                return nums[-1]
    return None


def interpretar(texto: str, instrumentos: dict[str, dict]) -> dict:
    """Interpreta lo pegado desde el portal. No guarda nada."""
    if not texto or not texto.strip():
        raise ErrorCaptura("Pegue el contenido copiado de su cuenta del Reto.")
    if len(texto) > 200_000:
        raise ErrorCaptura("El texto pegado es demasiado largo (máx. 200 000 caracteres).")
    filas = _filas(texto)
    efectivo = total = None
    for l in texto.replace("\r", "").split("\n"):
        if efectivo is None:
            efectivo = _etiqueta(l, ETIQUETAS_EFECTIVO)
        if total is None:
            total = _etiqueta(l, ETIQUETAS_TOTAL)
    mapa, posiciones, no_reconocidas = None, [], []
    for fila in filas:
        m = _mapa_encabezado(fila)
        if m:
            mapa = m
            continue
        if not mapa or len(fila) <= max(mapa.values()):
            continue
        texto_emisora = fila[mapa["emisora"]].strip()
        if "serie" in mapa and fila[mapa["serie"]].strip():
            texto_emisora = f"{texto_emisora} {fila[mapa['serie']].strip()}"
        if not texto_emisora or _norm(texto_emisora).startswith(("total", "subtotal")):
            continue
        titulos = _numero(fila[mapa["titulos"]])
        if titulos is None:
            continue
        try:
            n = cotizaciones.normalizar_simbolo(texto_emisora.replace("*", " *").replace("  ", " "), instrumentos)
        except ValueError:
            n = None
        if not n:
            no_reconocidas.append(texto_emisora)
            continue
        pos = {"instrumento_id": n["instrumento_id"], "texto": texto_emisora[:40], "titulos": titulos,
               "costo_promedio": _numero(fila[mapa["costo_promedio"]]) if "costo_promedio" in mapa else None,
               "precio": _numero(fila[mapa["precio"]]) if "precio" in mapa else None,
               "valor": _numero(fila[mapa["valor"]]) if "valor" in mapa else None}
        if pos["valor"] is None and pos["precio"] is not None:
            pos["valor"] = round(pos["titulos"] * pos["precio"], 2)
        posiciones.append(pos)
    advertencias = []
    if not mapa and efectivo is None and total is None:
        raise ErrorCaptura("No se reconoció una tabla de posiciones (con columnas de emisora y títulos) ni un saldo. "
                           "Copie la tabla completa, incluidos los encabezados.")
    vistos = {}
    for p in posiciones:
        if p["instrumento_id"] in vistos:
            advertencias.append(f"{p['instrumento_id']} aparece dos veces; se suman los títulos.")
            q = vistos[p["instrumento_id"]]
            q["titulos"] += p["titulos"]
            q["valor"] = (q["valor"] or 0) + (p["valor"] or 0)
        else:
            vistos[p["instrumento_id"]] = p
    posiciones = list(vistos.values())
    if any(p["titulos"] < 0 or p["titulos"] != int(p["titulos"]) for p in posiciones):
        advertencias.append("Hay títulos negativos o fraccionarios; revise lo pegado.")
    suma = sum(p["valor"] or 0 for p in posiciones)
    if total and efectivo is not None and posiciones and all(p["valor"] is not None for p in posiciones):
        dif = (suma + efectivo) / total - 1
        if abs(dif) > TOLERANCIA_CUADRE:
            advertencias.append(f"Posiciones + efectivo ({suma + efectivo:,.2f}) no cuadran con el valor total "
                                f"({total:,.2f}): diferencia {dif:+.2%}.")
    if total is None and efectivo is not None and posiciones and all(p["valor"] is not None for p in posiciones):
        total = round(suma + efectivo, 2)
        advertencias.append("El valor total se calculó como posiciones + efectivo (el texto no lo traía).")
    if no_reconocidas:
        advertencias.append(f"Emisoras no reconocidas (no se guardan): {', '.join(no_reconocidas[:10])}.")
    if efectivo is None:
        advertencias.append("No se encontró el efectivo; copie también la línea «Efectivo» o captúrelo abajo.")
    return {"valor_portafolio": total, "efectivo": efectivo, "posiciones": posiciones, "no_reconocidas": no_reconocidas,
            "advertencias": advertencias, "tabla_reconocida": bool(mapa)}


def guardar(con: sqlite3.Connection, texto: str, hora_portal: str, instrumentos: dict, efectivo: float | None = None,
            valor_portafolio: float | None = None, confirmar: bool = False) -> dict:
    """Vista previa (confirmar=False) o registro de la captura. Nunca adivina: exige hora del portal y valor total."""
    r = interpretar(texto, instrumentos) if texto and texto.strip() else {
        "valor_portafolio": None, "efectivo": None, "posiciones": [], "no_reconocidas": [], "advertencias": [],
        "tabla_reconocida": False}
    if efectivo is not None:
        r["efectivo"] = efectivo
    if valor_portafolio is not None:
        r["valor_portafolio"] = valor_portafolio
    errores = []
    try:
        t = pd.Timestamp(hora_portal)
        t = t.tz_localize("America/Mexico_City") if t.tzinfo is None else t
        if t.tz_convert("UTC") > pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=5):
            errores.append("hora_portal: está en el futuro")
        hora = t.isoformat()
    except (ValueError, TypeError):
        errores.append("hora_portal: indique la fecha y hora que muestra el portal")
        hora = None
    if not r["valor_portafolio"] or r["valor_portafolio"] <= 0:
        errores.append("valor del portafolio: no se encontró; cópielo con la tabla o captúrelo")
    r.update(hora_portal=hora, errores=errores, fuente=FUENTE, confirmado=False)
    if not confirmar or errores:
        return r
    ahora = datetime.now(UTC).isoformat(timespec="seconds")
    etapa = reto.etapa_operativa() if reto.activo() else None
    huella = hashlib.sha256(f"{hora}|{r['valor_portafolio']}|{r['efectivo']}|"
                            f"{sorted((p['instrumento_id'], p['titulos']) for p in r['posiciones'])}".encode()).hexdigest()[:16]
    if con.execute("SELECT 1 FROM capturas_portal WHERE huella=?", (huella,)).fetchone():
        r["errores"] = ["Esta captura ya estaba registrada (misma hora, saldo y posiciones)."]
        return r
    with transaccion(con):
        s = con.execute("INSERT INTO saldos_portal (capturado_en, hora_portal, etapa, valor_portafolio, efectivo, nota) "
                        "VALUES (?,?,?,?,?,?)", (ahora, hora, etapa, r["valor_portafolio"], r["efectivo"], FUENTE))
        c = con.execute("INSERT INTO capturas_portal (capturado_en, hora_portal, etapa, valor_portafolio, efectivo, fuente, "
                        "n_posiciones, tabla_reconocida, saldo_id, huella) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (ahora, hora, etapa, r["valor_portafolio"], r["efectivo"], FUENTE, len(r["posiciones"]),
                         int(r["tabla_reconocida"]), s.lastrowid, huella))
        con.executemany("INSERT INTO posiciones_portal (captura_id, instrumento_id, texto, titulos, costo_promedio, precio, "
                        "valor) VALUES (?,?,?,?,?,?,?)",
                        [(c.lastrowid, p["instrumento_id"], p["texto"], p["titulos"], p["costo_promedio"], p["precio"],
                          p["valor"]) for p in r["posiciones"]])
        auditar(con, "captura_portal", c.lastrowid, "alta",
                despues={"hora_portal": hora, "valor": r["valor_portafolio"], "efectivo": r["efectivo"],
                         "posiciones": len(r["posiciones"])})
    r.update(id=c.lastrowid, confirmado=True, capturado_en=ahora)
    return r


def captura(con: sqlite3.Connection, cid: int | None = None) -> dict | None:
    f = con.execute("SELECT * FROM capturas_portal WHERE id=?" if cid else
                    "SELECT * FROM capturas_portal ORDER BY hora_portal DESC, id DESC LIMIT 1", (cid,) if cid else ()).fetchone()
    if not f:
        return None
    d = dict(f)
    d["posiciones"] = [dict(p) for p in con.execute("SELECT * FROM posiciones_portal WHERE captura_id=? ORDER BY valor DESC",
                                                    (d["id"],))]
    return d


def anterior(con: sqlite3.Connection, c: dict) -> dict | None:
    f = con.execute("SELECT id FROM capturas_portal WHERE (hora_portal < ? OR (hora_portal = ? AND id < ?)) "
                    "ORDER BY hora_portal DESC, id DESC LIMIT 1", (c["hora_portal"], c["hora_portal"], c["id"])).fetchone()
    return captura(con, f["id"]) if f else None


def cambios(prev: dict | None, act: dict) -> list[str]:
    """Diferencias legibles entre dos capturas (saldo, efectivo y títulos por emisora)."""
    if not prev:
        return [f"Primera captura del portal: valor {act['valor_portafolio']:,.2f}, efectivo "
                f"{(act['efectivo'] or 0):,.2f}, {act['n_posiciones']} posiciones."]
    out = []
    for campo, nombre in (("valor_portafolio", "Valor del portafolio"), ("efectivo", "Efectivo")):
        a, b = prev.get(campo), act.get(campo)
        if a is not None and b is not None and abs(b - a) >= 0.01:
            out.append(f"{nombre}: {a:,.2f} → {b:,.2f} ({b - a:+,.2f}; {b / a - 1 if a else 0:+.2%}).")
    pa = {p["instrumento_id"]: p["titulos"] for p in prev["posiciones"]}
    pb = {p["instrumento_id"]: p["titulos"] for p in act["posiciones"]}
    if act.get("tabla_reconocida") or prev.get("tabla_reconocida"):
        for i in sorted(set(pa) | set(pb)):
            a, b = pa.get(i, 0), pb.get(i, 0)
            if abs(b - a) > 1e-9:
                tipo = "nueva posición" if not a else ("posición cerrada" if not b else "cambio de títulos")
                out.append(f"{i.split(':', 1)[-1]}: {a:,.0f} → {b:,.0f} títulos ({tipo}).")
    return out


def cartera(con: sqlite3.Connection, cot: dict, c: dict) -> dict:
    """Cartera con la forma de `cartera.calcular`, construida con la captura del portal (títulos y efectivo del Reto)
    y valuada con el último precio de la terminal; si no hay precio vigente, con el que mostraba el portal."""
    filas, valor_pos, sin_precio = [], 0.0, []
    for p in c["posiciones"]:
        if p["titulos"] <= 0:
            continue
        q = cot.get(p["instrumento_id"], {})
        precio = q.get("precio_mxn") if q.get("estado") not in (None, "sin_datos", "vencido") else None
        origen_precio = "terminal"
        if precio is None and p["precio"]:
            precio, origen_precio = p["precio"], "portal"
        valor = p["titulos"] * precio if precio else None
        if valor is None:
            sin_precio.append(p["instrumento_id"])
        else:
            valor_pos += valor
        costo = (p["costo_promedio"] or 0) * p["titulos"]
        nr = (valor - costo) if (valor is not None and p["costo_promedio"]) else None
        filas.append({"instrumento_id": p["instrumento_id"], "cantidad": p["titulos"], "costo_total": round(costo, 2),
                      "costo_promedio": p["costo_promedio"], "precio_mxn": precio, "origen_precio": origen_precio,
                      "valor_mxn": None if valor is None else round(valor, 2), "valor_portal": p["valor"],
                      "no_realizado": None if nr is None else round(nr, 2),
                      "no_realizado_pct": None if (nr is None or not costo) else round(nr / costo, 6),
                      "realizado": 0.0, "dividendos": 0.0, "comisiones": 0.0})
    efectivo = float(c["efectivo"] or 0)
    total = efectivo + valor_pos
    for f in filas:
        f["peso"] = round(f["valor_mxn"] / total, 6) if (f["valor_mxn"] is not None and total > 0) else None
    capital = float(reto.config().get("capital") or 0) if reto.activo() else float(c["valor_portafolio"])
    return {"efectivo": round(efectivo, 2), "valor_posiciones": round(valor_pos, 2), "valor_total": round(total, 2),
            "aportaciones": capital, "retiros": 0.0, "aportacion_neta": capital, "realizado": 0.0,
            "no_realizado": round(sum(f["no_realizado"] or 0 for f in filas), 2), "dividendos": 0.0, "comisiones": 0.0,
            "impuestos": 0.0, "resultado_total": round(total - capital, 2),
            "posiciones": sorted(filas, key=lambda f: -(f["valor_mxn"] or 0)), "cerradas": [], "sin_precio": sin_precio,
            "completa": not sin_precio}
