try{
  const r=await fetch('jpm/resultado_sintetico.json');if(!r.ok)throw Error();const d=await r.json();
  if(d.tipo_dato!=='sintetico'||![d.rendimiento_tramo,d.caida_maxima,d.volatilidad_entre_observaciones].every(Number.isFinite))throw Error();
  const pct=x=>(100*x).toFixed(2)+'%';
  document.getElementById('resultado').textContent=`DATOS SINTÉTICOS · ${d.observaciones} observaciones\nRetorno del tramo: ${pct(d.rendimiento_tramo)}\nCaída máxima: ${pct(d.caida_maxima)}\nVolatilidad entre observaciones: ${pct(d.volatilidad_entre_observaciones)} (no anualizada)\nFuente: ${d.fuente}\n${d.nota}`;
}catch{document.getElementById('resultado').textContent='SIN DATO · ejemplo local no disponible; no se consulta ningún proveedor.';}
