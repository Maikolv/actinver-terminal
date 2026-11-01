import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizarLayout,planNQ,CATALOGO,PRESETS} from '../web/static/mesa.mjs';
test('la disposición descarta destinos inyectados, duplicados y tipos desconocidos',()=>{
 assert.deepEqual(normalizarLayout(['mapa','https://evil.test','mapa','riesgo']),['mapa','riesgo']);
 assert.deepEqual(normalizarLayout(null),PRESETS.mercado);
 assert.equal(new Set(CATALOGO.map(c=>c[0])).size,CATALOGO.length);
});
test('NQ largo y corto: tick, multiplicador, costos y presupuesto conservador',()=>{
 const p=planNQ(20000,19990,2,1000,5,2);
 assert.equal(p.tp,20020);assert.equal(p.sl,19990);assert.equal(p.riesgo,215);assert.equal(p.contratos,4);
 assert.equal(planNQ(20000,20010,2,100).tp,19980);
 assert.equal(planNQ(20000,20010,2,100).contratos,0);
 assert.equal(planNQ(20000,19999.75,1.1,100).tp,20000.25);
});
test('rechaza escenarios inválidos y objetivos imposibles',()=>{
 for(const v of [[NaN,19000,2,100],[20000,19999.9,2,100],[20000,20000,2,100],
 [20000,19990,0,100],[20000,19990,2,-1],[20000,19990,2,100,-1],
 [1,100,2,100],[20000,19999.75,.1,100]]) assert.throws(()=>planNQ(...v));
});
test('cada escenario listo de NQ produce un plan válido con al menos un contrato y lectura sencilla',async()=>{
 const {ESCENARIOS_NQ,lecturaSencilla}=await import('../web/static/mesa.mjs');
 assert.ok(ESCENARIOS_NQ.length>=3);
 for(const e of ESCENARIOS_NQ){const v=e.valores;const p=planNQ(v.entrada,v.sl,v.r,v.presupuesto,v.costos,v.slip);
  assert.ok(p.contratos>=1,e.id);assert.match(lecturaSencilla(p),/perdería cerca de USD/);}
 assert.match(lecturaSencilla(planNQ(20000,19990,2,100)),/no alcanza/);
});
