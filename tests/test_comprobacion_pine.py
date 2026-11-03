"""La prueba en plataforma debe conservar cada vector y la fórmula de origen."""
import json
from pathlib import Path
import re
import runpy


def test_comprobador_conserva_todos_los_vectores_y_formulas(tmp_path):
    raiz = Path(__file__).resolve().parent.parent
    rutas = ["tradingview/mesa_riesgo_nq.pine", "tests/vectores/mesa_riesgo_ref.json"]
    for ruta in rutas:
        destino = tmp_path / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes((raiz / ruta).read_bytes())
    salida = tmp_path / "docs/proveedores-20261101-evidencia/pine-visual"
    salida.mkdir(parents=True)
    modulo = runpy.run_path(str(raiz / "tools/generar_comprobacion_pine.py"))
    modulo["generar"].__globals__["RAIZ"] = tmp_path
    modulo["generar"]()
    texto = (salida / "comprobacion-vectores.pine").read_text(encoding="utf-8")
    casos = json.loads((raiz / rutas[1]).read_text(encoding="utf-8"))["casos"]
    datos = [float(n) for n in re.search(r'var datos = str.split\("([^"\n]+)"', texto)[1].split("|")]
    referencias = [float(n) for n in re.search(r'var referencia = str.split\("([^"\n]+)"', texto)[1].split("|")]
    assert len(datos) == len(casos) * 8
    assert len(referencias) == len(casos) * 4
    for i, caso in enumerate(casos):
        assert datos[i*8:i*8+6] == [caso[k] for k in ["entrada", "stop", "r", "presupuesto", "costos", "slip"]]
        assert datos[i*8+6] == (2 if caso["raiz"] == "MNQ" else 20)
        esperado = caso.get("esperado", {})
        assert referencias[i*4:i*4+4] == [int(caso["valido"]), esperado.get("tp", 0), esperado.get("riesgo", 0), esperado.get("contratos", 0)]
    fuente = (raiz / rutas[0]).read_text(encoding="utf-8")
    for nombre in ["alineado", "direccion", "tp", "valido", "riesgo", "cantidad"]:
        assert "    " + re.search(rf"^{nombre} = .+$", fuente, re.M)[0].rstrip() in texto
    assert not re.search(r"\bstrategy\.|\balert(?:condition)?\s*\(|\brequest\.", texto)
