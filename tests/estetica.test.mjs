import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';

const leer = (r) => readFileSync(new URL(`../${r}`, import.meta.url), 'utf8');
const hojas = ['web/static/app.css', 'web/static/mesa.css', 'web/static/navegacion.css', 'web/static/grafica.css',
  ...readdirSync(new URL('../web/static/recursos/', import.meta.url)).filter((f) => f.endsWith('.css')).map((f) => `web/static/recursos/${f}`)];

test('una sola familia tipográfica: --mono es la misma fuente y no hay monoespaciadas sueltas', () => {
  assert.match(leer('web/static/app.css'), /--mono: var\(--fuente\)/);
  for (const h of hojas) assert.doesNotMatch(leer(h), /monospace|Consolas|Courier|Menlo/i, h);
});

test('los widgets de terceros siempre se piden en tema oscuro', () => {
  assert.match(leer('web/static/app.js'), /const TEMA_TV = "dark";/);
  assert.match(leer('web/static/mesa.mjs'), /const tema='dark';/);
  assert.match(leer('web/static/navegacion.mjs'), /cinta-macro\?tema=dark/);
  for (const r of ['web/static/app.js', 'web/static/mesa.mjs', 'web/static/navegacion.mjs'])
    assert.doesNotMatch(leer(r), /prefers-color-scheme: dark\)['"]\)\.matches/, r);
});

test('ningún widget cortado: ajuste de alto con tope y rótulo del proveedor dentro de sus 32 px', () => {
  const nav = leer('web/static/navegacion.mjs');
  assert.match(nav, /clientHeight/);              // compara contra el interior: sin bucle por el borde
  assert.match(nav, /Math\.min\(2000,/);           // nunca crece sin límite
  const g = leer('web/static/grafica.css');
  assert.match(g, /\.tradingview-widget-copyright \{ height: 32px !important/);
  assert.match(g, /body:not\(\.sin-cabecera\) > \.tradingview-widget-container \{ flex: 1 1 auto/);
});
