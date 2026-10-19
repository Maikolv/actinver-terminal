import {test} from 'node:test';
import assert from 'node:assert/strict';
import {resumir, instrumentosDelCatalogo} from '../web/static/recursos/oficina-inversion.mjs';
const ahora=Date.parse('2026-10-19T15:05:00Z');
const barra={inicio:'2026-10-19T15:00:00Z',fuente:'autorizada',feed:'CME',calidad:'proveedor',ema20:101,ema50:100};
test('catálogo completo, sin duplicados ni instrumentos inactivos, preserva vencimiento',()=>{
 const u={instrumentos:[{id:'BMV:NAFTRAC',clave_operable:'NAFTRAC',nombre:'ETF',estado:'activo'},{id:'SIC:NVDA',nombre:'NVIDIA',estado:'activo'},{id:'BAJA',estado:'inactivo'}]};
 const f={sic:[{id:'SIC:NVDA',clave:'NVDA'}],con_datos:['SIC:NVDA','CME:MNQZ26','CME:MNQZ26']};
 const r=instrumentosDelCatalogo(u,f);
 assert.equal(r.length,3);assert.equal(r.find(i=>i.id==='SIC:NVDA').conDatos,true);
 assert.equal(r.find(i=>i.id==='CME:MNQZ26').id,'CME:MNQZ26');assert.ok(r.find(i=>i.id==='BMV:NAFTRAC'));
});
test('catálogo parcial o vacío no inventa instrumentos',()=>{
 assert.deepEqual(instrumentosDelCatalogo(),[]);
 assert.deepEqual(instrumentosDelCatalogo({}, {con_datos:['CME:MESZ26']}).map(i=>i.id),['CME:MESZ26']);
});
test('sin datos no inventa mercado ni delta',()=>{
 const r=resumir({}, {},ahora);assert.match(r.mensajes[0].texto,/No hay velas/);assert.match(r.mensajes[2].texto,/no disponible/);assert.equal(r.ordenes_habilitadas,false);
});
test('comparación sólo con indicadores finitos y una fuente real',()=>{
 const r=resumir({barras:[barra]}, {},ahora);assert.match(r.mensajes[1].texto,/sobre/);
 for(const b of [{...barra,ema20:null},{...barra,calidad:'sintetico'}])assert.match(resumir({barras:[b]}, {},ahora).mensajes[1].texto,/Sin comparación/);
 assert.match(resumir({barras:[barra,{...barra,feed:'otro'}]}, {},ahora).mensajes[1].texto,/Sin comparación/);
});
test('datos antiguos o futuros suspenden revisión intradía',()=>{
 for(const t of [ahora+1e7,ahora-1e7])assert.match(resumir({barras:[barra]}, {},t).mensajes[4].texto,/suspendida/);
});
test('delta cero válido, lado ausente o feeds mezclados bloqueados',()=>{
 const f={resumen:{n:2,con_lado:2,delta:0},procedencia_operaciones:[{calidad:'proveedor'}]};
 assert.match(resumir({},f,ahora).mensajes[2].texto,/Delta observado 0/);
 f.resumen.con_lado=1;assert.match(resumir({},f,ahora).mensajes[2].texto,/no disponible/);
 f.resumen.con_lado=2;f.procedencia_operaciones.push({calidad:'real'});assert.match(resumir({},f,ahora).mensajes[2].texto,/no disponible/);
});
