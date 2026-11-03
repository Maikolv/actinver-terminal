import {test} from 'node:test';
import assert from 'node:assert/strict';
import {simularSecuencias} from '../web/static/simulador-secuencias.mjs';
const base={acierto:.45,ratio:1.4,riesgo:100,objetivo:1500,drawdown:1000,limiteDiario:400,tradesDia:5,maxTrades:100,iteraciones:1000,semilla:42,trailing:'estatico'};
test('semilla reproducible y partición completa de intentos hipotéticos',()=>{
 const r=simularSecuencias(base);assert.deepEqual(r,simularSecuencias(base));
 assert.equal(r.aprobadas+r.fallidas+r.inconclusas,base.iteraciones);
 assert.ok(r.intervaloMonteCarlo[0]>=0&&r.intervaloMonteCarlo[1]<=1);
 assert.equal(r.costoSimplificado,null);
});
test('casos límite de acierto, costos y horizonte no fabrican aprobación',()=>{
 assert.equal(simularSecuencias({...base,acierto:0}).fallidas,1000);
 const r=simularSecuencias({...base,acierto:1,objetivo:300,ratio:1,tarifa:10});
 assert.equal(r.aprobadas,1000);assert.equal(r.tradesMediosAprobadas,3);assert.equal(r.costoSimplificado,10);
 assert.equal(simularSecuencias({...base,acierto:1,costo:200}).fallidas,1000);
 const inconclusa=simularSecuencias({...base,maxTrades:1,tarifa:10});assert.equal(inconclusa.inconclusas,1000);assert.equal(inconclusa.costoSimplificado,null);
});
test('trailing restrictivo no mejora resultados frente al umbral estático con mismas secuencias',()=>{
 const est=simularSecuencias(base),dia=simularSecuencias({...base,trailing:'cierre_dia'}),trade=simularSecuencias({...base,trailing:'cierre_trade'});
 assert.ok(est.aprobadas>=dia.aprobadas&&dia.aprobadas>=trade.aprobadas);
 for(const r of [est,dia,trade])assert.equal(r.aprobadas+r.fallidas+r.inconclusas,1000);
});
test('rechaza no finitos, riesgo cero, costos negativos y cómputo excesivo',()=>{
 for(const cambio of [{riesgo:0},{acierto:NaN},{ratio:Infinity},{costo:-1},{tradesDia:0},{iteraciones:10000,maxTrades:2000},{trailing:'live'},{semilla:-1},{tarifa:NaN}])assert.throws(()=>simularSecuencias({...base,...cambio}));
});
test('centavos exactos evitan un trade adicional por deriva binaria y no admiten subcentavos',()=>{
 const r=simularSecuencias({...base,acierto:1,riesgo:.01,objetivo:.1,ratio:1,limiteDiario:0});
 assert.equal(r.tradesMediosAprobadas,10);
 assert.throws(()=>simularSecuencias({...base,riesgo:.005}));
 const redondeada=simularSecuencias({...base,riesgo:.01,ratio:1.5});assert.equal(redondeada.ratioEfectivo,1);
 assert.throws(()=>simularSecuencias({...base,ratio:1e308}));
});
