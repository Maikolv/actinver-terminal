"""Paneles nativos de la Mesa: noticias, macro, resumen fechado y contrato del calendario de resultados.

Solo LEEN lo que la terminal ya guardó con sus conectores autorizados; ninguna función consulta proveedores, pide
credenciales ni escribe en la base. Cada cifra sale con su fuente, su fecha y su corte. Lo que falta se declara
SIN DATO con el requisito exacto, nunca se rellena.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import unicodedata
from datetime import UTC, date, datetime, timedelta

from . import centro_investigacion, mercado
from .config import CONFIG_DIR, Ajustes

SIN_DATO = "SIN DATO"

# Series macro del panel: (fuente, serie, frecuencia declarada, grupo). La frecuencia es la de la publicación oficial.
SERIES_MACRO = [
    ("fred_macro", "DGS2", "diaria (hábil)", "Curva de EE. UU."),
    ("fred_macro", "DGS10", "diaria (hábil)", "Curva de EE. UU."),
    ("fred_macro", "DGS30", "diaria (hábil)", "Curva de EE. UU."),
    ("fred_macro", "FEDFUNDS", "mensual", "Tasas de política"),
    ("bls", "CPI_YOY", "mensual", "Inflación y empleo"),
    ("bls", "LNS14000000", "mensual", "Inflación y empleo"),
    ("bls", "CES0000000001", "mensual", "Inflación y empleo"),
    ("fred_macro", "INDPRO", "mensual", "Actividad"),
    ("eia", "WTI", "semanal", "Energía"),
    ("eia", "BRENT", "semanal", "Energía"),
    ("banxico_sie", "BANXICO_OBJETIVO", "según publicación", "México"),
    ("banxico_sie", "BANXICO_BONO10", "según publicación", "México"),
    ("banxico_sie", "INPC", "mensual", "México"),
]
# Requisito cuando una serie no tiene observaciones guardadas (no se activa nada desde aquí).
REQUISITO = {
    "DGS30": "DGS30: falta observación FRED o importación de la publicación XML H.15 oficial, disponible sin clave.",
    "BANXICO_OBJETIVO": "SF61745 confirmado como tasa objetivo; falta una observación guardada en esta base. Fuente automática apagada.",
    "BANXICO_BONO10": "SF30057 confirmado como bono a tasa fija a 10 años, promedio mensual; falta observación en esta base.",
    "INPC": "SP1 confirmado como índice nacional general mensual por catálogo SIE; falta una descarga manual de observaciones.",
}


def _norm(texto: str) -> str:
    s = unicodedata.normalize("NFKD", (texto or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()


def noticias(con: sqlite3.Connection, simbolo: str = "", limite: int = 40) -> dict:
    """Titulares deduplicados por enlace y por título normalizado. Sin cuerpo del artículo ni sentimiento."""
    limite = max(1, min(int(limite), 100))
    if simbolo:
        filas = con.execute("SELECT * FROM noticias WHERE instrumento_id=? ORDER BY publicado DESC LIMIT 400", (simbolo,))
    else:
        filas = con.execute("SELECT * FROM noticias ORDER BY publicado DESC LIMIT 1500")
    vistos, out = set(), []
    for f in filas:
        claves = {k for k in (("u", (f["enlace"] or "").split("?")[0]), ("t", _norm(f["titulo"]))) if k[1]}
        if claves & vistos:
            for o in out:  # el mismo artículo citado por otra emisora: se suma la emisora, no se repite la fila
                if o["enlace"] == f["enlace"] or _norm(o["titulo"]) == _norm(f["titulo"]):
                    if f["instrumento_id"] and f["instrumento_id"] not in o["instrumentos"]:
                        o["instrumentos"].append(f["instrumento_id"])
                    break
            continue
        vistos |= claves
        out.append({"titulo": f["titulo"], "enlace": f["enlace"], "fuente": f["fuente"],
                    "publicado": f["publicado"], "ingesta": f["obtenido_en"],
                    "instrumentos": [f["instrumento_id"]] if f["instrumento_id"] else []})
        if len(out) >= limite:
            break
    return {"simbolo": simbolo or None, "noticias": out,
            "nota": "Titulares de los feeds RSS configurados. «Publicado» lo declara la fuente; «ingesta» es cuándo los "
                    "guardó la terminal (la fuente no informa una hora de disponibilidad distinta). Se muestra solo el "
                    "título y el enlace al original; no se copia el artículo ni se calcula sentimiento."}


def _cetes(con: sqlite3.Connection) -> dict:
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='cetes28'").fetchone()
    if not f:
        return {"serie": "CETES28", "titulo": "CETES 28 días", "valor": None, "estado": SIN_DATO, "grupo": "Tasas de política", "frecuencia": "semanal",
                "requisito": "Se guarda al abrir Mis portafolios con BANXICO_TOKEN configurado."}
    d = json.loads(f[0])
    return {"serie": "CETES28", "titulo": "CETES 28 días (subasta)", "valor": None if d.get("valor") is None else d["valor"] * 100,
            "unidad": "%", "periodo": d.get("fecha"), "frecuencia": "semanal", "fuente": d.get("fuente"),
            "ingesta": d.get("consultado_en"), "grupo": "Tasas de política", "aviso": d.get("aviso")}


def macro(con: sqlite3.Connection, ajustes: Ajustes, ahora: datetime | None = None) -> dict:
    """Última observación conocida al corte de cada serie, con periodo, frecuencia y fuente."""
    ahora = ahora or datetime.now(UTC)
    obs = centro_investigacion.observaciones(con, "", ahora)
    ultima: dict[tuple[str, str], dict] = {}
    for o in obs:  # ordenadas por periodo descendente: la primera de cada serie es la más reciente
        ultima.setdefault((o["fuente"], o["serie"]), o)
    respaldos = {"LNS14000000": "UNRATE", "CES0000000001": "PAYEMS", "CPI_YOY": "CPIAUCSL"}

    def respaldo(serie):
        sid = respaldos[serie]
        o = ultima.get(("fred_macro", sid))
        if not o or serie != "CPI_YOY":
            return o
        mes = o["periodo"][:7]
        anterior = f"{int(mes[:4])-1:04d}{mes[4:]}"
        base = next((f for f in obs if f["fuente"] == "fred_macro" and f["serie"] == sid
                     and f["periodo"][:7] == anterior), None)
        if not base or base["valor"] <= 0 or o["valor"] <= 0:
            return None
        valor = (o["valor"] / base["valor"] - 1) * 100
        if not math.isfinite(valor):
            return None
        return {**o, "valor": valor, "unidad": "%", "titulo": "IPC EE. UU. · variación interanual de CPIAUCSL",
                "disponible_desde": max(o["disponible_desde"], base["disponible_desde"])}

    filas = []
    for fuente, serie, frecuencia, grupo in SERIES_MACRO:
        o = ultima.get((fuente, serie))
        serie_fuente = serie
        if fuente == "bls" and serie in respaldos:
            alternativa = respaldo(serie)
            # Comparar meses, no cadenas de distinta longitud; en empate se conserva BLS.
            if alternativa and (not o or alternativa["periodo"][:7] > o["periodo"][:7]):
                o, fuente, serie_fuente = alternativa, "fred_macro", respaldos[serie]
        if o and fuente == 'banxico_sie' and 'mensual' in _norm(o['titulo']):
            frecuencia = 'mensual (promedio)' if serie == 'BANXICO_BONO10' else 'mensual'
        if fuente == 'fred_macro' and serie == 'DGS30':
            primaria = ultima.get(('fed_h15', serie))
            if primaria and (not o or primaria['periodo'] > o['periodo']):
                o, fuente = primaria, 'fed_h15'
        if not o:
            filas.append({"serie": serie, "fuente": fuente, "grupo": grupo, "frecuencia": frecuencia, "valor": None,
                          "estado": SIN_DATO, "requisito": REQUISITO.get(serie, "Sin observaciones guardadas de esta serie.")})
            continue
        filas.append({"serie": serie, "titulo": o["titulo"], "valor": o["valor"], "unidad": o["unidad"],
                      "serie_fuente": serie_fuente,
                      "periodo": o["periodo"], "frecuencia": frecuencia, "fuente": fuente, "grupo": grupo,
                      "ingesta": o["disponible_desde"], "url": o["url"], "estado": "PUBLICACIÓN · NO COTIZACIÓN",
                      "via": "XML oficial H.15; no verifica API FRED" if fuente == 'fed_h15' else "conector de investigación"})
    fx = mercado.ultimo_fx(con, ajustes)
    filas.insert(0, {"serie": "USDMXN", "titulo": "Dólar / peso (FIX o referencia)", "valor": fx.get("valor"),
                     "unidad": "MXN por USD", "periodo": fx.get("fecha"), "frecuencia": "diaria (hábil)",
                     "fuente": fx.get("proveedor"), "grupo": "Tipo de cambio", "ingesta": fx.get("obtenido_en"),
                     "estado": None if fx.get("valor") is not None else SIN_DATO})
    filas.append(_cetes(con))
    periodos = sorted({f["periodo"][:10] for f in filas if f.get("periodo")})
    curva = [f for f in filas if f["grupo"] == "Curva de EE. UU." and f.get("valor") is not None]
    fechas_curva = {f["periodo"] for f in curva}
    return {"corte": ahora.isoformat(timespec="seconds"), "series": filas,
            "curva": {"puntos": [{"plazo": f["serie"].replace("DGS", "") + " años", "valor": f["valor"], "periodo": f["periodo"]} for f in curva],
                      "aviso": None if len(fechas_curva) <= 1 else "Los plazos tienen fechas distintas: no es una curva de un mismo día."},
            "aviso": ("Las series tienen periodos distintos (" + ", ".join([periodos[0], periodos[-1]]) + "); no se comparan como "
                      "si fueran del mismo día.") if len(periodos) > 1 else None,
            "nota": "Solo lectura de lo descargado por los conectores (FRED, BLS, EIA, Banxico). No consulta proveedores."}


def calendario_bea(ahora: datetime) -> dict:
    """Lee el corte local de fechas programadas para los próximos siete días."""
    vacio = {"consultado_en": None, "eventos": []}
    try:
        corte = json.loads((CONFIG_DIR / "calendario_bea.json").read_text(encoding="utf-8"))
        if datetime.fromisoformat(corte["consultado_en"]) > ahora:
            return vacio
        fin = ahora + timedelta(days=7)
        eventos = [fila for fila in corte["eventos"] if ahora <= datetime.fromisoformat(fila["fecha"]) < fin]
    except (OSError, ValueError, KeyError, TypeError):
        return vacio
    return {"consultado_en": corte["consultado_en"], "eventos": eventos}


def resumen(con: sqlite3.Connection, ajustes: Ajustes, ahora: datetime | None = None, cot: dict | None = None) -> dict:
    """Resumen fechado y trazable del corte local: sin explicaciones causales ni cotizaciones «actuales»."""
    ahora = ahora or datetime.now(UTC)
    from . import vigencia
    cot = mercado.cotizaciones(con, ajustes) if cot is None else cot  # la API pasa la caché de /api/estado
    conteo: dict[str, int] = {}
    for c in cot.values():
        e = c.get("estado") or "sin_datos"
        conteo[e] = conteo.get(e, 0) + 1
    hoy = ahora.date()
    eventos = [dict(r) for r in con.execute(
        "SELECT fecha, pais, titulo, impacto, pronostico, previo, fuente FROM eventos_macro WHERE impacto='High' AND "
        "pais IN ('USD','MXN') AND substr(fecha,1,10) BETWEEN ? AND ? ORDER BY fecha LIMIT 12",
        (hoy.isoformat(), (hoy + timedelta(days=7)).isoformat()))]
    n_noticias = con.execute("SELECT COUNT(DISTINCT lower(titulo)) FROM noticias WHERE publicado >= ?",
                             ((ahora - timedelta(hours=24)).isoformat(),)).fetchone()[0]
    m = macro(con, ajustes, ahora)
    clave = {s["serie"]: s for s in m["series"]}
    cifras = []
    for k in ("USDMXN", "DGS10", "CETES28", "CPI_YOY", "WTI"):
        s = clave.get(k)
        if s and s.get("valor") is not None:
            cifras.append({"serie": k, "titulo": s.get("titulo"), "valor": s["valor"], "unidad": s.get("unidad"),
                           "periodo": s.get("periodo"), "fuente": s.get("fuente")})
    return {"corte": ahora.isoformat(timespec="seconds"),
            "ultima_sesion": {"NYSE": vigencia.ultima_sesion_cerrada("XNYS", ahora).isoformat(),
                              "BMV": vigencia.ultima_sesion_cerrada("XMEX", ahora).isoformat()},
            "datos": {"instrumentos": len(cot), "por_estado": conteo},
            "calendario_bea": calendario_bea(ahora),
            "cifras": cifras, "eventos_alto_impacto_7d": eventos, "titulares_24h": n_noticias,
            "fuentes": {"cifras": "Panel macro (FRED, BLS, EIA, Banxico)", "eventos": "ForexFactory (feed de exportación)",
                        "titulares": "Seeking Alpha (RSS)", "estado de datos": "Precios guardados y su vigencia"},
            "nota": "Resumen de lo que la terminal tiene guardado a la hora de corte. No explica causas, no pronostica y "
                    "no es una cotización actual: cada cifra lleva su periodo y su fuente."}


# ---------------------------------------------------------------------------------------------------------------
# Calendario de resultados: CONTRATO DE DATOS y cálculo puro de la reacción. La parte real está BLOQUEADA: ninguna
# fuente autorizada de la terminal entrega fechas de reporte, estimaciones y cifras reportadas con su hora.
CONTRATO_RESULTADOS = {
    "estado": "bloqueado",
    "motivo": "Sin fuente autorizada de calendario de resultados (fecha, hora antes/después de la apertura, estimación, "
              "dato reportado y revisión). El widget de TradingView solo muestra eventos económicos.",
    "campos": {
        "simbolo": "id del instrumento (SIC:XXX o BMV:XXX)",
        "fecha_reporte": "AAAA-MM-DD del anuncio",
        "momento": "'antes' de la apertura o 'despues' del cierre (hora de la bolsa de origen)",
        "estimacion_bpa": "consenso antes del anuncio, con su fecha de corte (no se usa la revisada después)",
        "reportado_bpa": "cifra publicada por la empresa",
        "revisado_bpa": "cifra revisada posteriormente, si existe, con fecha de revisión",
        "fuente": "proveedor y licencia", "disponible_desde": "instante en que el dato pudo conocerse",
    },
    "siguiente_accion": "Elegir y autorizar un proveedor con licencia para estos campos; luego conectar import CSV con este contrato.",
}


def reaccion_resultados(cierres: list[tuple[str, float]], fecha_reporte: str, momento: str, sesiones: int = 1) -> dict:
    """Reacción del precio al reporte sin fuga temporal.

    Base: el último cierre CONOCIDO antes del anuncio (el día previo si se publicó antes de la apertura; el mismo día
    si fue después del cierre). Reacción: el cierre `sesiones` sesiones después de la base. Solo usa cierres con
    fecha posterior a la base para la reacción y nunca fechas anteriores para el resultado.
    """
    if momento not in ("antes", "despues"):
        raise ValueError("momento debe ser 'antes' o 'despues'")
    if sesiones < 1:
        raise ValueError("sesiones ≥ 1")
    fr = date.fromisoformat(fecha_reporte)
    serie = sorted((date.fromisoformat(f), float(c)) for f, c in cierres)
    previos = [x for x in serie if (x[0] < fr if momento == "antes" else x[0] <= fr)]
    if not previos:
        return {"estado": SIN_DATO, "motivo": "sin cierre previo al anuncio"}
    base = previos[-1]
    posteriores = [x for x in serie if x[0] > base[0]]
    if len(posteriores) < sesiones:
        return {"estado": SIN_DATO, "motivo": f"faltan {sesiones - len(posteriores)} sesiones posteriores", "base": base[0].isoformat()}
    fin = posteriores[sesiones - 1]
    return {"base": base[0].isoformat(), "cierre_base": base[1], "fin": fin[0].isoformat(), "cierre_fin": fin[1],
            "reaccion": fin[1] / base[1] - 1, "sesiones": sesiones}
