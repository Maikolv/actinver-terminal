// Interfaz real con una respuesta de costos sintética; sin servidor, claves o proveedores.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULO||'playwright');
const raiz=path.resolve(__dirname,'../../..'),origen='http://127.0.0.1:8796';
(async()=>{
 const navegador=await chromium.launch({executablePath:'C:/Users/MIKE/AppData/Local/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell-win64/chrome-headless-shell.exe'}),resultados=[];
 try{
  for(const ancho of [390,1440])for(const tema of ['light','dark']){
   const contexto=await navegador.newContext({viewport:{width:ancho,height:1000},colorScheme:tema}),pagina=await contexto.newPage(),errores=[];
   pagina.on('pageerror',e=>errores.push(e.message));
   await contexto.route('**/*',ruta=>{
    const peticion=ruta.request(),u=new URL(peticion.url());
    if(u.origin!==origen||peticion.method()!=='GET')return ruta.abort();
    if(u.pathname==='/api/costos')return ruta.fulfill({contentType:'application/json',body:fs.readFileSync(path.join(__dirname,'costos-sinteticos.json'))});
    if(u.pathname==='/api/universo')return ruta.fulfill({json:{instrumentos:[]}});
    if(u.pathname.startsWith('/api/'))return ruta.fulfill({status:503,json:{detail:'SIN DATO en la prueba aislada'}});
    let archivo=u.pathname==='/'?path.join(raiz,'web/index.html'):path.resolve(raiz,'web',u.pathname.slice(1));
    if(!archivo.startsWith(path.join(raiz,'web')+path.sep)||!fs.existsSync(archivo))return ruta.fulfill({status:404,body:'No disponible'});
    let contenido=fs.readFileSync(archivo);
    if(u.pathname==='/'){
     contenido=contenido.toString();
     // Equivalente a la plantilla del servidor en modo real; CSRF ficticio y todo POST bloqueado.
     for(const [k,v] of Object.entries({'__CSRF__':'revision-sin-post','__OCULTO_DEMO__':'hidden','__DESTINO__':'demo','__CLASE_MODO__':'','__TEXTO_MODO__':'Ver demostración'}))contenido=contenido.replaceAll(k,v);
     contenido=contenido.replace(/(<body[^>]*>)/,'$1<div role="note">REVISIÓN DE INTERFAZ · CONFIGURACIÓN SINTÉTICA · SIN PROVEEDORES</div>');
    }
    return ruta.fulfill({contentType:archivo.endsWith('.mjs')||archivo.endsWith('.js')?'text/javascript':archivo.endsWith('.css')?'text/css':archivo.endsWith('.json')?'application/json':archivo.endsWith('.svg')?'image/svg+xml':'text/html',body:contenido});
   });
   await pagina.goto(origen+'/?vista=tab-universo');
   await pagina.evaluate(()=>document.getElementById('tab-universo').click());
   await pagina.waitForFunction(()=>document.querySelector('#costos-servicios')?.textContent.includes('bloqueado por política'));
   // La carga inicial puede terminar después del primer clic: confirmar el panel visible.
   await pagina.evaluate(()=>document.getElementById('tab-universo').click());
   const caja=pagina.locator('#costos-servicios'),texto=await caja.innerText();
   await caja.waitFor({state:'visible'});
   for(const nombre of ['API de Claude','Twelve Data','Barchart'])assert.ok(texto.includes(nombre));
   assert.equal(await caja.getByRole('button',{name:'Aprobar cargo'}).count(),0);
   assert.equal((texto.match(/bloqueado por política/g)||[]).length,3);
   await pagina.screenshot({path:path.join(__dirname,`${ancho}-${tema}.png`),fullPage:true,animations:'disabled'});
   resultados.push({ancho,tema,servicios_pago_bloqueados:3,botones_aprobar:0,errores,alcance:'Solo interfaz de costos; los otros endpoints devuelven SIN DATO y no prueban datos o proveedores.'});
   await contexto.close();
  }
 }finally{await navegador.close();}
 fs.writeFileSync(path.join(__dirname,'resultado.json'),JSON.stringify(resultados,null,2));
 console.log('Cuatro revisiones de interfaz de costos aprobadas, sin peticiones externas ni botones de aprobación.');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
