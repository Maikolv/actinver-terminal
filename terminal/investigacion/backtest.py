"""Verificación cruzada de backtest: motor por eventos (backtrader, mementum/backtrader, GPL-3.0) frente a un cálculo
independiente propio con las mismas reglas del simulador.

Reglas comunes: rebalanceo a pesos iguales cada N sesiones al precio de cierre, títulos ENTEROS, primero ventas y luego
compras con el efectivo disponible, comisión 0.10 % + IVA 16 % sobre cada importe, sin cortos ni apalancamiento.
Si ambos motores no coinciden dentro de la tolerancia, hay un error de contabilidad en alguno.

backtrader NO se incluye en el proyecto (licencia GPL-3.0 frente a MIT): se usa como herramienta externa desde su copia
local (`BACKTRADER_RUTA`, por defecto ../backtrader) o desde un paquete instalado aparte.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import pandas as pd

from ..config import RAIZ


def reglas_rebalanceo(valor: float, precios: dict[str, float], ids: list[str]) -> dict[str, int]:
    """Títulos enteros objetivo para pesos iguales sobre el valor total disponible."""
    return {i: math.floor((valor / len(ids)) / precios[i]) for i in ids}


def referencia_vectorizada(precios: pd.DataFrame, capital: float, costo: float, cada: int) -> dict:
    ids = list(precios.columns)
    efectivo, tit, costos, operaciones = float(capital), {i: 0 for i in ids}, 0.0, 0
    for k, (_, fila) in enumerate(precios.iterrows()):
        px = fila.to_dict()
        if k % cada == 0:
            valor = efectivo + sum(tit[i] * px[i] for i in ids)
            # descuento aproximado de costos para que las compras quepan en el efectivo
            objetivo = reglas_rebalanceo(valor / (1 + costo), px, ids)
            for i in sorted(ids, key=lambda x: objetivo[x] - tit[x]):  # ventas primero
                delta = objetivo[i] - tit[i]
                if delta == 0:
                    continue
                importe = abs(delta) * px[i]
                c = importe * costo
                if delta > 0 and efectivo < importe + c:
                    delta = math.floor(efectivo / (px[i] * (1 + costo)))
                    if delta <= 0:
                        continue
                    importe, c = delta * px[i], delta * px[i] * costo
                efectivo += -importe - c if delta > 0 else importe - c
                tit[i] += delta
                costos += c
                operaciones += 1
    final = efectivo + sum(tit[i] * float(precios.iloc[-1][i]) for i in ids)
    return {"motor": "cálculo independiente", "valor_final": round(final, 2), "costos": round(costos, 2),
            "operaciones": operaciones, "titulos": tit, "efectivo": round(efectivo, 2)}


def _importar_backtrader():
    try:
        import backtrader as bt  # noqa: F401
        return bt
    except ImportError:
        ruta = Path(os.environ.get("BACKTRADER_RUTA", RAIZ.parent / "backtrader"))
        if (ruta / "backtrader").exists():
            sys.path.insert(0, str(ruta))
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                import backtrader as bt
            return bt
    return None


def backtrader_disponible() -> bool:
    return _importar_backtrader() is not None


def con_backtrader(precios: pd.DataFrame, capital: float, costo: float, cada: int) -> dict:
    bt = _importar_backtrader()
    if bt is None:
        raise RuntimeError("backtrader no disponible (defina BACKTRADER_RUTA o instálelo aparte)")
    ids = list(precios.columns)

    class Rebalanceo(bt.Strategy):
        def __init__(self):
            self.k = 0
            self.ops = 0

        def next(self):
            if self.k % cada == 0:
                px = {d._name: float(d.close[0]) for d in self.datas}
                valor = self.broker.getvalue()
                objetivo = reglas_rebalanceo(valor / (1 + costo), px, ids)
                efectivo = self.broker.getcash()
                for d in sorted(self.datas, key=lambda d: objetivo[d._name] - self.getposition(d).size):
                    actual = self.getposition(d).size
                    delta = objetivo[d._name] - actual
                    if delta == 0:
                        continue
                    if delta > 0:
                        maximo = math.floor(efectivo / (px[d._name] * (1 + costo)))
                        delta = min(delta, maximo)
                        if delta <= 0:
                            continue
                        efectivo -= delta * px[d._name] * (1 + costo)
                        self.buy(data=d, size=delta)
                    else:
                        efectivo += -delta * px[d._name] * (1 - costo)
                        self.sell(data=d, size=-delta)
                    self.ops += 1
            self.k += 1

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(capital)
    cerebro.broker.set_coc(True)            # ejecuta al cierre de la barra de la señal (igual que la referencia)
    cerebro.broker.set_checksubmit(False)   # el efectivo ya se controló con la misma regla
    cerebro.broker.setcommission(commission=costo)  # porcentaje sobre el importe: comisión + IVA
    idx = pd.to_datetime(precios.index)
    for i in ids:
        df = pd.DataFrame({"open": precios[i].values, "high": precios[i].values, "low": precios[i].values,
                           "close": precios[i].values, "volume": 1e9}, index=idx)
        cerebro.adddata(bt.feeds.PandasData(dataname=df, openinterest=None), name=i)
    cerebro.addstrategy(Rebalanceo)
    est = cerebro.run()[0]
    return {"motor": f"backtrader {bt.__version__}", "valor_final": round(cerebro.broker.getvalue(), 2),
            "operaciones": est.ops, "efectivo": round(cerebro.broker.getcash(), 2),
            "titulos": {d._name: int(est.getposition(d).size) for d in est.datas}}


def comparar(precios: pd.DataFrame, capital: float = 1_000_000, costo: float = 0.00116, cada: int = 5,
             tolerancia: float = 1e-4) -> dict:
    ref = referencia_vectorizada(precios, capital, costo, cada)
    if not backtrader_disponible():
        return {"referencia": ref, "backtrader": None, "coinciden": None, "nota": "backtrader no disponible"}
    btr = con_backtrader(precios, capital, costo, cada)
    dif = abs(btr["valor_final"] / ref["valor_final"] - 1)
    return {"referencia": ref, "backtrader": btr, "diferencia_relativa": dif, "coinciden": dif <= tolerancia,
            "titulos_iguales": btr["titulos"] == ref["titulos"]}
