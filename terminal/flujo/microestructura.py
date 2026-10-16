"""Footprint e historial de liquidez de registros observados. Sin interpolación ni órdenes."""
from collections import defaultdict
from datetime import UTC, datetime


def footprint(operaciones: list[dict], segundos: int = 300) -> dict:
    if segundos not in (60, 300, 900, 3600):
        raise ValueError("intervalo de footprint inválido")
    grupos = defaultdict(list)
    for op in operaciones:
        t = datetime.fromisoformat(op["instante"])
        if t.tzinfo is None:
            raise ValueError("footprint exige instantes con zona horaria")
        bloque = int(t.timestamp()) // segundos * segundos
        # Nunca sumar feeds o mercados diferentes como si fueran una sola cinta.
        grupos[(op.get("fuente", ""), op.get("feed", ""), op.get("mercado", ""), bloque)].append(op)
    barras, celdas = [], []
    elegidos = sorted(grupos, key=lambda k: (k[3], k[:3]))[-60:]
    for fuente, feed, mercado, t in elegidos:
        ops = grupos[(fuente, feed, mercado, t)]
        inicio = datetime.fromtimestamp(t, UTC).isoformat()
        meta = {"inicio": inicio, "fuente": fuente, "feed": feed, "mercado": mercado}
        niveles = defaultdict(list)
        for op in ops:
            niveles[op["precio"]].append(op)
        volumen = sum(o["tamano"] for o in ops)
        conocidos = all(o.get("lado") in ("compra", "venta") for o in ops)
        delta = sum(o["tamano"] * (1 if o["lado"] == "compra" else -1) for o in ops) if conocidos else None
        barras.append({**meta, "volumen": volumen, "operaciones": len(ops), "delta": delta,
                       "delta_pct": delta / volumen * 100 if delta is not None and volumen else None})
        for precio, nivel in sorted(niveles.items(), reverse=True):
            completo = all(o.get("lado") in ("compra", "venta") for o in nivel)
            compra = sum(o["tamano"] for o in nivel if o.get("lado") == "compra")
            venta = sum(o["tamano"] for o in nivel if o.get("lado") == "venta")
            celdas.append({**meta, "precio": precio, "volumen": sum(o["tamano"] for o in nivel),
                           "bid": venta if completo else None, "ask": compra if completo else None,
                           "delta": compra - venta if completo else None})
    return {"segundos": segundos, "barras": barras, "celdas": celdas[-1200:],
            "celdas_totales": len(celdas), "barras_totales": len(grupos),
            "parcial": len(grupos) > 60 or len(celdas) > 1200 or len(operaciones) >= 5000,
            "nota": "Sólo operaciones guardadas; hasta 60 intervalos y 1200 niveles visibles. Sin redondear precios "
                    "ni inventar tick. Bid/ask son volumen ejecutado por agresor, no profundidad. Si falta lado, "
                    "delta y bid/ask quedan nulos. Feeds separados. No es una cinta completa del mercado."}


def liquidez(libros: list[dict]) -> dict:
    if not libros:
        return {"instantes": [], "precios": [], "celdas": [], "parcial": False,
                "nota": "No hay snapshots guardados. Hace falta profundidad Level 2 histórica o capturas autorizadas."}
    ultimo = max(libros, key=lambda l: (l["instante"], l.get("id", 0)))
    referencia = tuple(ultimo.get(k, "") for k in ("fuente", "feed", "mercado"))
    compatibles = [l for l in libros if tuple(l.get(k, "") for k in ("fuente", "feed", "mercado")) == referencia]
    compatibles.sort(key=lambda l: (l["instante"], l.get("id", 0)))
    compatibles = compatibles[-60:]
    cantidades = defaultdict(float)
    celdas = []
    for l in compatibles:
        for n in l["niveles"]:
            cantidades[n["precio"]] += n["tamano"]
            celdas.append({"instante": l["instante"], "precio": n["precio"], "lado": n["lado"], "tamano": n["tamano"]})
    precios = sorted(cantidades, key=lambda p: (-cantidades[p], p))[:80]
    seleccion = set(precios)
    return {"instantes": sorted({l["instante"] for l in compatibles}), "precios": sorted(precios, reverse=True),
            "celdas": [c for c in celdas if c["precio"] in seleccion],
            "fuente": referencia[0], "feed": referencia[1], "mercado": referencia[2],
            "parcial": len(precios) < len(cantidades) or len(compatibles) < len(libros),
            "nota": "Liquidez pasiva visible en snapshots; hasta 60 capturas y 80 precios con mayor tamaño acumulado. "
                    "Mismo feed/mercado de la captura más reciente. Sin interpolar huecos. Una celda ausente no prueba "
                    "cero liquidez y una disminución no permite distinguir ejecución de cancelación. No es GEX."}
