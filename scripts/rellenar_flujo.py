"""Carga inicial de velas, libro, operaciones y cadenas de opciones para todos los instrumentos del SIC con listado en
EE. UU. (Alpaca gratuito, el mismo `servicio.actualizar` del botón «Actualizar» de cada panel).

Respeta el límite gratuito de Alpaca con una pausa entre consultas y se puede repetir: lo ya consultado hace poco queda
«en espera» y no se vuelve a pedir. La BMV y los fondos no tienen proveedor gratuito de flujo: no se tocan.

    uv run python scripts/rellenar_flujo.py [--pausa 0.4] [--simbolos SIC:MU,SIC:XOM]
"""
from __future__ import annotations

import argparse
import collections
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from terminal import db  # noqa: E402
from terminal.config import cargar_ajustes  # noqa: E402
from terminal.flujo import servicio  # noqa: E402

# (tipo, intervalo, días): las vistas por omisión de Velas, Order Flow y Option Flow
PEDIDOS = [("velas", "1Day", 365), ("velas", "1Hour", 30), ("velas", "15Min", 10), ("velas", "5Min", 5),
           ("velas", "1Min", 2), ("libro", "1Day", 1), ("operaciones", "1Day", 1),
           ("contratos_oi", "1Day", 1), ("opciones", "1Day", 1)]  # el OI va antes: el GEX solo une OI ya conocido


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pausa", type=float, default=0.4, help="segundos entre consultas (Alpaca gratuito: 200 por minuto)")
    ap.add_argument("--simbolos", default="", help="lista separada por comas; vacío = todo el catálogo SIC")
    a = ap.parse_args()
    ajustes = cargar_ajustes()
    con = db.conectar()
    sic = [x["id"] for x in servicio.catalogo(con, ajustes)["sic"]]
    simbolos = [s for s in a.simbolos.split(",") if s] or sic
    cuenta: collections.Counter = collections.Counter()
    problemas = []
    for k, s in enumerate(simbolos, 1):
        for tipo, intervalo, dias in PEDIDOS:
            r = servicio.actualizar(con, ajustes, tipo, s, intervalo, dias)
            cuenta[(tipo, intervalo if tipo == "velas" else "", r["estado"])] += 1
            if r["estado"] not in ("ok", "en_espera"):
                problemas.append(f"{s} {tipo} {intervalo if tipo == 'velas' else ''}: {r['estado']} · {r['mensaje'][:120]}")
            time.sleep(a.pausa)
        print(f"[{k}/{len(simbolos)}] {s}", flush=True)
    print("\nResumen (tipo, intervalo, estado): cuántos")
    for clave, n in sorted(cuenta.items()):
        print(f"  {clave}: {n}")
    print(f"\n{len(problemas)} consultas sin datos o con error:")
    print("\n".join(problemas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
