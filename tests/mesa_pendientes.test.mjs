import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CATALOGO,AVISO_RIESGO,rutaVelas,planNQ} from '../web/static/mesa.mjs';
test('Velas recibe el instrumento codificado sin añadir un panel',()=>{
 const simbolo='SIC:NVDA&vista=inyectada';const url=new URL(rutaVelas(simbolo),'http://127.0.0.1');
 assert.equal(url.searchParams.get('vista'),'tab-velas');assert.equal(url.searchParams.get('simbolo'),simbolo);
 assert.equal(CATALOGO.length,22);assert.equal(CATALOGO.find(c=>c[0]==='grafica')[1],'Gráfica TradingView');
});
test('el escenario advierte gap y distingue tope de fill en JS y Pine',()=>{
 assert.match(AVISO_RIESGO,/tope del escenario, no del fill real/);assert.match(AVISO_RIESGO,/gap.*deslizamiento/);
 const pine=readFileSync(new URL('../tradingview/mesa_riesgo_nq.pine',import.meta.url),'utf8');assert.match(pine,/Tope del escenario, no del fill real/);assert.match(pine,/gap o deslizamiento mayor/);
});
test('se mantiene la calculadora solo NQ sin cambiar sus unidades',()=>{
 assert.match(CATALOGO.find(c=>c[0]==='riesgo')[1],/solo NQ/);assert.equal(planNQ(20000,19990,2,1000).riesgo,200);
});
