"""Ejecuta pytest con conexiones/DNS externos bloqueados; HTTP simulado sigue permitido."""
import os
from pathlib import Path
import socket
import sys

os.environ.update(TERMINAL_SIN_MOTOR='1', TERMINAL_SIN_ENV='1', TERMINAL_SIN_CONFIG_LOCAL='1')
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
_conectar = socket.socket.connect
_resolver = socket.getaddrinfo
LOCALES = {'127.0.0.1', '::1', 'localhost', None, b'localhost', b'127.0.0.1'}


def conectar_local(self, direccion):
    if self.family in (socket.AF_INET, socket.AF_INET6) and direccion[0] not in LOCALES:
        raise OSError('Pruebas offline: conexión externa bloqueada')
    return _conectar(self, direccion)


def resolver_local(host, *args, **kwargs):
    if host not in LOCALES:
        raise OSError('Pruebas offline: resolución externa bloqueada')
    return _resolver(host, *args, **kwargs)


socket.socket.connect = conectar_local
socket.getaddrinfo = resolver_local
import pytest  # noqa: E402

raise SystemExit(pytest.main(sys.argv[1:]))
