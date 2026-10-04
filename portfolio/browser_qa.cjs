const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('fs');
(async()=>{
 const out=path.resolve(process.argv[3] || '.github/portfolio/qa/P002'); fs.mkdirSync(out,{recursive:true});
 const base=process.argv[2] || 'http://127.0.0.1:8873';
 const browser=await chromium.launch({headless:true});
 const config=JSON.parse(fs.readFileSync(path.join(__dirname,'sites.json')));
 const sites=[...config.sites,...config.aliases];
 const results=[];
 for(const width of [1440,390,320]) for(const site of sites){
  const page=await browser.newPage({viewport:{width,height:900}}); const errors=[];
  page.on('pageerror',e=>errors.push(e.message)); page.on('console',m=>{if(m.type()==='error') errors.push(m.text())});
  await page.goto(`${base}/${site.domain}/`,{waitUntil:'networkidle'});
  const overflow=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,offenders:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>e.tagName+'.'+e.className).slice(0,10)}));
  await page.locator('.skip').focus();
  const keyboard=await page.evaluate(()=>({text:document.activeElement.textContent,outline:getComputedStyle(document.activeElement).outlineStyle}));
  await page.keyboard.press('Enter'); await page.waitForURL('**/#main');
  const skip=await page.evaluate(()=>document.activeElement.id);
  const faqs=page.locator('summary'); for(let i=0;i<await faqs.count();i++){await faqs.nth(i).focus();await page.keyboard.press('Enter');if(!await faqs.nth(i).evaluate(e=>e.parentElement.open))errors.push('FAQ keyboard failed');await page.keyboard.press('Enter');}
  const checks={};
  checks.secondaryColors=await page.locator('.button.secondary').evaluateAll(els=>els.map(e=>({text:getComputedStyle(e).color,background:getComputedStyle(document.body).backgroundColor})));
  assert.ok(checks.secondaryColors.every(c=>c.text!==c.background),'secondary text visible');
  if(await page.locator('[data-walk-calculator]').count()){await page.selectOption('#walk-duration','60');await page.selectOption('#walk-count','5');checks.estimate=await page.locator('[data-total]').textContent();}
  if(await page.locator('[data-filters]').count()){checks.filters=[];for(const key of ['parks','patios','travel','all']){await page.locator(`[data-filter="${key}"]`).focus();await page.keyboard.press('Enter');checks.filters.push([key,await page.locator('[data-category]:visible').count(),await page.locator(`[data-filter="${key}"]`).getAttribute('aria-pressed')]);}}
  if(await page.locator('[data-workflow]').count()){checks.planner={};for(const key of ['leads','reports','scheduling','bookkeeping']){await page.selectOption('#workflow',key);checks.planner[key]=await page.locator('[data-workflow-output]').textContent();}}
  if(await page.locator('textarea').count()){await page.locator('textarea').first().fill(Array.from({length:40},(_,i)=>'Synthetic QA line '+(i+1)).join('\n')); await page.evaluate(()=>{window.print=()=>window.__printed=true});await page.locator('[data-print]').click();checks.printCalled=await page.evaluate(()=>window.__printed===true);await page.emulateMedia({media:'print'});checks.printFields=await page.locator('.print-value:visible').count();assert.equal(checks.printFields,3);assert.ok((await page.locator('.print-value').first().textContent()).includes('Synthetic QA line 40'));if(width===1440)await page.pdf({path:`${out}/${site.domain}-print.pdf`,format:'A4'});await page.emulateMedia({media:'screen'});await page.locator('[data-clear-worksheet]').click(); checks.clearWorks=await page.locator('textarea').first().inputValue()==='' && await page.locator('.print-value').first().textContent()==='';assert.ok(checks.clearWorks);await page.reload();checks.reloadCleared=await page.locator('textarea').first().inputValue()==='';}
  await page.evaluate(()=>{document.activeElement.blur();scrollTo(0,0)});
  if(width!==320)await page.screenshot({path:`${out}/${site.domain}-${width}.png`,fullPage:true});
  assert.equal(skip,'main'); assert.equal(keyboard.outline,'solid');assert.equal(overflow.scroll,width);assert.deepEqual(errors,[]);if(checks.estimate)assert.equal(checks.estimate,'$175 / week');if(checks.filters)assert.deepEqual(checks.filters.map(x=>x[1]),[1,1,1,3]);
  results.push({domain:site.domain,width,overflow,keyboard,skip,errors,checks});await page.close();
 }
 fs.writeFileSync(`${out}/browser-results.json`,JSON.stringify({browser:browser.version(),results},null,2));await browser.close();
 console.log('Passed '+results.length+' domain/viewport combinations; screenshots and print PDFs: '+out);
})();
