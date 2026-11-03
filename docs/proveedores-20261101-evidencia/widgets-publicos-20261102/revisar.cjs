// Revisión pública de marcos generados por la aplicación; no alimenta modelos.
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULO||'playwright');
const raiz=path.resolve(__dirname,'../../..'),origen='http://127.0.0.1:8796';
const lecturaScan=process.env.PERMITIR_LECTURA_SCAN==='1',preflight=process.env.PERMITIR_PREFLIGHT==='1';
const metainfo=process.env.PERMITIR_METAINFO==='1';
const prefijo=metainfo?'lectura-completa-':preflight?'lectura-scan-preflight-':lecturaScan?'lectura-scan-':'';
(async()=>{
 const navegador=await chromium.launch({executablePath:'C:/Users/MIKE/AppData/Local/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell-win64/chrome-headless-shell.exe'});
 const resultados=[];
 try{
  for(const marco of JSON.parse(fs.readFileSync(path.join(__dirname,'marcos.json'),'utf8')).filter(m=>preflight?m.tipo==='filtro':!lecturaScan||['mapa','mapa-etf','filtro','destacados'].includes(m.tipo))){
   const contexto=await navegador.newContext({viewport:{width:1440,height:1000}}),pagina=await contexto.newPage();
   const errores=[],bloqueos=[];
   pagina.on('pageerror',e=>errores.push(e.message.slice(0,250)));
   await contexto.route('**/*',async ruta=>{
    const peticion=ruta.request(),u=new URL(peticion.url());
    // POST /scan es la consulta de lectura del embed oficial en un contexto vacío,
    // no una orden, mensaje o API incorporada a los modelos de Actinver.
    const rutaLectura=/\/scan$/.test(u.pathname)||(metainfo&&u.pathname==='/america/metainfo');
    const consultaPublica=lecturaScan&&u.hostname==='scanner.tradingview.com'&&((peticion.method()==='POST'&&rutaLectura)||(preflight&&peticion.method()==='OPTIONS'));
    if(!['GET','HEAD'].includes(peticion.method())&&!consultaPublica){bloqueos.push({host:u.host,ruta:u.pathname,metodo:peticion.method(),motivo:'método excluido'});return ruta.abort();}
    if(u.origin===origen){
     if(u.pathname==='/revision')return ruta.fulfill({contentType:'text/html',body:`<!doctype html><html lang="es"><title>Revisión pública aislada</title><body style="margin:0;background:#090a0c"><iframe title="Panel externo en revisión" ${marco.tipo==='calendario'?'sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"':''} referrerpolicy="no-referrer" src="/panel" style="width:100%;height:900px;border:0"></iframe></body></html>`});
     if(u.pathname==='/panel')return ruta.fulfill({status:200,headers:marco.headers,body:fs.readFileSync(path.join(__dirname,marco.archivo))});
     if(['/static/grafica.css','/static/favicon.svg'].includes(u.pathname))return ruta.fulfill({body:fs.readFileSync(path.join(raiz,'web',u.pathname)),contentType:u.pathname.endsWith('.css')?'text/css':'image/svg+xml'});
     return ruta.fulfill({status:404,body:'SIN DATO en revisión aislada'});
    }
    if(/(^|\.)(tradingview\.com|tradingview-widget\.com)$/.test(u.hostname))return ruta.continue();
    bloqueos.push({host:u.host,motivo:'origen fuera del proveedor'});return ruta.abort();
   });
   await pagina.goto(origen+'/revision');await pagina.waitForTimeout(7000);
   const contenido=[];
   for(const f of pagina.frames()){
    if(f===pagina.mainFrame()||new URL(f.url()).origin===origen)continue;
    try{contenido.push({host:new URL(f.url()).host,texto:(await f.locator('body').innerText({timeout:1500})).slice(0,1800)});}catch{contenido.push({host:new URL(f.url()).host,texto:'',lectura:'No disponible en esta observación'});}
   }
   await pagina.screenshot({path:path.join(__dirname,prefijo+marco.tipo+'.png'),fullPage:true});
   resultados.push({tipo:marco.tipo,contenido,errores,bloqueos,consulta_publica_scan_permitida:lecturaScan,vigencia:'NO VERIFICADA',observado_en:new Date().toISOString()});
   fs.writeFileSync(path.join(__dirname,prefijo+'resultado.json'),JSON.stringify(resultados,null,2));
   console.log(marco.tipo+': '+contenido.filter(x=>x.texto).length+' marcos con texto; vigencia no verificada');
   await contexto.close();
  }
 }finally{await navegador.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
