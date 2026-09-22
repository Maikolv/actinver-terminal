"""Genera un CSV de operaciones de DEMOSTRACIÓN coherente con los precios sintéticos del modo demo.

Uso (con el modo demo inicializado al menos una vez):
    uv run python scripts/cartera_demo.py  ->  data/demo/cartera_demo.csv
Después impórtelo desde «Mi cartera → Importar». No representa operaciones reales.
"""
import csv
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "data" / "demo" / "terminal.db"
PLAN = [  # (fecha aproximada, tipo, instrumento, cantidad | monto)
    ("2024-01-03", "aportacion", None, 1000000),
    ("2024-01-04", "compra", "SIC:IVV", 200),
    ("2024-01-04", "compra", "FONDO:ACTIGOB", 2700),
    ("2024-02-01", "compra", "BMV:WALMEX", 1000),
    ("2024-03-01", "compra", "SIC:MSFT", 65),
    ("2024-09-02", "dividendo", "BMV:WALMEX", 1500),
    ("2025-02-03", "venta", "SIC:IVV", 50),
    ("2025-06-02", "retiro", None, 30000),
]


def precio(con, iid, fecha):
    f = con.execute("SELECT fecha, cierre, moneda FROM precios WHERE instrumento_id=? AND fecha>=? ORDER BY fecha LIMIT 1",
                    (iid, fecha)).fetchone()
    fx = con.execute("SELECT valor FROM fx WHERE par='USDMXN' AND fecha<=? ORDER BY fecha DESC LIMIT 1", (f[0],)).fetchone()
    return f[0], round(f[1] * (fx[0] if f[2] == "USD" else 1), 4)


def main():
    con = sqlite3.connect(DB)
    filas = []
    for fecha, tipo, iid, x in PLAN:
        if tipo in ("compra", "venta"):
            fecha, px = precio(con, iid, fecha)
            com = round(x * px * 0.0025 * 1.16, 2)
            filas.append([fecha, tipo, iid, x, px, "", com, 0, "MXN", 1, "DEMO sintética"])
        else:
            filas.append([fecha, tipo, iid or "", "", "", x, "", round(x * 0.1, 2) if tipo == "dividendo" else "", "MXN", 1,
                          "DEMO sintética"])
    salida = RAIZ / "data" / "demo" / "cartera_demo.csv"
    with salida.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["fecha", "tipo", "instrumento_id", "cantidad", "precio", "monto", "comision", "impuesto", "moneda",
                    "tipo_cambio", "nota"])
        w.writerows(filas)
    print(salida)


if __name__ == "__main__":
    main()
