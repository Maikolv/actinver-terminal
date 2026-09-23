"""División cronológica con embargo y purga (nunca se barajan filas).

Para un horizonte H (sesiones) y fechas negociadas ordenadas d_0 … d_{n-1}:

  n_ent = floor(n · p_ent), n_val = floor(n · p_val)
  embargo e = max(H, embargo_min)
  entrenamiento = [d_0, d_{n_ent})
  validación    = [d_{n_ent + e}, d_{n_ent + n_val})
  prueba        = [d_{n_ent + n_val + e}, d_{n-1}]

Purga: un ejemplo de un periodo se elimina si su ventana de etiqueta [t, t+H] termina en o después del primer día
del periodo siguiente (fecha_fin_etiqueta >= inicio_siguiente). Con e >= H casi nunca ocurre; la purga cubre los
días festivos distintos entre calendarios (BMV y NYSE), en los que t+H del instrumento cae más lejos.

Las e fechas de embargo son las únicas que no se usan para evaluar; su número se informa. L (ventana retrospectiva
máxima) no exige embargo adicional porque las ventanas de variables solo miran hacia atrás y el entrenamiento siempre
precede a la evaluación: que una variable de validación use precios del entrenamiento es información pasada legítima.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Cortes:
    H: int
    embargo: int
    fechas: list[str]
    entrenamiento: tuple[int, int]
    validacion: tuple[int, int]
    prueba: tuple[int, int]

    def rango(self, nombre: str) -> tuple[str, str] | None:
        a, b = getattr(self, nombre)
        return (self.fechas[a], self.fechas[b - 1]) if b > a else None

    def a_dict(self) -> dict:
        return {"H": self.H, "embargo_sesiones": self.embargo, "n_fechas": len(self.fechas),
                "entrenamiento": self.rango("entrenamiento"), "validacion": self.rango("validacion"),
                "prueba": self.rango("prueba"), "fechas_embargadas": 2 * self.embargo}


def dividir(fechas: list[str], H: int, proporciones=(0.70, 0.15, 0.15), embargo_min: int = 0) -> Cortes:
    fechas = sorted(set(fechas))
    n = len(fechas)
    e = max(int(H), int(embargo_min))
    n_ent, n_val = int(n * proporciones[0]), int(n * proporciones[1])
    if n_val <= e or n - (n_ent + n_val) <= e:
        raise ValueError(f"Datos insuficientes: {n} fechas no alcanzan para validación y prueba con embargo {e}")
    return Cortes(H, e, fechas, (0, n_ent), (n_ent + e, n_ent + n_val), (n_ent + n_val + e, n))


def mascara(panel: pd.DataFrame, cortes: Cortes, nombre: str) -> pd.Series:
    """Filas del periodo, purgadas contra el inicio del periodo siguiente."""
    a, b = getattr(cortes, nombre)
    desde, hasta = cortes.fechas[a], cortes.fechas[b - 1]
    m = (panel["fecha"] >= desde) & (panel["fecha"] <= hasta)
    siguiente = {"entrenamiento": cortes.validacion[0], "validacion": cortes.prueba[0]}.get(nombre)
    if siguiente is not None and siguiente < len(cortes.fechas):
        m &= panel["fecha_fin_etiqueta"].notna() & (panel["fecha_fin_etiqueta"] < cortes.fechas[siguiente])
    return m


def purgadas(panel: pd.DataFrame, cortes: Cortes, nombre: str) -> int:
    a, b = getattr(cortes, nombre)
    en = (panel["fecha"] >= cortes.fechas[a]) & (panel["fecha"] <= cortes.fechas[b - 1])
    return int(en.sum() - mascara(panel, cortes, nombre).sum())


def pliegues_walk_forward(fechas_ent: list[str], H: int, k: int = 4, frac_min: float = 0.4) -> list[dict]:
    """Validación progresiva dentro del entrenamiento: ventana de entrenamiento creciente, bloque de validación
    posterior separado por un embargo de H fechas; el ajuste de cada pliegue se purga contra su bloque."""
    n = len(fechas_ent)
    inicio = int(n * frac_min)
    tam = max((n - inicio) // k, H + 2)
    out = []
    for j in range(k):
        fin_ent = inicio + j * tam
        v0, v1 = fin_ent + H, min(fin_ent + tam, n)
        if v1 - v0 < 2:
            break
        out.append({"fin_entrenamiento": fechas_ent[fin_ent - 1], "inicio_validacion": fechas_ent[v0],
                    "fin_validacion": fechas_ent[v1 - 1]})
    return out


def mascaras_pliegue(panel: pd.DataFrame, p: dict) -> tuple[pd.Series, pd.Series]:
    ent = (panel["fecha"] <= p["fin_entrenamiento"]) & panel["fecha_fin_etiqueta"].notna() & (
        panel["fecha_fin_etiqueta"] < p["inicio_validacion"])
    val = (panel["fecha"] >= p["inicio_validacion"]) & (panel["fecha"] <= p["fin_validacion"])
    return ent, val


def sin_solapamiento(panel: pd.DataFrame, a: pd.Series, b: pd.Series) -> bool:
    """Comprueba que ninguna etiqueta de A llega al primer día de B (usado en pruebas)."""
    if not a.any() or not b.any():
        return True
    return bool(np.all(panel.loc[a, "fecha_fin_etiqueta"].to_numpy() < panel.loc[b, "fecha"].min()))
