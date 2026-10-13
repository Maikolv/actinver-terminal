"""Centro local de investigación: fuentes, instantáneas y notas, con disponibilidad conservadora.

Se almacena fuera de precios/fx/universo. No participa en puntuaciones ni operaciones.
Los valores descargados hoy no se consideran conocidos en el pasado; se retienen revisiones.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx

from . import db
from .adaptadores.base import ErrorProveedor, LimiteAlcanzado
from .centro_conectores import CONECTORES, numero
from .config import RAIZ

MAX_CSV = 1_000_000
COLUMNAS = ["fuente", "simbolo", "serie", "titulo", "periodo", "valor", "unidad", "texto", "url"]
DEFAULTS = {
    "alpha_vantage": {"intervalo_horas": 24, "peticiones_por_dia": 20},
    "fred_macro": {"intervalo_horas": 24, "peticiones_por_dia": 24},
    "coingecko": {"intervalo_horas": 1, "peticiones_por_dia": 24},
    "eia": {"intervalo_horas": 24, "peticiones_por_dia": 12},
    "bls": {"intervalo_horas": 24, "peticiones_por_dia": 4},
}


def fuentes():
    return json.loads((RAIZ / "config" / "fuentes_investigacion.json").read_text(encoding="utf-8"))


def inicializar(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS investigacion_observaciones (
      id INTEGER PRIMARY KEY, fuente TEXT NOT NULL, simbolo TEXT NOT NULL, serie TEXT NOT NULL,
      titulo TEXT NOT NULL, periodo TEXT NOT NULL, valor REAL, unidad TEXT NOT NULL, texto TEXT NOT NULL,
      url TEXT NOT NULL, origen TEXT NOT NULL CHECK(origen IN ('api','manual')),
      hora_fuente TEXT, disponible_desde TEXT NOT NULL, confirmado_en TEXT NOT NULL,
      huella TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS investigacion_por_serie ON investigacion_observaciones
      (fuente,simbolo,serie,periodo,disponible_desde);
    CREATE TABLE IF NOT EXISTS investigacion_consultas (
      fuente TEXT PRIMARY KEY, intento_en TEXT NOT NULL, estado TEXT NOT NULL,
      registros INTEGER NOT NULL DEFAULT 0, mensaje TEXT NOT NULL
    );
    """)


def _utc(ahora=None):
    ahora = ahora or datetime.now(UTC)
    if ahora.tzinfo is None:
        raise ValueError("Se requiere una hora con zona horaria")
    return ahora.astimezone(UTC)


def validar_simbolo(simbolo):
    simbolo = str(simbolo or "").strip().upper()
    if simbolo and not re.fullmatch(r"[A-Z0-9][A-Z0-9.:-]{0,23}", simbolo):
        raise ValueError("Símbolo no válido")
    return simbolo


def _periodo(valor, ahora):
    valor = str(valor)
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
            inicio = date.fromisoformat(valor)
        elif re.fullmatch(r"\d{4}-\d{2}", valor):
            inicio = date.fromisoformat(valor + "-01")
        elif re.fullmatch(r"\d{4}-Q[1-4]", valor):
            inicio = date(int(valor[:4]), (int(valor[-1])-1)*3+1, 1)
        elif re.fullmatch(r"\d{4}", valor):
            inicio = date(int(valor), 1, 1)
        else:
            raise ValueError
        if inicio > ahora.date():
            raise ValueError
    except ValueError:
        raise ValueError("Período inválido o futuro; use YYYY-MM-DD, YYYY-MM, YYYY-Qn o YYYY") from None
    return valor


def _sin_secretos(texto):
    for fuente in fuentes():
        variable = fuente.get("variable")
        clave = os.environ.get(variable, "") if variable else ""
        if len(clave) >= 6 and clave in texto:
            raise ValueError("El contenido incluye una credencial; elimínela antes de importar")
    if re.search(r"(?:api[_-]?key|apikey|auth[_-]?token|registrationkey|access[_-]?token)\s*[=:]", texto, re.I):
        raise ValueError("No se permiten credenciales en los datos de investigación")


def _validar_url(url, fuente):
    url = str(url or fuente["url"]).strip()
    _sin_secretos(url)
    try:
        p = urlsplit(url)
        puerto = p.port
    except ValueError:
        raise ValueError("Enlace HTTPS inválido") from None
    host = (p.hostname or "").lower()
    if (p.scheme != "https" or p.username or p.password or puerto not in (None, 443)
            or not any(host == d or host.endswith("." + d) for d in fuente["dominios"])):
        raise ValueError("El enlace debe ser HTTPS y pertenecer a la fuente seleccionada")
    if p.fragment and re.search(r"key|token|secret", p.fragment, re.I):
        raise ValueError("El enlace no puede contener credenciales")
    if any(re.search(r"key|token|secret|auth", k, re.I) for k in parse_qs(p.query)):
        raise ValueError("El enlace no puede contener credenciales")
    _sin_secretos(url)
    return url


def _validar(fila, fuente, ahora, origen):
    serie = str(fila.get("serie", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", serie):
        raise ValueError("Serie: use un identificador de hasta 64 caracteres")
    bruto = fila.get("valor")
    valor = numero(bruto)
    if bruto not in (None, "") and valor is None:
        raise ValueError("Valor: use un número finito, con punto decimal")
    titulo = str(fila.get("titulo", "")).strip()
    texto = str(fila.get("texto", "")).strip()
    unidad = str(fila.get("unidad", "")).strip()
    if not titulo or len(titulo) > 160 or len(texto) > 2000 or len(unidad) > 80:
        raise ValueError("Título requerido (máx. 160); nota máx. 2000 y unidad máx. 80 caracteres")
    if valor is None and not texto:
        raise ValueError("Se requiere un valor o una nota")
    if valor is not None and not unidad:
        raise ValueError("Indique la unidad del valor")
    _sin_secretos(titulo + " " + texto + " " + unidad)
    hora_fuente = fila.get("hora_fuente")
    if hora_fuente:
        try:
            momento = datetime.fromisoformat(hora_fuente)
        except (TypeError, ValueError):
            raise ValueError("Hora de la fuente no válida") from None
        if momento.tzinfo is None or momento > ahora:
            raise ValueError("Hora de la fuente sin zona horaria o futura")
        hora_fuente = momento.astimezone(UTC).isoformat()
    return {"fuente": fuente["id"], "simbolo": validar_simbolo(fila.get("simbolo")), "serie": serie,
            "titulo": titulo, "periodo": _periodo(fila.get("periodo", ""), ahora), "valor": valor,
            "unidad": unidad, "texto": texto, "url": _validar_url(fila.get("url"), fuente),
            "origen": origen, "hora_fuente": hora_fuente}


def _guardar(con, filas, ahora):
    nuevos = 0
    marca = ahora.isoformat(timespec="microseconds")
    for f in filas:
        huella = hashlib.sha256(json.dumps(f, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        anterior = con.execute("SELECT id,huella FROM investigacion_observaciones WHERE fuente=? AND simbolo=? "
                               "AND serie=? AND periodo=? AND origen=? ORDER BY disponible_desde DESC,id DESC LIMIT 1",
                               (f['fuente'], f['simbolo'], f['serie'], f['periodo'], f['origen'])).fetchone()
        if anterior and anterior['huella'] == huella:
            con.execute("UPDATE investigacion_observaciones SET confirmado_en=? WHERE id=?", (marca, anterior["id"]))
            continue
        cols = list(f) + ["disponible_desde", "confirmado_en", "huella"]
        con.execute(f"INSERT INTO investigacion_observaciones ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",
                    list(f.values()) + [marca, marca, huella])
        nuevos += 1
    return nuevos


def importar_csv(con, contenido: bytes, ahora=None):
    ahora = _utc(ahora)
    if len(contenido) > MAX_CSV:
        raise ValueError("CSV demasiado grande (máx. 1 MB)")
    try:
        lector = csv.DictReader(io.StringIO(contenido.decode("utf-8-sig")), restkey="_extra", strict=True)
        if lector.fieldnames != COLUMNAS:
            raise ValueError("Use los encabezados y el orden de la plantilla de investigación")
        mapa = {f["id"]: f for f in fuentes()}
        filas = []
        for indice, f in enumerate(lector, start=2):
            if indice > 1001:
                raise ValueError("CSV: máximo 1000 filas")
            try:
                if f.get("_extra") or any(f.get(c) is None for c in COLUMNAS):
                    raise ValueError("Número de columnas incorrecto")
                if f.get("fuente") not in mapa:
                    raise ValueError("Fuente desconocida; use su identificador de la lista")
                filas.append(_validar(f, mapa[f["fuente"]], ahora, "manual"))
            except ValueError as e:
                raise ValueError(f"Fila {indice}: {e}") from None
    except UnicodeError:
        raise ValueError("El archivo debe ser CSV UTF-8") from None
    except csv.Error:
        raise ValueError("CSV inválido o con una celda demasiado grande") from None
    if not filas:
        raise ValueError("El CSV no contiene registros")
    with db.transaccion(con):
        nuevos = _guardar(con, filas, ahora)
        db.auditar(con, "investigacion", "csv", "importar", despues={"filas": len(filas), "nuevos": nuevos})
    return {"filas": len(filas), "nuevos": nuevos, "nota": "Importación manual; fuente no verificada automáticamente. Disponible desde ahora."}


def plantilla():
    # Plantilla sin datos inventados: la interfaz explica cómo rellenar valores propios.
    return ",".join(COLUMNAS) + "\n"


def _cfg(ajustes, fid):
    cfg = {"activo": True, **DEFAULTS[fid], **(ajustes.get("centro_investigacion", {}).get(fid) or {})}
    if fid == "alpha_vantage":
        simbolos = cfg.get("simbolos", ["MU", "AMD", "NVDA", "XOM"])
        if not isinstance(simbolos, list) or not 1 <= len(simbolos) <= 8:
            raise ValueError("Alpha Vantage requiere de 1 a 8 símbolos")
        cfg["simbolos"] = [validar_simbolo(s) for s in simbolos]
        if not all(re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", s) for s in cfg["simbolos"]):
            raise ValueError("Alpha Vantage: use símbolos del mercado de origen")
    if not 1 <= float(cfg["intervalo_horas"]) <= 168:
        raise ValueError("Intervalo: de 1 a 168 horas")
    # El cupo gratuito de Alpha Vantage no se amplía por omisión ni desde la UI.
    if fid == "alpha_vantage":
        cfg["peticiones_por_dia"] = min(int(cfg["peticiones_por_dia"]), 25)
    return cfg


def actualizar(con, ajustes, ahora=None, env=None, cliente=None):
    if ajustes.es_demo:
        return {"estado": "demo_sin_consultas", "fuentes": {}, "nuevos": 0}
    ahora = _utc(ahora)
    env = os.environ if env is None else env
    resultados = {}
    nuevos_total = 0
    for fuente in fuentes():
        fid = fuente["id"]
        if fid not in CONECTORES:
            continue
        cfg = _cfg(ajustes, fid)
        clave = env.get(fuente["variable"]) or None
        if not cfg["activo"] or (fid != "bls" and not clave):
            resultados[fid] = {"estado": "desactivada" if not cfg["activo"] else "sin_credencial", "nuevos": 0}
            continue
        anterior = con.execute("SELECT * FROM investigacion_consultas WHERE fuente=?", (fid,)).fetchone()
        intervalo = timedelta(hours=float(cfg["intervalo_horas"]))
        if anterior:
            espera = intervalo if anterior["estado"] == "ok" else min(intervalo, timedelta(hours=1))
            if ahora - datetime.fromisoformat(anterior["intento_en"]) < espera:
                resultados[fid] = {"estado": "en_espera", "nuevos": 0}
                continue
        propio = cliente is None
        cli = cliente or httpx.Client(timeout=8, follow_redirects=False,
                                      headers={"User-Agent": "actinver-terminal/0.26 (investigacion local)"})
        adapter = CONECTORES[fid](con, cfg, clave, cliente=cli)
        estado, mensaje, nuevos = "ok", "Consulta completada", 0
        try:
            raw = adapter.consultar(ahora)
            filas = [_validar(f, fuente, ahora, "api") for f in raw]
            if not filas:
                raise ErrorProveedor("La fuente no entregó observaciones utilizables")
            with db.transaccion(con):
                nuevos = _guardar(con, filas, ahora)
        except LimiteAlcanzado:
            estado, mensaje = "limite", "Cupo local agotado; se conserva el histórico"
        except (ErrorProveedor, httpx.HTTPError, ValueError, KeyError, TypeError, OverflowError):
            # Nunca se devuelve el cuerpo o la URL del error: podrían contener la clave.
            estado, mensaje = "error", "No se pudo confirmar la respuesta; revise conexión, clave y acceso de la fuente"
        finally:
            if propio:
                adapter.cerrar()
        with db.transaccion(con):
            con.execute("INSERT INTO investigacion_consultas VALUES (?,?,?,?,?) ON CONFLICT(fuente) DO UPDATE SET "
                        "intento_en=excluded.intento_en, estado=excluded.estado, registros=excluded.registros, mensaje=excluded.mensaje",
                        (fid, ahora.isoformat(), estado, nuevos, mensaje))
        resultados[fid] = {"estado": estado, "nuevos": nuevos, "mensaje": mensaje}
        nuevos_total += nuevos
    return {"estado": "completado", "fuentes": resultados, "nuevos": nuevos_total}


def observaciones(con, simbolo="", hasta=None):
    simbolo = validar_simbolo(simbolo)
    corte = _utc(hasta).isoformat(timespec="microseconds")
    sql = """SELECT * FROM (
      SELECT o.*, ROW_NUMBER() OVER (
        PARTITION BY fuente,simbolo,serie,periodo,origen ORDER BY disponible_desde DESC,id DESC
      ) AS revision FROM investigacion_observaciones o WHERE disponible_desde<=?
    ) WHERE revision=1"""
    args = [corte]
    if simbolo:
        sql += " AND (simbolo=? OR simbolo='')"
        args.append(simbolo)
    sql += " ORDER BY periodo DESC,fuente,simbolo,serie LIMIT 1000"
    return [{k: f[k] for k in f.keys() if k != "revision"} for f in con.execute(sql, args)]


def resumen(con, ajustes, simbolo="", ahora=None, env=None):
    ahora = _utc(ahora)
    env = os.environ if env is None else env
    catalogo = []
    for fuente in fuentes():
        f = {k: v for k, v in fuente.items() if k != "dominios"}
        consulta = con.execute("SELECT * FROM investigacion_consultas WHERE fuente=?", (f["id"],)).fetchone()
        f["credencial_presente"] = bool(env.get(f["variable"])) if f["variable"] else False
        f["ultima_consulta"] = dict(consulta) if consulta else None
        if f["conector"]:
            cfg = _cfg(ajustes, f["id"])
            f["estado"] = ("desactivada" if not cfg["activo"] else "lista" if f["id"] == "bls" or f["credencial_presente"] else "requiere_clave")
        else:
            f["estado"] = "conector_existente" if f["id"] == "finviz" and f["credencial_presente"] else "consulta_manual"
        catalogo.append(f)
    filas = observaciones(con, simbolo, ahora)
    for f in filas:
        cfg = DEFAULTS.get(f["fuente"], {"intervalo_horas": 24})
        limite = timedelta(hours=float(cfg["intervalo_horas"]))
        confirmada = min(datetime.fromisoformat(f["confirmado_en"]), ahora)
        f["requiere_actualizacion"] = ahora - confirmada > limite
        f["referencia_atrasada"] = bool(f["hora_fuente"] and ahora - datetime.fromisoformat(f["hora_fuente"]) > limite)
    return {"fuentes": catalogo, "observaciones": filas, "modo": ajustes.modo,
            "nota": "Contexto de investigación. No modifica propuestas ni precios de la cartera. Los datos descargados hoy no se consideran conocidos en el pasado."}


def exportar(con, simbolo=""):
    salida = io.StringIO(newline="")
    columnas = COLUMNAS + ["origen", "hora_fuente", "disponible_desde", "confirmado_en"]
    escritor = csv.DictWriter(salida, fieldnames=columnas, extrasaction="ignore")
    escritor.writeheader()
    for fila in observaciones(con, simbolo):
        # Neutraliza fórmulas al abrir la exportación en una hoja de cálculo.
        fila = {k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
                for k, v in fila.items()}
        escritor.writerow(fila)
    return salida.getvalue()
