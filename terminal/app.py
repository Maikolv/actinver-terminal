"""Servidor local (FastAPI). Solo informa y simula: no existe ninguna ruta que envíe órdenes."""
from __future__ import annotations

import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import pandas as pd
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__, cartera, db, importar, ingesta, mercado, optimizador, vigencia
from .config import MODOS, RAIZ, cargar_ajustes, fijar_modo
from .seguridad import TOKEN_CSRF, Seguridad

logging.getLogger("httpx").setLevel(logging.WARNING)  # evita registrar URLs con credenciales
log = logging.getLogger("terminal")
WEB = RAIZ / "web"
AJUSTES = cargar_ajustes()
_calculo = threading.Lock()

RIESGOS = ("conservador", "moderado", "agresivo")
ESCENARIOS = ("base", "adverso", "favorable")


def con_db():
    con = db.conectar()
    try:
        yield con
    finally:
        con.close()


def _programador(stop: threading.Event) -> None:
    """Actualización automática opcional (EOD tras el cierre). Respeta los límites de cada proveedor."""
    prog = AJUSTES["programacion"]
    while not stop.wait(int(prog["revisar_cada_min"]) * 60):
        try:
            con = db.conectar()
            ingesta.actualizar_todo(con, AJUSTES, [p["instrumento_id"] for p in _cartera(con)["posiciones"]])
            con.close()
        except Exception:  # noqa: BLE001
            log.exception("fallo en actualización programada")


@asynccontextmanager
async def ciclo(app: FastAPI):
    con = db.conectar()
    db.inicializar(con)
    if AJUSTES.es_demo and not con.execute("SELECT 1 FROM precios WHERE proveedor='demo_sintetico' LIMIT 1").fetchone():
        ingesta.actualizar_todo(con, AJUSTES)
    con.close()
    stop = threading.Event()
    if AJUSTES["app"].get("actualizacion_automatica"):
        threading.Thread(target=_programador, args=(stop,), daemon=True).start()
    yield
    stop.set()


app = FastAPI(title="Terminal de portafolios", version=__version__, docs_url=None, redoc_url=None,
              openapi_url=None, lifespan=ciclo)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(Seguridad)


@app.exception_handler(cartera.ErrorValidacion)
async def _err_val(_: Request, e: cartera.ErrorValidacion):
    return JSONResponse({"error": "Datos no válidos", "errores": e.errores}, status_code=422)


@app.exception_handler(importar.ErrorArchivo)
async def _err_arch(_: Request, e: importar.ErrorArchivo):
    return JSONResponse({"error": str(e)}, status_code=422)


@app.exception_handler(Exception)
async def _err(_: Request, e: Exception):
    log.exception("error no controlado")
    return JSONResponse({"error": "Error interno; revise data/logs/terminal.log"}, status_code=500)


# --------------------------------------------------------------------------------------------
# Perfil
def perfil_actual(con) -> dict:
    fila = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='perfil'").fetchone()
    base = dict(AJUSTES["perfil"])
    return {**base, **json.loads(fila["valor"])} if fila else base


def validar_perfil(p: dict, ids_validos: set[str]) -> dict:
    e = []
    out = {}
    riesgo = str(p.get("riesgo", "")).strip().lower()
    if riesgo not in RIESGOS:
        e.append("riesgo: conservador, moderado o agresivo")
    out["riesgo"] = riesgo

    def num(campo, lo, hi, etiqueta):
        try:
            v = float(str(p.get(campo, "")).replace(",", ""))
        except ValueError:
            e.append(f"{campo}: {etiqueta}")
            return None
        if not lo <= v <= hi:
            e.append(f"{campo}: {etiqueta}")
        return v

    out["horizonte_anios"] = num("horizonte_anios", 0.25, 40, "entre 0.25 y 40 años")
    out["capital"] = num("capital", 0, 1e10, "entre 0 y 10 000 millones")
    out["max_peso_activo"] = num("max_peso_activo", 0.02, 1, "entre 0.02 y 1 (2 % a 100 %)")
    out["max_exposicion_usd"] = num("max_exposicion_usd", 0, 1, "entre 0 y 1")
    esc = str(p.get("escenario", "base")).lower()
    if esc not in ESCENARIOS:
        e.append("escenario: base, adverso o favorable")
    out["escenario"] = esc
    out["incluir_etf_por_confirmar"] = bool(p.get("incluir_etf_por_confirmar", True))
    excl = p.get("excluir") or []
    if not isinstance(excl, list) or len(excl) > 300 or any(str(x) not in ids_validos for x in excl):
        e.append("excluir: lista de identificadores del universo")
    out["excluir"] = [str(x) for x in excl] if isinstance(excl, list) else []
    if e:
        raise cartera.ErrorValidacion(e)
    return out


@app.get("/api/perfil")
def get_perfil(con=Depends(con_db)):
    return {"perfil": perfil_actual(con), "perfiles": AJUSTES["perfiles"], "puntuacion": AJUSTES["puntuacion"],
            "costos": AJUSTES["costos"], "optimizacion": AJUSTES["optimizacion"]}


@app.put("/api/perfil")
async def put_perfil(request: Request, con=Depends(con_db)):
    cuerpo = await request.json()
    ids = set(mercado.instrumentos(con))
    p = validar_perfil(cuerpo if isinstance(cuerpo, dict) else {}, ids)
    antes = perfil_actual(con)
    with db.transaccion(con):
        con.execute("INSERT INTO ajustes_usuario VALUES ('perfil', ?, ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor,"
                    " actualizado_en=excluded.actualizado_en", (json.dumps(p), db.ahora()))
        db.auditar(con, "perfil", "perfil", "cambio", antes=antes, despues=p)
    return {"perfil": p}


# --------------------------------------------------------------------------------------------
# Estado de datos y universo
@app.get("/api/estado")
def estado(con=Depends(con_db)):
    ins = mercado.instrumentos(con)
    activos = [i for i, v in ins.items() if v["estado"] == "activo"]
    cot = mercado.cotizaciones(con, AJUSTES, activos)
    conteo: dict[str, int] = {}
    for q in cot.values():
        conteo[q["estado"]] = conteo.get(q["estado"], 0) + 1
    return {
        "version": __version__, "modo": AJUSTES.modo, "hoy": date.today().isoformat(),
        "ultima_sesion": {"NYSE": vigencia.ultima_sesion_cerrada("XNYS").isoformat(),
                          "BMV": vigencia.ultima_sesion_cerrada("XMEX").isoformat()},
        "mercado_abierto": {"NYSE": vigencia.mercado_abierto("XNYS"), "BMV": vigencia.mercado_abierto("XMEX")},
        "fx": mercado.ultimo_fx(con, AJUSTES), "vigencia": conteo, "instrumentos_activos": len(activos),
        "instrumentos_total": len(ins), "proveedores": ingesta.estado_proveedores(con, AJUSTES),
        "operaciones_reales": False,
    }


@app.get("/api/universo")
def get_universo(con=Depends(con_db)):
    ins = mercado.instrumentos(con)
    cot = mercado.cotizaciones(con, AJUSTES)
    filas = []
    for i, v in ins.items():
        q = cot.get(i, {})
        filas.append({k: v[k] for k in ("id", "clave_operable", "nombre", "clase", "categoria", "mercado_operable",
                                         "moneda_operable", "bolsa_referencia", "moneda_referencia",
                                         "zona_horaria_referencia", "estado", "secciones_pdf", "fuente_verificacion",
                                         "detalle_verificacion", "fecha_verificacion")}
                     | {k: q.get(k) for k in ("precio", "moneda", "precio_mxn", "fecha", "proveedor", "tipo_dato",
                                              "retraso_horas", "sesiones_atraso", "etiqueta", "nota")}
                     | {"vigencia": q.get("estado")})
    return {"instrumentos": filas}


@app.post("/api/datos/actualizar")
def actualizar(con=Depends(con_db)):
    if not _calculo.acquire(blocking=False):
        raise HTTPException(409, "Ya hay una actualización o cálculo en curso")
    try:
        prio = [p["instrumento_id"] for p in _cartera(con)["posiciones"]]
        return {"resultado": ingesta.actualizar_todo(con, AJUSTES, prio)}
    finally:
        _calculo.release()


@app.post("/api/modo")
def cambiar_modo(cuerpo: dict = Body(...)):
    """Cambia entre datos reales y demostración sin reiniciar. Cada modo usa su propia base de datos.
    Al pasar a real se consulta de inmediato a los proveedores configurados para traer datos vigentes."""
    modo = str((cuerpo or {}).get("modo", ""))
    if modo not in MODOS:
        raise cartera.ErrorValidacion(["modo: use «real» o «demo»"])
    if not _calculo.acquire(blocking=False):
        raise HTTPException(409, "Hay una actualización o cálculo en curso; intente en unos segundos")
    try:
        fijar_modo(modo)
        con = db.conectar()
        try:
            db.inicializar(con)
            if modo == "demo":
                hay = con.execute("SELECT 1 FROM precios WHERE proveedor='demo_sintetico' LIMIT 1").fetchone()
                resultado = None if hay else ingesta.actualizar_todo(con, AJUSTES)
            else:
                prio = [p["instrumento_id"] for p in _cartera(con)["posiciones"]]
                resultado = ingesta.actualizar_todo(con, AJUSTES, prio)
            db.auditar(con, "modo", modo, "cambio")
            con.commit()
        finally:
            con.close()
        return {"modo": modo, "actualizacion": resultado}
    finally:
        _calculo.release()


# --------------------------------------------------------------------------------------------
# Cartera y operaciones
def _cartera(con) -> dict:
    tx = cartera.listar(con)
    ids = sorted({t["instrumento_id"] for t in tx if t["instrumento_id"]})
    cot = mercado.cotizaciones(con, AJUSTES, ids) if ids else {}
    precios = {i: (q["precio_mxn"] if q.get("estado") not in ("sin_datos",) else None) for i, q in cot.items()}
    res = cartera.calcular(tx, precios)
    for p in res["posiciones"] + res["cerradas"]:
        q = cot.get(p["instrumento_id"], {})
        p.update({"clave_operable": q.get("clave_operable"), "clase": q.get("clase"), "vigencia": q.get("estado"),
                  "etiqueta_vigencia": q.get("etiqueta"), "fecha_precio": q.get("fecha"), "proveedor": q.get("proveedor"),
                  "tipo_dato": q.get("tipo_dato")})
    estados = [p["vigencia"] for p in res["posiciones"] if p.get("vigencia")]
    res["vigencia"] = vigencia.peor(estados) if estados else ("sin_datos" if res["posiciones"] else "vigente")
    res["n_operaciones"] = len(tx)
    return res


@app.get("/api/cartera")
def get_cartera(con=Depends(con_db)):
    res = _cartera(con)
    tx = cartera.listar(con)
    ids = sorted({t["instrumento_id"] for t in tx if t["instrumento_id"]})
    historia, bench = [], None
    if tx:
        precios = mercado.precios_mxn(con, AJUSTES, ids, ajustados=False) if ids else pd.DataFrame()
        if precios.empty:
            cal = vigencia.calendario("XMEX")
            fechas = cal.sessions_in_range(pd.Timestamp(tx[0]["fecha"]), pd.Timestamp(date.today()))
            precios = pd.DataFrame(index=pd.DatetimeIndex(fechas.tz_localize(None) if fechas.tz else fechas))
        serie = cartera.serie_historica(tx, precios)
        ref_id = AJUSTES["app"]["indice_referencia"]
        ref = mercado.precios_mxn(con, AJUSTES, [ref_id])
        if not serie.empty:
            if ref_id in ref.columns:
                r = ref[ref_id].reindex(serie.index).ffill()
                if r.notna().any():
                    base = r.dropna().iloc[0]
                    serie["referencia"] = r / base - 1
                    bench = {"id": ref_id, "rend_acumulado": float(serie["referencia"].dropna().iloc[-1])}
            historia = [{"fecha": d.date().isoformat(), "valor": round(float(f.valor), 2),
                         "twr": round(float(f.twr_acumulado), 6), "completo": bool(f.completo),
                         "referencia": (None if pd.isna(f.get("referencia", float("nan"))) else round(float(f.referencia), 6))}
                        for d, f in serie.iterrows()]
            flujos = [(pd.Timestamp(t["fecha"]), -(1 if t["tipo"] == "aportacion" else -1) * t["monto"] * t["tipo_cambio"])
                      for t in tx if t["tipo"] in ("aportacion", "retiro")]
            if res["completa"] and flujos:
                flujos.append((serie.index[-1], float(serie["valor"].iloc[-1])))
                res["tir_anual"] = cartera.xirr(sorted(flujos, key=lambda x: x[0]))
            res["twr_acumulado"] = float(serie["twr_acumulado"].iloc[-1])
    res["historia"] = historia[-1500:]
    res["referencia"] = bench
    return res


@app.get("/api/transacciones")
def get_tx(anuladas: bool = False, con=Depends(con_db)):
    return {"transacciones": cartera.listar(con, incluir_anuladas=anuladas)}


@app.post("/api/transacciones")
async def post_tx(request: Request, con=Depends(con_db)):
    cuerpo = await request.json()
    t = cartera.validar(cuerpo if isinstance(cuerpo, dict) else {}, mercado.instrumentos(con))
    with db.transaccion(con):
        tid = cartera.registrar(con, t, "manual", ocurrencia=int(con.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]) + 1)
    return {"id": tid, "transaccion": t}


@app.post("/api/transacciones/{tid}/anular")
async def anular_tx(tid: int, request: Request, con=Depends(con_db)):
    cuerpo = await request.json()
    cartera.anular(con, tid, str((cuerpo or {}).get("motivo", ""))[:200])
    return {"ok": True}


@app.post("/api/transacciones/{tid}/corregir")
async def corregir_tx(tid: int, request: Request, con=Depends(con_db)):
    cuerpo = await request.json()
    if not isinstance(cuerpo, dict):
        raise cartera.ErrorValidacion(["Cuerpo no válido"])
    nuevos = {k: cuerpo[k] for k in cartera.CAMPOS if k in cuerpo}
    nid = cartera.corregir(con, tid, nuevos, mercado.instrumentos(con), str(cuerpo.get("motivo", ""))[:200])
    return {"id": nid}


@app.get("/api/auditoria")
def get_auditoria(limite: int = 200, con=Depends(con_db)):
    filas = con.execute("SELECT * FROM auditoria ORDER BY id DESC LIMIT ?", (max(1, min(limite, 1000)),))
    return {"eventos": [dict(f) for f in filas]}


@app.post("/api/importar")
async def post_importar(archivo: UploadFile = File(...), tipo: str = Form(...), confirmar: str = Form("no"),
                        con=Depends(con_db)):
    contenido = await archivo.read(importar.MAX_BYTES + 1)
    rep = importar.importar(con, contenido, archivo.filename or "", tipo, mercado.instrumentos(con),
                            confirmar=confirmar == "si")
    return rep


@app.get("/api/plantilla/{tipo}")
def plantilla(tipo: str):
    if tipo not in importar.COLUMNAS:
        raise HTTPException(404, "Plantilla no encontrada")
    return PlainTextResponse(importar.plantilla(tipo), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="plantilla_{tipo}.csv"'})


# --------------------------------------------------------------------------------------------
# Propuestas
def _revalidar(p: dict, perfil: dict) -> dict:
    """Una propuesta guardada nunca se presenta como actual si sus datos o el perfil cambiaron."""
    avisos = []
    if p.get("estado") in ("calculada", "demostracion"):
        if p.get("perfil") != perfil:
            avisos.append("El perfil cambió desde el cálculo: recalcule para ver la propuesta vigente.")
        if p["estado"] == "calculada" and p.get("datos_hasta"):
            atraso = vigencia.sesiones_de_atraso("XNYS", date.fromisoformat(p["datos_hasta"]),
                                                 vigencia.ultima_sesion_cerrada("XNYS"))
            if atraso > AJUSTES["vigencia"]["cierre_sesiones_retrasado"]:
                avisos.append(f"Calculada con datos al {p['datos_hasta']} ({atraso} sesiones de atraso): no es actual.")
                p = {**p, "estado": "desactualizada"}
    return {**p, "avisos": avisos}


@app.get("/api/propuestas")
def get_propuestas(con=Depends(con_db)):
    perfil = perfil_actual(con)
    out = {}
    for tipo in ("acciones", "mixta"):
        f = con.execute("SELECT resultado FROM propuestas WHERE tipo=? ORDER BY id DESC LIMIT 1", (tipo,)).fetchone()
        out[tipo] = _revalidar(json.loads(f["resultado"]), perfil) if f else None
    presentes = [v for v in out.values() if v]
    out["clasificacion"] = optimizador.clasificar(presentes, {}) if presentes else []
    return out


@app.post("/api/propuestas/calcular")
def calcular(con=Depends(con_db)):
    if not _calculo.acquire(blocking=False):
        raise HTTPException(409, "Ya hay un cálculo en curso")
    try:
        perfil = perfil_actual(con)
        actual = _cartera(con)
        ids = [i for i, v in mercado.instrumentos(con).items() if v["estado"] == "activo"]
        cot = mercado.cotizaciones(con, AJUSTES, ids)
        res = {}
        for tipo in ("acciones", "mixta"):
            p = optimizador.proponer(con, AJUSTES, perfil, tipo, actual, cot)
            with db.transaccion(con):
                con.execute("INSERT INTO propuestas (tipo, creado_en, parametros, resultado) VALUES (?,?,?,?)",
                            (tipo, p["calculado_en"], json.dumps(perfil), json.dumps(p, default=str)))
            res[tipo] = _revalidar(json.loads(json.dumps(p, default=str)), perfil)
        res["clasificacion"] = optimizador.clasificar([res["acciones"], res["mixta"]], actual)
        return res
    finally:
        _calculo.release()


# --------------------------------------------------------------------------------------------
# Interfaz
@app.get("/", response_class=HTMLResponse)
def index():
    html = (WEB / "index.html").read_text(encoding="utf-8").replace("__CSRF__", TOKEN_CSRF)
    return HTMLResponse(html)


@app.get("/salud")
def salud():
    return {"ok": True}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"  # herramienta privada: nada debe indexarse


app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


@app.exception_handler(404)
async def no_encontrado(request: Request, _):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Ruta no encontrada"}, status_code=404)
    return HTMLResponse((WEB / "404.html").read_text(encoding="utf-8"), status_code=404)


def _ruta_log() -> Path:
    p = db.ruta_db().parent / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p / "terminal.log"
