import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {destinoLocal} from '../web/static/navegacion.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const config=JSON.parse(readFileSync(root+'web/static/navegacion.json','utf8'));
test('el selector cubre todas las pestañas reales de la terminal',()=>{
 const html=readFileSync(root+'web/index.html','utf8');
 const ids=[...html.matchAll(/<button[^>]*role="tab"[^>]*id="([^"]+)"/g)].map(m=>m[1]);
 assert.deepEqual(config.secciones.map(s=>new URL(s.url,'http://localhost').searchParams.get('vista')).sort(),ids.sort());
});
test('todas las áreas independientes existen y comparten navegación',()=>{
 for(const a of config.areas) {
  const url=destinoLocal(a.url,'http://localhost');
  if(url.pathname==='/')continue;
  const path=root+'web'+url.pathname;
  assert.ok(existsSync(path),a.url);
  const html=readFileSync(path,'utf8');
  assert.match(html,/aria-label="Navegación entre áreas"/);
  assert.match(html,/src="\/static\/navegacion.mjs"/);
 }
});
test('el navegador sólo admite destinos locales',()=>{
 assert.equal(destinoLocal('/?vista=tab-riesgo','http://localhost').searchParams.get('vista'),'tab-riesgo');
 for(const u of ['https://otro.test/','//otro.test/','/\\otro.test/','javascript:alert(1)'])assert.throws(()=>destinoLocal(u,'http://localhost'));
});
