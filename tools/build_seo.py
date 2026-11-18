"""產生給搜尋引擎與社群預覽用的靜態頁面與網站地圖。

網站本身用 #c-2330 這類網址切換頁面，搜尋引擎不會把各公司頁分開收錄。
這支程式依 index.js 為每家公司產生一頁靜態 HTML（c/<代號>/index.html），
內容是各場法說會的摘要、財務指引與關鍵數據（附原句），並產生 sitemap.xml。

用法（在儲存庫根目錄）：
    python tools/build_seo.py

GitHub Actions 每次發布前都會執行，不必手動。網址與流量統計代碼讀自
skill/earnings-call-dashboard/assets/integrated_template.html 開頭的 SITE 設定。
"""
import html, json, os, re, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE = os.path.join(ROOT, "skill", "earnings-call-dashboard", "assets", "integrated_template.html")
E = lambda x: html.escape(str(x if x is not None else ""), quote=True)
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: https://*.goatcounter.com; object-src 'none'; base-uri 'self'; form-action 'self'")
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' "
        "fill='%230b2140'/%3E%3Crect x='14' y='34' width='8' height='16' rx='2' fill='%237fb6e6'/%3E%3Crect x='28' y='24' width='8' "
        "height='26' rx='2' fill='%234d9ee0'/%3E%3Crect x='42' y='14' width='8' height='36' rx='2' fill='%23ffffff'/%3E%3C/svg%3E")
CSS = """
:root{--ink:#1d2733;--grey:#5d6b7c;--line:#dfe5ec;--bg:#f6f8fb;--surface:#fff;--primary:#1766b8;--navy:#0b2140;--up:#d6303c;--down:#139a5b}
@media (prefers-color-scheme:dark){:root{--ink:#e6ebf2;--grey:#a3afbf;--line:#2a3442;--bg:#0f141b;--surface:#171e27;--primary:#4d9ee0;--navy:#a9c3e6;--up:#ff6b74;--down:#3ccf8e}}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;color:var(--ink);background:var(--bg);line-height:1.7}
a{color:var(--primary)}header{background:var(--surface);border-bottom:1px solid var(--line)}
.in{max-width:980px;margin:0 auto;padding:0 20px}header .in{display:flex;align-items:center;gap:12px;height:60px}
header a.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);font-weight:800}header img{height:30px}
.crumb{font-size:13px;color:var(--grey);margin:22px 0 4px}h1{font-size:30px;margin:0 0 6px;line-height:1.3}
.lead{color:var(--grey);margin:0 0 16px}.cta{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 26px}
.btn{display:inline-flex;align-items:center;height:42px;padding:0 18px;border-radius:999px;font-weight:700;text-decoration:none;border:1px solid var(--line);background:var(--surface);color:var(--ink)}
.btn.p{background:var(--primary);border-color:var(--primary);color:#fff}
section{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin:0 0 18px}
h2{font-size:20px;margin:0 0 4px}.meta{font-size:13px;color:var(--grey);margin:0 0 12px}.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:0 9px;font-size:12.5px;margin-left:6px}
h3{font-size:15px;margin:18px 0 8px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12.5px;color:var(--grey);font-weight:700}td.k{font-weight:700;white-space:nowrap}td:nth-child(2),td:last-child,th:last-child{white-space:nowrap}.q{display:block;font-size:12.5px;color:var(--grey);margin-top:3px}
.up{color:var(--up);font-weight:700}.down{color:var(--down);font-weight:700}.more{margin:12px 0 0;font-size:14px}
footer{border-top:1px solid var(--line);margin-top:30px;padding:18px 0 34px;font-size:13px;color:var(--grey)}footer a{margin-right:14px}
@media (max-width:640px){h1{font-size:24px}section{padding:16px}td.k{white-space:normal}}
"""


def load_index():
    s = open(os.path.join(ROOT, "index.js"), encoding="utf-8").read()
    return json.loads(s[s.index("{"): s.rindex("}") + 1])


def site_setting(name, default=""):
    t = open(TEMPLATE, encoding="utf-8").read()
    if name == "goatcounter":
        m = re.search(r"analytics:\{goatcounter:'([a-z0-9-]*)'\}", t)
    else:
        m = re.search(r"\n  url:'(https://[^']+)'", t)
    return m.group(1) if m else default


def label(s):
    if s.get("year") and s.get("quarter"):
        return f"{s['year']} 年第 {s['quarter']} 季法說會"
    return f"{s.get('date') or s.get('key')} 法說會"


def rev(v):
    if v == "上修":
        return '<span class="up">▲ 上修</span>'
    if v == "下修":
        return '<span class="down">▼ 下修</span>'
    return E(v)


def session_html(s, up):
    out = [f'<section id="{E(s["key"])}"><h2>{E(label(s))}</h2>',
           f'<p class="meta">{E(s.get("date", ""))}'
           + (f'<span class="chip">整體評價：{E(s["rating"])}</span>' if s.get("rating") else "")
           + "".join(f'<span class="chip">{E(f)}</span>' for f in s.get("flags", [])) + "</p>"]
    if s.get("summary"):
        out.append(f"<p>{E(s['summary'])}</p>")
    if s.get("conclusion"):
        out.append(f"<p>{E(s['conclusion'])}</p>")
    ol = s.get("outlook") or []
    if ol:
        out.append('<h3>財務指引</h3><table><thead><tr><th>項目</th><th>期間</th><th>內容</th><th>與上一場相比</th></tr></thead><tbody>')
        for o in ol:
            q = f'<span class="q">原文：{E(o["quote"])}</span>' if o.get("quote") else ""
            out.append(f'<tr><td class="k">{E(o.get("topic"))}</td><td>{E(o.get("period"))}</td><td>{E(o.get("value"))}{q}</td><td>{rev(o.get("vs_prior", ""))}</td></tr>')
        out.append("</tbody></table>")
    kd = s.get("key_data") or []
    if kd:
        out.append('<h3>關鍵數據</h3><table><thead><tr><th>項目</th><th>期間</th><th>數值</th><th>變化</th></tr></thead><tbody>')
        for k in kd:
            q = f'<span class="q">原文：{E(k["quote"])}</span>' if k.get("quote") else ""
            out.append(f'<tr><td class="k">{E(k.get("metric"))}</td><td>{E(k.get("period"))}</td><td>{E(k.get("value"))}{q}</td><td>{E(k.get("change"))}</td></tr>')
        out.append("</tbody></table>")
    out.append(f'<p class="more"><a href="{up}{E(s["path"])}">打開這場的完整儀表板（問答、語調、關鍵詞與報告稿）</a></p></section>')
    return "\n".join(out)


def company_page(c, base, gc, economy):
    tk, name = c["ticker"], c["name"]
    ss = sorted(c["sessions"], key=lambda s: s.get("date") or "", reverse=True)
    latest = ss[0]
    url = f"{base}c/{tk}/"
    title = f"{name}（{tk}）法說會重點與財務指引｜法說會大平台"
    desc = (latest.get("summary") or f"{name}法說會的摘要、財務指引與關鍵數據，每一項皆附逐字稿原句。")
    desc = desc if len(desc) <= 150 else desc[:148] + "…"
    up = "../../"
    ld = {"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url, "description": desc,
          "inLanguage": "zh-Hant-TW", "isPartOf": {"@type": "WebSite", "name": "法說會大平台", "url": base},
          "about": {"@type": "Corporation", "name": name, "tickerSymbol": tk},
          "dateModified": latest.get("date") or ""}
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    pixel = (f'<img src="https://{gc}.goatcounter.com/count?p=/c/{tk}/" alt="" width="1" height="1" style="position:absolute">'
             if gc else "")
    cta = [f'<a class="btn p" href="{up}#c-{E(tk)}">在法說會大平台查看互動版</a>',
           f'<a class="btn" href="{up}{E(latest["path"])}">最新一場儀表板</a>']
    if tk in economy:
        cta.insert(1, f'<a class="btn" href="{up}{E(economy[tk])}">{E(name)}經濟體</a>')
    body = "\n".join(session_html(s, up) for s in ss)
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(url)}">
<link rel="icon" href="{ICON}">
<meta property="og:type" content="article"><meta property="og:locale" content="zh_TW">
<meta property="og:title" content="{E(name)}（{E(tk)}）法說會重點｜法說會大平台">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{E(url)}"><meta property="og:image" content="{E(base)}og.jpg">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld_json}</script>
<style>{CSS}</style></head><body>
<header><div class="in"><a class="brand" href="{up}"><img src="{up}tej_mark.png" alt="">法說會大平台</a></div></header>
<main class="in">
<p class="crumb"><a href="{up}">法說會大平台</a> ／ {E(c.get("industry") or "公司")} ／ {E(name)}</p>
<h1>{E(name)}（{E(tk)}）法說會重點</h1>
<p class="lead">{E(c.get("industry") or "")}{"｜" if c.get("industry") else ""}共 {len(ss)} 場法說會，最新一場為 {E(latest.get("date", ""))}。每一項財務指引與關鍵數據皆附逐字稿原句。</p>
<div class="cta">{"".join(cta)}</div>
{body}
</main>
<footer><div class="in"><p>資料來源：TEJ 逐字稿資料庫{"、台積電投資人關係網站" if tk in economy else ""}。內容經 AI 整理及程式核對，僅供研究參考，不構成投資建議。</p>
<p><a href="{up}">首頁</a><a href="{up}#about">關於本站</a><a href="{up}#feedback">意見回饋</a><a href="{up}#terms">使用條款</a></p>
<p>© 2026 法說會大平台　台灣經濟新報（TEJ）</p></div></footer>{pixel}
</body></html>
"""


def main():
    idx = load_index()
    base = site_setting("url", "https://yiyu0501.github.io/earnings-call-dashboard/")
    if not base.endswith("/"):
        base += "/"
    gc = site_setting("goatcounter")
    t = open(TEMPLATE, encoding="utf-8").read()
    economy = dict(re.findall(r"'(\w+)':'(tsmc/index\.html)'", t))
    out_dir = os.path.join(ROOT, "c")
    keep = {c["ticker"] for c in idx["companies"]}
    if os.path.isdir(out_dir):  # 已經不在網站上的公司，刪掉它的靜態頁（沒有刪除權限時略過）
        for old in os.listdir(out_dir):
            if old not in keep:
                shutil.rmtree(os.path.join(out_dir, old), ignore_errors=True)
    urls = [(base, idx.get("generated", "")[:10], "1.0")]
    n = 0
    for c in idx["companies"]:
        if not re.fullmatch(r"[0-9A-Za-z]+", c["ticker"]) or not c["sessions"]:
            continue
        d = os.path.join(out_dir, c["ticker"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(company_page(c, base, gc, economy))
        last = max((s.get("date") or "") for s in c["sessions"])
        urls.append((f"{base}c/{c['ticker']}/", last, "0.8"))
        for s in c["sessions"]:
            urls.append((base + "/".join(p for p in s["path"].split("/")), s.get("date") or "", "0.6"))
        n += 1
    for path in sorted(set(economy.values())):
        urls.append((base + path, idx.get("generated", "")[:10], "0.7"))
    from urllib.parse import quote
    rows = []
    for u, lm, pr in urls:
        u = quote(u, safe=":/#?=&")
        rows.append(f"  <url><loc>{E(u)}</loc>" + (f"<lastmod>{lm}</lastmod>" if re.fullmatch(r"\d{4}-\d\d-\d\d", lm or "") else "")
                    + f"<priority>{pr}</priority></url>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "\n".join(rows) + "\n</urlset>\n")
    print(f"產生 {n} 個公司頁、sitemap.xml（{len(urls)} 個網址）")


if __name__ == "__main__":
    sys.exit(main())
