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


def ema(valores: list[float], n: int = 20) -> list[float | None]:
    """EMA con semilla SMA de las primeras `n` observaciones (convención de TradingView); nula antes de tener `n` datos."""
    out: list[float | None] = [None] * len(valores)
    if n < 1 or len(valores) < n:
        return out
    a = 2 / (n + 1)
    out[n - 1] = prev = sum(valores[:n]) / n
    for i in range(n, len(valores)):
        out[i] = prev = valores[i] * a + prev * (1 - a)
    return out


def macd(valores: list[float], rapida: int = 12, lenta: int = 26, senal: int = 9) -> dict[str, list[float | None]]:
    """MACD = EMA rápida − EMA lenta; señal = EMA de la línea MACD (semilla SMA); histograma = MACD − señal.
    La línea MACD empieza en la barra `lenta` − 1 y la señal `senal` − 1 barras después: sin relleno antes."""
    er, el = ema(valores, rapida), ema(valores, lenta)
    linea = [None if a is None or b is None else a - b for a, b in zip(er, el)]
    ini = next((i for i, v in enumerate(linea) if v is not None), len(linea))
    sen = [None] * ini + ema(linea[ini:], senal)
    hist = [None if m is None or g is None else m - g for m, g in zip(linea, sen)]
    return {"macd": linea, "senal": sen, "hist": hist}


def estocastico(maximos: list[float], minimos: list[float], cierres: list[float], n: int = 14, suave: int = 3,
                d: int = 3) -> dict[str, list[float | None]]:
    """Estocástico lento: %K bruto sobre `n` barras, %K = SMA(`suave`) del bruto, %D = SMA(`d`) de %K.
    Con rango máximo = mínimo el %K bruto no está definido (división entre cero): queda nulo, no 0 ni 50."""
    t = len(cierres)
    bruto: list[float | None] = [None] * t
    for i in range(n - 1, t):
        hh, ll = max(maximos[i - n + 1:i + 1]), min(minimos[i - n + 1:i + 1])
        bruto[i] = (cierres[i] - ll) / (hh - ll) * 100 if hh > ll else None

    def sma_nula(x, k):
        return [None if i < k - 1 or any(v is None for v in x[i - k + 1:i + 1]) else sum(x[i - k + 1:i + 1]) / k
                for i in range(len(x))]
    k_ = sma_nula(bruto, suave)
    return {"k": k_, "d": sma_nula(k_, d)}


def sar_parabolico(maximos: list[float], minimos: list[float], cierres: list[float], paso: float = 0.02,
                   maximo_af: float = 0.2) -> dict[str, list]:
    """SAR parabólico de Wilder. Tendencia inicial según el cierre de la barra 1 frente al de la 0; el SAR de la barra 0
    no existe (nulo). El SAR nunca entra en el rango de las dos barras previas; al cruzarlo se invierte hacia el EP previo."""
    t = len(cierres)
    sar: list[float | None] = [None] * t
    alza: list[bool | None] = [None] * t
    if t < 2:
        return {"sar": sar, "alcista": alza}
    sube = cierres[1] >= cierres[0]
    s, ep, af = (minimos[0], maximos[0], paso) if sube else (maximos[0], minimos[0], paso)
    for i in range(1, t):
        s = s + af * (ep - s)
        if sube:
            s = min(s, minimos[i - 1], minimos[i - 2] if i >= 2 else minimos[i - 1])
            if minimos[i] < s:
                sube, s, ep, af = False, ep, minimos[i], paso
            elif maximos[i] > ep:
                ep, af = maximos[i], min(af + paso, maximo_af)
        else:
            s = max(s, maximos[i - 1], maximos[i - 2] if i >= 2 else maximos[i - 1])
            if maximos[i] > s:
                sube, s, ep, af = True, ep, maximos[i], paso
            elif minimos[i] < ep:
                ep, af = minimos[i], min(af + paso, maximo_af)
        sar[i], alza[i] = s, sube
    return {"sar": sar, "alcista": alza}


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
