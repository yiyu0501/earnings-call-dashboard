#!/usr/bin/env python3
"""
把 dashboard.json 套進 assets/template.html，產生單檔 HTML 儀表板。

用法：
    python render.py dashboard.json --tone tone.json --keywords keywords.json --outdir <輸出資料夾>

- 語調分數一律讀 tone.json，關鍵字次數一律讀 keywords.json，不採用 dashboard.json 裡的數字。
- 所有文字都會跳脫處理，AI 寫的內容不會破壞版面。
- 檔名：{股票代號}_{年份}Q{季}.html；沒有代號時用公司名稱；年度法說會用 {年份}FY。
"""
import argparse
import base64
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")

NAMES = {
    "summary": "法說摘要", "conclusion": "結論", "rating": "投資評價", "key_data": "關鍵數據",
    "tone": "語調分析", "outlook": "未來展望", "qa": "QA 關注議題", "attendees": "出席人員組成",
    "keywords": "關鍵字",
}
RATINGS = ("樂觀", "審慎樂觀", "中性", "保守", "悲觀")
DIRECTIONS = ("成長", "改善", "持平", "下滑", "承壓", "未說明")
REVISIONS = ("上修", "下修", "維持", "新增", "")
STANCES = ("正面", "保守", "防禦性", "避重就輕")
DIR_CLS = {"成長": "chip", "改善": "chip", "持平": "chip flat", "未說明": "chip flat", "下滑": "chip fmt", "承壓": "chip fmt"}
REV_CLS = {"上修": "chip", "下修": "chip fmt", "維持": "chip flat", "新增": "chip flat"}
STANCE_CLS = {"正面": "chip", "保守": "chip flat", "防禦性": "chip fmt", "避重就輕": "chip fmt"}

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def b64(name):
    with open(os.path.join(ASSETS, name), "rb") as f:
        return base64.b64encode(f.read()).decode()


def head(mid, title):
    return (f'      <div class="mod" id="m-{mid}" data-mod="{e(title)}">\n'
            f'        <button class="filter-name mod-head" type="button" aria-expanded="true" onclick="fold(this)">'
            f'{e(title)}<span class="caret" aria-hidden="true"></span></button>\n')


def table(headers, rows_html, widths=None):
    ths = "".join(f'<th{f" style=\"width:{widths[i]}\"" if widths and widths[i] else ""}>{e(h)}</th>' for i, h in enumerate(headers))
    return (f'        <div class="mod-body flush"><div class="table-scroll"><table>\n'
            f'          <thead><tr>{ths}</tr></thead>\n          <tbody>\n{rows_html}          </tbody>\n'
            f'        </table></div>')


def m_text(mid, title, text, quote=None):
    q = f'<div class="des quote" style="margin-top:8px">{e(quote)}</div>' if quote else ""
    return head(mid, title) + f'        <div class="mod-body"><p>{e(text)}</p>{q}</div>\n      </div>\n'


def m_rating(r):
    ov = r.get("overall", "中性")
    g, k = r.get("growth", {}), r.get("risk", {})
    gs, ks = int(g.get("score", 0)), int(k.get("score", 0))
    rows = (f'            <tr><td class="c" rowspan="2"><span class="big">{e(ov)}</span></td>'
            f'<td><span class="name">成長動能</span> {gs}%<div class="bar"><i style="width:{gs}%"></i></div></td>'
            f'<td class="des">{e(g.get("reason", ""))}</td></tr>\n'
            f'            <tr><td><span class="name">風險程度</span> {ks}%<div class="bar navy"><i style="width:{ks}%"></i></div></td>'
            f'<td class="des">{e(k.get("reason", ""))}</td></tr>\n')
    return head("rating", NAMES["rating"]) + table(["整體評價", "指標", "說明"], rows, [None, None, "40%"]) + "\n        </div>\n      </div>\n"


def m_key_data(items):
    rows = ""
    for i, it in enumerate(items, 1):
        rows += (f'            <tr><td class="c">{i}</td><td><span class="name">{e(it.get("metric"))}</span>'
                 f'<div class="des quote">{e(it.get("quote"))}</div>'
                 f'<div class="tags"><span class="chip">{e(it.get("period"))}</span>｜<span class="chip fmt">原文</span></div></td>'
                 f'<td class="c">{e(it.get("value"))}</td><td class="c">{e(it.get("change") or "—")}</td></tr>\n')
    return head("key_data", NAMES["key_data"]) + table(["項次", "指標與原文", "數值", "變動"], rows) + "\n        </div>\n      </div>\n"


def fmt_score(x):
    return f"{x:+.2f}".replace("-", "−")


def m_tone(tone, note):
    rows = ""
    for key, label in (("presentation", "管理層講稿"), ("qa", "Q&A 回答")):
        t = tone.get(key)
        if t:
            cls = "chip" if t["label"] == "偏正向" else "chip fmt"
            en = tone.get("language") == "en"
            base_n = t.get("words") if en else t.get("chars")
            dens = round(t["uncertainty"] * 1000 / base_n) if base_n else 0
            unit = "每千詞" if en else "每千字"
            rows += (f'            <tr><td><span class="name">{e(label)}</span></td><td class="c"><span class="big">{fmt_score(t["score"])}</span></td>'
                     f'<td class="c">{t["uncertainty"]} 次<div class="des">{unit} {dens} 次</div></td>'
                     f'<td><span class="{cls}">{e(t["label"])}</span></td></tr>\n')
        else:
            msg = "本場無 Q&A" if key == "qa" else "無管理層講稿"
            rows += (f'            <tr><td><span class="name">{e(label)}</span></td><td class="c empty">—</td><td class="c empty">—</td>'
                     f'<td><span class="chip fmt">{e(msg)}</span></td></tr>\n')
    body = table(["段落", "語調分數", "不確定用詞", "判讀"], rows)
    base = "語調分數範圍 −1 到 +1，依詞表計算管理層發言；不確定用詞越多，語氣越保守。"
    body += f'\n          <p class="des note">{e(base)}{e(note)}</p>'
    return head("tone", NAMES["tone"]) + body + "\n        </div>\n      </div>\n"


def m_outlook(o, prior_label=""):
    """未來展望：一段總結＋指引表。每筆指引都附原文、方向，有上一場資料時附「與上場比較」。"""
    items = o.get("items", [])
    has_rev = any(it.get("vs_prior") for it in items)
    rows = ""
    for i, it in enumerate(items, 1):
        d = it.get("direction") or "未說明"
        rev = it.get("vs_prior") or ""
        rows += (f'            <tr><td class="c">{i}</td><td><span class="name">{e(it.get("topic"))}</span>'
                 f'<div class="des quote">{e(it.get("quote"))}</div>'
                 f'<div class="tags"><span class="chip">{e(it.get("period") or "未提及")}</span>｜<span class="chip fmt">原文</span></div></td>'
                 f'<td class="c">{e(it.get("value"))}</td>'
                 f'<td class="c"><span class="{DIR_CLS.get(d, "chip flat")}">{e(d)}</span></td>')
        if has_rev:
            rows += (f'<td class="c"><span class="{REV_CLS[rev]}">{e(rev)}</span></td>' if rev else '<td class="c empty">—</td>')
        rows += "</tr>\n"
    heads = ["項次", "指引項目與原文", "指引內容", "方向"] + (["與上場比較"] if has_rev else [])
    lead = f'        <div class="mod-body lead"><p>{e(o.get("text", ""))}</p>'
    if has_rev and prior_label:
        lead += f'<p class="des" style="margin-top:6px">比較基準：{e(prior_label)}</p>'
    lead += "</div>\n"
    body = table(heads, rows) if items else '        <div class="mod-body"><p class="empty">逐字稿未提供具體指引</p>'
    return head("outlook", NAMES["outlook"]) + lead + body + "\n        </div>\n      </div>\n"


def m_qa(items):
    if not items:
        return head("qa", NAMES["qa"]) + '        <div class="mod-body"><p class="empty">本場無 Q&amp;A</p></div>\n      </div>\n'
    rows = ""
    for i, it in enumerate(items, 1):
        st = it.get("stance") or ""
        stance = f'<div style="margin-top:6px"><span class="{STANCE_CLS.get(st, "chip flat")}">{e(st)}</span></div>' if st else ""
        ans = f'<div class="des">{e(it.get("answer"))}</div>' if it.get("answer") else ""
        rows += (f'            <tr class="qa-row" onclick="toggleQa(this)"><td class="c">{i}</td><td><span class="name">{e(it.get("question"))}</span>'
                 f'{ans}<button type="button" class="tog" onclick="event.stopPropagation();toggleQa(this.closest(\'tr\'))">看原文</button>'
                 f'<div class="more des quote">{e(it.get("quote"))}</div>'
                 f'<div class="tags"><span class="chip">{e(it.get("asker") or "法人")}</span>｜<span class="chip fmt">{e(it.get("tag"))}</span></div></td>'
                 f'<td class="c">{e(it.get("answerer"))}{stance}</td></tr>\n')
    return head("qa", NAMES["qa"]) + table(["項次", "提問與回答", "回答者與態度"], rows) + "\n        </div>\n      </div>\n"


def m_attendees(items):
    rows = "".join(
        f'            <tr><td class="c"><span class="name">{e(it.get("name") or "未具名")}</span></td>'
        f'<td class="c">{e(it.get("title"))}</td><td class="c">{e(it.get("sections"))}</td></tr>\n' for it in items)
    return head("attendees", NAMES["attendees"]) + table(["姓名", "職稱", "發言段落"], rows) + "\n        </div>\n      </div>\n"


def m_keywords(kw):
    chips = "".join(f'<span class="chip{"" if k["type"] == "positive" else " fmt"}">{e(k["word"])} {k["count"]}</span>' for k in kw)
    legend = ('<p class="des" style="margin-top:10px"><span class="chip sm">藍框</span> 正面議題　'
              '<span class="chip fmt sm">淺底</span> 風險或不確定議題　數字為提及次數</p>')
    return head("keywords", NAMES["keywords"]) + f'        <div class="mod-body"><div class="tags kw">{chips}</div>{legend}</div>\n      </div>\n'


def m_custom(i, c):
    title = c.get("title", f"自訂模組 {i + 1}")
    mid = f"custom-{i}"
    if c.get("kind") == "table":
        cols = c.get("columns", [])
        rows = "".join("            <tr>" + "".join(f"<td>{e(x)}</td>" for x in r) + "</tr>\n" for r in c.get("rows", []))
        return head(mid, title) + table(cols, rows) + "\n        </div>\n      </div>\n"
    return m_text(mid, title, c.get("text", ""), c.get("quote"))


def session_label(meta):
    y, q = meta.get("year"), int(meta.get("quarter") or 0)
    return f"{y} Q{q}" if q else f"{y} 年度"


def out_name(meta):
    base = (meta.get("ticker") or "").strip() or re.sub(r"[\\/:*?\"<>|\s]+", "", meta.get("company", "公司"))
    q = int(meta.get("quarter") or 0)
    return f"{base}_{meta.get('year')}{'Q' + str(q) if q else 'FY'}.html"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dashboard")
    ap.add_argument("--tone", help="tone_score.py 的輸出")
    ap.add_argument("--keywords", help="keyword_count.py 的輸出")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--template", default=os.path.join(ASSETS, "template.html"))
    a = ap.parse_args()

    d = json.load(open(a.dashboard, encoding="utf-8"))
    meta = d.get("meta", {})
    order = d.get("modules", [])
    tone = json.load(open(a.tone, encoding="utf-8")) if a.tone else None
    kw = json.load(open(a.keywords, encoding="utf-8"))["keywords"] if a.keywords else None
    problems = []

    parts, toc = [], []
    for mid in order:
        if mid.startswith("custom:"):
            idx = int(mid.split(":")[1])
            c = d.get("custom", [])[idx]
            parts.append(m_custom(idx, c)); toc.append((f"custom-{idx}", c.get("title", "自訂模組")))
            continue
        if mid not in NAMES:
            problems.append(f"未知的模組代號：{mid}"); continue
        name = NAMES[mid]
        if mid == "summary":
            parts.append(m_text("summary", name, d["summary"]["text"]))
        elif mid == "conclusion":
            parts.append(m_text("conclusion", name, d["conclusion"]["text"]))
        elif mid == "rating":
            if d["rating"].get("overall") not in RATINGS:
                problems.append(f"投資評價 overall 必須是 {RATINGS} 其中之一")
            parts.append(m_rating(d["rating"]))
        elif mid == "key_data":
            parts.append(m_key_data(d.get("key_data", [])))
        elif mid == "tone":
            if not tone:
                problems.append("有勾選語調分析，但沒有提供 --tone tone.json"); continue
            parts.append(m_tone(tone, d.get("tone", {}).get("note", "")))
        elif mid == "outlook":
            o = d.get("outlook", {})
            if isinstance(o, list):
                problems.append("outlook 格式已改為 {text, items}，請依 references/schema.md 修改"); continue
            for it in o.get("items", []):
                if (it.get("direction") or "未說明") not in DIRECTIONS:
                    problems.append(f"未來展望 direction「{it.get('direction')}」必須是 {DIRECTIONS} 其中之一")
                if (it.get("vs_prior") or "") not in REVISIONS:
                    problems.append(f"未來展望 vs_prior「{it.get('vs_prior')}」必須是 上修、下修、維持、新增 或留空")
            prior = d.get("meta", {}).get("prior_call", "")
            parts.append(m_outlook(o, prior))
        elif mid == "qa":
            for it in d.get("qa", []):
                if it.get("stance") and it["stance"] not in STANCES:
                    problems.append(f"QA stance「{it['stance']}」必須是 {STANCES} 其中之一")
            parts.append(m_qa(d.get("qa", [])))
        elif mid == "attendees":
            parts.append(m_attendees(d.get("attendees", [])))
        elif mid == "keywords":
            if kw is None:
                problems.append("有勾選關鍵字，但沒有提供 --keywords keywords.json"); continue
            parts.append(m_keywords(kw))
        toc.append((mid, name))

    if problems:
        print(json.dumps({"ok": False, "problems": problems}, ensure_ascii=False, indent=1))
        sys.exit(1)

    label = session_label(meta)
    company = meta.get("company", "")
    company_field = f"{company}（{meta['ticker']}）" if meta.get("ticker") else company
    toc_html = "".join(f'<li><a href="#m-{mid}" onclick="return goMod(\'m-{mid}\')">{e(n)}</a></li>' for mid, n in toc)
    y, q = meta.get("year"), int(meta.get("quarter") or 0)
    pager = (f'<button type="button" disabled aria-label="上一場">‹</button>'
             f'<span class="on" aria-current="page">'
             f'<span class="n">{e(y)}</span>{"Q" + str(q) if q else "年度"}</span>'
             f'<button type="button" disabled aria-label="下一場">›</button>')
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    date = meta.get("date") or "未提及"
    methods = "語調分數依詞表計算管理層發言；關鍵字次數由程式計算；摘要、結論、評價由 AI 依逐字稿整理"
    footer = "\n".join(f"    <p>{e(x)}</p>" for x in (
        f"資料來源：{meta.get('source_file', '')}（法說會日期 {date}）",
        f"分析方法：{methods}",
        f"生成時間：{now}　由法說會 Dashboard Skill 生成",
        "本頁內容由 AI 依法說會逐字稿整理，僅供參考，不構成投資建議。",
    ))

    tpl = open(a.template, encoding="utf-8").read()
    rep = {
        "{{PAGE_TITLE}}": e(f"{company} {label} 法說會儀表板"),
        "{{LOGO_MARK}}": b64("tej_mark.png"),
        "{{LOGO_LOCKUP}}": b64("tej_lockup.png"),
        "{{COMPANY}}": e(company),
        "{{SESSION_LABEL}}": e(label),
        "{{COMPANY_FIELD}}": e(company_field),
        "{{INDUSTRY}}": e(meta.get("industry") or "未提及"),
        "{{MODULE_COUNT}}": str(len(parts)),
        "{{PAGER}}": pager,
        "{{TOC_ITEMS}}": toc_html,
        "{{MODULES}}": "".join(parts),
        "{{FOOTER}}": footer,
    }
    for k, v in rep.items():
        tpl = tpl.replace(k, v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", tpl)
    if left:
        print(json.dumps({"ok": False, "problems": [f"模板還有未替換的欄位：{left}"]}, ensure_ascii=False)); sys.exit(1)

    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, out_name(meta))
    open(path, "w", encoding="utf-8").write(tpl)
    print(json.dumps({"ok": True, "output": path, "modules": [n for _, n in toc]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
