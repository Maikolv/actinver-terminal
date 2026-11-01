import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const fuente=readFileSync(new URL('../web/static/app.js',import.meta.url),'utf8');
function cliente(fetch){const contexto=vm.createContext({fetch,AbortSignal,CSRF:'prueba_no_secreta'});vm.runInContext(fuente.slice(fuente.indexOf('const consultasPendientes'),fuente.indexOf('function notificar('))+'\nthis.apiPrueba=api;',contexto);return contexto.apiPrueba;}
test('GET concurrentes se comparten; al terminar se consulta de nuevo, sin caché de precios',async()=>{
 let n=0,liberar;const api=cliente(async()=>{n++;await new Promise(r=>liberar=r);return {ok:true,json:async()=>({source:'offline',event_time:'2026-01-01'})};});
 const a=api('/api/estado'),b=api('/api/estado');assert.equal(n,1);liberar();assert.deepEqual(await a,await b);
 const c=api('/api/estado');assert.equal(n,2);liberar();await c;
});
test('un error libera la solicitud y no reintenta ni devuelve datos anteriores',async()=>{
 let n=0;const api=cliente(async()=>{n++;throw Error('offline');});await assert.rejects(api('/x'));await assert.rejects(api('/x'));assert.equal(n,2);
});
test('POST nunca se agrupan',async()=>{let n=0;const api=cliente(async()=>{n++;return {ok:true,json:async()=>({})};});await Promise.all([api('/x',{method:'POST'}),api('/x',{method:'POST'})]);assert.equal(n,2);});
test('el polling de Ranking no consulta con la página oculta',()=>{
 const linea=fuente.split('\n').find(x=>x.startsWith('setInterval(')&&x.includes('cargarRanking'));
 let consulta=0,callback;const document={hidden:true};
 vm.runInNewContext(linea,{document,pestanaVisible:()=>true,cargarRanking:()=>consulta++,setInterval:f=>callback=f});
 callback();assert.equal(consulta,0);document.hidden=false;callback();assert.equal(consulta,1);
});
