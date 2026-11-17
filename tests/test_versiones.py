"""Historial único: docs/versiones.json genera CHANGELOG.md sin perder texto y VERSIONES.md con cada versión."""
import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("versiones", RAIZ / "scripts" / "versiones.py")
versiones = importlib.util.module_from_spec(spec)
spec.loader.exec_module(versiones)


def test_ida_y_vuelta_sin_perder_texto():
    texto = "# Changelog\r\n\r\nIntro.\r\n\r\n## 2-ene — B\r\n- dos\r\n\r\n## 1-ene — A\r\n- uno\r\n"
    assert versiones.changelog(versiones.importar(texto)) == texto


def test_changelog_y_resumen_salen_del_json():
    datos = json.loads((RAIZ / "docs" / "versiones.json").read_text(encoding="utf-8"))
    lf = lambda t: t.replace("
", "
")  # noqa: E731 - Git puede cambiar CRLF/LF al clonar (Windows frente a Linux)
    assert lf((RAIZ / "CHANGELOG.md").read_bytes().decode("utf-8")) == lf(versiones.changelog(datos))
    resumen = versiones.resumen(datos)
    assert all(f"| {v['version']} |" in resumen for v in datos["versiones"])
