"""Exposición gamma (GEX) por strike y vencimiento, con gamma y spot de la misma referencia y metadatos fechados del contrato.

Cada contrato necesita gamma y spot compatibles (más la moneda), interés abierto y multiplicador propios.
El OI y multiplicador pueden proceder de contratos Paper conocidos antes del snapshot, con fecha previa explícita. Nada se supone: ni el
multiplicador 100 (los contratos ajustados por eventos corporativos pueden tener otro), ni un spot tomado de otra
tabla, hora o moneda. Si faltan, el resultado dice exactamente qué falta y qué importación o proveedor lo resolvería.

USD por movimiento de 1 % del subyacente = gamma × OI × multiplicador × S² × 0.01 (en la moneda del spot).
Dos lecturas separadas:
  * absoluta: calls + puts, siempre ≥ 0. Dice cuánta gamma hay abierta, no hacia dónde.
  * firmada (CONVENCIÓN): calls +, puts −. Supone que el mercado vendió calls y compró puts; la posición real de los
    intermediarios NO se conoce con interés abierto. No es una posición observada ni una señal.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

PORCENTAJE = 0.01
REQUISITO = ("Importe un CSV autorizado con gamma, spot y moneda compatibles, interés abierto y multiplicador; "
             "o habilite contratos Paper para OI fechado del cierre previo y size. Los metadatos solo se unen si "
             "ya eran conocidos al instante de la cadena. El feed indicativo (no equivale a OPRA) no aporta OI ni multiplicador y "
             "contratos Paper no aporta spot ni gamma; ningún campo ausente se inventa.")
CONVENCION = ("Firmada = calls positivos y puts negativos: es una CONVENCIÓN de signo, no la posición conocida de los "
              "intermediarios (dealers). Con interés abierto no se sabe quién compró o vendió; la lectura firmada puede "
              "ser errónea y no es una señal operativa.")
FORMULA = "Exposición en la moneda del spot por movimiento de 1 % = gamma × interés abierto × multiplicador × S² × 0.01 (S = spot de la misma referencia)"


def _num(v, minimo_estricto: bool = False) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x) or x < 0 or (minimo_estricto and x == 0):
        return None
    return x


def _clasificar(c: dict) -> tuple[str | None, tuple | None]:
    """(motivo de descarte, None) o (None, (gex, referencia))."""
    gamma, oi = _num(c.get("gamma")), _num(c.get("interes_abierto"))
    mult, spot = _num(c.get("multiplicador"), True), _num(c.get("spot"), True)
    if gamma is None:
        return "sin gamma válida", None
    if oi is None:
        return "sin interés abierto", None
    if mult is None:
        return "sin multiplicador", None
    if spot is None:
        return "sin spot de la misma referencia", None
    if not c.get("moneda"):
        return "sin moneda del spot/contrato", None
    g = gamma * oi * mult * spot * spot * PORCENTAJE
    if not math.isfinite(g):
        return "valor no finito", None
    return None, (g, (c["instante"], spot, c["moneda"]))


def calcular(cadena: list[dict]) -> dict:
    total = len(cadena)
    metadatos = [c for c in cadena if c.get("procedencia_contratos")]
    fechas = sorted({c["fecha_oi"] for c in metadatos if c.get("fecha_oi") and
                     "interes_abierto" in c["procedencia_contratos"].get("campos", ["interes_abierto"])})
    base = {"total": total, "formula": FORMULA, "convencion": CONVENCION, "requisito": REQUISITO,
            "fechas_oi": fechas, "oi_desactualizado": any(c.get("oi_desactualizado") for c in metadatos),
            "procedencia_contratos": [c["procedencia_contratos"] for c in metadatos],
            "aviso_oi": ("OI de cierre previo, no intradía. Fechas: " + ", ".join(fechas) +
                         "; desactualizado = antigüedad superior a 4 días calendario." if fechas else None)}
    if not total:
        return {**base, "disponible": False, "contratos_usados": 0, "descartados": {},
                "motivo": "No hay cadena de opciones guardada para este subyacente.", "celdas": []}
    descartes: Counter = Counter()
    validos = []
    for c in cadena:
        motivo, r = _clasificar(c)
        if motivo:
            descartes[motivo] += 1
        else:
            validos.append((c, *r))
    if not validos:
        detalle = "; ".join(f"{n} {m}" for m, n in descartes.most_common())
        return {**base, "disponible": False, "contratos_usados": 0, "descartados": dict(descartes), "celdas": [],
                "motivo": f"GEX no calculable: ningún contrato de {total} tiene todos los datos ({detalle}). "}
    # Una sola referencia (instante, spot, moneda): se usa la más reciente; el resto se descarta y se cuenta.
    grupos: dict[tuple, list] = defaultdict(list)
    for v in validos:
        grupos[v[2]].append(v)
    ref = max(grupos, key=lambda k: (k[0], len(grupos[k])))
    usados = grupos[ref]
    otros = len(validos) - len(usados)
    if otros:
        descartes["otra referencia de instante/spot/moneda"] += otros
    celdas: dict[tuple, dict] = {}
    for c, g, _ in usados:
        k = (c["vencimiento"], c["strike"])
        z = celdas.setdefault(k, {"vencimiento": c["vencimiento"], "strike": c["strike"], "calls": 0.0, "puts": 0.0, "n": 0})
        z["calls" if c["tipo"] == "call" else "puts"] += g
        z["n"] += 1
    filas = []
    for z in sorted(celdas.values(), key=lambda z: (z["vencimiento"], z["strike"])):
        filas.append({**z, "absoluta": z["calls"] + z["puts"], "firmada": z["calls"] - z["puts"]})
    calls, puts = sum(z["calls"] for z in filas), sum(z["puts"] for z in filas)
    return {**base, "disponible": True, "contratos_usados": len(usados), "descartados": dict(descartes), "celdas": filas,
            "cobertura": len(usados) / total, "instante": ref[0], "spot": ref[1], "moneda": ref[2],
            "vencimientos": sorted({z["vencimiento"] for z in filas}), "strikes": sorted({z["strike"] for z in filas}),
            "totales": {"absoluta": calls + puts, "calls": calls, "puts": puts, "firmada": calls - puts},
            "motivo": None,
            "aviso": (None if len(usados) == total else
                      f"Cobertura parcial: {len(usados)} de {total} contratos; los demás se excluyen ({', '.join(f'{n} {m}' for m, n in descartes.most_common())}). "
                      "Los totales subestiman la exposición.")}
