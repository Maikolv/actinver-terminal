"""Laboratorio offline: sólo backtesting. Sin broker, red, claves ni ejecución real."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover


def validar(tabla: pd.DataFrame, meta: dict) -> pd.DataFrame:
    for campo in ("simbolo", "fuente", "licencia", "calidad", "multiplicador"):
        if not meta.get(campo):
            raise ValueError(f"Falta metadato: {campo}")
    if meta["calidad"] not in ("proveedor", "importado", "sintetico"):
        raise ValueError("Calidad no admitida")
    multiplicador = float(meta["multiplicador"])
    if not np.isfinite(multiplicador) or multiplicador <= 0:
        raise ValueError("Multiplicador inválido")
    columnas = ["fecha", "Open", "High", "Low", "Close", "Volume"]
    if not set(columnas).issubset(tabla.columns):
        raise ValueError("Se requieren fecha, Open, High, Low, Close, Volume")
    if not 150 <= len(tabla) <= 200000:
        raise ValueError("Se requieren entre 150 y 200000 barras")
    t = tabla[columnas].copy()
    fechas = [pd.Timestamp(x) for x in t.pop("fecha")]
    if any(pd.isna(x) or x.tzinfo is None for x in fechas):
        raise ValueError("Fecha sin zona horaria o inválida")
    t.index = pd.DatetimeIndex(fechas).tz_convert("UTC")
    if not t.index.is_unique or not t.index.is_monotonic_increasing:
        raise ValueError("Fechas duplicadas o desordenadas")
    t = t.apply(pd.to_numeric, errors="raise")
    if not np.isfinite(t.to_numpy()).all():
        raise ValueError("Datos no finitos")
    if (t[["Open", "High", "Low", "Close"]] <= 0).any().any() or (t.Volume < 0).any():
        raise ValueError("Precios o volumen inválidos")
    if ((t.High < t[["Open", "Low", "Close"]].max(axis=1)) |
            (t.Low > t[["Open", "High", "Close"]].min(axis=1))).any():
        raise ValueError("OHLC inconsistente")
    return t


def demo() -> tuple[pd.DataFrame, dict]:
    n = 600
    base = 100 + np.sin(np.arange(n) / 15) * 6 + np.arange(n) / 100
    apertura = np.r_[base[0], base[:-1]]
    fechas = pd.date_range("2026-01-05T14:30:00Z", periods=n, freq="5min")
    tabla = pd.DataFrame({"fecha": fechas.astype(str), "Open": apertura,
                          "High": np.maximum(apertura, base) + .2,
                          "Low": np.minimum(apertura, base) - .2,
                          "Close": base, "Volume": np.full(n, 1000)})
    return tabla, {"simbolo": "DEMO:SINTETICO", "fuente": "fixture matemático local",
                   "licencia": "CC0; fixture generado para pruebas", "calidad": "sintetico",
                   "multiplicador": 1, "nota": "No representa un instrumento ni sesiones de mercado reales"}


def ejecutar(tabla: pd.DataFrame, meta: dict, comision: float = 1.0,
             spread: float = .0001, capital: float = 1000000) -> dict:
    if not all(np.isfinite(x) for x in (comision, spread, capital)) or comision < 0 or not 0 <= spread < .1 or capital <= 0:
        raise ValueError("Costes o capital inválidos")
    datos = validar(tabla, meta)
    corte = int(len(datos) * .8)
    inicio = datos.index[corte]
    # 50 barras anteriores sólo para calentamiento. Ninguna operación antes del corte.
    evaluacion = datos.iloc[corte - 50:].copy()
    evaluacion.loc[:, ["Open", "High", "Low", "Close"]] *= float(meta["multiplicador"])

    class CruceSma(Strategy):
        def init(self):
            self.rapida = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.Close)
            self.lenta = self.I(lambda x: pd.Series(x).rolling(50).mean(), self.data.Close)

        def next(self):
            if self.data.index[-1] < inicio:
                return
            if crossover(self.rapida, self.lenta) and not self.position:
                self.buy(size=1)
            elif crossover(self.lenta, self.rapida) and self.position:
                self.position.close()

    estadisticas = Backtest(evaluacion, CruceSma, cash=capital, spread=spread,
                           commission=lambda cantidad, precio: abs(cantidad) * comision,
                           margin=1, trade_on_close=False, exclusive_orders=True,
                           finalize_trades=True).run()
    operaciones = estadisticas["_trades"]
    if len(operaciones) and (operaciones.EntryTime < inicio).any():
        raise RuntimeError("Operación fuera del periodo de evaluación")
    return {"motor": "backtesting.py", "version": importlib.metadata.version("backtesting"),
            "procedencia": meta, "sha256_csv_normalizado": hashlib.sha256(tabla.to_csv(index=False).encode()).hexdigest(),
            "estrategia": "SMA20/50 long/flat, tamaño fijo 1, señal al cierre y ejecución en apertura siguiente",
            "corte_temporal": str(inicio), "barras_calentamiento": 50,
            "parametros_optimizados": False, "ordenes_reales": False,
            "capital_virtual": capital, "comision_por_lado_por_unidad": comision, "spread_relativo": spread,
            "operaciones": int(estadisticas["# Trades"]),
            "pnl_neto_virtual": float(estadisticas["Equity Final [$]"] - capital),
            "retorno_capital_virtual_pct": float(estadisticas["Return [%]"]),
            "drawdown_max_pct": float(estadisticas["Max. Drawdown [%]"]),
            "primera_entrada": str(operaciones.EntryTime.min()) if len(operaciones) else None,
            "limites": ["Ejemplo exploratorio; no demuestra alfa ni aplica reglas de una prop firm",
                        "Margin=1: sin apalancamiento; no modela márgenes, rollover, colas, ticks ni liquidación de futuros",
                        "Multiplicador transforma precios en valor por contrato/unidad; verificar especificación y comisiones",
                        "Spread constante no sustituye un modelo de slippage con libro de órdenes",
                        "Repetir el experimento o elegir reglas tras ver el periodo deja de ser un holdout independiente"]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--csv", type=Path)
    p.add_argument("--metadata", type=Path)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--comision", type=float, default=1.0)
    p.add_argument("--spread", type=float, default=.0001)
    p.add_argument("--capital", type=float, default=1000000)
    a = p.parse_args()
    if a.demo and (a.csv or a.metadata):
        p.error("--demo no se combina con --csv/--metadata")
    if a.demo:
        tabla, meta = demo()
    else:
        if not a.csv or not a.metadata:
            p.error("Proporcione --csv y --metadata, o --demo")
        if a.csv.stat().st_size > 40 * 1024 * 1024:
            p.error("CSV supera el límite de 40 MiB")
        tabla = pd.read_csv(a.csv, nrows=200001)
        meta = json.loads(a.metadata.read_text(encoding="utf-8"))
    resultado = ejecutar(tabla, meta, a.comision, a.spread, a.capital)
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Informe offline guardado: {a.salida}")
