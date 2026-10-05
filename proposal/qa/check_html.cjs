const { chromium } = require('/Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');
const path=require('path');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 await page.goto('file://'+root+'/thesis_proposal.html');
 await page.evaluate(()=>document.fonts.ready);
 const result=await page.evaluate(()=>({
  images:[...document.images].map(x=>({src:x.getAttribute('src'),ok:x.complete&&x.naturalWidth>0})),
  pages:[...document.querySelectorAll('.page')].map(x=>{
   const foot=x.querySelector('.foot');const content=[...x.children].filter(y=>!y.classList.contains('foot')&&!y.classList.contains('running'));
   return {id:x.id,width:x.clientWidth,scrollWidth:x.scrollWidth,footerGap:foot?foot.getBoundingClientRect().top-Math.max(...content.map(y=>y.getBoundingClientRect().bottom)):null};
  }),
  brokenAnchors:[...document.querySelectorAll('a[href^="#"]')].map(a=>a.getAttribute('href')).filter(h=>!document.getElementById(h.slice(1))),
  equations:document.querySelectorAll('.equation').length,
  tables:document.querySelectorAll('table').length
 }));
 await page.locator('.toolbar').evaluate(e=>e.style.visibility='hidden');
 await page.locator('#page-measures').screenshot({path:root+'/qa/revision_render/html-equations.png'});
 await page.locator('.toolbar').evaluate(e=>e.style.visibility='visible');
 await page.setViewportSize({width:390,height:844});
 result.mobile=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth,equationWidths:[...document.querySelectorAll('.equation')].map(e=>({width:e.clientWidth,scrollWidth:e.scrollWidth}))}));
 fs.writeFileSync(root+'/qa/html_checks.json',JSON.stringify(result,null,2));
 console.log(JSON.stringify(result,null,2));
 await browser.close();
})();
