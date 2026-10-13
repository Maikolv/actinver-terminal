"""Orquestación de velas, Order Flow y Option Flow: consulta a proveedores bajo demanda (con límite por símbolo),
guarda con procedencia y arma las respuestas de la API. No hay procesos persistentes: solo se consulta cuando el
usuario pulsa «Actualizar» en un panel.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from .. import db
from . import almacen, calculos
from .adaptadores import Alpaca, Cripto, FuenteNoDisponible, tasa_libre_riesgo
from .contratos import INTERVALOS

ESPERA_S = {"velas": 60, "operaciones": 30, "libro": 5, "opciones": 120}
SIN_FUENTE = ("Sin fuente autorizada para este dato. No se simula: importe un CSV con datos que tenga derecho a usar "
              "(plantilla en este panel) o configure un proveedor (ver docs/acciones-requeridas-usuario.md).")


def es_cripto(simbolo: str) -> bool:
    return ":" in simbolo and "/" in simbolo


def origen_eeuu(con, simbolo: str) -> str | None:
    """Símbolo de origen en EE. UU. de un instrumento del catálogo (p. ej. SIC:MU → MU)."""
    f = con.execute("SELECT listado_referencia FROM instrumentos WHERE id=? AND moneda_referencia='USD'", (simbolo,)).fetchone()
    return f[0].replace(".", "") if f and f[0] else None


def catalogo(con, ajustes) -> dict:
    cripto = Cripto(ajustes)
    sic = [{"id": r[0], "clave": r[1], "origen": r[2], "mercado": "SIC (origen EE. UU.)"} for r in con.execute(
        "SELECT id, clave_operable, listado_referencia FROM instrumentos WHERE estado='activo' AND moneda_referencia='USD' "
        "AND listado_referencia IS NOT NULL AND listado_referencia <> '' ORDER BY clave_operable")]
    pares = [{"id": cripto.simbolo(p), "clave": p, "mercado": "cripto (fuera del Reto)"} for p in cripto.cfg["pares"]] \
        if cripto.cfg.get("activo", True) else []
    importados = sorted(set(almacen.simbolos(con, "flujo_barras")) | set(almacen.simbolos(con, "flujo_operaciones"))
                        | set(almacen.simbolos(con, "flujo_libro")) | set(almacen.simbolos(con, "flujo_opciones")))
    return {"sic": sic, "cripto": pares, "con_datos": importados, "intervalos": list(INTERVALOS)}


def estado(con, ajustes, env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    alpaca = bool(env.get("ALPACA_API_KEY_ID") and env.get("ALPACA_API_SECRET_KEY"))
    cripto = Cripto(ajustes)
    try:
        import ccxt  # noqa: F401
        ccxt_ok = True
    except ImportError:
        ccxt_ok = False
    consultas = [dict(r) for r in con.execute("SELECT * FROM flujo_consultas ORDER BY intento_en DESC LIMIT 20")]
    return {"proveedores": [
        {"id": "alpaca", "nombre": "Alpaca Market Data (gratuito)", "configurado": alpaca,
         "datos": "Velas OHLCV SIP (≥ 15 min de retraso), operaciones SIP (≥ 15 min, sin lado), mejor bid/ask IEX (1 nivel), "
                  "cadenas de opciones (feed indicativo, diferido)", "licencia": "Uso personal; sin redistribución"},
        {"id": str(cripto.cfg["exchange"]), "nombre": f"Cripto vía ccxt ({cripto.cfg['exchange']})",
         "configurado": bool(cripto.cfg.get("activo", True) and ccxt_ok),
         "datos": "Libro por niveles y operaciones públicas con lado del agresor; " + ", ".join(cripto.cfg["pares"]),
         "licencia": "Términos públicos del exchange; ccxt MIT. Fuera del Reto."},
        {"id": "csv", "nombre": "CSV importado por usted", "configurado": True,
         "datos": "Velas, libro, operaciones y opciones con licencia propia", "licencia": "La que usted declare"},
    ], "consultas": consultas, "modo": "sintetico" if ajustes.es_demo else "real",
        "no_disponible": ["Libro con profundidad de acciones (EE. UU. o BMV): requiere contrato",
                          "Opciones en tiempo real (OPRA) e interés abierto: requiere suscripción",
                          "Opciones y libro de MexDer/BMV: requiere contrato"]}


def _puede(con, clave: str, tipo: str, ahora: datetime) -> bool:
    u = almacen.ultima_consulta(con, clave)
    return not u or (ahora - datetime.fromisoformat(u["intento_en"])).total_seconds() >= ESPERA_S[tipo]


def actualizar(con, ajustes, tipo: str, simbolo: str, intervalo: str = "1Day", dias: int = 180,
               env: dict | None = None, cliente=None, exchange=None) -> dict:
    """Consulta el proveedor del símbolo y guarda. En demostración no consulta (no hay datos sintéticos de flujo)."""
    if ajustes.es_demo:
        return {"estado": "demo", "mensaje": "En demostración no se consultan proveedores ni se simula flujo."}
    if tipo not in ESPERA_S:
        raise ValueError("tipo desconocido")
    if intervalo not in INTERVALOS:
        raise ValueError("intervalo inválido")
    ahora = datetime.now(UTC)
    clave = f"{tipo}:{simbolo}:{intervalo if tipo == 'velas' else ''}"
    if not _puede(con, clave, tipo, ahora):
        return {"estado": "en_espera", "mensaje": f"Consultado hace menos de {ESPERA_S[tipo]} s; se muestran los datos guardados."}
    try:
        if es_cripto(simbolo):
            c = Cripto(ajustes, exchange)
            par = simbolo.split(":", 1)[1]
            if tipo == "libro":
                libro, p = c.libro(par)
                n = almacen.guardar_libro(con, libro, p)
            elif tipo == "operaciones":
                ops, p = c.operaciones(par)
                n = almacen.guardar_operaciones(con, ops, p)
            elif tipo == "velas":
                barras, p = c.barras(par, intervalo, dias)
                n = almacen.guardar_barras(con, barras, p)
            else:
                raise FuenteNoDisponible("el exchange de cripto no ofrece cadenas de opciones en este adaptador")
        else:
            origen = origen_eeuu(con, simbolo)
            if not origen:
                raise FuenteNoDisponible("sin proveedor para este instrumento (solo emisoras con listado en EE. UU.; "
                                         "para la BMV importe un CSV)")
            a = Alpaca(ajustes, env, cliente)
            if tipo == "velas":
                barras, p = a.barras(origen, simbolo, intervalo, dias)
                n = almacen.guardar_barras(con, barras, p)
            elif tipo == "operaciones":
                ops, p = a.operaciones(origen, simbolo)
                n = almacen.guardar_operaciones(con, ops, p)
            elif tipo == "libro":
                libro, p = a.mejor_precio(origen, simbolo)
                n = almacen.guardar_libro(con, libro, p)
            else:
                spot = _spot(con, simbolo, origen)
                tasa, _ = tasa_libre_riesgo(con)
                contratos, p = a.cadena(origen, spot, tasa)
                for ct in contratos:
                    ct.subyacente = simbolo
                n = almacen.guardar_opciones(con, contratos, p)
        estado_c, msg = ("ok", f"{n} registros") if n else ("vacio", "el proveedor no devolvió datos para este rango")
    except FuenteNoDisponible as e:
        con.rollback()
        estado_c, msg, n = "sin_fuente", str(e), 0
    except ValueError as e:  # dato del proveedor que no pasa la validación (p. ej. libro cruzado): no se guarda
        con.rollback()
        estado_c, msg, n = "error", f"dato rechazado por la validación: {e}", 0
    with db.transaccion(con):
        almacen.registrar_consulta(con, clave, estado_c, n, msg)
    return {"estado": estado_c, "mensaje": msg, "registros": n}


def _spot(con, simbolo: str, origen: str) -> float | None:
    """Último cierre de origen en USD guardado (para filtrar strikes y calcular IV). Se dice en la nota."""
    f = con.execute("SELECT cierre FROM precios WHERE instrumento_id=? AND moneda='USD' AND proveedor<>'demo_sintetico' "
                    "ORDER BY fecha DESC LIMIT 1", (simbolo,)).fetchone()
    b = con.execute("SELECT cierre FROM flujo_barras WHERE simbolo=? ORDER BY inicio DESC LIMIT 1", (simbolo,)).fetchone()
    return float(b[0]) if b else float(f[0]) if f else None


def _procedencia(filas: list[dict]) -> list[dict]:
    vistos = {}
    for f in filas:
        k = (f["fuente"], f["feed"], f["calidad"])
        if k not in vistos:
            vistos[k] = {c: f.get(c) for c in ("fuente", "licencia", "mercado", "feed", "calidad", "retraso_s", "nota",
                                               "capturado_en")}
        elif f["capturado_en"] > vistos[k]["capturado_en"]:
            vistos[k].update(capturado_en=f["capturado_en"], retraso_s=f.get("retraso_s"))
    return list(vistos.values())


def velas(con, ajustes, simbolo: str, intervalo: str = "1Day", dias: int = 180) -> dict:
    if intervalo not in INTERVALOS:
        raise ValueError("intervalo inválido")
    desde = (datetime.now(UTC) - timedelta(days=int(dias))).isoformat()
    bs = almacen.barras(con, simbolo, intervalo, desde, demo=ajustes.es_demo)
    cierres = [b["cierre"] for b in bs]
    bol = calculos.bollinger(cierres)
    out = [{**{k: b[k] for k in ("inicio", "apertura", "maximo", "minimo", "cierre", "volumen", "vwap", "fuente", "feed",
                                "calidad", "retraso_s", "capturado_en")},
            "sma20": s, "rsi14": r, "boll_inf": bb[0] if bb else None, "boll_sup": bb[1] if bb else None, "vwap_anclado": v}
           for b, s, r, bb, v in zip(bs, calculos.sma(cierres, 20), calculos.rsi_wilder(cierres, 14), bol,
                                     calculos.vwap_anclado(bs))]
    return {"simbolo": simbolo, "intervalo": intervalo, "barras": out, "procedencia": _procedencia(bs),
            "zona_horaria": "Instantes en UTC; se muestran en America/Mexico_City",
            "vacio": None if out else SIN_FUENTE,
            "nota": "Velas solo con OHLCV real (proveedor o CSV). Los cierres diarios locales no se convierten en velas. "
                    "SMA20, RSI14 (Wilder), Bollinger (20, 2) y VWAP anclado al inicio del rango son descriptivos."}


def orderflow(con, ajustes, simbolo: str, minutos: int = 240, niveles: int = 20) -> dict:
    libro = almacen.ultimo_libro(con, simbolo, demo=ajustes.es_demo)
    desde = (datetime.now(UTC) - timedelta(minutes=int(minutos))).isoformat()
    ops = almacen.operaciones(con, simbolo, desde, demo=ajustes.es_demo)
    res = calculos.resumen_operaciones(ops)
    return {"simbolo": simbolo, "libro": calculos.resumen_libro(libro, niveles),
            "libro_meta": {k: libro[k] for k in ("instante", "fuente", "licencia", "mercado", "feed", "calidad", "retraso_s",
                                                 "nota", "capturado_en")} if libro else None,
            "operaciones": ops[-200:], "resumen": res, "procedencia_operaciones": _procedencia(ops),
            "vacio_libro": None if libro else SIN_FUENTE, "vacio_operaciones": None if ops else SIN_FUENTE,
            "nota": "Delta de volumen solo cuando el proveedor informa el lado del agresor de TODAS las operaciones; "
                    "nunca se infiere. El perfil de volumen usa solo las operaciones guardadas del rango."}


def optionflow(con, ajustes, subyacente: str, filtros: dict | None = None) -> dict:
    f = filtros or {}
    cadena = almacen.cadena(con, subyacente, demo=ajustes.es_demo)
    hoy = datetime.now(UTC).date()
    vencs = sorted({c["vencimiento"] for c in cadena})

    def pasa(c):
        if f.get("vencimiento") and c["vencimiento"] != f["vencimiento"]:
            return False
        if f.get("tipo") in ("call", "put") and c["tipo"] != f["tipo"]:
            return False
        for campo, minimo in (("volumen", f.get("volumen_min")), ("interes_abierto", f.get("oi_min"))):
            if minimo not in (None, "") and (c.get(campo) or 0) < float(minimo):
                return False
        if f.get("strike_min") not in (None, "") and c["strike"] < float(f["strike_min"]):
            return False
        if f.get("strike_max") not in (None, "") and c["strike"] > float(f["strike_max"]):
            return False
        if f.get("delta_abs_max") not in (None, "") and c.get("delta") is not None and abs(c["delta"]) > float(f["delta_abs_max"]):
            return False
        return True
    visibles = [c for c in cadena if pasa(c)]
    for c in visibles:
        c["dias"] = calculos.dias_al_vencimiento(c["vencimiento"], hoy)
    regla = {"ratio_oi": float(f.get("ratio_oi") or 1.0), "percentil": float(f.get("percentil") or 0.95),
             "minimo": float(f.get("vol_inusual_min") or 100)}
    _, origen_tasa = tasa_libre_riesgo(con)
    return {"subyacente": subyacente, "vencimientos": vencs, "contratos": visibles, "total": len(cadena),
            "iv": calculos.superficie_iv(visibles), "inusual": calculos.volumen_inusual(visibles, **regla), "regla": regla,
            "procedencia": _procedencia(cadena), "vacio": None if cadena else SIN_FUENTE,
            "tasa_para_iv_calculada": origen_tasa,
            "nota": "IV «proveedor» viene de la fuente; «calculado» es Black-Scholes-Merton europeo sobre el punto medio "
                    "bid/ask (las opciones de EE. UU. son americanas); «importado», de su CSV. El volumen inusual es una "
                    "regla descriptiva configurable, no una recomendación."}


# --- Etapa 2: adaptadores de repositorios (interruptores en [flujo.<nombre>] activo) ------------------------------
def activo(ajustes, nombre: str) -> bool:
    return bool((((ajustes.get("flujo") or {}) if ajustes else {}).get(nombre) or {}).get("activo", True))


def heston(con, ajustes, subyacente: str) -> dict:
    """Calibra Heston a la última cadena guardada del subyacente (código propio; ver flujo/heston.py)."""
    from . import heston as hs
    if not activo(ajustes, "heston"):
        raise ValueError("calibración de Heston desactivada en [flujo.heston]")
    ahora = datetime.now(UTC)
    clave = f"heston:{subyacente}:"
    u = almacen.ultima_consulta(con, clave)
    if u and (ahora - datetime.fromisoformat(u["intento_en"])).total_seconds() < 30:
        raise ValueError("calibrado hace menos de 30 s; espere un momento")
    cadena = almacen.cadena(con, subyacente, demo=ajustes.es_demo)
    if not cadena:
        raise ValueError("sin cadena guardada: pulse «Actualizar cadena desde proveedor» o importe un CSV")
    origen = origen_eeuu(con, subyacente) or subyacente
    spot = _spot(con, subyacente, origen)
    if not spot:
        raise ValueError("sin precio del subyacente para calibrar")
    tasa, origen_tasa = tasa_libre_riesgo(con)
    try:
        r = hs.calibrar(cadena, spot, (tasa if tasa is not None else 4.0) / 100)
        estado_c, msg = "ok", f"RMSE {r['rmse_iv']:.4f}"
    except ValueError as e:
        with db.transaccion(con):
            almacen.registrar_consulta(con, clave, "error", 0, str(e))
        raise
    with db.transaccion(con):
        almacen.registrar_consulta(con, clave, estado_c, r["contratos"], msg)
    f = con.execute("SELECT inicio FROM flujo_barras WHERE simbolo=? ORDER BY inicio DESC LIMIT 1", (subyacente,)).fetchone()
    return {**r, "subyacente": subyacente, "origen_tasa": origen_tasa,
            "origen_spot": f"último cierre guardado ({f[0][:10] if f else 'tabla de precios'}), USD de origen"}
