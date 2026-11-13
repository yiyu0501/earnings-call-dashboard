#!/usr/bin/env python3
"""把測試產出的互動版 HTML 和標準答案比對，列出一致與不同之處。
用法：python compare_output.py <產出的 html> <標準答案 json>
只需要 Python 3，不需要安裝其他套件。"""
import json, re, sys

def load_html(p):
    h = open(p, encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', h, re.S)
    if not m:
        sys.exit("這份 HTML 不是互動版（找不到內嵌資料）。表格版請改用肉眼比對，或請 AI 重新產生互動版。")
    return json.loads(m.group(1).replace("<\\/", "</"))

def nums(s):
    s = re.sub(r"(?<=\d),(?=\d{3})", "", str(s))
    return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)}

clen = lambda s: len(re.sub(r"\s", "", s or ""))
got, ref = load_html(sys.argv[1]), json.load(open(sys.argv[2], encoding="utf-8"))
rows = []
def row(item, ok, note):
    rows.append(("✅" if ok is True else ("⚠️" if ok is None else "❌"), item, note))

gm, rm = got.get("meta", {}), ref.get("meta", {})
row("公司", gm.get("company", "").startswith(rm.get("company", "")[:2]), f"產出 {gm.get('company')}／答案 {rm.get('company')}")
row("年份與季別", (gm.get("year"), gm.get("quarter")) == (rm.get("year"), rm.get("quarter")),
    f"產出 {gm.get('year')} Q{gm.get('quarter')}／答案 {rm.get('year')} Q{rm.get('quarter')}")
gs, rs = got.get("summary", {}).get("text", ""), ref.get("summary", {}).get("text", "")
row("摘要字數 80–120", 80 <= clen(gs) <= 120, f"{clen(gs)} 字")
# 資料異常：標準答案的摘要有寫的，產出也要寫到
for kw, label in (("重複收錄", "有發現重複收錄"), ("主持人", "有發現整場標成主持人"), ("問答", "有說明問答不完整"), ("年份", "有發現年份矛盾")):
    if kw in rs:
        row(label, kw in gs or (kw == "重複收錄" and "重複" in gs), "答案的摘要有寫明這件事" + ("" if kw in gs else "，產出沒有"))
# 未來展望的前後比較
def revs(d):
    c = {}
    for it in (d.get("outlook") or {}).get("items", []):
        if it.get("vs_prior"): c[it["vs_prior"]] = c.get(it["vs_prior"], 0) + 1
    return c
gr, rr = revs(got), revs(ref)
row("上修／下修判斷", gr.get("上修", 0) == rr.get("上修", 0) and gr.get("下修", 0) == rr.get("下修", 0),
    f"產出 上修 {gr.get('上修',0)}、下修 {gr.get('下修',0)}／答案 上修 {rr.get('上修',0)}、下修 {rr.get('下修',0)}")
if not rr:
    row("不該做前後比較時沒有比較", not gr, "答案沒有任何前後比較" + ("" if not gr else f"，產出卻標了 {gr}"))
gi, ri = len((got.get("outlook") or {}).get("items", [])), len((ref.get("outlook") or {}).get("items", []))
row("指引項目數", abs(gi - ri) <= 3 or None, f"產出 {gi}／答案 {ri}（差 3 項以內算一致）")
# 關鍵數據：答案的數字有幾成出現在產出
rn = set().union(*[nums(k.get("value", "")) for k in ref.get("key_data", [])]) if ref.get("key_data") else set()
gn = set().union(*[nums(k.get("value", "")) for k in got.get("key_data", [])]) if got.get("key_data") else set()
if rn:
    hit = len(rn & gn) / len(rn)
    row("關鍵數據涵蓋率", hit >= 0.6 or None, f"答案的數字有 {hit:.0%} 出現在產出（60% 以上算一致）")
row("關鍵數據筆數 4–12", 4 <= len(got.get("key_data", [])) <= 12 if "key_data" in got.get("modules", []) else True, f"{len(got.get('key_data', []))} 筆")
# 評價
gR, rR = got.get("rating") or {}, ref.get("rating") or {}
if rR:
    row("整體評價", gR.get("overall") == rR.get("overall") or None, f"產出 {gR.get('overall')}／答案 {rR.get('overall')}（AI 判斷，差一級可接受）")
    for k, n_ in (("growth", "成長動能"), ("risk", "風險程度")):
        a, b = (gR.get(k) or {}).get("score"), (rR.get(k) or {}).get("score")
        if a is not None and b is not None:
            row(n_, abs(a - b) <= 15 or None, f"產出 {a}／答案 {b}（差 15 分以內算一致）")
# Q&A 與提問單位
gq, rq = got.get("qa", []), ref.get("qa", [])
row("Q&A 題數", abs(len(gq) - len(rq)) <= 2 or None, f"產出 {len(gq)}／答案 {len(rq)}")
ro = {a.get("org") for a in ref.get("analysts", []) if a.get("org") not in (None, "", "逐字稿未提及")}
go = {a.get("org") for a in got.get("analysts", [])}
if ro:
    row("提問單位", ro <= go or None, f"答案的單位 {sorted(ro)}；產出缺少 {sorted(ro - go) or '無'}")
ra = {p["name"] for p in ref.get("attendees", [])}; ga = {p["name"] for p in got.get("attendees", [])}
row("出席人員", ra <= ga and not any("未發言" in (p.get("sections") or "") for p in got.get("attendees", [])) or None,
    f"缺少 {sorted(ra - ga) or '無'}；多列 {sorted(ga - ra) or '無'}")
# 報告稿格式
b = got.get("briefs") or {}
if not b:
    row("報告稿", False, "沒有 briefs")
else:
    line = b.get("line", "")
    row("LINE 稿格式", len(re.findall(r"(?m)^\s*\d+\.\s", line)) >= 3 and not re.search(r"早安|午安|晚安", line), "至少 3 條編號、沒有自己加問候語")
    row("組內摘要格式", "重點" in b.get("memo", "") and len(re.findall(r"(?m)^\s*\d+\.\s", b.get("memo", ""))) >= 3, "先總結，再「重點：」條列")
    row("研報格式", "結論：" in b.get("report", ""), "有「結論：」")
    row("沒有多餘空格", not any(re.search(r"\S {2,}\S", v) for v in b.values()), "")
rk = {k["word"].lower() for k in ref.get("keywords", [])}; gk = {k["word"].lower() for k in got.get("keywords", [])}
if rk:
    row("關鍵字重疊", len(rk & gk) / len(rk) >= 0.4 or None, f"答案的關鍵字有 {len(rk & gk)/len(rk):.0%} 出現在產出（40% 以上算一致）")

ok = sum(r[0] == "✅" for r in rows); warn = sum(r[0] == "⚠️" for r in rows); bad = sum(r[0] == "❌" for r in rows)
print(f"# 比對結果：{sys.argv[1].split('/')[-1]}\n")
print(f"✅ 一致 {ok} 項　⚠️ 有差異但可接受 {warn} 項　❌ 不一致 {bad} 項\n")
print("| | 項目 | 說明 |\n|---|---|---|")
for r in rows: print(f"| {r[0]} | {r[1]} | {r[2]} |")
print("\n❌ 代表違反規則或漏掉重要判斷；⚠️ 多半是 AI 判斷的合理差異，請人工看一下。")
