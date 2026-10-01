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

from . import (__version__, alertas, cartera, cotizaciones, db, espacios, importar, ingesta, mercado, notificador, reto,
               registro, servicios, tiempo_real, vigencia, webhook_tv)
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
        servicios.resumen_seguro(AJUSTES)  # plan del día por Telegram a primera hora (una vez por sesión)
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
    bot = None
    if not os.environ.get("TERMINAL_SIN_MOTOR"):
        from .bot_telegram import BotTelegram
        bot = BotTelegram(AJUSTES)
        bot.iniciar()  # solo si TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID están en .env
    yield
    stop.set()
    if bot:
        bot.detener()
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
    mercado_acc = str(p.get("mercado_acciones", "ambos")).lower()
    if mercado_acc not in ("ambos", "nacionales", "extranjeras"):
        e.append("mercado_acciones: ambos, nacionales o extranjeras")
    out["mercado_acciones"] = mercado_acc
    criterio = str(p.get("criterio_plan", "puntuacion")).lower()
    if criterio not in ("puntuacion", "plusvalia"):
        e.append("criterio_plan: puntuacion o plusvalia")
    out["criterio_plan"] = criterio
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
    r["version_reglas"] = registro.estado_reglas(con)
    return r


@app.post("/api/reto/reglas/{version}/revisada")
def reglas_revisadas(version: int, con=Depends(con_db)):
    registro.marcar_reglas_revisadas(con, version)
    db.auditar(con, "reglas", version, "revisada")
    con.commit()
    return registro.estado_reglas(con)


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


@app.post("/api/fondos/hoja")
async def post_hoja_fondos(archivo: UploadFile | None = File(None), confirmar: str = Form("si"), con=Depends(con_db)):
    """Hoja oficial de precios de los fondos Actinver: PDF subido por el participante o, sin archivo, la descarga
    pública de actinver.com. Solo asigna fondo y serie exactos con la fecha de valuación del documento."""
    from . import fondos_actinver as fa
    try:
        if archivo is not None:
            contenido = await archivo.read(5_000_001)
            if len(contenido) > 5_000_000:
                raise cartera.ErrorValidacion(["El PDF excede 5 MB."])
            rep = fa.importar(con, contenido, archivo.filename or "hoja.pdf", confirmar=confirmar == "si")
        else:
            rep = fa.actualizar(con, AJUSTES)
    except fa.ErrorHoja as e:
        raise cartera.ErrorValidacion([str(e)]) from None
    if rep.get("confirmado") or rep.get("estado") == "ok":
        disparar_motor()
    return rep


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
    from . import importar_contexto
    if tipo not in importar.COLUMNAS and tipo not in importar_contexto.COLUMNAS:
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


# ------------------------------------------------------------------------------------------------------------
# PASADO / PRESENTE / FUTURO
@app.get("/api/pasado")
def get_pasado(con=Depends(con_db)):
    return espacios.pasado(con, AJUSTES)


@app.get("/api/presente")
def get_presente(con=Depends(con_db)):
    return espacios.presente(con, AJUSTES)


@app.get("/api/futuro")
def get_futuro(con=Depends(con_db)):
    return espacios.futuro(con, AJUSTES)


INVESTIGACION = {"estado": "inactivo", "inicio": None, "fin": None, "resultado": None}
_bloqueo_inv = threading.Lock()


def _investigar(horizontes: list[int]) -> None:
    from .investigacion import reto_pronostico
    con = db.conectar()
    try:
        INVESTIGACION["resultado"] = [{k: v for k, v in r.items() if not k.startswith("_")}
                                      for r in reto_pronostico.emitir_todo(con, AJUSTES.es_demo, horizontes)]
        INVESTIGACION["estado"] = "terminado"
    except Exception as e:  # noqa: BLE001
        log.exception("fallo en investigación")
        INVESTIGACION.update(estado="error", resultado=type(e).__name__)
    finally:
        INVESTIGACION["fin"] = db.ahora()
        con.close()
        _bloqueo_inv.release()


@app.post("/api/investigacion/calcular")
def calcular_investigacion(cuerpo: dict = Body(default={})):
    """Corre el experimento (walk-forward → validación → prueba) y emite pronósticos a 1 y 5 sesiones y al cierre del
    Reto. En segundo plano (unos minutos)."""
    horizontes = [int(h) for h in ((cuerpo or {}).get("horizontes") or AJUSTES.get("investigacion", {}).get("horizontes", [1, 5]))
                  if 1 <= int(h) <= 20][:3]
    if not _bloqueo_inv.acquire(blocking=False):
        raise _ocupado()
    INVESTIGACION.update(estado="calculando", inicio=db.ahora(), fin=None, resultado=None)
    threading.Thread(target=_investigar, args=(horizontes,), daemon=True).start()
    return {"estado": "calculando", "horizontes": horizontes}


@app.get("/api/investigacion/estado")
def estado_investigacion():
    return INVESTIGACION


@app.get("/api/pronostico")
def get_pronostico(con=Depends(con_db)):
    from .investigacion import reto_pronostico
    r = reto_pronostico.construir(con, AJUSTES)
    return {**r, "texto": reto_pronostico.texto(r)}


@app.post("/api/pronostico/telegram")
def pronostico_telegram(cuerpo: dict = Body(default={}), con=Depends(con_db)):
    """Envía el resumen del pronóstico por Telegram (o solo lo devuelve con enviar=false). No envía órdenes."""
    from . import notificador
    from .investigacion import reto_pronostico
    texto = reto_pronostico.texto(reto_pronostico.construir(con, AJUSTES))
    if cuerpo.get("enviar", True) is False:
        return {"resultado": None, "texto": texto}
    cfg = {**AJUSTES["alertas"], "notificar_escritorio": False, "notificar_telegram": True, "notificar_correo": False}
    return {"resultado": notificador.enviar("🔮 Pronóstico (estimación)", texto, cfg, detalle=texto), "texto": texto}


# ------------------------------------------------------------------------------------------------------------
# Cobertura por símbolo, saldo del portal y webhook de TradingView
@app.get("/api/cobertura")
def get_cobertura(con=Depends(con_db)):
    provs = cotizaciones.construir(con, AJUSTES.es_demo)
    return {"tabla": cotizaciones.tabla_cobertura(con, provs), "proveedores": [p.estado() for p in provs.values()],
            "latencias": cotizaciones.latencias_medidas(con),
            "catalogo_simulador_importado": bool(con.execute("SELECT 1 FROM universo_simulador LIMIT 1").fetchone()),
            "webhook_tradingview": {"configurado": webhook_tv.TradingViewAlertReceiver(con).configurado(),
                                    "plantilla": webhook_tv.plantilla_mensaje()}}


@app.post("/api/cobertura/verificar")
def verificar_cobertura(con=Depends(con_db)):
    provs = cotizaciones.construir(con, AJUSTES.es_demo)
    filas = cotizaciones.verificar_cobertura(con, provs, cotizaciones.catalogo(con))
    conteo: dict[str, dict[str, int]] = {}
    for f in filas:
        conteo.setdefault(f["proveedor"], {}).setdefault(f["estado"], 0)
        conteo[f["proveedor"]][f["estado"]] += 1
    return {"resumen": conteo}


@app.get("/api/estado-informacion")
def get_estado_informacion(con=Depends(con_db)):
    """Qué está confirmado, estimado, vencido o falta, con la acción concreta (para personas no técnicas)."""
    from . import estado_info
    return estado_info.calcular(con, AJUSTES)


@app.get("/api/plan-accion")
def get_plan_accion(con=Depends(con_db)):
    """Plan de acción por instrumento (comprar, vender, mantener o decisión pendiente), el mismo que resume Telegram."""
    from . import plan_accion, resumen
    perfil = servicios.perfil_actual(con, AJUSTES)
    props = servicios.propuestas_guardadas(con, AJUSTES, perfil)
    ref = resumen.propuesta_referencia(props)
    plan = plan_accion.calcular(con, AJUSTES, propuesta=ref)
    plan["propuestas_texto"] = resumen.bloque_propuestas(props, ref) if ref else []
    return plan


@app.get("/api/portal/captura")
def get_captura_portal(con=Depends(con_db)):
    """Última captura del portal del Reto (la que el participante pegó), con sus cambios frente a la anterior."""
    from . import portal
    c = portal.captura(con)
    if not c:
        return {"captura": None, "cambios": [], "vigente": False,
                "aviso": "Sin captura del portal: «Mi portafolio Actinver» muestra el registro local de la terminal."}
    return {"captura": c, "cambios": portal.cambios(portal.anterior(con, c), c),
            "vigente": servicios.captura_vigente(con) is not None, "fuente": portal.FUENTE}


@app.post("/api/portal/captura")
def post_captura_portal(cuerpo: dict = Body(...), con=Depends(con_db)):
    """Vista previa o registro de lo que el participante copió de su cuenta del Reto (la terminal no entra al portal)."""
    from . import portal

    def num(k):
        v = cuerpo.get(k)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            raise cartera.ErrorValidacion([f"{k}: número"]) from None
    try:
        r = portal.guardar(con, str(cuerpo.get("texto") or ""), str(cuerpo.get("hora_portal") or ""),
                           mercado.instrumentos(con), efectivo=num("efectivo"), valor_portafolio=num("valor_portafolio"),
                           confirmar=bool(cuerpo.get("confirmar")), por_liquidar=num("por_liquidar"))
    except portal.ErrorCaptura as e:
        raise cartera.ErrorValidacion([str(e)]) from None
    if r.get("confirmado"):
        disparar_motor()
    else:  # vista previa: qué cambiaría frente a la última captura y frente al registro local
        r["diferencias"] = portal.diferencias(con, AJUSTES, r)
    return r


@app.post("/api/portal/capturas-imagen")
async def post_capturas_imagen(imagenes: list[UploadFile] = File(...), con=Depends(con_db)):
    """Capturas de pantalla del portafolio → texto para la vista previa. OCR de Windows en esta PC; las imágenes se
    procesan en memoria y no se guardan. No registra nada: el participante revisa y confirma en la vista previa."""
    from starlette.concurrency import run_in_threadpool
    from . import ocr_portal
    if not 1 <= len(imagenes) <= ocr_portal.MAX_IMAGENES:
        raise cartera.ErrorValidacion([f"Suba entre 1 y {ocr_portal.MAX_IMAGENES} capturas."])
    ins = mercado.instrumentos(con)
    resultados, avisos = [], []
    for n, im in enumerate(imagenes, 1):
        data = await im.read(ocr_portal.LIMITE_BYTES + 1)
        try:
            resultados.append(await run_in_threadpool(ocr_portal.leer_captura, data, ins))
        except ocr_portal.ErrorImagen as e:
            avisos.append(f"Captura {n}: {e}")
        except ocr_portal.OcrNoDisponible as e:
            raise HTTPException(status_code=501, detail=str(e)) from None
    out = ocr_portal.texto_para_captura(resultados)
    out.update(avisos=avisos + out["avisos"], imagenes=len(resultados))
    return out


@app.post("/api/saldo-portal")
def post_saldo_portal(cuerpo: dict = Body(...), con=Depends(con_db)):
    """El participante copia a mano el valor y el efectivo que muestra el portal (la terminal no entra al portal)."""
    errores = []
    try:
        valor = float(cuerpo.get("valor_portafolio"))
        if not (0 < valor < 1e10):
            raise ValueError
    except (TypeError, ValueError):
        errores.append("valor_portafolio: número positivo")
        valor = 0
    montos = {}
    for campo in ("efectivo", "invertido", "por_liquidar"):  # opcionales: poder de compra, inversiones, por liquidar
        v = cuerpo.get(campo)
        try:
            montos[campo] = None if v in (None, "") else float(v)
        except (TypeError, ValueError):
            errores.append(f"{campo}: número")
    hora = str(cuerpo.get("hora_portal") or db.ahora())[:40]
    if errores:
        raise cartera.ErrorValidacion(errores)
    cur = con.execute("INSERT INTO saldos_portal (capturado_en, hora_portal, etapa, valor_portafolio, efectivo, invertido, "
                      "por_liquidar, nota) VALUES (?,?,?,?,?,?,?,?)",
                      (db.ahora(), hora, reto.etapa_operativa(), valor, montos["efectivo"], montos["invertido"],
                       montos["por_liquidar"], str(cuerpo.get("nota") or "")[:200]))
    db.auditar(con, "saldo_portal", cur.lastrowid, "alta", despues={"valor": valor, **montos, "hora": hora})
    con.commit()
    disparar_motor(False)
    return {"id": cur.lastrowid}


# ------------------------------------------------------------------------------------------------------------
# Órdenes pendientes (solo referencia) y bitácora de decisiones humanas
@app.get("/api/pendientes-portal")
def get_ordenes(todas: bool = False, con=Depends(con_db)):
    return {"ordenes": registro.ordenes(con, not todas),
            "nota": "Referencia de órdenes capturadas por usted en el portal. No cambian posiciones ni efectivo: solo una "
                    "operación CONFIRMADA registrada en «Mi portafolio Actinver» lo hace. La terminal no envía órdenes."}


@app.post("/api/pendientes-portal")
def post_orden(cuerpo: dict = Body(...), con=Depends(con_db)):
    iid = str(cuerpo.get("instrumento_id") or "")
    if iid not in mercado.instrumentos(con):
        raise cartera.ErrorValidacion(["instrumento_id: no está en el universo"])
    try:
        oid = registro.registrar_orden_pendiente(con, iid, str(cuerpo.get("lado")), str(cuerpo.get("tipo_orden", "limitada")),
                                                 float(cuerpo.get("cantidad") or 0),
                                                 float(cuerpo["precio_limite"]) if cuerpo.get("precio_limite") else None,
                                                 str(cuerpo.get("nota") or ""))
    except (TypeError, ValueError):
        raise cartera.ErrorValidacion(["lado compra/venta, tipo mercado/limitada y cantidad positiva"]) from None
    return {"id": oid}


@app.post("/api/pendientes-portal/{oid}")
def cerrar_orden(oid: int, cuerpo: dict = Body(...), con=Depends(con_db)):
    try:
        registro.cerrar_orden(con, oid, str(cuerpo.get("estado")), cuerpo.get("transaccion_id"))
    except ValueError:
        raise cartera.ErrorValidacion(["estado: ejecutada, cancelada o expirada"]) from None
    return {"ok": True}


@app.get("/api/bitacora")
def get_bitacora(con=Depends(con_db)):
    return {"entradas": registro.bitacora(con)}


@app.post("/api/bitacora")
def post_bitacora(cuerpo: dict = Body(...), con=Depends(con_db)):
    tipo = str(cuerpo.get("tipo") or "tesis")
    if tipo not in ("tesis", "entrada", "salida", "revision", "error", "leccion"):
        raise cartera.ErrorValidacion(["tipo: tesis, entrada, salida, revision, error o leccion"])
    fuentes = [str(f)[:300] for f in (cuerpo.get("fuentes") or []) if str(f).startswith("https://")][:10]
    try:
        i = registro.registrar_decision(con, tipo, str(cuerpo.get("decision_humana") or ""), cuerpo.get("instrumento_id") or None,
                                        str(cuerpo.get("tesis") or ""), fuentes, cuerpo.get("alerta_id"),
                                        cuerpo.get("transaccion_id"), str(cuerpo.get("resultado") or ""))
    except ValueError as e:
        raise cartera.ErrorValidacion([str(e)]) from None
    return {"id": i}


# ------------------------------------------------------------------------------------------------------------
# Boletas de decisión (para captura MANUAL en el portal; nunca se envían)
@app.get("/api/boletas")
def get_boletas(con=Depends(con_db)):
    from . import boleta
    return {"boletas": boleta.listar(con, AJUSTES, recalcular_vigentes=True),
            "aviso": "Cada boleta vigente se recalculó justo ahora. Una boleta no es una orden: usted la captura en el portal."}


@app.post("/api/boletas/generar")
def generar_boletas(cuerpo: dict = Body(default={}), con=Depends(con_db)):
    from . import boleta
    clave = str((cuerpo or {}).get("propuesta") or "acciones_ajuste")
    try:
        return {"resultado": boleta.generar(con, AJUSTES, clave)}
    except ValueError as e:
        raise cartera.ErrorValidacion([str(e)]) from None


@app.post("/api/boletas/telegram")
def boletas_telegram(cuerpo: dict = Body(default={}), con=Depends(con_db)):
    """Boletas por Telegram desde la terminal. generar=true crea antes las del plan del día (reemplaza las vigentes);
    enviar=false solo devuelve el texto (vista previa). Nada de esto envía órdenes al portal."""
    from . import boleta
    if cuerpo.get("generar"):
        try:
            boleta.generar(con, AJUSTES, boleta.PLAN_DEL_DIA)
        except ValueError as e:
            raise cartera.ErrorValidacion([f"No se generaron boletas: {e}"]) from None
    lista = boleta.listar(con, AJUSTES, recalcular_vigentes=True)
    vig = [b for b in lista if b.get("estado") == "vigente"]
    conteo = {"listas": sum(1 for b in vig if b["tipo"] in ("considerar compra", "considerar venta") and b.get("cantidad")),
              "condicionales": sum(1 for b in vig if b.get("referencia_condicional")),
              "por_investigar": sum(1 for b in vig if b["tipo"] == "investigar" and not b.get("referencia_condicional"))}
    texto = boleta.texto_telegram(lista)
    if cuerpo.get("enviar", True) is False:
        return {"resultado": None, "texto": texto, "conteo": conteo}
    from . import notificador
    cfg = {**AJUSTES["alertas"], "notificar_escritorio": False, "notificar_telegram": True, "notificar_correo": False}
    return {"resultado": notificador.enviar("🧾 Boletas para capturar", texto, cfg, detalle=texto), "texto": texto,
            "conteo": conteo}


@app.post("/api/boletas/{bid}/recalcular")
def recalcular_boleta(bid: int, con=Depends(con_db)):
    from . import boleta
    try:
        return boleta.recalcular(con, AJUSTES, bid)
    except ValueError as e:
        raise cartera.ErrorValidacion([str(e)]) from None


@app.post("/api/boletas/{bid}/descartar")
def descartar_boleta(bid: int, cuerpo: dict = Body(default={}), con=Depends(con_db)):
    from . import boleta
    boleta.descartar(con, bid, str((cuerpo or {}).get("motivo") or ""))
    return {"ok": True}


@app.post("/api/boletas/{bid}/ejecutada")
def boleta_ejecutada(bid: int, cuerpo: dict = Body(...), con=Depends(con_db)):
    """El participante declara la ejecución CONFIRMADA en el portal (folio, cantidad y precio reales)."""
    from . import boleta
    try:
        tid = boleta.marcar_ejecutada(con, bid, str(cuerpo.get("folio") or ""), str(cuerpo.get("fecha") or ""),
                                      float(cuerpo.get("cantidad") or 0), float(cuerpo.get("precio") or 0),
                                      cuerpo.get("comision"), cuerpo.get("impuesto"))
    except (ValueError, TypeError) as e:
        errores = getattr(e, "errores", None) or [str(e)]
        raise cartera.ErrorValidacion(errores) from None
    disparar_motor()
    return {"transaccion_id": tid}


@app.get("/api/ranking")
def get_ranking(mercado_filtro: str = "ambos", con=Depends(con_db)):
    from . import ranking
    if mercado_filtro not in ("ambos", "nacionales", "extranjeras"):
        raise cartera.ErrorValidacion(["mercado_filtro: ambos, nacionales o extranjeras"])
    return ranking.calcular(con, AJUSTES, mercado_filtro)


@app.post("/webhook/tradingview")
async def webhook_tradingview(request: Request):
    cuerpo = await request.body()
    con = db.conectar()
    try:
        r = webhook_tv.TradingViewAlertReceiver(con, verificar_ip=bool(os.environ.get("TRADINGVIEW_VERIFICAR_IP"))).recibir(
            cuerpo, request.client.host if request.client else None)
    except webhook_tv.WebhookRechazado as e:
        return JSONResponse({"error": str(e)}, status_code=e.codigo)
    finally:
        con.close()
    if not r.get("duplicado"):
        disparar_motor(False)
    return r


@app.post("/api/resumen/muestra")
def muestra_resumen(con=Depends(con_db)):
    """Envía ahora por Telegram una MUESTRA del plan del día con los datos actuales (no cuenta como el envío diario)."""
    from . import resumen
    perfil = servicios.perfil_actual(con, AJUSTES)
    return resumen.enviar_muestra(con, AJUSTES, servicios.cartera_actual(con, AJUSTES),
                                  servicios.propuestas_guardadas(con, AJUSTES, perfil))


@app.post("/api/notificaciones/prueba")
def probar_notificaciones():
    """Envía un aviso de prueba por los canales configurados (escritorio, Telegram, correo)."""
    cfg = {**AJUSTES["alertas"], "notificar_telegram": True}
    texto = ("Si recibe este mensaje, los avisos de la terminal llegan a este canal. "
             "Solo informativo: las órdenes se capturan a mano en el simulador del Reto.")
    ejemplo = [{"severidad": "info", "titulo": "PRUEBA — así se ve una alerta de la terminal",
                "motivo": "Cambio detectado: (ejemplo) Efectivo 1,000,000.00 → 912,250.00. " + texto,
                "accion": "Nada que hacer: es una prueba de entrega.", "fuente": "prueba de canales de la terminal",
                "ts": db.ahora()}]
    return {"resultado": notificador.enviar("Actinver Terminal — prueba de avisos", texto, cfg,
                                            detalle=notificador.detalle(ejemplo))}


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
