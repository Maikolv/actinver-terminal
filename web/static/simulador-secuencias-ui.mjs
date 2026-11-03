import {simularSecuencias} from './simulador-secuencias.mjs';
const form=document.getElementById('secuencias-form'),salida=document.getElementById('secuencias-resultado');
const n=k=>Number(form.elements[k].value);
function calcular(e){
  e?.preventDefault();
  try {
    const r=simularSecuencias({acierto:n('acierto')/100,ratio:n('ratio'),riesgo:n('riesgo'),objetivo:n('objetivo'),drawdown:n('drawdown'),limiteDiario:n('limiteDiario'),tradesDia:n('tradesDia'),maxTrades:n('maxTrades'),iteraciones:n('iteraciones'),semilla:n('semilla'),trailing:form.elements.trailing.value,costo:n('costo'),tarifa:form.elements.tarifa.value.trim()===''?null:n('tarifa')});
    const pct=x=>(x*100).toLocaleString('es-MX',{maximumFractionDigits:2})+'%';
    salida.replaceChildren();
    const h=document.createElement('h2');h.textContent='Resultado del modelo hipotético';salida.append(h);
    const filas=[['Aprobación dentro del horizonte',pct(r.probabilidadModelo)],['Intervalo Monte Carlo 95% (Wilson)',r.intervaloMonteCarlo.map(pct).join(' a ')],['Intentos fallidos',String(r.fallidas)],['Sin concluir al agotar el horizonte',String(r.inconclusas)],['Trades medios entre las aprobadas',r.tradesMediosAprobadas?.toFixed(1)??'SIN DATO'],['Ganancia/pérdida efectiva tras redondeo',r.ratioEfectivo.toFixed(4)],['Factor de beneficio teórico, sin costos',r.factorBeneficioTeoricoSinCostos?.toFixed(2)??'Sin pérdidas brutas en el modelo'],['Tarifas/éxito bajo intentos IID completos',r.costoSimplificado?.toFixed(2)??'SIN DATO: tarifa ausente, probabilidad cero o intentos inconclusos']];
    const tabla=document.createElement('table'),cabecera=document.createElement('thead'),titulos=document.createElement('tr'),cuerpo=document.createElement('tbody');
    for(const t of ['Métrica','Valor del modelo']){const th=document.createElement('th');th.scope='col';th.textContent=t;titulos.append(th);}cabecera.append(titulos);
    for(const [k,v] of filas){const tr=document.createElement('tr'),th=document.createElement('th'),td=document.createElement('td');th.scope='row';th.textContent=k;td.textContent=v;tr.append(th,td);cuerpo.append(tr);}tabla.append(cabecera,cuerpo);salida.append(tabla);
    const p=document.createElement('p');p.className='aviso-caja';p.textContent=r.nota+' El intervalo mide variación de simulación condicionada al modelo, no incertidumbre del mercado. El costo simplificado omite suscripciones, renovaciones e impuestos.';salida.append(p);
  } catch(error){salida.textContent=error.message;}
}
form.addEventListener('submit',calcular);
calcular();
