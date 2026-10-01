"""Entidades de registro: versiones de reglas, órdenes pendientes (referencia), bitácora de decisiones,
correspondencia de símbolos, licencias de fuentes e instantáneas.

- Una orden PENDIENTE nunca cambia posiciones ni efectivo: solo una operación CONFIRMADA (tabla transacciones) lo hace.
- Las reglas del Reto se versionan por huella de `config/reto.yaml`. Si el archivo cambia, se abre una versión nueva
  y se muestra un aviso de discrepancia hasta que el usuario lo revise. Los cálculos guardados conservan la versión
  con la que se hicieron: no se recalculan en silencio.
- La bitácora registra tesis, decisión HUMANA y resultado (adoptado de LuxAlgo/trade-journal). No ejecuta nada.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

from .config import CONFIG_DIR

ESQUEMA = """
CREATE TABLE IF NOT EXISTS versiones_reglas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, huella TEXT NOT NULL UNIQUE, detectada_en TEXT NOT NULL, contenido TEXT NOT NULL,
    fuente TEXT, consultado TEXT, revisada INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ordenes_pendientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, creada_en TEXT NOT NULL, instrumento_id TEXT NOT NULL, lado TEXT NOT NULL
    CHECK (lado IN ('compra','venta')), tipo_orden TEXT NOT NULL CHECK (tipo_orden IN ('mercado','limitada')),
    cantidad REAL NOT NULL, precio_limite REAL, estado TEXT NOT NULL DEFAULT 'pendiente'
    CHECK (estado IN ('enviada','pendiente','ejecutada','cancelada','expirada')), transaccion_id INTEGER, nota TEXT,
    ingested_at TEXT NOT NULL, folio TEXT, boleta_id INTEGER
);
-- Boleta de decisión: propuesta completa para que el PARTICIPANTE capture la orden a mano. No es una orden.
CREATE TABLE IF NOT EXISTS boletas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, creada_en TEXT NOT NULL, caduca_en TEXT NOT NULL, instrumento_id TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('mantener','investigar','considerar compra','considerar venta','considerar rebalanceo')),
    estado TEXT NOT NULL DEFAULT 'vigente' CHECK (estado IN ('vigente','invalidada','caducada','descartada','marcada_ejecutada')),
    contenido TEXT NOT NULL, huella_datos TEXT NOT NULL, motivo_estado TEXT, folio TEXT, marcada_en TEXT, transaccion_id INTEGER
);
CREATE TABLE IF NOT EXISTS bitacora_decisiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, creada_en TEXT NOT NULL, instrumento_id TEXT, tipo TEXT NOT NULL
    CHECK (tipo IN ('tesis','entrada','salida','revision','error','leccion')), tesis TEXT, decision_humana TEXT NOT NULL,
    fuentes TEXT, alerta_id INTEGER, transaccion_id INTEGER, version_reglas INTEGER, version_modelo TEXT, resultado TEXT
);
CREATE TABLE IF NOT EXISTS correspondencia_simbolos (
    instrumento_id TEXT PRIMARY KEY, simbolo_actinver TEXT, emisor TEXT, serie TEXT, isin TEXT, mic TEXT NOT NULL,
    mercado TEXT NOT NULL, moneda TEXT NOT NULL, simbolo_bmv TEXT, simbolo_origen TEXT, mic_origen TEXT, moneda_origen TEXT,
    elegible TEXT NOT NULL, actualizado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS licencias_fuente (
    fuente TEXT PRIMARY KEY, url TEXT NOT NULL, modalidad TEXT NOT NULL, licencia TEXT NOT NULL, cobertura TEXT,
    latencia TEXT, estado TEXT NOT NULL, revisado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots_cartera (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_time TEXT NOT NULL, available_at TEXT NOT NULL, ingested_at TEXT NOT NULL,
    etapa TEXT, valor_estimado REAL, efectivo REAL, posiciones TEXT NOT NULL, version_reglas INTEGER, calidad TEXT
);
CREATE TABLE IF NOT EXISTS versiones_modelo (
    version TEXT PRIMARY KEY, creada_en TEXT NOT NULL, configuracion TEXT NOT NULL, semilla INTEGER, experimento_id INTEGER,
    supera_referencias INTEGER, notas TEXT
);
"""

MIC = {"BMV": "XMEX", "BMV-SIC": "XMEX", "NYSE": "XNYS", "NASDAQ": "XNAS", "NYSE ARCA": "ARCX", "NYSE American": "XASE",
       "Fondos Actinver": "OTC-FONDO"}


def ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _migrar_ordenes(con: sqlite3.Connection) -> None:
    """Versiones previas no tenían el estado «enviada», folio ni boleta: se reconstruye la tabla conservando filas."""
    f = con.execute("SELECT sql FROM sqlite_master WHERE name='ordenes_pendientes'").fetchone()
    if f and "'enviada'" not in f[0]:
        con.execute("ALTER TABLE ordenes_pendientes RENAME TO ordenes_pendientes_v1")
        con.executescript(ESQUEMA)
        con.execute("INSERT INTO ordenes_pendientes (id, creada_en, instrumento_id, lado, tipo_orden, cantidad, precio_limite, "
                    "estado, transaccion_id, nota, ingested_at) SELECT id, creada_en, instrumento_id, lado, tipo_orden, cantidad, "
                    "precio_limite, estado, transaccion_id, nota, ingested_at FROM ordenes_pendientes_v1")
        con.execute("DROP TABLE ordenes_pendientes_v1")
        con.commit()
    cols = {r[1] for r in con.execute("PRAGMA table_info(bitacora_decisiones)")}
    if not cols:
        return
    for c, t in (("nivel_invalidacion", "REAL"), ("direccion_invalidacion", "TEXT")):
        if c not in cols:
            con.execute(f"ALTER TABLE bitacora_decisiones ADD COLUMN {c} {t}")  # noqa: S608 (nombres fijos)


def inicializar(con: sqlite3.Connection) -> None:
    _migrar_ordenes(con)
    con.executescript(ESQUEMA)
    _migrar_ordenes(con)
    registrar_version_reglas(con)
    poblar_correspondencia(con)


# --- reglas versionadas ---------------------------------------------------------------------------------------------
def registrar_version_reglas(con: sqlite3.Connection) -> dict:
    ruta = CONFIG_DIR / "reto.yaml"
    if not ruta.exists():
        return {}
    texto = ruta.read_text(encoding="utf-8")
    huella = hashlib.sha256(texto.encode()).hexdigest()
    f = con.execute("SELECT id FROM versiones_reglas WHERE huella=?", (huella,)).fetchone()
    if not f:
        import yaml
        c = yaml.safe_load(texto) or {}
        primera = con.execute("SELECT COUNT(*) FROM versiones_reglas").fetchone()[0] == 0
        con.execute("INSERT INTO versiones_reglas (huella, detectada_en, contenido, fuente, consultado, revisada) VALUES (?,?,?,?,?,?)",
                    (huella, ahora(), texto, c.get("fuente"), str(c.get("consultado")), int(primera)))
        con.commit()
    return estado_reglas(con)


def estado_reglas(con: sqlite3.Connection) -> dict:
    filas = [dict(r) for r in con.execute("SELECT id, huella, detectada_en, fuente, consultado, revisada FROM versiones_reglas "
                                          "ORDER BY id")]
    if not filas:
        return {"version": None, "historial": [], "discrepancia": False}
    actual = filas[-1]
    return {"version": actual["id"], "huella": actual["huella"][:12], "consultado": actual["consultado"],
            "historial": [{k: v for k, v in f.items() if k != "huella"} | {"huella": f["huella"][:12]} for f in filas],
            "discrepancia": not actual["revisada"],
            "aviso": None if actual["revisada"] else
            "Las reglas del Reto cambiaron respecto a la versión anterior. Revise config/reto.yaml contra las bases oficiales; "
            "los cálculos guardados conservan la versión con que se hicieron."}


def marcar_reglas_revisadas(con: sqlite3.Connection, version: int) -> None:
    con.execute("UPDATE versiones_reglas SET revisada=1 WHERE id=?", (version,))
    con.commit()


# --- órdenes pendientes: solo referencia -----------------------------------------------------------------------------
def registrar_orden_pendiente(con, instrumento_id: str, lado: str, tipo_orden: str, cantidad: float,
                              precio_limite: float | None = None, nota: str = "") -> int:
    if lado not in ("compra", "venta") or tipo_orden not in ("mercado", "limitada") or not cantidad or cantidad <= 0:
        raise ValueError("orden pendiente inválida")
    cur = con.execute("INSERT INTO ordenes_pendientes (creada_en, instrumento_id, lado, tipo_orden, cantidad, precio_limite, "
                      "nota, ingested_at) VALUES (?,?,?,?,?,?,?,?)",
                      (ahora(), instrumento_id, lado, tipo_orden, float(cantidad), precio_limite, nota[:200], ahora()))
    con.commit()
    return cur.lastrowid


def cerrar_orden(con, oid: int, estado: str, transaccion_id: int | None = None) -> None:
    """Marca la referencia como ejecutada/cancelada/expirada. La tenencia solo cambia si el usuario registra la
    operación CONFIRMADA en «Mi portafolio Actinver»; aquí únicamente se enlaza su id."""
    if estado not in ("enviada", "pendiente", "ejecutada", "cancelada", "expirada"):
        raise ValueError("estado inválido")
    if estado == "ejecutada" and not transaccion_id:
        raise ValueError("una orden solo es «ejecutada» con la operación CONFIRMADA registrada (transaccion_id)")
    con.execute("UPDATE ordenes_pendientes SET estado=?, transaccion_id=? WHERE id=?", (estado, transaccion_id, oid))
    con.commit()


def ordenes(con, solo_pendientes: bool = True) -> list[dict]:
    q = "SELECT * FROM ordenes_pendientes" + (" WHERE estado IN ('enviada','pendiente')" if solo_pendientes else "") + " ORDER BY id DESC"
    return [dict(r) for r in con.execute(q)]


# --- bitácora de decisiones ------------------------------------------------------------------------------------------
def registrar_decision(con, tipo: str, decision_humana: str, instrumento_id: str | None = None, tesis: str = "",
                       fuentes: list[str] | None = None, alerta_id: int | None = None, transaccion_id: int | None = None,
                       resultado: str = "", nivel_invalidacion: float | None = None,
                       direccion_invalidacion: str | None = None) -> int:
    if direccion_invalidacion not in (None, "debajo", "arriba"):
        raise ValueError("direccion_invalidacion: debajo o arriba")
    if not decision_humana.strip():
        raise ValueError("decision_humana: obligatoria (la decisión es del participante)")
    ver = estado_reglas(con).get("version")
    modelo = con.execute("SELECT version FROM versiones_modelo ORDER BY creada_en DESC LIMIT 1").fetchone()
    cur = con.execute("INSERT INTO bitacora_decisiones (creada_en, instrumento_id, tipo, tesis, decision_humana, fuentes, "
                      "alerta_id, transaccion_id, version_reglas, version_modelo, resultado) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (ahora(), instrumento_id, tipo, tesis[:2000], decision_humana[:1000],
                       json.dumps(fuentes or [], ensure_ascii=False), alerta_id, transaccion_id, ver,
                       modelo[0] if modelo else None, resultado[:1000]))
    if nivel_invalidacion is not None:
        con.execute("UPDATE bitacora_decisiones SET nivel_invalidacion=?, direccion_invalidacion=? WHERE id=?",
                    (float(nivel_invalidacion), direccion_invalidacion or "debajo", cur.lastrowid))
    con.commit()
    return cur.lastrowid


def bitacora(con, limite: int = 200) -> list[dict]:
    out = []
    for r in con.execute("SELECT * FROM bitacora_decisiones ORDER BY id DESC LIMIT ?", (limite,)):
        d = dict(r)
        d["fuentes"] = json.loads(d["fuentes"] or "[]")
        out.append(d)
    return out


# --- correspondencia de símbolos ---------------------------------------------------------------------------------------
def elegibilidad(i: dict, en_simulador: bool | None) -> str:
    if i.get("estado") != "activo":
        return f"no elegible ({i.get('estado')})"
    if en_simulador is False:
        return "no está en el catálogo del simulador"
    if en_simulador is None:
        return "pendiente: catálogo del simulador no importado"
    return "elegible"


def poblar_correspondencia(con: sqlite3.Connection) -> int:
    sim = {r[0] for r in con.execute("SELECT id FROM universo_simulador")}
    filas = []
    for r in con.execute("SELECT * FROM instrumentos"):
        i = dict(r)
        es_sic = i["mercado_operable"] == "BMV-SIC"
        mercado = "SIC" if es_sic else ("fondo" if str(i["clase"]).startswith("fondo") else "local")
        filas.append((i["id"], i["clave_operable"], i["nombre"], i["serie"], None,
                      MIC.get(i["mercado_operable"], "desconocido"), mercado, i["moneda_operable"] or "MXN",
                      f"{i['clave']}{(i['serie'] or '').replace(' ', '')}" if mercado != "fondo" else None,
                      i["listado_referencia"] if es_sic else None, MIC.get(i["bolsa_referencia"], i["bolsa_referencia"]) if es_sic else None,
                      i["moneda_referencia"] if es_sic else None,
                      elegibilidad(i, (i["id"] in sim) if sim else None), ahora()))
    con.executemany("INSERT OR REPLACE INTO correspondencia_simbolos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", filas)
    con.commit()
    return len(filas)


# --- instantáneas --------------------------------------------------------------------------------------------------------
def guardar_snapshot_cartera(con, cartera: dict, calidad: str) -> int:
    t = ahora()
    pos = [{k: p.get(k) for k in ("instrumento_id", "cantidad", "precio_mxn", "valor_mxn", "peso", "proveedor", "vigencia")}
           for p in cartera.get("posiciones", [])]
    cur = con.execute("INSERT INTO snapshots_cartera (event_time, available_at, ingested_at, etapa, valor_estimado, efectivo, "
                      "posiciones, version_reglas, calidad) VALUES (?,?,?,?,?,?,?,?,?)",
                      (t, t, t, cartera.get("etapa"), cartera.get("valor_total"), cartera.get("efectivo"),
                       json.dumps(pos, default=str), estado_reglas(con).get("version"), calidad))
    con.commit()
    return cur.lastrowid


def registrar_version_modelo(con, version: str, configuracion: dict, semilla: int, experimento_id: int | None,
                             supera: bool, notas: str = "") -> None:
    con.execute("INSERT OR IGNORE INTO versiones_modelo VALUES (?,?,?,?,?,?,?)",
                (version, ahora(), json.dumps(configuracion, default=str), semilla, experimento_id, int(supera), notas))
    con.commit()
