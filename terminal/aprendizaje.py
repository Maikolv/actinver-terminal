"""Catálogo educativo verificado. Las capturas personales se leen sólo de data local."""
import json

from .config import CONFIG_DIR, data_dir


def catalogo(demo: bool = False) -> dict:
    contenido = json.loads((CONFIG_DIR / "aprendizaje.json").read_text(encoding="utf-8"))
    captura = data_dir("demo" if demo else "real") / "recursos" / "captura-referencia.json"
    contenido["captura_referencia"] = None
    if captura.exists():
        try:
            contenido["captura_referencia"] = json.loads(captura.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            contenido["captura_aviso"] = "No se pudo leer la captura local de referencia. No afecta cotizaciones."
    return contenido
