import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buscarDestinos,siguienteSugerencia} from '../web/static/paleta.mjs';
test('flecha arriba inicial selecciona la última sugerencia y el recorrido envuelve',()=>{
 for(const n of [1,2,8]){
  assert.equal(siguienteSugerencia(-1,'ArrowUp',n),n-1);
  assert.equal(siguienteSugerencia(-1,'ArrowDown',n),0);
  assert.equal(siguienteSugerencia(0,'ArrowUp',n),n-1);
  assert.equal(siguienteSugerencia(n-1,'ArrowDown',n),0);
 }
 assert.equal(siguienteSugerencia(-1,'ArrowUp',0),-1);
 assert.equal(siguienteSugerencia(0,'Escape',2),-1);
});
test('paleta compartida busca nombre, clave e ID y solo acepta destinos locales',()=>{
 const datos={catalogo:[{id:'SIC:NVDA',clave_operable:'NVDA',nombre:'NVIDIA'}],secciones:[{titulo:'Mesa',url:'/static/mesa.html'},{titulo:'Mesa falsa',url:'//externo.test'},{titulo:'Mesa código',url:'javascript:alert(1)'}]};
 assert.equal(buscarDestinos('sic:nvda',datos)[0].valor,'SIC:NVDA');
 assert.equal(buscarDestinos('nvidia',datos)[0].tipo,'instrumento');
 assert.deepEqual(buscarDestinos('mesa',datos),[{tipo:'seccion',etiqueta:'Ir a Mesa',valor:'/static/mesa.html'}]);
 assert.deepEqual(buscarDestinos(' ',datos),[]);
});
test('paleta limita resultados para no desplegar el universo completo',()=>{
 const catalogo=Array.from({length:100},(_,i)=>({id:String(i),clave_operable:'X'+i,nombre:'Empresa'}));
 assert.equal(buscarDestinos('empresa',{catalogo}).length,8);
});
