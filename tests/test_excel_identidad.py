"""Identidad visual del Excel de Markowitz: entradas y resultados se distinguen por forma, sin macros ni vínculos externos."""
import io
import zipfile

from openpyxl import load_workbook

from terminal import excel_markowitz


def test_plantilla_identidad_y_formas():
    datos = excel_markowitz.plantilla()
    nombres = zipfile.ZipFile(io.BytesIO(datos)).namelist()
    assert not any("vbaProject" in n or "externalLink" in n for n in nombres)   # sin macros ni vínculos a otros libros
    wb = load_workbook(io.BytesIO(datos))
    for ws in wb.worksheets:
        assert ws["A1"].fill.fgColor.rgb.endswith(excel_markowitz.NEGRO)          # banda negra con título blanco
        assert ws["A1"].font.color.rgb.endswith("FFFFFF")
        assert ws.sheet_properties.tabColor.rgb.endswith(excel_markowitz.MARCA)
    celdas = [c for ws in wb.worksheets for fila in ws.iter_rows() for c in fila]
    entradas = [c for c in celdas if c.fill.fgColor.rgb and c.fill.fgColor.rgb.endswith("FFF5F5")]
    resultados = [c for c in celdas if c.fill.fgColor.rgb and c.fill.fgColor.rgb.endswith(excel_markowitz.GRIS_RESULTADO)]
    assert entradas and all(c.border.left.style == "dashed" for c in entradas)
    assert resultados and all(c.border.bottom.style == "double" and c.font.bold for c in resultados)
    assert not any(isinstance(c.value, str) and c.value.startswith("=") for c in entradas if c.parent.title != "Guía")
    assert all(isinstance(c.value, str) and c.value.startswith("=") for c in resultados if c.parent.title != "Guía")
