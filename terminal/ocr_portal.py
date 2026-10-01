"""Capturas de pantalla del portafolio del Reto → texto para «Mi portafolio Actinver».

Por qué así:
- El reglamento (§17) prohíbe programas en el portal: la terminal no lo abre ni lo lee. El participante toma la captura
  de pantalla él mismo (Win+Shift+S) y la sube o la pega aquí.
- El OCR es el de Windows (Windows.Media.Ocr, español): corre en esta PC, sin descargas ni servicios externos. Las
  imágenes se procesan en memoria y no se guardan.
- El OCR se equivoca con separadores («$995.116.81», «$611.62509»): los montos del portal siempre llevan centavos, así
  que se reconstruyen con sus dígitos. El resultado NO se guarda solo: pasa por la misma vista previa que el texto
  pegado (cuadre con la valuación, emisoras reconocidas, duplicados) y el participante lo confirma.
"""
from __future__ import annotations

import asyncio
import re
import statistics
import unicodedata
from dataclasses import dataclass

from . import cotizaciones

LIMITE_BYTES = 8_000_000
MAX_IMAGENES = 6
FIRMAS = (b"\x89PNG", b"\xff\xd8\xff", b"BM", b"GIF8")
RESUMEN = (("valuacion total", "Valuación total"), ("inversiones", "Inversiones"), ("poder de compra", "Poder de compra"),
           ("movimientos por liquidar", "Movimientos por liquidar"), ("efectivo disponible", "Efectivo disponible"))
COLUMNAS = {"emisora": ("emisora",), "titulos": ("titulos",), "costo_unitario": ("valor al costo",),
            "costo_total": ("costo",), "precio": ("precio actual",)}
ESCALA_ANCHO = 2400  # se amplía la captura hasta ~2400 px de ancho: el OCR lee mejor el «$» y los dígitos sueltos


class OcrNoDisponible(RuntimeError):
    pass


class ErrorImagen(ValueError):
    pass


@dataclass
class Palabra:
    texto: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class Celda:
    texto: str
    x0: float
    x1: float
    y: float

    @property
    def centro(self) -> float:
        return (self.x0 + self.x1) / 2


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip(" :")


def disponible() -> bool:
    """Sin importar WinRT en este proceso (sus DLL chocan con las de scipy): solo comprueba que el paquete exista."""
    import importlib.util
    import sys
    try:
        return sys.platform == "win32" and importlib.util.find_spec("winrt.windows.media.ocr") is not None
    except (ImportError, ValueError):
        return False


async def _palabras_async(data: bytes, ampliar: bool) -> list[Palabra]:
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
    stream = InMemoryRandomAccessStream()
    w = DataWriter(stream)
    w.write_bytes(data)
    await w.store_async()
    await w.flush_async()
    w.detach_stream()
    stream.seek(0)
    try:
        dec = await BitmapDecoder.create_async(stream)
        bmp = await _preparar(dec, ampliar) if ampliar else await dec.get_software_bitmap_async()  # 1ª lectura: tal cual
    except Exception as e:  # noqa: BLE001 - imagen dañada o formato no admitido
        raise ErrorImagen("No se pudo leer la imagen (use PNG o JPG).") from e
    motor = None
    for tag in ("es-MX", "es-ES"):
        motor = OcrEngine.try_create_from_language(Language(tag))
        if motor:
            break
    motor = motor or OcrEngine.try_create_from_user_profile_languages()
    if not motor:
        raise OcrNoDisponible("Windows no tiene un idioma de OCR instalado (Configuración → Idioma → español).")
    r = await motor.recognize_async(bmp)
    return [Palabra(wd.text, wd.bounding_rect.x, wd.bounding_rect.y, wd.bounding_rect.width, wd.bounding_rect.height)
            for linea in r.lines for wd in linea.words]


async def _preparar(dec, ampliar: bool):
    """Pasa a gris con el canal más claro (el texto verde, rojo o azul del portal queda legible) y, si se pide, amplía
    hasta ~2400 px de ancho (máx. 3×): en tablas de letra chica el OCR lee mejor el «$» y los dígitos sueltos."""
    import numpy as np
    from winrt.windows.graphics.imaging import (BitmapAlphaMode, BitmapInterpolationMode, BitmapPixelFormat,
                                                BitmapTransform, ColorManagementMode, ExifOrientationMode, SoftwareBitmap)
    from winrt.windows.storage.streams import DataWriter
    f = max(1.0, min(3.0, ESCALA_ANCHO / max(dec.pixel_width, 1))) if ampliar else 1.0
    ancho, alto = int(dec.pixel_width * f), int(dec.pixel_height * f)
    t = BitmapTransform()
    t.scaled_width, t.scaled_height, t.interpolation_mode = ancho, alto, BitmapInterpolationMode.FANT
    prov = await dec.get_pixel_data_transformed_async(BitmapPixelFormat.BGRA8, BitmapAlphaMode.PREMULTIPLIED, t,
                                                       ExifOrientationMode.IGNORE_EXIF_ORIENTATION,
                                                       ColorManagementMode.DO_NOT_COLOR_MANAGE)
    px = np.frombuffer(bytes(prov.detach_pixel_data()), dtype=np.uint8).reshape(alto, ancho, 4).copy()
    gris = px[..., :3].max(axis=2)
    px[..., 0] = px[..., 1] = px[..., 2] = gris
    px[..., 3] = 255
    dw = DataWriter()
    dw.write_bytes(px.tobytes())
    bmp = SoftwareBitmap(BitmapPixelFormat.BGRA8, ancho, alto, BitmapAlphaMode.PREMULTIPLIED)
    bmp.copy_from_buffer(dw.detach_buffer())
    return bmp


def leer(data: bytes, ampliar: bool = True) -> list[Palabra]:
    """Palabras con su posición (en este proceso; la terminal usa `leer_captura`, que lo aísla en otro)."""
    _validar(data)
    if not disponible():
        raise OcrNoDisponible("El lector de capturas usa el OCR de Windows y no está disponible en este equipo; copie y "
                              "pegue el texto del portal.")
    return asyncio.run(_palabras_async(data, ampliar))


def _validar(data: bytes) -> None:
    if not data:
        raise ErrorImagen("La imagen está vacía.")
    if len(data) > LIMITE_BYTES:
        raise ErrorImagen(f"La imagen pesa más de {LIMITE_BYTES // 1_000_000} MB.")
    if not data.startswith(FIRMAS):
        raise ErrorImagen("Formato no admitido: use una captura PNG o JPG.")


def _leer_en_proceso(data: bytes) -> tuple[list[Palabra], list[Palabra]]:
    """El OCR corre en un proceso aparte: sus bibliotecas nativas (WinRT) chocan con las de scipy/cvxpy si comparten
    proceso, y así un fallo del OCR nunca detiene la terminal."""
    import json
    import subprocess
    import sys
    banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run([sys.executable, "-m", "terminal.ocr_portal"], input=data, capture_output=True, timeout=120,
                           creationflags=banderas)
    except subprocess.TimeoutExpired:
        raise ErrorImagen("La lectura de la captura tardó demasiado; intente con una imagen más pequeña.") from None
    if r.returncode == 3:
        raise OcrNoDisponible(r.stderr.decode("utf-8", "replace").strip()[-300:])
    if r.returncode != 0:
        raise ErrorImagen(r.stderr.decode("utf-8", "replace").strip()[-300:] or "No se pudo leer la imagen.")
    d = json.loads(r.stdout.decode("utf-8"))
    return tuple([Palabra(**w) for w in d[k]] for k in ("original", "ampliada"))


def leer_captura(data: bytes, instrumentos: dict) -> dict:
    """Dos lecturas (tamaño original y ampliada) combinadas: cada una acierta en cosas distintas según el tamaño de la
    letra de la captura. Si discrepan en un monto o en títulos, se avisa."""
    _validar(data)
    if not disponible():
        raise OcrNoDisponible("El lector de capturas usa el OCR de Windows y no está disponible en este equipo; copie y "
                              "pegue el texto del portal.")
    pa, pb = _leer_en_proceso(data)
    a, b = interpretar(pa, instrumentos), interpretar(pb, instrumentos)
    resumen, avisos = dict(b["resumen"]), list(b["avisos"])
    for k, v in a["resumen"].items():
        if k not in resumen:
            resumen[k] = v
        elif abs(resumen[k] - v) > 0.005:
            avisos.append(f"«{k}»: dos lecturas distintas ({resumen[k]:,.2f} y {v:,.2f}); se usó {resumen[k]:,.2f}, revíselo.")
    pos = {p["emisora"]: p for p in b["posiciones"]}
    for p in a["posiciones"]:
        q = pos.get(p["emisora"])
        if not q or p.get("puntos", 0) > q.get("puntos", 0):  # gana la lectura cuya fila cuadra
            fusion = dict(p)
            for k, v in (q or {}).items():
                if fusion.get(k) is None:
                    fusion[k] = v
            pos[p["emisora"]] = fusion
            continue
        for campo in ("titulos", "costo_unitario", "precio"):
            if q[campo] is None:
                q[campo] = p[campo]
            elif False:  # con la fila coherente elegida, la otra lectura no se reporta (solo confunde)
                avisos.append(f"{p['emisora']}: dos lecturas de {campo.replace('_', ' ')} ({q[campo]} y {p[campo]}); "
                              f"se usó {q[campo]}, revíselo.")
    for q in pos.values():
        if q.get("puntos", 0) < 3:
            avisos.append(f"{q['emisora']}: la fila no cuadra del todo (títulos, costo y precio); compárela con la captura.")
    lectura = [" | ".join(c.texto for c in f) for f in filas(pb)][:80]  # lo que leyó el OCR (para revisar a mano)
    legibles = set(pos)
    avisos += [x for x in a["avisos"] if not any(e in x for e in legibles)]
    avisos = [x for x in avisos if not (x.startswith("Fila no legible") and any(e in x for e in legibles))]
    return {"resumen": resumen, "posiciones": list(pos.values()), "avisos": list(dict.fromkeys(avisos)), "lectura": lectura}


# ------------------------------------------------------------------------------------------------------------------
def filas(palabras: list[Palabra]) -> list[list[Celda]]:
    """Agrupa palabras en filas (misma altura) y, dentro de cada fila, en celdas (huecos grandes separan columnas)."""
    if not palabras:
        return []
    alto = statistics.median(p.h for p in palabras) or 10
    orden = sorted(palabras, key=lambda p: p.y + p.h / 2)
    grupos: list[list[Palabra]] = []
    for p in orden:
        yc = p.y + p.h / 2
        if grupos and abs(yc - statistics.mean(q.y + q.h / 2 for q in grupos[-1])) <= 0.6 * alto:
            grupos[-1].append(p)
        else:
            grupos.append([p])
    out = []
    for g in grupos:
        g.sort(key=lambda p: p.x)
        celdas: list[Celda] = []
        for p in g:
            if celdas and p.x - celdas[-1].x1 <= 1.2 * alto:
                c = celdas[-1]
                c.texto, c.x1 = f"{c.texto} {p.texto}", max(c.x1, p.x + p.w)
            else:
                celdas.append(Celda(p.texto, p.x, p.x + p.w, p.y))
        out.append(celdas)
    return out


def _limpiar_monto(t: str) -> str:
    """Confusiones típicas del OCR en montos: «$1» → «SI», «$» → «s»/«S», «8» → «&», «0» → «o», «1» → «l»."""
    s = str(t or "").strip()
    s = re.sub(r"^(-?)\s*[sS$]\s*[Il|](?=[\s\d,.oO])", r"\g<1>$1", s)   # «SI 20,192.56» = «$120,192.56»
    s = re.sub(r"^(-?)\s*[sS](?=[\s\doO.,])", r"\1$", s)                # «so.oo» = «$0.00»
    s = s.replace("&", "8").replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
    return re.sub(r"(?<=\d)\s+(?=[\d,.])|(?<=[,.])\s+(?=\d)", "", s)     # «38,244 72» → «38,24472»


def monto(t: str) -> float | None:
    """Monto del portal (siempre con centavos): «$995.116.81», «$611.62509» o «-$4,883.19» → número."""
    s = _limpiar_monto(t)
    digitos = re.sub(r"\D", "", s)
    if not digitos:
        return None
    v = int(digitos) / 100 if re.search(r"[.,]", s) else float(digitos)
    return -v if re.search(r"-\s*\$?\s*\d", s) else v


def candidatos(t: str) -> list[float]:
    """Lecturas posibles de un monto de la tabla: tal cual y sin el primer carácter cuando el «$» se leyó como 3, 5 o S.
    La fila decide cuál es coherente (costo ÷ costo unitario entero y precio cercano al costo)."""
    s = _limpiar_monto(t).lstrip("-").strip()
    out = []
    v = monto(s)
    if v is not None:
        out.append(v)
    if not s.startswith("$") and len(re.sub(r"\D", "", s)) > 3 and s[:1] in "35":
        w = monto(s[1:])
        if w is not None:
            out.append(w)
    return list(dict.fromkeys(out))


def _resolver(unit_t: str | None, total_t: str | None, precio_t: str | None, titulos: int | None):
    """(títulos, costo unitario, precio, puntos) coherentes entre sí. El «Costo» del portal incluye la comisión, así que
    costo ÷ costo unitario se acepta como entero con 0.1 % de tolerancia; el precio debe estar cerca del costo (0.4×–2.5×).
    puntos: 3 = fila coherente; menos = algún dato dudoso."""
    import math
    U = candidatos(unit_t) if unit_t else []
    T = candidatos(total_t) if total_t else []
    P = candidatos(precio_t) if precio_t else []
    mejor = None
    for u in U:
        for t in T or [None]:
            q = t / u if (t and u) else None
            # el costo unitario viene redondeado a centavos: con muchos títulos el cociente puede desviarse 1 o 2 títulos
            tol = max(0.6, 0.0005 * (q or 0) * 2) if q else 0
            if q is not None and titulos is not None and abs(q - titulos) <= tol:
                n = titulos  # el OCR leyó los títulos y el costo lo confirma
            else:
                n = round(q) if q else None
            ok_n = n is not None and n > 0 and q is not None and abs(q - n) <= tol
            for pr in P or [None]:
                ok_p = pr is not None and u > 0 and 0.4 <= pr / u <= 2.5
                cercania = -abs(math.log(pr / u)) if (ok_p and pr > 0) else -9
                coincide = titulos is not None and n == titulos  # desempate: confirma los títulos que leyó el OCR
                clave = (2 * ok_n + ok_p, coincide, cercania)
                if mejor is None or clave > mejor[0]:
                    mejor = (clave, (n if ok_n else titulos), u, pr if ok_p else (pr if len(P) == 1 else None))
    if mejor is None:
        return titulos, None, (P[0] if len(P) == 1 else None), 0
    return mejor[1], mejor[2], mejor[3], mejor[0][0]


def entero(t: str) -> int | None:
    d = re.sub(r"\D", "", str(t or ""))
    return int(d) if d else None


def _parecido(a: str, b: str) -> bool:
    import difflib
    return a.startswith(b) or difflib.SequenceMatcher(None, a[:len(b) + 2], b).ratio() >= 0.75


def _sin_espacios(t: str) -> str:
    return _norm(t).replace(" ", "")


def _emisora(texto: str, instrumentos: dict) -> str | None:
    """Clave operable reconocida; el icono «?» del portal suele leerse como un carácter suelto al final."""
    limpio = re.sub(r"[^A-Za-z0-9&*\- ]", " ", texto).split()
    for n in range(len(limpio), 0, -1):
        try:
            r = cotizaciones.normalizar_simbolo(" ".join(limpio[:n]), instrumentos)
        except ValueError:
            r = None
        if r:
            return instrumentos.get(r["instrumento_id"], {}).get("clave_operable") or " ".join(limpio[:n])
    return None


def interpretar(palabras: list[Palabra], instrumentos: dict) -> dict:
    """Resumen («Tu inversión» / «Portafolio») y tabla de posiciones de UNA captura."""
    resumen, posiciones, avisos = {}, [], []
    cols, y_cab, pendiente = None, None, None
    for fila in filas(palabras):
        textos = [_norm(c.texto) for c in fila]
        # resumen: etiqueta y monto en la misma fila, o el monto en la fila de abajo («Valuación total» del portafolio)
        if pendiente and len(fila) == 1 and "$" in fila[0].texto and pendiente not in resumen:
            v = monto(fila[0].texto)
            if v is not None:
                resumen[pendiente] = v
        pendiente = None
        for pref, etiqueta in RESUMEN:
            if textos and _sin_espacios(textos[0]).startswith(pref.replace(" ", "")) and etiqueta not in resumen:
                montos = [monto(c.texto) for c in fila[1:] if re.search(r"[\doO]", c.texto)]
                if montos and montos[-1] is not None:
                    resumen[etiqueta] = montos[-1]
                elif len(fila) == 1:
                    pendiente = etiqueta
        # encabezado de la tabla
        if sum(any(_parecido(t, h) for t in textos) for h in ("emisora", "titulos", "valor al costo", "precio actual")) >= 2:
            cabecera = fila
            cols = {}
            for campo, sins in COLUMNAS.items():
                exacta = campo == "costo_total"  # «Costo» a secas; «Valor al Costo» es el costo unitario
                c = next((c for c, t in zip(fila, textos)
                          if any((t == s) if exacta else _parecido(t, s) for s in sins)), None)
                if c:
                    cols[campo] = c
            y_cab = fila[0].y
            continue
        ancla = any(t.startswith("ver") for t in textos[:2])  # cada fila del portal empieza con «Ver Detalle»
        if not ancla and (not cols or "emisora" not in cols or fila[0].y <= (y_cab or 0)):
            continue
        if ancla and not cols:  # sin encabezado legible: posición de la celda tras «Ver Detalle»
            cabecera, cols = fila, {"emisora": fila[min(1, len(fila) - 1)]}

        asignadas: dict[int, Celda] = {}  # cada celda va a la columna del encabezado más cercana
        for c in fila:
            j = min(range(len(cabecera)), key=lambda k: abs(cabecera[k].centro - c.centro))
            if j not in asignadas or abs(c.centro - cabecera[j].centro) < abs(asignadas[j].centro - cabecera[j].centro):
                asignadas[j] = c

        def celda(campo):
            ref = cols.get(campo)
            return asignadas.get(next((k for k, h in enumerate(cabecera) if h is ref), -1)) if ref else None

        ce, ct = celda("emisora"), celda("titulos")
        if not ce:
            continue
        clave = _emisora(ce.texto, instrumentos)
        titulos = entero(ct.texto) if ct else None
        cu, cp, cc = celda("costo_unitario"), celda("precio"), celda("costo_total")
        # El portal siempre ordena: Valor al Costo, Costo, Precio Actual, Plusvalía. Con 3 o más montos con «$» a la
        # derecha de la emisora se toman por posición (no depende de que el OCR haya leído cada encabezado).
        es_monto = lambda c: (re.search(r"[$sS]", c.texto) or len(re.sub(r"\D", "", c.texto)) > 3) and "%" not in c.texto
        montos_fila = [c for c in fila if c.x0 > ce.x1 and es_monto(c) and not c.texto.strip().startswith("-")
                       and c is not ct]
        if len(montos_fila) >= 3:  # orden fijo del portal: Valor al Costo, Costo, Precio Actual (Plusvalía al final)
            cu, cc, cp = montos_fila[0], montos_fila[1], montos_fila[2]
        n_ocr = titulos
        titulos, unit, precio_res, puntos = _resolver(cu.texto if cu else None, cc.texto if cc else None,
                                                      cp.texto if cp else None, n_ocr)
        if n_ocr is not None and titulos is not None and n_ocr != titulos:
            avisos.append(f"{clave or ce.texto}: el OCR leyó {n_ocr} títulos; costo ÷ costo unitario da {titulos} y se "
                          "usó ese valor (revíselo).")
        titulos = titulos if titulos is not None else n_ocr
        if not clave or titulos is None:
            avisos.append(f"Fila no legible: «{' '.join(c.texto for c in fila)[:80]}» (corríjala en el texto).")
            continue
        posiciones.append({"emisora": clave, "titulos": titulos, "costo_unitario": unit, "precio": precio_res,
                           "puntos": puntos})
    return {"resumen": resumen, "posiciones": posiciones, "avisos": avisos}


def texto_para_captura(resultados: list[dict]) -> dict:
    """Une varias capturas (resumen y una o más páginas de la tabla) en el formato que entiende `portal.interpretar`."""
    resumen, posiciones, avisos, vistas = {}, [], [], set()
    for r in resultados:
        for k, v in r["resumen"].items():
            resumen.setdefault(k, v)
        for p in r["posiciones"]:
            if p["emisora"] in vistas:
                avisos.append(f"{p['emisora']} aparece en dos capturas; se tomó la primera.")
                continue
            vistas.add(p["emisora"])
            posiciones.append(p)
        avisos += r["avisos"]
    if "Valuación total" not in resumen and "Inversiones" in resumen and "Poder de compra" in resumen:
        resumen["Valuación total"] = round(resumen["Inversiones"] + resumen["Poder de compra"]
                                           + resumen.get("Movimientos por liquidar", 0.0), 2)
        avisos.append("La «Valuación total» no se leyó: se calculó con el resumen del portal (inversiones + poder de "
                      "compra + por liquidar) para verificar las posiciones.")
    lineas = [f"{k}\t${v:,.2f}" for k, v in resumen.items()]
    if posiciones:
        lineas.append("Emisora\tTítulos\tValor al Costo\tPrecio Actual")
        for p in posiciones:
            lineas.append(f"{p['emisora']}\t{p['titulos']:,}\t"
                          + (f"{p['costo_unitario']:.2f}" if p["costo_unitario"] is not None else "") + "\t"
                          + (f"{p['precio']:.2f}" if p["precio"] is not None else ""))
    if not resumen:
        avisos.append("No se leyó el resumen («Valuación total», «Poder de compra»…): suba también esa captura o escriba "
                      "los montos.")
    if not posiciones:
        avisos.append("No se leyó la tabla de posiciones: suba la captura de «Ver detalle de mi inversión».")
    if any(p["precio"] is None for p in posiciones):
        avisos.append("Hay posiciones sin precio legible; revise el texto antes de la vista previa.")
    return {"texto": "\n".join(lineas), "avisos": avisos, "resumen": resumen, "n_posiciones": len(posiciones),
            "lectura": [x for r in resultados for x in r.get("lectura", [])],
            "nota": "Texto leído por OCR en esta PC: revíselo contra su captura. Nada se guarda hasta que confirme."}


if __name__ == "__main__":  # proceso aislado: imagen por stdin → palabras de las dos lecturas en JSON por stdout
    import dataclasses
    import json
    import sys
    try:
        datos = sys.stdin.buffer.read()
        salida = {"original": [dataclasses.asdict(w) for w in leer(datos, ampliar=False)],
                  "ampliada": [dataclasses.asdict(w) for w in leer(datos, ampliar=True)]}
    except OcrNoDisponible as e:
        sys.stderr.write(str(e))
        sys.exit(3)
    except ErrorImagen as e:
        sys.stderr.write(str(e))
        sys.exit(2)
    sys.stdout.write(json.dumps(salida))
