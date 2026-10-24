/* Real browser integration: uses the running API; no mocked metrics or screenshots. */
const path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || require.resolve('playwright',{paths:[path.join(__dirname,'../frontend')]}));
const assert=require('node:assert/strict');
const fs=require('fs');
const base=process.env.DASHBOARD_URL || 'http://localhost:3000';
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})});
  try {
    const page=await browser.newPage({viewport:{width:1600,height:1100},deviceScaleFactor:1});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base,{waitUntil:'networkidle'});
    await page.getByRole('heading',{name:'Operations overview'}).waitFor();
    await page.getByText('Live updates',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Reset scenario',exact:true}).click();
    await page.getByRole('button',{name:'CPU spike',exact:true}).click();
    await page.getByText('Your cluster needs attention',{exact:true}).waitFor();
    await page.getByRole('link',{name:'AI fault intelligence',exact:true}).click();
    await page.getByRole('heading',{name:'Detection evidence'}).waitFor();
    assert((await page.locator('body').innerText()).includes('cpu_usage'));
    fs.mkdirSync(path.join(__dirname,'../docs/screenshots'),{recursive:true});
    await page.screenshot({path:path.join(__dirname,'../docs/screenshots/autohealops-intelligence.png'),fullPage:true});
    await page.getByRole('link',{name:'Healing operations',exact:true}).click();
    await page.getByRole('button',{name:'Approve action',exact:true}).first().click();
    if(await page.getByRole('button',{name:'Resume healing',exact:true}).count()) await page.getByRole('button',{name:'Resume healing',exact:true}).click();
    const policy=await (await page.request.get(base+'/api/v1/settings')).json();
    const prior=await (await page.request.get(base+'/api/v1/healing/actions')).json();
    const latest=prior.items.filter(x=>x.target==='checkout-service' && x.executed_at).sort((a,b)=>Date.parse(b.executed_at)-Date.parse(a.executed_at))[0];
    const cooldownWait=latest ? Math.max(0,policy.cooldown_seconds*1000-(Date.now()-Date.parse(latest.executed_at))+500) : 0;
    if(cooldownWait){console.log(`Honoring configured safety cooldown: ${Math.ceil(cooldownWait/1000)}s`);await page.waitForTimeout(cooldownWait);}
    await page.getByRole('button',{name:'Simulate recovery',exact:true}).first().click();
    await page.getByText('Simulated recovery only; no Kubernetes operation performed',{exact:true}).first().waitFor();
    await page.screenshot({path:path.join(__dirname,'../docs/screenshots/autohealops-healing.png'),fullPage:true});
    await page.getByRole('link',{name:'Cluster explorer',exact:true}).click();
    await page.getByRole('button',{name:'Inspect',exact:true}).first().click();
    await page.getByRole('dialog').waitFor();
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('dialog').count(),0);
    await page.screenshot({path:path.join(__dirname,'../docs/screenshots/autohealops-cluster.png'),fullPage:true});
    for(const [link,heading] of [['Observability','Observability'],['Alerts & incidents','Alerts & incidents'],['Event & audit logs','Events & audit logs'],['Settings & integrations','Settings & integrations']]){
      await page.getByRole('link',{name:link,exact:link !== 'Alerts & incidents'}).click();await page.getByRole('heading',{name:heading,exact:true}).waitFor();
    }
    await page.getByRole('link',{name:'Overview',exact:true}).click();
    await page.getByRole('heading',{name:'Operations overview'}).waitFor();
    await page.screenshot({path:path.join(__dirname,'../docs/screenshots/autohealops-dashboard.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(__dirname,'../docs/screenshots/autohealops-mobile.png'),fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Mobile page must not overflow horizontally');
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({result:'passed',checks:['8 routes','live websocket','synthetic fault detection','approval','simulated recovery','resource dialog + Escape','mobile width','no browser errors'],screenshots:5}));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
