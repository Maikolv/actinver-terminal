"""Costos y presentación de propuestas sin cargar dependencias de optimización."""
from __future__ import annotations

from . import reto
from .config import Ajustes

# Horizonte de proyección: unidad -> sesiones bursátiles (252 al año, 21 al mes, 5 a la semana).
UNIDADES_HORIZONTE = {"dias": 1, "semanas": 5, "meses": 21, "anios": 252}


def horizonte_sesiones(valor: float, unidad: str) -> int:
    if unidad not in UNIDADES_HORIZONTE:
        raise ValueError("unidad del horizonte: dias, semanas, meses o anios")
    return max(1, round(float(valor) * UNIDADES_HORIZONTE[unidad]))


def _clase_costo(ins: dict) -> str:
    if ins["clase"].startswith("fondo"):
        return "fondo"
    if ins["clase"] in ("accion", "reit"):
        return "accion_sic" if ins["mercado_operable"] == "BMV-SIC" else "accion_bmv"
    return ins["clase"] if ins["clase"] in ("etf", "fibra") else "accion_bmv"


def costo_unitario(ins: dict, ajustes: Ajustes) -> float:
    """Costo de operar un peso: comisión con IVA + spread estimado. Con el Reto activo, la comisión es la del
    simulador (0.10 % + IVA sobre toda orden, reglamento §8)."""
    c = ajustes["costos"]
    spread = c["spread_pct"].get(_clase_costo(ins), 0.003)
    if reto.activo() and reto.costo_operacion() is not None:
        return reto.costo_operacion() + spread
    if ins["clase"].startswith("fondo"):
        return 0.0  # compra/venta de fondos sin comisión explícita; el costo va implícito en el NAV
    return c["comision_pct"] * (1 + c["iva"]) + spread


def clasificar(propuestas: list[dict], cartera_actual: dict) -> list[dict]:
    """Ordena las alternativas por puntuación total. Se presenta como resultado de criterios, no como certeza."""
    filas = []
    for p in propuestas:
        clave = p.get("clave", p["tipo"])
        if p.get("estado") in ("calculada", "demostracion"):
            filas.append({"alternativa": p["nombre"], "tipo": p["tipo"], "clave": clave, "puntuacion": p["puntuacion"]["total"],
                          "estado": p["estado"]})
        else:
            filas.append({"alternativa": p["nombre"], "tipo": p["tipo"], "clave": clave, "puntuacion": None,
                          "estado": p.get("estado"), "motivo": "; ".join(p.get("motivos", []))})
    filas.sort(key=lambda f: -(f["puntuacion"] if f["puntuacion"] is not None else -1))
    for i, f in enumerate(filas, 1):
        f["posicion"] = i if f["puntuacion"] is not None else None
    return filas
