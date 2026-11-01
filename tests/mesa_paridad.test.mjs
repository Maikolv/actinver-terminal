import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {planNQ} from '../web/static/mesa.mjs';
const vectores=JSON.parse(readFileSync(new URL('../docs/auditoria-reels-20261031-evidencia/codex-continuacion/vectores.json',import.meta.url)));
test('contrato de 12 escenarios NQ y resultados finitos',()=>{
 for(const v of vectores){const args=[v.entrada,v.stop,v.r,v.presupuesto,v.costos,v.slip];
  if(!v.valido){assert.throws(()=>planNQ(...args),v.id);continue;}
  const p=planNQ(...args);assert.ok(Object.values(p).filter(x=>typeof x==='number').every(Number.isFinite),v.id);
  if(v.id==='largo')assert.deepEqual([p.tp,p.sl,p.riesgo,p.contratos],[20020,19990,215,4]);
  if(v.id==='corto')assert.equal(p.tp,19980);
 }
 for(const x of [NaN,Infinity,-Infinity])assert.throws(()=>planNQ(x,19990,2,100));
});
test('el archivo Pine comparte epsilon, límites y no tiene operaciones ni alertas',()=>{
 const p=readFileSync(new URL('../tradingview/mesa_riesgo_nq.pine',import.meta.url),'utf8');
 assert.match(p,/objetivoR \/ tick \+ 0\.00000001/);assert.match(p,/maxval=1000,/);
 assert.doesNotMatch(p,/\b(strategy\.(entry|exit|order)|alert(condition)?\s*\()/);
});
