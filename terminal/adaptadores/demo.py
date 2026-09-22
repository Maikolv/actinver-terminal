"""Generador de datos SINTÉTICOS para demostración y pruebas.

Solo se activa con TERMINAL_MODO=demo. Todo lo que produce queda marcado con
proveedor «demo_sintetico» y tipo de dato «sintetico», que la capa de vigencia nunca
considera actual. No representa cotizaciones reales de ningún instrumento.
"""
from __future__ import annotations

import hashlib
import sqlite3

import numpy as np
import pandas as pd

from ..db import ahora, transaccion
from ..vigencia import calendario

PROVEEDOR = "demo_sintetico"

# (rendimiento anual, volatilidad anual, carga al factor de mercado) por clase — supuestos ilustrativos
PARAMS = {
    "accion": (0.09, 0.30, 0.9), "reit": (0.07, 0.28, 0.7), "fibra": (0.08, 0.22, 0.6),
    "etf": (0.08, 0.17, 0.8), "fondo_renta_variable": (0.08, 0.18, 0.85),
    "fondo_multiactivo": (0.07, 0.10, 0.5), "fondo_deuda": (0.085, 0.03, 0.05),
}


def _semilla(texto: str) -> int:
    return int(hashlib.sha256(texto.encode()).hexdigest()[:8], 16)


def generar(con: sqlite3.Connection, anios: int = 5, semilla: int = 42) -> int:
    fechas = calendario("XNYS").sessions_in_range(pd.Timestamp.today().normalize() - pd.DateOffset(years=anios),
                                                   pd.Timestamp.today().normalize() - pd.Timedelta(days=1))
    n = len(fechas)
    rng = np.random.default_rng(semilla)
    mercado = rng.normal(0.0, 0.011, n)
    fx = 17.5 * np.exp(np.cumsum(rng.normal(0, 0.006, n)))
    instrs = con.execute("SELECT id, clase, categoria, moneda_referencia FROM instrumentos WHERE estado='activo'").fetchall()
    filas = []
    ts = ahora()
    for ins in instrs:
        mu, vol, beta = PARAMS.get(ins["clase"], (0.07, 0.2, 0.7))
        r2 = np.random.default_rng(_semilla(ins["id"]) ^ semilla)
        mu = mu + r2.normal(0, 0.03)
        vol = max(vol * r2.uniform(0.7, 1.4), 0.01)
        idio = np.sqrt(max(vol**2 / 252 - (beta * 0.011) ** 2, 1e-8))
        ret = mu / 252 + beta * mercado + r2.normal(0, idio, n)
        precio = 100 * np.exp(np.cumsum(ret))
        moneda = ins["moneda_referencia"] or "MXN"
        for f, p in zip(fechas, precio):
            filas.append((ins["id"], f.date().isoformat(), float(p), float(p), 1e6, moneda, PROVEEDOR,
                          "sintetico", None, ts))
    with transaccion(con):
        con.execute("DELETE FROM precios WHERE proveedor=?", (PROVEEDOR,))
        con.executemany("INSERT INTO precios VALUES (?,?,?,?,?,?,?,?,?,?)", filas)
        con.execute("DELETE FROM fx WHERE proveedor=?", (PROVEEDOR,))
        con.executemany("INSERT INTO fx VALUES ('USDMXN',?,?,?,?,?)",
                        [(f.date().isoformat(), float(v), PROVEEDOR, "sintetico", ts) for f, v in zip(fechas, fx)])
    return len(filas)
