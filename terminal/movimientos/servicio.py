"""Movimientos públicos de inversionistas institucionales (13F) e insiders (Form 4), con fuente oficial SEC EDGAR.

Es contexto de investigación: ningún movimiento crea por sí solo una orden, una boleta ni una recomendación de compra o
venta, y no entra a la puntuación de las propuestas (peso 0, ver docs/movimientos-publicos.md).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from .. import config, vigencia
from . import almacen as alm
from . import sec

log = logging.getLogger("terminal.movimientos")
_bloqueo = threading.Lock()

GESTORES = [  # verificados en data.sec.gov el 1-oct-2026 (nombre y último 13F)
    {"cik": 1067983, "nombre": "Berkshire Hathaway"},
    {"cik": 1656456, "nombre": "Appaloosa (David Tepper)"},
    {"cik": 1061768, "nombre": "Baupost Group (Seth Klarman)"},
    {"cik": 1536411, "nombre": "Duquesne Family Office (Stanley Druckenmiller)"},
    {"cik": 1709323, "nombre": "Himalaya Capital (Li Lu)"},
    {"cik": 1040273, "nombre": "Third Point (Daniel Loeb)"},
    {"cik": 1112520, "nombre": "Akre Capital Management"},
    {"cik": 1649339, "nombre": "Scion Asset Management (Michael Burry)"},
]
POR_OMISION = {"compra_min_usd": 100_000, "venta_min_usd": 1_000_000, "dias_alerta_form4": 3, "dias_alerta_13f": 10,
               "dias_form4": 90, "periodos_13f": 3, "cada_horas_form4": 6, "cada_horas_13f": 24, "max_emisoras": 40,
               "en_puntuacion": False}
LIMITE_13F = ("Cambio inferido de dos fotografías trimestrales (fin de periodo): no es una operación con fecha conocida. "
              "El gestor pudo comprar y vender en medio. El 13F se publica hasta 45 días después del corte.")
LIMITE_F4 = {
    True: "Compra o venta discrecional declarada; el Form 4 se presenta hasta 2 días hábiles después. No implica por sí sola "
          "que la emisora suba o baje.",
    False: "No equivale a una compra o venta discrecional en mercado (adjudicación, ejercicio, impuestos, plan 10b5-1, "
           "donación u otra).",
}
TIPOS_FORM4 = {"compra_mercado": "Compra en mercado", "venta_mercado": "Venta en mercado",
               "venta_plan_10b5_1": "Venta programada (10b5-1)", "compra_plan_10b5_1": "Compra programada (10b5-1)",
               "adjudicacion": "Adjudicación", "ejercicio": "Ejercicio de opciones", "retencion_impuestos": "Retención de impuestos",
               "donacion": "Donación", "conversion": "Conversión"}
TIPOS_13F = {"nueva": "Nueva posición", "aumento": "Aumento", "reduccion": "Reducción", "salida": "Salida",
             "sin_cambio": "Sin cambio", "no_comparable": "No comparable (posible split)", "sin_periodo_previo": "Sin periodo previo"}


def cfg(ajustes) -> dict:
    return {**POR_OMISION, **(ajustes.get("movimientos") or {})}


def gestores(ajustes) -> list[dict]:
    return (ajustes.get("movimientos") or {}).get("gestores") or GESTORES


# ------------------------------------------------------------------------------------------------- relación con la terminal
def relevancia(con: sqlite3.Connection, ajustes) -> dict:
    """Emisoras de su cartera (captura del portal o registro), de las propuestas vigentes y de su lista de seguimiento."""
    from .. import servicios
    rel: dict[str, set[str]] = {}
    try:
        for p in servicios.cartera_actual(con, ajustes).get("posiciones") or []:
            rel.setdefault(p["instrumento_id"], set()).add("cartera")
        props = servicios.propuestas_guardadas(con, ajustes, servicios.perfil_actual(con, ajustes))
        for p in props.values():
            for a in (p or {}).get("pesos") or []:
                if (a.get("peso") or 0) > 0:
                    rel.setdefault(a["id"], set()).add("propuesta")
    except Exception:  # noqa: BLE001 - sin cartera o propuestas, se usa lo demás
        log.exception("relevancia: cartera o propuestas no disponibles")
    for (iid,) in con.execute("SELECT instrumento_id FROM seguimiento"):
        rel.setdefault(iid, set()).add("seguimiento")
    return rel


def catalogo(con) -> set[str]:
    """Emisoras del catálogo del simulador importado (si no se importó, el universo activo de la terminal)."""
    ids = {r[0] for r in con.execute("SELECT id FROM universo_simulador")}
    return ids or {r[0] for r in con.execute("SELECT id FROM instrumentos WHERE estado='activo'")}


def mapa_simbolos(con) -> dict[str, str]:
    """Símbolo de EE. UU. → instrumento del SIC (BRK.B, BRK-B y BRKB se tratan igual)."""
    out = {}
    for iid, s in con.execute("SELECT id, listado_referencia FROM instrumentos WHERE moneda_referencia='USD' AND listado_referencia IS NOT NULL"):
        out[s.upper().replace(".", "-")] = iid
    return out


def _grupo(iid: str | None, rel: dict, cat: set) -> str:
    if not iid:
        return "fuera del catálogo"
    g = rel.get(iid) or set()
    for nombre in ("cartera", "propuesta", "seguimiento"):
        if nombre in g:
            return nombre
    return "operable en el Reto" if iid in cat else "fuera del catálogo"


def _fx(con, fecha: str | None) -> dict | None:
    if not fecha:
        return None
    f = con.execute("SELECT fecha, valor, proveedor FROM fx WHERE par='USDMXN' AND fecha<=? AND proveedor <> 'demo_sintetico' "
                    "ORDER BY fecha DESC, CASE proveedor WHEN 'banxico' THEN 0 ELSE 1 END LIMIT 1", (fecha,)).fetchone()
    return {"fecha": f[0], "valor": float(f[1]), "fuente": f[2]} if f else None


def factor_split(con):
    def f(cusip: str, desde: str, hasta: str) -> float:
        m = con.execute("SELECT simbolo FROM mp_cusip WHERE cusip=?", (cusip,)).fetchone()
        if not m or not m[0]:
            return 1.0
        iid = mapa_simbolos(con).get(m[0].upper().replace(".", "-"))
        if not iid:
            return 1.0
        x = 1.0
        for (v,) in con.execute("SELECT DISTINCT valor FROM eventos_corporativos WHERE instrumento_id=? AND tipo='split' "
                                "AND fecha > ? AND fecha <= ?", (iid, desde, hasta)):
            x *= float(v)
        return x
    return f


# ------------------------------------------------------------------------------------------------- actualización
def _cliente(cliente=None) -> sec.ClienteSEC:
    return sec.ClienteSEC(os.environ.get("SEC_USER_AGENT"), cliente=cliente)


def tickers_sec(cli: sec.ClienteSEC) -> list[dict]:
    """Lista oficial ticker ↔ CIK de la SEC, guardada una semana en data/ (evita repetir la descarga)."""
    ruta = config.data_dir() / "sec_company_tickers.json"
    if ruta.exists() and datetime.now(UTC).timestamp() - ruta.stat().st_mtime < 7 * 86400:
        return json.loads(ruta.read_text(encoding="utf-8"))
    datos = list(cli.get(sec.TICKERS).json().values())
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return datos


def _toca(con, clave: str, horas: float) -> bool:
    f = con.execute("SELECT ultimo_ok FROM mp_fuente WHERE clave=?", (clave,)).fetchone()
    return not f or not f[0] or datetime.fromisoformat(f[0]) < datetime.now(UTC) - timedelta(hours=horas)


def _xml_de_indice(cli, cik: int, acceso: str) -> tuple[str | None, str | None]:
    idx = cli.get(sec.url_documento(cik, acceso, "index.json")).json()
    nombres = [i["name"] for i in idx["directory"]["item"] if i["name"].lower().endswith(".xml")]
    primario = next((n for n in nombres if n.lower() == "primary_doc.xml"), None)
    tabla = next((n for n in nombres if n.lower() != "primary_doc.xml"), None)
    return primario, tabla


def actualizar_13f(con, ajustes, cli: sec.ClienteSEC | None = None) -> dict:
    alm.asegurar(con)
    c = cfg(ajustes)
    cli = cli or _cliente()
    nuevos, errores, avisos = 0, [], []
    tickers = None
    for g in gestores(ajustes):
        try:
            sub = cli.get(sec.SUBMISSIONS.format(cik=int(g["cik"]))).json()
            rec = sub["filings"]["recent"]
            filas = [dict(zip(("forma", "acceso", "fecha", "periodo", "aceptado"), x)) for x in
                     zip(rec["form"], rec["accessionNumber"], rec["filingDate"], rec["reportDate"], rec["acceptanceDateTime"])
                     if x[0] in ("13F-HR", "13F-HR/A", "13F-NT", "13F-NT/A")]
            periodos = sorted({f["periodo"] for f in filas if f["forma"].startswith("13F-HR")}, reverse=True)[: int(c["periodos_13f"])]
            if filas and filas[0]["forma"].startswith("13F-NT"):
                avisos.append(f"{g['nombre']}: su último documento es un 13F-NT (sus posiciones se reportan en el 13F de otro gestor).")
            for f in filas:
                if not f["forma"].startswith("13F-HR") or f["periodo"] not in periodos or alm.visto(con, f["acceso"]):
                    continue
                primario, tabla = _xml_de_indice(cli, g["cik"], f["acceso"])
                if not primario:
                    continue
                portada = sec.parsear_portada_13f(cli.get(sec.url_documento(g["cik"], f["acceso"], primario)).content)
                filas_t = sec.parsear_tabla_13f(cli.get(sec.url_documento(g["cik"], f["acceso"], tabla)).content) if tabla else []
                alm.guardar_13f(con, acceso=f["acceso"], cik=str(g["cik"]), gestor=g["nombre"], fecha_presentacion=f["fecha"],
                                aceptado_en=f["aceptado"], portada=portada, filas=filas_t,
                                url=sec.url_documento(g["cik"], f["acceso"], primario), url_indice=sec.url_indice(g["cik"], f["acceso"]))
                tickers = tickers if tickers is not None else tickers_sec(cli)
                forzado = cusips_manual()
                for x in {(r["cusip"], r["emisor"]) for r in filas_t if not r["put_call"]}:
                    alm.mapear_cusip(con, x[0], x[1], tickers, forzado)
                nuevos += 1
        except (sec.ErrorSEC, KeyError, ValueError) as e:
            errores.append(f"{g['nombre']}: {e}")
    alm.fuente(con, "13f", ok=not errores, consultas=cli.consultas, error="; ".join(errores)[:200] or None,
               detalle={"documentos_nuevos": nuevos, "avisos": avisos, "errores": errores[:5]})
    return {"estado": "ok" if not errores else "parcial", "documentos_nuevos": nuevos, "consultas": cli.consultas,
            "errores": errores, "avisos": avisos}


def emisoras_form4(con, ajustes) -> list[dict]:
    """Emisoras de EE. UU. (SIC) relevantes: cartera, propuestas y seguimiento (máximo `max_emisoras`)."""
    rel = relevancia(con, ajustes)
    orden = sorted(rel, key=lambda i: (0 if "cartera" in rel[i] else 1 if "seguimiento" in rel[i] else 2, i))
    ins = {r["id"]: dict(r) for r in con.execute("SELECT * FROM instrumentos")}
    out = [ins[i] for i in orden if i in ins and ins[i].get("moneda_referencia") == "USD" and ins[i].get("listado_referencia")
           and ins[i].get("clase") != "etf"]
    return out[: int(cfg(ajustes)["max_emisoras"])]


def actualizar_form4(con, ajustes, cli: sec.ClienteSEC | None = None, emisoras: list[dict] | None = None) -> dict:
    alm.asegurar(con)
    c = cfg(ajustes)
    cli = cli or _cliente()
    emisoras = emisoras if emisoras is not None else emisoras_form4(con, ajustes)
    limite = (date.today() - timedelta(days=int(c["dias_form4"]))).isoformat()
    nuevos, errores = 0, []
    ciks = None
    for ins in emisoras:
        try:
            if ciks is None:
                ciks = {t["ticker"].upper().replace(".", "-"): int(t["cik_str"]) for t in tickers_sec(cli)}
            cik = ciks.get(ins["listado_referencia"].upper().replace(".", "-"))
            if not cik:
                continue
            rec = cli.get(sec.SUBMISSIONS.format(cik=cik)).json()["filings"]["recent"]
            for forma, acc, doc, fecha, acept in zip(rec["form"], rec["accessionNumber"], rec["primaryDocument"],
                                                     rec["filingDate"], rec["acceptanceDateTime"]):
                if forma not in ("4", "4/A") or fecha < limite or alm.visto(con, acc):
                    continue
                url = sec.url_documento(cik, acc, doc.split("/")[-1])
                try:
                    f4 = sec.parsear_form4(cli.get(url).content)
                except sec.ErrorSEC as e:
                    errores.append(f"{ins['id']} {acc}: {e}")
                    continue
                except Exception:  # noqa: BLE001 - un documento mal formado no detiene el resto
                    errores.append(f"{ins['id']} {acc}: documento no legible")
                    continue
                alm.guardar_form4(con, acceso=acc, cik_presentador=str(cik), fecha_presentacion=fecha, aceptado_en=acept, f4=f4,
                                  url=url, url_indice=sec.url_indice(cik, acc))
                nuevos += 1
        except (sec.ErrorSEC, KeyError, ValueError) as e:
            errores.append(f"{ins['id']}: {e}")
    alm.fuente(con, "form4", ok=not errores, consultas=cli.consultas, error="; ".join(errores)[:200] or None,
               detalle={"documentos_nuevos": nuevos, "emisoras": len(emisoras), "errores": errores[:5]})
    return {"estado": "ok" if not errores else "parcial", "documentos_nuevos": nuevos, "emisoras": len(emisoras),
            "consultas": cli.consultas, "errores": errores}


def actualizar(con, ajustes, forzar: bool = False) -> dict:
    """Actualización incremental respetando el ritmo de cada fuente (Form 4 cada 6 h; 13F cada 24 h)."""
    alm.asegurar(con)
    if not os.environ.get("SEC_USER_AGENT"):
        return {"estado": "requiere_configuracion", "mensaje": "Defina SEC_USER_AGENT (nombre y correo) en .env"}
    if not _bloqueo.acquire(blocking=False):
        return {"estado": "en_curso"}
    try:
        c = cfg(ajustes)
        cli = _cliente()
        res = {}
        if forzar or _toca(con, "form4", c["cada_horas_form4"]):
            res["form4"] = actualizar_form4(con, ajustes, cli)
        if forzar or _toca(con, "13f", c["cada_horas_13f"]):
            res["13f"] = actualizar_13f(con, ajustes, cli)
        return {"estado": "ok" if res else "al_dia", **res, "consultas": cli.consultas}
    except sec.ErrorSEC as e:
        return {"estado": "requiere_configuracion" if "SEC_USER_AGENT" in str(e) else "error", "mensaje": str(e)}
    finally:
        _bloqueo.release()


def cusips_manual() -> dict[str, str]:
    """CUSIP verificados a mano (config/cusip.csv: cusip,simbolo,fuente). Resuelven clases ambiguas."""
    ruta = config.CONFIG_DIR / "cusip.csv"
    out = {}
    if ruta.exists():
        for ln in ruta.read_text(encoding="utf-8").splitlines()[1:]:
            partes = [x.strip() for x in ln.split(",")]
            if len(partes) >= 2 and len(partes[0]) == 9:
                out[partes[0].upper()] = partes[1].upper()
    return out


# ------------------------------------------------------------------------------------------------- consulta y vista
def fecha_limite_13f(periodo: str) -> str:
    """45 días después del fin del trimestre; si cae en fin de semana o festivo, el siguiente día hábil."""
    d = pd.Timestamp(periodo) + pd.Timedelta(days=45)
    cal = vigencia.calendario("XNYS")
    return cal.date_to_session(d, direction="next").date().isoformat()


def _iso(t: str | None) -> str | None:
    return t


def listar(con, ajustes, emisora: str | None = None, gestor: str | None = None, tipo: str | None = None,
           desde: str | None = None, hasta: str | None = None, limite: int = 300) -> dict:
    alm.asegurar(con)
    rel, cat, simbolos = relevancia(con, ajustes), catalogo(con), mapa_simbolos(con)
    ins = {r["id"]: dict(r) for r in con.execute("SELECT id, clave_operable FROM instrumentos")}
    hasta_iso = (pd.Timestamp(hasta, tz="UTC") + pd.Timedelta(days=1)).isoformat() if hasta else None
    f4 = []
    for r in alm.form4(con, hasta=hasta_iso, desde_operacion=desde):
        iid = simbolos.get((r["simbolo"] or "").replace(".", "-"))
        if emisora and iid != emisora:
            continue
        if tipo and not (tipo == r["clasificacion"] or (tipo == "no_discrecional" and not r["discrecional"])):
            continue
        valor = (r["titulos"] or 0) * (r["precio"] or 0)
        fx = _fx(con, r["fecha_operacion"]) if iid and r["precio"] else None
        f4.append({
            "fuente": "Form 4", "acceso": r["acceso"], "tabla": r["tabla"], "fila": r["fila"], "tipo_documento": r["tipo"], "emisor": r["emisor"], "simbolo": r["simbolo"],
            "instrumento_id": iid, "clave": (ins.get(iid) or {}).get("clave_operable"), "grupo": _grupo(iid, rel, cat),
            "operable": bool(iid and iid in cat), "declarantes": r["declarantes"], "titulo_valor": r["titulo_valor"],
            "fecha_operacion": r["fecha_operacion"], "fecha_presentacion": r["fecha_presentacion"], "aceptado_en": r["aceptado_en"],
            "conocido_en": r["obtenido_en"], "codigo": r["codigo"], "clasificacion": r["clasificacion"],
            "tipo": TIPOS_FORM4.get(r["clasificacion"], r["descripcion"]), "descripcion": r["descripcion"],
            "discrecional": bool(r["discrecional"]) and not r["tras_ejercicio"], "tras_ejercicio": bool(r["tras_ejercicio"]),
            "titulos": r["titulos"], "precio_usd": r["precio"], "valor_usd": valor, "titularidad":
                {"D": "directa", "I": "indirecta"}.get(r["titularidad"] or "", r["titularidad"]), "naturaleza": r["naturaleza"],
            "posee_despues": r["posee_despues"], "notas": r["notas"], "url": r["url"], "url_indice": r["url_indice"],
            "tambien_en": r.get("tambien_en", []), "corregido_por": r.get("corregido_por"),
            "referencia_mxn": ({"valor": valor * fx["valor"], "fx": fx,
                                "etiqueta": f"referencia EE. UU. × tipo de cambio del {fx['fecha']}; no es cotización del SIC"}
                               if fx and valor else None),
            "limite": LIMITE_F4[bool(r["discrecional"]) and not r["tras_ejercicio"]]
                      + (" Venta del mismo día que un ejercicio de opciones." if r["tras_ejercicio"] else "")})
    trece = []
    hoy = date.today()
    fs = factor_split(con)
    for g in gestores(ajustes):
        if gestor and str(g["cik"]) != str(gestor):
            continue
        cam = alm.cambios_13f(con, str(g["cik"]), hasta=hasta_iso, factor_split=fs)
        if not cam["periodo"]:
            continue
        docs = {d["acceso"]: d for d in cam["documentos"]}
        antiguo = (hoy - date.fromisoformat(cam["periodo"])).days > 200
        for x in cam["filas"]:
            if tipo and tipo != x["clasificacion"]:
                continue
            if not tipo and x["clasificacion"] == "sin_cambio":
                continue
            m = con.execute("SELECT * FROM mp_cusip WHERE cusip=?", (x["cusip"],)).fetchone()
            sim = m["simbolo"] if m else None
            iid = simbolos.get(sim.replace(".", "-")) if sim else None
            if emisora and iid != emisora:
                continue
            d = [docs[a] for a in x["accesos"] if a in docs]
            trece.append({
                "fuente": "13F", "gestor": g["nombre"], "cik_gestor": g["cik"], "cusip": x["cusip"], "emisor": x["emisor"],
                "clase": x["clase"], "simbolo": sim, "mapeo": (dict(m)["metodo"] if m else "sin_mapear"),
                "candidatos": (m["candidatos"] if m else None), "instrumento_id": iid,
                "grupo": _grupo(iid, rel, cat) if sim else ("sin identificar (varias clases)" if m and m["ambiguo"] else "sin identificar"),
                "operable": bool(iid and iid in cat), "clasificacion": x["clasificacion"],
                "tipo": TIPOS_13F.get(x["clasificacion"], x["clasificacion"]), "periodo": cam["periodo"],
                "periodo_previo": cam["periodo_previo"], "titulos": x["titulos"], "titulos_previo": x["titulos_previo"],
                "titulos_previo_ajustado": x["titulos_previo_ajustado"], "factor_split": x["factor_split"],
                "valor_usd": x["valor_usd"], "valor_usd_previo": x["valor_usd_previo"], "nota": x["nota"],
                "fecha_operacion": None, "fecha_presentacion": max((y["fecha_presentacion"] for y in d), default=None),
                "aceptado_en": max((y["aceptado_en"] for y in d), default=None),
                "conocido_en": max((y["obtenido_en"] for y in d), default=None),
                "documentos": [{"acceso": y["acceso"], "tipo": y["tipo"], "tipo_enmienda": y["tipo_enmienda"], "url": y["url"],
                                "url_indice": y["url_indice"], "nota": y.get("nota")} for y in d],
                "antiguo": antiguo, "limite": LIMITE_13F + (" Datos de un corte de hace más de 200 días: no son recientes." if antiguo else "")})
    if desde:
        trece = [t for t in trece if (t["fecha_presentacion"] or "") >= desde]
    orden = {"cartera": 0, "propuesta": 1, "seguimiento": 2, "operable en el Reto": 3}
    f4.sort(key=lambda r: r["aceptado_en"] or "", reverse=True)          # estable: primero por fecha…
    f4.sort(key=lambda r: (orden.get(r["grupo"], 4), not r["discrecional"]))  # …luego lo que le afecta y lo discrecional
    trece.sort(key=lambda r: (r["aceptado_en"] or "", r["valor_usd"]), reverse=True)
    trece.sort(key=lambda r: (orden.get(r["grupo"], 4), r["antiguo"]))
    return {"form4": f4[:limite], "trece_f": trece[:limite], "fuentes": estado_fuentes(con, ajustes),
            "gestores": gestores(ajustes), "seguimiento": [dict(r) for r in con.execute("SELECT * FROM seguimiento ORDER BY instrumento_id")],
            "aviso": ("Contexto de investigación con documentos públicos de la SEC. No son cotizaciones en tiempo real ni "
                      "recomendaciones: ningún movimiento crea por sí solo una orden o boleta.")}


def estado_fuentes(con, ajustes) -> list[dict]:
    alm.asegurar(con)
    out = []
    ahora_dt = datetime.now(UTC)
    for clave, nombre, horas in (("form4", "SEC EDGAR · Form 4 (insiders)", cfg(ajustes)["cada_horas_form4"]),
                                 ("13f", "SEC EDGAR · Form 13F (institucionales)", cfg(ajustes)["cada_horas_13f"])):
        f = con.execute("SELECT * FROM mp_fuente WHERE clave=?", (clave,)).fetchone()
        f = dict(f) if f else {}
        ok = f.get("ultimo_ok")
        edad = (ahora_dt - datetime.fromisoformat(ok)).total_seconds() / 3600 if ok else None
        estado = ("sin_consultar" if not f else "error" if f.get("ultimo_error") and (not ok or f["ultimo_intento"] > ok)
                  else "antigua" if edad is not None and edad > 3 * horas else "vigente")
        if estado == "sin_consultar":
            explicacion = "Aún no se consulta. Requiere SEC_USER_AGENT en .env; se actualiza sola con el motor."
        elif estado == "error":
            explicacion = f"Último intento con error: {f.get('ultimo_error')}. Se reintenta en el siguiente ciclo."
        elif estado == "antigua":
            explicacion = f"Sin actualizar desde hace {edad:.0f} h (se espera cada {horas} h)."
        else:
            explicacion = f"Actualizada hace {edad:.1f} h."
        if clave == "13f":
            u = con.execute("SELECT MAX(periodo) FROM mp_documentos WHERE tipo LIKE '13F%'").fetchone()[0]
            if u:
                sig = (pd.Timestamp(u) + pd.offsets.QuarterEnd(1)).date().isoformat()
                explicacion += (f" Último corte disponible: {u}. El 13F del corte {sig} vence el {fecha_limite_13f(sig)}"
                                + (" (después del cierre del Reto el 13-nov-2026: no basar decisiones del Reto en él)."
                                   if fecha_limite_13f(sig) > "2026-11-13" else "."))
        else:
            explicacion += " El Form 4 se presenta hasta 2 días hábiles después de la operación."
        out.append({"clave": clave, "fuente": nombre, "estado": estado, "ultimo_ok": ok, "ultimo_intento": f.get("ultimo_intento"),
                    "ultimo_error": f.get("ultimo_error"), "consultas": f.get("consultas"), "explicacion": explicacion,
                    "detalle": json.loads(f.get("detalle") or "{}")})
    return out


# ------------------------------------------------------------------------------------------------- alertas y reporte
def materiales(con, ajustes, ahora_dt: datetime | None = None) -> dict:
    """Movimientos nuevos y materiales en emisoras de su cartera, propuestas o seguimiento."""
    c = cfg(ajustes)
    ahora_dt = ahora_dt or datetime.now(UTC)
    d = listar(con, ajustes, hasta=ahora_dt.date().isoformat())
    lim4 = (ahora_dt - timedelta(days=int(c["dias_alerta_form4"]))).isoformat()
    lim13 = (ahora_dt - timedelta(days=int(c["dias_alerta_13f"]))).isoformat()
    f4 = [r for r in d["form4"] if r["grupo"] in ("cartera", "propuesta", "seguimiento") and r["discrecional"]
          and (r["aceptado_en"] or "") >= lim4 and not r.get("corregido_por")
          and ((r["clasificacion"] == "compra_mercado" and r["valor_usd"] >= c["compra_min_usd"])
               or (r["clasificacion"] == "venta_mercado" and r["valor_usd"] >= c["venta_min_usd"]))]
    t13 = [r for r in d["trece_f"] if r["grupo"] in ("cartera", "propuesta", "seguimiento") and not r["antiguo"]
           and r["clasificacion"] in ("nueva", "salida") and (r["aceptado_en"] or "") >= lim13]
    return {"form4": f4, "trece_f": t13}


def condiciones(con, ajustes, ahora_dt: datetime | None = None) -> list:
    from ..alertas import Condicion
    if not cfg(ajustes).get("alertas", True):
        return []
    m = materiales(con, ajustes, ahora_dt)
    out = []
    for r in m["form4"]:
        quien = "; ".join(f"{x['nombre']} ({x['relacion']})" for x in r["declarantes"])
        out.append(Condicion(
            "movimiento_publico", f"{r['instrumento_id']}|f4|{r['acceso']}|{r['tabla']}|{r['fila']}", True, "info",
            f"Insider: {r['tipo'].lower()} en {r['clave'] or r['simbolo']} ({r['grupo']})",
            f"{quien}: {r['tipo'].lower()} de {r['titulos']:,.0f} acciones a {r['precio_usd']:,.2f} USD (≈ {r['valor_usd']:,.0f} USD; "
            f"titularidad {r['titularidad']}) el {r['fecha_operacion']}; publicada {r['fecha_presentacion']}. {r['limite']}",
            {"enlace": r["url"], "valor_usd": r["valor_usd"]}, "SEC EDGAR (Form 4)",
            "CONTEXTO de investigación: no es una recomendación ni crea órdenes o boletas.", rearme=False))
    for r in m["trece_f"]:
        out.append(Condicion(
            "movimiento_publico", f"{r['instrumento_id']}|13f|{r['documentos'][0]['acceso'] if r['documentos'] else r['periodo']}|{r['cusip']}|{r['clasificacion']}",
            True, "info", f"13F: {r['gestor']} — {r['tipo'].lower()} en {r['simbolo']} ({r['grupo']})",
            f"Corte {r['periodo']} frente a {r['periodo_previo']}: {r['titulos_previo_ajustado']:,.0f} → {r['titulos']:,.0f} títulos; "
            f"publicado {r['fecha_presentacion']}. {LIMITE_13F}",
            {"enlace": r["documentos"][0]["url"] if r["documentos"] else None}, "SEC EDGAR (Form 13F)",
            "CONTEXTO de investigación: no es una recomendación ni crea órdenes o boletas.", rearme=False))
    return out


def texto_reporte(con, ajustes, ahora_dt: datetime | None = None) -> list[str]:
    ahora_dt = ahora_dt or datetime.now(UTC)
    m = materiales(con, ajustes, ahora_dt)
    out = [f"## Movimientos públicos (SEC EDGAR) — al {ahora_dt.date().isoformat()}", ""]
    for f in estado_fuentes(con, ajustes):
        out.append(f"- {f['fuente']}: **{f['estado']}** — {f['explicacion']}")
    out.append("")
    if not m["form4"] and not m["trece_f"]:
        out.append("Sin movimientos materiales nuevos en emisoras de su cartera, propuestas o seguimiento.")
    for r in m["form4"][:8]:
        out.append(f"- {r['fecha_operacion']} (publicado {r['fecha_presentacion']}) · {r['clave'] or r['simbolo']} · {r['tipo']} · "
                   f"{r['titulos']:,.0f} a {r['precio_usd']:,.2f} USD · {r['declarantes'][0]['nombre'] if r['declarantes'] else ''} · "
                   f"[documento]({r['url']})")
    for r in m["trece_f"][:8]:
        out.append(f"- Corte {r['periodo']} (publicado {r['fecha_presentacion']}) · {r['gestor']} · {r['tipo']} en {r['simbolo']} · "
                   f"[documento]({r['documentos'][0]['url'] if r['documentos'] else ''})")
    out += ["", "_Contexto de investigación: no son cotizaciones ni recomendaciones. El 13F es una fotografía trimestral; "
            "el Form 4 se publica hasta 2 días hábiles después de la operación._", ""]
    return out
