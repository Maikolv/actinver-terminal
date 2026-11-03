"""Inspección por defecto; aplicación explícita con respaldo, sin red, claves, motor ni órdenes."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from terminal import calidad_precios, db  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=RAIZ / "data/terminal.db")
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--esperados", type=int)
    args = parser.parse_args()
    ruta = args.base.resolve()
    if ruta.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise SystemExit("Indique un archivo de base SQLite.")
    if not ruta.is_file():
        raise SystemExit("La base indicada no existe; no se crea ninguna.")
    if args.aplicar and args.esperados is None:
        parser.error("--aplicar requiere --esperados con el recuento revisado.")
    con = sqlite3.connect(ruta.as_uri() + ("?mode=rw" if args.aplicar else "?mode=ro"), uri=True)
    try:
        con.execute("PRAGMA foreign_keys=ON")
        if not args.aplicar:
            con.execute("PRAGMA query_only=ON")
        previo = calidad_precios.auditar(con)
        resultado = {"modo": "solo lectura", "auditoria": previo}
        if args.aplicar:
            if previo["candidatos"] != args.esperados:
                raise SystemExit("El recuento cambió; no se aplicó la cuarentena.")
            # El máximo tamaño de lista impide rotar/eliminar respaldos anteriores en esta llamada.
            copia = db.respaldar(ruta, conservar=sys.maxsize)
            resultado = {"modo": "cuarentena local", "auditoria_previa": previo, "respaldo": str(copia),
                         "resultado": calidad_precios.poner_en_cuarentena(con, args.esperados),
                         "auditoria_posterior": calidad_precios.auditar(con)}
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    finally:
        con.close()


if __name__ == "__main__":
    main()
