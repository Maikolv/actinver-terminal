"""Perfil reproducible de importación; sin servidor, credenciales, motor ni conexiones."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).resolve().parent
HIJO = r'''
import ctypes, json, os, socket, time
def prohibida(*args, **kwargs):
    raise OSError('Perfil offline: conexiones prohibidas')
socket.socket.connect = prohibida
socket.socket.connect_ex = prohibida
inicio = time.perf_counter()
import terminal.app
duracion = time.perf_counter() - inicio
class Memoria(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
        (n, ctypes.c_size_t) for n in ('PeakWorkingSetSize', 'WorkingSetSize',
        'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
        'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]
memoria = Memoria()
memoria.cb = ctypes.sizeof(memoria)
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetCurrentProcess.restype = ctypes.c_void_p
psapi = ctypes.WinDLL('psapi', use_last_error=True)
psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Memoria), ctypes.c_ulong]
if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(memoria), memoria.cb):
    raise OSError('No se pudo medir memoria del proceso propio')
print(json.dumps({'importacion_ms': duracion * 1000,
    'privada_bytes': memoria.PrivateUsage, 'rss_bytes': memoria.WorkingSetSize,
    'pico_rss_bytes': memoria.PeakWorkingSetSize,
    'pico_comprometido_bytes': memoria.PeakPagefileUsage}))
'''


def main():
    if os.name != "nt":
        raise SystemExit("Este perfil de memoria requiere Windows.")
    # Se heredan solo variables de Windows necesarias para ejecutar Python, nunca claves.
    nombres = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA"}
    entorno = {k: v for k, v in os.environ.items() if k.upper() in nombres}
    entorno.update(TERMINAL_SIN_ENV="1", TERMINAL_SIN_CONFIG_LOCAL="1", TERMINAL_SIN_MOTOR="1",
                   TERMINAL_MODO="real", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    resultado = {"fecha": __import__("datetime").datetime.now().astimezone().isoformat(),
                 "python": platform.python_version(), "sistema": platform.platform(),
                 "procesador": platform.processor(), "procesadores_logicos": os.cpu_count(),
                 "alcance": "Importación instrumentada, no arranque HTTP ni memoria de navegador.",
                 "cache": "Proceso nuevo por repetición; caché de disco Windows sin purgar.",
                 "fuentes": "Sin datos ni proveedores; base temporal vacía; conexiones prohibidas.",
                 "sha256_app": hashlib.sha256((RAIZ / "terminal/app.py").read_bytes()).hexdigest(),
                 "repeticiones": []}
    for numero in range(1, 4):
        with tempfile.TemporaryDirectory(prefix="perfil-importacion-") as temporal:
            entorno["TERMINAL_DATA_DIR"] = temporal
            proceso = subprocess.run([sys.executable, "-X", "importtime", "-c", HIJO], cwd=RAIZ,
                                     env=entorno, capture_output=True, text=True, timeout=240)
        # El perfil contiene nombres y tiempos de módulos; no se guardan salidas arbitrarias.
        lineas = [l for l in proceso.stderr.splitlines() if l.startswith("import time:")]
        (SALIDA / f"importaciones-{numero}.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
        if proceso.returncode:
            raise SystemExit(f"Falló la repetición {numero}; código {proceso.returncode}. Sin publicar stderr.")
        medicion = json.loads(proceso.stdout)
        resultado["repeticiones"].append({"numero": numero, **medicion})
        (SALIDA / "perfil-importaciones.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Repetición {numero} registrada.", flush=True)


if __name__ == "__main__":
    main()
