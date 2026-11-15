# 把 tpl.html 和資料組成 tsmc/index.html。需要先執行 geo.mjs 產生 geo.json、events.json（這兩個檔案不放進儲存庫）。
import json, os
HERE=os.path.dirname(os.path.abspath(__file__))
P=lambda f:os.path.join(HERE,f)
d={'geo':json.load(open(P('geo.json'))),'ev':json.load(open(P('events.json'))),'fin':json.load(open(P('fin.json'))),'words':json.load(open(P('words.json')))}
s=open(P('tpl.html'),encoding='utf-8').read().replace('__DATA__',json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
out=os.path.join(HERE,'..','..','tsmc','index.html')
open(out,'w',encoding='utf-8').write(s);print(len(s)//1024,'KB →',os.path.normpath(out))
