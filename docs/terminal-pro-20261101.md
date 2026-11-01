# Terminal profesional y funciones de OpenTerminal — 1-nov-2026

Entrega de Claude. Línea base, coordinación, capturas, Excel de muestra, mediciones y pruebas en
`docs/terminal-pro-20261101-evidencia/`. Pendientes por ID en `docs/pendientes-terminal-pro-20261101.json`.
Sin trades (tampoco demo), sin brokers, estrategias, adaptadores ni puentes; sin mensajes externos; sin leer `.env`;
sin commit ni push. Revisión en 127.0.0.1:8766 con `TERMINAL_SIN_MOTOR=1` (motor, bot y sincronización apagados).

## 1. Qué se implementó y para qué sirve

- **Sistema visual único** (todas las áreas comparten `app.css`): negro/grises, texto blanco, rojo de identidad;
  tokens con contraste medido en `DESIGN.md`. Logo, favicon, páginas aisladas de widgets y Excel con el mismo rojo.
  Enlaces blancos con subrayado rojo; variaciones con signo y flecha; selección con borde y negritas además del color.
- **Mesa — paleta de comandos** sobre el buscador existente: instrumentos (clave y nombre), secciones, añadir/enfocar
  paneles y cambiar disposiciones (predefinidas y guardadas con nombre). Ctrl/Cmd+K, ↑ ↓, Enter, Escape.
- **Mesa — Seguimiento**: franja compacta con la MISMA lista y fuente de la sección Seguimiento
  (`/api/lista-seguimiento`): último cierre MXN, variación de 1 sesión solo si el dato es válido, fecha, proveedor y
  estado. Seleccionar una fila cambia el instrumento compartido. Lista vacía → SIN DATO + enlace para administrarla.
- **Mesa — cuadrícula configurable**: «Ancho» (fila completa, `aria-pressed`), arrastre con el asa ⠿ y ← → como
  equivalente por teclado. Tamaños y disposiciones con nombre en la misma clave `actinver.mesa.v1`; las disposiciones
  anteriores `{widgets, simbolo}` migran sin pérdida. Reordenar mueve nodos: conserva paneles abiertos y lo escrito en
  el escenario NQ. Iframes siguen creándose al desplegar y destruyéndose al cerrar. Sin bibliotecas nuevas.
- **Ficha de cotización nativa** (panel `info`): último cierre, variación con signo, fecha, RSI14; gráfica SVG propia
  (la misma técnica que Velas) con línea de cierres, **velas OHLCV cuando existen**, volumen, SMA20 y rango 1M/3M/6M/Todo.
  Procedencia: símbolo, intervalo, proveedor, moneda, ajuste por splits, ingesta y «histórico, no es cotización en vivo».
- **Noticias nativas** (`noticias` y `noticias-emisora`): titulares guardados de los RSS configurados, deduplicados por
  enlace y título normalizado (el mismo artículo de varias emisoras se agrupa), con publicación, ingesta, fuente y enlace
  al original. No se copia el artículo ni se muestra el «sentimiento» que guarda la tabla.
- **Panel macro + resumen** (panel `resumen`): USD/MXN, curva de EE. UU. (2 y 10 años; 30 SIN DATO), Fed funds, CPI,
  desempleo, nóminas, producción industrial, WTI/Brent y CETES 28 guardado; cada serie con periodo, frecuencia y
  fuente; aviso cuando los periodos difieren. Resumen fechado del corte: estado de datos, titulares 24 h y eventos de
  alto impacto. Sin explicaciones causales ni cifras «actuales».
- **Calendario** (panel `calendario`): eventos económicos de alto impacto (EE. UU. y México) de la próxima semana y el
  **contrato de datos de resultados**, marcado BLOQUEADO.
- **Excel de Markowitz** con la misma identidad; fórmulas y valores intactos (ver §5).

Backend nuevo: `terminal/mesa_datos.py` (solo lectura, sin red) y 4 rutas GET `/api/mesa/{noticias,macro,resumen,resultados}`.

## 2. Matriz OpenTerminal → Actinver

Inventario recontado en el clon local `ErTasselli/OpenTerminal` (remoto `https://github.com/ErTasselli/OpenTerminal.git`,
commit `aed097c680cd8ec1c391ae06966babe7d6d91fc6`): 15 tipos en `web/components/widgets/*Widget.tsx` y el switch de
`Workspace.tsx` (`volume` es un formato de precio, no un tipo). Sin código copiado; MIT no licencia sus datos.

| Tipo | Actinver | Estado |
|---|---|---|
| quote | Ficha de cotización nativa + ficha externa TradingView | **implementado** (cierres locales; no es cotización en vivo) |
| chart | Gráfica nativa en la Ficha (línea/velas/volumen/SMA/rango) + Gráfica TradingView identificada como externa + sección Velas | **implementado** (velas solo si hay OHLCV guardado) |
| watchlist | Franja de Seguimiento en Mesa (misma lista) | **implementado** |
| news | Noticias nativas general y por instrumento + widgets externos | **implementado** |
| macro | Panel macro nativo + widget externo | **parcial**: faltan DGS30, tasa objetivo Banxico e inflación de México (sin conector) |
| calendar | Eventos económicos nativos + contrato de resultados | **parcial / bloqueado**: resultados de empresas sin fuente autorizada |
| recap | Resumen fechado en el panel macro | **implementado** (descriptivo, sin causas) |
| heatmap | Mapa sectorial / ETF externos | **reutilizado** |
| screener | Explorador externo + Ranking | **reutilizado** |
| crypto | Mapa cripto externo (fuera del Reto) | **reutilizado** |
| options | Option Flow (acceso) | **reutilizado** |
| portfolio | Cartera (acceso) | **reutilizado** |
| ai | Asistente (acceso) | **reutilizado** |
| insider | Movimientos públicos (acceso) | **reutilizado** |
| tv | 16 widgets TradingView | **reutilizado** |

Paleta global (concepto de `CommandPalette.tsx`): **implementado** sobre el buscador de Mesa. Cuadrícula
(`react-grid-layout` en upstream): **parcial**: reordenar por arrastre/teclado y ancho de fila completa; sin
redimensionar alto por arrastre (los iframes ya permiten `resize: vertical`). Los 23 tipos se mantienen.

## 3. Archivos

Modificados en esta entrega (hashes finales en `evidencia/hashes-final.txt`, diff en `evidencia/cambios-propios.patch`):
`web/static/app.css`, `web/static/mesa.mjs`, `web/static/mesa.html`, `web/static/mesa.css`, `web/static/favicon.svg`,
`web/static/grafica.css`, `web/static/navegacion.css`, `terminal/app.py` (4 rutas y `isTransparent`),
`terminal/excel_markowitz.py`, `DESIGN.md`, `CLAUDE.md`, `CHANGELOG.md`, `docs/historial-estado.md`.
Nuevos: `terminal/mesa_datos.py`, `tests/test_mesa_datos.py`, `tests/test_excel_identidad.py`,
`tests/mesa_paleta.test.mjs`, este documento, `docs/pendientes-terminal-pro-20261101.json`, la carpeta de evidencia.
No se tocaron los archivos de la sesión de formación Python (ver `evidencia/COORDINACION.md`).

## 4. Capturas

`evidencia/capturas/`: `antes-1440-{terminal,mesa,oficina,cuaderno}.jpg` y `despues-1440-*.jpg`,
`despues-1440-mesa-paneles-nativos.jpg`, `despues-390-mesa-ficha.jpg` (sin desplazamiento horizontal: scrollWidth =
390) y `despues-768-mesa-claro.jpg` (modo claro). Las capturas del navegador integrado no pintan el contenido de los
iframes de TradingView anidados; esos widgets se comprobaron abriendo su página directamente.

## 5. Excel de Markowitz

Libros de muestra con datos SINTÉTICOS rotulados («MUESTRA SINTÉTICA A/B», CETES de muestra) generados con
`evidencia/excel_volcado.py`: `excel/{plantilla,libro}-sintetico-{antes,despues}.xlsx` y su volcado JSON. Comparación
celda por celda (`excel/comparacion-excel.txt`): mismas hojas, mismos nombres definidos, validaciones, uniones,
protección, imágenes y gráficas; **0 cambios en fórmulas, números o formatos numéricos**. Solo cambiaron 8 (plantilla)
y 7 (libro) textos de la leyenda de colores («azul claro» → «borde rojo punteado», «verde» → «gris con doble línea»).
La generación es determinista (dos corridas idénticas). Prueba nueva `tests/test_excel_identidad.py`: banda negra,
pestaña roja, entradas con borde punteado sin fórmulas, resultados con doble línea y fórmula, sin macros ni vínculos.

**Representación en Excel: NO comprobada.** Excel 2013 instalado rechazó la automatización (`RPC_E_CALL_REJECTED`,
probablemente un diálogo de activación); se cerró el proceso que se abrió. Solo hay validación programática.
Impresión: el cuerpo es blanco; la banda negra del título imprime como bloque oscuro (sin variante aparte).

## 6. Rendimiento (mismo servidor, misma base, mismo escenario)

| Medida | Antes | Después |
|---|---|---|
| Mesa, DCL / load (1.ª carga) | 176 / 212 ms | 168 / 178 ms |
| Mesa, cargas tibias | — | 136/146 y 85/94 ms |
| Recursos / transferencia | 9 / 38 KB | 12 / 49 KB |
| Memoria JS | 4 MB | 4 MB |
| `/api/universo?solo_catalogo` | 55 ms | 128 ms (1.ª, concurrente) / 55–61 ms |
| Rutas nuevas | — | macro 24–65 ms, resumen 34–43, noticias 18–62, resultados 5 |

Más peticiones por mostrar datos locales que antes no existían; `/api/mesa/resumen` lo comparten dos paneles en una
sola petición. Pocas repeticiones, misma PC; no se atribuye mejora de velocidad al parche. Detalle en
`evidencia/rendimiento-{antes,despues}.txt`. Sin polling nuevo.

## 7. Pruebas

Ver `evidencia/pytest-completa.txt` y el resumen en CHANGELOG. Específicas: `test_mesa_datos.py` (8),
`test_excel_identidad.py` (1), `mesa_paleta.test.mjs` (6). Navegador: paleta (instrumento, panel, disposición), ficha y
noticias nativas con datos reales locales, migración de disposición v1, «Ancho», ← →, arrastre, conservación del
escenario NQ y de paneles abiertos, 404 → SIN DATO, lista vacía → SIN DATO, 390/768/1440 px, oscuro y claro, consola
sin errores propios. Candados de futuros-lab consultados con `scripts/estado_demo.py` (solo lectura): PAPER;
adaptador, live y fondeada en `false`.

## 8. Pendientes

Por ID en `docs/pendientes-terminal-pro-20261101.json`.
