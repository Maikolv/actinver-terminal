"""Seguimiento del inversionista a partir de su libro de operaciones.

Método de costo: costo promedio ponderado (las comisiones e impuestos de compra se suman al
costo; los de venta se restan del ingreso). Todo se expresa en MXN: montos en otra moneda se
convierten con el tipo de cambio capturado en la propia operación.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from .db import ahora, auditar, transaccion

TIPOS = ("aportacion", "retiro", "compra", "venta", "dividendo", "comision", "impuesto", "split")
REQUIERE_INSTRUMENTO = ("compra", "venta", "dividendo", "split")
CAMPOS = ("fecha", "tipo", "instrumento_id", "cantidad", "precio", "monto", "comision", "impuesto", "moneda",
          "tipo_cambio", "nota")
MAX_NOTA = 200
TOL = 1e-9


class ErrorValidacion(ValueError):
    def __init__(self, errores: list[str]):
        super().__init__("; ".join(errores))
        self.errores = errores


def _num(v, campo: str, errores: list[str], minimo: float | None = 0.0) -> float:
    if v in (None, ""):
        return 0.0
    try:
        x = float(str(v).replace(",", "").strip())
    except ValueError:
        errores.append(f"{campo}: «{str(v)[:20]}» no es un número")
        return 0.0
    if not np.isfinite(x):
        errores.append(f"{campo}: valor no finito")
        return 0.0
    if minimo is not None and x < minimo:
        errores.append(f"{campo}: no puede ser negativo")
    return x


def validar(t: dict, instrumentos: dict[str, dict]) -> dict:
    """Valida y normaliza una operación. Tolerante con formatos (espacios, mayúsculas, comas de miles),
    estricto con el significado (tipos, fechas, signos, instrumentos existentes)."""
    e: list[str] = []
    tipo = str(t.get("tipo", "")).strip().lower()
    tipo = {"aportación": "aportacion", "deposito": "aportacion", "depósito": "aportacion"}.get(tipo, tipo)
    if tipo not in TIPOS:
        e.append(f"tipo: debe ser uno de {', '.join(TIPOS)}")
    fecha_txt = str(t.get("fecha", "")).strip()
    try:
        f = date.fromisoformat(fecha_txt[:10])
        if f > date.today():
            e.append("fecha: no puede estar en el futuro")
    except ValueError:
        e.append("fecha: use el formato AAAA-MM-DD")
        f = None
    instr = str(t.get("instrumento_id") or "").strip().upper() or None
    if instr and ":" not in instr:  # admite la clave corta (p. ej. «AAPL»)
        candidatos = [k for k in instrumentos if k.split(":", 1)[1] == instr]
        instr = candidatos[0] if len(candidatos) == 1 else instr
    if tipo in REQUIERE_INSTRUMENTO:
        if not instr:
            e.append("instrumento_id: obligatorio para este tipo")
        elif instr not in instrumentos:
            e.append(f"instrumento_id: «{instr[:30]}» no está en el universo verificado")
    cantidad = _num(t.get("cantidad"), "cantidad", e)
    precio = _num(t.get("precio"), "precio", e)
    monto = _num(t.get("monto"), "monto", e)
    comision = _num(t.get("comision"), "comision", e)
    impuesto = _num(t.get("impuesto"), "impuesto", e)
    tc = _num(t.get("tipo_cambio") or 1, "tipo_cambio", e)
    moneda = str(t.get("moneda") or "MXN").strip().upper()
    if moneda not in ("MXN", "USD"):
        e.append("moneda: solo MXN o USD")
    if moneda == "MXN" and abs(tc - 1) > TOL:
        e.append("tipo_cambio: debe ser 1 cuando la moneda es MXN")
    if moneda == "USD" and tc <= 0:
        e.append("tipo_cambio: obligatorio (> 0) para operaciones en USD")
    if tipo in ("compra", "venta"):
        if cantidad <= 0:
            e.append("cantidad: debe ser mayor que cero")
        if precio <= 0:
            e.append("precio: debe ser mayor que cero")
    if tipo == "split" and cantidad <= 0:
        e.append("cantidad: para split indique el factor (p. ej. 2 para 2:1, 0.1 para 1:10)")
    if tipo in ("aportacion", "retiro", "dividendo", "comision", "impuesto") and monto <= 0:
        e.append("monto: debe ser mayor que cero")
    nota = str(t.get("nota") or "").strip()
    if len(nota) > MAX_NOTA:
        e.append(f"nota: máximo {MAX_NOTA} caracteres")
    if e:
        raise ErrorValidacion(e)
    return {"fecha": f.isoformat(), "tipo": tipo, "instrumento_id": instr if tipo in REQUIERE_INSTRUMENTO else None,
            "cantidad": cantidad, "precio": precio, "monto": monto, "comision": comision, "impuesto": impuesto,
            "moneda": moneda, "tipo_cambio": tc, "nota": nota}


def huella(t: dict, ocurrencia: int = 1) -> str:
    base = json.dumps([t.get(c) for c in CAMPOS if c != "nota"] + [ocurrencia], default=str)
    return hashlib.sha256(base.encode()).hexdigest()


def listar(con: sqlite3.Connection, incluir_anuladas: bool = False, limite: int = 1000) -> list[dict]:
    q = "SELECT * FROM transacciones" + ("" if incluir_anuladas else " WHERE anulada=0") + " ORDER BY fecha, id LIMIT ?"
    return [dict(r) for r in con.execute(q, (min(limite, 5000),))]


def registrar(con: sqlite3.Connection, t: dict, origen: str, ocurrencia: int = 1, validar_saldo: bool = True) -> int | None:
    """Inserta una operación ya validada. Devuelve None si es duplicada (misma huella)."""
    h = huella(t, ocurrencia)
    if con.execute("SELECT 1 FROM transacciones WHERE huella=?", (h,)).fetchone():
        return None
    if validar_saldo and t["tipo"] == "venta":
        calcular(listar(con) + [{**t, "id": 10**12}], {})  # lanza si vende más de lo que tiene
    cur = con.execute(
        "INSERT INTO transacciones (fecha, tipo, instrumento_id, cantidad, precio, monto, comision, impuesto, moneda,"
        " tipo_cambio, nota, origen, huella, creado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (*[t[c] for c in CAMPOS], origen, h, ahora()))
    marcar_tiempos(con, cur.lastrowid, t["fecha"])
    auditar(con, "transaccion", cur.lastrowid, "alta", despues=t, motivo=origen)
    return cur.lastrowid


def marcar_tiempos(con: sqlite3.Connection, tid: int, fecha: str) -> None:
    """Etapa del Reto (práctica / competencia / fuera) y marcas event_time / available_at de una operación confirmada."""
    from . import reto
    cols = {r[1] for r in con.execute("PRAGMA table_info(transacciones)")}
    if "etapa" in cols:
        con.execute("UPDATE transacciones SET etapa=?, event_time=?, available_at=creado_en WHERE id=?",
                    (reto.etapa_de_fecha(fecha), f"{fecha}T00:00:00-06:00", tid))


def anular(con: sqlite3.Connection, tid: int, motivo: str) -> None:
    fila = con.execute("SELECT * FROM transacciones WHERE id=?", (tid,)).fetchone()
    if not fila or fila["anulada"]:
        raise ErrorValidacion(["La operación no existe o ya está anulada"])
    if not motivo.strip():
        raise ErrorValidacion(["motivo: obligatorio para anular"])
    with transaccion(con):
        con.execute("UPDATE transacciones SET anulada=1 WHERE id=?", (tid,))
        try:
            calcular(listar(con), {})
        except ErrorValidacion:
            raise ErrorValidacion(["Anular esta operación deja ventas sin posición suficiente"]) from None
        auditar(con, "transaccion", tid, "anulacion", antes=dict(fila), motivo=motivo[:200])


def corregir(con: sqlite3.Connection, tid: int, nuevos: dict, instrumentos: dict, motivo: str) -> int:
    """Corrige conservando el original: el registro previo queda anulado y el nuevo lo referencia."""
    fila = con.execute("SELECT * FROM transacciones WHERE id=?", (tid,)).fetchone()
    if not fila or fila["anulada"]:
        raise ErrorValidacion(["La operación no existe o ya está anulada"])
    if not motivo.strip():
        raise ErrorValidacion(["motivo: obligatorio para corregir"])
    t = validar({**{c: fila[c] for c in CAMPOS}, **nuevos}, instrumentos)
    with transaccion(con):
        con.execute("UPDATE transacciones SET anulada=1 WHERE id=?", (tid,))
        h = huella(t, ocurrencia=int(con.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]) + 1)
        cur = con.execute(
            "INSERT INTO transacciones (fecha, tipo, instrumento_id, cantidad, precio, monto, comision, impuesto, moneda,"
            " tipo_cambio, nota, origen, huella, reemplaza_id, creado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (*[t[c] for c in CAMPOS], "correccion", h, tid, ahora()))
        marcar_tiempos(con, cur.lastrowid, t["fecha"])
        calcular(listar(con), {})
        auditar(con, "transaccion", tid, "correccion", antes=dict(fila), despues={**t, "nuevo_id": cur.lastrowid},
                motivo=motivo[:200])
    return cur.lastrowid


@dataclass
class Posicion:
    instrumento_id: str
    cantidad: float = 0.0
    costo: float = 0.0  # costo total en MXN de las unidades vigentes
    realizado: float = 0.0
    dividendos: float = 0.0
    comisiones: float = 0.0

    @property
    def costo_promedio(self) -> float:
        return self.costo / self.cantidad if self.cantidad > TOL else 0.0


@dataclass
class Estado:
    efectivo: float = 0.0
    aportaciones: float = 0.0
    retiros: float = 0.0
    comisiones: float = 0.0
    impuestos: float = 0.0
    dividendos: float = 0.0
    posiciones: dict[str, Posicion] = field(default_factory=dict)


def aplicar(est: Estado, t: dict) -> None:
    tc = float(t.get("tipo_cambio") or 1)
    tipo = t["tipo"]
    if tipo == "aportacion":
        est.efectivo += t["monto"] * tc
        est.aportaciones += t["monto"] * tc
        return
    if tipo == "retiro":
        est.efectivo -= t["monto"] * tc
        est.retiros += t["monto"] * tc
        return
    if tipo == "comision":
        est.efectivo -= t["monto"] * tc
        est.comisiones += t["monto"] * tc
        return
    if tipo == "impuesto":
        est.efectivo -= t["monto"] * tc
        est.impuestos += t["monto"] * tc
        return
    p = est.posiciones.setdefault(t["instrumento_id"], Posicion(t["instrumento_id"]))
    com, imp = t.get("comision", 0) * tc, t.get("impuesto", 0) * tc
    est.comisiones += com
    est.impuestos += imp
    p.comisiones += com
    if tipo == "compra":
        bruto = t["cantidad"] * t["precio"] * tc
        p.cantidad += t["cantidad"]
        p.costo += bruto + com + imp
        est.efectivo -= bruto + com + imp
    elif tipo == "venta":
        if t["cantidad"] > p.cantidad + TOL:
            raise ErrorValidacion([f"venta de {t['cantidad']:g} {t['instrumento_id']} el {t['fecha']} excede la "
                                   f"posición disponible ({p.cantidad:g})"])
        bruto = t["cantidad"] * t["precio"] * tc
        costo_salida = p.costo_promedio * t["cantidad"]
        p.realizado += bruto - com - imp - costo_salida
        p.costo -= costo_salida
        p.cantidad -= t["cantidad"]
        if p.cantidad < TOL:
            p.cantidad, p.costo = 0.0, 0.0
        est.efectivo += bruto - com - imp
    elif tipo == "dividendo":
        neto = t["monto"] * tc - imp
        p.dividendos += neto
        est.dividendos += neto
        est.efectivo += neto
    elif tipo == "split":
        p.cantidad *= t["cantidad"]  # el costo total no cambia; el costo promedio se ajusta solo


def calcular(transacciones: list[dict], precios_mxn: dict[str, float | None]) -> dict:
    est = Estado()
    for t in sorted(transacciones, key=lambda x: (x["fecha"], x.get("id") or 0)):
        aplicar(est, t)
    filas = []
    valor_pos, no_realizado, sin_precio = 0.0, 0.0, []
    for iid, p in est.posiciones.items():
        precio = precios_mxn.get(iid)
        valor = p.cantidad * precio if (precio is not None and p.cantidad > TOL) else None
        nr = (valor - p.costo) if valor is not None else None
        if p.cantidad > TOL:
            if valor is None:
                sin_precio.append(iid)
            else:
                valor_pos += valor
                no_realizado += nr
        filas.append({"instrumento_id": iid, "cantidad": round(p.cantidad, 8), "costo_total": round(p.costo, 2),
                      "costo_promedio": round(p.costo_promedio, 6), "precio_mxn": precio,
                      "valor_mxn": None if valor is None else round(valor, 2),
                      "no_realizado": None if nr is None else round(nr, 2),
                      "no_realizado_pct": None if (nr is None or p.costo <= 0) else round(nr / p.costo, 6),
                      "realizado": round(p.realizado, 2), "dividendos": round(p.dividendos, 2),
                      "comisiones": round(p.comisiones, 2)})
    realizado = sum(p.realizado for p in est.posiciones.values())
    total = est.efectivo + valor_pos
    for f in filas:
        f["peso"] = round(f["valor_mxn"] / total, 6) if (f["valor_mxn"] is not None and total > 0) else None
    return {
        "efectivo": round(est.efectivo, 2), "valor_posiciones": round(valor_pos, 2), "valor_total": round(total, 2),
        "aportaciones": round(est.aportaciones, 2), "retiros": round(est.retiros, 2),
        "aportacion_neta": round(est.aportaciones - est.retiros, 2),
        "realizado": round(realizado, 2), "no_realizado": round(no_realizado, 2),
        "dividendos": round(est.dividendos, 2), "comisiones": round(est.comisiones, 2),
        "impuestos": round(est.impuestos, 2),
        "resultado_total": round(total - (est.aportaciones - est.retiros), 2),
        "posiciones": sorted([f for f in filas if f["cantidad"] > TOL], key=lambda f: -(f["valor_mxn"] or 0)),
        "cerradas": [f for f in filas if f["cantidad"] <= TOL],
        "sin_precio": sin_precio, "completa": not sin_precio,
    }


def serie_historica(transacciones: list[dict], precios: pd.DataFrame) -> pd.DataFrame:
    """Valor diario de la cartera y rendimiento ponderado por tiempo (TWR) con flujos externos.
    `precios` son cierres NO ajustados en MXN (los dividendos ya entran como efectivo)."""
    if not transacciones or precios.empty:
        return pd.DataFrame()
    tx = sorted(transacciones, key=lambda x: (x["fecha"], x.get("id") or 0))
    inicio = pd.Timestamp(tx[0]["fecha"])
    fechas = precios.index[precios.index >= inicio]
    if len(fechas) == 0:
        return pd.DataFrame()
    p = precios.ffill(limit=5)
    est = Estado()
    i = 0
    filas = []
    for d in fechas:
        flujo = 0.0
        while i < len(tx) and pd.Timestamp(tx[i]["fecha"]) <= d:
            t = tx[i]
            if t["tipo"] in ("aportacion", "retiro"):
                flujo += (1 if t["tipo"] == "aportacion" else -1) * t["monto"] * float(t.get("tipo_cambio") or 1)
            aplicar(est, t)
            i += 1
        valor, completo = est.efectivo, True
        for iid, pos in est.posiciones.items():
            if pos.cantidad > TOL:
                px = p.at[d, iid] if iid in p.columns else np.nan
                if pd.isna(px):
                    completo = False
                else:
                    valor += pos.cantidad * px
        filas.append({"fecha": d, "valor": valor, "flujo": flujo, "completo": completo})
    df = pd.DataFrame(filas).set_index("fecha")
    prev = df["valor"].shift(1)
    r = (df["valor"] - df["flujo"]) / prev - 1
    r[(prev <= 0) | prev.isna() | ~df["completo"] | ~df["completo"].shift(1, fill_value=True)] = 0.0
    df["rend_diario"] = r
    df["twr_acumulado"] = (1 + r).cumprod() - 1
    return df


def xirr(flujos: list[tuple[pd.Timestamp, float]]) -> float | None:
    """Tasa interna de retorno anual (ponderada por dinero). Flujos: aportación negativa, valor final positivo."""
    if len(flujos) < 2 or all(v >= 0 for _, v in flujos) or all(v <= 0 for _, v in flujos):
        return None
    t0 = flujos[0][0]
    anios = np.array([(d - t0).days / 365.25 for d, _ in flujos])
    v = np.array([x for _, x in flujos])
    lo, hi = -0.99, 10.0
    f = lambda r: np.sum(v / (1 + r) ** anios)  # noqa: E731
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
