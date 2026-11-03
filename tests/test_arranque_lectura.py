"""La lectura y presentación no deben cargar el motor matemático en un proceso frío."""
import os
from pathlib import Path
import subprocess
import sys


def test_importacion_y_clasificacion_de_lectura_no_cargan_modelos(tmp_path):
    nombres = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA"}
    entorno = {k: v for k, v in os.environ.items() if k.upper() in nombres}
    entorno.update(TERMINAL_SIN_ENV="1", TERMINAL_SIN_CONFIG_LOCAL="1", TERMINAL_SIN_MOTOR="1",
                   TERMINAL_MODO="real", TERMINAL_DATA_DIR=str(tmp_path), OPENBLAS_NUM_THREADS="1",
                   OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    codigo = """
import socket, sys
conectar = socket.socket.connect
conectar_ex = socket.socket.connect_ex
resolver = socket.getaddrinfo
def solo_local(self, direccion):
    if not isinstance(direccion, tuple) or direccion[0] not in ('127.0.0.1','::1','localhost'):
        raise AssertionError('La prueba no permite conexiones externas')
    return conectar(self, direccion)
socket.socket.connect = solo_local
def solo_local_ex(self, direccion):
    if not isinstance(direccion, tuple) or direccion[0] not in ('127.0.0.1','::1','localhost'):
        raise AssertionError('La prueba no permite conexiones externas')
    return conectar_ex(self, direccion)
def resolver_local(host, *args, **kwargs):
    if host not in ('127.0.0.1','::1','localhost',None):
        raise AssertionError('La prueba no permite DNS externo')
    return resolver(host, *args, **kwargs)
socket.socket.connect_ex = solo_local_ex
socket.getaddrinfo = resolver_local
from terminal import app, criterios_propuestas, servicios
assert 'terminal.optimizador' not in sys.modules
assert 'sklearn' not in sys.modules and 'skfolio' not in sys.modules, sorted(n for n in sys.modules if n.startswith(('terminal.investigacion', 'skfolio', 'sklearn')))[:20]
filas = criterios_propuestas.clasificar([
    {'tipo':'acciones','nombre':'A','estado':'calculada','puntuacion':{'total':2}},
    {'tipo':'mixta','nombre':'B','estado':'insuficiente','motivos':['SIN DATO']},
    {'tipo':'acciones','nombre':'C','estado':'calculada','puntuacion':{'total':5}},
], {})
assert [f['alternativa'] for f in filas] == ['C','A','B']
assert [f['posicion'] for f in filas] == [1,2,None]
assert 'sklearn' not in sys.modules and 'skfolio' not in sys.modules
from fastapi.testclient import TestClient
with TestClient(app.app, base_url='http://127.0.0.1') as cliente:
    assert cliente.get('/api/estado').status_code == 200
    assert cliente.get('/api/universo').status_code == 200
    assert cliente.get('/api/presente').status_code == 200
    assert 'terminal.optimizador' not in sys.modules
    assert 'sklearn' not in sys.modules and 'skfolio' not in sys.modules
    assert cliente.get('/api/pasado').status_code == 200
    assert cliente.get('/api/futuro').status_code == 200
    assert 'terminal.investigacion.evaluacion' not in sys.modules
    assert 'sklearn' not in sys.modules and 'skfolio' not in sys.modules
from terminal import optimizador
assert optimizador.clasificar is criterios_propuestas.clasificar
assert optimizador.costo_unitario is criterios_propuestas.costo_unitario
from terminal.investigacion import evaluacion, lecturas
assert evaluacion.ultimo is lecturas.ultimo
"""
    resultado = subprocess.run([sys.executable, "-c", codigo], cwd=Path(__file__).resolve().parents[1],
                               env=entorno, capture_output=True, text=True, timeout=90)
    assert resultado.returncode == 0, resultado.stderr
