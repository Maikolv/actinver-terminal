"""Adaptadores de intercambio con repositorios externos, sin depender de su código.

1. Exportación a `hftbacktest` (MIT, nkaz001/hftbacktest): arreglo de eventos `event_dtype` en un `.npz` con la llave
   `data`, como lo documenta `py-hftbacktest/hftbacktest/types.py`. Libro → DEPTH_CLEAR + DEPTH_SNAPSHOT por nivel;
   operaciones → TRADE_EVENT con BUY/SELL solo si la fuente informó el lado. Marcas en nanosegundos:
   exch_ts = instante del evento; local_ts = hora de captura de la terminal.
2. Importación de velas exportadas por TradingView (botón «Exportar datos del gráfico»), OpenBB (`.to_csv()` de
   `obb.equity.price.historical`) u hojas tipo Yahoo/Excel (Date, Open, High, Low, Close, Volume). Se convierten a la
   plantilla de velas de la terminal y pasan por la misma validación (todo o nada, calidad «importado»).
"""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from .. import config
from . import almacen, importar_csv

# --- hftbacktest -------------------------------------------------------------------------------------------------
DEPTH_EVENT, TRADE_EVENT, DEPTH_CLEAR_EVENT, DEPTH_SNAPSHOT_EVENT = 1, 2, 3, 4
EXCH_EVENT, LOCAL_EVENT, BUY_EVENT, SELL_EVENT = 1 << 31, 1 << 30, 1 << 29, 1 << 28
EVENT_DTYPE = np.dtype([("ev", "u8"), ("exch_ts", "i8"), ("local_ts", "i8"), ("px", "f8"), ("qty", "f8"),
                        ("order_id", "u8"), ("ival", "i8"), ("fval", "f8")], align=True)


def _ns(iso: str) -> int:
    t = datetime.fromisoformat(iso)
    return int(t.timestamp()) * 1_000_000_000 + t.microsecond * 1000


def eventos_hftbacktest(con, simbolo: str, desde: str | None = None, demo: bool = False) -> tuple[np.ndarray, dict]:
    eventos = []
    corte = desde or ""
    filtro = "calidad = 'sintetico' OR calidad = 'importado'" if demo else "calidad <> 'sintetico'"
    libros = con.execute(f"SELECT * FROM flujo_libro WHERE simbolo=? AND instante >= ? AND ({filtro}) ORDER BY instante",
                         (simbolo, corte)).fetchall()
    for lb in libros:
        ex, lo = _ns(lb["instante"]), max(_ns(lb["capturado_en"]), _ns(lb["instante"]))
        niveles = con.execute("SELECT lado, nivel, precio, tamano FROM flujo_libro_niveles WHERE libro_id=? ORDER BY lado, nivel",
                              (lb["id"],)).fetchall()
        for lado in ("bid", "ask"):
            ladof = BUY_EVENT if lado == "bid" else SELL_EVENT
            n = [x for x in niveles if x["lado"] == lado]
            if not n:
                continue
            extremo = min(x["precio"] for x in n) if lado == "bid" else max(x["precio"] for x in n)
            eventos.append((DEPTH_CLEAR_EVENT | EXCH_EVENT | LOCAL_EVENT | ladof, ex, lo, extremo, 0.0, 0, 0, 0.0))
            eventos += [(DEPTH_SNAPSHOT_EVENT | EXCH_EVENT | LOCAL_EVENT | ladof, ex, lo, x["precio"], x["tamano"], 0, 0, 0.0)
                        for x in n]
    ops = almacen.operaciones(con, simbolo, desde, demo=demo, limite=1_000_000)
    con_lado = 0
    for o in ops:
        lado = BUY_EVENT if o["lado"] == "compra" else SELL_EVENT if o["lado"] == "venta" else 0
        con_lado += bool(lado)
        eventos.append((TRADE_EVENT | EXCH_EVENT | LOCAL_EVENT | lado, _ns(o["instante"]),
                        max(_ns(o["capturado_en"]), _ns(o["instante"])), o["precio"], o["tamano"], 0, 0, 0.0))
    arr = np.array(eventos, dtype=EVENT_DTYPE)
    if len(arr):
        arr = arr[np.argsort(arr["exch_ts"], kind="stable")]
    info = {"simbolo": simbolo, "eventos": int(len(arr)), "instantaneas_libro": len(libros), "operaciones": len(ops),
            "operaciones_con_lado": con_lado,
            "advertencias": [a for a in (
                "Instantáneas del libro espaciadas (se capturan al pulsar «Actualizar»): no equivalen a un libro continuo; "
                "sirven para probar el formato o estrategias lentas, no colas de alta frecuencia." if libros else None,
                f"{len(ops) - con_lado} operaciones sin lado del agresor: se exportan sin bandera BUY/SELL." if len(ops) > con_lado else None,
                "Sin datos para exportar." if not len(arr) else None) if a]}
    return arr, info


def exportar_hftbacktest(con, simbolo: str, carpeta: Path | None = None, desde: str | None = None, demo: bool = False) -> dict:
    arr, info = eventos_hftbacktest(con, simbolo, desde, demo)
    if not len(arr):
        raise ValueError("sin libro ni operaciones guardados para este símbolo")
    d = Path(carpeta or config.data_dir() / "exportaciones" / "hftbacktest")
    d.mkdir(parents=True, exist_ok=True)
    nombre = "".join(ch if ch.isalnum() else "_" for ch in simbolo) + f"_{datetime.now(UTC):%Y%m%dT%H%M%S}.npz"
    ruta = d / nombre
    np.savez_compressed(ruta, data=arr)
    return {**info, "archivo": str(ruta), "formato": "hftbacktest event_dtype (npz, llave «data»)",
            "uso": "En hftbacktest: BacktestAsset().data([ruta]) — consulte su documentación; la terminal no ejecuta backtests HFT."}


# --- velas exportadas por otras herramientas -----------------------------------------------------------------------
COLUMNAS_TIEMPO = ("time", "date", "datetime", "timestamp", "fecha")


def _formato(cabecera: list[str]) -> tuple[str, dict]:
    c = {h.strip().lower(): h for h in cabecera}
    t = next((c[k] for k in COLUMNAS_TIEMPO if k in c), None)
    falta = [k for k in ("open", "high", "low", "close") if k not in c]
    if not t or falta:
        raise ValueError("no se reconoce el formato: se esperan columnas de tiempo (time/date/datetime) y "
                         "open, high, low, close (volume opcional)")
    nombre = "tradingview" if t.lower() == "time" else "openbb" if t.lower() == "date" and "vwap" in c else "generico"
    return nombre, {"tiempo": t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"],
                    "volume": c.get("volume")}


def _a_utc(valor: str, zona: str) -> str:
    v = valor.strip()
    if v.replace(".", "", 1).isdigit():                          # tiempo Unix (TradingView), en s o ms
        x = float(v)
        return datetime.fromtimestamp(x / 1000 if x > 1e11 else x, UTC).isoformat()
    t = datetime.fromisoformat(v.replace("Z", "+00:00").replace(" ", "T", 1) if len(v) > 10 else v)
    if t.tzinfo is None:                                         # fecha u hora local de la bolsa indicada por el usuario
        t = t.replace(tzinfo=ZoneInfo(zona))
    return t.astimezone(UTC).isoformat()


def importar_velas_externas(con, contenido: bytes, simbolo: str, mercado: str, intervalo: str, fuente: str, licencia: str,
                            zona: str = "America/Mexico_City") -> dict:
    if len(contenido) > importar_csv.MAX_BYTES:
        raise ValueError("archivo demasiado grande (máx. 5 MB)")
    try:
        ZoneInfo(zona)
    except Exception:  # noqa: BLE001
        raise ValueError("zona horaria desconocida (p. ej. America/Mexico_City o America/New_York)") from None
    try:
        lector = csv.DictReader(io.StringIO(contenido.decode("utf-8-sig")))
        nombre, col = _formato(lector.fieldnames or [])
        salida = io.StringIO()
        w = csv.writer(salida, lineterminator="\n")
        w.writerow(importar_csv.COLUMNAS["velas"])
        n = 0
        for i, f in enumerate(lector, start=2):
            try:
                w.writerow([simbolo, mercado, intervalo, _a_utc(f[col["tiempo"]], zona), f[col["open"]], f[col["high"]],
                            f[col["low"]], f[col["close"]], (f.get(col["volume"]) or "") if col["volume"] else "", fuente, licencia])
            except (ValueError, KeyError, TypeError) as e:
                raise ValueError(f"fila {i}: {e}") from None
            n += 1
    except UnicodeError:
        raise ValueError("el archivo debe ser CSV en UTF-8") from None
    if not n:
        raise ValueError("el archivo no tiene filas")
    r = importar_csv.importar(con, "velas", salida.getvalue().encode("utf-8"))
    return {**r, "formato_detectado": nombre, "zona_supuesta_para_fechas_sin_zona": zona}
