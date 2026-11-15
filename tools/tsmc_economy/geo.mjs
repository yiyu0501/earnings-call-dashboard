import fs from 'fs';import {geoMercator,geoPath} from 'd3-geo';import * as topo from 'topojson-client';import {presimplify,simplify,quantile} from 'topojson-simplify';
let w50=JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-50m.json'));w50=presimplify(w50);w50=simplify(w50,quantile(w50,.35));
let tw=JSON.parse(fs.readFileSync('node_modules/taiwan-atlas/counties-10t.json'));tw=presimplify(tw);tw=simplify(tw,quantile(tw,.4));
const W=24000,H=15000;
const proj=geoMercator().scale(W/(2*Math.PI)).translate([W/2,H/2+ (W/(2*Math.PI))*Math.log(Math.tan(Math.PI/4+ (12*Math.PI/180)/2))]).precision(.2).rotate([-150,0]);
const P=geoPath(proj);const rd=s=>s.replace(/(\d+)\.\d+/g,(m)=>String(Math.round(+m))).replace(/L(-?\d+),(-?\d+)(?=L\1,\2)/g,'');
const land=topo.feature(w50,w50.objects.land);const borders=topo.mesh(w50,w50.objects.countries,(a,b)=>a!==b);
const twc=topo.feature(tw,tw.objects.counties);const twm=topo.mesh(tw,tw.objects.counties,(a,b)=>a!==b);
const out={W,H,land:rd(P(land)),borders:rd(P(borders)),tw:rd(P(topo.feature(tw,tw.objects.counties))),twb:rd(P(twm))};
const pt=(lon,lat)=>proj([lon,lat]).map(v=>+v.toFixed(2));
out.ref={taiwan:pt(120.97,23.7),hsinchu:pt(120.97,24.8)};out.twbox=[...pt(119.9,25.4),...pt(122.1,21.8)];
fs.writeFileSync('geo.json',JSON.stringify(out));
for(const k of ['land','borders','tw','twb'])console.log(k,out[k].length);
// project events
const csv=fs.readFileSync('/home/claude/tsmcdata/raw/data/tsmc_footprint.csv','utf8').replace(/^﻿/,'').trim().split('\n');
const hd=csv[0].split(',');const parse=l=>{const r=[];let c='',q=false;for(const ch of l){if(ch=='"'){q=!q;continue;}if(ch==','&&!q){r.push(c);c='';}else c+=ch;}r.push(c);return r;};
const ev=csv.slice(1).map(l=>{const v=parse(l),o={};hd.forEach((h,i)=>o[h]=v[i]);return o;}).filter(o=>o.lat&&o.lon).map(o=>({d:o.date,n:o.site_name,c:o.city,co:o.country,t:o.type,e:o.event,z:o.description_zh,u:o.source_url,p:pt(+o.lon,+o.lat)}));
fs.writeFileSync('events.json',JSON.stringify(ev));console.log('events',ev.length, ev[0].p, out.ref);
