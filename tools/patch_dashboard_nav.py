#!/usr/bin/env python3
"""讓單場儀表板左上角的 logo 能回到網站首頁（與 assets/template_motion.html 的同一段程式）。
已用新版模板產生的檔案會自動略過，可以重複執行。用法：python tools/patch_dashboard_nav.py data/*.html"""
import sys
MARK = "/* ec-site-nav */"
SNIP = MARK + """(function(){var b=document.querySelector('a.brand');if(!b)return;var t='回法說會大平台首頁';
if(window.top!==window){b.title=t;b.addEventListener('click',function(e){e.preventDefault();try{parent.postMessage({ec:'home'},'*');}catch(x){}});}
else if(/\\/data\\/[^\\/]+\\.html$/.test(decodeURIComponent(location.pathname))){b.href='../index.html';b.title=t;}})();
"""
n = 0
for p in sys.argv[1:]:
    h = open(p, encoding="utf-8").read()
    if MARK in h:
        continue
    i = h.rfind("</script>")
    if i < 0:
        print("略過（找不到 script）：" + p, file=sys.stderr)
        continue
    open(p, "w", encoding="utf-8").write(h[:i] + SNIP + h[i:])
    n += 1
print(f"已更新 {n} 個檔案")
