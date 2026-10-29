import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {GUIAS} from '../web/static/guias.mjs';
import {instrumentosDelCatalogo} from '../web/static/recursos/oficina-inversion.mjs';

const leer = (r) => readFileSync(new URL(`../${r}`, import.meta.url), 'utf8');
const PAGINAS = ['web/static/recursos/oficina-inversion.html', 'web/static/recursos/laboratorio-bots-reel.html',
  'web/static/recursos/practica-proyectos-financieros.html'];

test('cada sección de la terminal tiene guía completa, sin excepción', () => {
  const paneles = [...leer('web/index.html').matchAll(/role="tabpanel" id="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(paneles.length >= 24);
  for (const p of paneles) {
    const g = GUIAS[p];
    assert.ok(g, `sin guía: ${p}`);
    assert.ok(g.titulo && g.que && g.pasos.length >= 1 && g.terminos.length >= 1, `guía incompleta: ${p}`);
  }
});

test('cada página de área carga la guía y tiene la suya', () => {
  for (const r of ['web/index.html', ...PAGINAS]) assert.match(leer(r), /src="\/static\/guias\.mjs"/, r);
  for (const r of PAGINAS) assert.ok(GUIAS[`/${r.replace(/^web\//, '')}`], `sin guía: ${r}`);
});

test('la oficina no muestra documentos de trabajo y ofrece accesos al instrumento', () => {
  const h = leer('web/static/recursos/oficina-inversion.html');
  assert.doesNotMatch(h, /Documentos de trabajo|prompt-[a-z-]+\.md/);
  for (const id of ['ir-velas', 'ir-orderflow', 'ir-optionflow']) assert.match(h, new RegExp(`id="${id}"`));
  assert.doesNotMatch(leer('web/static/recursos/laboratorio-bots-reel.html'), /prompt-[a-z-]+\.md/);
});

test('la oficina lista primero los instrumentos con datos guardados', () => {
  const u = {instrumentos: [{id: 'BMV:AMX', clave_operable: 'AMX', nombre: 'América Móvil', estado: 'activo'},
    {id: 'SIC:NVDA', clave_operable: 'NVDA', nombre: 'NVIDIA', estado: 'activo'}]};
  assert.equal(instrumentosDelCatalogo(u, {con_datos: ['SIC:NVDA']})[0].id, 'SIC:NVDA');
});
