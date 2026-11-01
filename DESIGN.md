# DESIGN.md — sistema visual de Actinver Terminal

Formato inspirado en la colección `awesome-design-md` y en los criterios de `hallmark`: sin estética genérica y con contraste verificado.

## Principio

**Un dato observado, un dato retrasado y un pronóstico nunca se ven igual.**

| Clase de dato | Tratamiento visual |
|---|---|
| Observado y vigente (`REAL_TIME` o EOD de la última sesión) | chip verde «vigente», cifra monoespaciada |
| Retrasado o desconocido (`DELAYED`, `UNKNOWN`) | chip ámbar o gris, con la latencia en segundos al lado |
| Sin precio confiable | chip rojo **SIN PRECIO CONFIABLE**; el motivo se lee al pasar el cursor |
| Referencia externa (bolsa de origen en USD) | columna separada, texto secundario, con la etiqueta «estimado» |
| Pronóstico | sección FUTURO con borde discontinuo y sello violeta «FUTURO · ESTIMACIONES»; rangos 10–90 %, nunca un solo número |
| Ficticio | banda «DATOS SIMULADOS» y la marca «FICTICIO» en cada cotización |

**Cualquier persona puede usar cualquier herramienta sin saber qué escribir.** Toda calculadora o formulario de
cálculo abre con valores iniciales que ya producen un resultado válido, ofrece «Ejemplo listo» o «Escenario listo»
con opciones predefinidas (más «Personalizado») y, cuando el resultado es técnico, lo acompaña de una lectura en
palabras simples. Los ejemplos son hipótesis de estudio y se rotulan así; nunca se presentan como cotizaciones.
Hoy: escenarios NQ en Mesa (`ESCENARIOS_NQ`), ejemplos de Modelos (`EJEMPLOS_OPCIONES`) y, en el Cuaderno, una lista
de opciones precargadas junto a cada campo de texto (`PRECARGAS`) más escenarios listos de valoración y volatilidad. `tests/mesa.test.mjs` exige que cada escenario NQ calcule al menos un contrato.

**Estética de terminal profesional (1-nov-2026).** Negro y grises para fondos, blanco y grises claros para texto y
cifras, rojo como acento de identidad y selección. Alta densidad: títulos y encabezados de tabla en monoespaciado y
mayúsculas, filas compactas alternadas, bordes finos. Referencia de densidad y organización: terminales financieras
profesionales (tipo Bloomberg), con identidad propia: no se usa su marca, logotipo, textos, recursos ni código.
Paleta de partida inspirada en OpenTerminal (ErTasselli, MIT). El tema oscuro es la referencia; el claro conserva los
mismos roles.

**El rojo nunca es la única señal.** Selección = borde/subrayado rojo + negritas + `aria-selected`/`aria-pressed`;
pérdida = color + signo «−» + ▼; error y antigüedad = chip con texto («vencido», «SIN DATO») + color. Una ganancia
siempre lleva «+» y ▲ en verde: la paleta roja no la convierte en pérdida. Los enlaces son blancos con subrayado rojo
(no rojos) para no competir con las pérdidas.

**Mapas de calor: verde, rojo y gris.** Verde = positivo o mejor, rojo = negativo o peor, gris = neutro (±0.25 % en
Mercado; |t| < 0.05 en escalas normalizadas) o sin dato. Una sola función (`colorCalor` en `app.js`) para Robustez,
volatilidad implícita (alta en rojo), GEX y correlaciones (rojo: se mueven juntos); el texto conserva signo y cifra.
Los mapas de calor de TradingView usan su propia escala rojo/verde con gris en el cero.

**Sin cripto.** Retirado de la interfaz el 1-nov-2026: widgets, cotizaciones, cinta, panel de Mesa y selectores.

## Tokens

Centralizados en `web/static/app.css` (`:root`, oscuro en `prefers-color-scheme: dark` y `[data-theme="dark"]`).
Contraste medido con la fórmula WCAG 2.x (script en `docs/terminal-pro-20261101.md`).

| Token | Oscuro | Claro | Uso | Contraste medido |
|---|---|---|---|---|
| `--fondo` | `#090a0c` | `#f5f5f4` | página | — |
| `--superficie` | `#121419` | `#ffffff` | tarjetas, cabecera | — |
| `--superficie-2` | `#1b1e24` | `#ecece9` | elevada, encabezados de tabla | — |
| `--texto` | `#f3f4f6` | `#111318` | texto y cifras | 18.0 / 16.7 / 15.2 (oscuro: fondo/superficie/elevada); 17.0–18.6 (claro) |
| `--texto-2` | `#b4bac4` | `#4a505a` | texto secundario | 10.2 / 9.4 / 8.6; claro 6.9–8.1 |
| `--borde` | `#343942` | `#d4d4d0` | separadores decorativos | 1.4–1.7 (decorativo, no transmite información) |
| `--borde-control` | `#6b7280` | `#6e747e` | límite de campos y botones secundarios | 3.45–4.10; claro 3.98–4.71 (≥ 3:1) |
| `--acento-grafico` | `#d94848` | `#b42626` | marca, bordes de selección, barras | 4.69 / 4.36 / 3.95 (≥ 3:1 gráfico) |
| `--acento` | `#f06a6a` | `#b42626` | texto rojo (selección) | 6.58 / 6.12 / 5.55; claro 5.47–6.47 |
| `--acento-solido` | `#b42626` | `#b42626` | fondo de botón primario con texto blanco | blanco sobre él 6.47; lleva borde `--acento-grafico` |
| `--positivo` / `--negativo` | `#4cc38a` / `#f2777a` | `#1d6b3a` / `#a3261c` | variaciones, siempre con signo y flecha | ≥ 6.1 en oscuro; ≥ 5.5 en claro |
| `--marca` | `#d94848` | `#d94848` | logo, favicon y Excel | trazo blanco sobre rojo 4.22 (≥ 3:1 gráfico) |

Rechazado tras medir: `#d94848` como texto sobre superficie (4.36) y elevada (3.95) no llega a 4.5:1; blanco sobre
`#d94848` (4.22) tampoco. Por eso el rojo se divide en tres tokens (texto, sólido y gráfico).

- **Estados de dato:** `--vigente`, `--retrasado`, `--vencido`, `--sin-datos`, `--sintetico` siguen distintos entre sí
  y del acento; FUTURO conserva el violeta y el borde discontinuo.
- **Widgets de terceros (TradingView):** siempre en tema oscuro (negro), en cualquier modo de la terminal. Nunca se
  cortan: `navegacion.mjs` mide el contenido de cada marco `/widget` o `/grafica` (mismo origen) y lo agranda hasta
  mostrarlo completo (tope 2000 px); el rótulo del proveedor cabe en sus 32 px. Solo admiten `colorTheme` e `isTransparent`. La terminal pide
  transparencia para que tomen el fondo de `grafica.css`; sus colores internos (velas, textos, logos) los decide el
  proveedor y **no** se pueden recolorear desde Actinver.
- **Excel de Markowitz:** banda negra con título blanco y borde rojo, encabezados gris oscuro con texto blanco, cuerpo
  blanco (imprime legible). Entrada = relleno muy claro + **borde rojo punteado**; resultado = gris + **negritas + doble
  línea**: se distinguen por forma, no solo por color. Sin macros ni vínculos externos.
- **Tipografía:** una sola familia en toda la terminal, Mesa, Oficina, Cuaderno, páginas de widgets y Excel: Segoe UI (con
  respaldo del sistema). `--mono` apunta a la misma familia; las cifras se alinean con `font-variant-numeric: tabular-nums`.
  Sin fuentes externas. Excepción: el texto DENTRO de los widgets de TradingView usa la fuente del proveedor.
- **Cuadrícula:** gutter de 16 px; tres cortes: ≤ 720 px, 721–1024 px y > 1024 px.

## Componentes

- **Tarjetas de espacio:** PASADO (borde gris), PRESENTE (borde verde) y FUTURO (borde violeta discontinuo).
- **Ficha de revisión en cada alerta:** qué ocurrió, qué datos lo sustentan, qué falta confirmar, costos, riesgos y opciones para revisar. **No hay botones de operar.**
- **Esqueletos de carga:** tres pulsos como máximo; se respeta la preferencia de movimiento reducido del sistema.

## Accesibilidad

Pestañas con ARIA y navegación con teclado (flechas, Inicio, Fin). Todo el contenido dinámico se crea con `textContent`, nunca como HTML.
Foco visible blanco (oscuro) o casi negro (claro) de 3 px. `prefers-reduced-motion` desactiva animaciones y transiciones.
Mesa: paleta con `role="combobox"`/`listbox`, Ctrl/Cmd+K, ↑ ↓, Enter y Escape; reordenar con ← → (equivalente del
arrastre con el asa ⠿) y «Ancho» con `aria-pressed`.
