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

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  let informe;
  function mostrar(r) {
    $('oficina').replaceChildren(...r.mensajes.map((m,i) => {
      const card = document.createElement('article');
      const icon = document.createElement('div'); icon.className='persona p'+i; icon.setAttribute('aria-hidden','true');
      const h = document.createElement('h2');h.textContent=m.rol;
      const p = document.createElement('p');p.textContent=m.texto;
      card.append(icon,h,p);return card;
    }));
    $('exportar').disabled=false;$('claude').disabled=false;
  }
  $('consulta').addEventListener('submit', async e => {
    e.preventDefault();$('consultar').disabled=true;$('exportar').disabled=true;$('claude').disabled=true;$('analisis-claude').hidden=true;informe=null;
    const simbolo=$('simbolo').value.trim();
    $('estado').textContent='Leyendo datos guardados…';$('oficina').replaceChildren();
    try {
      const q=encodeURIComponent(simbolo), intervalo=$('intervalo').value;
      const leer=async path => {const res=await fetch(path,{signal:AbortSignal.timeout(15000),cache:'no-store'});if(!res.ok)throw new Error(`Consulta fallida (${res.status})`);return res.json();};
      const [velas,flujo]=await Promise.all([leer(`/api/flujo/velas?simbolo=${q}&intervalo=${intervalo}&dias=7`),leer(`/api/flujo/libro-operaciones?simbolo=${q}&minutos=60&niveles=5`)]);
      informe=resumir(velas,flujo);mostrar(informe);
      $('estado').textContent=`${simbolo} · informe ${new Date(informe.generado_en).toLocaleString('es-MX')} · lectura local; no actualiza proveedores.`;
    } catch(err) {$('estado').textContent=`${err.message}. Abre esta vista desde la terminal local y verifica los datos importados.`;}
    finally {$('consultar').disabled=false;}
  });
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
}
