"""Reglas y calendario del Reto Actinver (config/reto.yaml)."""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

from . import vigencia
from .config import CONFIG_DIR

MX = ZoneInfo("America/Mexico_City")


@lru_cache(maxsize=1)
def _cargar(mtime: float) -> dict:
    with (CONFIG_DIR / "reto.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def config() -> dict:
    ruta = CONFIG_DIR / "reto.yaml"
    return _cargar(ruta.stat().st_mtime) if ruta.exists() else {"activo": False}


def activo() -> bool:
    return bool(config().get("activo"))


def _fecha(txt: str) -> datetime:
    return datetime.fromisoformat(txt).replace(tzinfo=MX)


def etapa(ahora: datetime | None = None) -> str:
    c = config()
    if not c.get("fechas"):
        return "sin_reto"
    f = c["fechas"]
    t = (ahora or datetime.now(MX)).astimezone(MX)
    if t < _fecha(f["practica_inicio"]):
        return "inscripcion"
    if t <= _fecha(f["practica_fin"]):
        return "practica"
    if t < _fecha(f["competencia_inicio"]):
        return "previa_competencia"
    if t <= _fecha(f["competencia_fin"]):
        return "competencia"
    return "concluido"


def etapa_de_fecha(fecha: str) -> str | None:
    """Etapa a la que pertenece una operación por su fecha: «practica», «competencia» o None (fuera del Reto).
    La práctica y la competencia son carteras separadas: la competencia reinicia el saldo (reglamento §5)."""
    f = config().get("fechas")
    if not f or not fecha:
        return None
    d = str(fecha)[:10]
    if f["practica_inicio"][:10] <= d <= f["practica_fin"][:10]:
        return "practica"
    if f["competencia_inicio"][:10] <= d <= f["competencia_fin"][:10]:
        return "competencia"
    return None


def etapa_operativa(ahora: datetime | None = None) -> str | None:
    """Cartera que se monitorea ahora: práctica durante la práctica, competencia desde su inicio; si no, ninguna."""
    e = etapa(ahora)
    return {"practica": "practica", "competencia": "competencia", "concluido": "competencia"}.get(e)


def inicio_etapa(etapa_: str) -> str | None:
    f = config().get("fechas") or {}
    return (f.get(f"{etapa_}_inicio") or "")[:10] or None


CLASES_ACCION = ("accion", "fibra", "reit")  # «acciones» para la regla de 5; los ETF no se cuentan (conservador)


def acciones_operadas(transacciones: list[dict], instrumentos: dict, etapa_: str = "competencia") -> dict:
    """Regla §6: «operaciones con por lo menos 5 acciones distintas». Cuenta compras CONFIRMADAS de la etapa."""
    minimo = int((config().get("reglas") or {}).get("min_emisoras") or 5)
    ids = sorted({t["instrumento_id"] for t in transacciones
                  if t.get("tipo") == "compra" and not t.get("anulada") and t.get("confirmada", 1)
                  and (t.get("etapa") or etapa_de_fecha(t.get("fecha"))) == etapa_
                  and (instrumentos.get(t["instrumento_id"]) or {}).get("clase") in CLASES_ACCION})
    return {"minimo": minimo, "operadas": ids, "n": len(ids), "cumple": len(ids) >= minimo, "faltan": max(minimo - len(ids), 0),
            "nota": "Se cuentan acciones, FIBRAs y REIT con compra confirmada en la etapa; los ETF no se cuentan "
                    "(las bases dicen «acciones»; confirme con el Comité si un ETF cuenta)."}


def costo_detalle(importe: float) -> dict:
    """Comisión 0.10 % sobre el importe + IVA 16 % sobre la comisión (reglamento §8). Estimación: el portal redondea."""
    c = config().get("costos") or {}
    tasa, iva = float(c.get("comision_pct") or 0), float(c.get("iva_sobre_comision") or 0)
    comision = abs(importe) * tasa
    return {"importe": round(abs(importe), 2), "comision": round(comision, 2), "iva": round(comision * iva, 2),
            "total": round(comision * (1 + iva), 2), "tasa_efectiva": tasa * (1 + iva)}


def verificar_compras(compras: list[dict], valor_portafolio: float, posiciones: dict[str, float]) -> list[dict]:
    """Regla §6/§7: «en ningún momento haber realizado compras en una sola acción por más del 50 %».
    Se revisan dos lecturas: (a) una compra individual > 50 % del valor del portafolio y (b) la posición resultante
    > 50 %. Ambas se advierten ANTES de presentar la propuesta; la interpretación oficial la define el Comité."""
    tope = float((config().get("reglas") or {}).get("max_peso_emisora") or 0.5)
    out = []
    if valor_portafolio <= 0:
        return out
    for c in compras:
        monto = float(c.get("monto") or 0)
        if monto <= 0:
            continue
        iid = c["id"]
        pct_compra = monto / valor_portafolio
        pct_pos = (posiciones.get(iid, 0.0) + monto) / valor_portafolio
        if pct_compra > tope + 1e-9:
            out.append({"id": iid, "nivel": "critica", "pct_compra": round(pct_compra, 4), "pct_posicion": round(pct_pos, 4),
                        "mensaje": f"La compra de {iid} ({pct_compra:.1%} del portafolio) excede el {tope:.0%} permitido."})
        elif pct_pos > tope + 1e-9:
            out.append({"id": iid, "nivel": "aviso", "pct_compra": round(pct_compra, 4), "pct_posicion": round(pct_pos, 4),
                        "mensaje": f"Tras comprar, {iid} pesaría {pct_pos:.1%} (> {tope:.0%}); revise la regla de concentración."})
    return out


def sesiones_restantes(ahora: datetime | None = None) -> int:
    """Sesiones de la BMV desde hoy (si aún no cierra) hasta el cierre de la competencia."""
    c = config()
    if not c.get("fechas"):
        return 0
    t = (ahora or datetime.now(MX)).astimezone(MX)
    fin = _fecha(c["fechas"]["competencia_fin"])
    if t >= fin:
        return 0
    cal = vigencia.calendario("XMEX")
    inicio = max(t, _fecha(c["fechas"]["competencia_inicio"])) if etapa(t) != "competencia" else t
    return len(cal.sessions_in_range(pd.Timestamp(inicio.date()), pd.Timestamp(fin.date())))


def horizonte_anios(ahora: datetime | None = None) -> float:
    """Horizonte hasta el final del Reto en años bursátiles (mínimo 5 sesiones para estimar)."""
    return max(sesiones_restantes(ahora), 5) / 252


def reglas_sin_confirmar() -> list[str]:
    c = config()
    out = [f"reglas.{k}" for k, v in (c.get("reglas") or {}).items() if v is None]
    out += [f"costos.{k}" for k, v in (c.get("costos") or {}).items() if v is None]
    return out


def costo_operacion() -> float | None:
    """Comisión + IVA del simulador por peso operado."""
    c = config().get("costos") or {}
    if c.get("comision_pct") is None:
        return None
    return float(c["comision_pct"]) * (1 + float(c.get("iva_sobre_comision") or 0))


def cumplimiento(pesos: dict[str, float]) -> list[dict]:
    """Verifica una asignación contra las reglas de rendimiento del Reto."""
    r = config().get("reglas") or {}
    w = {k: v for k, v in pesos.items() if v > 1e-6}
    out = []
    if r.get("min_emisoras") is not None:
        n = len(w)
        out.append({"regla": f"Al menos {r['min_emisoras']} emisoras", "cumple": bool(n >= r["min_emisoras"]),
                    "detalle": f"{n} emisoras"})
    if r.get("max_peso_emisora") is not None:
        mx = float(max(w.values(), default=0))
        out.append({"regla": f"Máximo {r['max_peso_emisora']:.0%} por emisora", "cumple": bool(mx <= r["max_peso_emisora"] + 1e-9),
                    "detalle": f"mayor peso {mx:.1%}"})
    prohibidos = set(r.get("instrumentos_prohibidos") or [])
    if prohibidos:
        hay = sorted(prohibidos & set(w))
        out.append({"regla": "Sin instrumentos prohibidos", "cumple": not hay, "detalle": ", ".join(hay) or "ninguno"})
    return out


def ganancia(valor_actual: float, capital_inicial: float, comisiones_pagadas: float) -> dict:
    """Ganancia absoluta y porcentual estimadas, con la comisión de salida estimada si se vendiera todo."""
    salida = costo_detalle(max(valor_actual, 0))
    bruta = valor_actual - capital_inicial
    return {"capital_inicial": capital_inicial, "valor_estimado": round(valor_actual, 2), "ganancia": round(bruta, 2),
            "ganancia_pct": (bruta / capital_inicial) if capital_inicial else None,
            "comisiones_pagadas": round(comisiones_pagadas, 2), "comision_salida_estimada": salida["total"],
            "ganancia_neta_si_liquidara": round(bruta - salida["total"], 2),
            "nota": "Estimación con precios de la terminal; la valuación oficial es la del portal (precio BMV continuo, "
                    "redondeos y comisiones aplicadas por el simulador). Registre el saldo del portal para compararlos."}


def resumen(ahora: datetime | None = None) -> dict:
    c = config()
    if not c.get("activo"):
        return {"activo": False}
    return {
        "activo": True, "nombre": c.get("nombre"), "fuente": c.get("fuente"), "consultado": c.get("consultado"),
        "capital": c.get("capital"), "fechas": c.get("fechas"), "etapa": etapa(ahora),
        "sesiones_restantes": sesiones_restantes(ahora), "horizonte_anios": round(horizonte_anios(ahora), 4),
        "costo_operacion": costo_operacion(), "reglas": c.get("reglas"), "horario_bmv": c.get("horario_bmv"),
        "evaluacion": c.get("evaluacion"), "tareas": c.get("tareas", []), "sin_confirmar": reglas_sin_confirmar(),
        "etapa_operativa": etapa_operativa(ahora), "zona_horaria": c.get("zona_horaria", "America/Mexico_City"),
        "prohibicion_automatizacion": c.get("prohibicion_automatizacion"),
    }
