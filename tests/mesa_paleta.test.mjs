import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buscarPaleta,signo,fmt,recortar,normalizarTamanos,CATALOGO,NOMBRES_PRESET,obtener} from '../web/static/mesa.mjs';

test('el formato numérico distingue cero de campos vacíos o booleanos', () => {
  for(const valor of [null,undefined,'','  ',false,true,NaN,Infinity])assert.equal(fmt(valor),'SIN DATO');
  assert.equal(fmt(0),'0.00');
  assert.equal(fmt('0'),'0.00');
});

const catalogo=[{id:'SIC:NVDA',clave_operable:'NVDA',nombre:'NVIDIA Corp'},{id:'BMV:GMEXICO',clave_operable:'GMEXICO B',nombre:'Grupo México'}];
const secciones=[{titulo:'Velas',url:'/?vista=tab-velas'},{titulo:'Datos y fuentes',url:'/?vista=tab-universo'}];

test('la paleta busca instrumentos por clave y nombre, secciones, paneles y disposiciones', () => {
  assert.deepEqual(buscarPaleta('méxico',{catalogo}).map(r=>r.valor),['BMV:GMEXICO']);
  assert.deepEqual(buscarPaleta('nvda',{catalogo}).map(r=>r.tipo),['instrumento']);
  assert.equal(buscarPaleta('velas',{secciones})[0].valor,'/?vista=tab-velas');
  const p=buscarPaleta('macro',{activos:['resumen']}).find(r=>r.tipo==='panel');
  assert.match(p.etiqueta,/^Enfocar/);assert.match(buscarPaleta('macro').find(r=>r.tipo==='panel').etiqueta,/^Añadir/);
  assert.equal(buscarPaleta('futuros').find(r=>r.tipo==='disposicion').valor,'futuros');
  assert.deepEqual(buscarPaleta('   '),[]);
  assert.ok(Object.keys(NOMBRES_PRESET).length>=3);
});

test('la paleta nunca ofrece acciones financieras', () => {
  const todo=buscarPaleta('a',{catalogo,secciones}).concat(buscarPaleta('orden'),buscarPaleta('comprar'),buscarPaleta('vender'));
  assert.ok(todo.every(r=>['instrumento','seccion','panel','disposicion'].includes(r.tipo)));
  assert.ok(!todo.some(r=>/comprar|vender|enviar orden|ejecutar/i.test(r.etiqueta)));
});

test('signo y flecha además del color; SIN DATO cuando no hay variación válida', () => {
  assert.equal(signo(0.0123),'+1.23 % ▲');assert.equal(signo(-0.0123),'−1.23 % ▼');assert.equal(signo(0),'0.00 % =');
  for(const x of [null,undefined,NaN,Infinity])assert.equal(signo(x),'SIN DATO');
});

test('rango temporal recorta sin inventar puntos', () => {
  const p=Array.from({length:100},(_,i)=>({cierre:i}));
  assert.equal(recortar(p,'1M').length,21);assert.equal(recortar(p,'6M').length,100);assert.equal(recortar(p,'Todo').length,100);
  assert.equal(recortar(p,'1M')[0].cierre,79);
});

test('tamaños guardados: migran disposiciones viejas y descartan ids o valores desconocidos', () => {
  assert.deepEqual(normalizarTamanos(undefined),{});
  assert.deepEqual(normalizarTamanos({info:'ancho',mapa:'gigante','https://x':'ancho'}),{info:'ancho'});
  assert.equal(CATALOGO.length,22);
});

test('consultas simultáneas a la misma ruta comparten una sola petición y no quedan en caché', async () => {
  let llamadas=0;const original=globalThis.fetch;
  globalThis.fetch=async()=>{llamadas++;await new Promise(r=>setTimeout(r,10));return {ok:true,json:async()=>({n:llamadas})};};
  try{
    const [a,b]=await Promise.all([obtener('/api/x'),obtener('/api/x')]);
    assert.equal(llamadas,1);assert.deepEqual(a,b);
    await obtener('/api/x');assert.equal(llamadas,2);  // terminada la primera, se vuelve a pedir: nunca se sirve una respuesta vieja
    globalThis.fetch=async()=>({ok:false,status:404});
    await assert.rejects(obtener('/api/y'),/HTTP 404/);
  }finally{globalThis.fetch=original;}
});
