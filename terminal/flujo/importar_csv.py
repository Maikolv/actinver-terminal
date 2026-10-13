"""Importación de CSV autorizados por el usuario (velas, libro, operaciones, opciones). Todo o nada.

Reglas: encabezados exactos y en orden, UTF-8, ≤ 5 MB y ≤ 50,000 filas; instantes ISO 8601 con zona horaria y no
futuros; precios > 0; tamaños ≥ 0; libro sin cruzar; OHLC consistente. La licencia la declara el usuario y se guarda
con cada fila; la calidad queda como «importado».
"""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import UTC, date, datetime

from .. import db
from . import almacen
from .contratos import (INTERVALOS, Barra, ContratoOpcion, Libro, Nivel, Operacion, Procedencia, instante, opcional,
                        positivo, simbolo)

MAX_BYTES = 5_000_000
MAX_FILAS = 50_000
COLUMNAS = {
    "velas": ["simbolo", "mercado", "intervalo", "inicio", "apertura", "maximo", "minimo", "cierre", "volumen",
              "fuente", "licencia"],
    "operaciones": ["simbolo", "mercado", "instante", "precio", "tamano", "lado", "id_origen", "fuente", "licencia"],
    "libro": ["simbolo", "mercado", "instante", "lado", "nivel", "precio", "tamano", "fuente", "licencia"],
    "opciones": ["contrato", "subyacente", "mercado", "vencimiento", "strike", "tipo", "instante", "bid", "ask", "ultimo",
                 "volumen", "interes_abierto", "iv", "delta", "gamma", "theta", "vega", "fuente", "licencia"],
}


def plantilla(tipo: str) -> str:
    return ",".join(COLUMNAS[tipo]) + "\n"


def _texto(f, campo, maximo=80):
    v = str(f.get(campo) or "").strip()
    if not v or len(v) > maximo:
        raise ValueError(f"{campo}: requerido (máximo {maximo} caracteres)")
    return v


def importar(con, tipo: str, contenido: bytes, ahora: datetime | None = None) -> dict:
    if tipo not in COLUMNAS:
        raise ValueError("tipo de importación desconocido")
    if len(contenido) > MAX_BYTES:
        raise ValueError("archivo demasiado grande (máx. 5 MB)")
    ahora = ahora or datetime.now(UTC)
    try:
        lector = csv.DictReader(io.StringIO(contenido.decode("utf-8-sig")), restkey="_extra", strict=True)
        if lector.fieldnames != COLUMNAS[tipo]:
            raise ValueError("use exactamente los encabezados y el orden de la plantilla: " + ",".join(COLUMNAS[tipo]))
        grupos: dict[tuple, list] = defaultdict(list)   # (fuente, licencia, mercado) → filas válidas
        libros: dict[tuple, list] = defaultdict(list)
        n = 0
        for i, f in enumerate(lector, start=2):
            n += 1
            if n > MAX_FILAS:
                raise ValueError(f"máximo {MAX_FILAS:,} filas")
            try:
                if f.get("_extra") or any(f.get(c) is None for c in COLUMNAS[tipo]):
                    raise ValueError("número de columnas incorrecto")
                clave = (_texto(f, "fuente"), _texto(f, "licencia", 200), _texto(f, "mercado", 40))
                if tipo == "velas":
                    if f["intervalo"] not in INTERVALOS:
                        raise ValueError("intervalo: use " + ", ".join(INTERVALOS))
                    b = Barra(simbolo(f["simbolo"]), f["intervalo"], instante(f["inicio"], ahora),
                              positivo(f["apertura"], "apertura"), positivo(f["maximo"], "maximo"),
                              positivo(f["minimo"], "minimo"), positivo(f["cierre"], "cierre"),
                              opcional(f["volumen"], "volumen"))
                    b.validar()
                    grupos[clave].append(b)
                elif tipo == "operaciones":
                    lado = (f["lado"] or "").strip().lower() or None
                    if lado not in (None, "compra", "venta"):
                        raise ValueError("lado: compra, venta o vacío (si la fuente no lo informa)")
                    grupos[clave].append(Operacion(simbolo(f["simbolo"]), instante(f["instante"], ahora),
                                                   positivo(f["precio"], "precio"), positivo(f["tamano"], "tamano"),
                                                   lado, str(f["id_origen"] or "")[:64]))
                elif tipo == "libro":
                    lado = (f["lado"] or "").strip().lower()
                    if lado not in ("bid", "ask"):
                        raise ValueError("lado: bid o ask")
                    nivel = int(f["nivel"])
                    if not 1 <= nivel <= 500:
                        raise ValueError("nivel: de 1 a 500")
                    libros[(*clave, simbolo(f["simbolo"]), instante(f["instante"], ahora))].append(
                        Nivel(lado, nivel, positivo(f["precio"], "precio"), positivo(f["tamano"], "tamano", cero=True)))
                else:
                    tipo_op = (f["tipo"] or "").strip().lower()
                    if tipo_op not in ("call", "put"):
                        raise ValueError("tipo: call o put")
                    venc = date.fromisoformat(f["vencimiento"]).isoformat()
                    bid, ask = opcional(f["bid"], "bid"), opcional(f["ask"], "ask")
                    if bid is not None and ask is not None and bid > ask:
                        raise ValueError("bid mayor que ask")
                    iv = opcional(f["iv"], "iv")
                    if iv is not None and iv > 10:
                        raise ValueError("iv: use fracción anual (0.35 = 35 %)")
                    griegas = {}
                    for g in ("delta", "gamma", "theta", "vega"):
                        v = f[g]
                        griegas[g] = None if v in (None, "") else float(v)
                    grupos[clave].append(ContratoOpcion(
                        _texto(f, "contrato", 40), simbolo(f["subyacente"]), venc, positivo(f["strike"], "strike"),
                        tipo_op, instante(f["instante"], ahora), bid, ask, opcional(f["ultimo"], "ultimo"),
                        opcional(f["volumen"], "volumen"), opcional(f["interes_abierto"], "interes_abierto"), iv,
                        origen_iv="importado" if iv is not None else None, **griegas))
            except (ValueError, TypeError) as e:
                raise ValueError(f"fila {i}: {e}") from None
    except UnicodeError:
        raise ValueError("el archivo debe ser CSV en UTF-8") from None
    except csv.Error:
        raise ValueError("CSV inválido") from None
    if not grupos and not libros:
        raise ValueError("el CSV no contiene registros")
    guardados = 0
    with db.transaccion(con):
        for (fuente, lic, mercado), filas in grupos.items():
            p = Procedencia(fuente, lic, mercado, calidad="importado",
                            nota="Importado por el usuario; la terminal no verifica la fuente ni el retraso.")
            if tipo == "velas":
                guardados += almacen.guardar_barras(con, filas, p)
            elif tipo == "operaciones":
                guardados += almacen.guardar_operaciones(con, filas, p)
            else:
                guardados += almacen.guardar_opciones(con, filas, p)
        for (fuente, lic, mercado, sim, inst), niveles in libros.items():
            libro = Libro(sim, inst, niveles)
            try:
                libro.validar()
            except ValueError as e:
                raise ValueError(f"libro {sim} {inst}: {e}") from None
            guardados += almacen.guardar_libro(con, libro, Procedencia(
                fuente, lic, mercado, calidad="importado", nota="Importado por el usuario; la terminal no verifica la fuente."))
        db.auditar(con, "flujo", tipo, "importar", despues={"filas": n, "guardados": guardados})
    return {"tipo": tipo, "filas": n, "guardados": guardados, "calidad": "importado",
            "nota": "Datos importados por usted: se muestran como «importado», con la fuente y licencia que declaró."}
