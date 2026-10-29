// Análisis descriptivo original: no agentes LLM, señales ejecutables ni órdenes.
export function resumir(velas = {}, flujo = {}, ahora = Date.now()) {
  const barras = Array.isArray(velas.barras) ? velas.barras : [];
  const ultima = barras.at(-1);
  const finitos = (...xs) => xs.every(x => typeof x === 'number' && Number.isFinite(x));
  const fuentes = new Set(barras.map(b => `${b.fuente}|${b.feed}|${b.calidad}`));
  const calidad = ultima?.calidad || 'sin dato';
  const ms = Date.parse(ultima?.inicio);
  const edad = Number.isFinite(ms) ? (ahora - ms) / 60000 : null;
  const reciente = edad !== null && edad >= 0 && edad <= 15;
  const limpia = barras.length > 0 && fuentes.size === 1 && ['proveedor','importado'].includes(calidad);
  const tendencia = limpia && finitos(ultima?.ema20, ultima?.ema50)
    ? (ultima.ema20 > ultima.ema50 ? 'EMA20 sobre EMA50' : ultima.ema20 < ultima.ema50 ? 'EMA20 bajo EMA50' : 'EMA20 igual a EMA50')
    : 'Sin comparación válida de medias';
  const r = flujo.resumen || {};
  const p = flujo.procedencia_operaciones || [];
  const deltaValido = r.n > 0 && r.con_lado === r.n && finitos(r.delta) && p.length === 1 && ['proveedor','importado'].includes(p[0].calidad);
  const mensajes = [
    {rol:'Datos', texto:ultima ? `${barras.length} barras · fuente ${ultima.fuente || 'desconocida'} · ${calidad}. Inicio de última barra: ${ultima.inicio || 'sin fecha'}.` : 'No hay velas guardadas para este símbolo y rango.'},
    {rol:'Cuantitativo', texto:`${tendencia}. Comparación descriptiva; no prueba alfa ni constituye entrada.`},
    {rol:'Order Flow', texto:deltaValido ? `Delta observado ${r.delta}, en ${r.n} operaciones con lado informado. Ventana independiente de las velas.` : 'Delta no disponible o procedencia no homogénea. No se infiere el agresor.'},
    {rol:'Crítico', texto:fuentes.size > 1 ? 'Hay fuentes, feeds o calidades mezcladas. Comparación de medias bloqueada.' : 'Una sola observación y un consenso visual no demuestran rentabilidad. Faltan holdout, costes y prueba de permutación.'},
    {rol:'Riesgo', texto:limpia && reciente ? 'Barra reciente de proveedor o importación. Esto no certifica tiempo real, liquidez, permisos CME ni suficiencia para operar.' : 'Revisión suspendida para uso intradía: datos ausentes, antiguos, futuros, sintéticos o de calidad no confirmada.'},
    {rol:'Coordinación', texto:'Informe descriptivo. No genera órdenes, posiciones, P&L ni decisiones automáticas. Gamma, opciones y TPO se revisan en sus apartados específicos.'}
  ];
  return {simbolo:velas.simbolo || flujo.simbolo || '', generado_en:new Date(ahora).toISOString(), motor:'reglas descriptivas; sin LLM', ordenes_habilitadas:false, edad_inicio_barra_min:edad, evidencia:{intervalo:velas.intervalo,procedencia_velas:velas.procedencia || [],procedencia_operaciones:p,nota_velas:velas.nota,nota_operaciones:flujo.nota}, mensajes};
}

export function instrumentosDelCatalogo(universo = {}, flujo = {}) {
  const filas = new Map();
  const agregar = (id, nombre, grupo) => {
    if (typeof id !== 'string' || !id.trim() || filas.has(id)) return;
    filas.set(id, {id, nombre: nombre || id, grupo, conDatos:false});
  };
  for (const i of universo.instrumentos || []) {
    if (i.estado !== 'inactivo') agregar(i.id, `${i.clave_operable || i.id} — ${i.nombre || i.id}`, 'Catálogo de la terminal');
  }
  for (const i of [...(flujo.sic || []), ...(flujo.cripto || [])]) agregar(i.id, i.clave || i.id, 'Otros instrumentos de flujo');
  for (const id of flujo.con_datos || []) {
    agregar(id, id, 'Símbolos importados');
    if (filas.has(id)) filas.get(id).conDatos = true;
  }
  return [...filas.values()].sort((a,b) => (b.conDatos - a.conDatos) || a.grupo.localeCompare(b.grupo,'es') || a.nombre.localeCompare(b.nombre,'es'));
}

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  let informe;
  const leer = async path => {
    const res = await fetch(path,{signal:AbortSignal.timeout(15000),cache:'no-store'});
    if(!res.ok) throw new Error(`Consulta fallida (${res.status})`);
    return res.json();
  };
  function invalidarInforme() {
    informe=null;$('exportar').disabled=true;$('claude').disabled=true;
    $('analisis-claude').hidden=true;$('prompt-comite').value='';
    $('estado-informe').textContent='Sin consulta';
    $('estado').textContent='Selecciona el instrumento y pulsa Consultar mesas. Velas: 7 días; operaciones: 60 minutos.';
    const p=document.createElement('p');p.className='vacio';p.textContent='Consulta pendiente para esta selección.';
    $('oficina').replaceChildren(p);
  }
  async function cargarCatalogo() {
    $('simbolo').disabled=true;$('consultar').disabled=true;$('recargar-catalogo').hidden=true;
    $('catalogo-estado').textContent='Leyendo catálogo local…';
    const [universo, flujo] = await Promise.allSettled([leer('/api/universo'),leer('/api/flujo/estado')]);
    const lista=instrumentosDelCatalogo(universo.status==='fulfilled' ? universo.value : {}, flujo.status==='fulfilled' ? flujo.value.catalogo : {});
    $('simbolo').replaceChildren(new Option(lista.length ? 'Selecciona un instrumento' : 'Catálogo no disponible',''));
    const grupoDe = i => i.conDatos ? 'Con datos guardados' : i.grupo;
    for(const nombre of new Set(lista.map(grupoDe))) {
      const grupo=document.createElement('optgroup');grupo.label=nombre;
      for(const i of lista.filter(i=>grupoDe(i)===nombre))grupo.append(new Option(i.nombre,i.id));
      $('simbolo').append(grupo);
    }
    const parcial=universo.status!=='fulfilled' || flujo.status!=='fulfilled';
    $('catalogo-estado').textContent=lista.length ? `${lista.length} instrumentos${parcial ? ' · catálogo parcial; una fuente local no respondió' : ''}.` : 'No se pudo obtener un catálogo con instrumentos. Reintenta la carga.';
    $('simbolo').disabled=!lista.length;
    $('recargar-catalogo').hidden=!parcial && !!lista.length;
    // Selección inicial: ?simbolo= en la dirección, o la última consulta de este navegador
    const pedido=new URLSearchParams(location.search).get('simbolo') || guardado('simbolo');
    const intervalo=guardado('intervalo');
    if(intervalo && [...$('intervalo').options].some(o=>o.value===intervalo))$('intervalo').value=intervalo;
    if(pedido && lista.some(i=>i.id===pedido)){$('simbolo').value=pedido;actualizarAccesos();consultar();}
  }
  function guardado(k){try{return localStorage.getItem(`oficina:${k}`);}catch{return null;}}
  function guardar(k,v){try{localStorage.setItem(`oficina:${k}`,v);}catch{/* sin almacenamiento */}}
  function actualizarAccesos(){
    const id=$('simbolo').value, q=encodeURIComponent(id);
    for(const [a,vista] of [['ir-velas','tab-velas'],['ir-orderflow','tab-orderflow'],['ir-optionflow','tab-optionflow']]){
      $(a).href=id?`/?vista=${vista}&simbolo=${q}`:`/?vista=${vista}`;
      if(id)$(a).removeAttribute('aria-disabled');else $(a).setAttribute('aria-disabled','true');
    }
    $('accesos-ayuda').textContent=!id?'Elija un instrumento para ver sus accesos directos.'
      :id.startsWith('SIC:')?'Abre la sección de la terminal con este instrumento ya elegido. El GEX está en Option Flow.'
      :'Abre la sección con este instrumento. Option Flow y GEX solo existen para emisoras del SIC con opciones en EE. UU.';
  }
  $('simbolo').addEventListener('change',()=>{invalidarInforme();actualizarAccesos();$('consultar').disabled=!$('simbolo').value;if($('simbolo').value)consultar();});
  $('intervalo').addEventListener('change',()=>{invalidarInforme();guardar('intervalo',$('intervalo').value);if($('simbolo').value)consultar();});
  $('recargar-catalogo').addEventListener('click',()=>{invalidarInforme();cargarCatalogo();});
  function mostrar(r) {
    $('oficina').replaceChildren(...r.mensajes.map((m,i) => {
      const card = document.createElement('article');
      const folio = document.createElement('span'); folio.className='oficina-folio'; folio.textContent=String(i+1).padStart(2,'0'); folio.setAttribute('aria-hidden','true');
      const texto = document.createElement('div');
      const h = document.createElement('h3');h.textContent=m.rol;
      const p = document.createElement('p');p.textContent=m.texto;
      texto.append(h,p);card.append(folio,texto);return card;
    }));
    $('exportar').disabled=false;$('claude').disabled=false;$('estado-informe').textContent='Informe disponible';
  }
  $('consulta').addEventListener('submit', e => {e.preventDefault();consultar();});
  async function consultar() {
    $('consultar').disabled=true;$('exportar').disabled=true;$('claude').disabled=true;$('analisis-claude').hidden=true;informe=null;
    const simbolo=$('simbolo').value.trim();
    if(!simbolo){$('consultar').disabled=true;return;}
    $('simbolo').disabled=true;$('intervalo').disabled=true;
    $('estado').textContent='Leyendo datos guardados…';$('estado-informe').textContent='Consultando';$('oficina').setAttribute('aria-busy','true');$('oficina').replaceChildren();
    try {
      const q=encodeURIComponent(simbolo), intervalo=$('intervalo').value;
      const [velas,flujo]=await Promise.all([leer(`/api/flujo/velas?simbolo=${q}&intervalo=${intervalo}&dias=7`),leer(`/api/flujo/libro-operaciones?simbolo=${q}&minutos=60&niveles=5`)]);
      informe=resumir(velas,flujo);mostrar(informe);guardar('simbolo',simbolo);
      $('estado').textContent=`${simbolo} · informe ${new Date(informe.generado_en).toLocaleString('es-MX')} · lectura local; no actualiza proveedores.`;
    } catch(err) {$('estado-informe').textContent='Consulta no disponible';$('estado').textContent=`${err.message}. Abre esta vista desde la terminal local y verifica los datos importados.`;}
    finally {$('consultar').disabled=false;$('simbolo').disabled=false;$('intervalo').disabled=false;$('oficina').setAttribute('aria-busy','false');}
  }
  $('exportar').addEventListener('click',()=>{
    if(!informe)return;
    const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(informe,null,2)],{type:'application/json'}));
    a.href=url;a.download='informe-oficina.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $('claude').addEventListener('click',()=>{
    if(!informe)return;
    $('prompt-comite').value='Actúa como comité de investigación de Actinver-terminal. Examina esta evidencia con seis roles: Datos, Cuantitativo, Order Flow, Crítico, Riesgo y Coordinación. Son perspectivas de una revisión, no agentes ejecutándose de forma autónoma. Separa hechos, hipótesis y datos ausentes. Cita fuente, feed, fecha y calidad; no confundas hora del informe con vigencia del mercado. No inventes cotizaciones, alfa, gamma, órdenes ni P&L. Propón un experimento preregistrado con costes, holdout temporal y permutaciones por bloques; rechaza usos intradía si el feed es insuficiente. Resume desacuerdos y próximos pasos sin ejecutar operaciones. Si faltan observaciones crudas, solicítalas antes de cálculos nuevos.\n\nEvidencia local:\n'+JSON.stringify(informe,null,2);
    $('analisis-claude').hidden=false;$('prompt-comite').focus();
  });
  cargarCatalogo();
}
