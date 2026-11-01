export function destinoLocal(valor, origen) {
  if (typeof valor !== 'string' || !valor.startsWith('/') || valor.startsWith('//')) throw new Error('Destino no local');
  const url=new URL(valor,origen);
  if(url.origin!==origen)throw new Error('Destino no local');
  return url;
}

if(typeof document!=='undefined') {
  const nav=document.querySelector('.nav-global');
  const selector=document.getElementById('destino-global');
  // Reloj de plazas y cinta de indicadores macro (TradingView, con su retraso): la misma barra en todas las áreas.
  const reloj=document.createElement('span');reloj.className='nav-global__reloj';reloj.setAttribute('aria-label','Hora en Ciudad de México, Nueva York y Londres');
  const plazas=[['CDMX','America/Mexico_City'],['NY','America/New_York'],['LDN','Europe/London']];
  const marcar=()=>reloj.replaceChildren(...plazas.flatMap(([n,z],i)=>{const b=document.createElement('b');b.textContent=n;
    return [...(i?[' · ']:[]),b,' '+new Date().toLocaleTimeString('es-MX',{timeZone:z,hour:'2-digit',minute:'2-digit',hour12:false})];}));
  marcar();setInterval(marcar,30000);
  nav.querySelector('.nav-global__interior')?.append(reloj);
  const cinta=document.createElement('iframe');cinta.className='cinta-global';cinta.loading='lazy';
  cinta.title='Cinta de indicadores: índices, VIX, bono a 10 años, dólar, oro y petróleo (TradingView, con retraso)';
  cinta.src='/widget/cinta-macro?tema=dark';
  nav.after(cinta);
  // Ningún widget cortado: los marcos /widget y /grafica son del mismo origen, así que se mide su contenido real y el
  // marco crece hasta mostrarlo completo (nunca baja de su alto configurado). El contenido de TradingView vive en un
  // iframe interno de otro origen: aquí solo se ajusta el contenedor.
  const ajustar=(f)=>{
    const doc=f.contentDocument;if(!doc?.documentElement)return;
    // Se compara con el alto INTERIOR (clientHeight): el borde del marco no cuenta, así no hay bucle de crecimiento.
    const minimo=Number(f.dataset.altoMin||(f.dataset.altoMin=String(f.clientHeight||0)));
    const medir=()=>{const contenido=Math.max(doc.documentElement.scrollHeight,doc.body?.scrollHeight||0);
      if(contenido>f.clientHeight&&contenido>minimo){const borde=f.offsetHeight-f.clientHeight;f.style.height=`${Math.min(2000,Math.ceil(contenido+borde))}px`;}};  // tope: nunca crece sin límite
    medir();try{new ResizeObserver(medir).observe(doc.documentElement);if(doc.body)new ResizeObserver(medir).observe(doc.body);}catch{/* sin ResizeObserver: queda el alto medido */}
    doc.querySelectorAll('iframe').forEach(i=>new ResizeObserver(medir).observe(i));
    new MutationObserver(()=>{doc.querySelectorAll('iframe').forEach(i=>{if(!i.dataset.observado){i.dataset.observado='1';new ResizeObserver(medir).observe(i);}});medir();}).observe(doc.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['style','height']});
  };
  const vigilar=(f)=>{if(f.dataset.ajuste||!/^\/(widget|grafica)\//.test(new URL(f.src||'about:blank',location.href).pathname))return;f.dataset.ajuste='1';f.addEventListener('load',()=>ajustar(f));if(f.contentDocument?.readyState==='complete')ajustar(f);};
  document.querySelectorAll('iframe').forEach(vigilar);
  new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType!==1)return;if(n.tagName==='IFRAME')vigilar(n);else n.querySelectorAll?.('iframe').forEach(vigilar);}))).observe(document.body,{childList:true,subtree:true});
  function actualizar() {
    const tab=document.querySelector('[role="tab"][aria-selected="true"]');
    const actual=location.pathname==='/' ? '/?vista='+(tab?.id || new URLSearchParams(location.search).get('vista') || 'tab-resumen') : location.pathname;
    selector.value=[...selector.options].some(o=>o.value===actual)?actual:location.pathname;
    for(const enlace of nav.querySelectorAll('a')) {
      const activa=enlace.getAttribute('href')===actual || (enlace.getAttribute('href')==='/' && location.pathname==='/');
      if(activa)enlace.setAttribute('aria-current','page');else enlace.removeAttribute('aria-current');
    }
  }
  function ir(evento,valor) {
    const url=destinoLocal(valor,location.origin);
    const tab=url.pathname==='/' && location.pathname==='/' ? document.getElementById(url.searchParams.get('vista') || '') : null;
    if(tab?.matches('[role="tab"]')) {evento.preventDefault();tab.click();actualizar();}
    else if(evento.type==='change')location.assign(url.href);
  }
  selector.addEventListener('change',e=>ir(e,selector.value));
  nav.addEventListener('click',e=>{
    const a=e.target.closest('a');
    if(a && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.button===0)ir(e,a.getAttribute('href'));
  });
  document.addEventListener('terminal:pestana',actualizar);
  (async()=>{
    try {
      const r=await fetch('/static/navegacion.json',{signal:AbortSignal.timeout(10000)});
      if(!r.ok)throw new Error('Catálogo no disponible');
      const datos=await r.json();selector.replaceChildren();const vistos=new Set();
      for(const [titulo,filas] of [['Áreas y laboratorios',datos.areas],['Secciones de la terminal',datos.secciones]]) {
        const grupo=document.createElement('optgroup');grupo.label=titulo;
        for(const f of filas) {
          destinoLocal(f.url,location.origin);
          if(vistos.has(f.url))continue;vistos.add(f.url);
          grupo.append(new Option(f.titulo,f.url));
        }
        selector.append(grupo);
      }
      selector.disabled=false;actualizar();
    }catch {selector.replaceChildren(new Option('Usa los accesos directos',''));selector.disabled=true;}
  })();
}
