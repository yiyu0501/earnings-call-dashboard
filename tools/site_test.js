// 網站自動回歸測試：走訪首頁、各公司頁、各場儀表板、搜尋、行事曆、關於、小額支持，檢查錯誤訊息與版面。
// 用法：npm i playwright && npx playwright install chromium && node tools/site_test.js
const {chromium}=require('playwright');const fs=require('fs');
const ROOT=require('path').resolve(__dirname,'..')+'/';const base='file://'+ROOT+'index.html';
const fails=[];const ok=(c,m)=>{if(!c)fails.push(m);};
const J=f=>{const s=fs.readFileSync(ROOT+f,'utf8');return JSON.parse(s.slice(s.indexOf('{'),s.lastIndexOf('}')+1));};
(async()=>{const b=await chromium.launch();const IDX=J('index.js'),U=J('universe.js');
 const ALL=IDX.companies.flatMap(c=>c.sessions.map(s=>({c,s})));
 const ids=new Set(ALL.map(({c,s})=>'#s-'+c.ticker+'-'+s.key.replace(/[^0-9A-Za-z]/g,'')));
 const LEAD=new Set(Object.values(U.industries).flat());
 const ctx=await b.newContext({viewport:{width:1440,height:900}});const p=await ctx.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
 p.on('requestfailed',r=>errs.push('reqfail '+decodeURIComponent(r.url())));
 await p.goto(base);await p.waitForTimeout(1200);
 ok((await p.textContent('.hero h1'))==='法說會大平台','title');ok((await p.title()).startsWith('法說會大平台'),'doc title');ok((await p.textContent('.brand b'))==='法說會大平台','brand');
 ok(!(await p.content()).includes('一頁看懂重點'),'old title gone');
 // LED inside hero, calm colors
 ok(await p.$('.hero .led-cv')!==null,'led in hero');const lh=await p.$eval('.led-cv',c=>c.getBoundingClientRect().height);ok(lh<=32,'led slim '+lh);
 // intro numbers
 const nU=Object.keys(U.companies).length,nC=Object.values(U.companies).reduce((a,c)=>a+c.c.length,0);ok((await p.textContent('.intro-stats')).includes(`${nU}家公司`)&&(await p.textContent('.intro-stats')).includes(`${nC}場法說會`),'intro universe');
 // autocomplete
 await p.fill('.sbar input','中鋼');await p.waitForTimeout(200);ok(await p.isVisible('.ac'),'ac visible');
 const rows=await p.$$eval('.ac-main b',x=>x.map(e=>e.textContent));ok(rows[0]==='中鋼','ac first '+rows);
 const box=await p.$eval('.ac',e=>{const r=e.getBoundingClientRect();const el=document.elementFromPoint(r.left+20,r.bottom-10);return e.contains(el);});ok(box,'ac not clipped');
 await p.click('.ac-row:has-text("中鋼") .star');ok((await p.evaluate(()=>JSON.parse(localStorage.getItem('ec_follow')))).includes('2002'),'follow saved');
 await p.click('.ac-main:has-text("中鋼")');await p.waitForTimeout(400);ok(await p.evaluate(()=>location.hash)==='#calendar','ac -> calendar');
 ok((await p.textContent('.cal-det')).includes('中鋼'),'detail shown');ok((await p.textContent('.cal-det')).includes('2026 年 6 月 24 日'),'detail date');
 // calendar: default leaders + analyzed + followed
 await p.goto(base+'#calendar');await p.waitForTimeout(400);
 const shown=await p.$$eval('.mg .dc:not(.out) .ev,.mg .dc:not(.out) .evmore',x=>x.length);ok(shown>0,'calendar events');
 const opts=await p.$$eval('.isel option',x=>x.map(o=>o.textContent));ok(opts.length>=19,'industry options '+opts.length);
 const tot=+opts[0].match(/（(\d+)）/)[1];
 const exp=new Set();ALL.forEach(({c,s})=>{if(/^\d{4}-\d\d-\d\d$/.test(s.date))exp.add(c.ticker+'|'+s.date);});
 Object.entries(U.companies).forEach(([code,co])=>{if(LEAD.has(code)||code==='2002')co.c.forEach(k=>exp.add(code+'|'+k.d.slice(0,4)+'-'+k.d.slice(4,6)+'-'+k.d.slice(6,8)));});
 ok(tot===exp.size,'calendar total '+tot+' vs '+exp.size);
 await p.selectOption('.isel select','航運');await p.waitForTimeout(200);ok((await p.$$eval('.mg .ev',x=>x.length))>=0,'filter ok');
 await p.check('.folt input');await p.waitForTimeout(200);const fo=await p.$$eval('.isel option',x=>x.map(o=>o.textContent));ok(/全部產業（1）/.test(fo[0]),'only followed '+fo[0]);
 await p.uncheck('.folt input');await p.selectOption('.isel select','');
 // click todo event -> detail; done event -> dashboard
 await p.click('.cal-jump .fchip:has-text("8 月")');const t=await p.$('.mg .ev.todo');await t.click();await p.waitForTimeout(200);ok(await p.$('.cal-det')!==null,'todo detail');
 await p.click('.mg .ev.done');await p.waitForTimeout(300);ok(ids.has(await p.evaluate(()=>location.hash)),'done -> dashboard');
 // industry tile -> calendar filtered
 await p.goto(base);await p.waitForTimeout(500);await p.click('.itile:has-text("金融保險")');await p.waitForTimeout(400);ok(await p.evaluate(()=>location.hash)==='#calendar'&&(await p.$eval('.isel select',s=>s.value))==='金融保險','tile -> calendar filter');
 // my follow tab
 await p.goto(base);await p.waitForTimeout(500);await p.click('.ptabs button:has-text("我的關注")');const fi=await p.$$eval('.pitem',x=>x.map(a=>a.textContent));ok(fi.length===1&&fi[0].includes('中鋼'),'follow tab '+fi);
 await p.click('#menu');await p.click('.cocard[data-tk="2330"] .star');await p.keyboard.press('Escape');await p.waitForTimeout(200);
 ok((await p.$$eval('.pitem',x=>x.length))>1,'follow tab updates live');ok((await p.textContent('.ptabs .fcount')).trim()==='2','follow count');
 // company page star
 await p.goto(base+'#c-2330');await p.waitForTimeout(200);ok((await p.textContent('.fbar')).includes('台積電經濟體'),'economy page');
 // routes
 for(const id of ids){await p.goto(base+id);await p.waitForTimeout(80);const src=await p.getAttribute('iframe','src');ok(src&&fs.existsSync(ROOT+decodeURIComponent(src)),'iframe '+id);}
 for(const c of IDX.companies){await p.goto(base+'#c-'+c.ticker);await p.waitForTimeout(60);ok((await p.textContent('.phead h1, .fbar')).includes(c.name),'company '+c.ticker);}
 for(const r of ['calls','search','about']){await p.goto(base+'#'+r);await p.waitForTimeout(150);ok(await p.$('.phead h1')!==null,'page '+r);}
 // search kw
 await p.goto(base);await p.waitForTimeout(400);await p.fill('.sbar input','資本支出');await p.press('.sbar input','Enter');await p.waitForTimeout(400);ok((await p.$$eval('.res',x=>x.length))>0,'search');
 ok(await p.evaluate(()=>{const s=[...document.querySelectorAll('[id]')].map(e=>e.id);return s.length===new Set(s).size;}),'unique ids');
 for(const w of [390,768,1024,1440]){const q=await b.newPage({viewport:{width:w,height:900}});q.on('pageerror',e=>errs.push(w+' '+e.message));
   for(const r of ['','calls','calendar','search','about','c-2330']){await q.goto(base+'#'+r);await q.waitForTimeout(300);
     const o=await q.evaluate(()=>{const m=document.querySelector('#main');return {doc:document.documentElement.scrollWidth>innerWidth+1,main:m.scrollWidth>m.clientWidth+1};});ok(!o.doc&&!o.main,`overflow ${w} #${r}`);}
   await q.close();}
 // without universe.js (local mode) still works
 const z=await b.newPage();const ze=[];z.on('pageerror',e=>ze.push(e.message));await z.route(/universe\.js/,r=>r.abort());await z.goto(base);await z.waitForTimeout(600);await z.goto(base+'#calendar');await z.waitForTimeout(300);ok(ze.length===0&&(await z.$$eval('.ev',x=>x.length))>0,'no-universe ok '+ze);
 ok(errs.length===0,'errors '+JSON.stringify(errs));
 console.log(fails.length?'FAIL\n'+fails.join('\n'):'ALL PASS');await b.close();})();
