"""Libros de muestra SINTÉTICOS de Markowitz y volcado de su estructura para comparar antes/después del rediseño.

Uso: uv run python docs/terminal-pro-20261101-evidencia/excel_volcado.py <etiqueta>
Crea una base temporal con precios sintéticos (sin .env ni red), genera la plantilla y un libro con dos portafolios,
guarda los .xlsx y un JSON con valores, fórmulas, formatos numéricos, validaciones, nombres, uniones, protección,
imágenes y gráficas. El estilo (colores, fuentes, bordes) se vuelca aparte para documentar el cambio visual.
"""
import io
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.update(TERMINAL_DATA_DIR=tempfile.mkdtemp(prefix="excel-muestra-"), TERMINAL_MODO="real", TERMINAL_SIN_MOTOR="1",
                  TERMINAL_SIN_ENV="1", TERMINAL_SIN_CONFIG_LOCAL="1")
RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "tests")]

from openpyxl import load_workbook  # noqa: E402

from conftest import sembrar_precios  # noqa: E402
from terminal import db, excel_markowitz, markowitz, vigencia  # noqa: E402
from terminal.config import cargar_ajustes  # noqa: E402

IDS = ["SIC:AAPL", "SIC:MU", "SIC:NVDA", "BMV:AMX", "BMV:WALMEX"]


def volcar(datos: bytes) -> dict:
    wb = load_workbook(io.BytesIO(datos))
    out = {"hojas": wb.sheetnames, "nombres": sorted(wb.defined_names.keys()), "hojas_detalle": {}}
    for ws in wb.worksheets:
        celdas = {}
        for fila in ws.iter_rows():
            for c in fila:
                if c.value is not None:
                    v = c.value if not hasattr(c.value, "isoformat") else c.value.isoformat()
                    celdas[c.coordinate] = [v if c.coordinate != "A2" or ws.title != "Guía" else "(fecha de generación)", c.number_format]
        out["hojas_detalle"][ws.title] = {
            "celdas": celdas, "uniones": sorted(str(r) for r in ws.merged_cells.ranges),
            "validaciones": [(str(v.sqref), v.type, v.formula1) for v in ws.data_validations.dataValidation],
            "proteccion": bool(ws.protection.sheet), "imagenes": len(ws._images), "graficas": len(ws._charts),
            "congelado": ws.freeze_panes}
    return out


def main(etiqueta: str) -> None:
    ajustes = cargar_ajustes()
    ajustes.datos["app"]["modo"] = "real"
    ajustes.datos["optimizacion"].update(historia_min_sesiones=250, walk_forward_entrenamiento=168, walk_forward_prueba=21)
    con = db.conectar()
    db.inicializar(con)
    sembrar_precios(con, IDS, fin=vigencia.ultima_sesion_cerrada("XNYS"), sesiones=320, proveedor="archivo")
    con.execute("INSERT OR REPLACE INTO ajustes_usuario (clave, valor, actualizado_en) VALUES ('cetes28', ?, '2026-11-01')",
                (json.dumps({"valor": 0.07, "fecha": "2026-10-29", "fuente": "SINTÉTICO", "aviso": "dato sintético de muestra",
                             "consultado_en": "2099-01-01T00:00:00+00:00"}),))
    markowitz.guardar(con, ajustes, {"nombre": "MUESTRA SINTÉTICA A", "activos": IDS, "objetivo": "autorrealizacion"})
    markowitz.guardar(con, ajustes, {"nombre": "MUESTRA SINTÉTICA B", "activos": IDS[:3], "metodo": "min_varianza", "peso_max": 0.5})
    destino = Path(__file__).parent / "excel"
    destino.mkdir(exist_ok=True)
    libros = {"plantilla": excel_markowitz.plantilla(), "libro": excel_markowitz.libro(con, ajustes, markowitz.listar(con))}
    for nombre, datos in libros.items():
        (destino / f"{nombre}-sintetico-{etiqueta}.xlsx").write_bytes(datos)
        (destino / f"{nombre}-{etiqueta}.json").write_text(json.dumps(volcar(datos), ensure_ascii=False, indent=1, default=str),
                                                            encoding="utf-8")
    print("ok", etiqueta, {k: len(v) for k, v in libros.items()})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "antes")
