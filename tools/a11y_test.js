// 無障礙自動檢查（axe-core，WCAG 2.1 A／AA）：以本機伺服器開啟主要頁面，列出違規項目。
// 用法：npm i --no-save playwright @axe-core/playwright && node tools/a11y_test.js [--strict]
// 預設只報告、不擋下；加 --strict 時，有 critical 或 serious 違規就回傳錯誤碼。
const {chromium}=require('playwright');const {AxeBuilder}=require('@axe-core/playwright');
const http=require('http'),fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..');const STRICT=process.argv.includes('--strict');
const TYPES={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.json':'application/json','.woff2':'font/woff2','.xml':'application/xml'};
const srv=http.createServer((q,r)=>{let f=path.join(ROOT,decodeURIComponent(q.url.split('?')[0]));if(!f.startsWith(ROOT)){r.writeHead(403);return r.end();}
 if(fs.existsSync(f)&&fs.statSync(f).isDirectory())f=path.join(f,'index.html');
 fs.readFile(f,(e,b)=>{if(e){r.writeHead(404);return r.end();}r.writeHead(200,{'Content-Type':TYPES[path.extname(f)]||'application/octet-stream'});r.end(b);});});
(async()=>{await new Promise(ok=>srv.listen(0,ok));const B=`http://127.0.0.1:${srv.address().port}/`;
 const dash=fs.readdirSync(path.join(ROOT,'data')).filter(f=>f.endsWith('.html')).sort()[0];
 const pages=['index.html','index.html#calendar','index.html#companies','index.html#watch','index.html#search','index.html#about','index.html#c-2330',`data/${encodeURIComponent(dash)}`,'tsmc/index.html','c/2330/'];
 const b=await chromium.launch();let bad=0;const lines=[];
 for(const u of pages){const ctx=await b.newContext({viewport:{width:1440,height:900}});const p=await ctx.newPage();
  await p.goto(B+u);await p.waitForTimeout(1200);
  const r=await new AxeBuilder({page:p}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
  const v=r.violations;bad+=v.filter(x=>['critical','serious'].includes(x.impact)).length;
  lines.push(`${decodeURIComponent(u)}：${v.length?v.map(x=>`${x.id}（${x.impact}，${x.nodes.length} 處）`).join('、'):'無違規'}`);
  await ctx.close();}
 await b.close();srv.close();
 const out=['## 無障礙檢查（axe-core）','',...lines.map(l=>'- '+l),'',`critical／serious 違規：${bad} 項${STRICT?'':'（僅報告，不擋下）'}`].join('\n');
 console.log(out);if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,out+'\n');
 process.exitCode=STRICT&&bad?1:0;})().catch(e=>{console.error(e);process.exit(1);});
