# Mejoras adoptadas desde COATL — 17-nov-2026

Ocho prácticas de COATL revisadas. Antes de cada una se buscó si ya existía algo equivalente. La identidad visual de DESIGN.md no cambió.

## Además: la terminal completa en GitHub Pages, sin servidor

- `scripts/exportar_estatico.cjs` (`npm run estatico`):
  - recorre las 23 pestañas de la demo con Edge sin ventana;
  - graba 220 respuestas GET de la API y copia la interfaz con las rutas reescritas a `sitio/terminal/`;
  - aborta si el servidor no está en modo demo: nunca exporta datos reales.
- `web/static/estatico.js` (solo en la exportación):
  - las lecturas salen de `api/<hash>.json`, con un índice para no pedir archivos que no existen;
  - escribir, calcular u operar responde con un aviso;
  - la vela en vivo queda apagada.
- Publicada en https://maikolv.github.io/help-quote-terminal/terminal/ por `.github/workflows/pages.yml`.

## Resultado por práctica

| # | Práctica | Estado | Dónde |
|---|---|---|---|
| 1 | Indicador «cálculo listo» | **Adoptada** | `web/static/app.js` (`marcarCalculo`): `<html data-calculo="pendiente\|listo" data-calculo-version="n">`. Cambia en la capa de API, así cubre plan, propuestas, riesgo y Estación. Usa `setTimeout`, no `requestAnimationFrame`, porque este se pausa con la pestaña oculta. |
| 2 | Historial único de versiones | **Adoptada** | Fuente: `docs/versiones.json`. `scripts/versiones.py generar` produce `CHANGELOG.md` (idéntico byte a byte; probado) y `docs/VERSIONES.md` (versión, fecha, commit, cifras). `docs/historial-estado.md` y «Estado comprobado» de CLAUDE.md siguen como narrativa: no se fusionaron para no perder texto. |
| 3 | Escenario de referencia | **Adoptada** | `terminal/escenario_referencia.py` + `tests/test_escenario_referencia.py`. Cartera demo 40/35/10/15 % (IVV, ACTIGOB, WALMEX, MSFT) con rendimientos fijos de semilla 2026: rendimiento esperado 17.31 %, volatilidad 10.26 %, VaR 95 % 1.02 %, CVaR 1.26 % y pesos de máximo Sharpe. |
| 4 | Resultado para llevar con QR | **Adoptada** | Ver detalle abajo. |
| 5 | Datos guardados aislados | **Ya cumplía** | Los 7 usos de localStorage son preferencias de vista. No hay cartera, pesos ni montos en el navegador: viven en el servidor local (SQLite). No se agregó cifrado: no hay nada sensible que cifrar. |
| 6 | Tipografías propias y CSP estricta | **Ya cumplía, se apretó** | Ver detalle abajo. |
| 7 | Accesibilidad medida | **Adoptada** | `tests/navegador/accesibilidad.cjs` (`npm run e2e`): axe WCAG 2.1 A/AA en Estación, plan y portafolios, a 1440, 375×812 y 812×375. Espera `data-calculo="listo"`. Se corrigieron 2 problemas sin cambiar la estética. |
| 8 | Documentos generados desde el modelo | **Adoptada** | Ver detalle abajo. |

### 4. Resultado para llevar con QR

- `web/static/reporte.js`:
  - botón «Imprimir o guardar PDF (con QR)» en el plan;
  - reporte propio para imprimir, no una captura de pantalla.
- El QR solo lleva el escenario (vista, fecha, modo de venta, demo) en el fragmento `#r=`. Nunca títulos, montos ni pesos, y nunca en la consulta de la URL.
- `qrcode-generator` 2.0.4 (MIT) va copiado en `web/static/vendor/`.
- El reporte ejecutivo trae QR a la terminal en Pages.

### 6. Tipografías propias y CSP estricta

- Ya cumplía:
  - sin Google Fonts (tipografías del sistema);
  - CSP principal con `style-src 'self'` y `font-src 'self'`;
  - los estilos dinámicos usan CSSOM, que la CSP permite.
- Se apretó:
  - `img-src` de la gráfica de TradingView pasó de `https:` a `https://*.tradingview.com`;
  - un `style.flex` se cambió por una clase.
- Excepción justificada: `'unsafe-inline'` en `style-src` de la gráfica de TradingView, porque su librería inyecta estilos en línea.

### 7. Accesibilidad: lo que se corrigió

- `label-content-name-mismatch` en las 174 celdas del mapa de calor: la etiqueta ahora empieza con el texto visible.
- Contraste en las filas inactivas del plan: se atenúan con color en lugar de opacidad.

### 8. Documentos generados desde el modelo

- `scripts/reporte_ejecutivo.cjs`: llena `docs/reporte-ejecutivo/plantilla.html` con:
  - las cifras del motor (`python -m terminal.escenario_referencia`);
  - las cifras de prueba de `docs/versiones.json`.
- El PDF se compone con Chromium (Edge, `page.pdf`).
- El Excel de Markowitz **ya** salía del modelo (`terminal/excel_markowitz.py` lee el resultado guardado, con la paleta de la terminal). No se tocó para no cambiar sus números.

## Descartado y por qué

- **Tipografías woff2 propias:** la terminal usa las del sistema por decisión de DESIGN.md. Servir woff2 no agrega seguridad, porque ya no hay fuentes externas.
- **Cifrado PBKDF2/AES-GCM:** no hay datos de cartera en el navegador (práctica 5).
- **Validador independiente en otro lenguaje** para el escenario de referencia: queda pendiente; hoy la vigilancia es la prueba de Python.
- **Pruebas de navegador con esperas fijas:** no había; `tests/navegador/mesa-disposiciones.cjs` ya esperaba por condición.

## Pruebas

| Prueba | Resultado |
|---|---|
| `node --test tests/*.test.mjs` | 55 aprobadas (52 + 3 nuevas del QR) |
| `uv run pytest` | Ver CHANGELOG de la versión 101 |
| `tests/test_versiones.py`, `tests/test_escenario_referencia.py` | Aprobadas |
| axe (`npm run e2e`) en la demo local y en la copia estática | 0 violaciones en 3 vistas × 3 tamaños, sin errores de página |
| Navegador, versión estática | Indicador «listo», QR `#r=` reabre la vista, consola sin errores |

## Archivos

- **Nuevos:**
  - `package.json`;
  - `scripts/exportar_estatico.cjs`, `scripts/versiones.py`, `scripts/reporte_ejecutivo.cjs`;
  - `terminal/escenario_referencia.py`;
  - `web/static/estatico.js`, `web/static/reporte.js`, `web/static/vendor/qrcode.js`;
  - `tests/navegador/accesibilidad.cjs`, `tests/reporte.test.mjs`, `tests/test_versiones.py`, `tests/test_escenario_referencia.py`;
  - `docs/versiones.json`, `docs/VERSIONES.md`, `docs/reporte-ejecutivo/plantilla.html`;
  - `sitio/terminal/` (generado).
- **Modificados:**
  - `web/static/app.js`, `web/static/app.css`, `web/index.html`, `web/static/apariencia.js`;
  - `terminal/app.py` (CSP);
  - `.github/workflows/pages.yml`, `.gitignore`;
  - `sitio/index.html`.
