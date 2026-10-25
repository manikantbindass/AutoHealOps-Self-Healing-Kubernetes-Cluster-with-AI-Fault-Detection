/* Real browser check of the explicitly simulated autonomous workflow. */
const {chromium}=require(require.resolve('playwright',{paths:[require('path').join(__dirname,'../frontend')]}));
const assert=require('node:assert/strict');
const path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})});
 try {
  const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[],traffic=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))traffic.push(r.url());});
  await page.goto(`${process.env.DASHBOARD_URL || 'http://localhost:13001'}/settings`,{waitUntil:'networkidle'});
  await page.getByLabel('Operating mode').selectOption('automatic');
  await page.getByRole('button',{name:'Save policy',exact:true}).click();
  await page.getByRole('link',{name:'Healing operations',exact:true}).click();
  await page.getByRole('button',{name:'Resume healing',exact:true}).click();
  await page.getByRole('link',{name:'Overview',exact:true}).click();
  await page.getByRole('button',{name:'CPU spike',exact:true}).click();
  await page.getByRole('link',{name:'Healing operations',exact:true}).click();
  await page.getByText('Simulated recovery only; no Kubernetes operation performed',{exact:true}).waitFor({timeout:25000});
  assert((await page.locator('.policy-bar').innerText()).includes('automatic'));
  assert.equal(await page.getByRole('button',{name:'Approve action',exact:true}).count(),0);
  await page.screenshot({path:path.join(__dirname,'../docs/screenshots/autohealops-autonomous.png'),fullPage:true});
  await page.locator('article.record').first().screenshot({path:path.join(__dirname,'../docs/screenshots/autohealops-autonomous-result.png')});
  await page.reload({waitUntil:'networkidle'});
  await page.getByRole('button',{name:'Resume healing',exact:true}).waitFor();
  await page.getByRole('link',{name:'Settings & integrations',exact:true}).click();
  await page.setViewportSize({width:390,height:844});
  await page.getByLabel('Operating mode').focus();
  assert(await page.getByLabel('Operating mode').evaluate(el=>el===document.activeElement));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(errors,[]);assert.deepEqual(traffic,[]);
  console.log('Autonomous browser simulation passed: automatic outcome, no approval, reload pause, keyboard focus, mobile width, no API traffic or browser errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
