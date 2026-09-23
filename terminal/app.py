"""Servidor local (FastAPI). Solo informa y simula: no existe ninguna ruta que envíe órdenes."""
from __future__ import annotations

import html
import json
import logging
import os
import re
import threading
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, alertas, cartera, db, importar, ingesta, mercado, notificador, reto, servicios, tiempo_real, vigencia
from .config import MODOS, RAIZ, cargar_ajustes, fijar_modo
from .seguridad import TOKEN_CSRF, Seguridad

logging.getLogger("httpx").setLevel(logging.WARNING)  # evita registrar URLs con credenciales
log = logging.getLogger("terminal")
WEB = RAIZ / "web"
AJUSTES = cargar_ajustes()

RIESGOS = ("conservador", "moderado", "agresivo")
ESCENARIOS = ("base", "adverso", "favorable")


def con_db():
    con = db.conectar()
    try:
        yield con
    finally:
        con.close()


def disparar_motor(forzar: bool = True) -> None:
    """Recalcula en segundo plano tras un cambio (operación, importación, perfil). No bloquea la respuesta."""
    if os.environ.get("TERMINAL_SIN_MOTOR"):
        return
    threading.Thread(target=servicios.ciclo_seguro, args=(AJUSTES, forzar), daemon=True).start()


FLUJO: tiempo_real.FlujoVivo | None = None  # precios en vivo de EE. UU. (Alpaca IEX); None si el motor está apagado


def _programador(stop: threading.Event) -> None:
    """Motor automático: adquiere datos (respetando límites), recalcula si hay datos nuevos y evalúa alertas.
    Entre ciclos completos, si el flujo en vivo trae precios que se movieron, recalcula sin consultar proveedores."""
    import time
    prog = AJUSTES["programacion"]
    siguiente = time.monotonic() + 5  # primer ciclo pocos segundos después de arrancar
    while not stop.wait(15):
        ahora = time.monotonic()
        if ahora >= siguiente:
            if servicios.ciclo_seguro(AJUSTES) is not None and FLUJO:
                FLUJO.marcar_recalculo()
            abierto = vigencia.mercado_abierto("XMEX") or vigencia.mercado_abierto("XNYS")
            siguiente = time.monotonic() + int(prog["revisar_cada_min"] if abierto else prog["fuera_horario_min"]) * 60
        elif FLUJO and FLUJO.debe_recalcular():
            if servicios.ciclo_seguro(AJUSTES, forzar=True, en_vivo=True) is not None:
                FLUJO.marcar_recalculo()


@asynccontextmanager
async def vida(app: FastAPI):
    con = db.conectar()
    db.inicializar(con)
    if AJUSTES.es_demo and not con.execute("SELECT 1 FROM precios WHERE proveedor='demo_sintetico' LIMIT 1").fetchone():
        ingesta.actualizar_todo(con, AJUSTES)
    con.close()
    global FLUJO
    stop = threading.Event()
    if AJUSTES["app"].get("actualizacion_automatica") and not os.environ.get("TERMINAL_SIN_MOTOR"):
        FLUJO = tiempo_real.FlujoVivo(AJUSTES)
        FLUJO.iniciar()
        threading.Thread(target=_programador, args=(stop,), daemon=True).start()
    yield
    stop.set()
    if FLUJO:
        FLUJO.detener()


app = FastAPI(title="Actinver Terminal", version=__version__, docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=vida)
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


def _ocupado():
    return HTTPException(409, "Hay una actualización o cálculo en curso; intente en unos segundos")


# ------------------------------------------------------------------------------------------------------------
# Perfil y Reto
def validar_perfil(p: dict, ids_validos: set[str]) -> dict:
    e, out = [], {}
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

    out["horizonte_anios"] = num("horizonte_anios", 0.02, 40, "entre 0.02 y 40 años")
    out["horizonte_reto"] = bool(p.get("horizonte_reto", True))
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
    from .optimizador import perfil_efectivo
    p = servicios.perfil_actual(con, AJUSTES)
    return {"perfil": p, "perfil_efectivo": perfil_efectivo(p), "perfiles": AJUSTES["perfiles"],
            "puntuacion": AJUSTES["puntuacion"], "costos": AJUSTES["costos"], "optimizacion": AJUSTES["optimizacion"],
            "alertas": AJUSTES["alertas"]}


@app.put("/api/perfil")
def put_perfil(cuerpo: dict = Body(...), con=Depends(con_db)):
    p = validar_perfil(cuerpo if isinstance(cuerpo, dict) else {}, set(mercado.instrumentos(con)))
    antes = servicios.perfil_actual(con, AJUSTES)
    with db.transaccion(con):
        con.execute("INSERT INTO ajustes_usuario VALUES ('perfil', ?, ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor,"
                    " actualizado_en=excluded.actualizado_en", (json.dumps(p), db.ahora()))
        db.auditar(con, "perfil", "perfil", "cambio", antes=antes, despues=p)
    disparar_motor()
    return {"perfil": p}


@app.get("/api/reto")
def get_reto(con=Depends(con_db)):
    r = reto.resumen()
    if r.get("activo"):
        hechas = {f["id"]: bool(f["hecha"]) for f in con.execute("SELECT id, hecha FROM tareas_reto")}
        r["tareas"] = [{**t, "hecha": hechas.get(t["id"], False)} for t in r["tareas"]]
        r["universo_simulador"] = int(con.execute("SELECT COUNT(*) FROM universo_simulador").fetchone()[0])
    return r


@app.put("/api/reto/tareas/{tid}")
def put_tarea(tid: str, cuerpo: dict = Body(...), con=Depends(con_db)):
    if tid not in {t["id"] for t in reto.config().get("tareas", [])}:
        raise HTTPException(404, "Tarea no encontrada")
    with db.transaccion(con):
        con.execute("INSERT INTO tareas_reto VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET hecha=excluded.hecha, "
                    "actualizado_en=excluded.actualizado_en", (tid, int(bool(cuerpo.get("hecha"))), db.ahora()))
    return {"id": tid, "hecha": bool(cuerpo.get("hecha"))}


# ------------------------------------------------------------------------------------------------------------
# Estado de datos, universo y motor
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
        "motor": servicios.estado_motor(con), "alertas_pendientes": alertas.pendientes(con),
        "tiempo_real": FLUJO.resumen() if FLUJO else {"activo": False, "modo": "apagado",
                                                        "mensaje": "Motor automático desactivado"},
        "notificaciones": notificador.configurados(), "operaciones_reales": False,
    }


@app.get("/api/universo")
def get_universo(con=Depends(con_db)):
    ins = mercado.instrumentos(con)
    cot = mercado.cotizaciones(con, AJUSTES)
    sim = {r[0] for r in con.execute("SELECT id FROM universo_simulador")}
    filas = []
    for i, v in ins.items():
        q = cot.get(i, {})
        filas.append({k: v[k] for k in ("id", "clave_operable", "nombre", "clase", "categoria", "mercado_operable",
                                         "moneda_operable", "bolsa_referencia", "moneda_referencia",
                                         "zona_horaria_referencia", "estado", "secciones_pdf", "fuente_verificacion",
                                         "detalle_verificacion", "fecha_verificacion")}
                     | {k: q.get(k) for k in ("precio", "moneda", "precio_mxn", "fecha", "proveedor", "tipo_dato",
                                              "retraso_horas", "sesiones_atraso", "etiqueta", "nota")}
                     | {"vigencia": q.get("estado"), "en_simulador": (i in sim) if sim else None,
                        "grafica": simbolo_tradingview(v)})
    return {"instrumentos": filas}


@app.post("/api/datos/actualizar")
def actualizar(con=Depends(con_db)):
    if not servicios.bloqueo.acquire(blocking=False):
        raise _ocupado()
    try:
        return {"resultado": servicios.ciclo(con, AJUSTES)}
    finally:
        servicios.bloqueo.release()


@app.post("/api/modo")
def cambiar_modo(cuerpo: dict = Body(...)):
    """Cambia entre datos reales y demostración sin reiniciar. Cada modo usa su propia base de datos.
    Al pasar a real se consulta de inmediato a los proveedores configurados para traer datos vigentes."""
    modo = str((cuerpo or {}).get("modo", ""))
    if modo not in MODOS:
        raise cartera.ErrorValidacion(["modo: use «real» o «demo»"])
    if not servicios.bloqueo.acquire(blocking=False):
        raise _ocupado()
    try:
        fijar_modo(modo)
        con = db.conectar()
        try:
            db.inicializar(con)
            if modo == "demo":
                hay = con.execute("SELECT 1 FROM precios WHERE proveedor='demo_sintetico' LIMIT 1").fetchone()
                resultado = None if hay else ingesta.actualizar_todo(con, AJUSTES)
            else:
                prio = [p["instrumento_id"] for p in servicios.cartera_actual(con, AJUSTES)["posiciones"]]
                resultado = ingesta.actualizar_todo(con, AJUSTES, prio)
            db.auditar(con, "modo", modo, "cambio")
            con.commit()
        finally:
            con.close()
    finally:
        servicios.bloqueo.release()
    disparar_motor()
    return {"modo": modo, "actualizacion": resultado}


# ------------------------------------------------------------------------------------------------------------
# Cartera y operaciones
@app.get("/api/cartera")
def get_cartera(con=Depends(con_db)):
    return servicios.seguimiento(con, AJUSTES)


@app.get("/api/transacciones")
def get_tx(anuladas: bool = False, con=Depends(con_db)):
    return {"transacciones": cartera.listar(con, incluir_anuladas=anuladas)}


@app.post("/api/transacciones")
def post_tx(cuerpo: dict = Body(...), con=Depends(con_db)):
    t = cartera.validar(cuerpo if isinstance(cuerpo, dict) else {}, mercado.instrumentos(con))
    with db.transaccion(con):
        tid = cartera.registrar(con, t, "manual", ocurrencia=int(con.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]) + 1)
    disparar_motor()
    return {"id": tid, "transaccion": t}


@app.post("/api/transacciones/{tid}/anular")
def anular_tx(tid: int, cuerpo: dict = Body(...), con=Depends(con_db)):
    cartera.anular(con, tid, str((cuerpo or {}).get("motivo", ""))[:200])
    disparar_motor()
    return {"ok": True}


@app.post("/api/transacciones/{tid}/corregir")
def corregir_tx(tid: int, cuerpo: dict = Body(...), con=Depends(con_db)):
    if not isinstance(cuerpo, dict):
        raise cartera.ErrorValidacion(["Cuerpo no válido"])
    nuevos = {k: cuerpo[k] for k in cartera.CAMPOS if k in cuerpo}
    nid = cartera.corregir(con, tid, nuevos, mercado.instrumentos(con), str(cuerpo.get("motivo", ""))[:200])
    disparar_motor()
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
    if rep.get("confirmado"):
        disparar_motor()
    return rep


@app.get("/api/plantilla/{tipo}")
def plantilla(tipo: str):
    if tipo not in importar.COLUMNAS:
        raise HTTPException(404, "Plantilla no encontrada")
    return PlainTextResponse(importar.plantilla(tipo), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="plantilla_{tipo}.csv"'})


# ------------------------------------------------------------------------------------------------------------
# Propuestas, alertas y simulación
@app.get("/api/propuestas")
def get_propuestas(con=Depends(con_db)):
    perfil = servicios.perfil_actual(con, AJUSTES)
    return servicios.respuesta_propuestas(servicios.propuestas_guardadas(con, AJUSTES, perfil))


@app.post("/api/propuestas/calcular")
def calcular(con=Depends(con_db)):
    if not servicios.bloqueo.acquire(blocking=False):
        raise _ocupado()
    try:
        props = servicios.calcular_propuestas(con, AJUSTES)
        alertas.evaluar(con, AJUSTES, servicios.cartera_actual(con, AJUSTES), props)
        return servicios.respuesta_propuestas(props)
    finally:
        servicios.bloqueo.release()


@app.get("/api/alertas")
def get_alertas(limite: int = 200, con=Depends(con_db)):
    return {"alertas": alertas.listar(con, limite), "pendientes": alertas.pendientes(con),
            "configuracion": AJUSTES["alertas"]}


@app.post("/api/notificaciones/prueba")
def probar_notificaciones():
    """Envía un aviso de prueba por los canales configurados (escritorio, Telegram, correo)."""
    cfg = {**AJUSTES["alertas"], "notificar_telegram": True}
    texto = ("Si recibe este mensaje, los avisos de la terminal llegan a este canal. "
             "Solo informativo: las órdenes se capturan a mano en el simulador del Reto.")
    return {"resultado": notificador.enviar("Actinver Terminal — prueba de avisos", texto, cfg)}


@app.post("/api/alertas/{aid}")
def marcar_alerta(aid: int, cuerpo: dict = Body(...), con=Depends(con_db)):
    try:
        alertas.marcar(con, aid, str(cuerpo.get("estado", "")))
    except ValueError:
        raise cartera.ErrorValidacion(["estado: vista, descartada o nueva"]) from None
    return {"ok": True}


@app.post("/api/simular")
def post_simular(cuerpo: dict = Body(...), con=Depends(con_db)):
    cambios = cuerpo.get("cambios") if isinstance(cuerpo, dict) else None
    if not isinstance(cambios, list) or not 0 < len(cambios) <= 100:
        raise cartera.ErrorValidacion(["cambios: lista de 1 a 100 elementos {id, monto}"])
    limpios = []
    for c in cambios:
        try:
            monto = float(c["monto"])
            if abs(monto) > 1e10:
                raise ValueError
            limpios.append({"id": str(c["id"])[:40], "monto": monto})
        except (KeyError, TypeError, ValueError):
            raise cartera.ErrorValidacion(["cambios: cada elemento requiere id y monto numérico"]) from None
    return servicios.simular(con, AJUSTES, limpios)


@app.get("/api/mercado")
def get_mercado(con=Depends(con_db)):
    ids = [p["instrumento_id"] for p in servicios.cartera_actual(con, AJUSTES)["posiciones"]]
    marcas = ",".join("?" * len(ids)) or "''"
    macro = [dict(r) for r in con.execute("SELECT * FROM eventos_macro WHERE impacto IN ('High','Medium') AND "
                                          "pais IN ('USD','MXN') ORDER BY fecha LIMIT 60")]
    noticias = [dict(r) for r in con.execute(f"SELECT * FROM noticias WHERE instrumento_id IN ({marcas}) "  # noqa: S608
                                             "ORDER BY publicado DESC LIMIT 60", ids)]
    insiders = [dict(r) for r in con.execute(f"SELECT * FROM insiders WHERE instrumento_id IN ({marcas}) "  # noqa: S608
                                             "ORDER BY fecha DESC LIMIT 60", ids)]
    return {"macro": macro, "noticias": noticias, "insiders": insiders, "cartera": ids,
            "fuentes": {"macro": "ForexFactory (feed de exportación)", "noticias": "Seeking Alpha (RSS)",
                        "insiders": "SEC EDGAR Formulario 4"}}


# ------------------------------------------------------------------------------------------------------------
# Gráfica: widget oficial de TradingView en una página aislada con su propia CSP
BOLSA_TV = {"NASDAQ": "NASDAQ", "NYSE": "NYSE", "NYSE Arca": "AMEX", "NYSE American": "AMEX", "Cboe BZX": "CBOE",
            "BMV": "BMV"}


def simbolo_tradingview(ins: dict) -> str | None:
    if ins.get("clase", "").startswith("fondo") or ins.get("estado") not in ("activo",):
        return None
    if ins.get("mercado_operable") == "BMV":
        return f"BMV:{ins['clave'].replace('&', '')}{(ins.get('serie') or '').replace('*', '').replace(' ', '')}"
    pref = BOLSA_TV.get(ins.get("bolsa_referencia") or "")
    return f"{pref}:{ins['listado_referencia']}" if pref and ins.get("listado_referencia") else None


CSP_GRAFICA = ("default-src 'none'; script-src https://s3.tradingview.com; style-src 'self' 'unsafe-inline'; "
               "frame-src https://s.tradingview.com https://www.tradingview-widget.com https://*.tradingview.com; "
               "img-src 'self' data: https:; connect-src https://*.tradingview.com; base-uri 'none'; frame-ancestors 'none'")


@app.get("/grafica/{iid}", response_class=HTMLResponse)
def grafica(iid: str, con=Depends(con_db)):
    ins = mercado.instrumentos(con).get(iid)
    sim = simbolo_tradingview(ins) if ins else None
    if not sim or not re.fullmatch(r"[A-Z]{3,6}:[A-Z0-9.&\-]{1,20}", sim):
        raise HTTPException(404, "Instrumento sin gráfica disponible")
    cfg = json.dumps({"autosize": True, "symbol": sim, "interval": "D", "timezone": "America/Mexico_City",
                      "theme": "dark", "style": "1", "locale": "es", "allow_symbol_change": False,
                      "support_host": "https://www.tradingview.com"})
    pagina = f"""<!doctype html><html lang="es-MX"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Gráfica {html.escape(sim)} — Actinver Terminal</title><link rel="icon" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/grafica.css"></head><body>
<header><strong>{html.escape(ins['clave_operable'])}</strong> · {html.escape(sim)} · Widget de TradingView (datos y
retraso según TradingView; pueden diferir del simulador). <a href="/">Volver</a></header>
<div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div>
<script src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>{cfg}</script></div>
</body></html>"""
    return HTMLResponse(pagina, headers={"Content-Security-Policy": CSP_GRAFICA})


# ------------------------------------------------------------------------------------------------------------
# Interfaz
@app.get("/", response_class=HTMLResponse)
def index():
    demo = AJUSTES.es_demo  # se decide en el servidor para que la cabecera no se desplace al cargar
    reemplazos = {"__CSRF__": TOKEN_CSRF, "__OCULTO_DEMO__": "" if demo else "hidden",
                  "__DESTINO__": "real" if demo else "demo", "__CLASE_MODO__": "boton--real" if demo else "",
                  "__TEXTO_MODO__": "Usar datos reales y vigentes" if demo else "Ver demostración"}
    pagina = (WEB / "index.html").read_text(encoding="utf-8")
    for k, v in reemplazos.items():
        pagina = pagina.replace(k, v)
    return HTMLResponse(pagina)


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
