import json
geo=json.load(open('/home/claude/tsmcdata/geo/geo.json'));ev=json.load(open('/home/claude/tsmcdata/geo/events.json'))
d={'geo':geo,'ev':ev,'fin':json.load(open('fin.json')),'words':json.load(open('words.json'))}
s=open('tpl.html',encoding='utf-8').read().replace('__DATA__',json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
import os;os.makedirs('/home/claude/tsmcdata/sketch',exist_ok=True)
open('/home/claude/tsmcdata/sketch/tsmc.html','w',encoding='utf-8').write(s);print(len(s)//1024,'KB')
