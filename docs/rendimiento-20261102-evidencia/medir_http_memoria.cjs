// Tres repeticiones controladas; solo lecturas locales y procesos creados por esta medición.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process'),net=require('node:net'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULO||'playwright');
const raiz=path.resolve(__dirname,'../..'),python=path.join(raiz,'.venv/Scripts/python.exe');
const powershell='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe';
const fase=process.argv[2]||'linea-base';
assert.match(fase,/^[a-z0-9-]+$/);
const versionOriginal=fase.startsWith('antes-');
const archivoDatos=process.env.PERFIL_BASE_SQLITE;
assert.ok(archivoDatos&&fs.existsSync(archivoDatos),'Hace falta el archivo SQLite de medición explícito.');
const permitidas=new Set(['SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA']);
const entorno=Object.fromEntries(Object.entries(process.env).filter(([k])=>permitidas.has(k.toUpperCase())));
const esperar=ms=>new Promise(r=>setTimeout(r,ms));
const raizTemporal=fs.realpathSync(os.tmpdir());
const huella=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const memoria=ids=>{
 assert.ok(ids.length&&ids.every(x=>Number.isInteger(x)&&x>0));
 const texto=cp.execFileSync(powershell,['-NoProfile','-NonInteractive','-Command',`Get-Process -Id ${ids.join(',')} -ErrorAction Stop | Select-Object Id,CPU,WorkingSet64,PrivateMemorySize64,PeakWorkingSet64 | ConvertTo-Json -Compress`],{encoding:'utf8',windowsHide:true});
 const r=JSON.parse(texto);return Array.isArray(r)?r:[r];
};
const puertoLibre=()=>new Promise((resolve,reject)=>{const s=net.createServer();s.on('error',reject);s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
(async()=>{
 const resultado={fecha:new Date().toISOString(),fase,node:process.version,cpu:os.cpus()[0]?.model,ram_bytes:os.totalmem(),procesadores_logicos:os.cpus().length,
  cache:'Proceso y contexto nuevos; caché de disco Windows sin purgar.',fuentes:'Copia SQLite local; motor/env/configuración personal y red externa desactivados; no prueba proveedores.',
  dataset_sha256:huella(archivoDatos),dataset_bytes:fs.statSync(archivoDatos).size,
  archivos:Object.fromEntries(['terminal/app.py','terminal/servicios.py','terminal/optimizador.py','web/static/mesa.mjs','config/ajustes.ejemplo.toml'].map(f=>[f,huella(path.join(raiz,f))])),repeticiones:[]};
 resultado.fuentes_cargadas=Object.fromEntries(['servicios','optimizador','espacios'].map(n=>[n,huella(path.join(versionOriginal?path.join(__dirname,'originales'):path.join(raiz,'terminal'),n+'.py'))]));
 if(!versionOriginal)resultado.fuentes_cargadas.criterios_propuestas=huella(path.join(raiz,'terminal/criterios_propuestas.py'));
 resultado.protocolo='Dos fases con cargador idéntico, compilación sin caché de bytecode para tres módulos; primera respuesta de navegación medida antes de consultas explícitas. Pasado/Futuro se consultan después de la ventana de memoria para declarar carga diferida.';
 for(let numero=1;numero<=3;numero++){
  const temporal=fs.mkdtempSync(path.join(raizTemporal,'terminal-medicion-'));
  let servidor,navegador,pid;
  try{
   fs.copyFileSync(archivoDatos,path.join(temporal,'terminal.db'));
   assert.equal(huella(path.join(temporal,'terminal.db')),resultado.dataset_sha256);
   const puerto=await puertoLibre(),origen=`http://127.0.0.1:${puerto}`,inicio=performance.now();
   servidor=cp.spawn(python,[path.join(__dirname,'servidor_aislado.py'),temporal,String(puerto),versionOriginal?'antes':'actual'],{cwd:raiz,env:entorno,stdio:['ignore','pipe','ignore'],windowsHide:true});
   let pendiente='';servidor.stdout.on('data',b=>{pendiente+=b.toString();const i=pendiente.indexOf('\n');if(i!==-1){try{const v=JSON.parse(pendiente.slice(0,i));if(Number.isInteger(v.pid_medicion))pid=v.pid_medicion;}catch{}pendiente='';}});
   let disponible=false,consultasInicio=0;
   while(performance.now()-inicio<180000){
    if(servidor.exitCode!==null)throw Error('El servidor de medición terminó antes de estar disponible.');
    try{consultasInicio++;const r=await fetch(origen+'/static/mesa.html',{signal:AbortSignal.timeout(1500)});if(r.ok){await r.arrayBuffer();disponible=true;break;}}catch{}
    await esperar(200);
   }
   assert.ok(disponible&&pid,'No se pudo confirmar la instancia propia.');
   const arranque=performance.now()-inicio;
   navegador=await chromium.launch({executablePath:process.env.CHROMIUM_EJECUTABLE,headless:true,env:entorno});
   const contexto=await navegador.newContext({viewport:{width:1440,height:1000},colorScheme:'dark'}),pagina=await contexto.newPage();
   let bloqueadas=0,mutaciones=0,peticiones=0,bytes=0;const errores=[];
   await contexto.route('**/*',r=>{if(r.request().method()!=='GET'){mutaciones++;return r.abort();}if(new URL(r.request().url()).origin!==origen){bloqueadas++;return r.abort();}return r.continue();});
   pagina.on('pageerror',e=>errores.push(e.name));pagina.on('request',()=>peticiones++);
   const cdp=await contexto.newCDPSession(pagina);await cdp.send('Network.enable');await cdp.send('Performance.enable');cdp.on('Network.loadingFinished',e=>bytes+=e.encodedDataLength);
   const frioPromesa=pagina.waitForResponse(r=>new URL(r.url()).pathname==='/api/estado',{timeout:120000}).then(r=>({respuesta:r}),error=>({error}));
   let t=performance.now();await pagina.goto(origen+'/static/mesa.html');await pagina.waitForFunction(()=>document.querySelector('#mesa-simbolo')?.disabled===false);const primerPanel=performance.now()-t;
   const frio=await frioPromesa;if(frio.error)throw frio.error;await frio.respuesta.finished();assert.ok(frio.respuesta.ok());
   const estadoFrio=frio.respuesta.request().timing().responseEnd;assert.ok(estadoFrio>=0);
   assert.equal(await pagina.locator('#mesa-paneles iframe').count(),0,'La medición requiere los paneles de Mesa inicialmente cerrados.');
   const marcosGlobales=await pagina.locator('iframe').count(); // La cinta de navegación es independiente de los paneles.
   const api={};for(const nombre of ['estado','universo']){const tiempos=[];for(let n=0;n<15;n++){t=performance.now();const r=await pagina.request.get(origen+'/api/'+nombre);assert.ok(r.ok(),`API ${nombre} no disponible`);await r.body();tiempos.push(performance.now()-t);}api[nombre]=tiempos;}
   t=performance.now();await pagina.reload();await pagina.waitForFunction(()=>document.querySelector('#mesa-simbolo')?.disabled===false);const tibia=performance.now()-t;
   const bc=await navegador.newBrowserCDPSession(),procesos=await bc.send('SystemInfo.getProcessInfo'),renderers=procesos.processInfo.filter(p=>p.type==='renderer').map(p=>p.id);
   assert.ok(renderers.length);const ids=[pid,...renderers];
   const muestras=[memoria(ids)],metricas0=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
   const inicioOcioso=performance.now(),q0=peticiones,b0=bytes;
   while(performance.now()-inicioOcioso<60000){await esperar(Math.min(6000,60000-(performance.now()-inicioOcioso)));muestras.push(memoria(ids));}
   const ventana=performance.now()-inicioOcioso,metricas=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
   const peticionesEspera=peticiones-q0,bytesEspera=bytes-b0;
   const vistasDiferidas={};for(const nombre of ['pasado','futuro']){t=performance.now();const r=await pagina.request.get(origen+'/api/'+nombre,{timeout:120000});assert.ok(r.ok(),`Vista ${nombre} no disponible`);await r.body();vistasDiferidas[nombre]={primera_consulta_ms:performance.now()-t,memoria:memoria(ids)};}
   assert.equal(mutaciones,0,'Se detectó una petición distinta de GET y quedó bloqueada.');assert.deepEqual(errores,[]);
   resultado.repeticiones.push({numero,arranque_http_ms:arranque,sondeos_arranque:consultasInicio,primer_panel_local_ms:primerPanel,navegacion_tibia_ms:tibia,estado_frio_navegacion_ms:estadoFrio,api,vistas_diferidas:vistasDiferidas,
    api_muestras_por_endpoint:15,ventana_espera_ms:ventana,peticiones_espera:peticionesEspera,bytes_cdp_espera:bytesEspera,peticiones_pagina_total:peticiones,bytes_cdp_pagina_total:bytes,
    peticiones_api_medidas:30,marcos_globales:marcosGlobales,externas_bloqueadas:bloqueadas,mutaciones,errores_js:errores,renderers,pid_servidor:pid,muestras_memoria:muestras,
    heap_js_bytes:metricas.JSHeapUsedSize,tareas_pestana_s:metricas.TaskDuration-metricas0.TaskDuration,
    cpu_servidor_espera_s:muestras.at(-1).find(p=>p.Id===pid).CPU-muestras[0].find(p=>p.Id===pid).CPU});
   fs.writeFileSync(path.join(__dirname,`${fase}-http-memoria.json`),JSON.stringify(resultado,null,2));
   console.log(`Repetición ${numero}/3 registrada; solo lectura local.`,{arranque_http_ms:Math.round(arranque)});
  }finally{
   try{if(navegador)await navegador.close();}finally{
    try{if(pid)cp.execFileSync(powershell,['-NoProfile','-NonInteractive','-Command',`Stop-Process -Id ${pid} -ErrorAction SilentlyContinue`],{stdio:'ignore',windowsHide:true});}finally{
     if(servidor){servidor.kill();await esperar(300);}
     const resuelto=fs.realpathSync(temporal);
     assert.equal(path.dirname(resuelto),raizTemporal);assert.ok(path.basename(resuelto).startsWith('terminal-medicion-'));
     fs.rmSync(resuelto,{recursive:true,force:true,maxRetries:5,retryDelay:500});
    }
   }
  }
 }
 assert.equal(huella(archivoDatos),resultado.dataset_sha256,'El archivo de origen debe permanecer intacto.');
 console.log('Tres repeticiones completas; instancias y copias temporales cerradas.');
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
