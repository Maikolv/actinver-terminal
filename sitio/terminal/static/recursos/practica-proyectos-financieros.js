
'use strict';
const Finanzas = (() => {
  const finito = (x,n) => {if(!Number.isFinite(x)) throw new Error(`${n}: introduce un número finito.`);};
  function validarDCF(f,g,r,t){[f,g,r,t].forEach((x,i)=>finito(x,['FCFF','Crecimiento','Descuento','Terminal'][i]));if(f<=0)throw new Error('FCFF base debe ser positivo.');if(g<=-1||t<=-1||r<=-1)throw new Error('Las tasas deben ser mayores que −100%.');if(r<=t)throw new Error('La tasa de descuento debe ser mayor que el crecimiento terminal.');}
  function dcf(f,g,r,t){validarDCF(f,g,r,t);let pv=0,flujo=f;for(let año=1;año<=5;año++){flujo*=1+g;pv+=flujo/(1+r)**año;}const terminal=flujo*(1+t)/(r-t)/(1+r)**5;const ev=pv+terminal;if(!Number.isFinite(ev)||!Number.isFinite(terminal))throw new Error('Los supuestos producen un valor fuera del rango numérico.');return {ev,flujos:pv,terminal};}
  function reverse(f,r,t,objetivo){validarDCF(f,0,r,t);finito(objetivo,'EV objetivo');if(objetivo<=0)throw new Error('EV objetivo debe ser positivo.');let a=-0.9,b=2,va=dcf(f,a,r,t).ev,vb=dcf(f,b,r,t).ev;if(objetivo<va||objetivo>vb)return {enRango:false,minimo:va,maximo:vb};if(objetivo===va)return {enRango:true,crecimiento:a};if(objetivo===vb)return {enRango:true,crecimiento:b};for(let i=0;i<120;i++){let m=(a+b)/2;if(dcf(f,m,r,t).ev<objetivo)a=m;else b=m;}return {enRango:true,crecimiento:(a+b)/2};}
  function parsear(texto){const s=texto.trim();if(!s)throw new Error('Introduce al menos tres cierres.');if(s.includes(','))throw new Error('Usa punto decimal y separa los cierres con espacios, punto y coma o saltos de línea; no uses comas.');const p=s.split(/[\s;]+/).map(x=>{if(!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(x))throw new Error('Hay un cierre con formato inválido.');return Number(x);});return p;}
  function volatilidad(precios,sesiones=252,lambda=0.94){if(!Array.isArray(precios)||precios.length<3)throw new Error('Introduce al menos tres cierres.');if(precios.length>20000)throw new Error('El ejercicio admite hasta 20 000 cierres.');precios.forEach(p=>{if(!Number.isFinite(p)||p<=0)throw new Error('Todos los cierres deben ser positivos y finitos.');});if(!Number.isInteger(sesiones)||sesiones<1||sesiones>10000)throw new Error('Sesiones debe ser un entero entre 1 y 10 000.');if(!Number.isFinite(lambda)||lambda<0||lambda>=1)throw new Error('Lambda debe estar entre 0 (incluido) y 1 (excluido).');const ret=precios.slice(1).map((p,i)=>Math.log(p)-Math.log(precios[i]));const media=ret.reduce((a,b)=>a+b,0)/ret.length;const v=ret.reduce((s,x)=>s+(x-media)**2,0)/(ret.length-1);let ewma=ret[0]**2;for(let i=1;i<ret.length;i++)ewma=lambda*ewma+(1-lambda)*ret[i]**2;return {n:ret.length,media,muestral:Math.sqrt(v*sesiones),ewma:Math.sqrt(ewma*sesiones)};}
  return {dcf,reverse,parsear,volatilidad};
})();

// FIN_MATEMATICAS_INICIO_UI

const $=id=>document.getElementById(id), numero=id=>{const v=$(id).value.trim();if(!v)throw new Error('Completa todos los campos numéricos.');const x=Number(v);if(!Number.isFinite(x))throw new Error('Introduce números finitos.');return x;};
const fmt=x=>new Intl.NumberFormat('es-MX',{maximumFractionDigits:2}).format(x),pct=x=>`${fmt(x*100)}%`;
function mostrar(id,texto,error=false){$(id).textContent=texto;$(id).classList.toggle('error',error);}
$('dcf-form').addEventListener('submit',e=>{e.preventDefault();try{const f=numero('fcf'),g=numero('crecimiento')/100,r=numero('descuento')/100,t=numero('terminal')/100,o=numero('objetivo');const d=Finanzas.dcf(f,g,r,t),rev=Finanzas.reverse(f,r,t,o);mostrar('dcf-resultado',`EV estimado: ${fmt(d.ev)} unidades monetarias\nValor presente de los cinco flujos: ${fmt(d.flujos)}\nValor presente terminal: ${fmt(d.terminal)} (${pct(d.terminal/d.ev)} del EV)\n${rev.enRango?`Crecimiento anual implícito en el EV objetivo: ${pct(rev.crecimiento)}`:`Sin solución en el rango de crecimiento −90% a +200%. En este modelo, el EV en los extremos es ${fmt(rev.minimo)} y ${fmt(rev.maximo)}.`}\nResultado hipotético; no corresponde a precio por acción.`);}catch(err){mostrar('dcf-resultado',err.message,true);}});
$('vol-form').addEventListener('submit',e=>{e.preventDefault();try{const v=Finanzas.volatilidad(Finanzas.parsear($('cierres').value),numero('sesiones'),numero('lambda'));mostrar('vol-resultado',`${v.n} log-retornos\nDesviación muestral anualizada: ${pct(v.muestral)}\nVolatilidad EWMA anualizada, último estado: ${pct(v.ewma)}\nMedia de log-retornos por sesión: ${pct(v.media)}\nNo es una señal ni un rendimiento esperado.`);}catch(err){mostrar('vol-resultado',err.message,true);}});

// Opciones precargadas: cualquiera puede llenar el cuaderno eligiendo en vez de escribir. Todo es hipotético y sintético.
const PRECARGAS={
  empresa:['Empresa madura de consumo básico (hipotética)','Banco mexicano (hipotético)','Fabricante de semiconductores (hipotético)','Cadena de autoservicio en México (hipotética)','Fibra inmobiliaria industrial (hipotética)','Minera de cobre y plata (hipotética)'],
  'tesis-texto':['Creo que las ventas crecerán más que el sector porque la demanda de su producto aumenta y tiene capacidad para atenderla. El mecanismo sería: más volumen con costos fijos estables → mayor margen operativo.','Creo que el margen operativo mejorará porque está bajando costos (eficiencias, mejores compras). El mecanismo sería: igual venta con menor costo → más utilidad por peso vendido.','Creo que el precio descuenta un crecimiento menor al probable porque el mercado castigó al sector entero. El mecanismo sería: si los resultados confirman el crecimiento, el múltiplo se normaliza.','Creo que el nearshoring aumentará la demanda de sus servicios en México porque llegan nuevas plantas al país. El mecanismo sería: más contratos de largo plazo → ingresos más estables.','Creo que bajar su deuda reducirá el riesgo y el costo de financiamiento. El mecanismo sería: menos intereses → más flujo libre para el accionista.','Creo que un ciclo de tasas a la baja favorecerá a la empresa porque su demanda depende del crédito. El mecanismo sería: crédito más barato → más ventas.'],
  contra:['Mi tesis dejaría de sostenerse si las ventas de los próximos dos trimestres crecen menos que el sector.','Mi tesis dejaría de sostenerse si el margen operativo cae dos trimestres seguidos.','Mi tesis dejaría de sostenerse si la deuda neta sube por encima de 3 veces el EBITDA.','Mi tesis dejaría de sostenerse si Banxico sube la tasa objetivo y encarece el financiamiento.','Mi tesis dejaría de sostenerse si el crecimiento implícito en el precio (DCF inverso, sección 02) ya supera lo que espero.','Mi tesis dejaría de sostenerse si un competidor gana participación de mercado de forma sostenida.'],
  fuentes:['Reporte trimestral en BMV o SEC · fecha de publicación · respalda ventas y márgenes · próxima revisión: siguiente reporte.','Informe anual (o 10-K) · fecha · respalda deuda, segmentos y riesgos · próxima revisión: siguiente informe anual.','Banxico: tasa objetivo y tipo de cambio FIX · fecha · respalda el costo de financiamiento · próxima revisión: siguiente decisión de política monetaria.','INEGI: consumo, producción industrial o inflación · fecha · respalda la demanda · próxima revisión: siguiente publicación mensual.','Presentación a inversionistas · fecha · respalda la guía de la empresa · próxima revisión: siguiente llamada de resultados.','SEC Form 4 (compras y ventas de directivos) · fecha · respalda la confianza interna · próxima revisión: consultar en Movimientos públicos.'],
  cierres:[['Acción tranquila (sintética)','100 100.4 99.9 100.6 100.2 100.9 100.5 101.1 100.8 101.3'],['Acción volátil (sintética)','100 104 97 103 95 101 108 99 106 98'],['Tendencia con sobresaltos (sintética)','100 102 101 104 103 99 105 107 106 110']],
  sesiones:[['252 · acciones (sesiones al año)','252'],['52 · datos semanales','52'],['12 · datos mensuales','12']],
  lambda:[['0.94 · estándar para datos diarios (RiskMetrics)','0.94'],['0.97 · estándar para datos mensuales','0.97'],['0.90 · reacciona más rápido','0.9']]
};
const ESCENARIOS={
  'escenario-dcf':{campos:['fcf','crecimiento','descuento','terminal','objetivo'],form:'dcf-form',opciones:[
    ['Empresa madura: crece poco y es estable',[100,3,9,2,1500]],['Empresa en crecimiento: crece rápido, más riesgo',[100,12,11,3,2500]],['Empresa defensiva: crecimiento casi nulo',[100,1,8,1,1300]]]},
  'escenario-vol':{campos:['cierres','sesiones','lambda'],form:'vol-form',opciones:PRECARGAS.cierres.map(([n,c])=>[n,[c,252,0.94]])}
};
for(const [id,lista] of Object.entries(PRECARGAS)){
  const campo=$(id),sel=document.createElement('select');
  sel.className='precarga';sel.setAttribute('aria-label',`Opciones precargadas para ${campo.closest('label').firstChild.textContent.trim()}`);
  sel.append(new Option('Elegir una opción precargada…',''));
  for(const x of lista){const [texto,valor]=Array.isArray(x)?x:[x,x];sel.append(new Option(texto,valor));}
  sel.addEventListener('change',()=>{if(!sel.value)return;const agregar=campo.tagName==='TEXTAREA'&&id!=='cierres'&&campo.value.trim();campo.value=agregar?`${campo.value.trim()}\n${sel.value}`:sel.value;sel.value='';campo.dispatchEvent(new Event('input',{bubbles:true}));});
  campo.after(sel);
}
for(const [id,e] of Object.entries(ESCENARIOS)){
  const sel=$(id);
  e.opciones.forEach(([n],i)=>sel.append(new Option(n,String(i))));sel.append(new Option('Personalizado (escribe tus valores)','propio'));
  const aplicar=()=>{const o=e.opciones[Number(sel.value)];if(!o)return;e.campos.forEach((c,i)=>{$(c).value=o[1][i];});$(e.form).requestSubmit();};
  sel.addEventListener('change',aplicar);
  $(e.form).addEventListener('input',ev=>{if(ev.target!==sel)sel.value='propio';});
  aplicar();
}
if(!$('fecha').value)$('fecha').value=new Date().toLocaleDateString('en-CA');

// 04 · Python aplicado: ejemplo sintético precalculado con la función Python del proyecto (sin proveedores).
fetch('jpm/resultado_sintetico.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{
  if(d.tipo_dato!=='sintetico'||![d.rendimiento_tramo,d.caida_maxima,d.volatilidad_entre_observaciones].every(Number.isFinite))throw Error();
  mostrar('python-resultado',`DATOS SINTÉTICOS · ${d.observaciones} observaciones
Retorno del tramo: ${pct(d.rendimiento_tramo)}
Caída máxima: ${pct(d.caida_maxima)}
Volatilidad entre observaciones: ${pct(d.volatilidad_entre_observaciones)} (no anualizada)
Fuente: ${d.fuente}
${d.nota}`);
}).catch(()=>mostrar('python-resultado','SIN DATO · ejemplo local no disponible; no se consulta ningún proveedor.',true));
