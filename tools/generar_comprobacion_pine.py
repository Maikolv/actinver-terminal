"""Genera un indicador de pruebas con vectores propios; no envía ni sugiere órdenes."""
from pathlib import Path
import hashlib
import json
import re

RAIZ = Path(__file__).resolve().parent.parent


def generar():
    fuente = RAIZ / "tradingview/mesa_riesgo_nq.pine"
    vectores = RAIZ / "tests/vectores/mesa_riesgo_ref.json"
    texto = fuente.read_text(encoding="utf-8")
    casos = json.loads(vectores.read_text(encoding="utf-8"))["casos"]
    destino = RAIZ / "docs/proveedores-20261101-evidencia/pine-visual"
    lineas = [
        "//@version=6",
        'indicator("Futuros Lab · COMPROBACIÓN NUMÉRICA · SIN EJECUCIÓN", overlay=true)',
        "// Casos hipotéticos fijos; sin cotizaciones, señales, alertas o ejecución.",
        "calcular(entrada, stop, objetivoR, presupuesto, comision, slip, punto) =>",
        "    esNQ = true",
        "    tick = 0.25",
    ]
    # Copiar las expresiones aritméticas reales, sin volver a escribir su lógica.
    for nombre in ["alineado", "direccion", "tp", "valido", "riesgo", "cantidad"]:
        linea = re.search(rf"^{nombre} = .+$", texto, re.M)
        if linea is None:
            raise ValueError(f"Falta la expresión {nombre} en la fuente")
        lineas.append("    " + linea.group().rstrip())
    lineas += ["    [valido, tp, riesgo, cantidad]"]
    datos = []
    referencias_datos = []
    for caso in casos:
        limites = [("entrada", 0, 1e9), ("stop", 0, 1e9), ("r", 0, 1000),
                   ("presupuesto", 0, 1e9), ("costos", 0, 1e6), ("slip", 0, 1e6)]
        admitido = all(mn <= caso[k] <= mx for k, mn, mx in limites)
        admitido = admitido and caso["slip"] == int(caso["slip"])
        valores = [caso[k] for k in ["entrada", "stop", "r", "presupuesto", "costos", "slip"]]
        valores += [2 if caso["raiz"] == "MNQ" else 20, int(admitido)]
        esperado = caso.get("esperado", {})
        referencias = [int(caso["valido"]), esperado.get("tp", 0),
                       esperado.get("riesgo", 0), esperado.get("contratos", 0)]
        datos.extend(valores)
        referencias_datos.extend(referencias)
    # Dos cadenas de números fijos evitan miles de instrucciones array.push;
    # se conservan todos los casos y referencias, sin compresión con pérdida.
    for nombre, numeros in [("datos", datos), ("referencia", referencias_datos)]:
        serializados = "|".join(repr(float(v)) for v in numeros)
        lineas.append(f'var {nombre} = str.split("{serializados}", "|")')
    lineas += [
        "var panel = table.new(position.bottom_right, 1, 3)",
        "if barstate.islast",
        "    fallos = 0",
        "    primero = -1",
        f"    for i = 0 to {len(casos)-1}",
        "        j = i * 8",
        "        k = i * 4",
        "        [v, tp, riesgo, cantidad] = calcular(array.get(datos,j), array.get(datos,j+1), array.get(datos,j+2), array.get(datos,j+3), array.get(datos,j+4), array.get(datos,j+5), array.get(datos,j+6))",
        "        valido = array.get(datos,j+7) == 1 and v",
        "        esperadoValido = array.get(referencia,k) == 1",
        "        coincide = valido == esperadoValido",
        "        if valido and esperadoValido",
        "            coincide := coincide and math.abs(tp-array.get(referencia,k+1)) <= 0.000000001 and math.abs(riesgo-array.get(referencia,k+2)) <= 0.000000001 * math.max(1,math.abs(array.get(referencia,k+2))) and cantidad == array.get(referencia,k+3)",
        "        if not coincide",
        "            fallos += 1",
        "            if primero == -1",
        "                primero := i",
        '    table.cell(panel,0,0,"PRUEBA FIJA · SIN EJECUCIÓN",text_color=color.white,bgcolor=color.black)',
        f'    table.cell(panel,0,1,"{len(casos)} casos · diferencias: " + str.tostring(fallos),text_color=color.white,bgcolor=color.black)',
        '    table.cell(panel,0,2,"Primer índice distinto: " + str.tostring(primero),text_color=color.white,bgcolor=color.black)',
    ]
    # Solo cambia la lectura del contenedor, no las expresiones de calcular().
    lineas = [re.sub(r"array\.get\((datos|referencia),([^)]*)\)",
                     r"str.tonumber(array.get(\1,\2))", linea) for linea in lineas]
    salida = destino / "comprobacion-vectores.pine"
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    manifiesto = {"casos": len(casos), "validos": sum(c["valido"] for c in casos),
                  "fuente_sha256": hashlib.sha256(fuente.read_bytes()).hexdigest(),
                  "vectores_sha256": hashlib.sha256(vectores.read_bytes()).hexdigest(),
                  "comprobacion_sha256": hashlib.sha256(salida.read_bytes()).hexdigest(),
                  "limite": "Los límites de input se modelan explícitamente; no simula la interacción con campos ni prueba na/Infinity como entradas de usuario."}
    (destino / "comprobacion-vectores-manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifiesto, ensure_ascii=True))


if __name__ == "__main__":
    generar()
