"""Indicadores descriptivos sobre datos reales almacenados. Ninguno es una señal de compra o venta.

Cada función devuelve `None` (o una lista vacía) cuando los datos no alcanzan: nunca rellena con supuestos.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date


def sma(valores: list[float], n: int = 20) -> list[float | None]:
    out, suma = [], 0.0
    for i, v in enumerate(valores):
        suma += v
        if i >= n:
            suma -= valores[i - n]
        out.append(suma / n if i >= n - 1 else None)
    return out


def rsi_wilder(valores: list[float], n: int = 14) -> list[float | None]:
    """RSI de Wilder (media móvil suavizada), el mismo método que usa TradingView."""
    out: list[float | None] = [None] * len(valores)
    if len(valores) <= n:
        return out
    cambios = [valores[i] - valores[i - 1] for i in range(1, len(valores))]
    sub = sum(max(c, 0) for c in cambios[:n]) / n
    baj = sum(max(-c, 0) for c in cambios[:n]) / n

    def valor(s, b):
        return 100.0 if b == 0 and s > 0 else 50.0 if b == 0 else 100 - 100 / (1 + s / b)
    out[n] = valor(sub, baj)
    for i in range(n + 1, len(valores)):
        c = cambios[i - 1]
        sub = (sub * (n - 1) + max(c, 0)) / n
        baj = (baj * (n - 1) + max(-c, 0)) / n
        out[i] = valor(sub, baj)
    return out


def bollinger(valores: list[float], n: int = 20, k: float = 2.0) -> list[tuple[float, float] | None]:
    out = []
    for i in range(len(valores)):
        if i < n - 1:
            out.append(None)
            continue
        v = valores[i - n + 1:i + 1]
        m = sum(v) / n
        de = math.sqrt(sum((x - m) ** 2 for x in v) / n)  # desviación poblacional, como la definición original
        out.append((m - k * de, m + k * de))
    return out


def vwap_anclado(barras: list[dict]) -> list[float | None]:
    """VWAP anclado a la primera barra del rango, con precio típico (H+L+C)/3. Sin volumen no hay VWAP."""
    out, pv, vol = [], 0.0, 0.0
    for b in barras:
        v = b.get("volumen")
        if v is None or v < 0:
            out.append(None)
            continue
        pv += (b["maximo"] + b["minimo"] + b["cierre"]) / 3 * v
        vol += v
        out.append(pv / vol if vol > 0 else None)
    return out


def resumen_libro(libro: dict | None, niveles: int = 10) -> dict | None:
    """Mejor bid/ask, diferencial, profundidad acumulada y desequilibrio de los primeros `niveles`."""
    if not libro:
        return None
    bids = sorted([n for n in libro["niveles"] if n["lado"] == "bid"], key=lambda n: -n["precio"])[:niveles]
    asks = sorted([n for n in libro["niveles"] if n["lado"] == "ask"], key=lambda n: n["precio"])[:niveles]
    if not bids or not asks:
        return {"bids": bids, "asks": asks, "mejor_bid": bids[0]["precio"] if bids else None,
                "mejor_ask": asks[0]["precio"] if asks else None, "desequilibrio": None, "diferencial": None,
                "profundidad": []}
    vb, va = sum(n["tamano"] for n in bids), sum(n["tamano"] for n in asks)
    prof, acum = [], 0.0
    for n in bids:
        acum += n["tamano"]
        prof.append({"lado": "bid", "precio": n["precio"], "acumulado": acum})
    acum = 0.0
    for n in asks:
        acum += n["tamano"]
        prof.append({"lado": "ask", "precio": n["precio"], "acumulado": acum})
    medio = (bids[0]["precio"] + asks[0]["precio"]) / 2
    return {"bids": bids, "asks": asks, "mejor_bid": bids[0]["precio"], "mejor_ask": asks[0]["precio"],
            "medio": medio, "diferencial": asks[0]["precio"] - bids[0]["precio"],
            "diferencial_pb": (asks[0]["precio"] - bids[0]["precio"]) / medio * 1e4,
            "desequilibrio": (vb - va) / (vb + va) if vb + va > 0 else None, "volumen_bid": vb, "volumen_ask": va,
            "profundidad": prof, "niveles_usados": niveles}


def resumen_operaciones(ops: list[dict], cubetas: int = 24) -> dict:
    """Volumen acumulado, delta (solo con lado informado por el proveedor) y perfil de volumen por precio."""
    if not ops:
        return {"n": 0, "volumen": 0.0, "delta": None, "delta_acumulado": [], "perfil": [], "con_lado": 0}
    con_lado = [o for o in ops if o.get("lado") in ("compra", "venta")]
    delta_acum, d = [], 0.0
    if len(con_lado) == len(ops):
        for o in ops:
            d += o["tamano"] if o["lado"] == "compra" else -o["tamano"]
            delta_acum.append({"instante": o["instante"], "delta": d})
    precios = [o["precio"] for o in ops]
    lo, hi = min(precios), max(precios)
    ancho = (hi - lo) / cubetas if hi > lo else 1.0
    perfil = defaultdict(lambda: {"volumen": 0.0, "compra": 0.0, "venta": 0.0})
    for o in ops:
        k = min(int((o["precio"] - lo) / ancho), cubetas - 1) if hi > lo else 0
        perfil[k]["volumen"] += o["tamano"]
        if o.get("lado") in ("compra", "venta"):
            perfil[k][o["lado"]] += o["tamano"]
    return {"n": len(ops), "volumen": sum(o["tamano"] for o in ops), "con_lado": len(con_lado),
            "delta": d if delta_acum else None, "delta_acumulado": delta_acum,
            "perfil": [{"desde": lo + k * ancho, "hasta": lo + (k + 1) * ancho, **v} for k, v in sorted(perfil.items())]}


def volumen_inusual(contratos: list[dict], ratio_oi: float = 1.0, percentil: float = 0.95, minimo: float = 100) -> list[dict]:
    """Regla DESCRIPTIVA y configurable: marca contratos con volumen ≥ `minimo` y, si hay interés abierto,
    volumen/interés abierto ≥ `ratio_oi`; si no lo hay, volumen ≥ percentil `percentil` de la cadena."""
    vols = sorted(c["volumen"] for c in contratos if c.get("volumen"))
    if not vols:
        return []
    corte = vols[min(int(len(vols) * percentil), len(vols) - 1)]
    out = []
    for c in contratos:
        v = c.get("volumen") or 0
        if v < minimo:
            continue
        oi = c.get("interes_abierto")
        if oi:
            if v / oi >= ratio_oi:
                out.append({**c, "motivo": f"volumen/interés abierto = {v / oi:.2f} ≥ {ratio_oi}"})
        elif v >= corte:
            out.append({**c, "motivo": f"volumen {v:,.0f} ≥ percentil {percentil:.0%} de la cadena ({corte:,.0f}); sin interés abierto"})
    return out


def superficie_iv(contratos: list[dict]) -> dict:
    """Curvas de IV por vencimiento (strike → IV) y la superficie como lista de puntos. Solo IV presente."""
    curvas = defaultdict(list)
    for c in contratos:
        if c.get("iv") and c["iv"] > 0:
            curvas[c["vencimiento"]].append({"strike": c["strike"], "iv": c["iv"], "tipo": c["tipo"],
                                             "origen": c.get("origen_iv")})
    return {"curvas": {k: sorted(v, key=lambda p: p["strike"]) for k, v in sorted(curvas.items())},
            "vencimientos": len(curvas), "puntos": sum(len(v) for v in curvas.values()),
            "superficie": len(curvas) >= 2 and all(len(v) >= 3 for v in curvas.values())}


def dias_al_vencimiento(vencimiento: str, hoy: date) -> int:
    return (date.fromisoformat(vencimiento) - hoy).days
