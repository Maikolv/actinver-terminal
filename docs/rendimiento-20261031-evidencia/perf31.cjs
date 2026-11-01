const fs=require('fs'),cp=require('child_process'),path=require('path');
const {chromium}=require('./ui-check/node_modules/playwright');
const root='C:/Users/MIKE/Desktop/Repos/actinver-terminal',ev=root+'/docs/rendimiento-20261031-evidencia';fs.mkdirSync(ev,{recursive:true});
const phase=process.argv[2],url='http://127.0.0.1:8796';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const stats=pid=>JSON.parse(cp.execFileSync('powershell',['-NoProfile','-Command',`Get-Process -Id ${pid} | Select-Object CPU,WorkingSet64 | ConvertTo-Json -Compress`],{encoding:'utf8'}));
(async()=>{const out=[];for(let i=0;i<3;i++){
 const start=performance.now(),server=cp.spawn(root+'/.venv/Scripts/python.exe',[__dirname+'/perf31_server.py',__dirname+'/perf31-datos'],{stdio:'ignore'});
 let ready=false;for(let n=0;n<240;n++){try{const r=await fetch(url+'/static/mesa.html');if(r.ok){ready=true;break;}}catch{}await sleep(250);}if(!ready)throw Error('Servidor no disponible');
 const startup=performance.now()-start,pid=Number(fs.readFileSync(__dirname+'/perf31-datos/pid.txt','utf8'));console.log('Inicio '+phase+' '+(i+1));
 const browser=await chromium.launch({executablePath:'C:/Users/MIKE/AppData/Local/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell-win64/chrome-headless-shell.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});await context.route('**/*',r=>r.request().url().startsWith(url)?r.continue():r.abort());
 const page=await context.newPage();const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');await cdp.send('Network.enable');let bytes=0,requests=0;cdp.on('Network.loadingFinished',e=>bytes+=e.encodedDataLength);page.on('request',()=>requests++);
 let t=performance.now();await page.goto(url+'/static/mesa.html');await page.waitForFunction(()=>document.querySelector('#mesa-simbolo')?.disabled===false);const first=performance.now()-t;
 const api={};for(const endpoint of ['estado','universo']){const times=[];for(let k=0;k<15;k++){t=performance.now();const r=await page.request.get(url+'/api/'+endpoint);if(!r.ok())throw Error(endpoint);await r.body();times.push(performance.now()-t);}api[endpoint]=times;}
 t=performance.now();await page.reload();await page.waitForFunction(()=>document.querySelector('#mesa-simbolo')?.disabled===false);const warm=performance.now()-t;
 // Deliberately retain the same four open external panels; providers are blocked in both phases.
 await page.locator('details summary').first().click();await sleep(200);
 t=performance.now();await page.locator('[data-panel="grafica"] button').filter({hasText:'→'}).click();const move=performance.now()-t;
 const before=stats(pid),metrics0=await cdp.send('Performance.getMetrics');const q0=requests,b0=bytes;await sleep(60000);const after=stats(pid),metrics1=await cdp.send('Performance.getMetrics');
 const metrics=Object.fromEntries(metrics1.metrics.map(m=>[m.name,m.value]));const m0=Object.fromEntries(metrics0.metrics.map(m=>[m.name,m.value]));
 out.push({rep:i+1,startup_ms:startup,first_panel_ms:first,warm_navigation_ms:warm,reorder_ms:move,api,server_rss:after.WorkingSet64,server_idle_cpu_seconds:after.CPU-before.CPU,tab_heap_bytes:metrics.JSHeapUsedSize,tab_task_seconds_60s:metrics.TaskDuration-m0.TaskDuration,requests_60s:requests-q0,bytes_60s:bytes-b0,total_requests:requests,total_bytes:bytes,iframes_after_move:await page.locator('iframe').count()});
 await browser.close();cp.execFileSync('taskkill',['/PID',String(pid),'/F'],{stdio:'ignore'});server.kill();await sleep(1200);fs.writeFileSync(ev+'/'+phase+'.json',JSON.stringify(out,null,2));process.stdout.write(phase+' repetición '+(i+1)+' guardada\n');
 }})().catch(e=>{console.error(e);process.exit(1)});
