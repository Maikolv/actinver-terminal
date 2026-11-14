"""Libros de Excel con el desarrollo del modelo de Markowitz, con fórmulas vivas (se pueden editar como plantilla).

* `plantilla()`: ejercicio paramétrico del Taller de Acelera (IPC, S&P 500 y Treasury MXN) con las fórmulas que en
  el original quedaron como #REF!, más una hoja histórica vacía para pegar precios propios.
* `libro(...)`: los portafolios guardados del generador, cada uno con sus precios, rendimientos, estadísticos,
  covarianzas, correlaciones, pesos, resultados, frontera eficiente y gráfica.

Cada hoja de modelo deja cargado el modelo de Solver (nombres ocultos `solver_*` de la hoja, los que Excel guarda al
pulsar «Guardar» en Solver): Datos → Solver abre ya con objetivo, celdas variables y restricciones; solo falta «Resolver».
Todas llevan un bloque de proyección a un horizonte en días, semanas, meses o años con las fórmulas de
`markowitz.proyeccion`. La plantilla incluye además la «Matriz de precios» del documento del usuario, completada.

Llevan el diseño de la terminal (logo, colores y tipografía de `web/static/app.css`) y una hoja «Guía» con los pasos
y las celdas exactas de cada libro. La varianza del portafolio se calcula sin fórmulas matriciales:
(Σw)_i = Σ_j cov_ij·w_j y σ²_p = Σ_i w_i·(Σw)_i, así funciona igual en Excel, LibreOffice y Google Sheets.
"""
from __future__ import annotations

import io
from datetime import date
from functools import lru_cache

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.image import Image as ImagenXL
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.utils.cell import absolute_coordinate
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from . import markowitz
from .config import CONFIG_DIR

# Identidad de la terminal (DESIGN.md): banda negra con texto blanco, encabezados gris oscuro, cuerpo blanco para que
# imprima legible, y rojo solo como acento. Entradas y resultados se distinguen por FORMA (borde punteado / doble
# línea y negritas), no solo por color. Contraste: blanco sobre NEGRO 17:1, blanco sobre GRIS_CAB 15:1, ROJO_TEXTO 6.5:1.
MARCA, TEXTO, TEXTO_2, BORDE = "D94848", "111318", "4A505A", "C9CBD0"
NEGRO, GRIS_CAB, ROJO_TEXTO, GRIS_RESULTADO = "121419", "1B1E24", "B42626", "ECECE9"
POSITIVO, SERIE_1, SERIE_2 = "1D6B3A", "1F5F8B", "B0600F"
FUENTE = "Segoe UI"
NEGRITA = Font(name=FUENTE, bold=True, color=TEXTO)
TITULO = Font(name=FUENTE, bold=True, size=15, color="FFFFFF")
SECCION = Font(name=FUENTE, bold=True, size=12, color=ROJO_TEXTO)
SUAVE = Font(name=FUENTE, size=10, color=TEXTO_2)
FUENTE_CAB = Font(name=FUENTE, bold=True, color="FFFFFF")
BANDA = PatternFill("solid", fgColor=NEGRO)
CABECERA = PatternFill("solid", fgColor=GRIS_CAB)
ENTRADA = PatternFill("solid", fgColor="FFF5F5")      # editable: relleno muy claro + borde rojo punteado
RESULTADO = PatternFill("solid", fgColor=GRIS_RESULTADO)  # resultado: gris claro + negritas + doble línea inferior
LINEA = Side(style="thin", color=BORDE)
PUNTEADA = Side(style="dashed", color=ROJO_TEXTO)
PCT, NUM = "0.00%", "#,##0.00"
# Ejercicio de Acelera: E(r) y σ anuales; correlaciones derivadas de las covarianzas diarias del mismo archivo
ACELERA = (["IPC", "SP500", "Treasury MXN"], [0.11, 0.16, 0.09], [0.18, 0.17, 0.10],
           [[1, 0.324, -0.265], [0.324, 1, 0.472], [-0.265, 0.472, 1]])
AVISO = "Simulación educativa con datos históricos: no es pronóstico ni recomendación. La terminal no envía órdenes."
EJEMPLO_MATRIZ = CONFIG_DIR / "markowitz_matriz_ejemplo.csv"  # precios del documento «Matriz de precios» del usuario
UNIDADES = (("días", 1), ("semanas", 5), ("meses", 21), ("años", 252))  # = criterios_propuestas.UNIDADES_HORIZONTE


@lru_cache(maxsize=1)
def _logo_png(px: int = 96) -> bytes:
    """El mismo logo que web/static/favicon.svg (cuadro rojo con línea de precio blanca), en PNG."""
    from PIL import Image, ImageDraw
    k = px / 32
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, px - 1, px - 1], radius=round(6 * k), fill="#" + MARCA)
    w = round(2.6 * k)
    for trazo in ([(6, 25), (26, 25)], [(8, 20), (13, 14), (17, 17), (24, 8)]):
        puntos = [(x * k, y * k) for x, y in trazo]
        d.line(puntos, fill="white", width=w, joint="curve")
        for x, y in puntos:  # extremos y vértices redondeados, como stroke-linecap/linejoin «round»
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill="white")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _encabezado(ws, titulo: str, columnas: int, subtitulo: str | None = None) -> None:
    """Fila 1 como la cabecera de la terminal: logo, nombre y título, con línea inferior."""
    logo = ImagenXL(io.BytesIO(_logo_png()))
    logo.width = logo.height = 30
    ws.add_image(logo, "A1")
    ws.row_dimensions[1].height = 32
    ws["A1"] = f"Help Quote Terminal · {titulo}"
    ws["A1"].font = TITULO
    ws["A1"].alignment = Alignment(vertical="center", indent=3)
    for c in range(1, columnas + 1):
        ws.cell(1, c).fill = BANDA
        ws.cell(1, c).border = Border(bottom=Side(style="thick", color=MARCA))
    if subtitulo:
        ws["A2"] = subtitulo
        ws["A2"].font = SUAVE
    ws.sheet_properties.tabColor = MARCA


def _cabecera(celda) -> None:
    celda.font, celda.fill, celda.border = FUENTE_CAB, CABECERA, Border(bottom=Side(style="thin", color=MARCA))


def _entrada(celda, formato: str | None = None) -> None:
    celda.fill, celda.border = ENTRADA, Border(left=PUNTEADA, right=PUNTEADA, top=PUNTEADA, bottom=PUNTEADA)
    if formato:
        celda.number_format = formato


def _resultado(celda) -> None:
    celda.fill, celda.font = RESULTADO, Font(name=FUENTE, bold=True, color=TEXTO)
    celda.border = Border(top=LINEA, bottom=Side(style="double", color=TEXTO))


def _fuente_terminal(wb: Workbook) -> None:
    """Segoe UI en todo el libro (openpyxl deja Calibri en las celdas sin formato)."""
    for ws in wb.worksheets:
        for fila in ws.iter_rows():
            for c in fila:
                if c.font.name != FUENTE:
                    f = c.font
                    c.font = Font(name=FUENTE, bold=f.bold, italic=f.italic, size=f.size, color=f.color)


def _guia(wb: Workbook, titulo: str, bloques: list[tuple[str, list[str]]]) -> None:
    """Hoja «Guía»: pasos numerados, cortos y con las celdas exactas del libro."""
    ws = wb.active
    ws.title = "Guía"
    ws.sheet_view.showGridLines = False
    _encabezado(ws, titulo, 2, f"Generado el {date.today():%d/%m/%Y}. {AVISO}")
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 118
    ws["A2"].alignment = Alignment(indent=0)
    fila = 4
    for encabezado, pasos in bloques:
        ws.cell(fila, 1, encabezado).font = SECCION
        fila += 1
        for k, paso in enumerate(pasos, start=1):
            ws.cell(fila, 1, k if len(pasos) > 1 else "•").font = Font(name=FUENTE, bold=True, color=MARCA)
            ws.cell(fila, 1).alignment = Alignment(horizontal="right", vertical="top")
            c = ws.cell(fila, 2, paso)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[fila].height = 15 * max(1, -(-len(paso) // 115))
            fila += 1
        fila += 1
    ejemplo = [("Borde rojo punteado", ENTRADA, "usted escribe aquí"), ("Sin borde", None, "fórmula: no la borre"),
               ("Gris, negritas y doble línea", RESULTADO, "resultado principal")]
    ws.cell(fila, 1, "Colores del libro").font = SECCION
    for k, (nombre, relleno, uso) in enumerate(ejemplo, start=fila + 1):
        c = ws.cell(k, 2, f"{nombre}: {uso}")
        if relleno is ENTRADA:
            _entrada(c)
        elif relleno is RESULTADO:
            _resultado(c)
    ws.freeze_panes = "A4"


def _matriz(ws, fila: int, col: int, nombres: list[str], celda) -> tuple[int, int]:
    """Escribe una matriz n×n; celda(i, j) devuelve la fórmula. Regresa (fila, col) de la esquina superior izquierda."""
    _cabecera(ws.cell(fila, col))
    for k, nm in enumerate(nombres):
        _cabecera(ws.cell(fila, col + 1 + k, nm))
        _cabecera(ws.cell(fila + 1 + k, col, nm))
    for i in range(len(nombres)):
        for j in range(len(nombres)):
            ws.cell(fila + 1 + i, col + 1 + j, celda(i, j)).number_format = "0.000000"
    return fila + 1, col + 1


def _resultados(ws, fila: int, n: int, f_e: int, c_e: str, c_w: str, f_cov: int, c_cov: int, rf: str, a: str) -> dict:
    """Bloque (Σw)_i, contribución al riesgo y resultados del portafolio. Devuelve las celdas clave."""
    fin = f_e + n - 1
    cw = f"{c_w}{f_e}:{c_w}{fin}"
    fila_w = fila + n + 9  # fila auxiliar con los pesos en horizontal (para multiplicar por renglones de la matriz)
    ws.cell(fila_w, 1, "Pesos en fila (auxiliar)").font = SUAVE
    for j in range(n):
        ws.cell(fila_w, c_cov + j, f"={c_w}{f_e + j}").number_format = PCT
    fila_aux = f"{L(c_cov)}{fila_w}:{L(c_cov + n - 1)}{fila_w}"
    ws.cell(fila - 1, 1, "Resultados del portafolio").font = SECCION
    for k, t in enumerate(["Activo", "(Σw)_i", "Contribución al riesgo"]):
        _cabecera(ws.cell(fila, 1 + k, t))
    for i in range(n):
        r = fila + 1 + i
        ws.cell(r, 1, f"=A{f_e + i}")
        ws.cell(r, 2, f"=SUMPRODUCT({L(c_cov)}{f_cov + i}:{L(c_cov + n - 1)}{f_cov + i},{fila_aux})").number_format = "0.000000"
        ws.cell(r, 3, f"=IFERROR({c_w}{f_e + i}*B{r}/$B${fila + n + 3},\"\")").number_format = PCT
    r0 = fila + n + 2
    celdas = {}
    principales = {"E(r_p) anual", "σ_p anual", "Sharpe"}
    for k, (et, f, fmt) in enumerate([
        ("E(r_p) anual", f"=SUMPRODUCT({cw},{c_e}{f_e}:{c_e}{fin})", PCT),
        ("Varianza σ²_p", f"=SUMPRODUCT({cw},B{fila + 1}:B{fila + n})", "0.000000"),
        ("σ_p anual", f"=SQRT(MAX(B{r0 + 1},0))", PCT),
        ("Sharpe", f"=IFERROR((B{r0}-{rf})/B{r0 + 2},\"\")", "0.000"),
        ("Utilidad U = E − ½·A·σ²", f"=B{r0}-0.5*{a}*B{r0 + 1}", "0.0000"),
        ("Asignación al riesgoso y* = (E−r_f)/(A·σ²)", f"=IFERROR((B{r0}-{rf})/({a}*B{r0 + 1}),\"\")", PCT),
        ("Suma de pesos (debe ser 100 %)", f"=SUM({cw})", PCT),
    ]):
        ws.cell(r0 + k, 1, et).font = NEGRITA
        c = ws.cell(r0 + k, 2, f)
        c.number_format = fmt
        if et in principales:
            _resultado(c)
        celdas[et] = f"B{r0 + k}"
    celdas["pesos"] = cw
    return celdas


def _colorear(serie: Series, color: str, marcador: str | None = None, linea: bool = True) -> None:
    if linea:
        serie.graphicalProperties.line.solidFill = color
        serie.graphicalProperties.line.width = 28000
    else:
        serie.graphicalProperties.line.noFill = True
    if marcador:
        serie.marker.symbol, serie.marker.size = marcador, 7
        relleno = GraphicalProperties(solidFill=color)
        relleno.line.solidFill = color
        serie.marker.graphicalProperties = relleno


def _frontera(ws, fila: int, res: dict, ancla: str) -> None:
    ws.cell(fila, 1, "Frontera eficiente (calculada por la terminal; Solver la reproduce)").font = SECCION
    for col, t in ((1, "σ_p"), (2, "E(r_p)"), (4, "Activo"), (5, "σ"), (6, "E(r)"), (8, "Elegido σ"), (9, "Elegido E(r)")):
        _cabecera(ws.cell(fila + 1, col, t))
    for k, p in enumerate(res["frontera"]):
        ws.cell(fila + 2 + k, 1, p["riesgo"]).number_format = PCT
        ws.cell(fila + 2 + k, 2, p["rend"]).number_format = PCT
    for k, a in enumerate(res["activos"]):
        ws.cell(fila + 2 + k, 4, a["clave"])
        ws.cell(fila + 2 + k, 5, a["riesgo"]).number_format = PCT
        ws.cell(fila + 2 + k, 6, a["rend"]).number_format = PCT
    m = res["metricas"]
    ws.cell(fila + 2, 8, m["riesgo"]).number_format = PCT
    ws.cell(fila + 2, 9, m["rend"]).number_format = PCT
    nf, na = len(res["frontera"]), len(res["activos"])
    if not nf:
        return
    g = ScatterChart()
    g.title, g.style, g.height, g.width = "Frontera eficiente", 13, 9, 18
    g.x_axis.title, g.y_axis.title = "Riesgo σ (anual)", "Rendimiento esperado (anual)"
    for xs, ys, nombre, color, marcador, linea in [
        (Reference(ws, min_col=1, min_row=fila + 2, max_row=fila + 1 + nf), Reference(ws, min_col=2, min_row=fila + 2, max_row=fila + 1 + nf), "Frontera", TEXTO, None, True),
        (Reference(ws, min_col=5, min_row=fila + 2, max_row=fila + 1 + na), Reference(ws, min_col=6, min_row=fila + 2, max_row=fila + 1 + na), "Activos", TEXTO_2, "circle", False),
        (Reference(ws, min_col=8, min_row=fila + 2), Reference(ws, min_col=9, min_row=fila + 2), "Elegido", MARCA, "diamond", False)]:
        se = Series(ys, xs, title=nombre)
        _colorear(se, color, marcador, linea)
        g.series.append(se)
    ws.add_chart(g, ancla)


def _hoja_historica(wb: Workbook, prefijo: str, nombres: list[str], precios: pd.DataFrame | None, filas_vacias: int,
                    pesos: list[float], rf: float, aversion: float, peso_max: float, peso_min: float, res: dict | None,
                    capital: float = 100_000, horizonte: tuple[float, str] = (1, "años")) -> dict:
    n = len(nombres)
    datos = wb.create_sheet(f"{prefijo}Datos"[:31])
    cr = n + 3  # primera columna de rendimientos
    _encabezado(datos, "Precios (MXN) y rendimientos diarios", cr + n - 1)
    _cabecera(datos.cell(2, 1, "Fecha"))
    for j, nm in enumerate(nombres):
        c = datos.cell(2, 2 + j, nm)
        _cabecera(c)
        if precios is None:
            _entrada(c)
        _cabecera(datos.cell(2, cr + j, f"r {nm}" if precios is not None else f"=\"r \"&{L(2 + j)}2"))
    total = len(precios) if precios is not None else filas_vacias
    for k in range(total):
        r = 3 + k
        if precios is not None:
            datos.cell(r, 1, precios.index[k].date()).number_format = "yyyy-mm-dd"
            for j, i in enumerate(precios.columns):
                datos.cell(r, 2 + j, float(precios.iloc[k, j])).number_format = NUM
        else:
            for j in range(n + 1):
                _entrada(datos.cell(r, 1 + j))
        if k:
            for j in range(n):
                p = L(2 + j)
                datos.cell(r, cr + j, f'=IFERROR({p}{r}/{p}{r - 1}-1,"")').number_format = "0.0000%"
    ultima = 2 + total
    datos.column_dimensions["A"].width = 13
    for c in range(2, cr + n):
        datos.column_dimensions[L(c)].width = 13
    datos.freeze_panes = "B3"
    rango = lambda j: f"'{datos.title}'!${L(cr + j)}$4:${L(cr + j)}${ultima}"  # noqa: E731  (fila 3 no tiene rendimiento)

    ws = wb.create_sheet(f"{prefijo}Modelo"[:31])
    _encabezado(ws, f"Modelo de Markowitz · {res['especificacion']['nombre'] if res else 'plantilla con sus datos'}", n + 9,
                "Borde rojo punteado: usted escribe. Gris con negritas y doble línea: resultado principal. " + AVISO)
    for k, (et, v, fmt) in enumerate([("Tasa libre de riesgo r_f", rf, PCT), ("Aversión al riesgo A", aversion, "0.0"),
                                      ("Peso máximo por activo", peso_max, PCT), ("Peso mínimo por activo", peso_min, PCT)]):
        ws.cell(3 + k, 1, et).font = NEGRITA
        _entrada(ws.cell(3 + k, 2, v), fmt)
    f_e = 10
    ws.cell(f_e - 2, 1, "Activos: estadísticos anuales y pesos").font = SECCION
    for k, t in enumerate(["Activo", "E(r) anual", "σ anual", "Sharpe", "Peso w", "Máx.", "Mín."]
                          + (["Peso Solver (terminal)"] if res else [])):
        _cabecera(ws.cell(f_e - 1, 1 + k, t))
    for i, nm in enumerate(nombres):
        r = f_e + i
        ws.cell(r, 1, nm if precios is not None else f"='{datos.title}'!{L(2 + i)}2")
        ws.cell(r, 2, f"=IFERROR(AVERAGE({rango(i)})*252,0)").number_format = PCT
        ws.cell(r, 3, f"=IFERROR(_xlfn.STDEV.S({rango(i)})*SQRT(252),0)").number_format = PCT
        ws.cell(r, 4, f'=IFERROR((B{r}-$B$3)/C{r},"")').number_format = "0.000"
        _entrada(ws.cell(r, 5, pesos[i]), PCT)
        ws.cell(r, 6, "=$B$5").number_format = PCT
        ws.cell(r, 7, "=$B$6").number_format = PCT
        if res:  # el máximo Sharpe que calculó la terminal: Solver debe llegar a lo mismo
            ws.cell(r, 8, res["pesos_tangente"].get(res["activos"][i]["id"], 0.0)).number_format = PCT
    etiquetas = nombres if precios is not None else [f"='{datos.title}'!{L(2 + k)}2" for k in range(n)]
    f_cov = f_e + n + 2
    ws.cell(f_cov - 1, 1, "Matriz de covarianzas anual = COVARIANCE.S × 252").font = SECCION
    fc, cc = _matriz(ws, f_cov, 1, etiquetas,
                     lambda i, j: f"=IFERROR(_xlfn.COVARIANCE.S({rango(i)},{rango(j)})*252,0)")
    f_cor = f_cov + n + 3
    ws.cell(f_cor - 1, 1, "Matriz de correlaciones").font = SECCION
    _matriz(ws, f_cor, 1, etiquetas,
            lambda i, j: f'=IFERROR(CORREL({rango(i)},{rango(j)}),"")')
    f_res = f_cor + n + 3
    celdas = _resultados(ws, f_res, n, f_e, "B", "E", fc, cc, "$B$3", "$B$4")
    _solver(ws, celdas["Sharpe"], celdas["pesos"], celdas["Suma de pesos (debe ser 100 %)"], "B5", "B6")
    proy = _proyeccion(ws, f_res + n + 12, celdas["E(r_p) anual"], celdas["σ_p anual"], capital, *horizonte)
    celdas.update(proy)
    if res:
        _frontera(ws, proy["fin"] + 2, res, f"K{f_e}")
    ws.column_dimensions["A"].width = 42
    for c in range(2, n + 12):
        ws.column_dimensions[L(c)].width = 14
    ws.freeze_panes = "A3"
    return {"hoja": ws.title, "datos": datos.title, "ultima": ultima, "n": n, **celdas}


def _hoja_parametrica(wb: Workbook) -> dict:
    nombres, e, s, rho = ACELERA
    n = len(nombres)
    ws = wb.create_sheet("Paramétrico Acelera")
    _encabezado(ws, "Ejercicio del Taller de Portafolios (Acelera)", 8,
                "Matriz de covarianzas armada con correlaciones. Borde rojo punteado: usted escribe. " + AVISO)
    ws["A3"], ws["B3"] = "Tasa libre de riesgo r_f", 0.07
    ws["A4"], ws["B4"] = "Aversión al riesgo A", 4
    ws["A3"].font = ws["A4"].font = NEGRITA
    _entrada(ws["B3"], PCT)
    _entrada(ws["B4"], "0.0")
    f_e = 7
    for k, t in enumerate(["Activo", "E(r) anual", "σ anual", "Sharpe", "Peso w"]):
        _cabecera(ws.cell(f_e - 1, 1 + k, t))
    for i in range(n):
        r = f_e + i
        ws.cell(r, 1, nombres[i])
        for col, v in ((2, e[i]), (3, s[i]), (5, round(1 / n, 6))):
            _entrada(ws.cell(r, col, v), PCT)
        ws.cell(r, 4, f'=IFERROR((B{r}-$B$3)/C{r},"")').number_format = "0.000"
    f_rho = f_e + n + 2
    ws.cell(f_rho - 1, 1, "Correlaciones ρ (cambie el triángulo de borde punteado; el otro se copia)").font = SECCION
    fr, cr = _matriz(ws, f_rho, 1, nombres, lambda i, j: 1 if i == j else (rho[i][j] if j > i else f"={L(2 + i)}{f_rho + 1 + j}"))
    for i in range(n):
        for j in range(i + 1, n):
            _entrada(ws.cell(fr + i, cr + j))
    f_cov = f_rho + n + 3
    ws.cell(f_cov - 1, 1, "Covarianzas cov_ij = ρ_ij · σ_i · σ_j").font = SECCION
    fc, cc = _matriz(ws, f_cov, 1, nombres, lambda i, j: f"={L(cr + j)}{fr + i}*$C${f_e + i}*$C${f_e + j}")
    celdas = _resultados(ws, f_cov + n + 3, n, f_e, "B", "E", fc, cc, "$B$3", "$B$4")
    _solver(ws, celdas["Sharpe"], celdas["pesos"], celdas["Suma de pesos (debe ser 100 %)"])
    # Dos activos con correlación variable (preguntas 1–3 del ejercicio original, sin las referencias rotas)
    f2 = f_cov + 3 * n + 16  # (dos activos)
    ws.cell(f2, 1, "Dos activos (A = IPC, B = SP500): σ_p = √(wA²σA² + wB²σB² + 2·wA·wB·ρ·σA·σB)").font = SECCION
    ws.cell(f2 + 1, 1, "ρ(A,B) para esta tabla").font = NEGRITA
    _entrada(ws.cell(f2 + 1, 2, 0.5))
    for k, t in enumerate(["wA", "wB", "σ_p", "E(r_p)", "σ_p con ρ=+1", "σ_p con ρ=0", "σ_p con ρ=−1"]):
        _cabecera(ws.cell(f2 + 2, 1 + k, t))
    for k in range(11):
        r = f2 + 3 + k
        ws.cell(r, 1, k / 10).number_format = PCT
        ws.cell(r, 2, f"=1-A{r}").number_format = PCT
        sa, sb, ea, eb = f"$C${f_e}", f"$C${f_e + 1}", f"$B${f_e}", f"$B${f_e + 1}"
        base = f"A{r}^2*{sa}^2+B{r}^2*{sb}^2+2*A{r}*B{r}*{{rho}}*{sa}*{sb}"
        ws.cell(r, 3, f"=SQRT(MAX({base.format(rho=f'$B${f2 + 1}')},0))").number_format = PCT
        ws.cell(r, 4, f"=A{r}*{ea}+B{r}*{eb}").number_format = PCT
        for col, rv in ((5, "1"), (6, "0"), (7, "-1")):
            ws.cell(r, col, f"=SQRT(MAX({base.format(rho=rv)},0))").number_format = PCT
    g = ScatterChart()
    g.title, g.style, g.height, g.width = "Dos activos: efecto de la correlación", 13, 9, 16
    g.x_axis.title, g.y_axis.title = "σ_p", "E(r_p)"
    ys = Reference(ws, min_col=4, min_row=f2 + 3, max_row=f2 + 13)
    for col, nm, color in ((3, "ρ elegida", MARCA), (5, "ρ=+1", TEXTO_2), (6, "ρ=0", SERIE_2), (7, "ρ=−1", SERIE_1)):
        se = Series(ys, Reference(ws, min_col=col, min_row=f2 + 3, max_row=f2 + 13), title=nm)
        _colorear(se, color)
        g.series.append(se)
    ws.add_chart(g, f"I{f2}")
    ws.column_dimensions["A"].width = 46
    for c in range(2, 9):
        ws.column_dimensions[L(c)].width = 14
    ws.freeze_panes = "A3"
    return {"hoja": ws.title, "rho": f"{L(cr + 1)}{fr}:{L(cr + n - 1)}{fr + n - 2}", "f_e": f_e, "n": n, **celdas}


def _solver(ws, objetivo: str, pesos: str, suma: str, maximo: str | None = None, minimo: str | None = None) -> None:
    """Deja el modelo de Solver guardado en la hoja: maximizar `objetivo` cambiando `pesos`, con suma = 1, pesos ≤ máximo,
    pesos ≥ mínimo y no negativos, motor GRG Nonlinear. Son los mismos nombres ocultos que Excel escribe al guardar."""
    h = f"'{ws.title}'!"
    restr = [(suma, 2, "1")] + ([(pesos, 1, h + absolute_coordinate(maximo))] if maximo else []) \
        + ([(pesos, 3, h + absolute_coordinate(minimo))] if minimo else [])
    nombres = {"solver_adj": h + absolute_coordinate(pesos), "solver_opt": h + absolute_coordinate(objetivo), "solver_typ": "1",
               "solver_val": "0", "solver_num": str(len(restr)), "solver_eng": "1", "solver_neg": "1", "solver_ver": "3",
               "solver_lin": "2", "solver_cvg": "0.0001", "solver_drv": "1", "solver_est": "1", "solver_itr": "2147483647",
               "solver_mip": "2147483647", "solver_msl": "2", "solver_nod": "2147483647", "solver_nwt": "1",
               "solver_pre": "0.000001", "solver_rbv": "1", "solver_rlx": "2", "solver_rsd": "0", "solver_scl": "1",
               "solver_sho": "2", "solver_ssz": "100", "solver_tim": "2147483647", "solver_tol": "0.01"}
    for k, (izq, rel, der) in enumerate(restr, start=1):
        nombres |= {f"solver_lhs{k}": h + absolute_coordinate(izq), f"solver_rel{k}": str(rel), f"solver_rhs{k}": der}
    for nombre, valor in nombres.items():
        ws.defined_names[nombre] = DefinedName(nombre, attr_text=valor, hidden=True)


def _proyeccion(ws, fila: int, e: str, s: str, capital: float, horizonte: float = 1, unidad: str = "años",
                por_anio: bool = True) -> dict:
    """Bloque de proyección: el usuario elige cantidad y unidad; E_h = E·t, σ_h = σ·√t, banda del 90 % y P(pérdida),
    las mismas fórmulas que `markowitz.proyeccion`. `e` y `s` son celdas anuales (t = sesiones/252) o diarias
    (`por_anio=False`, t = sesiones)."""
    ws.cell(fila, 1, "Proyección a un horizonte (días, semanas, meses o años)").font = SECCION
    t = f"B{fila + 3}/252" if por_anio else f"B{fila + 3}"
    u = f"B{fila + 2}"
    filas = [("Horizonte (cantidad)", horizonte, "0.##", True), ("Unidad (días, semanas, meses o años)", unidad, None, True),
             ("Sesiones bursátiles", f'=MAX(1,ROUND(B{fila + 1}*IF({u}="días",1,IF({u}="semanas",5,IF({u}="meses",21,252))),0))',
              "0", False),
             ("Capital (MXN)", capital, NUM, True),
             ("Rendimiento esperado en el horizonte", f"={e}*{t}", PCT, False),
             ("Riesgo σ en el horizonte", f"={s}*SQRT({t})", PCT, False),
             ("Escenario bajo (solo 5 % de las veces peor)", f"=B{fila + 5}-1.645*B{fila + 6}", PCT, False),
             ("Escenario alto (solo 5 % de las veces mejor)", f"=B{fila + 5}+1.645*B{fila + 6}", PCT, False),
             ("Probabilidad de terminar con pérdida", f'=IFERROR(NORMDIST(0,B{fila + 5},B{fila + 6},TRUE),"")', PCT, False),
             ("Valor esperado (MXN)", f"=B{fila + 4}*(1+B{fila + 5})", NUM, False),
             ("Valor en el escenario bajo (MXN)", f"=B{fila + 4}*(1+B{fila + 7})", NUM, False),
             ("Valor en el escenario alto (MXN)", f"=B{fila + 4}*(1+B{fila + 8})", NUM, False)]
    for k, (et, v, fmt, entrada) in enumerate(filas, start=1):
        ws.cell(fila + k, 1, et).font = NEGRITA
        c = ws.cell(fila + k, 2, v)
        if entrada:
            _entrada(c, fmt)
        else:
            c.number_format = fmt
            if k in (5, 6, 10):
                _resultado(c)
    dv = DataValidation(type="list", formula1='"' + ",".join(nm for nm, _ in UNIDADES) + '"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(u)
    ws.cell(fila + len(filas) + 1, 1, "E_h = E·t y σ_h = σ·√t; banda del 90 % = E_h ± 1.645·σ_h. Supone rendimientos normales con "
            "la media y covarianza de la ventana: extrapola la historia, no la predice.").font = SUAVE
    return {"proyeccion": f"B{fila + 5}", "horizonte": f"B{fila + 1}", "unidad": u, "fin": fila + len(filas) + 1}


def _hoja_matriz(wb: Workbook, precios: pd.DataFrame, rf: float = 0.07) -> dict:
    """«Matriz de precios y rendimiento» del documento del usuario (precios del más reciente al más antiguo, rendimiento
    (P_t − P_t−1)/P_t−1, promedio, varianza y desviación por activo, proporciones 1/N), completada con covarianzas,
    resultados del portafolio, Sharpe, proyección y el modelo de Solver listo."""
    nombres, N, n = list(precios.columns), len(precios), precios.shape[1]
    ws = wb.create_sheet("Matriz de precios")
    c0 = n + 4  # columna «Indicador financiero», como en el documento original (I con 5 activos)
    _encabezado(ws, "Matriz de precios y rendimiento", c0 + n,
                "Su documento, completado: pegue precios de cierre (del más reciente al más antiguo) en la matriz de borde "
                "punteado. " + AVISO)
    ws.cell(3, 1, "Matriz de precios").font = SECCION
    _cabecera(ws.cell(4, 1, "Fecha"))
    for j, nm in enumerate(nombres):
        _entrada(ws.cell(4, 2 + j, nm))
    for k in range(N):
        _entrada(ws.cell(5 + k, 1, precios.index[k].date()), "dd.mm.yyyy")
        for j in range(n):
            _entrada(ws.cell(5 + k, 2 + j, float(precios.iloc[k, j])), NUM)
    rt = 5 + N + 1
    ws.cell(rt, 1, "Matriz de rendimiento  r_t = (P_t − P_t−1) / P_t−1").font = SECCION
    _cabecera(ws.cell(rt + 1, 1, "Fecha"))
    for j in range(n):
        _cabecera(ws.cell(rt + 1, 2 + j, f"={L(2 + j)}4"))
    for k in range(N - 1):
        ws.cell(rt + 2 + k, 1, f"=A{5 + k}").number_format = "dd.mm.yyyy"
        for j in range(n):
            p = L(2 + j)
            ws.cell(rt + 2 + k, 2 + j, f'=IFERROR(({p}{5 + k}-{p}{6 + k})/{p}{6 + k},"")').number_format = "0.0000%"
    rango = lambda j: f"{L(2 + j)}{rt + 2}:{L(2 + j)}{rt + N}"  # noqa: E731
    cols = [L(c0 + 1 + j) for j in range(n)]
    _cabecera(ws.cell(4, c0, "Indicador financiero (diario)"))
    for j in range(n):
        _cabecera(ws.cell(4, c0 + 1 + j, f"={L(2 + j)}4"))
    for j in range(n):
        ws.cell(5, c0 + 1 + j, f"=AVERAGE({rango(j)})").number_format = "0.0000%"
        ws.cell(6, c0 + 1 + j, f"=VAR({rango(j)})").number_format = "0.000000"
        ws.cell(7, c0 + 1 + j, f"=SQRT({cols[j]}6)").number_format = "0.0000%"
    for f, et in ((5, "Rendimiento promedio"), (6, "Varianza"), (7, "Desviación estándar")):
        ws.cell(f, c0, et).font = NEGRITA
    _cabecera(ws.cell(9, c0, "Proporciones w (Solver las cambia)"))
    for j in range(n):
        _cabecera(ws.cell(9, c0 + 1 + j, f"={L(2 + j)}4"))
        _entrada(ws.cell(10, c0 + 1 + j, round(1 / n, 6)), PCT)
    props = f"{cols[0]}10:{cols[-1]}10"
    ws.cell(12, c0, "Matriz de varianzas y covarianzas (diaria) = COVARIANCE.S").font = SECCION
    fc, _ = _matriz(ws, 13, c0, [f"={L(2 + j)}4" for j in range(n)],
                    lambda i, j: f"=IFERROR(_xlfn.COVARIANCE.S({rango(i)},{rango(j)}),0)")
    fa = fc + n + 1
    ws.cell(fa, c0, "(Σw)_i auxiliar").font = SUAVE
    for i in range(n):
        ws.cell(fa, c0 + 1 + i, f"=SUMPRODUCT({cols[0]}{fc + i}:{cols[-1]}{fc + i},{props})").number_format = "0.000000"
    r0 = fa + 3
    ws.cell(r0 - 1, c0, "Portafolio").font = SECCION
    v = L(c0 + 1)
    for k, (et, f, fmt, entrada) in enumerate([
            ("Rendimiento del portafolio (diario)", f"=SUMPRODUCT({props},{cols[0]}5:{cols[-1]}5)", "0.0000%", False),
            ("Varianza del portafolio (diaria)", f"=SUMPRODUCT({props},{cols[0]}{fa}:{cols[-1]}{fa})", "0.000000", False),
            ("Desviación estándar del portafolio (diaria)", f"=SQRT(MAX({v}{r0 + 1},0))", "0.0000%", False),
            ("Rendimiento anualizado (×252)", f"={v}{r0}*252", PCT, False),
            ("Riesgo anualizado (×√252)", f"={v}{r0 + 2}*SQRT(252)", PCT, False),
            ("Tasa libre de riesgo anual", rf, PCT, True),
            ("Sharpe anual (objetivo de Solver)", f'=IFERROR(({v}{r0 + 3}-{v}{r0 + 5})/{v}{r0 + 4},"")', "0.000", False),
            ("Suma de proporciones (debe ser 100 %)", f"=SUM({props})", PCT, False),
            ("Proporción máxima por activo", 1, PCT, True)]):
        ws.cell(r0 + k, c0, et).font = NEGRITA
        c = ws.cell(r0 + k, c0 + 1, f)
        if entrada:
            _entrada(c, fmt)
        else:
            c.number_format = fmt
            if k in (3, 4, 6):
                _resultado(c)
    sharpe, suma, maximo = f"{v}{r0 + 6}", f"{v}{r0 + 7}", f"{v}{r0 + 8}"
    _solver(ws, sharpe, props, suma, maximo)
    proy = _proyeccion(ws, rt + N + 2, f"{v}{r0}", f"{v}{r0 + 2}", 100_000, 1, "meses", por_anio=False)
    ws.column_dimensions["A"].width = 46
    for c in range(2, c0 + n + 1):
        ws.column_dimensions[L(c)].width = 13
    ws.column_dimensions[L(c0)].width = 44
    return {"hoja": ws.title, "pesos": props, "Sharpe": sharpe, "suma": suma, "maximo": maximo, "rf": f"{v}{r0 + 5}",
            "precios": f"A5:{L(1 + n)}{4 + N}", "n": n, **proy}


def _pasos_solver(h: dict) -> list[str]:
    pesos, hoja = h["pesos"], h["hoja"]
    return [
        "Active Solver una sola vez: Archivo → Opciones → Complementos → abajo «Administrar: Complementos de Excel» → Ir → marque "
        "«Solver» → Aceptar.",
        f"Vaya a la hoja «{hoja}» y abra Datos → Solver: el modelo ya viene cargado (máximo Sharpe). Pulse «Resolver» → "
        "«Conservar solución de Solver». Los pasos siguientes son lo que ya está capturado, por si quiere cambiarlo.",
        f"Establecer objetivo: {h['Sharpe']} (Sharpe) con «Máx.»  —  o {h['σ_p anual']} (riesgo σ_p) con «Mín.» si busca el de "
        "menor riesgo.",
        f"Cambiando las celdas de variables: {pesos}.",
        f"Restricciones (botón Agregar): {h['Suma de pesos (debe ser 100 %)']} = 1  ·  {pesos} <= $B$5  ·  {pesos} >= $B$6.",
        "Método de resolución: GRG Nonlinear → Resolver → «Conservar solución de Solver». Los resultados en gris con doble línea se actualizan solos.",
    ]


def _bytes(wb: Workbook) -> bytes:
    _fuente_terminal(wb)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def plantilla() -> bytes:
    wb = Workbook()
    m = _hoja_matriz(wb, pd.read_csv(EJEMPLO_MATRIZ, index_col="Fecha", parse_dates=True))
    p = _hoja_parametrica(wb)
    h = _hoja_historica(wb, "Histórico ", [f"Activo {k}" for k in range(1, 6)], None, 253, [0.2] * 5, 0.07, 4, 0.4, 0, None)
    f_e, n = p["f_e"], p["n"]
    _guia(wb, "Plantilla del modelo de Markowitz", [
        ("¿Para qué sirve?", ["Calcula qué mezcla de inversiones da el mejor rendimiento por cada unidad de riesgo (teoría de "
                              "Markowitz). Tiene dos formas de usarla: un ejercicio rápido con supuestos y un modelo con sus "
                              "propios precios."]),
        ("Opción 0 · Su documento «Matriz de precios» (hoja «Matriz de precios»)", [
            f"{m['precios']}: fechas y precios de cierre, del más reciente al más antiguo, como en su documento (trae su ejemplo "
            "AAL, ABNB, MU, XOM y MSFT del 12 al 30-oct-2026). Puede cambiar nombres y precios.",
            "La matriz de rendimiento (P_t − P_t−1)/P_t−1, el rendimiento promedio, la varianza y la desviación estándar se "
            "calculan solas, igual que en su archivo.",
            f"Proporciones w en {m['pesos']} (empiezan en 1/N). Resultado: Sharpe anual {m['Sharpe']}, suma {m['suma']}; tasa libre "
            f"de riesgo en {m['rf']} y proporción máxima por activo en {m['maximo']}.",
            f"Solver: Datos → Solver ya trae el modelo (maximizar {m['Sharpe']} cambiando {m['pesos']}, suma = 1, cada w ≤ "
            f"{m['maximo']}, sin negativos, GRG Nonlinear). Pulse «Resolver».",
            f"Proyección: elija la cantidad en {m['horizonte']} y la unidad en {m['unidad']} (días, semanas, meses o años); "
            f"rendimiento esperado en {m['proyeccion']}. Con 15 días de precios la estimación es muy inestable: use más historia "
            "si puede."]),
        ("Opción A · Ejercicio rápido (hoja «Paramétrico Acelera»)", [
            "B3: tasa libre de riesgo anual (use la de CETES; p. ej. 7 %). B4: aversión al riesgo A (2 agresivo · 4–6 moderado · "
            "10 conservador).",
            f"B{f_e}:C{f_e + n - 1}: rendimiento esperado y riesgo (σ) anual de cada activo. E{f_e}:E{f_e + n - 1}: los pesos "
            "(deben sumar 100 %).",
            f"{p['rho']}: correlaciones entre activos (triángulo de borde punteado; el resto se copia solo).",
            f"Lea el resultado: rendimiento {p['E(r_p) anual']}, riesgo {p['σ_p anual']} y Sharpe {p['Sharpe']}. Más abajo, la "
            "tabla y la gráfica de dos activos muestran cómo la correlación baja el riesgo."]),
        ("Opción B · Con sus precios (hojas «Histórico Datos» e «Histórico Modelo»)", [
            "«Histórico Datos», fila 2 (B2:F2): escriba el nombre de sus 5 activos.",
            "Desde la fila 3: fecha en la columna A y precio de cierre de cada activo en B–F, del más antiguo al más reciente "
            "(ideal: 252 días, un año). Puede usar menos filas: las vacías no cuentan.",
            "Los rendimientos diarios (columnas H–L) y toda la hoja «Histórico Modelo» se calculan solos.",
            f"«Histórico Modelo»: B3 tasa libre de riesgo, B4 aversión A, B5 y B6 peso máximo y mínimo, {h['pesos']} sus pesos.",
            f"Resultado: rendimiento {h['E(r_p) anual']}, riesgo {h['σ_p anual']}, Sharpe {h['Sharpe']}. La suma de pesos "
            f"({h['Suma de pesos (debe ser 100 %)']}) debe dar 100 %.",
            f"Proyección: cantidad en {h['horizonte']}, unidad en {h['unidad']}; rendimiento esperado en el horizonte en "
            f"{h['proyeccion']}."]),
        ("Encontrar la mejor mezcla con Solver (Opción B)", _pasos_solver(h)),
        ("Cómo leer los resultados", [
            "E(r_p): rendimiento anual promedio que habría tenido la mezcla. σ_p: cuánto varía (riesgo). Sharpe: rendimiento extra "
            "sobre la tasa libre de riesgo por unidad de riesgo; más alto es mejor.",
            "y*: qué parte de su dinero pondría en esta mezcla según su aversión A; el resto iría a la tasa libre de riesgo (p. ej. "
            "CETES).",
            "Son datos del pasado: no garantizan resultados futuros. Compare siempre contra repartir en partes iguales."]),
    ])
    return _bytes(wb)


def libro(con, ajustes, portafolios: list[dict]) -> bytes:
    wb = Workbook()
    resumen = wb.create_sheet("Resumen")
    _encabezado(resumen, "Resumen de portafolios", 11, "Cifras enlazadas a cada hoja «P# Modelo»: si cambia los pesos allá, aquí se "
                                                        "actualizan. " + AVISO)
    cab = ["#", "Portafolio", "Perfil", "Método", "Activos", "Ventana", "E(r_p)", "σ_p", "Sharpe", "Capital", "Hoja"]
    for k, t in enumerate(cab, start=1):
        _cabecera(resumen.cell(3, k, t))
    hojas = []
    for k, p in enumerate(portafolios, start=1):
        res = markowitz.calcular(con, ajustes, p["especificacion"])  # con los datos actuales, para que las hojas cuadren
        s = res["especificacion"]  # normalizada: los guardados antes del horizonte en días/semanas/meses/años lo traen completo
        precios, _ = markowitz._datos(con, ajustes, [a["id"] for a in res["activos"]], s["ventana"])
        claves = [a["clave"] for a in res["activos"]]
        unidad = dict(zip(("dias", "semanas", "meses", "anios"), (u for u, _ in UNIDADES)))[s["horizonte_unidad"]]
        celdas = _hoja_historica(wb, f"P{k} ", claves, precios, 0, [a["peso"] for a in res["activos"]], s["rf"],
                                 s["aversion"], s["peso_max"], s["peso_min"], res, s["capital"], (s["horizonte_valor"], unidad))
        hojas.append((s["nombre"], celdas))
        h = f"'{celdas['hoja']}'"
        for c, v in enumerate([k, s["nombre"], res["objetivo_nombre"], res["metodo_nombre"], ", ".join(claves), s["ventana"],
                               f"={h}!{celdas['E(r_p) anual']}", f"={h}!{celdas['σ_p anual']}", f"={h}!{celdas['Sharpe']}",
                               s["capital"], celdas["hoja"]], start=1):
            cel = resumen.cell(3 + k, c, v)
            cel.number_format = PCT if c in (7, 8) else ("0.000" if c == 9 else (NUM if c == 10 else "General"))
            cel.alignment = Alignment(wrap_text=c == 5, vertical="top")
            cel.border = Border(bottom=LINEA)
    # Las hojas calculan con covarianza muestral y sin topes por moneda o sector: si la terminal usó otra cosa, se dice.
    distintos = [p["especificacion"]["nombre"] for p in portafolios
                 if p["especificacion"].get("covarianza", "muestral") != "muestral"
                 or p["especificacion"].get("usd_max") is not None or p["especificacion"].get("sector_max") is not None]
    if distintos:
        resumen.cell(5 + len(portafolios), 2, "Nota: " + ", ".join(distintos) + " se calcularon en la terminal con Ledoit-Wolf o "
                     "con topes por moneda o sector. Este libro usa covarianza muestral y no aplica esos topes: sus cifras "
                     "pueden diferir de las de la terminal.").font = Font(name=FUENTE, italic=True)
    for c, w in zip("ABCDEFGHIJK", (4, 30, 16, 34, 40, 9, 10, 10, 9, 14, 14)):
        resumen.column_dimensions[c].width = w
    resumen.freeze_panes = "A4"
    _guia(wb, f"{len(portafolios)} portafolio(s) del generador", [
        ("Qué contiene", [
            "«Resumen»: los portafolios lado a lado (rendimiento, riesgo y Sharpe enlazados a sus hojas).",
            "Por cada portafolio, «P# Datos» (precios en MXN y rendimientos diarios) y «P# Modelo» (estadísticos, covarianzas, "
            "correlaciones, pesos, resultados, frontera eficiente y gráfica).",
            "Los pesos con borde rojo punteado son los que calculó la terminal. Cámbielos para explorar: todo se recalcula.",
            "Columna «Peso Solver (terminal)»: el portafolio de máximo Sharpe que calculó la terminal; Solver en Excel llega a lo "
            "mismo (salvo redondeo y topes por moneda o sector, que Excel no aplica).",
            "Bloque «Proyección»: cambie la cantidad y la unidad (días, semanas, meses o años) para ver el rendimiento esperado, su "
            "rango del 90 % y la probabilidad de pérdida a ese plazo."]),
        ("Dónde está cada cosa", [f"«{nombre}» → hoja «{c['hoja']}»: pesos {c['pesos']} · rendimiento {c['E(r_p) anual']} · riesgo "
                                  f"{c['σ_p anual']} · Sharpe {c['Sharpe']} · suma de pesos {c['Suma de pesos (debe ser 100 %)']} · "
                                  f"horizonte {c['horizonte']} y {c['unidad']} → {c['proyeccion']}."
                                  for nombre, c in hojas]),
        ("Volver a optimizar con Solver", _pasos_solver(hojas[0][1]) + (
            ["En los demás portafolios use las celdas de su hoja (lista de arriba)."] if len(hojas) > 1 else [])),
        ("Cómo leer los resultados", [
            "E(r_p): rendimiento anual promedio en la ventana. σ_p: riesgo. Sharpe: rendimiento extra por unidad de riesgo (más alto "
            "es mejor). La gráfica muestra dónde queda su portafolio frente a la frontera eficiente.",
            "Son datos del pasado: no garantizan resultados futuros."]),
    ])
    return _bytes(wb)
