// Independent implementation inspired by ErTasselli/OpenTerminal (MIT).
export const CATALOGO = [
  ['grafica','Gráfica TradingView','chart'], ['mapa','Mapa sectorial','mapa'],
  ['calendario','Calendario económico','calendario'], ['noticias','Noticias','noticias'],
  ['filtro','Explorador de acciones','filtro'], ['resumen','Macro e índices','resumen'],
  ['cotizaciones','Cotizaciones por grupo','cotizaciones'], ['destacados','Mayores movimientos','destacados'],
  ['mapa-etf','Mapa de ETF','mapa-etf'], ['divisas','Divisas','divisas'],
  ['mapa-cripto','Cripto · fuera del Reto','mapa-cripto'], ['info','Ficha de cotización','info'],
  ['perfil','Perfil de empresa','perfil'], ['finanzas','Fundamentales','finanzas'],
  ['tecnico','Resumen técnico externo','tecnico'], ['noticias-emisora','Noticias del instrumento','noticias-emisora'],
  ['opciones','Cadena, GEX y gamma','link','tab-optionflow'],
  ['orderflow','Libro, delta y perfil','link','tab-orderflow'],
  ['cartera','Cartera y rendimiento','link','tab-cartera'],
  ['asistente','Asistente de investigación','link','tab-asistente'],
  ['insiders','Movimientos públicos','link','tab-movimientos'],
  ['robustez','Backtesting y robustez','link','tab-robustez'],
  ['riesgo','Plan de riesgo · solo NQ · cálculo manual','risk'],
];
export const PRESETS = {mercado:['grafica','mapa','resumen','calendario'],
  futuros:['grafica','calendario','orderflow','opciones','riesgo','robustez'],
  empresa:['grafica','info','finanzas','noticias-emisora','insiders','cartera']};
export const AVISO_RIESGO = 'El riesgo calculado es un tope del escenario, no del fill real: un gap o un deslizamiento mayor puede superarlo.';
export function rutaVelas(simbolo){return '/?'+new URLSearchParams({vista:'tab-velas',simbolo});}
export function normalizarLayout(v) {
  if(!Array.isArray(v))return [...PRESETS.mercado];
  return [...new Set(v.filter(k=>CATALOGO.some(c=>c[0]===k)))].slice(0,CATALOGO.length);
}
// Escenarios listos para que cualquiera vea un resultado sin saber qué escribir. Precios de estudio, no de mercado;
// la comisión es una estimación (no una tarifa verificada). El primero es el valor inicial del formulario.
export const ESCENARIOS_NQ = [
  {id:'basico',nombre:'Largo básico: arriesgar 10 puntos para buscar 20',valores:{entrada:20000,sl:19990,r:2,presupuesto:500,costos:5,slip:1}},
  {id:'conservador',nombre:'Conservador: stop corto de 5 puntos, objetivo 3 a 1',valores:{entrada:20000,sl:19995,r:3,presupuesto:300,costos:5,slip:1}},
  {id:'corto',nombre:'Corto: arriesgar 15 puntos para buscar 22.5',valores:{entrada:20000,sl:20015,r:1.5,presupuesto:1000,costos:5,slip:2}},
];
export function lecturaSencilla(p) {
  const total=(x)=>(x*p.contratos).toFixed(2);
  return p.contratos===0
    ? `En palabras simples: con ese riesgo máximo no alcanza ni para un contrato; cada contrato arriesga USD ${p.riesgo.toFixed(2)}.`
    : `En palabras simples: con ${p.contratos} contrato${p.contratos===1?'':'s'}, si el precio toca el stop perdería cerca de USD ${total(p.riesgo)}; si llega al objetivo ganaría cerca de USD ${total(p.recompensaNeta)}.`;
}
export function planNQ(entrada,stop,r,presupuesto,costos=0,deslizamiento=0) {
  const valores=[entrada,stop,r,presupuesto,costos,deslizamiento].map(Number);
  [entrada,stop,r,presupuesto,costos,deslizamiento]=valores;
  if(!valores.every(Number.isFinite)||entrada<=0||stop<=0||r<=0||presupuesto<=0||costos<0||deslizamiento<0||entrada===stop)
    throw new Error('Use precios positivos distintos, R y presupuesto positivos, y costos no negativos.');
  if(entrada>1e9||stop>1e9||r>1000||presupuesto>1e9||costos>1e6||!Number.isInteger(deslizamiento)||deslizamiento>1e6)
    throw new Error('Escenario fuera de los límites de la calculadora; el deslizamiento debe ser un número entero de ticks.');
  if(![entrada,stop].every(x=>Math.abs(x*4-Math.round(x*4))<1e-8))throw new Error('NQ requiere múltiplos de 0.25 puntos.');
  const riesgo=Math.abs(entrada-stop)*20+Number(costos)+Number(deslizamiento)*5;
  const direccion=entrada>stop?1:-1;
  const tp=entrada+direccion*Math.floor(Math.abs(entrada-stop)*r*4+1e-8)/4;
  if(!Number.isFinite(tp)||!Number.isFinite(riesgo)||!Number.isSafeInteger(Math.floor(presupuesto/riesgo))||tp<=0||tp===entrada)throw new Error('El objetivo o presupuesto calculado no es válido.');
  return {lado:direccion===1?'Largo':'Corto',tp,sl:stop,riesgo,contratos:Math.floor(presupuesto/riesgo),
    recompensaNeta:Math.abs(tp-entrada)*20-Number(costos)-Number(deslizamiento)*5};
}
if(typeof document!=='undefined') {
  const KEY='actinver.mesa.v1', $=id=>document.getElementById(id);
  let activos=[...PRESETS.mercado],simbolo='SIC:NVDA',catalogoListo=false,catalogo=[];
  const crear=(tag,texto)=>{const n=document.createElement(tag);if(texto!==undefined)n.textContent=texto;return n;};
  try {const s=JSON.parse(localStorage.getItem(KEY));if(s){activos=normalizarLayout(s.widgets);if(typeof s.simbolo==='string'&&s.simbolo.length<50)simbolo=s.simbolo;}}catch{}
  const guardada=new Option('Personalizada / guardada','guardada');guardada.disabled=true;$('mesa-preset').prepend(guardada);$('mesa-preset').value='guardada';
  function guardar(){try{localStorage.setItem(KEY,JSON.stringify({widgets:activos,simbolo}));}catch{$('mesa-estado').textContent='Su navegador no permite guardar la disposición.';}}
  function mover(id,delta){const i=activos.indexOf(id),j=i+delta;if(j<0||j>=activos.length)return;[activos[i],activos[j]]=[activos[j],activos[i]];$('mesa-preset').value='guardada';guardar();dibujar();}
  function boton(t,fn){const b=crear('button',t);b.type='button';b.className='boton boton--secundario';b.onclick=fn;return b;}
  function panelRiesgo(box){
    box.append(crear('p','Ejercicio manual, sin precio conectado ni señal. NQ: USD 20/punto, tick 0.25 = USD 5. No envía mensajes ni órdenes.'));
    const form=crear('form');const campos={};
    const lista=crear('label','Escenario listo ');const sel=crear('select');
    for(const e of ESCENARIOS_NQ)sel.append(new Option(e.nombre,e.id));
    sel.append(new Option('Personalizado (escriba sus valores)','propio'));lista.append(sel);form.append(lista);
    const inicial=ESCENARIOS_NQ[0].valores;
    for(const [key,label,step] of [['entrada','Precio de entrada (estudio)',.25],['sl','Stop: precio donde la idea deja de valer',.25],['r','Objetivo: cuántas veces el riesgo (R)','any'],['presupuesto','Lo máximo que acepta perder, USD',1],['costos','Comisión estimada ida y vuelta, USD',.01],['slip','Deslizamiento en ticks (precio peor al esperado)',1]]) {
      const l=crear('label',label+' '),n=crear('input');n.type='number';n.value=inicial[key];n.step=step;n.required=true;campos[key]=n;l.append(n);form.append(l);
    }
    const output=crear('p'),simple=crear('p');output.setAttribute('role','status');const b=crear('button','Calcular escenario');b.type='submit';b.className='boton';form.append(b);
    const calcular=()=>{try{const p=planNQ(...['entrada','sl','r','presupuesto','costos','slip'].map(k=>Number(campos[k].value)));simple.textContent=lecturaSencilla(p);output.textContent=`ESTUDIO · ${p.lado} · TP ${p.tp.toFixed(2)} · SL ${p.sl.toFixed(2)} · riesgo por contrato USD ${p.riesgo.toFixed(2)} · recompensa neta USD ${p.recompensaNeta.toFixed(2)} · caben ${p.contratos} contratos en el presupuesto. La comisión es una hipótesis, no una tarifa verificada. ${AVISO_RIESGO}`;}catch(err){simple.textContent='';output.textContent=err.message;}};
    sel.addEventListener('change',()=>{const e=ESCENARIOS_NQ.find(x=>x.id===sel.value);if(!e)return;for(const k in e.valores)campos[k].value=e.valores[k];calcular();});
    form.addEventListener('input',ev=>{if(ev.target===sel)return;sel.value='propio';simple.textContent='';output.textContent='Escenario cambiado. Vuelva a calcular.';});
    form.onsubmit=e=>{e.preventDefault();calcular();};
    box.append(form,simple,output);calcular();
  }
  function dibujar(){
    const anteriores=new Map([...$('mesa-paneles').children].map(n=>[n.dataset.panel,n]));
    const abiertos=new Set([...anteriores].filter(([,n])=>n.querySelector('details')?.open).map(([id])=>id));
    const tema=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
    for(const id of activos){
      const anterior=anteriores.get(id);
      if(anterior&&anterior.dataset.simbolo===simbolo&&anterior.dataset.tema===tema&&anterior.dataset.catalogo===String(catalogoListo)){
        const cont=$('mesa-paneles'),destino=cont.children[activos.indexOf(id)]||null;
        if(destino!==anterior){if(cont.moveBefore)cont.moveBefore(anterior,destino);else cont.insertBefore(anterior,destino);}
        const flechas=anterior.querySelectorAll('header button');flechas[0].disabled=activos.indexOf(id)===0;flechas[1].disabled=activos.indexOf(id)===activos.length-1;
        anteriores.delete(id);continue;
      }
      const [,titulo,tipo,destino]=CATALOGO.find(c=>c[0]===id),card=crear('section');card.className='tarjeta mesa-panel';
      card.dataset.panel=id;card.dataset.simbolo=simbolo;card.dataset.tema=tema;card.dataset.catalogo=String(catalogoListo);
      const head=crear('header'),h=crear('h2',titulo);h.tabIndex=-1;
      const antes=boton('←',()=>{mover(id,-1);document.querySelector(`[data-panel="${id}"] h2`)?.focus();}),despues=boton('→',()=>{mover(id,1);document.querySelector(`[data-panel="${id}"] h2`)?.focus();});
      antes.setAttribute('aria-label',`Mover ${titulo} antes`);despues.setAttribute('aria-label',`Mover ${titulo} después`);
      antes.disabled=activos.indexOf(id)===0;despues.disabled=activos.indexOf(id)===activos.length-1;
      head.append(h,antes,despues,boton('Quitar',()=>{activos=activos.filter(x=>x!==id);$('mesa-preset').value='guardada';guardar();dibujar();$('mesa-agregar').focus();}));card.append(head);
      if(tipo==='chart'){const local=crear('a','Abrir Velas de la terminal');local.href=rutaVelas(simbolo);card.append(local);}
      if(tipo==='link'){const a=crear('a','Abrir '+titulo);a.href='/?'+new URLSearchParams({vista:destino,simbolo});a.className='boton';card.append(crear('p','Abra el análisis completo con sus fuentes, fecha y límites de datos.'),a);}
      else if(tipo==='risk')panelRiesgo(card);
      else if(['chart','info','perfil','finanzas','tecnico','noticias-emisora'].includes(tipo)&&(!catalogoListo||!catalogo.find(i=>i.id===simbolo)?.grafica)) {
        card.append(crear('p',!catalogoListo?'SIN DATO · catálogo no disponible. No se presupone un instrumento.':'SIN DATO · este instrumento no tiene gráfica externa declarada en el catálogo. Consulte Datos y fuentes.'));
        if(tipo!=='chart'){const a=crear('a','Consultar el instrumento en Velas');a.href=rutaVelas(simbolo);card.append(a);}
      }
      else {const d=crear('details'),s=crear('summary','Mostrar panel');d.append(s,crear('p','Referencia externa de TradingView; retraso y disponibilidad propios. No alimenta los cálculos de la terminal. HTTP 200 solo confirma que se sirve el marco: la terminal no puede verificar los datos de otro origen.'));
        const aviso=crear('p');aviso.setAttribute('role','status');d.append(aviso);
        const alternativa=crear('a','Alternativa local: '+(tipo==='chart'?'Velas':'Datos y fuentes'));alternativa.href=tipo==='chart'?rutaVelas(simbolo):'/?'+new URLSearchParams({vista:'tab-universo',simbolo});d.append(alternativa);
        let control;
        d.addEventListener('toggle',async()=>{
          if(!d.open){control?.abort();control=null;d.querySelector('iframe')?.remove();aviso.textContent='';return;}
          if(d.querySelector('iframe')||control)return;
          const actual=new AbortController();control=actual;aviso.textContent='Comprobando disponibilidad del marco…';
          const ruta=tipo==='chart'?`/grafica/${encodeURIComponent(simbolo)}?tema=${tema}`:`/widget/${tipo}?${new URLSearchParams({simbolo,tema})}`;
          try{const r=await fetch(ruta,{signal:AbortSignal.any([actual.signal,AbortSignal.timeout(15000)])});
            if(!d.open||!card.isConnected||actual.signal.aborted)return;
            if(!r.ok){aviso.textContent=`SIN DATO · el servidor no ofrece este panel (HTTP ${r.status}). Use la alternativa local.`;return;}
            if(!r.headers.get('content-type')?.includes('text/html')){aviso.textContent='SIN DATO · la respuesta no es un panel HTML.';return;}
            const f=crear('iframe');f.title=titulo;f.loading='lazy';
            // Sin allow-same-origin, la gráfica falla al consultar cookies/Locks API.
            // Solo calendario tiene contenido visible comprobado con este sandbox.
            if(tipo==='calendario')f.setAttribute('sandbox','allow-scripts allow-popups allow-popups-to-escape-sandbox');
            f.referrerPolicy='no-referrer';f.src=ruta;d.append(f);aviso.textContent='Marco disponible; datos y vigencia externos sin verificar.';
          }catch{if(d.open&&card.isConnected&&!actual.signal.aborted)aviso.textContent='SIN DATO · no se pudo consultar el panel. Use la alternativa local.';}
          finally{if(control===actual)control=null;}
        });card.append(d);if(abiertos.has(id))d.open=true;}
      $('mesa-paneles').append(card);
    }
    for(const n of anteriores.values()){const d=n.querySelector('details');if(d)d.open=false;n.remove();}
    $('mesa-conteo').textContent=`${activos.length} paneles · se cargan al desplegarlos`;
  }
  for(const [id,t] of CATALOGO)$('mesa-agregar').append(new Option(t,id));
  $('mesa-anadir').onclick=()=>{const id=$('mesa-agregar').value;if(!activos.includes(id)){activos.push(id);$('mesa-preset').value='guardada';guardar();dibujar();}else{$('mesa-estado').textContent='Ese panel ya está en la mesa.';}};
  $('mesa-preset').onchange=e=>{activos=[...PRESETS[e.target.value]];guardar();dibujar();};
  $('mesa-simbolo').onchange=e=>{simbolo=e.target.value;guardar();dibujar();};
  function filtrar(){const texto=$('mesa-buscar').value.trim().toLocaleLowerCase('es');const filas=catalogo.filter(i=>`${i.clave_operable} ${i.nombre}`.toLocaleLowerCase('es').includes(texto));$('mesa-simbolo').replaceChildren(...filas.map(i=>new Option(`${i.clave_operable} · ${i.nombre}`,i.id)));$('mesa-simbolo').value=simbolo;if(!filas.length)$('mesa-simbolo').append(new Option('Sin coincidencias',''));$('mesa-estado').textContent=`${filas.length} coincidencias; el instrumento activo no cambia hasta seleccionarlo.`;}
  $('mesa-buscar').addEventListener('input',filtrar);
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('mesa-buscar').focus();}if(e.key==='Escape'&&e.target===$('mesa-buscar')){$('mesa-buscar').value='';filtrar();$('mesa-simbolo').focus();}});
  (async()=>{try{const r=await fetch('/api/universo?solo_catalogo=true',{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error();const u=await r.json();const filas=u.instrumentos.filter(i=>i.estado==='activo');catalogo=filas;catalogoListo=filas.length>0;$('mesa-simbolo').replaceChildren(...filas.map(i=>new Option(`${i.clave_operable} · ${i.nombre}`,i.id)));if(!filas.some(i=>i.id===simbolo))simbolo=filas[0]?.id||'';if(!filas.length)$('mesa-simbolo').append(new Option('Catálogo vacío',''));$('mesa-simbolo').value=simbolo;$('mesa-simbolo').disabled=!simbolo;$('mesa-estado').textContent=filas.length?'Catálogo local cargado. Los widgets externos pueden no cubrir todos los instrumentos.':'SIN DATO · catálogo vacío. Los escenarios manuales siguen disponibles.';dibujar();}catch{simbolo='';catalogoListo=false;$('mesa-simbolo').replaceChildren(new Option('Catálogo no disponible',''));$('mesa-simbolo').disabled=true;$('mesa-estado').textContent='No se pudo consultar el catálogo. Vuelva a abrir esta mesa con la terminal en ejecución.';dibujar();}})();
  dibujar();
}
