// Auditoría del catálogo de la Mesa: lo que la documentación promete (22 tipos = 15 externos + 6 accesos + 1 calculadora; cripto retirado el 1-nov)
// debe coincidir con el código, con las pestañas reales de index.html y con los widgets que sirve terminal/app.py.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {CATALOGO, PRESETS} from '../web/static/mesa.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const html = readFileSync(root + 'web/index.html', 'utf8');
const app = readFileSync(root + 'terminal/app.py', 'utf8');
const pestanas = new Set([...html.matchAll(/<button[^>]*role="tab"[^>]*id="([^"]+)"/g)].map(m => m[1]));
const widgetsServidor = new Set([...app.slice(app.indexOf('WIDGETS_TV = {'), app.indexOf('MAPAS_TV'))
  .matchAll(/"([a-z-]+)":\s*\("/g)].map(m => m[1]));

test('22 tipos: 15 externos, 6 accesos y la calculadora manual', () => {
  const por = t => CATALOGO.filter(c => c[2] === t);
  const externos = CATALOGO.filter(c => !['link', 'risk'].includes(c[2]));
  assert.equal(CATALOGO.length, 22);
  assert.equal(externos.length, 15);
  assert.equal(por('link').length, 6);
  assert.equal(por('risk').length, 1);
});

test('cada panel externo tiene ruta en el servidor y cada acceso apunta a una pestaña real', () => {
  assert.ok(widgetsServidor.size >= 15, 'no se pudo leer WIDGETS_TV de terminal/app.py');
  for (const [id, , tipo] of CATALOGO.filter(c => !['link', 'risk'].includes(c[2])))
    assert.ok(tipo === 'chart' || widgetsServidor.has(tipo), `${id}: el servidor no sirve /widget/${tipo}`);
  assert.ok(app.includes('@app.get("/grafica/{iid}"'), 'falta /grafica/{iid}');
  for (const [id, , tipo, destino] of CATALOGO.filter(c => c[2] === 'link'))
    assert.ok(pestanas.has(destino), `${id}: la pestaña ${destino} no existe en index.html`);
});

test('las disposiciones solo nombran paneles del catálogo y sin repetidos', () => {
  const ids = new Set(CATALOGO.map(c => c[0]));
  for (const [nombre, lista] of Object.entries(PRESETS)) {
    assert.equal(new Set(lista).size, lista.length, `${nombre} repite paneles`);
    for (const id of lista) assert.ok(ids.has(id), `${nombre}: ${id} no existe`);
  }
});

test('los paneles externos avisan del origen y ningún texto del catálogo promete tiempo real', () => {
  const fuente = readFileSync(root + 'web/static/mesa.mjs', 'utf8');
  assert.match(fuente, /Referencia externa de TradingView/);
  assert.doesNotMatch(CATALOGO.map(c => c[1]).join(' '), /tiempo real|en vivo|live/i);
  assert.doesNotMatch(readFileSync(root + 'web/static/mesa.html', 'utf8'), /innerHTML|onclick=|<script>[^<]/);
});
