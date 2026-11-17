// Modelo propio de secuencias hipotéticas: no consulta datos ni envía órdenes.
export function simularSecuencias(c) {
  const {acierto,ratio,riesgo,objetivo,drawdown,limiteDiario,tradesDia,maxTrades,iteraciones,semilla,trailing,tarifa=null,costo=0}=c;
  for(const [k,v] of Object.entries({acierto,ratio,riesgo,objetivo,drawdown,limiteDiario,tradesDia,maxTrades,iteraciones,semilla,costo}))
    if(typeof v!=='number'||!Number.isFinite(v))throw new Error(`Valor no finito: ${k}`);
  if(acierto<0||acierto>1||ratio<=0||riesgo<=0||objetivo<=0||drawdown<=0||limiteDiario<0||costo<0)
    throw new Error('Probabilidad entre 0 y 1; importes y ratio positivos; costo y límite diario no negativos.');
  if(![tradesDia,maxTrades,iteraciones,semilla].every(Number.isInteger)||tradesDia<1||maxTrades<1||iteraciones<1||iteraciones>20000||semilla<0||semilla>4294967295)
    throw new Error('Días, horizonte, iteraciones y semilla requieren enteros válidos.');
  if(iteraciones*maxTrades>5000000)throw new Error('Reduzca iteraciones u horizonte: presupuesto máximo de cinco millones de pasos.');
  if(!['estatico','cierre_trade','cierre_dia'].includes(trailing))throw new Error('Modelo de drawdown no reconocido.');
  if(tarifa!==null&&(typeof tarifa!=='number'||!Number.isFinite(tarifa)||tarifa<0))throw new Error('Tarifa inválida.');
  const centavos=v=>{const c=Math.round(v*100);if(v>1e9||Math.abs(v*100-c)>1e-5||(v!==0&&c===0))throw new Error('Use importes en USD con hasta dos decimales y máximo mil millones.');return c;};
  const riesgoC=centavos(riesgo),objetivoC=centavos(objetivo),drawdownC=centavos(drawdown),diarioC=centavos(limiteDiario),costoC=centavos(costo);
  if(tarifa!==null)centavos(tarifa);
  const gananciaC=Math.floor(riesgoC*ratio+1e-7),ratioEfectivo=gananciaC/riesgoC;
  if(!Number.isSafeInteger((gananciaC+riesgoC+costoC)*maxTrades))throw new Error('Los importes exceden la precisión numérica del modelo.');
  let estado=semilla>>>0;
  const uniforme=()=>{estado=(estado+0x6D2B79F5)>>>0;let t=estado;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};
  let aprobadas=0,fallidas=0,inconclusas=0,tradesAprobadas=0;
  for(let intento=0;intento<iteraciones;intento++) {
    // La misma semilla reproduce cada intento aunque otro modelo termine antes.
    estado=(semilla+Math.imul(intento,0x9E3779B9))>>>0;
    let capital=0,pico=0,inicioDia=0,terminada=false;
    for(let t=0;t<maxTrades;t++) {
      if(t%tradesDia===0)inicioDia=capital;
      capital+=(uniforme()<acierto?gananciaC:-riesgoC)-costoC;
      // El umbral se comprueba en cada cierre modelado. No conocemos el trayecto intratrade.
      if((diarioC>0&&capital-inicioDia<=-diarioC)||capital<=pico-drawdownC) {fallidas++;terminada=true;break;}
      if(capital>=objetivoC) {aprobadas++;tradesAprobadas+=t+1;terminada=true;break;}
      if(trailing==='cierre_trade'||(trailing==='cierre_dia'&&(t+1)%tradesDia===0))pico=Math.max(pico,capital);
    }
    if(!terminada)inconclusas++;
  }
  const p=aprobadas/iteraciones,z2=1.96**2,den=1+z2/iteraciones;
  const centro=(p+z2/(2*iteraciones))/den;
  const mitad=1.96*Math.sqrt(p*(1-p)/iteraciones+z2/(4*iteraciones**2))/den;
  return {iteraciones,aprobadas,fallidas,inconclusas,probabilidadModelo:p,
    intervaloMonteCarlo:[Math.max(0,centro-mitad),Math.min(1,centro+mitad)],
    tradesMediosAprobadas:aprobadas?tradesAprobadas/aprobadas:null,
    ratioEfectivo,factorBeneficioTeoricoSinCostos:acierto<1?acierto*ratioEfectivo/(1-acierto):null,
    costoSimplificado:tarifa!==null&&p>0&&inconclusas===0&&Number.isFinite(tarifa/p)?tarifa/p:null,
    nota:'Modelo IID binario de cierres con riesgo fijo. Aritmética en centavos; ganancias redondeadas hacia abajo. No modela P&L intratrade, slippage variable, dependencia temporal, reglas completas ni retiros. No predice la aprobación real ni demuestra alfa.'};
}
