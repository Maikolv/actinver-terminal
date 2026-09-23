"""Reducción PEQUEÑA de correlación entre VARIABLES PREDICTORAS, ajustada solo con el entrenamiento de cada ventana.

Criterio declarado antes de evaluar: se recorren las variables en su orden de prioridad (datos.VARIABLES) y se
conserva una variable si su |r| con todas las ya conservadas es < umbral (0.95 por defecto). Ante un par casi
duplicado queda la de mayor prioridad (más simple y estable). La matriz se calcula con el `fit` (entrenamiento);
`transform` solo selecciona columnas: validación y prueba no influyen en la selección.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class FiltroCorrelacion(TransformerMixin, BaseEstimator):
    def __init__(self, umbral: float = 0.95, prioridad: list[str] | None = None):
        self.umbral = umbral
        self.prioridad = prioridad

    def fit(self, X, y=None):
        X = pd.DataFrame(X) if not isinstance(X, pd.DataFrame) else X
        orden = [c for c in (self.prioridad or []) if c in X.columns] + [c for c in X.columns if c not in (self.prioridad or [])]
        c = X[orden].corr().abs().fillna(0.0)
        conservadas, eliminadas = [], []
        for v in orden:
            choque = [(k, float(c.loc[v, k])) for k in conservadas if c.loc[v, k] >= self.umbral]
            if choque:
                k, r = max(choque, key=lambda x: x[1])
                eliminadas.append({"variable": v, "conservada": k, "abs_r": round(r, 4)})
            else:
                conservadas.append(v)
        self.columnas_ = conservadas
        self.eliminadas_ = eliminadas
        self.matriz_ = c
        self.n_features_in_ = X.shape[1]
        self.feature_names_in_ = np.asarray(list(X.columns), dtype=object)
        return self

    def transform(self, X):
        X = pd.DataFrame(X, columns=self.feature_names_in_) if not isinstance(X, pd.DataFrame) else X
        return X[self.columnas_]

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.columnas_, dtype=object)
