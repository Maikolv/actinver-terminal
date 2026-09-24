"""Candidato experimental Kronos (shiyu-coder/Kronos, MIT): modelo fundacional para series de velas (K-line).

Identidad verificada en la copia local (README y model/): `KronosTokenizer`, `Kronos`, `KronosPredictor.predict(df,
x_timestamp, y_timestamp, pred_len, T, top_p, sample_count)`; exige columnas open/high/low/close y un contexto ≤ 512.

Requisitos que HOY no están disponibles en este equipo (no se descargan sin autorización del usuario):
- `torch>=2.0` (rueda CPU para Windows, del orden de cientos de MB) y `einops`, `huggingface_hub`, `safetensors`;
- pesos públicos `NeoQuasar/Kronos-mini` (o -small) y `NeoQuasar/Kronos-Tokenizer-2k`/`-base` desde Hugging Face.

Protocolo cuando estén disponibles: pronóstico a H sesiones con contexto SOLO hasta t (sin fuga), en las mismas fechas de
prueba que el experimento principal y frente a las mismas referencias. Un pronóstico de Kronos nunca es un precio
observado: se guarda como FUTURO. Con series de solo cierre (FRED, CSV), open=high=low=close degrada el insumo del modelo
y se reporta así.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import RAIZ

RUTA = Path(os.environ.get("KRONOS_RUTA", RAIZ.parent / "Kronos"))
MODELO = os.environ.get("KRONOS_MODELO", "NeoQuasar/Kronos-mini")
TOKENIZADOR = os.environ.get("KRONOS_TOKENIZADOR", "NeoQuasar/Kronos-Tokenizer-2k")


def estado() -> dict:
    faltan = []
    if not (RUTA / "model").exists():
        faltan.append(f"código de Kronos en {RUTA} (KRONOS_RUTA)")
    for mod in ("torch", "einops", "huggingface_hub", "safetensors"):
        if importlib.util.find_spec(mod) is None:
            faltan.append(f"paquete {mod}")
    return {"identidad": "shiyu-coder/Kronos (MIT)", "modelo": MODELO, "tokenizador": TOKENIZADOR,
            "disponible": not faltan, "pendiente": faltan,
            "nota": "Descargar torch y pesos requiere autorización explícita del usuario; no se hace automáticamente."}


def cargar(dispositivo: str = "cpu"):
    e = estado()
    if not e["disponible"]:
        raise RuntimeError("Kronos no disponible: " + "; ".join(e["pendiente"]))
    sys.path.insert(0, str(RUTA))
    from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore
    tok = KronosTokenizer.from_pretrained(TOKENIZADOR)
    mdl = Kronos.from_pretrained(MODELO)
    return KronosPredictor(mdl, tok, device=dispositivo, max_context=512)


def pronosticos_rodantes(serie: pd.Series, fechas_objetivo: list, H: int, predictor, contexto: int = 256) -> pd.Series:
    """log(P[t+H]/P[t]) pronosticado para cada t en fechas_objetivo con contexto estrictamente ≤ t.
    `predictor` debe exponer predict(df, x_timestamp, y_timestamp, pred_len, ...) como KronosPredictor."""
    s = serie.dropna().sort_index()
    out = {}
    for t in fechas_objetivo:
        hist = s.loc[:t].iloc[-contexto:]
        if len(hist) < 30:
            continue
        df = pd.DataFrame({"open": hist.values, "high": hist.values, "low": hist.values, "close": hist.values})
        x_ts = pd.Series(pd.to_datetime(hist.index))
        y_ts = pd.Series(pd.bdate_range(pd.Timestamp(hist.index[-1]) + pd.tseries.offsets.BDay(1), periods=H))
        pred = predictor.predict(df=df, x_timestamp=x_ts, y_timestamp=y_ts, pred_len=H, T=1.0, top_p=0.9, sample_count=1)
        out[t] = float(np.log(float(pred["close"].iloc[-1]) / float(hist.iloc[-1])))
    return pd.Series(out, dtype=float)
