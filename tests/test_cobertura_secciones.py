"""Cada sección visible declara dato, fuente, retraso y criterio de vigencia."""
import json
from pathlib import Path

from terminal import cobertura_secciones


def test_toda_seccion_visible_declara_procedencia():
    ruta = Path(__file__).resolve().parents[1] / "web/static/navegacion.json"
    navegacion = json.loads(ruta.read_text(encoding="utf-8"))
    visibles = {fila["url"].split("vista=")[1] for fila in navegacion["secciones"]}
    assert visibles == set(cobertura_secciones.SECCIONES)
    for fila in cobertura_secciones.tabla():
        assert all(fila[campo].strip() for campo in ("dato", "fuente", "retraso", "vigencia")), fila


def test_api_de_cobertura_entrega_la_tabla_por_seccion(con):
    from terminal.app import get_cobertura

    respuesta = get_cobertura(con)
    assert respuesta["secciones"] == cobertura_secciones.tabla()
