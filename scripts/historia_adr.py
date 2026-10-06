"""Descarga la historia diaria de los ADR (EE. UU.) de emisoras de la BMV con la clave gratuita de Tiingo (uso
personal). Sirve para extender HACIA ATRÁS la historia de esas emisoras: el plan gratuito de EODHD solo da 1 año.

No son precios de la BMV: son rendimientos del ADR convertidos a MXN con el FIX de cada fecha (terminal/proxy_adr.py),
y solo se usan si en el año en que hay ambos se mueven juntos (correlación diaria ≥ 0.80).

Uso: uv run python scripts/historia_adr.py   → data/referencias/adr/<ADR>.csv (local, fuera de Git)
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal import config, db, proxy_adr  # noqa: E402
from terminal.adaptadores.base import ErrorProveedor  # noqa: E402
from terminal.adaptadores.proveedores import Tiingo  # noqa: E402
from terminal.config import cargar_ajustes  # noqa: E402


def main() -> None:
    ajustes = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con, ajustes)
    import os
    t = Tiingo(con, (ajustes.get("proveedores") or {}).get("tiingo", {}), os.environ.get("TIINGO_API_KEY"))
    if not t.configurado():
        sys.exit("Falta TIINGO_API_KEY en .env")
    carpeta = config.data_dir() / "referencias" / "adr"
    carpeta.mkdir(parents=True, exist_ok=True)
    for local, adr in proxy_adr.MAPA.items():
        try:
            barras = t.historico({"id": f"ADR:{adr}", "listado_referencia": adr, "moneda_referencia": "USD"},
                                 date(2021, 1, 1), date.today())
        except ErrorProveedor as e:
            print(f"{local:<14} {adr:<6} sin datos: {str(e)[:80]}")
            continue
        with (carpeta / f"{adr}.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["fecha", "cierre", "factor_split", "volumen"])
            w.writerows([(b.fecha, b.cierre, b.factor_split, b.volumen) for b in barras])
        print(f"{local:<14} {adr:<6} {len(barras)} sesiones {barras[0].fecha if barras else ''} → {barras[-1].fecha if barras else ''}",
              flush=True)
        time.sleep(1.5)  # respeta los límites por hora del plan gratuito


if __name__ == "__main__":
    main()
