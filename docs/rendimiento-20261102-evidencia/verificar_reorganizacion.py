"""Evidencia estructural del refactor: no sustituye regresión numérica ni demuestra ventaja."""
import ast
import hashlib
import json
from pathlib import Path

EVIDENCIA = Path(__file__).resolve().parent
RAIZ = EVIDENCIA.parents[1]


class Normalizar(ast.NodeTransformer):
    def visit_Import(self, node):
        return None

    def visit_ImportFrom(self, node):
        return None

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Name):
            if node.value.id == "criterios_propuestas" and node.attr in ("clasificar", "costo_unitario"):
                node.value.id = "optimizador"
            if node.value.id == "lecturas" and node.attr == "ultimo":
                node.value.id = "evaluacion"
        return node

    def visit_Assign(self, node):
        if any(isinstance(t, ast.Name) and t.id == "ARCHIVOS_CALCULO" for t in node.targets):
            # La única modificación deliberada de caché es incluir el fichero trasladado.
            node.value.elts = [v for v in node.value.elts
                               if not isinstance(v, ast.Constant) or v.value != "criterios_propuestas.py"]
        return self.generic_visit(node)


def huella(arbol):
    return hashlib.sha256(ast.dump(arbol, include_attributes=False).encode()).hexdigest()


def main():
    modulos = {
        "servicios": ("terminal/servicios.py", set()),
        "optimizador": ("terminal/optimizador.py", {"_clase_costo", "costo_unitario", "clasificar"}),
        "espacios": ("terminal/espacios.py", set()),
        "investigacion-evaluacion": ("terminal/investigacion/evaluacion.py", {"ultimo"}),
        "investigacion-pronosticos": ("terminal/investigacion/pronosticos.py", set()),
        "investigacion-reto_pronostico": ("terminal/investigacion/reto_pronostico.py", set()),
        "robustez-informe": ("terminal/robustez/informe.py", set()),
        "robustez-calculo": ("terminal/robustez/calculo.py", set()),
    }
    resultado = {"alcance": "Compara AST excluyendo importaciones, alias explícitos de funciones trasladadas y la inclusión del nuevo archivo en la huella de caché. No verifica efectos de importación ni sustituye pruebas de ejecución.", "modulos": {}}
    for nombre, (ruta, trasladadas) in modulos.items():
        antes = ast.parse((EVIDENCIA / "originales" / f"{nombre}.py").read_text(encoding="utf-8"))
        despues = ast.parse((RAIZ / ruta).read_text(encoding="utf-8"))
        antes.body = [n for n in antes.body if not isinstance(n, ast.FunctionDef) or n.name not in trasladadas]
        a, b = huella(Normalizar().visit(antes)), huella(Normalizar().visit(despues))
        resultado["modulos"][ruta] = {"ast_original_normalizado": a, "ast_actual_normalizado": b, "coinciden": a == b}
    for nombre, ruta, funciones in [
        ("optimizador", "terminal/criterios_propuestas.py", {"_clase_costo", "costo_unitario", "clasificar"}),
        ("investigacion-evaluacion", "terminal/investigacion/lecturas.py", {"ultimo"}),
    ]:
        a = ast.parse((EVIDENCIA / "originales" / f"{nombre}.py").read_text(encoding="utf-8"))
        b = ast.parse((RAIZ / ruta).read_text(encoding="utf-8"))
        originales = {n.name: huella(n) for n in a.body if isinstance(n, ast.FunctionDef) and n.name in funciones}
        actuales = {n.name: huella(n) for n in b.body if isinstance(n, ast.FunctionDef) and n.name in funciones}
        resultado["modulos"][ruta] = {"funciones_originales": originales, "funciones_actuales": actuales, "coinciden": originales == actuales}
    (EVIDENCIA / "reorganizacion-ast.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    assert all(v["coinciden"] for v in resultado["modulos"].values()), "Hay diferencias adicionales que requieren revisión."
    print("Ocho módulos y cuatro funciones trasladadas coinciden en el alcance estructural declarado.")


if __name__ == "__main__":
    main()
