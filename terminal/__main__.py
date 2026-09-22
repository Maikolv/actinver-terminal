"""Línea de comandos: iniciar | actualizar | respaldar | demo.

  uv run terminal iniciar        # abre la terminal en http://127.0.0.1:8765
  uv run terminal actualizar     # consulta proveedores configurados (respeta límites)
  uv run terminal respaldar      # copia verificada de la base de datos local
"""
from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sqlite3
import sys
import webbrowser
from datetime import datetime
from pathlib import Path


def _logs() -> None:
    from .config import DATA_DIR
    d = Path(DATA_DIR) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(d / "terminal.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[h, logging.StreamHandler()])
    logging.getLogger("httpx").setLevel(logging.WARNING)  # nunca registrar URLs con credenciales


def iniciar(args) -> None:
    import uvicorn

    from .config import cargar_ajustes
    a = cargar_ajustes()
    host = a["app"]["host"]
    if host not in ("127.0.0.1", "localhost", "::1"):
        sys.exit("Por seguridad la terminal solo escucha en la máquina local (host 127.0.0.1). "
                 "Vea docs/12-seguridad.md antes de exponerla en red.")
    url = f"http://127.0.0.1:{a['app']['puerto']}/"
    print(f"Terminal disponible en {url}  (modo: {a.modo}). Ctrl+C para detener.")
    if not args.sin_navegador:
        webbrowser.open(url)
    uvicorn.run("terminal.app:app", host=host, port=int(a["app"]["puerto"]), log_level="warning",
                server_header=False, proxy_headers=False)


def actualizar(_args) -> None:
    from . import db, ingesta
    from .config import cargar_ajustes
    a = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con)
    print(ingesta.actualizar_todo(con, a))


def respaldar(args) -> None:
    from . import db
    origen = db.ruta_db()
    destino_dir = origen.parent / "respaldos"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"terminal-{datetime.now():%Y%m%d-%H%M%S}.db"
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
    n = dst.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]
    src.close()
    dst.close()
    if ok != "ok":
        destino.unlink(missing_ok=True)
        sys.exit(f"Respaldo inválido ({ok}); no se conservó")
    copias = sorted(destino_dir.glob("terminal-*.db"))
    for viejo in copias[: max(len(copias) - args.conservar, 0)]:
        viejo.unlink()
    print(f"Respaldo verificado: {destino} (integridad ok, {n} operaciones)")


def main() -> None:
    p = argparse.ArgumentParser(prog="terminal", description="Terminal local de análisis de portafolios")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("iniciar", help="inicia el servidor local y abre el navegador")
    s.add_argument("--sin-navegador", action="store_true")
    s.set_defaults(fn=iniciar)
    sub.add_parser("actualizar", help="actualiza datos de mercado").set_defaults(fn=actualizar)
    r = sub.add_parser("respaldar", help="crea un respaldo verificado de la base local")
    r.add_argument("--conservar", type=int, default=14)
    r.set_defaults(fn=respaldar)
    d = sub.add_parser("demo", help="inicia con datos SINTÉTICOS etiquetados (sin credenciales)")
    d.add_argument("--sin-navegador", action="store_true")
    d.set_defaults(fn=iniciar)
    args = p.parse_args()
    if args.cmd == "demo":  # base separada: los datos sintéticos nunca se mezclan con los reales
        # Se fija antes de importar .config, que lee estas variables al cargarse.
        os.environ["TERMINAL_MODO"] = "demo"  # la base se separa sola en data/demo (config.data_dir)
    _logs()
    args.fn(args)


if __name__ == "__main__":
    main()
