"""Historia sustituta de emisoras BMV a partir de su ADR en EE. UU. (alternativa gratuita a EODHD de pago).

Por qué: el plan gratuito de EODHD solo da un año de cierres de la BMV. Varias emisoras tienen ADR en EE. UU. con
historia larga en Tiingo (clave gratuita, uso personal). El rendimiento diario del ADR convertido a MXN con el FIX de
cada fecha aproxima el de la acción local: el ADR es un certificado sobre esas mismas acciones, y la BMV y NYSE
cierran a la misma hora (14:00 CDMX = 16:00 Nueva York).

Reglas:
- Nunca se guarda como precio de la BMV ni se muestra como cotización: solo extiende RENDIMIENTOS hacia atrás, antes
  del primer dato local, para validar con historia larga (protocolo de robustez, validación).
- Solo splits (el Reto no reproduce dividendos). El cambio de razón del ADR llega como split en Tiingo.
- Solo se usa si en el periodo con ambos datos (≥ 120 sesiones) la correlación diaria es ≥ 0.80. Si no, se descarta
  y se informa.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, mercado

# Emisora BMV → ADR (programas de ADR públicos de cada emisora; los OTC se aceptan solo si pasan la validación)
MAPA = {"BMV:AMX": "AMX", "BMV:FEMSA": "FMX", "BMV:CEMEX": "CX", "BMV:ASUR": "ASR", "BMV:GAP": "PAC", "BMV:OMA": "OMAB",
        "BMV:KOF": "KOF", "BMV:TLEVISA": "TV", "BMV:VESTA": "VTMX", "BMV:VOLAR": "VLRS", "BMV:BIMBO": "BMBOY",
        "BMV:WALMEX": "WMMVY", "BMV:GFNORTE": "GBOOY", "BMV:GMEXICO": "GMBXF", "BMV:KIMBER": "KCDMY",
        "BMV:GCARSO": "GPOVY", "BMV:ORBIA": "MXCHY", "BMV:PE&OLES": "IPOAF"}
MIN_SOLAPE = 120
MIN_CORRELACION = 0.80


def carpeta() -> Path:
    return config.data_dir() / "referencias" / "adr"


def serie_adr(adr: str, base: Path | None = None) -> pd.Series:
    """Precio del ADR ajustado solo por splits (USD), por fecha."""
    f = (base or carpeta()) / f"{adr}.csv"
    if not f.exists():
        return pd.Series(dtype=float)
    filas = list(csv.DictReader(f.open(encoding="utf-8")))
    if not filas:
        return pd.Series(dtype=float)
    df = pd.DataFrame(filas)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.set_index("fecha").sort_index()
    c, sp = df["cierre"].astype(float), df["factor_split"].astype(float)
    # el factor de split del día t multiplica a las fechas anteriores (mismo criterio que mercado._solo_splits)
    ajuste = sp[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    return c / ajuste


def retornos_mxn(adr: str, fx: pd.Series, base: Path | None = None) -> pd.Series:
    p = serie_adr(adr, base)
    if p.empty or fx.empty:
        return pd.Series(dtype=float)
    fx_al = fx.reindex(p.index.union(fx.index)).ffill(limit=3).reindex(p.index)
    return (p * fx_al).pct_change(fill_method=None).dropna()


def validar(local: pd.Series, proxy: pd.Series) -> dict:
    """Correlación y error de seguimiento diarios en el periodo con ambos datos."""
    comun = local.dropna().index.intersection(proxy.dropna().index)
    if len(comun) < MIN_SOLAPE:
        return {"aceptado": False, "motivo": f"solo {len(comun)} sesiones en común (mínimo {MIN_SOLAPE})", "n": len(comun)}
    a, b = local.loc[comun], proxy.loc[comun]
    rho = float(np.corrcoef(a, b)[0, 1])
    te = float((a - b).std() * np.sqrt(252))
    ok = rho >= MIN_CORRELACION
    return {"aceptado": ok, "n": len(comun), "correlacion": round(rho, 3), "error_seguimiento_anual": round(te, 3),
            "motivo": "" if ok else f"correlación {rho:.2f} < {MIN_CORRELACION}"}


def extender(con, ajustes, R: pd.DataFrame, base: Path | None = None) -> tuple[pd.DataFrame, list[dict]]:
    """R (rendimientos diarios MXN, fechas × ids): llena las fechas ANTERIORES al primer dato local de cada emisora con
    el rendimiento del ADR en MXN, solo si el ADR pasa la validación. Devuelve (R extendida, informe por emisora)."""
    fx = mercado.fx_serie(con, ajustes)
    R2, informe = R.copy(), []
    for iid, adr in MAPA.items():
        if iid not in R.columns:
            continue
        prox = retornos_mxn(adr, fx, base)
        if prox.empty:
            informe.append({"id": iid, "adr": adr, "aceptado": False, "motivo": "sin historia del ADR descargada"})
            continue
        v = validar(R[iid], prox)
        fila = {"id": iid, "adr": adr, **v}
        if v["aceptado"]:
            primero = R[iid].first_valid_index()
            antes = prox.loc[prox.index < primero].reindex(R.index).dropna()
            antes = antes.loc[antes.index < primero]
            R2.loc[antes.index, iid] = antes
            fila.update(sesiones_agregadas=int(len(antes)),
                        desde=str(antes.index[0].date()) if len(antes) else None)
        informe.append(fila)
    return R2, informe
