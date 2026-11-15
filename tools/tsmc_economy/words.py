import re,glob,json,csv,collections
TXT='/home/claude/tsmcdata/txt'
N=lambda n:rf'\b{n}[\s-]?(?:nm|nanometers?)\b'
W=[ # (label, theme, regex)
 ('PC','市場',r'\bPCs?\b'),('Notebook','市場',r'\bnotebooks?\b'),('Handset','市場',r'\bhandsets?\b'),('Smartphone','市場',r'\bsmart ?phones?\b'),
 ('Consumer','市場',r'\bconsumer\b'),('Tablet','市場',r'\btablets?\b'),('Server','市場',r'\bservers?\b'),('Data center','市場',r'\bdata ?cent(?:er|re)s?\b'),
 ('HPC','市場',r'\bHPC\b|high[\s-]performance computing'),('AI','市場',r'\bAI\b|artificial intelligence'),('GPU','市場',r'\bGPUs?\b'),
 ('Automotive','市場',r'\bautomotive\b'),('IoT','市場',r'\bIoT\b|internet of things'),('5G','市場',r'\b5G\b'),('Crypto','市場',r'\bcrypto\w*|\bmining\b'),('Digital TV','市場',r'\bdigital TVs?\b|\bDTV\b'),
 ('0.13µm','製程',r'0?\.13[\s-]?(?:micron|um|µm)'),('90nm','製程',N('90')),('65nm','製程',N('65')),('40nm','製程',N('4[05]')),('28nm','製程',N('28')),('20nm','製程',N('20')),
 ('16nm','製程',N('16')),('FinFET','製程',r'\bFinFETs?\b'),('10nm','製程',N('10')),('7nm','製程',N('7')+r'|\bN7\b'),('5nm','製程',N('5')+r'|\bN5\b'),('3nm','製程',N('3')+r'|\bN3[EP]?\b'),
 ('2nm','製程',N('2')+r'|\bN2P?\b'),('A16','製程',r'\bA16\b'),('A14','製程',r'\bA14\b'),('EUV','製程',r'\bEUV\b'),('12-inch','製程',r'\b12[\s-]?inch\b|\b300[\s-]?mm\b'),
 ('CoWoS','封裝',r'\bCoWoS\b'),('InFO','封裝',r'\bInFO\b'),('SoIC','封裝',r'\bSoIC\b'),('Advanced packaging','封裝',r'advanced packaging'),
 ('Inventory','景氣',r'\binventor(?:y|ies)\b'),('Utilization','景氣',r'\butili[sz]ation\b'),('Depreciation','景氣',r'\bdepreciation\b'),('Exchange rate','景氣',r'exchange rates?|\bNT dollar\b'),
 ('Dividend','景氣',r'\bdividends?\b'),('Pricing','景氣',r'\bpric(?:e|es|ing)\b'),('Recovery','景氣',r'\brecover(?:y|ies)\b'),('Downturn','景氣',r'\bdownturns?\b|\brecession\b'),
 ('SARS','事件',r'\bSARS\b'),('Financial crisis','事件',r'financial (?:crisis|tsunami)'),('Earthquake','事件',r'\bearthquakes?\b'),('COVID','事件',r'\bCOVID\b|pandemic'),
 ('Tariff','事件',r'\btariffs?\b'),('Geopolitics','事件',r'geopolitic\w*'),('Subsidy','事件',r'\bsubsid(?:y|ies)\b'),('Export control','事件',r'export controls?'),
 ('Arizona','版圖',r'\bArizona\b'),('Japan','版圖',r'\bJapan(?:ese)?\b|\bKumamoto\b'),('Germany','版圖',r'\bGermany\b|\bDresden\b'),('Nanjing','版圖',r'\bNanjing\b'),('Shanghai','版圖',r'\bShanghai\b|\bSongjiang\b'),('China','版圖',r'\bChina\b'),('Overseas','版圖',r'\boverseas\b'),
 ('Intel','競爭',r'\bIntel\b'),('Samsung','競爭',r'\bSamsung\b'),('Competition','競爭',r'\bcompetit(?:ion|ors?|ive)\b'),
]
G={'電腦':r'\bPCs?\b|\bnotebooks?\b|\bcomputers?\b|\bcomputing\b(?!.{0,3}high)','通訊':r'\bhandsets?\b|\bsmart ?phones?\b|\bcommunications?\b|\bmobile\b|\bcellular\b|\bwireless\b',
   '消費性':r'\bconsumer\b|\bdigital TVs?\b|\bgame consoles?\b|\bset[\s-]?top\b','HPC 與 AI':r'\bHPC\b|\bAI\b|\bdata ?cent(?:er|re)s?\b|\bservers?\b|\bGPUs?\b|\baccelerators?\b|artificial intelligence',
   '車用與物聯網':r'\bautomotive\b|\bIoT\b|internet of things|\bwearables?\b'}
def clean(t):
  t=re.sub(r'\n.*(?:Thomson|StreetEvents|Refinitiv|LSEG|Reuters|Republished|reproduced|permission|registered trademark|CallStreet|FINAL TRANSCRIPT|Event Date|EVENT DATE).*','\n',t)
  t=re.sub(r'(?i)corporate communications?|communications? division|director of communications?','',t)
  return t
cal={ (r['year'],r['quarter']):r['call_date'] for r in csv.DictReader(open('/home/claude/tsmcdata/raw/data/tsmc_calls.csv',encoding='utf-8-sig'))}
cal[('2026','1')]='2026-04-16';cal[('2026','2')]='2026-07-16';cal[('2026','3')]='2026-10-15'
out=[]
for f in sorted(glob.glob(TXT+'/TSMC_*.txt')):
  m=re.search(r'TSMC_(\d{4})Q(\d)',f);y,q=m.group(1),m.group(2)
  t=clean(open(f,encoding='utf-8',errors='ignore').read());nw=len(re.findall(r'[A-Za-z]+',t)) or 1
  c={lab:len(re.findall(rx,t,re.I if lab not in('AI','PC','HPC','IoT','GPU','EUV','InFO','SoIC','CoWoS','SARS','A16','A14','5G','Intel','Samsung','Server') else 0)) for lab,th,rx in W}
  g={k:len(re.findall(rx,t,re.I if k!='HPC 與 AI' else 0)) for k,rx in G.items()}
  out.append({'y':int(y),'q':int(q),'d':cal.get((y,q),''),'nw':nw,'c':{k:v for k,v in c.items() if v},'g':g})
json.dump({'words':[[a,b] for a,b,_ in W],'calls':out},open('/home/claude/tsmcdata/build/words.json','w'),ensure_ascii=False)
dom=collections.Counter(max(o['g'],key=o['g'].get) for o in out);print(len(out),dom)
for o in out[::6]: print(o['y'],o['q'],o['d'],max(o['g'],key=o['g'].get),o['g'],sorted(o['c'].items(),key=lambda x:-x[1])[:6])
