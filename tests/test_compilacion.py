"""Todos los módulos de la terminal y los scripts compilan (un error de sintaxis en la línea de comandos impidió arrancar)."""
import py_compile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVOS = sorted([*(RAIZ / "terminal").rglob("*.py"), *(RAIZ / "scripts").glob("*.py")])


@pytest.mark.parametrize("ruta", ARCHIVOS, ids=lambda p: str(p.relative_to(RAIZ)))
def test_compila(ruta):
    py_compile.compile(str(ruta), doraise=True)
