#!/usr/bin/env python3
"""
檢查儀表板是否符合規格。有任何 error 就必須修正 dashboard.json 後重新 render，直到通過。

用法：
    python check_output.py --dashboard dashboard.json --transcript transcript.json \
        --keywords keywords.json --tone tone.json --html <輸出的 html> \
        [--prior-transcript prior/transcript.json]

檢查三類：
  內容：原文是否真的在逐字稿裡、數字是否出自原文、字數與筆數、選項是否合法、
        「由 A……至 B」寫完整、禁用 AI 腔用語
  延伸欄位：上一場原文（prior_quote）、提問者與提問單位、報告稿（briefs）的格式與數字
  版面：互動版（預設）檢查單檔離線、資料可讀、無障礙；表格版另檢查色票、字重、圓角（layout.md 第 11 節）
  兩種版本都會在 375px 寬度下檢查是否出現橫向捲軸
"""
import argparse
import json
import re
import sys

ALLOWED_COLORS = {
    "#0d0d0d", "#717171", "#f8f8f8", "#ffffff", "#eeeeee", "#1970b8", "#186eb4", "#0f548d", "#204383",
    "#dadada", "#fff3a6", "#1562be", "#2cb1b1",
    "rgba(13,13,13,.38)", "rgba(23,103,169,.05)", "rgba(26,115,188,.2)", "rgba(32,67,131,.1)",
    "rgba(25,112,184,.12)", "rgba(13,13,13,.1)", "rgba(13,13,13,.87)", "rgba(13,13,13,.5)", "rgba(13,13,13,.6)",
    "rgba(0,0,0,.2)", "rgba(0,0,0,.14)", "rgba(0,0,0,.12)",
}
ALLOWED_RADIUS = {"0", "4px", "8px", "50%"}
RATINGS = {"樂觀", "審慎樂觀", "中性", "保守", "悲觀"}
DIRECTIONS = {"成長", "改善", "持平", "下滑", "承壓", "未說明"}
REVISIONS = {"上修", "下修", "維持", "新增", ""}
STANCES = {"正面", "保守", "防禦性", "避重就輕"}
ASKERS = {"投信", "投顧", "證券", "外資", "媒體", "個人投資人", "法人", "分析師", "保險", "銀行"}
VALID_MODULES = {"summary", "conclusion", "rating", "key_data", "tone", "outlook", "qa", "attendees", "keywords"}


def n(s):
    """比對用：去掉空白與常見標點差異。"""
    s = re.sub(r"\s+", "", str(s))
    return s.replace("，", ",").replace("：", ":").replace("（", "(").replace("）", ")").replace("％", "%")


def clen(s):
    return len(re.sub(r"\s+", "", str(s)))


def quote_in(quote, body):
    parts = [p for p in re.split(r"……|\.\.\.|…", quote) if clen(p) >= 4]
    if not parts:
        return False
    return all(n(p).strip("。,.、") in body for p in parts)


def nums(s):
    return re.findall(r"\d+(?:\.\d+)?", str(s))


BANNED = ("令人振奮", "表現亮眼", "亮眼", "驚豔", "值得期待", "值得關注", "不容小覷", "毋庸置疑", "綜上所述",
          "總而言之", "值得一提的是", "強勢回歸", "全面爆發", "一片看好")
TYPES = {"外資", "證券", "投顧", "投信", "媒體", "個人投資人", "保險", "銀行", "未提及"}


def num_in(x, text):
    """數字 x 是否出現在 text 裡。年份 2024 可以對到口語的 '24。"""
    t = n(text)
    if x in t:
        return True
    return bool(re.fullmatch(r"20\d\d", x)) and ("'" + x[2:] in t or "’" + x[2:] in t)


def numset(s):
    """取出數字（先去掉千分位逗號），回傳 float 集合。"""
    s = re.sub(r"(?<=\d),(?=\d{3})", "", str(s))
    return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)}


HALF = re.compile(r"由[^，。；、,]*?(增加|下降|減少|降低|提高|上升|成長|下滑|回升|擴大|縮小)(?![^，。；、,]*?[至到])")


def half_change(s):
    """「由 58 天下降」只寫了起點；要寫成「由 58 天下降至 33 天」。回傳有問題的片段。"""
    for part in re.split(r"[，。；、,]", s or ""):
        if HALF.search(part) and not re.search(r"[至到]", part.split("由", 1)[-1]):
            return part.strip()
    return None


def check_content(d, t, kw, errors, warns):
    body = n(t.get("full_text", "") or "".join(s["text"] for s in t["segments"]))
    meta = d.get("meta", {})
    for f in ("company", "year", "quarter", "source_file"):
        if meta.get(f) in (None, ""):
            errors.append(f"meta.{f} 必填")
    mods = d.get("modules", [])
    if not mods:
        errors.append("modules 是空的，至少要有一個模組")
    for m in mods:
        if m not in VALID_MODULES and not re.fullmatch(r"custom:\d+", m):
            errors.append(f"未知的模組代號 {m}")
        if m in VALID_MODULES and m not in ("tone", "keywords") and m not in d:
            errors.append(f"有勾選 {m}，但沒有填內容")

    if "summary" in mods:
        L = clen(d["summary"]["text"])
        if not 80 <= L <= 120:
            errors.append(f"法說摘要 {L} 字，規格是 80–120 字")
    if "conclusion" in mods:
        L = clen(d["conclusion"]["text"])
        if not 100 <= L <= 150:
            errors.append(f"結論 {L} 字，規格是 100–150 字")
    if "rating" in mods:
        r = d["rating"]
        if r.get("overall") not in RATINGS:
            errors.append(f"投資評價 overall「{r.get('overall')}」不在選項內：{'、'.join(RATINGS)}")
        for k in ("growth", "risk"):
            x = r.get(k, {})
            sc = x.get("score")
            if not isinstance(sc, int) or not 0 <= sc <= 100:
                errors.append(f"投資評價 {k}.score 必須是 0–100 的整數")
            if clen(x.get("reason", "")) > 20:
                errors.append(f"投資評價 {k}.reason 超過 20 字")
            if not x.get("reason"):
                errors.append(f"投資評價 {k}.reason 不可空白")
    if "key_data" in mods:
        items = d.get("key_data", [])
        if not items:
            errors.append("關鍵數據沒有任何一列")
        for i, it in enumerate(items, 1):
            q = it.get("quote", "")
            if not q:
                errors.append(f"關鍵數據第 {i} 列（{it.get('metric')}）沒有原文")
                continue
            if not quote_in(q, body):
                errors.append(f"關鍵數據第 {i} 列（{it.get('metric')}）的原文在逐字稿裡找不到，請改成逐字稿原句：{q[:30]}")
            for x in nums(it.get("value", "")):
                if x not in n(q):
                    errors.append(f"關鍵數據第 {i} 列（{it.get('metric')}）的數值 {x} 沒有出現在原文裡")
            for x in nums(it.get("change", "")):
                if x not in n(q):
                    errors.append(f"關鍵數據第 {i} 列（{it.get('metric')}）的變動 {x} 沒有出現在原文裡")
            for fld in ("value", "change"):
                h = half_change(it.get(fld, ""))
                if h:
                    errors.append(f"關鍵數據第 {i} 列（{it.get('metric')}）的 {fld}「{h}」只寫了起點，要寫完整，例如「由 58 天下降至 33 天」")
    if "tone" in mods and clen(d.get("tone", {}).get("note", "")) > 40:
        errors.append("語調分析 note 超過 40 字")
    if "outlook" in mods:
        o = d.get("outlook", {})
        if isinstance(o, list):
            errors.append("outlook 必須是 {text, items} 格式（見 schema.md）")
            o = {}
        L = clen(o.get("text", ""))
        if not 80 <= L <= 200:
            errors.append(f"未來展望總結 {L} 字，規格是 80–200 字")
        items = o.get("items", [])
        if not 3 <= len(items) <= 15:
            errors.append(f"未來展望指引 {len(items)} 項，規格是 3–15 項")
        for i, it in enumerate(items, 1):
            tag = f"未來展望第 {i} 項（{it.get('topic')}）"
            if clen(it.get("topic", "")) > 12:
                errors.append(f"{tag} topic 超過 12 字")
            if not it.get("period"):
                errors.append(f"{tag} period 空白，沒提到請填「未提及」")
            if clen(it.get("value", "")) > 40:
                errors.append(f"{tag} value 超過 40 字")
            if half_change(it.get("value", "")):
                errors.append(f"{tag} value「{half_change(it.get('value', ''))}」只寫了起點，要寫完整，例如「由 30% 以上上修至略高於 40%」")
            if (it.get("direction") or "") not in DIRECTIONS:
                errors.append(f"{tag} direction 必須是 {'、'.join(sorted(DIRECTIONS))} 其中之一")
            if (it.get("vs_prior") or "") not in REVISIONS:
                errors.append(f"{tag} vs_prior 必須是 上修、下修、維持、新增 或留空")
            q = it.get("quote", "")
            if not q:
                errors.append(f"{tag} 沒有原文")
                continue
            if not quote_in(q, body):
                errors.append(f"{tag} 的原文在逐字稿裡找不到：{q[:30]}")
            for x in nums(it.get("value", "")):
                if not num_in(x, q):
                    errors.append(f"{tag} 的數字 {x} 沒有出現在原文裡")
    if "qa" in mods:
        items = d.get("qa", [])
        if t.get("has_qa") and not items:
            errors.append("逐字稿有 Q&A，但 QA 關注議題是空的")
        for i, it in enumerate(items, 1):
            if clen(it.get("question", "")) > 40:
                errors.append(f"QA 第 {i} 題 question 超過 40 字")
            if not 10 <= clen(it.get("answer", "")) <= 60:
                errors.append(f"QA 第 {i} 題 answer（回答摘要）{clen(it.get('answer', ''))} 字，規格是 10–60 字")
            if it.get("stance") not in STANCES:
                errors.append(f"QA 第 {i} 題 stance「{it.get('stance')}」必須是 {'、'.join(sorted(STANCES))} 其中之一")
            if it.get("asker") not in ASKERS:
                warns.append(f"QA 第 {i} 題 asker「{it.get('asker')}」不是建議的類別，看不出來請填「法人」")
            if clen(it.get("tag", "")) > 6:
                errors.append(f"QA 第 {i} 題 tag 超過 6 字")
            if not it.get("quote"):
                errors.append(f"QA 第 {i} 題沒有回答原文")
            elif not quote_in(it["quote"], body):
                errors.append(f"QA 第 {i} 題的回答原文在逐字稿裡找不到：{it['quote'][:30]}")
    if "attendees" in mods:
        for it in d.get("attendees", []):
            nm = it.get("name", "")
            speakers = {n(x.get("name", "")) for x in t.get("speakers", [])} | {n(x.get("speaker", "")) for x in t.get("segments", [])}
            if nm not in ("未具名", "提問法人") and n(nm) not in body and n(nm) not in speakers:
                errors.append(f"出席人員「{nm}」沒有出現在逐字稿裡")
    if "keywords" in mods and kw is not None:
        k = len(kw.get("keywords", []))
        if not 8 <= k <= 12:
            errors.append(f"有效關鍵字 {k} 個（次數 0 的已排除：{[x['word'] for x in kw.get('dropped', [])]}），規格是 8–12 個")
    for i, c in enumerate(d.get("custom", [])):
        if clen(c.get("title", "")) > 10:
            errors.append(f"自訂模組 {i} 標題超過 10 字")
        if c.get("kind") == "table":
            for r in c.get("rows", []):
                for cell in r:
                    for x in nums(cell):
                        if x not in body:
                            errors.append(f"自訂模組「{c.get('title')}」的數字 {x} 在逐字稿裡找不到")


STD = {"revenue", "revenue_growth", "gross_margin", "op_margin", "net_margin", "net_income", "eps", "capex",
       "depreciation", "dividend", "utilization", "roe", "other"}
TOPICS = {"AI需求", "需求展望", "毛利率", "價格", "產能與擴產", "資本支出", "海外布局", "先進製程", "先進封裝",
          "庫存", "匯率", "關稅與地緣", "股東回饋", "財務與費用", "競爭", "其他"}
PERIOD = re.compile(r"^20\d\d (Q[1-4]|全年|上半年|下半年)$")


def fmtnum(x):
    """數字轉成原文常見寫法：去掉多餘的 .0。"""
    s = ("%f" % float(x)).rstrip("0").rstrip(".")
    return s


def check_deep(d, t, errors, warns):
    """深度追蹤欄位（選填）：std、num/unit、low/high/unit、voices、qa.topic。有填才檢查。"""
    body = n(t.get("full_text", "") or " ".join(s.get("text", "") for s in t.get("segments", [])))
    for i, it in enumerate(d.get("key_data", []), 1):
        tag = f"關鍵數據第 {i} 列（{it.get('metric')}）"
        if it.get("std") and it["std"] not in STD:
            errors.append(f"{tag} std「{it['std']}」不在標準代碼清單裡（見 schema.md）")
        if "num" in it:
            if not isinstance(it["num"], (int, float)):
                errors.append(f"{tag} num 必須是數字")
            elif not num_in(fmtnum(it["num"]), it.get("quote", "")):
                errors.append(f"{tag} num {fmtnum(it['num'])} 沒有出現在原文裡")
            if not it.get("unit"):
                errors.append(f"{tag} 有 num 就要填 unit")
            if it.get("std") and not PERIOD.match(it.get("period", "")):
                errors.append(f"{tag} 有 std 與 num 時，period 要寫成「2026 Q1」「2026 全年」這種格式")
    for i, it in enumerate((d.get("outlook") or {}).get("items", []) if isinstance(d.get("outlook"), dict) else [], 1):
        tag = f"未來展望第 {i} 項（{it.get('topic')}）"
        if it.get("std") and it["std"] not in STD:
            errors.append(f"{tag} std「{it['std']}」不在標準代碼清單裡（見 schema.md）")
        if "low" in it or "high" in it:
            lo, hi = it.get("low"), it.get("high")
            if not all(isinstance(x, (int, float)) for x in (lo, hi)) or lo > hi:
                errors.append(f"{tag} low／high 必須都是數字，且 low ≤ high")
            else:
                for x in (lo, hi):
                    if not num_in(fmtnum(x), it.get("quote", "")):
                        errors.append(f"{tag} 區間數字 {fmtnum(x)} 沒有出現在原文裡")
            if not it.get("unit"):
                errors.append(f"{tag} 有 low／high 就要填 unit")
            if it.get("std") and not PERIOD.match(it.get("period", "")):
                errors.append(f"{tag} 有 std 與區間時，period 要寫成「2026 Q1」「2026 全年」這種格式")
    for i, v in enumerate(d.get("voices", []), 1):
        if not v.get("role") or not v.get("points"):
            errors.append(f"voices 第 {i} 位缺 role 或 points")
        if not 2 <= len(v.get("points", [])) <= 5:
            errors.append(f"voices 第 {i} 位（{v.get('role')}）重點 {len(v.get('points', []))} 點，規格是 2–5 點")
        for j, p in enumerate(v.get("points", []), 1):
            if not 8 <= clen(p.get("text", "")) <= 40:
                errors.append(f"voices 第 {i} 位第 {j} 點 text {clen(p.get('text', ''))} 字，規格是 8–40 字")
            q = p.get("quote", "")
            if not q or not quote_in(q, body):
                errors.append(f"voices 第 {i} 位第 {j} 點的原文在逐字稿裡找不到：{q[:30]}")
            for x in nums(p.get("text", "")):
                if not num_in(x, q):
                    errors.append(f"voices 第 {i} 位第 {j} 點的數字 {x} 沒有出現在原文裡")
    for i, it in enumerate(d.get("qa", []), 1):
        if it.get("topic") and it["topic"] not in TOPICS:
            errors.append(f"QA 第 {i} 題 topic「{it['topic']}」不在標準議題清單裡（見 schema.md）")
    if d.get("meta", {}).get("deep"):
        if not any(it.get("std") for it in d.get("key_data", [])):
            errors.append("meta.deep 為 true，但關鍵數據沒有任何一列填 std")
        if not d.get("voices"):
            errors.append("meta.deep 為 true，但沒有填 voices（CEO／CFO 重點）")
        if d.get("qa") and not all(it.get("topic") for it in d["qa"]):
            errors.append("meta.deep 為 true，每一題 QA 都要填 topic")


def walk_text(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from walk_text(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_text(v)
    elif isinstance(o, (str, int, float)):
        yield str(o)


def check_extra(d, t, pt, tone, errors, warns):
    """互動版用到的延伸欄位：上一場原文、提問者與提問單位、報告稿。"""
    body = n(" ".join(s.get("text", "") for s in t.get("segments", [])))
    pbody = n(" ".join(s.get("text", "") for s in pt.get("segments", []))) if pt else None
    # 禁用的 AI 腔用語：摘要、結論、展望、報告稿
    texts = {"法說摘要": d.get("summary", {}).get("text", ""), "結論": d.get("conclusion", {}).get("text", ""),
             "未來展望總結": (d.get("outlook") or {}).get("text", "") if isinstance(d.get("outlook"), dict) else ""}
    for k, v in (d.get("briefs") or {}).items():
        texts[f"報告稿 {k}"] = v
    for where, txt in texts.items():
        for w in BANNED:
            if w in (txt or ""):
                errors.append(f"{where} 出現禁用的形容詞「{w}」，改寫成具體的事實或數字")
    # 上一場：prior_value 要有 prior_quote，原文要在上一場逐字稿裡
    items = (d.get("outlook") or {}).get("items", []) if isinstance(d.get("outlook"), dict) else []
    for i, it in enumerate(items, 1):
        tag = f"未來展望第 {i} 項（{it.get('topic')}）"
        pv, pq = it.get("prior_value"), it.get("prior_quote")
        if pv and not it.get("vs_prior"):
            errors.append(f"{tag} 有 prior_value，但 vs_prior 是空的")
        if pv and not pq:
            errors.append(f"{tag} 有前次數值，但沒有 prior_quote（上一場原文）")
        if pq:
            if pbody is None:
                warns.append(f"{tag} 有上一場原文，但沒有提供 --prior-transcript，無法核對")
            elif not quote_in(pq, pbody):
                errors.append(f"{tag} 的上一場原文在上一場逐字稿裡找不到：{pq[:30]}")
            for x in nums(pv or ""):
                if not num_in(x, pq):
                    errors.append(f"{tag} 的前次數值 {x} 沒有出現在上一場原文裡")
    # 提問者：有寫姓名就要在逐字稿裡；提問單位分組的題數要對得上
    qa = d.get("qa", [])
    for i, q in enumerate(qa, 1):
        nm = q.get("asker_name", "")
        if nm and n(nm) not in body and not any(n(nm) == n(s.get("speaker", "")) for s in t.get("segments", [])):
            errors.append(f"QA 第 {i} 題的提問者「{nm}」沒有出現在逐字稿裡")
        if qa and "asker_org" not in q:
            warns.append(f"QA 第 {i} 題沒有 asker_org（提問單位）；逐字稿沒說請填「逐字稿未提及」")
    for p in d.get("attendees", []):
        if "未發言" in (p.get("sections") or ""):
            errors.append(f"出席人員「{p.get('name')}」沒有發言，只列逐字稿裡有說話的人")
    if "key_data" in d.get("modules", []) and not 4 <= len(d.get("key_data", [])) <= 12:
        errors.append(f"關鍵數據 {len(d.get('key_data', []))} 筆，規格是 4–12 筆（只列影響判斷的本期數字）")
    an = d.get("analysts")
    if an is not None and qa:
        tot = sum(int(a.get("questions", 0)) for a in an)
        if tot != len(qa):
            errors.append(f"analysts 的題數合計 {tot} 題，和 QA 的 {len(qa)} 題對不上")
        for a in an:
            if a.get("type") not in TYPES:
                errors.append(f"analysts「{a.get('name')}」的 type「{a.get('type')}」必須是 {'、'.join(sorted(TYPES))} 其中之一")
    # 報告稿：三種格式、數字要能在儀表板資料裡找到（億與 billion 換算可接受）
    b = d.get("briefs")
    if b is None:
        warns.append("沒有 briefs（報告稿），互動版會依資料自動組稿；建議照 references/briefs.md 寫")
        return
    for k in ("line", "memo", "report"):
        if not (b.get(k) or "").strip():
            errors.append(f"briefs.{k} 是空的")
    line, memo, report = b.get("line", ""), b.get("memo", ""), b.get("report", "")
    if re.search(r"早安|午安|晚安|晚上好|大家好", line):
        errors.append("briefs.line 不要寫問候語，頁面會依時間自動加上")
    if len(re.findall(r"(?m)^\s*\d+\.\s", line)) < 3:
        errors.append("briefs.line 至少要有 3 條「1. 2. 3.」編號條列")
    if not 80 <= clen(line) <= 260:
        errors.append(f"briefs.line {clen(line)} 字，規格是 80–260 字")
    paras = [p for p in re.split(r"\n\s*\n", memo) if p.strip()]
    if len(paras) < 2 or "重點" not in memo or len(re.findall(r"(?m)^\s*\d+\.\s", memo)) < 3:
        errors.append("briefs.memo 要先一段總結，再「重點：」加至少 3 條編號條列")
    if not 200 <= clen(memo) <= 520:
        errors.append(f"briefs.memo {clen(memo)} 字，規格是 200–520 字")
    for k in ("line", "memo", "report"):
        if re.search(r"[^\s] {2,}[^\s]", b.get(k, "")):
            errors.append(f"briefs.{k} 有連續兩個空格（常見原因是日期空白），請改寫")
    if "結論：" not in report:
        errors.append("briefs.report 要有一行「結論：」")
    pool = set()
    for s0 in walk_text({k: v for k, v in d.items() if k != "briefs"}):
        pool |= numset(s0)
    if tone:
        for sec in ("presentation", "qa"):
            if tone.get(sec):
                pool |= {abs(tone[sec]["score"]), float(tone[sec].get("uncertainty", 0))}
    pool |= {float(len(qa)), float(len(items))}
    for st in STANCES:
        pool.add(float(sum(1 for q in qa if q.get("stance") == st)))
    for k in ("上修", "下修", "維持", "新增"):
        pool.add(float(sum(1 for it in items if it.get("vs_prior") == k)))
    pool |= {1.0, 0.0}
    for k in ("line", "memo", "report"):
        txt = re.sub(r"(?m)^\s*\d+\.\s", "", b.get(k, ""))      # 去掉條列編號
        txt = re.sub(r"(?m)^[一二三四五六七八九十]+、", "", txt)
        miss = sorted({x for x in numset(txt) if x not in pool and round(x / 10, 4) not in pool}, key=float)
        if miss:
            errors.append(f"briefs.{k} 的數字 {'、'.join(f'{x:g}' for x in miss)} 在儀表板資料裡找不到；報告稿的每個數字都要出自已查證的內容")


def check_html_motion(h, errors, warns):
    if re.search(r"""(src|href)\s*=\s*["']\s*(https?:)?//""", h, re.I) or re.search(r"@import|url\(\s*['\"]?https?:", h, re.I):
        errors.append("HTML 載入了外部資源，必須是單檔、離線可開")
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', h, re.S)
    if not m:
        errors.append("互動版找不到內嵌資料（id=data）")
    else:
        try:
            json.loads(m.group(1).replace("<\\/", "</"))
        except Exception as ex:  # noqa
            errors.append(f"互動版內嵌資料無法解析：{ex}")
    if re.search(r"localStorage|sessionStorage", h):
        errors.append("互動版不可使用瀏覽器儲存空間")
    for img in re.findall(r"<img[^>]*>", h):
        if 'alt="' not in img or 'alt=""' in img:
            errors.append("有圖片沒有 alt 文字")
    if "跳至主要內容" not in h:
        errors.append("缺少「跳至主要內容」連結")
    if "prefers-reduced-motion" not in h:
        errors.append("互動版缺少「減少動態」設定")


def check_html(h, errors, warns):
    if re.search(r"""(src|href)\s*=\s*["']\s*(https?:)?//""", h, re.I) or re.search(r"@import|url\(\s*['\"]?https?:", h, re.I):
        errors.append("HTML 載入了外部資源，必須是單檔、離線可開")
    css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", h, re.S)) + " " + " ".join(re.findall(r'style="([^"]*)"', h))
    css_flat = css.replace(" ", "")
    for c in set(re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\)", css_flat)):
        cc = c.lower()
        if cc not in ALLOWED_COLORS:
            errors.append(f"出現色票以外的顏色 {c}")
    svg_colors = set(re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,6})"', h))
    for c in svg_colors:
        if c.lower() not in ALLOWED_COLORS:
            errors.append(f"圖示使用色票以外的顏色 {c}")
    if re.search(r"font-weight\s*:\s*(800|900|bolder)", css):
        errors.append("出現 font-weight 800／900，規格只允許 400–700")
    for r in re.findall(r"border-radius\s*:\s*([^;}\"]+)", css):
        for v in r.split():
            if v not in ALLOWED_RADIUS:
                errors.append(f"出現規格外的圓角 {v}")
    acc = len(re.findall(r'class="acc"[^>]*>:::</a>', h))
    if acc != 3:
        errors.append(f"無障礙定位點 ::: 應有 3 個，目前 {acc} 個")
    for img in re.findall(r"<img[^>]*>", h):
        if 'alt="' not in img or 'alt=""' in img:
            errors.append("有圖片沒有 alt 文字")
    mods = re.findall(r'<div class="mod"', h)
    heads = re.findall(r'class="filter-name mod-head"', h)
    if len(mods) != len(heads):
        errors.append("有模組缺少標題列")
    if not mods:
        errors.append("頁面沒有任何模組")
    if "跳至主要內容" not in h:
        errors.append("缺少「跳至主要內容」連結")


def check_mobile(path, warns, errors):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        warns.append("沒有安裝 playwright，略過 375px 寬度檢查")
        return
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 375, "height": 812})
            pg.goto("file://" + path)
            sw = pg.evaluate("document.documentElement.scrollWidth")
            b.close()
        if sw > 376:
            errors.append(f"375px 寬度下出現橫向捲軸（頁面寬 {sw}px）")
    except Exception as ex:  # noqa
        warns.append(f"375px 寬度檢查無法執行：{ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", required=True)
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--keywords")
    ap.add_argument("--html", required=True)
    ap.add_argument("--tone")
    ap.add_argument("--prior-transcript")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    import os
    d = json.load(open(a.dashboard, encoding="utf-8"))
    t = json.load(open(a.transcript, encoding="utf-8"))
    kw = json.load(open(a.keywords, encoding="utf-8")) if a.keywords else None
    h = open(a.html, encoding="utf-8").read()
    errors, warns = [], []
    pt = json.load(open(a.prior_transcript, encoding="utf-8")) if a.prior_transcript else None
    tone = json.load(open(a.tone, encoding="utf-8")) if a.tone else None
    check_content(d, t, kw, errors, warns)
    check_deep(d, t, errors, warns)
    motion = 'id="data"' in h
    if motion:
        check_extra(d, t, pt, tone, errors, warns)
        check_html_motion(h, errors, warns)
    else:
        check_html(h, errors, warns)
    if not a.no_browser:
        check_mobile(os.path.abspath(a.html), warns, errors)
    out = {"ok": not errors, "errors": errors, "warnings": warns}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
