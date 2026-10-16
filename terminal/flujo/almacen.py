"""Tablas de flujo (separadas de `precios`): barras OHLCV, libro, operaciones y opciones, con procedencia completa.

`disponible_desde` = hora en que la terminal conoció el dato. Las consultas aceptan `hasta` para reproducir lo que se
sabía en una fecha (sin fuga de información futura en pruebas históricas).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from .contratos import Barra, ContratoOpcion, Libro, Operacion, Procedencia

PROC = ("fuente TEXT NOT NULL, licencia TEXT NOT NULL, mercado TEXT NOT NULL, feed TEXT NOT NULL DEFAULT '', "
        "calidad TEXT NOT NULL CHECK (calidad IN ('proveedor','importado','calculado','sintetico')), "
        "retraso_s REAL, nota TEXT NOT NULL DEFAULT '', capturado_en TEXT NOT NULL, disponible_desde TEXT NOT NULL")


def inicializar(con: sqlite3.Connection) -> None:
    con.executescript(f"""
    CREATE TABLE IF NOT EXISTS flujo_barras (
      id INTEGER PRIMARY KEY, simbolo TEXT NOT NULL, intervalo TEXT NOT NULL, inicio TEXT NOT NULL,
      apertura REAL NOT NULL, maximo REAL NOT NULL, minimo REAL NOT NULL, cierre REAL NOT NULL, volumen REAL, vwap REAL,
      {PROC}, UNIQUE (simbolo, intervalo, inicio, fuente, feed));
    CREATE INDEX IF NOT EXISTS ix_flujo_barras ON flujo_barras (simbolo, intervalo, inicio);
    CREATE TABLE IF NOT EXISTS flujo_libro (
      id INTEGER PRIMARY KEY, simbolo TEXT NOT NULL, instante TEXT NOT NULL, {PROC},
      UNIQUE (simbolo, instante, fuente));
    CREATE TABLE IF NOT EXISTS flujo_libro_niveles (
      libro_id INTEGER NOT NULL REFERENCES flujo_libro(id) ON DELETE CASCADE,
      lado TEXT NOT NULL CHECK (lado IN ('bid','ask')), nivel INTEGER NOT NULL, precio REAL NOT NULL, tamano REAL NOT NULL,
      PRIMARY KEY (libro_id, lado, nivel));
    CREATE TABLE IF NOT EXISTS flujo_operaciones (
      id INTEGER PRIMARY KEY, simbolo TEXT NOT NULL, instante TEXT NOT NULL, precio REAL NOT NULL, tamano REAL NOT NULL,
      lado TEXT CHECK (lado IS NULL OR lado IN ('compra','venta')), id_origen TEXT NOT NULL DEFAULT '', {PROC},
      UNIQUE (simbolo, fuente, id_origen, instante, precio, tamano));
    CREATE INDEX IF NOT EXISTS ix_flujo_operaciones ON flujo_operaciones (simbolo, instante);
    CREATE TABLE IF NOT EXISTS flujo_opciones (
      id INTEGER PRIMARY KEY, contrato TEXT NOT NULL, subyacente TEXT NOT NULL, vencimiento TEXT NOT NULL,
      strike REAL NOT NULL, tipo TEXT NOT NULL CHECK (tipo IN ('call','put')), instante TEXT NOT NULL,
      bid REAL, ask REAL, ultimo REAL, volumen REAL, interes_abierto REAL, iv REAL, delta REAL, gamma REAL, theta REAL,
      vega REAL, origen_iv TEXT, multiplicador REAL, spot REAL, moneda TEXT, {PROC}, UNIQUE (contrato, fuente, instante));
    CREATE INDEX IF NOT EXISTS ix_flujo_opciones ON flujo_opciones (subyacente, vencimiento, strike);
    CREATE TABLE IF NOT EXISTS flujo_consultas (
      clave TEXT PRIMARY KEY, intento_en TEXT NOT NULL, estado TEXT NOT NULL, registros INTEGER NOT NULL DEFAULT 0,
      mensaje TEXT NOT NULL DEFAULT '');
    """)
    columnas = {r[1] for r in con.execute("PRAGMA table_info(flujo_opciones)")}  # bases anteriores a GEX
    for c, t in (("multiplicador", "REAL"), ("spot", "REAL"), ("moneda", "TEXT")):
        if c not in columnas:
            con.execute(f"ALTER TABLE flujo_opciones ADD COLUMN {c} {t}")


def _p(p: Procedencia) -> tuple:
    return (p.fuente, p.licencia, p.mercado, p.feed, p.calidad, p.retraso_s, p.nota, p.capturado_en,
            datetime.now(UTC).isoformat())


COLS_P = "fuente, licencia, mercado, feed, calidad, retraso_s, nota, capturado_en, disponible_desde"


def guardar_barras(con, barras: list[Barra], p: Procedencia) -> int:
    filas = []
    for b in barras:
        b.validar()
        filas.append((b.simbolo, b.intervalo, b.inicio, b.apertura, b.maximo, b.minimo, b.cierre, b.volumen, b.vwap, *_p(p)))
    con.executemany(f"INSERT OR REPLACE INTO flujo_barras (simbolo, intervalo, inicio, apertura, maximo, minimo, cierre, "
                    f"volumen, vwap, {COLS_P}) VALUES ({','.join('?' * 18)})", filas)
    return len(filas)


def guardar_libro(con, libro: Libro, p: Procedencia) -> int:
    libro.validar()
    con.execute("DELETE FROM flujo_libro WHERE simbolo=? AND instante=? AND fuente=?", (libro.simbolo, libro.instante, p.fuente))
    cur = con.execute(f"INSERT INTO flujo_libro (simbolo, instante, {COLS_P}) VALUES ({','.join('?' * 11)})",
                      (libro.simbolo, libro.instante, *_p(p)))
    con.executemany("INSERT INTO flujo_libro_niveles VALUES (?,?,?,?,?)",
                    [(cur.lastrowid, n.lado, n.nivel, n.precio, n.tamano) for n in libro.niveles])
    return len(libro.niveles)


def guardar_operaciones(con, ops: list[Operacion], p: Procedencia) -> int:
    antes = con.total_changes
    con.executemany(f"INSERT OR IGNORE INTO flujo_operaciones (simbolo, instante, precio, tamano, lado, id_origen, {COLS_P}) "
                    f"VALUES ({','.join('?' * 15)})",
                    [(o.simbolo, o.instante, o.precio, o.tamano, o.lado, o.id_origen, *_p(p)) for o in ops])
    return con.total_changes - antes


def guardar_opciones(con, contratos: list[ContratoOpcion], p: Procedencia) -> int:
    con.executemany(f"INSERT OR REPLACE INTO flujo_opciones (contrato, subyacente, vencimiento, strike, tipo, instante, bid, "
                    f"ask, ultimo, volumen, interes_abierto, iv, delta, gamma, theta, vega, origen_iv, multiplicador, spot, "
                    f"moneda, {COLS_P}) VALUES ({','.join('?' * 29)})",
                    [(c.contrato, c.subyacente, c.vencimiento, c.strike, c.tipo, c.instante, c.bid, c.ask, c.ultimo,
                      c.volumen, c.interes_abierto, c.iv, c.delta, c.gamma, c.theta, c.vega, c.origen_iv, c.multiplicador,
                      c.spot, c.moneda, *_p(p))
                     for c in contratos])
    return len(contratos)


def _filtro_calidad(demo: bool) -> str:
    # En modo real nunca aparece lo sintético; en demostración solo lo sintético y lo importado.
    return "calidad = 'sintetico' OR calidad = 'importado'" if demo else "calidad <> 'sintetico'"


def barras(con, simbolo: str, intervalo: str, desde: str | None = None, hasta: str | None = None,
           demo: bool = False, limite: int = 2000) -> list[dict]:
    """Una barra por inicio. Con varias fuentes gana la del proveedor sobre la importada, y entre iguales la de captura
    más reciente."""
    corte = hasta or datetime.now(UTC).isoformat()
    filas = con.execute(f"""
      SELECT * FROM (SELECT b.*, ROW_NUMBER() OVER (PARTITION BY inicio ORDER BY
                CASE calidad WHEN 'proveedor' THEN 0 WHEN 'importado' THEN 1 ELSE 2 END, capturado_en DESC) AS r
              FROM flujo_barras b WHERE simbolo=? AND intervalo=? AND inicio >= ? AND disponible_desde <= ?
              AND ({_filtro_calidad(demo)}))
      WHERE r=1 ORDER BY inicio DESC LIMIT ?""", (simbolo, intervalo, desde or "", corte, limite)).fetchall()
    return [dict(f) for f in reversed(filas)]


def historia_libro(con, simbolo: str, desde: str, demo: bool = False) -> list[dict]:
    corte = datetime.now(UTC).isoformat()
    filas = con.execute(f"SELECT * FROM flujo_libro WHERE simbolo=? AND instante>=? AND disponible_desde<=? "
                        f"AND ({_filtro_calidad(demo)}) ORDER BY instante DESC, id DESC LIMIT 60",
                        (simbolo, desde, corte)).fetchall()
    if not filas:
        return []
    ids = [f["id"] for f in filas]
    niveles = con.execute(f"SELECT * FROM flujo_libro_niveles WHERE libro_id IN ({','.join('?' for _ in ids)}) "
                          "ORDER BY libro_id,lado,nivel", ids).fetchall()
    por_id = {i: [] for i in ids}
    for n in niveles:
        por_id[n["libro_id"]].append(dict(n))
    return [{**dict(f), "niveles": por_id[f["id"]]} for f in reversed(filas)]


def ultimo_libro(con, simbolo: str, demo: bool = False, hasta: str | None = None) -> dict | None:
    corte = hasta or datetime.now(UTC).isoformat()
    f = con.execute(f"SELECT * FROM flujo_libro WHERE simbolo=? AND disponible_desde <= ? AND ({_filtro_calidad(demo)}) "
                    "ORDER BY instante DESC, id DESC LIMIT 1", (simbolo, corte)).fetchone()
    if not f:
        return None
    d = dict(f)
    d["niveles"] = [dict(n) for n in con.execute("SELECT lado, nivel, precio, tamano FROM flujo_libro_niveles "
                                                 "WHERE libro_id=? ORDER BY lado, nivel", (f["id"],))]
    return d


def operaciones(con, simbolo: str, desde: str | None = None, demo: bool = False, limite: int = 5000,
                hasta: str | None = None) -> list[dict]:
    corte = hasta or datetime.now(UTC).isoformat()
    filas = con.execute(f"SELECT * FROM flujo_operaciones WHERE simbolo=? AND instante >= ? AND disponible_desde <= ? "
                        f"AND ({_filtro_calidad(demo)}) ORDER BY instante DESC, id DESC LIMIT ?",
                        (simbolo, desde or "", corte, limite)).fetchall()
    return [dict(f) for f in reversed(filas)]


def cadena(con, subyacente: str, demo: bool = False, hasta: str | None = None) -> list[dict]:
    """Última cotización conocida de cada contrato del subyacente."""
    corte = hasta or datetime.now(UTC).isoformat()
    filas = con.execute(f"""
      SELECT * FROM (SELECT o.*, ROW_NUMBER() OVER (PARTITION BY contrato ORDER BY instante DESC, id DESC) AS r
              FROM flujo_opciones o WHERE subyacente=? AND disponible_desde <= ? AND ({_filtro_calidad(demo)}))
      WHERE r=1 ORDER BY vencimiento, strike, tipo""", (subyacente, corte)).fetchall()
    return [dict(f) for f in filas]


def simbolos(con, tabla: str) -> list[str]:
    assert tabla in ("flujo_barras", "flujo_libro", "flujo_operaciones", "flujo_opciones")
    col = "subyacente" if tabla == "flujo_opciones" else "simbolo"
    return [r[0] for r in con.execute(f"SELECT DISTINCT {col} FROM {tabla} ORDER BY 1")]


def registrar_consulta(con, clave: str, estado: str, registros: int, mensaje: str) -> None:
    con.execute("INSERT INTO flujo_consultas VALUES (?,?,?,?,?) ON CONFLICT(clave) DO UPDATE SET intento_en=excluded.intento_en, "
                "estado=excluded.estado, registros=excluded.registros, mensaje=excluded.mensaje",
                (clave, datetime.now(UTC).isoformat(), estado, registros, mensaje[:300]))


def ultima_consulta(con, clave: str) -> dict | None:
    f = con.execute("SELECT * FROM flujo_consultas WHERE clave=?", (clave,)).fetchone()
    return dict(f) if f else None
