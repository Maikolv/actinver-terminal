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
    if(u.pathname==='/api/flujo/estado')return ruta.fulfill({json:{catalogo:{con_datos:[],sic:[],intervalos:['1Day']}}});
    if(u.pathname==='/api/flujo/velas')return ruta.fulfill({json:{barras:[],grafica:false,vacio:'SIN DATO'}});
    if(u.pathname==='/api/visualizaciones/serie/BMV%3ASMARTRC'&&process.env.AMX_ERROR==='1')return ruta.fulfill({status:503,json:{detail:'Prueba'}});
    if(u.pathname==='/api/visualizaciones/serie/BMV%3ASMARTRC')return ruta.fulfill({json:process.env.AMX_CACHE==='1'?JSON.parse(fs.readFileSync(path.join(__dirname,'serie-amx.json'),'utf8')):{puntos:process.env.AMX_SIN_CIERRES==='1'?[]:[{fecha:'2026-10-30',cierre:23}],proveedor:'fixture',moneda:'MXN',modo:'sintetico'}});
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
   await pagina.goto(origen+'/?vista=tab-velas&simbolo=BMV%3ASMARTRC');
   const caja=pagina.locator('#velas-contenido');
   const sinCierres=process.env.AMX_SIN_CIERRES==='1'; await caja.getByText(process.env.AMX_ERROR==='1'?'SIN DATO · No se pudo consultar el histórico local.':sinCierres?'SIN DATO · No hay cierres locales de SMARTRC 14.':'Cierres diarios guardados',{exact:true}).waitFor({timeout:8000});
   assert.equal(await caja.getByLabel('Instrumento').inputValue(),'BMV:SMARTRC');
   assert.equal(await caja.locator('iframe').count(),0); assert.match(await caja.getByRole('link',{name:'Consultar la gráfica pública de BMV'}).getAttribute('href'), /SMARTRC%2014-31400/);
   if(sinCierres)assert.equal(await caja.getByRole('link',{name:'Consultar SMARTRC 14 en TradingView'}).getAttribute('href'),'https://es.tradingview.com/symbols/BMV-SMARTRC%2F14/');
   if(!sinCierres&&process.env.AMX_ERROR!=='1')assert.match(await caja.innerText(),process.env.AMX_CACHE==='1'?/eodhd.*MXN.*Histórico/:/fixture.*MXN.*Sintético/);
   await pagina.screenshot({path:path.join(__dirname,(process.env.AMX_ERROR==='1'?'error-':process.env.AMX_CACHE==='1'?'cache-':sinCierres?'smartrc-sin-cierres-':'respaldo-')+ancho+'-'+tema+'.png')});
   resultados.push({ancho,tema,errores});
      await contexto.close();
  }
 }finally{await navegador.close();}
 fs.writeFileSync(path.join(__dirname,process.env.AMX_ERROR==='1'?'error-resultado.json':process.env.AMX_CACHE==='1'?'cache-resultado.json':process.env.AMX_SIN_CIERRES==='1'?'smartrc-sin-cierres-resultado.json':'respaldo-resultado.json'),JSON.stringify(resultados,null,2));
 console.log('Cuatro casos de SMARTRC sin cierres aprobados.');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
