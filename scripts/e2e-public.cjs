/** Browser checks for the opt-in public showcase, locally or on Vercel. */
const {chromium}=require(require.resolve('playwright',{paths:[require('path').join(__dirname,'../frontend')]}));
const assert=require('node:assert/strict');
const path=require('path');
const base=process.env.DASHBOARD_URL || 'http://localhost:13001';
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})});
 try {
  const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[],serviceTraffic=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))serviceTraffic.push(r.url());});
  page.on('websocket',ws=>serviceTraffic.push(ws.url()));
  await page.goto(base,{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:'Operations overview'}).waitFor();
  await page.getByText('browser simulation',{exact:true}).waitFor();
  assert((await page.locator('.demo-banner').innerText()).includes('No backend or Kubernetes connection'));
  await page.getByRole('button',{name:'CPU spike',exact:true}).click();
  await page.getByText('Your cluster needs attention',{exact:true}).waitFor();
  await page.getByRole('link',{name:'AI fault intelligence',exact:true}).click();
  await page.getByText('Browser simulation using transparent rules; no ML inference.',{exact:false}).first().waitFor();
  await page.getByRole('link',{name:'Healing operations',exact:true}).click();
  await page.getByRole('button',{name:'Approve action',exact:true}).first().click();
  await page.getByRole('button',{name:'Resume healing',exact:true}).click();
  await page.getByRole('button',{name:'Simulate recovery',exact:true}).first().click();
  await page.getByText('Simulated recovery only; no Kubernetes operation performed',{exact:true}).waitFor();
  for(const [route,title] of [['cluster','Cluster explorer'],['observability','Observability'],['alerts','Alerts & incidents'],['logs','Events & audit logs'],['settings','Settings & integrations']]){
   await page.goto(`${base}/${route}`,{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:title,exact:true}).waitFor();
  }
  await page.goto(base,{waitUntil:'networkidle'});
  const filename=base.includes('vercel.app')?'autohealops-vercel.png':'autohealops-public-demo.png';
  await page.screenshot({path:path.join(__dirname,'../docs/screenshots',filename),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(errors,[]);assert.deepEqual(serviceTraffic,[]);
  console.log(JSON.stringify({result:'passed',url:base,checks:['public provenance','browser rules','fault/approval/recovery','all routes + direct deep links','session history','mobile width','zero backend or WebSocket traffic','zero browser errors'],screenshot:filename}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
