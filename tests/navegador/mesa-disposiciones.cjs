// Altura automática y disposiciones con proveedores simulados; no requiere servidor ni claves.
const {chromium}=require(process.env.PLAYWRIGHT_MODULO||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const raiz=process.env.TERMINAL_RAIZ||path.resolve(__dirname,'../..');
(async()=>{const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EJECUTABLE||undefined});try{
 const resultados=[];
 for(const ancho of [390,1440]){
 const c=await b.newContext({viewport:{width:ancho,height:1000}}),p=await c.newPage(),errores=[];p.on('pageerror',e=>errores.push(e.message));
 await c.route('**/*',async r=>{const u=new URL(r.request().url());if(u.origin!=='http://127.0.0.1:8796'||r.request().method()!=='GET')return r.abort();
 if(u.pathname.startsWith('/static/')){const f=path.resolve(raiz,'web',u.pathname.slice(1));if(!f.startsWith(path.resolve(raiz,'web/static')+path.sep))return r.abort();if(fs.existsSync(f))return r.fulfill({body:fs.readFileSync(f),contentType:f.endsWith('.mjs')?'text/javascript':f.endsWith('.css')?'text/css':f.endsWith('.json')?'application/json':'text/html'});}
 if(u.pathname.startsWith('/widget/'))return r.fulfill({body:`<!doctype html><title>Marco simulado para prueba de interfaz</title><body style="margin:0"><div data-prueba style="height:${u.pathname==='/widget/mapa'?1100:24}px">Sin proveedor conectado · prueba de altura automática</div></body>`,contentType:'text/html'});
 if(u.pathname==='/api/universo')return r.fulfill({status:503,body:'Catálogo no disponible en prueba aislada'});
 if(u.pathname==='/api/mesa/resumen')return r.fulfill({json:{eventos_alto_impacto_7d:[],calendario_bea:{consultado_en:'2026-11-03T19:00:00+00:00',eventos:[{fecha:'2026-11-04T13:30:00+00:00',titulo:'Comercio internacional'}]}}});
 if(u.pathname==='/api/mesa/resultados')return r.fulfill({status:503,body:'Resultados no disponibles en prueba aislada'});
 return r.fulfill({status:503,body:'Sin dato en prueba aislada'});});
 await p.goto('http://127.0.0.1:8796/static/mesa.html');
 await p.evaluate(()=>localStorage.setItem('actinver.mesa.v1',JSON.stringify({widgets:['mapa'],simbolo:'',altos:{mapa:620},guardadas:{Compacta:{widgets:['mapa'],tamanos:{},altos:{mapa:620}},Amplia:{widgets:['mapa'],tamanos:{mapa:'ancho'},altos:{mapa:900}}}})));
 await p.reload();const card=p.locator('[data-panel="mapa"]'),d=card.locator('details');await d.locator('summary').click();await card.locator('iframe').waitFor();
 await p.waitForFunction(()=>document.querySelector('[data-panel="mapa"] iframe')?.clientHeight>=1100);
 await card.locator('iframe').evaluate(f=>{window.marcoOriginal=f});
 await p.locator('#mesa-preset').selectOption('g:Amplia');
 assert.ok(await card.locator('iframe').evaluate(f=>f.clientHeight>=1100)); // No impone el alto manual antiguo.
 assert.equal(await card.getByRole('button',{name:/Ocupar todo el ancho/}).getAttribute('aria-pressed'),'true');
 await p.locator('#mesa-preset').selectOption('g:Compacta');
 assert.ok(await card.locator('iframe').evaluate(f=>f.clientHeight>=1100));
 assert.equal(await card.locator('iframe').evaluate(f=>f===window.marcoOriginal),true);
 assert.equal(await card.getByRole('button',{name:/Ocupar todo el ancho/}).getAttribute('aria-pressed'),'false');
 assert.equal(await card.getByRole('slider').count(),0);
 await card.locator('iframe').evaluate(f=>{f.contentDocument.querySelector('[data-prueba]').style.height='2500px';});
 await p.waitForFunction(()=>document.querySelector('[data-panel="mapa"] iframe')?.style.height==='2000px');
 await d.locator('summary').click();await card.locator('iframe').waitFor({state:'detached'});assert.equal(await card.locator('iframe').count(),0);await d.locator('summary').click();await card.locator('iframe').waitFor();
 await p.waitForFunction(()=>document.querySelector('[data-panel="mapa"] iframe')?.clientHeight>=1100);
 await p.reload();assert.equal(await p.locator('[data-panel="mapa"] input[type="range"]').count(),0);
 await p.locator('[data-panel="mapa"] summary').click();await p.locator('[data-panel="mapa"] iframe').waitFor();
 await p.waitForFunction(()=>document.querySelector('[data-panel="mapa"] iframe')?.clientHeight>=1100);
 await p.evaluate(()=>localStorage.setItem('actinver.mesa.v1',JSON.stringify({widgets:['calendario'],simbolo:''})));
 await p.reload();
 const calendario=p.locator('[data-panel="calendario"]');
 await calendario.locator('.mesa-nativo').waitFor();
 await calendario.getByText('2026-11-04 13:30 UTC · Comercio internacional',{exact:true}).waitFor({timeout:5000}).catch(async e=>{console.error(await calendario.innerText());throw e;});
 await calendario.getByText('BEA · Publicaciones programadas (UTC)',{exact:true}).waitFor({timeout:5000}).catch(async e=>{console.error(await calendario.innerText());throw e;});
 await calendario.getByText(/Resultados de empresas: SIN DATO/).waitFor();
 assert.match(await calendario.getByText(/Copia local consultada/).textContent(),/2026-11-03T19:00:00/);
 assert.equal(await calendario.getByRole('link',{name:'Consultar el calendario oficial de BEA'}).getAttribute('href'),'https://www.bea.gov/news/schedule');
 assert.deepEqual(errores,[]);assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));resultados.push({ancho,altura_automatica:true,tope_2000:true,cierre_destruye_marco:true,disposiciones_conservadas:true,marco_reutilizado:true,errores});await c.close();}
 fs.writeFileSync(raiz+'/docs/proveedores-20261101-evidencia/mesa-altura-automatica-ui-20261102.json',JSON.stringify({proveedores:'simulados; solo interfaz',resultados},null,2));console.log(JSON.stringify(resultados));
 }finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
