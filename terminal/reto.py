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
    }
