"""Perfil EXPERIMENTAL del filtro de Option Flow descrito en un video de Skylit, aplicado a operaciones de opciones importadas por CSV o guardadas desde datos de mercado. Son criterios de un video, no reglas validadas ni una recomendación de comprar opciones.

Criterios por operación: prima ≥ USD 100 000; vencimiento ≤ ~183 días; volumen del contrato / interés abierto ≥ 10;
fuera del dinero; subyacente acción (no ETF ni índice); una sola pata; precio en el ask o encima del NBBO del instante.
Prima (USD), volumen del contrato (contratos) e interés abierto (contratos) se reportan por separado: son magnitudes
distintas. Si falta el dato que un criterio necesita (NBBO, condición, patas, OI, spot, clase…), ese criterio queda
«no_evaluable» y la operación no cuenta como filtrada por completo. Volumen/OI alto NO prueba apertura de posiciones: el
OI se publica con desfase (normalmente al cierre previo) y una operación puede cerrar, cubrir o ser parte de una
estructura no identificada.
"""
from __future__ import annotations

import csv
import io
import math
from datetime import date, datetime

COLUMNAS = ["instante", "contrato", "subyacente", "clase_subyacente", "tipo", "strike", "vencimiento", "precio", "tamano",
            "multiplicador", "moneda", "bid", "ask", "condicion", "patas", "volumen_contrato_dia", "interes_abierto",
            "fecha_oi", "spot"]
OBLIGATORIAS = ("instante", "contrato", "subyacente", "tipo", "strike", "vencimiento", "precio", "tamano")
PERFIL = {"prima_min_usd": 100_000, "dte_max": 183, "vol_oi_min": 10}
MAX_FILAS, MAX_BYTES = 20_000, 2_000_000
AVISOS = [
    "Perfil experimental basado en los criterios mostrados en un video; no es una regla validada ni recomendación de comprar opciones.",
    "Volumen/OI ≥ 10 no prueba que se abrieron posiciones: el OI tiene desfase y la operación puede cerrar, cubrir o ser parte de una estructura.",
    "«En el ask o encima» exige el NBBO del mismo instante; una cadena o un bid/ask de otra hora no sirven.",
    "Una operación solo cuenta como filtrada por completo si los 7 criterios son evaluables.",
]


def plantilla() -> str:
    return ",".join(COLUMNAS) + "\n"


def _num(v):
    if v in (None, ""):
        return None
    x = float(v)
    if not math.isfinite(x) or x < 0:
        raise ValueError
    return x


def _c(estado: str, motivo: str = "") -> dict:
    return {"estado": estado, "motivo": motivo}


def evaluar_fila(f: dict) -> dict:
    tipo = f["tipo"].strip().lower()
    if tipo not in ("call", "put"):
        raise ValueError("tipo debe ser call o put")
    strike, precio, tam = _num(f["strike"]), _num(f["precio"]), _num(f["tamano"])
    mult, bid, ask, spot = _num(f.get("multiplicador")), _num(f.get("bid")), _num(f.get("ask")), _num(f.get("spot"))
    vol, oi = _num(f.get("volumen_contrato_dia")), _num(f.get("interes_abierto"))
    patas = _num(f.get("patas"))
    t = datetime.fromisoformat(f["instante"].strip().replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("instante sin zona horaria")
    dte = (date.fromisoformat(f["vencimiento"].strip()) - t.date()).days
    if dte < 0:
        raise ValueError("vencimiento anterior a la operación")
    moneda = (f.get("moneda") or "").strip().upper()
    prima = precio * tam * mult if mult else None
    cr = {}
    if prima is None:
        cr["prima"] = _c("no_evaluable", "falta multiplicador")
    elif moneda != "USD":
        cr["prima"] = _c("no_evaluable", "moneda distinta de USD o vacía")
    else:
        cr["prima"] = _c("cumple" if prima >= PERFIL["prima_min_usd"] else "no_cumple")
    cr["vencimiento"] = _c("cumple" if dte <= PERFIL["dte_max"] else "no_cumple")
    if vol is None or oi is None:
        cr["volumen_oi"] = _c("no_evaluable", "falta volumen del contrato o interés abierto")
    elif oi == 0:
        cr["volumen_oi"] = _c("no_evaluable", "interés abierto 0: cociente indefinido")
    else:
        cr["volumen_oi"] = _c("cumple" if vol / oi >= PERFIL["vol_oi_min"] else "no_cumple")
    if spot is None:
        cr["fuera_del_dinero"] = _c("no_evaluable", "falta spot del instante")
    else:
        cr["fuera_del_dinero"] = _c("cumple" if (strike > spot if tipo == "call" else strike < spot) else "no_cumple")
    clase = (f.get("clase_subyacente") or "").strip().lower()
    cr["accion"] = _c("no_evaluable", "falta clase del subyacente") if not clase else _c("cumple" if clase == "accion" else "no_cumple")
    if patas is None or not (f.get("condicion") or "").strip():
        cr["una_pata"] = _c("no_evaluable", "falta condición de la operación o número de patas")
    else:
        cr["una_pata"] = _c("cumple" if patas == 1 else "no_cumple")
    if bid is None or ask is None or bid > ask:
        cr["en_ask"] = _c("no_evaluable", "falta NBBO del instante o bid > ask")
    else:
        cr["en_ask"] = _c("cumple" if precio >= ask - 1e-9 else "no_cumple")
    estados = [c["estado"] for c in cr.values()]
    resultado = "no_pasa" if "no_cumple" in estados else ("pasa" if all(e == "cumple" for e in estados) else "no_evaluable")
    return {"instante": t.isoformat(), "contrato": f["contrato"].strip(), "subyacente": f["subyacente"].strip().upper(),
            "tipo": tipo, "strike": strike, "dte": dte, "prima_usd": prima, "volumen_contrato_dia": vol,
            "interes_abierto": oi, "fecha_oi": (f.get("fecha_oi") or "").strip() or None,
            "volumen_oi": (vol / oi) if vol is not None and oi else None, "criterios": cr, "resultado": resultado}


def evaluar_csv(texto: str) -> dict:
    if len(texto.encode()) > MAX_BYTES:
        raise ValueError("CSV demasiado grande (máx. 2 MB)")
    lector = csv.DictReader(io.StringIO(texto.lstrip(chr(0xFEFF)).strip()))
    enc = [c.strip() for c in (lector.fieldnames or [])]
    faltan = [c for c in OBLIGATORIAS if c not in enc]
    if faltan:
        raise ValueError("faltan columnas obligatorias: " + ", ".join(faltan) + " (use la plantilla)")
    filas, errores = [], []
    for i, f in enumerate(lector, start=2):
        if i - 1 > MAX_FILAS:
            raise ValueError(f"máximo {MAX_FILAS} operaciones")
        f = {k.strip(): (v or "") for k, v in f.items() if k}
        if any(not f.get(c, "").strip() for c in OBLIGATORIAS):
            errores.append({"fila": i, "error": "faltan campos obligatorios"})
            continue
        try:
            filas.append(evaluar_fila(f))
        except (ValueError, TypeError):
            errores.append({"fila": i, "error": "valor inválido (números ≥ 0, fechas ISO con zona, tipo call/put)"})
    if not filas:
        raise ValueError("ninguna operación válida" + (f": {errores[0]['error']} (fila {errores[0]['fila']})" if errores else ""))
    return {**resumir(filas, errores), "calidad": "importado",
            "nota": "Datos del CSV del usuario; la terminal no los guarda ni los verifica contra un proveedor."}


def resumir(filas: list[dict], errores: list[dict] | None = None) -> dict:
    errores = errores or []
    conteo = {r: sum(1 for x in filas if x["resultado"] == r) for r in ("pasa", "no_pasa", "no_evaluable")}
    faltantes: dict[str, int] = {}
    for x in filas:
        for k, c in x["criterios"].items():
            if c["estado"] == "no_evaluable":
                faltantes[k] = faltantes.get(k, 0) + 1
    return {"perfil": PERFIL, "operaciones": len(filas), "conteo": conteo, "no_evaluables_por_criterio": faltantes,
            "filtro_completo_aplicado": bool(filas) and conteo["no_evaluable"] == 0 and not faltantes,
            "filas": filas[:500], "errores": errores[:50], "avisos": AVISOS}
