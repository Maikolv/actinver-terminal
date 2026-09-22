"""Base de datos SQLite local. Todas las consultas usan parámetros (sin concatenar SQL)."""
from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from . import config
from .config import CONFIG_DIR

ESQUEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS instrumentos (
    id TEXT PRIMARY KEY, clave TEXT NOT NULL, serie TEXT, clave_operable TEXT, nombre TEXT,
    clase TEXT NOT NULL, categoria TEXT, pais TEXT, mercado_operable TEXT, moneda_operable TEXT,
    zona_horaria_operable TEXT, listado_referencia TEXT, moneda_referencia TEXT, bolsa_referencia TEXT,
    zona_horaria_referencia TEXT, estado TEXT NOT NULL, secciones_pdf TEXT, fuente_verificacion TEXT,
    detalle_verificacion TEXT, fecha_verificacion TEXT
);

-- Precios en la moneda de su listado de referencia. tipo_dato: cierre | nav | retrasado | tiempo_real | sintetico
CREATE TABLE IF NOT EXISTS precios (
    instrumento_id TEXT NOT NULL REFERENCES instrumentos(id), fecha TEXT NOT NULL,
    cierre REAL NOT NULL, cierre_ajustado REAL, volumen REAL, moneda TEXT NOT NULL,
    proveedor TEXT NOT NULL, tipo_dato TEXT NOT NULL, hora_cotizacion TEXT, obtenido_en TEXT NOT NULL,
    PRIMARY KEY (instrumento_id, fecha, proveedor)
);
CREATE INDEX IF NOT EXISTS ix_precios_fecha ON precios(instrumento_id, fecha);

CREATE TABLE IF NOT EXISTS eventos_corporativos (
    instrumento_id TEXT NOT NULL, fecha TEXT NOT NULL, tipo TEXT NOT NULL CHECK (tipo IN ('dividendo','split')),
    valor REAL NOT NULL, proveedor TEXT NOT NULL, PRIMARY KEY (instrumento_id, fecha, tipo, proveedor)
);

CREATE TABLE IF NOT EXISTS fx (
    par TEXT NOT NULL, fecha TEXT NOT NULL, valor REAL NOT NULL, proveedor TEXT NOT NULL,
    tipo_dato TEXT NOT NULL, obtenido_en TEXT NOT NULL, PRIMARY KEY (par, fecha, proveedor)
);

CREATE TABLE IF NOT EXISTS ingestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, proveedor TEXT NOT NULL, inicio TEXT NOT NULL, fin TEXT,
    estado TEXT NOT NULL, registros INTEGER DEFAULT 0, mensaje TEXT
);

CREATE TABLE IF NOT EXISTS uso_proveedor (
    proveedor TEXT NOT NULL, ventana TEXT NOT NULL, peticiones INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (proveedor, ventana)
);

-- Libro de operaciones del inversionista. Nunca se borra: se anula o se corrige con auditoría.
CREATE TABLE IF NOT EXISTS transacciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('aportacion','retiro','compra','venta','dividendo','comision','impuesto','split')),
    instrumento_id TEXT,
    cantidad REAL NOT NULL DEFAULT 0,
    precio REAL NOT NULL DEFAULT 0,
    monto REAL NOT NULL DEFAULT 0,
    comision REAL NOT NULL DEFAULT 0,
    impuesto REAL NOT NULL DEFAULT 0,
    moneda TEXT NOT NULL DEFAULT 'MXN',
    tipo_cambio REAL NOT NULL DEFAULT 1,
    nota TEXT,
    origen TEXT NOT NULL,
    huella TEXT NOT NULL UNIQUE,
    anulada INTEGER NOT NULL DEFAULT 0,
    reemplaza_id INTEGER REFERENCES transacciones(id),
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, entidad TEXT NOT NULL, entidad_id TEXT,
    accion TEXT NOT NULL, antes TEXT, despues TEXT, motivo TEXT
);

CREATE TABLE IF NOT EXISTS importaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, archivo TEXT NOT NULL, sha256 TEXT NOT NULL,
    tipo TEXT NOT NULL, filas INTEGER, aceptadas INTEGER, duplicadas INTEGER, rechazadas INTEGER,
    contenido_original BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS ajustes_usuario (clave TEXT PRIMARY KEY, valor TEXT NOT NULL, actualizado_en TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS propuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, creado_en TEXT NOT NULL,
    parametros TEXT NOT NULL, resultado TEXT NOT NULL
);
"""


def ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ruta_db() -> Path:
    d = config.data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "terminal.db"


def conectar(ruta: Path | str | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(str(ruta or ruta_db()), check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


@contextmanager
def transaccion(con: sqlite3.Connection):
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise


def inicializar(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA)
    cargar_universo(con)


def cargar_universo(con: sqlite3.Connection, ruta: Path | None = None) -> int:
    ruta = ruta or CONFIG_DIR / "universo.csv"
    filas = list(csv.DictReader(ruta.open(encoding="utf-8")))
    cols = ["id", "clave", "serie", "clave_operable", "nombre", "clase", "categoria", "pais", "mercado_operable",
            "moneda_operable", "zona_horaria_operable", "listado_referencia", "moneda_referencia", "bolsa_referencia",
            "zona_horaria_referencia", "estado", "secciones_pdf", "fuente_verificacion", "detalle_verificacion",
            "fecha_verificacion"]
    sql = (f"INSERT INTO instrumentos ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
           f"ON CONFLICT(id) DO UPDATE SET {','.join(f'{c}=excluded.{c}' for c in cols[1:])}")
    with transaccion(con):
        con.executemany(sql, [[f.get(c, "") for c in cols] for f in filas])
    return len(filas)


def auditar(con: sqlite3.Connection, entidad: str, entidad_id, accion: str, antes=None, despues=None,
            motivo: str | None = None) -> None:
    con.execute(
        "INSERT INTO auditoria (ts, entidad, entidad_id, accion, antes, despues, motivo) VALUES (?,?,?,?,?,?,?)",
        (ahora(), entidad, str(entidad_id) if entidad_id is not None else None, accion,
         json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
         json.dumps(despues, ensure_ascii=False, default=str) if despues is not None else None, motivo),
    )
