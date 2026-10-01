"""Almacenamiento incremental y consultas «a una fecha» (sin conocimiento futuro) de movimientos públicos.

Identificadores estables: CIK (gestor, emisor y declarante), número de acceso de la SEC (documento) y CUSIP (13F).
Cada documento se procesa una sola vez (clave = número de acceso); cada dato conserva su procedencia (URL original).

Fechas que se distinguen siempre:
- operación (Form 4) o corte de la cartera (13F, «periodo»);
- publicación: fecha de presentación y hora de aceptación de la SEC (`aceptado_en`);
- conocimiento de la terminal: cuándo la terminal lo guardó (`obtenido_en`).
Una consulta «hasta T» solo usa documentos con `aceptado_en <= T`.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import UTC, datetime

from . import sec

ESQUEMA = """
CREATE TABLE IF NOT EXISTS mp_documentos (
    acceso TEXT PRIMARY KEY, tipo TEXT NOT NULL, cik_presentador TEXT NOT NULL, nombre_presentador TEXT,
    cik_emisor TEXT, emisor TEXT, simbolo TEXT, periodo TEXT, fecha_presentacion TEXT NOT NULL, aceptado_en TEXT NOT NULL,
    es_enmienda INTEGER NOT NULL DEFAULT 0, tipo_enmienda TEXT, fecha_original TEXT, plan_10b5_1 INTEGER,
    declarantes TEXT, url TEXT NOT NULL, url_indice TEXT, obtenido_en TEXT NOT NULL, filas INTEGER, nota TEXT
);
CREATE INDEX IF NOT EXISTS mp_doc_presentador ON mp_documentos (cik_presentador, tipo, periodo);
CREATE INDEX IF NOT EXISTS mp_doc_emisor ON mp_documentos (cik_emisor, tipo);
CREATE TABLE IF NOT EXISTS mp_13f (
    acceso TEXT NOT NULL, cusip TEXT NOT NULL, instrumento TEXT NOT NULL, emisor TEXT, clase TEXT,
    titulos REAL NOT NULL, valor_usd REAL NOT NULL, PRIMARY KEY (acceso, cusip, instrumento)
);
CREATE TABLE IF NOT EXISTS mp_form4 (
    acceso TEXT NOT NULL, tabla TEXT NOT NULL, fila INTEGER NOT NULL, titulo_valor TEXT, fecha_operacion TEXT,
    codigo TEXT, adquirido_dispuesto TEXT, titulos REAL, precio REAL, posee_despues REAL, titularidad TEXT, naturaleza TEXT,
    clasificacion TEXT NOT NULL, descripcion TEXT, discrecional INTEGER NOT NULL, plan_10b5_1 INTEGER NOT NULL,
    tras_ejercicio INTEGER NOT NULL DEFAULT 0, notas TEXT, huella TEXT NOT NULL, PRIMARY KEY (acceso, tabla, fila)
);
CREATE INDEX IF NOT EXISTS mp_f4_huella ON mp_form4 (huella);
CREATE TABLE IF NOT EXISTS mp_cusip (
    cusip TEXT PRIMARY KEY, simbolo TEXT, cik TEXT, metodo TEXT NOT NULL, ambiguo INTEGER NOT NULL DEFAULT 0,
    candidatos TEXT, actualizado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mp_fuente (
    clave TEXT PRIMARY KEY, ultimo_intento TEXT, ultimo_ok TEXT, ultimo_error TEXT, consultas INTEGER, detalle TEXT
);
CREATE TABLE IF NOT EXISTS seguimiento (instrumento_id TEXT PRIMARY KEY, agregado_en TEXT NOT NULL, nota TEXT);
"""


def asegurar(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA)


def ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def visto(con: sqlite3.Connection, acceso: str) -> bool:
    return con.execute("SELECT 1 FROM mp_documentos WHERE acceso=?", (acceso,)).fetchone() is not None


def _norm_iso(t: str | None, respaldo: str) -> str:
    """aceptado_en en ISO UTC; si falta, el final del día de presentación (conservador: nunca antes de lo publicado)."""
    if t:
        try:
            return datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(UTC).isoformat(timespec="seconds")
        except ValueError:
            pass
    return f"{respaldo}T23:59:59+00:00"


def guardar_13f(con: sqlite3.Connection, *, acceso: str, cik: str, gestor: str, fecha_presentacion: str, aceptado_en: str | None,
                portada: sec.Portada13F, filas: list[dict], url: str, url_indice: str, obtenido_en: str | None = None) -> int:
    agregadas = sec.agregar_tabla(filas, fecha_presentacion)
    _, nota = sec.escala_valor(filas, fecha_presentacion)
    tipo = "13F-HR/A" if portada.es_enmienda else "13F-HR"
    with con:
        con.execute("INSERT OR IGNORE INTO mp_documentos (acceso, tipo, cik_presentador, nombre_presentador, periodo, "
                    "fecha_presentacion, aceptado_en, es_enmienda, tipo_enmienda, url, url_indice, obtenido_en, filas, nota) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (acceso, tipo, str(int(cik)), gestor or portada.gestor, portada.periodo, fecha_presentacion,
                     _norm_iso(aceptado_en, fecha_presentacion), int(portada.es_enmienda), portada.tipo_enmienda, url,
                     url_indice, obtenido_en or ahora(), len(filas), nota))
        con.executemany("INSERT OR IGNORE INTO mp_13f VALUES (?,?,?,?,?,?,?)",
                        [(acceso, a["cusip"], a["instrumento"], a["emisor"], a["clase"], a["titulos"], a["valor_usd"])
                         for a in agregadas.values()])
    return len(agregadas)


def huella_f4(emisor_cik: str, declarantes: list[dict], t: dict) -> str:
    """Identidad de una operación para detectar duplicados entre un Form 4 y su 4/A (mismos hechos declarados)."""
    quien = ",".join(sorted(d["cik"] for d in declarantes))
    return "|".join(str(x) for x in (emisor_cik, quien, t["tabla"], t["fecha_operacion"], t["codigo"], t["titulos"], t["precio"],
                                     t["titularidad"]))


def guardar_form4(con: sqlite3.Connection, *, acceso: str, cik_presentador: str, fecha_presentacion: str,
                  aceptado_en: str | None, f4: sec.Form4, url: str, url_indice: str, obtenido_en: str | None = None) -> int:
    ejercidos = {(t["fecha_operacion"]) for t in f4.transacciones if t["codigo"] in ("M", "X", "O", "C")}
    with con:
        con.execute("INSERT OR IGNORE INTO mp_documentos (acceso, tipo, cik_presentador, nombre_presentador, cik_emisor, emisor, "
                    "simbolo, periodo, fecha_presentacion, aceptado_en, es_enmienda, fecha_original, plan_10b5_1, declarantes, url, "
                    "url_indice, obtenido_en, filas) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (acceso, f4.tipo, str(int(cik_presentador)), "; ".join(d["nombre"] for d in f4.declarantes), f4.emisor_cik,
                     f4.emisor, f4.simbolo, f4.periodo, fecha_presentacion, _norm_iso(aceptado_en, fecha_presentacion),
                     int(f4.tipo.endswith("/A")), f4.fecha_original, int(f4.plan_10b5_1),
                     json.dumps(f4.declarantes, ensure_ascii=False), url, url_indice, obtenido_en or ahora(),
                     len(f4.transacciones)))
        con.executemany(
            "INSERT OR IGNORE INTO mp_form4 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(acceso, t["tabla"], t["fila"], t["titulo_valor"], t["fecha_operacion"], t["codigo"], t["adquirido_dispuesto"],
              t["titulos"], t["precio"], t["posee_despues"], t["titularidad"], t["naturaleza"], t["clasificacion"],
              t["descripcion"], int(t["discrecional"]), int(t["plan_10b5_1"]),
              int(t["codigo"] == "S" and t["fecha_operacion"] in ejercidos), t["notas"],
              huella_f4(f4.emisor_cik, f4.declarantes, t)) for t in f4.transacciones])
    return len(f4.transacciones)


# ------------------------------------------------------------------------------------------------- 13F a una fecha
def documentos_13f(con, cik: str, hasta: str | None = None) -> list[dict]:
    q = "SELECT * FROM mp_documentos WHERE cik_presentador=? AND tipo LIKE '13F%'"
    par: list = [str(int(cik))]
    if hasta:
        q += " AND aceptado_en <= ?"
        par.append(hasta)
    return [dict(r) for r in con.execute(q + " ORDER BY periodo, aceptado_en", par)]


def cartera_13f(con, cik: str, periodo: str, hasta: str | None = None) -> tuple[dict, list[dict]]:
    """Cartera del gestor en el periodo tal como se conocía a la hora `hasta`.
    El original (13F-HR) o la última enmienda RESTATEMENT la reemplazan; las enmiendas NEW HOLDINGS se suman."""
    docs = [d for d in documentos_13f(con, cik, hasta) if d["periodo"] == periodo]
    base = None
    for d in docs:  # en orden de aceptación: la última versión completa vigente
        if not d["es_enmienda"] or (d["tipo_enmienda"] or "").upper() == "RESTATEMENT":
            base = d
    if base is None:
        return {}, docs
    usados = [base] + [d for d in docs if d["es_enmienda"] and (d["tipo_enmienda"] or "").upper() == "NEW HOLDINGS"
                       and d["aceptado_en"] >= base["aceptado_en"]]
    cartera: dict[tuple[str, str], dict] = {}
    for d in usados:
        for r in con.execute("SELECT * FROM mp_13f WHERE acceso=?", (d["acceso"],)):
            a = cartera.setdefault((r["cusip"], r["instrumento"]), {"cusip": r["cusip"], "instrumento": r["instrumento"],
                                                                    "emisor": r["emisor"], "clase": r["clase"], "titulos": 0.0,
                                                                    "valor_usd": 0.0, "accesos": []})
            a["titulos"] += r["titulos"]
            a["valor_usd"] += r["valor_usd"]
            a["accesos"].append(d["acceso"])
    return cartera, usados


UMBRAL_SIN_CAMBIO = 0.01
SPLITS_COMUNES = (2, 3, 4, 5, 10, 20, 25, 50)


def clasificar_cambio(previo: float, actual: float) -> str:
    if previo <= 0 and actual > 0:
        return "nueva"
    if previo > 0 and actual <= 0:
        return "salida"
    if previo <= 0 and actual <= 0:
        return "sin_cambio"
    d = actual / previo - 1
    return "sin_cambio" if abs(d) < UMBRAL_SIN_CAMBIO else ("aumento" if d > 0 else "reduccion")


def corregir_escala(con) -> list[str]:
    """Reescala documentos ya guardados cuyo VALUE venía en miles (una vez; deja la nota en el documento)."""
    corregidos = []
    for (acc,) in con.execute("SELECT acceso FROM mp_documentos WHERE tipo LIKE '13F%' AND nota IS NULL").fetchall():
        px = sorted(v / t for t, v in con.execute("SELECT titulos, valor_usd FROM mp_13f WHERE acceso=? AND instrumento='SH' "
                                                   "AND titulos > 0 AND valor_usd > 0", (acc,)))
        if len(px) >= 3 and px[len(px) // 2] < 1.0:
            with con:
                con.execute("UPDATE mp_13f SET valor_usd = valor_usd * 1000 WHERE acceso=?", (acc,))
                con.execute("UPDATE mp_documentos SET nota=? WHERE acceso=?",
                            (f"El documento declara VALUE en miles de dólares (precio implícito mediano {px[len(px) // 2]:.3f} "
                             "USD): la terminal lo multiplicó por 1000.", acc))
            corregidos.append(acc)
    return corregidos


def cambios_13f(con, cik: str, hasta: str | None = None, factor_split=None) -> dict:
    """Cambios entre las dos últimas carteras conocidas a la hora `hasta`. `factor_split(cusip, desde, hasta)` devuelve el
    factor acumulado de splits entre los dos cortes (títulos previos × factor). Sin split conocido, un cambio con
    precio implícito ≈ 1/k (k = 2, 3, 4, 5, 10…) se marca «no comparable (posible split)» en vez de aumento o reducción."""
    periodos = sorted({d["periodo"] for d in documentos_13f(con, cik, hasta) if d["periodo"]})
    if not periodos:
        return {"periodo": None, "periodo_previo": None, "filas": [], "documentos": []}
    actual_p = periodos[-1]
    previo_p = periodos[-2] if len(periodos) > 1 else None
    actual, docs_a = cartera_13f(con, cik, actual_p, hasta)
    previo, docs_p = cartera_13f(con, cik, previo_p, hasta) if previo_p else ({}, [])
    filas = []
    for clave in sorted(set(actual) | set(previo)):
        a, p = actual.get(clave), previo.get(clave)
        if clave[1] != "SH":  # opciones y deuda: se informan aparte, no son posiciones en acciones
            continue
        tit_p = (p or {}).get("titulos", 0.0)
        tit_a = (a or {}).get("titulos", 0.0)
        factor = factor_split(clave[0], previo_p, actual_p) if (factor_split and previo_p and p and a) else 1.0
        nota = None
        clas = clasificar_cambio(tit_p * factor, tit_a) if previo_p else "sin_periodo_previo"
        if factor != 1.0:
            nota = f"Títulos del periodo previo ajustados por split ×{factor:g}."
        elif p and a and tit_p > 0 and tit_a > 0 and p["valor_usd"] > 0 and a["valor_usd"] > 0:
            razon_px = (p["valor_usd"] / tit_p) / (a["valor_usd"] / tit_a)
            k = min(SPLITS_COMUNES, key=lambda x: abs(math.log(razon_px / x)))
            # caída del precio implícito ≈ k veces (con ±60 % de movimiento propio en el trimestre)
            if razon_px > 1.6 and abs(math.log(razon_px / k)) < math.log(1.6):
                clas, nota = "no_comparable", (f"El precio implícito cayó ≈ {razon_px:.1f}×: posible split no registrado; "
                                               "los títulos no son comparables entre periodos.")
        filas.append({"cusip": clave[0], "emisor": (a or p)["emisor"], "clase": (a or p)["clase"], "titulos_previo": tit_p,
                      "titulos_previo_ajustado": tit_p * factor, "titulos": tit_a, "valor_usd": (a or {}).get("valor_usd", 0.0),
                      "valor_usd_previo": (p or {}).get("valor_usd", 0.0), "factor_split": factor, "clasificacion": clas,
                      "nota": nota, "accesos": (a or p)["accesos"]})
    return {"periodo": actual_p, "periodo_previo": previo_p, "filas": filas, "documentos": docs_a + docs_p}


# ------------------------------------------------------------------------------------------------- Form 4 a una fecha
def form4(con, cik_emisor: str | None = None, hasta: str | None = None, desde_operacion: str | None = None) -> list[dict]:
    """Operaciones de Form 4 conocidas a `hasta`, sin duplicar las que una 4/A repite. Si una 4/A cambia los datos, la
    original queda marcada «corregida por» la enmienda (del mismo emisor, declarantes y fecha de operación)."""
    q = ("SELECT f.*, d.tipo, d.cik_emisor, d.emisor, d.simbolo, d.fecha_presentacion, d.aceptado_en, d.obtenido_en, d.url, "
         "d.url_indice, d.declarantes, d.fecha_original FROM mp_form4 f JOIN mp_documentos d ON d.acceso=f.acceso WHERE 1=1")
    par: list = []
    if cik_emisor:
        q += " AND d.cik_emisor=?"
        par.append(str(int(cik_emisor)))
    if hasta:
        q += " AND d.aceptado_en <= ?"
        par.append(hasta)
    if desde_operacion:
        q += " AND f.fecha_operacion >= ?"
        par.append(desde_operacion)
    filas = [dict(r) for r in con.execute(q + " ORDER BY d.aceptado_en, f.acceso, f.tabla, f.fila", par)]
    vistas: dict[str, dict] = {}
    out = []
    for f in filas:
        f["declarantes"] = json.loads(f["declarantes"] or "[]")
        if f["huella"] in vistas:  # mismo hecho repetido en una enmienda: una sola fila, con ambas evidencias
            vistas[f["huella"]].setdefault("tambien_en", []).append(f["acceso"])
            continue
        vistas[f["huella"]] = f
        out.append(f)
    enmiendas = [f for f in out if f["tipo"].endswith("/A")]
    for f in out:
        if f["tipo"].endswith("/A"):
            continue
        quien = {d["cik"] for d in f["declarantes"]}
        for e in enmiendas:
            if e["cik_emisor"] == f["cik_emisor"] and {d["cik"] for d in e["declarantes"]} == quien \
                    and e["aceptado_en"] > f["aceptado_en"] and (e["fecha_original"] == f["fecha_presentacion"] if e["fecha_original"]
                                                                  else f["fecha_presentacion"] <= e["fecha_presentacion"]):
                f["corregido_por"] = e["acceso"]
                break
    return out


# ------------------------------------------------------------------------------------------------- CUSIP → símbolo
ABREV = {"FINL": "FINANCIAL", "INTL": "INTERNATIONAL", "HLDGS": "HOLDINGS", "HLDG": "HOLDING", "MTRS": "MOTORS",
         "SVCS": "SERVICES", "COS": "COMPANIES", "PETE": "PETROLEUM", "SOUTHN": "SOUTHERN", "INS": "INSURANCE", "TECHNOLOGIES": "TECHNOLOGY", "PPTYS": "PROPERTIES", "RES": "RESOURCES",
         "PHARMACEUTICALS": "PHARMACEUTICAL", "COMMUNICATIONS": "COMMUNICATION", "SYS": "SYSTEM", "GRP": "GROUP",
         "BANCORPORATION": "BANCORP", "LABS": "LABORATORIES", "ENTMT": "ENTERTAINMENT", "MGMT": "MANAGEMENT",
         "PAC": "PACIFIC", "INDS": "INDUSTRIES", "RUBR": "RUBBER", "MATLS": "MATERIALS", "GEN": "GENERAL", "NATL": "NATIONAL",
         "HLDNGS": "HOLDINGS", "INCORPORATED": "INC", "AMER": "AMERIC", "AMERN": "AMERIC", "AMERICA": "AMERIC", "AMERICAN": "AMERIC", "COMMUN": "COMMUNICATIONS",
         "ELEC": "ELECTRIC", "INVT": "INVESTMENT", "MED": "MEDICAL", "PRODS": "PRODUCTS", "SOLUTIONS": "SOLUTION",
         "SYSTEMS": "SYSTEM", "MANAGEMENT": "MANAGEMENT", "TR": "TRUST", "CMNTYS": "COMMUNITIES", "SVCS": "SERVICES"}
SUFIJOS = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC", "NV", "SA", "AG", "LP", "LLC", "THE",
           "NEW", "DEL", "HOLDINGS", "HOLDING", "GROUP", "CL", "CLASS", "A", "B", "C", "COM", "SE", "SPONSORED", "ADR", "ADS",
           "SHS", "SAB", "DE", "CV", "PLC", "ORD", "REIT"}


def normalizar_nombre(n: str) -> str:
    """Nombre comparable: sin puntuación ni sufijos societarios, abreviaturas expandidas y palabras en orden alfabético
    (la SEC escribe «HORTON D R INC /DE/» y el 13F «D R HORTON INC»)."""
    t = (n or "").upper().replace("&", " AND ")
    t = re.sub(r"\s*/[A-Z]{2,3}/?\s*$|\s/[A-Z]{2,3}/", " ", t)       # sufijo de estado de la SEC: «/DE/», «INC/CA»
    t = re.split(r"\bFORMERLY\b", t)[0]                                 # «ELEVANCE HEALTH INC FORMERLY …»
    palabras = [ABREV.get(p, p) for p in re.sub(r"[^A-Z0-9 ]", " ", t).split()]
    if len(palabras) > 2 and len(palabras[-1]) == 1 and palabras[-2] in SUFIJOS:
        palabras = palabras[:-1]                                        # «… INC N» (NEW truncado en el 13F)
    nucleo = [p for p in palabras if p not in SUFIJOS]
    return "".join(sorted(nucleo or palabras))


def mapear_cusip(con, cusip: str, emisor: str, tickers_sec: list[dict], forzado: dict[str, str] | None = None) -> dict:
    """CUSIP → símbolo por el nombre del emisor (lista oficial de la SEC). Varias clases (p. ej. LEN y LEN-B) ⇒ ambiguo:
    no se atribuye a ninguna. `forzado` permite fijar CUSIP verificados a mano (config/cusip.csv)."""
    f = con.execute("SELECT * FROM mp_cusip WHERE cusip=?", (cusip,)).fetchone()
    if f and f["metodo"] in ("manual", "nombre_sec"):
        return dict(f)
    if forzado and cusip in forzado:
        res = {"cusip": cusip, "simbolo": forzado[cusip], "cik": None, "metodo": "manual", "ambiguo": 0, "candidatos": None}
    else:
        n = normalizar_nombre(emisor)
        ciks = {t["cik_str"] for t in tickers_sec if normalizar_nombre(t["title"]) == n}
        cands = sorted({t["ticker"] for t in tickers_sec if t["cik_str"] in ciks})
        if len(cands) == 1:
            res = {"cusip": cusip, "simbolo": cands[0], "cik": str(next(iter(ciks))), "metodo": "nombre_sec", "ambiguo": 0,
                   "candidatos": None}
        else:
            res = {"cusip": cusip, "simbolo": None, "cik": str(next(iter(ciks))) if len(ciks) == 1 else None,
                   "metodo": "ambiguo" if cands else "sin_coincidencia", "ambiguo": int(len(cands) > 1),
                   "candidatos": ",".join(cands) or None}
    with con:
        con.execute("INSERT OR REPLACE INTO mp_cusip VALUES (?,?,?,?,?,?,?)",
                    (res["cusip"], res["simbolo"], res["cik"], res["metodo"], res["ambiguo"], res["candidatos"], ahora()))
    return res


def fuente(con, clave: str, *, ok: bool, consultas: int, error: str | None = None, detalle: dict | None = None) -> None:
    t = ahora()
    with con:
        con.execute("INSERT INTO mp_fuente (clave, ultimo_intento, ultimo_ok, ultimo_error, consultas, detalle) VALUES (?,?,?,?,?,?) "
                    "ON CONFLICT(clave) DO UPDATE SET ultimo_intento=excluded.ultimo_intento, "
                    "ultimo_ok=COALESCE(excluded.ultimo_ok, mp_fuente.ultimo_ok), ultimo_error=excluded.ultimo_error, "
                    "consultas=excluded.consultas, detalle=excluded.detalle",
                    (clave, t, t if ok else None, None if ok else (error or "error")[:200], consultas,
                     json.dumps(detalle or {}, ensure_ascii=False)))


def remapear(con, tickers_sec: list[dict], forzado: dict[str, str] | None = None) -> dict:
    """Vuelve a mapear los CUSIP automáticos (conserva los manuales), p. ej. tras mejorar la normalización."""
    with con:
        con.execute("DELETE FROM mp_cusip WHERE metodo <> 'manual'")
    for cusip, emisor in con.execute("SELECT cusip, MAX(emisor) FROM mp_13f WHERE instrumento='SH' GROUP BY cusip").fetchall():
        mapear_cusip(con, cusip, emisor, tickers_sec, forzado)
    return {r[0]: r[1] for r in con.execute("SELECT metodo, COUNT(*) FROM mp_cusip GROUP BY metodo")}
