"""Vigencia de datos: calendarios de mercado (NYSE, BMV), festivos y umbrales por tipo de dato.

Estados posibles:
  vigente    -> el dato corresponde a la última sesión esperada según su tipo y umbral
  retrasado  -> atraso dentro de la tolerancia configurada («dato retrasado»)
  vencido    -> atraso mayor a la tolerancia; se suspende cualquier clasificación que dependa de él
  sin_datos  -> no hay dato («sin datos suficientes»)
  sintetico  -> dato de demostración; nunca se presenta como actual
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from functools import lru_cache

import exchange_calendars as xc
import pandas as pd

ETIQUETAS = {
    "vigente": "Vigente",
    "retrasado": "Dato retrasado",
    "vencido": "Dato vencido",
    "sin_datos": "Sin datos suficientes",
    "sintetico": "Sintético (demostración)",
}
ORDEN_GRAVEDAD = {"vigente": 0, "retrasado": 1, "sintetico": 2, "vencido": 3, "sin_datos": 4}


@lru_cache(maxsize=4)
def calendario(codigo: str):
    return xc.get_calendar(codigo)


def codigo_calendario(instr: dict) -> str:
    """NYSE para listados de referencia en EE. UU.; BMV (XMEX) para emisoras locales, fondos y FX."""
    return "XNYS" if instr.get("moneda_referencia") == "USD" else "XMEX"


def _ahora(ahora: datetime | None) -> pd.Timestamp:
    ts = pd.Timestamp(ahora or datetime.now(UTC))
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def ultima_sesion_cerrada(codigo: str, ahora: datetime | None = None) -> date:
    return _ultima_sesion(codigo, _ahora(ahora).floor("min"))


@lru_cache(maxsize=256)
def _ultima_sesion(codigo: str, ts: pd.Timestamp) -> date:  # memoizada por minuto
    cal = calendario(codigo)
    sesion = cal.date_to_session(pd.Timestamp(ts.date()), direction="previous")
    while cal.session_close(sesion) > ts:  # sesión en curso o futura: retroceder
        sesion = cal.previous_session(sesion)
    return sesion.date()


@lru_cache(maxsize=4096)
def cierre_de_sesion(codigo: str, d: date) -> datetime | None:
    cal = calendario(codigo)
    s = pd.Timestamp(d)
    if not cal.is_session(s):
        return None
    return cal.session_close(s).to_pydatetime()


@lru_cache(maxsize=4096)
def sesiones_de_atraso(codigo: str, fecha_dato: date, referencia: date) -> int:
    if fecha_dato >= referencia:
        return 0
    cal = calendario(codigo)
    return max(len(cal.sessions_in_range(pd.Timestamp(fecha_dato), pd.Timestamp(referencia))) - 1, 0)


def mercado_abierto(codigo: str, ahora: datetime | None = None) -> bool:
    return bool(calendario(codigo).is_open_on_minute(_ahora(ahora).floor("min")))


def evaluar(tipo_dato: str | None, fecha_dato: str | None, codigo: str, umbrales: dict,
            hora_cotizacion: str | None = None, ahora: datetime | None = None) -> dict:
    """Devuelve estado de vigencia y retraso medido de un dato."""
    if not fecha_dato or not tipo_dato:
        return {"estado": "sin_datos", "etiqueta": ETIQUETAS["sin_datos"], "sesiones_atraso": None,
                "retraso_horas": None}
    ts = _ahora(ahora)
    f = date.fromisoformat(fecha_dato[:10])
    if hora_cotizacion:
        hq = pd.Timestamp(hora_cotizacion)
        hq = hq.tz_localize("UTC") if hq.tzinfo is None else hq
    else:
        cierre = cierre_de_sesion(codigo, f)
        hq = pd.Timestamp(cierre) if cierre else pd.Timestamp(f).tz_localize("UTC")
    retraso_h = round((ts - hq).total_seconds() / 3600, 1)
    if tipo_dato == "sintetico":
        return {"estado": "sintetico", "etiqueta": ETIQUETAS["sintetico"], "sesiones_atraso": None,
                "retraso_horas": retraso_h}
    if tipo_dato == "tiempo_real":
        estado = "vigente" if retraso_h * 3600 <= umbrales["tiempo_real_segundos_vigente"] else "retrasado"
        return {"estado": estado, "etiqueta": ETIQUETAS[estado], "sesiones_atraso": 0, "retraso_horas": retraso_h}
    if tipo_dato == "retrasado":
        estado = "retrasado" if retraso_h * 60 <= umbrales["retrasado_minutos_vigente"] else "vencido"
        if not mercado_abierto(codigo, ahora):
            tipo_dato = "cierre"  # fuera de horario se evalúa contra la última sesión
        else:
            return {"estado": estado, "etiqueta": ETIQUETAS[estado], "sesiones_atraso": 0, "retraso_horas": retraso_h}
    pref = {"cierre": "cierre", "nav": "nav", "fx": "fx"}.get(tipo_dato, "cierre")
    ref = ultima_sesion_cerrada(codigo, ahora)
    atraso = sesiones_de_atraso(codigo, f, ref)
    if atraso <= umbrales[f"{pref}_sesiones_vigente"]:
        estado = "vigente"
    elif atraso <= umbrales[f"{pref}_sesiones_retrasado"]:
        estado = "retrasado"
    else:
        estado = "vencido"
    return {"estado": estado, "etiqueta": ETIQUETAS[estado], "sesiones_atraso": atraso, "retraso_horas": retraso_h,
            "sesion_esperada": ref.isoformat()}


def peor(estados: list[str]) -> str:
    return max(estados, key=lambda e: ORDEN_GRAVEDAD.get(e, 5)) if estados else "sin_datos"
