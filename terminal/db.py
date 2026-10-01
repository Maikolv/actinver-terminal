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

-- Lista de instrumentos exportada del simulador del Reto (si se importa, restringe el universo).
CREATE TABLE IF NOT EXISTS universo_simulador (id TEXT PRIMARY KEY, clave_operable TEXT, importado_en TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS tareas_reto (id TEXT PRIMARY KEY, hecha INTEGER NOT NULL DEFAULT 0, actualizado_en TEXT NOT NULL);

-- Alertas: cada disparo queda registrado; el estado por regla/clave implementa histéresis y enfriamiento.
CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, regla TEXT NOT NULL, clave TEXT NOT NULL,
    severidad TEXT NOT NULL CHECK (severidad IN ('info','aviso','critica')), titulo TEXT NOT NULL, motivo TEXT NOT NULL,
    datos TEXT, fuente TEXT, accion TEXT, simulacion TEXT, estado TEXT NOT NULL DEFAULT 'nueva',
    notificada TEXT
);
CREATE INDEX IF NOT EXISTS ix_alertas_ts ON alertas(ts);
CREATE TABLE IF NOT EXISTS estado_alertas (
    regla TEXT NOT NULL, clave TEXT NOT NULL, activa INTEGER NOT NULL DEFAULT 0, ultimo_disparo TEXT,
    PRIMARY KEY (regla, clave)
);

CREATE TABLE IF NOT EXISTS noticias (
    id TEXT PRIMARY KEY, instrumento_id TEXT, titulo TEXT NOT NULL, enlace TEXT, publicado TEXT, fuente TEXT NOT NULL,
    impacto TEXT, sentimiento REAL, motivo TEXT, obtenido_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eventos_macro (
    id TEXT PRIMARY KEY, fecha TEXT NOT NULL, pais TEXT, titulo TEXT NOT NULL, impacto TEXT, pronostico TEXT,
    previo TEXT, fuente TEXT NOT NULL, obtenido_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS insiders (
    id TEXT PRIMARY KEY, instrumento_id TEXT NOT NULL, fecha TEXT NOT NULL, nombre TEXT, cargo TEXT, codigo TEXT,
    acciones REAL, precio REAL, valor REAL, enlace TEXT, fuente TEXT NOT NULL, obtenido_en TEXT NOT NULL
);

-- Registro de cotizaciones por proveedor (PRESENTE). Nunca se mezcla con pronósticos.
-- estado_latencia: REAL_TIME | DELAYED | EOD | UNKNOWN, calculado con la latencia MEDIDA, no con la publicidad.
CREATE TABLE IF NOT EXISTS cotizaciones_registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT, proveedor TEXT NOT NULL, simbolo_origen TEXT NOT NULL,
    simbolo_normalizado TEXT NOT NULL, instrumento_id TEXT, mercado TEXT NOT NULL, bolsa TEXT, precio REAL NOT NULL,
    moneda TEXT NOT NULL, hora_evento TEXT NOT NULL, hora_recepcion TEXT NOT NULL, latencia_declarada_s REAL,
    latencia_medida_s REAL, estado_latencia TEXT NOT NULL CHECK (estado_latencia IN ('REAL_TIME','DELAYED','EOD','UNKNOWN')),
    sintetico INTEGER NOT NULL DEFAULT 0, detalle TEXT
);
CREATE INDEX IF NOT EXISTS ix_cotreg ON cotizaciones_registro(instrumento_id, hora_recepcion);

-- Cobertura verificada por proveedor e instrumento del catálogo (serie, moneda y mercado exactos).
CREATE TABLE IF NOT EXISTS cobertura (
    proveedor TEXT NOT NULL, instrumento_id TEXT NOT NULL, simbolo_origen TEXT, estado TEXT NOT NULL,
    moneda_observada TEXT, bolsa_observada TEXT, mercado_observado TEXT, latencia_mediana_s REAL,
    estado_latencia TEXT, detalle TEXT, verificado_en TEXT NOT NULL, PRIMARY KEY (proveedor, instrumento_id)
);

CREATE TABLE IF NOT EXISTS metricas_proveedor (
    proveedor TEXT PRIMARY KEY, solicitudes INTEGER NOT NULL DEFAULT 0, fallos INTEGER NOT NULL DEFAULT 0,
    fallos_consecutivos INTEGER NOT NULL DEFAULT 0, ultimo_exito TEXT, ultimo_fallo TEXT, ultimo_error TEXT
);

-- Eventos recibidos por webhook de TradingView (alertas voluntarias del usuario, no un flujo de precios).
CREATE TABLE IF NOT EXISTS eventos_webhook (
    id INTEGER PRIMARY KEY AUTOINCREMENT, huella TEXT NOT NULL UNIQUE, recibido_en TEXT NOT NULL, simbolo_origen TEXT,
    instrumento_id TEXT, precio REAL, moneda TEXT, hora_evento TEXT, alerta TEXT, estado TEXT NOT NULL, motivo TEXT
);

-- Saldo que muestra el portal de Actinver, capturado a mano por el participante (fuente oficial).
CREATE TABLE IF NOT EXISTS saldos_portal (
    id INTEGER PRIMARY KEY AUTOINCREMENT, capturado_en TEXT NOT NULL, hora_portal TEXT NOT NULL, etapa TEXT,
    valor_portafolio REAL NOT NULL, efectivo REAL, nota TEXT, invertido REAL, por_liquidar REAL
);

-- FUTURO: pronósticos emitidos. Inmutables salvo el resultado observado, que se añade al conocerse.
CREATE TABLE IF NOT EXISTS pronosticos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, emitido_en TEXT NOT NULL, datos_hasta TEXT NOT NULL, instrumento_id TEXT NOT NULL,
    horizonte INTEGER NOT NULL, fecha_base TEXT NOT NULL, fecha_objetivo TEXT, modelo TEXT NOT NULL, version TEXT NOT NULL,
    semilla INTEGER, prediccion REAL NOT NULL, p10 REAL, p90 REAL, prob_subida REAL, recomendacion_permitida INTEGER NOT NULL,
    resultado REAL, resuelto_en TEXT, UNIQUE (emitido_en, instrumento_id, horizonte, modelo)
);

-- Registro de experimentos: versión, semilla, cortes temporales y resultados; marca si la prueba final ya se usó.
CREATE TABLE IF NOT EXISTS experimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, configuracion TEXT NOT NULL, huella_config TEXT NOT NULL,
    huella_datos TEXT NOT NULL, semilla INTEGER NOT NULL, cortes TEXT NOT NULL, resultados TEXT NOT NULL,
    prueba_ya_vista INTEGER NOT NULL DEFAULT 0, version_codigo TEXT
);

-- Calificaciones de terceros importadas por el participante (p. ej. exportación de Seeking Alpha Premium). Contexto:
-- se muestran en el Ranking con su fecha; no entran al optimizador (no hay historia sin sesgo de anticipación).
CREATE TABLE IF NOT EXISTS calificaciones (
    id TEXT PRIMARY KEY, instrumento_id TEXT NOT NULL, fecha TEXT NOT NULL, fuente TEXT NOT NULL,
    quant REAL, autores REAL, wall_street REAL, valuacion TEXT, crecimiento TEXT, rentabilidad TEXT, momentum TEXT,
    revisiones TEXT, importado_en TEXT NOT NULL
);

-- Capturas del portal del Reto que el participante copia y pega (la terminal no entra al portal, reglamento §17).
CREATE TABLE IF NOT EXISTS capturas_portal (
    id INTEGER PRIMARY KEY AUTOINCREMENT, capturado_en TEXT NOT NULL, hora_portal TEXT NOT NULL, etapa TEXT,
    valor_portafolio REAL NOT NULL, efectivo REAL, fuente TEXT NOT NULL, n_posiciones INTEGER NOT NULL DEFAULT 0,
    tabla_reconocida INTEGER NOT NULL DEFAULT 0, saldo_id INTEGER, huella TEXT NOT NULL UNIQUE, por_liquidar REAL,
    invertido REAL
);
CREATE TABLE IF NOT EXISTS posiciones_portal (
    id INTEGER PRIMARY KEY AUTOINCREMENT, captura_id INTEGER NOT NULL REFERENCES capturas_portal(id),
    instrumento_id TEXT NOT NULL, texto TEXT, titulos REAL NOT NULL, costo_promedio REAL, precio REAL, valor REAL
);

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


def respaldar(origen: Path | None = None, conservar: int = 14) -> Path:
    """Copia consistente (API de respaldo de SQLite) con verificación de integridad; conserva las `conservar` más recientes."""
    import time
    origen = Path(origen or ruta_db())
    destino_dir = origen.parent / "respaldos"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"terminal-{time.strftime('%Y%m%d-%H%M%S')}-{time.perf_counter_ns() % 1000000:06d}.db"
    src, dst = sqlite3.connect(origen), sqlite3.connect(destino)
    try:
        with dst:
            src.backup(dst)
        ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        src.close()
        dst.close()
    if ok != "ok":
        destino.unlink(missing_ok=True)
        raise RuntimeError(f"Respaldo inválido ({ok}); no se conservó")
    copias = sorted(destino_dir.glob("terminal-*.db"))
    for viejo in copias[: max(len(copias) - conservar, 0)]:
        viejo.unlink()
    return destino


def respaldo_diario(origen: Path | None = None, conservar: int = 14, horas: float = 20) -> Path | None:
    """Un respaldo verificado si el último tiene más de `horas`; lo llama el motor en cada ciclo."""
    import time
    origen = Path(origen or ruta_db())
    copias = sorted((origen.parent / "respaldos").glob("terminal-*.db"), key=lambda p: p.stat().st_mtime)
    if copias and time.time() - copias[-1].stat().st_mtime < horas * 3600:
        return None
    return respaldar(origen, conservar)


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


def inicializar(con: sqlite3.Connection, ajustes=None) -> None:
    con.executescript(ESQUEMA)
    cargar_universo(con)
    from . import migraciones, registro
    migraciones.migrar(con, ajustes)
    registro.inicializar(con)


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
