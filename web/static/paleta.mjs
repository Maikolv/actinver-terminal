// Búsqueda compartida de destinos locales. No consulta precios ni ejecuta acciones financieras.
export function siguienteSugerencia(actual,tecla,total) {
  if(!Number.isInteger(total)||total<1||!['ArrowUp','ArrowDown'].includes(tecla))return -1;
  if(!Number.isInteger(actual)||actual<0||actual>=total)return tecla==='ArrowUp'?total-1:0;
  return (actual+(tecla==='ArrowUp'?-1:1)+total)%total;
}
export function buscarDestinos(texto,{catalogo=[],secciones=[]}={}) {
  const q=String(texto||'').trim().toLocaleLowerCase('es');
  if(!q)return [];
  const tiene=s=>String(s).toLocaleLowerCase('es').includes(q),out=[];
  for(const i of catalogo.filter(i=>tiene(`${i.id} ${i.clave_operable} ${i.nombre}`)).slice(0,8))
    out.push({tipo:'instrumento',etiqueta:`${i.clave_operable} · ${i.nombre}`,valor:i.id});
  for(const s of secciones.filter(s=>typeof s.url==='string'&&s.url.startsWith('/')&&!s.url.startsWith('//')&&tiene(s.titulo)).slice(0,6))
    out.push({tipo:'seccion',etiqueta:`Ir a ${s.titulo}`,valor:s.url});
  return out;
}
