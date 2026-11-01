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
  cinta.title='Cinta de indicadores: índices, VIX, bono a 10 años, dólar, oro, petróleo y bitcoin (TradingView, con retraso)';
  cinta.src=`/widget/cinta-macro?tema=${matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}`;
  nav.after(cinta);
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
