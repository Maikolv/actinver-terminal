"""Servidor exclusivo de medición: datos copiados, solo localhost y sin red externa."""
import json
import os
from pathlib import Path
import socket
import sys

os.environ.update(TERMINAL_SIN_ENV="1", TERMINAL_SIN_CONFIG_LOCAL="1", TERMINAL_SIN_MOTOR="1",
                  TERMINAL_MODO="real", TERMINAL_DATA_DIR=sys.argv[1],
                  OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
conectar_original = socket.socket.connect
conectar_ex_original = socket.socket.connect_ex
resolver_original = socket.getaddrinfo


def conectar_local(self, direccion):
    if not isinstance(direccion, tuple) or direccion[0] not in ("127.0.0.1", "::1", "localhost"):
        raise OSError("Medición offline: conexión externa prohibida")
    return conectar_original(self, direccion)


def resolver_local(host, *args, **kwargs):
    if host not in ("127.0.0.1", "::1", "localhost", None):
        raise OSError("Medición offline: DNS externo prohibido")
    return resolver_original(host, *args, **kwargs)


def conectar_ex_local(self, direccion):
    if not isinstance(direccion, tuple) or direccion[0] not in ("127.0.0.1", "::1", "localhost"):
        raise OSError("Medición offline: conexión externa prohibida")
    return conectar_ex_original(self, direccion)


socket.socket.connect = conectar_local
socket.socket.connect_ex = conectar_ex_local
socket.getaddrinfo = resolver_local

# Ambas fases usan el mismo cargador sin caché de bytecode, conservando __file__ canónico.
# Las instantáneas originales solo se cargan en este proceso; no se revierte el árbol de trabajo.
import importlib.abc  # noqa: E402
import importlib.util  # noqa: E402

raiz = Path(__file__).resolve().parents[2]
originales = Path(__file__).resolve().parent / "originales"
antes = len(sys.argv) > 3 and sys.argv[3] == "antes"


class FuentesMedicion(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ("terminal.servicios", "terminal.optimizador", "terminal.espacios"):
            return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        nombre = module.__name__.split(".")[-1] + ".py"
        canonico = raiz / "terminal" / nombre
        fuente = originales / nombre if antes else canonico
        module.__file__ = str(canonico)
        exec(compile(fuente.read_bytes(), str(canonico), "exec"), module.__dict__)


sys.meta_path.insert(0, FuentesMedicion())
print(json.dumps({"pid_medicion": os.getpid()}), flush=True)
import uvicorn  # noqa: E402

uvicorn.run("terminal.app:app", host="127.0.0.1", port=int(sys.argv[2]), log_level="critical", access_log=False)
