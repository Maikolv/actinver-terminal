"""Ciclo del motor en un proceso aparte, con prioridad baja.

El ciclo (propuestas ≈ 6–20 min, investigación ≈ 4–9 min) corría en un hilo del servidor: Python solo ejecuta un hilo a
la vez, así que mientras calculaba, las rutas de la interfaz esperaban (plan 79 s, Option Flow 24 s el 5-nov-2026).
Todo el estado del ciclo vive en la base (etapas, propuestas, alertas), por eso puede correr en otro proceso sin cambios.
El servidor conserva `servicios.bloqueo` mientras el hijo trabaja: un cálculo pedido por la API no convive con el ciclo.
Se apaga con `[app] motor_proceso_aparte = false`; en demo y en pruebas el ciclo sigue dentro del proceso.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys

from . import servicios
from .config import RAIZ, Ajustes, modo_activo

log = logging.getLogger("terminal.motor")
LIMITE_S = 3 * 3600


def ciclo_seguro(ajustes: Ajustes, forzar: bool = False, en_vivo: bool = False) -> dict | None:
    """Mismo contrato que `servicios.ciclo_seguro`: None si había otro ciclo o falló."""
    if ajustes.es_demo or not ajustes["app"].get("motor_proceso_aparte", True):
        return servicios.ciclo_seguro(ajustes, forzar, en_vivo)
    if not servicios.bloqueo.acquire(blocking=False):
        return None
    try:
        orden = [sys.executable, "-m", "terminal.motor_aislado", *(["--forzar"] if forzar else []),
                 *(["--en-vivo"] if en_vivo else [])]
        banderas = (subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS) if os.name == "nt" else 0
        r = subprocess.run(orden, cwd=RAIZ, env={**os.environ, "TERMINAL_MODO": modo_activo()}, timeout=LIMITE_S,
                           creationflags=banderas, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if r.returncode != 0:
            log.error("el ciclo en proceso aparte terminó con código %s (detalle en data/terminal_motor.log)", r.returncode)
            return None
        return {"proceso": "aparte"}
    except (OSError, subprocess.TimeoutExpired):
        log.exception("no se pudo completar el ciclo en proceso aparte")
        return None
    finally:
        servicios.bloqueo.release()


def _principal() -> int:
    import logging.handlers

    from .config import cargar_ajustes, data_dir
    h = logging.handlers.RotatingFileHandler(data_dir() / "terminal_motor.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[h])
    logging.getLogger("httpx").setLevel(logging.WARNING)  # nunca registrar URLs con credenciales
    r = servicios.ciclo_seguro(cargar_ajustes(), forzar="--forzar" in sys.argv, en_vivo="--en-vivo" in sys.argv)
    return 0 if r is not None else 3


if __name__ == "__main__":
    sys.exit(_principal())
