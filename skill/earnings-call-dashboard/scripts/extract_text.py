#!/usr/bin/env python3
"""
把法說會逐字稿（.docx / .pdf / .txt / .md / TEJ 逐字稿 .xlsx）轉成結構化的 transcript.json，
並另外輸出一份加上標記、方便閱讀的 transcript_labeled.txt。

用法：
    python extract_text.py <逐字稿檔案> --outdir <輸出資料夾>

輸出：
    transcript.json          段落、發言人、角色、講稿或 Q&A
    transcript_labeled.txt   每段開頭標 [編號][講稿/Q&A][角色] 發言人：
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
import zipfile
from xml.etree import ElementTree as ET

# ---------- 讀檔 ----------

def read_text_file(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_docx(path):
    try:
        import docx  # python-docx
        d = docx.Document(path)
        lines = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                cells = [c.text.strip() for c in row.cells]
                lines.append("　".join(c for c in cells if c))
        return "\n".join(lines)
    except ImportError:
        pass
    # 沒有 python-docx 時直接讀 XML
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    out = []
    for p in root.iter(ns + "p"):
        out.append("".join(t.text or "" for t in p.iter(ns + "t")))
    return "\n".join(out)


def read_pdf(path):
    errors = []
    import logging
    logging.disable(logging.WARNING)  # pdfminer 對中文字型常會印出大量無害警告
    try:
        text = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"], capture_output=True, text=True).stdout
        if text.strip():
            return text
    except Exception as e:  # noqa
        errors.append(f"pdftotext: {e}")
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        if text.strip():
            return text
    except Exception as e:  # noqa
        errors.append(f"pdfplumber: {e}")
    try:
        from pypdf import PdfReader
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
        if text.strip():
            return text
    except Exception as e:  # noqa
        errors.append(f"pypdf: {e}")
    raise RuntimeError("PDF 讀不到文字，可能是掃描檔（圖片）。請改用可選取文字的 PDF 或 Word 檔。" + "；".join(errors))


def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".markdown", ".text"):
        return read_text_file(path), ext.lstrip(".")
    if ext == ".docx":
        return read_docx(path), "docx"
    if ext == ".pdf":
        return read_pdf(path), "pdf"
    if ext == ".doc":
        raise RuntimeError("不支援舊版 .doc，請另存成 .docx 或 .pdf 再上傳。")
    # 不認得的副檔名就當純文字試試看
    return read_text_file(path), ext.lstrip(".") or "txt"

# ---------- 清理 ----------

PAGE_NO = re.compile(r"^\s*(\d{1,3}|-\s*\d+\s*-|第\s*\d+\s*頁(\s*/\s*共\s*\d+\s*頁)?|\d+\s*/\s*\d+|Page\s+\d+(\s+of\s+\d+)?)\s*$", re.I)


# PDF 常把一般漢字抽成外觀相同的「部首」或「相容」字元（例如 ⼈→人、⻑→長），比對會失敗，要轉回來
RADICAL_SUPPLEMENT = {
    "⺠": "民", "⺟": "母", "⻑": "長", "⻄": "西", "⻝": "食", "⻘": "青", "⻆": "角", "⻅": "見",
    "⻉": "貝", "⻋": "車", "⻔": "門", "⻢": "馬", "⻣": "骨", "⻤": "鬼", "⻥": "魚", "⻦": "鳥",
    "⻨": "麥", "⻩": "黃", "⻬": "齊", "⻮": "齒", "⻯": "竜", "⻰": "龍", "⻳": "龜", "⺩": "王",
    "⺮": "竹", "⺶": "羊", "⺻": "聿", "⻁": "虎", "⻈": "言", "⻌": "辶", "⺾": "艹", "⺍": "小",
    "⺁": "厂", "⺅": "亻", "⺉": "刂", "⺌": "小", "⺗": "心", "⺡": "氵", "⺨": "犭", "⺮": "竹",
}


def fix_cjk(text):
    import unicodedata
    out = []
    for ch in text:
        o = ord(ch)
        if 0x2F00 <= o <= 0x2FDF or 0xF900 <= o <= 0xFAFF or 0x2F800 <= o <= 0x2FA1F:
            out.append(unicodedata.normalize("NFKC", ch))
        elif 0x2E80 <= o <= 0x2EFF:
            out.append(RADICAL_SUPPLEMENT.get(ch, ch))
        else:
            out.append(ch)
    return "".join(out)


def clean(text):
    text = fix_cjk(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("　", " ").replace("\xa0", " ")
    raw_lines = [ln.strip() for ln in text.split("\n")]
    # 每頁重複出現的頁首、頁尾、版權聲明（出現 3 次以上、不是發言人標記的行）
    from collections import Counter
    freq = Counter(l for l in raw_lines if len(l) >= 12)
    boiler = {l for l, c in freq.items() if c >= 3 and not match_speaker(l)}
    lines = []
    for s in raw_lines:
        if PAGE_NO.match(s) or s in boiler:
            continue
        lines.append(s)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()

# ---------- 分段與發言人 ----------

MGMT = r"董事長|副董事長|總經理|副總經理|執行長|營運長|財務長|技術長|發言人|代理發言人|副總裁|總裁|副總|協理|處長|資深經理|經理|特助|投資人關係|IR|CEO|CFO|COO|CTO|President|Chairman|Vice President|VP|Director|Head of|Investor Relations"
HOST = r"主持人|司儀|會議主持|投資人關係|法人關係|Operator|Moderator|Host|Investor Relations|\bIR\b"
ANALYST = r"分析師|研究員|研究部|投信|投顧|證券|證券投資|資產管理|投資|基金|保險|外資|法人|媒體|記者|股東|Analyst|Research|Securities|Capital|Investment|Asset"

QA_MARK = re.compile(
    r"^(#+\s*)?(#QA_START|Q\s*&\s*A(\s*Session)?|QA|問答(時間|環節|階段)?|問與答|提問(時間|與回答)?|開放提問|綜合座談|Question[s]?\s*(and|&)\s*Answer[s]?)\s*[:：]?\s*$",
    re.I,
)
QA_INLINE = re.compile(r"(進入|開放|開始)(問答|提問|Q\s*&\s*A)|接下來.{0,6}(問答|提問|Q\s*&\s*A)|open (the|it) (up )?(for|to) questions", re.I)
ROSTER_MARK = re.compile(r"^(CORPORATE PARTICIPANTS|CONFERENCE CALL PARTICIPANTS|PARTICIPANTS|出席人員|與會人員|公司出席人員)\s*[:：]?\s*$", re.I)
END_MARK = re.compile(r"^(DISCLAIMER|免責聲明)\s*[:：]?\s*$", re.I)
PRES_MARK = re.compile(r"^(#+\s*)?(逐字稿|簡報|公司簡報|營運報告|Presentation|Prepared Remarks)\s*[:：]?\s*$", re.I)

# 發言人標記的幾種寫法
SPEAKER_PATTERNS = [
    # Jeff Su - Taiwan Semiconductor Manufacturing Company Limited - Director of Investor Relations
    re.compile(r"^(?P<name>[A-Z][\w.'’]*(?:[ \-][A-Z][\w.'’]*){0,4}|Unidentified (?:Participant|Company Representative|Analyst))\s+[-–—]\s+(?P<org>[^:：]{2,90}?)\s+[-–—]\s+(?P<title>[^:：]{2,120})$"),
    re.compile(r"^(?P<name>Operator|Moderator|Unidentified Participant|Unidentified Company Representative)\s*[:：]?\s*(?P<rest>.*)$"),
    # **王大明 - 範例科技, 總經理**   或  **王大明，總經理**
    re.compile(r"^\*\*(?P<name>[^*\-–—,，:：]{1,20})\s*[-–—]\s*(?P<org>[^*,，]{1,40})[,，]\s*(?P<title>[^*]{1,30})\*\*\s*[:：]?\s*(?P<rest>.*)$"),
    re.compile(r"^\*\*(?P<name>[^*,，:：]{1,20})[,，]\s*(?P<title>[^*]{1,30})\*\*\s*[:：]?\s*(?P<rest>.*)$"),
    re.compile(r"^\*\*(?P<name>[^*:：]{1,30})\*\*\s*[:：]?\s*(?P<rest>.*)$"),
    # 王大明（總經理）：  /  王大明(範例科技 總經理):
    re.compile(r"^(?P<name>[^\s（(：:]{1,12})\s*[（(](?P<title>[^）)]{1,30})[）)]\s*[:：]\s*(?P<rest>.*)$"),
    # 總經理 王大明：  /  財務長李小華：
    re.compile(rf"^(?P<title>{MGMT}|{HOST})\s*(?P<name>[一-鿿]{{2,4}})\s*[:：]\s*(?P<rest>.*)$"),
    # 王大明 總經理：
    re.compile(rf"^(?P<name>[一-鿿]{{2,4}})\s*(?P<title>{MGMT}|{HOST})\s*[:：]\s*(?P<rest>.*)$"),
    # 某某投信 分析師：  /  元大證券研究員 陳小明：  /  ABC Securities Analyst:
    re.compile(r"^(?P<org>[^\s：:，,。]{1,20}?)\s*(?P<title>分析師|研究員|研究部|經理人|基金經理人|記者|Analyst)\s*(?P<name>[一-鿿A-Za-z ]{0,12}?)\s*[:：]\s*(?P<rest>.*)$", re.I),
    # Q: / A: / 問： / 答： / 提問： / 回答：
    re.compile(r"^(?P<qa>Q|A|問|答|提問|回答|Question|Answer)\s*\d*\s*[:：.、]\s*(?P<rest>.*)$", re.I),
    # 某某證券 陳分析師：  /  主持人：  /  王大明：
    re.compile(r"^(?P<name>[^\s：:，,。]{1,16})\s*[:：]\s*(?P<rest>.*)$"),
]


def classify(title, name, org=""):
    blob = " ".join(x for x in (title, name, org) if x)
    if re.search(HOST, blob, re.I):
        return "host"
    if re.search(ANALYST, title or "", re.I) or (not title and re.search(ANALYST, blob, re.I)):
        return "analyst"
    if re.search(MGMT, blob, re.I):
        return "management"
    if re.search(ANALYST, blob, re.I):
        return "analyst"
    return "unknown"


def match_speaker(line):
    for i, pat in enumerate(SPEAKER_PATTERNS):
        m = pat.match(line)
        if not m:
            continue
        g = m.groupdict()
        if g.get("qa"):
            tag = g["qa"].lower()
            role = "analyst" if tag in ("q", "問", "提問", "question") else "management"
            return {"name": "提問者" if role == "analyst" else "回答者", "title": "", "org": "", "role": role,
                    "rest": g.get("rest", "").strip(), "pattern": i}
        name = (g.get("name") or "").strip()
        title = (g.get("title") or "").strip()
        org = (g.get("org") or "").strip()
        if not name:
            name = f"{org}{title}" if org else title
        # 最後一個寬鬆規則：避免把「營收：52 億」這種內文誤判成發言人
        if i == len(SPEAKER_PATTERNS) - 1:
            if not (re.search(MGMT, name, re.I) or re.search(HOST, name, re.I) or re.search(ANALYST, name, re.I)
                    or re.fullmatch(r"[一-鿿]{2,4}", name) or re.fullmatch(r"[A-Z][a-z]+( [A-Z][a-z]+){0,2}", name)):
                continue
            if re.search(r"\d", name):
                continue
        # 有些格式只有名字，職稱寫在名字裡（例如「主持人」）
        if not title and re.search(f"{MGMT}|{HOST}", name, re.I):
            title = name
        return {"name": name, "title": title, "org": org, "role": classify(title, name, org),
                "rest": g.get("rest", "").strip(), "pattern": i}
    return None


def segment(text):
    segs = []
    section = "presentation"
    qa_by = "none"
    cur = None
    warnings = []

    def push():
        nonlocal cur
        if cur and cur["text"].strip():
            cur["text"] = re.sub(r"\s*\n\s*", "", cur["text"]).strip() if re.search(r"[一-鿿]", cur["text"]) else re.sub(r"\s+", " ", cur["text"]).strip()
            segs.append(cur)
        cur = None

    roster = []
    in_roster = False
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if END_MARK.match(line):
            break
        if ROSTER_MARK.match(line):
            push(); in_roster = True; continue
        if in_roster:
            if PRES_MARK.match(line) or QA_MARK.match(line):
                in_roster = False
            else:
                roster.append(line)
                continue
        if QA_MARK.match(line):
            push(); section = "qa"; qa_by = "marker"; continue
        if PRES_MARK.match(line) and section == "presentation":
            push(); continue
        sp = match_speaker(line)
        if sp:
            push()
            if section == "presentation" and sp["role"] == "analyst":
                section = "qa"; qa_by = "speaker"
            cur = {"section": section, "speaker": sp["name"], "title": sp["title"], "org": sp["org"],
                   "role": sp["role"], "text": sp["rest"]}
        else:
            if cur is None:
                cur = {"section": section, "speaker": "", "title": "", "org": "", "role": "unknown", "text": ""}
            sep = "" if re.search(r"[一-鿿　-〿＀-￯]$", cur["text"]) else " "
            cur["text"] += (sep if cur["text"] else "") + line
        if section == "presentation" and QA_INLINE.search(line):
            push(); section = "qa"; qa_by = "marker"
    push()

    # 同一位發言人的角色補齊（例如後面才出現職稱）
    known = {}
    for s in segs:
        if s["speaker"] and s["role"] != "unknown":
            known.setdefault(s["speaker"], (s["role"], s["title"]))
    for s in segs:
        if s["role"] == "unknown" and s["speaker"] in known:
            s["role"], t = known[s["speaker"]]
            s["title"] = s["title"] or t

    for i, s in enumerate(segs, 1):
        s["i"] = i

    if qa_by == "none":
        warnings.append("沒有找到 Q&A 段落的標記，也沒有辨識到分析師發言，全部視為講稿。請確認這份逐字稿是否沒有 Q&A。")
    unknown = sum(1 for s in segs if s["role"] == "unknown")
    if segs and unknown / len(segs) > 0.3:
        warnings.append(f"{unknown}/{len(segs)} 段無法判斷發言人角色，語調分數可能不準，請人工確認發言人。")
    if not any(s["role"] == "management" for s in segs):
        warnings.append("沒有辨識到管理層發言人（董事長、總經理、財務長等），語調分析會沒有資料。")

    speakers = {}
    for s in segs:
        key = s["speaker"] or "（未標示）"
        sp = speakers.setdefault(key, {"name": key, "title": s["title"], "org": s["org"], "role": s["role"],
                                       "segments": 0, "sections": set()})
        sp["segments"] += 1
        sp["sections"].add("簡報" if s["section"] == "presentation" else "Q&A")
    sp_list = []
    for v in speakers.values():
        v["sections"] = "、".join(x for x in ("簡報", "Q&A") if x in v["sections"])
        sp_list.append(v)
    return segs, sp_list, qa_by, warnings, roster


ROLE_ZH = {"management": "管理層", "analyst": "提問方", "host": "主持人", "unknown": "未知"}


def speaker_list(segs):
    speakers = {}
    for s in segs:
        key = s["speaker"] or "（未標示）"
        sp = speakers.setdefault(key, {"name": key, "title": s["title"], "org": s.get("org", ""), "role": s["role"],
                                       "segments": 0, "sections": set()})
        sp["segments"] += 1
        sp["sections"].add("簡報" if s["section"] == "presentation" else "Q&A")
    out = []
    for v in speakers.values():
        v["sections"] = "、".join(x for x in ("簡報", "Q&A") if x in v["sections"])
        out.append(v)
    return out

# ---------- TEJ 逐字稿資料庫（xlsx） ----------
# 欄位：Company Code、Company Name、Investor Conference date、Conference No.、Content Oder.、
#       Line Breaker Oder.、Content、Segment type（報告／提問／回答）、Speaker title、Speaker name、English(Y/N)

XLSX_HOST = re.compile(r"主持人|司儀|投資人關係|法人關係|^IR$|發言人室", re.I)
XLSX_ANALYST = re.compile(r"分析師|投資人|研究員|記者|法人$")


def load_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = []
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        head = next(it, None)
        if not head or "Content" not in head or "Segment type" not in head:
            continue
        head = [str(h).strip() if h is not None else "" for h in head]
        for r in it:
            d = dict(zip(head, r))
            if d.get("Content") in (None, ""):
                continue
            rows.append(d)
    if not rows:
        raise RuntimeError("這份 Excel 不是 TEJ 逐字稿格式（找不到 Content、Segment type 欄位）。")
    return rows


def call_key(r):
    return (str(r.get("Company Code") or "").strip(), str(r.get("Investor Conference date") or "").strip()[:8],
            str(r.get("Conference No.") or "1").strip())


def list_calls(rows):
    calls = {}
    for r in rows:
        k = call_key(r)
        c = calls.setdefault(k, {"id": f"{k[0]}:{k[1]}:{k[2]}", "code": k[0], "company": str(r.get("Company Name") or ""),
                                 "date": k[1], "no": k[2], "rows": 0, "description": str(r.get("Description") or "")[:40],
                                 "english": str(r.get("English(Y/N)") or "N"), "has_qa": False})
        c["rows"] += 1
        if str(r.get("Segment type")) == "提問":
            c["has_qa"] = True
    return sorted(calls.values(), key=lambda c: (c["code"], c["date"], c["no"]))


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def xlsx_segments(rows):
    rows = sorted(rows, key=lambda r: (_num(r.get("Content Oder.")), _num(r.get("Line Breaker Oder."))))
    groups = []
    for r in rows:
        co = r.get("Content Oder.")
        if groups and groups[-1]["co"] == co:
            groups[-1]["text"].append(str(r["Content"]).strip())
        else:
            groups.append({"co": co, "type": str(r.get("Segment type") or "").strip(),
                           "title": str(r.get("Speaker title") or "").strip(),
                           "name": str(r.get("Speaker name") or "").strip(), "text": [str(r["Content"]).strip()]})
    segs, section = [], "presentation"
    for g in groups:
        if g["type"] == "提問":
            section = "qa"
        title, name = g["title"], g["name"]
        # 職稱優先：主持人轉述問題時，資料庫常把段落類型標成「提問」
        if XLSX_HOST.search(title):
            role = "host"
        elif g["type"] == "提問" or XLSX_ANALYST.search(title):
            role = "analyst"
        else:
            role = "management"
        txt = fix_cjk("".join(g["text"]) if re.search(r"[一-鿿]", "".join(g["text"])) else " ".join(g["text"]))
        segs.append({"section": section, "speaker": name or title, "title": title, "org": "", "role": role,
                     "text": txt, "segment_type": g["type"]})
    segs, dropped = dedupe(segs)
    for i, s in enumerate(segs, 1):
        s["i"] = i
    return segs, dropped


FILLER = re.compile(r"\b(uh|um|er|ah|you know)\b|[嗯呃啊]|\.{2,}|…", re.I)


def _norm_for_dup(t):
    t = FILLER.sub("", t.lower())
    t = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", t)   # how how → how
    return re.sub(r"[\W_]+", "", t)


def dedupe(segs):
    """逐字稿資料庫偶爾會把同一段落重複收錄（第二份常多了 uh、um），重複的段落會灌水語調與關鍵字次數，要拿掉。"""
    import difflib
    keep, dropped, seen = [], [], []
    for s in segs:
        n = _norm_for_dup(s["text"])
        dup = False
        if len(n) >= 60:
            for prev_speaker, pn in seen:
                if prev_speaker != s["speaker"] or abs(len(pn) - len(n)) > 0.2 * max(len(pn), len(n)):
                    continue
                if pn == n or difflib.SequenceMatcher(None, pn, n, autojunk=False).quick_ratio() > 0.95 and \
                        difflib.SequenceMatcher(None, pn, n, autojunk=False).ratio() > 0.9:
                    dup = True
                    break
        if dup:
            dropped.append(s["text"][:40])
        else:
            keep.append(s)
            seen.append((s["speaker"], n))
    return keep, dropped


QCUE = re.compile(r"請問|想請教|請教一下|下一位提問|my (?:first |second |last )?question|next question|line is open|ask questions", re.I)
IRTITLE = re.compile(r"法人關係|投資人關係|Investor Relations|\bIR\b", re.I)
LOOP = re.compile(r"(.{20,300}?)(?:\s*\1){2,}", re.S)
SENT = re.compile(r"(?<=[。！？!?])|(?<=[.?!])\s+")


def dedupe_sentences(segs, min_len=60):
    """刪除重複收錄的長句（TEJ 偶爾把同一段問答重複收錄上百次）。
    只刪 60 字以上、一字不差的句子，第一次出現的保留。回傳被刪掉的字數。"""
    seen, removed = set(), 0
    for sg in segs:
        out = []
        for sent in SENT.split(sg["text"]):
            key = re.sub(r"\s+", " ", sent).strip()
            if len(key) >= min_len and key in seen:
                removed += len(sent)
                continue
            if len(key) >= min_len:
                seen.add(key)
            out.append(sent)
        if removed:
            sg["text"] = "".join(x if re.search(r"[。！？]$", x) else x + " " for x in out).strip()
        # 轉寫系統卡住時，同一串短句會連續重複上百次：連續出現三次以上的片段只留一次
        before = len(sg["text"])
        sg["text"] = LOOP.sub(r"\1", sg["text"])
        removed += before - len(sg["text"])
    return removed


def similarity(a, b, k=6):
    """兩份逐字稿的相似度：6 字一組的片段重疊比例（去掉空白與標點）。
    校準結果：重複收錄約 0.85；正常的中文場次 0.01–0.04，英文場次最高約 0.32，所以門檻定在 0.7。"""
    def grams(t):
        t = re.sub(r"[\s，。、：；！？,.:;!?…「」『』（）()]", "", t)
        return {t[i:i + k] for i in range(0, max(0, len(t) - k))}
    ga, gb = grams(a), grams(b)
    return len(ga & gb) / max(1, min(len(ga), len(gb)))


def pick_call(rows, want):
    calls = list_calls(rows)
    if want:
        parts = want.split(":")
        hit = [c for c in calls if c["code"] == parts[0] and (len(parts) < 2 or c["date"] == parts[1])
               and (len(parts) < 3 or c["no"] == parts[2])]
        if not hit:
            raise RuntimeError(f"找不到場次 {want}。請先用 --list 查看可用場次。")
        if len(hit) > 1:
            raise RuntimeError(f"{want} 對應到 {len(hit)} 場，請加上日期：" + "、".join(c["id"] for c in hit))
        return hit[0], calls
    if len(calls) == 1:
        return calls[0], calls
    raise RuntimeError(f"這份 Excel 有 {len(calls)} 場法說會，請用 --call 指定（例如 --call 2330:20260716），或先用 --list 查看。")


def write_outputs(outdir, data):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "transcript.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(outdir, "transcript_labeled.txt"), "w", encoding="utf-8") as f:
        for s in data["segments"]:
            who = s["speaker"] + (f"（{s['title']}）" if s["title"] and s["title"] != s["speaker"] else "")
            sec = "講稿" if s["section"] == "presentation" else "Q&A"
            f.write(f"[{s['i']}][{sec}][{ROLE_ZH[s['role']]}] {who}：{s['text']}\n\n")


def build_data(source, fmt, segs, qa_by, warnings, roster=None, meta=None):
    full = "\n".join(s["text"] for s in segs)
    return {
        "ok": True, "source_file": source, "format": fmt, "char_count": len(full),
        "has_qa": any(s["section"] == "qa" for s in segs), "qa_detected_by": qa_by,
        "meta_hint": meta or {}, "speakers": speaker_list(segs), "roster": roster or [],
        "segments": segs, "warnings": warnings, "full_text": full,
    }


def brief(data):
    out = {k: data[k] for k in ("ok", "source_file", "format", "char_count", "has_qa", "qa_detected_by", "warnings")}
    out["segments"] = len(data["segments"])
    if data.get("meta_hint"):
        out["meta_hint"] = data["meta_hint"]
    if data.get("roster"):
        out["roster"] = data["roster"]
    out["speakers"] = [{k: v[k] for k in ("name", "title", "role", "segments", "sections")} for v in data["speakers"]]
    return out


def run_xlsx(a):
    rows = load_xlsx(a.input)
    if a.list:
        calls = list_calls(rows)
        if a.company:
            calls = [c for c in calls if a.company in (c["code"], c["company"])]
        print(json.dumps({"ok": True, "calls": len(calls), "list": calls}, ensure_ascii=False, indent=1))
        return
    call, calls = pick_call(rows, a.call)
    key = (call["code"], call["date"], call["no"])

    def make(c):
        k = (c["code"], c["date"], c["no"])
        segs, dropped = xlsx_segments([r for r in rows if call_key(r) == k])
        before = sum(len(s["text"]) for s in segs)
        cut = dedupe_sentences(segs)
        tot = sum(len(s["text"]) for s in segs) or 1
        warn = [] if any(s["section"] == "qa" for s in segs) else ["這場沒有提問段落（Segment type 沒有「提問」），Q&A 相關模組會顯示「本場無 Q&A」。"]
        if tot < 500:
            warn.append(f"這場逐字稿只有 {tot} 字，內容不足以做成儀表板；請向資料來源確認是否收錄不完整。")
        if cut > before * 0.05:
            warn.append(f"逐字稿裡有大量重複收錄的句子，已刪除 {cut:,} 字（原本 {before:,} 字，約 {cut / before:.0%}）；"
                        "同一句話第一次出現的位置保留。")
        if dropped:
            warn.append(f"移除 {len(dropped)} 段重複收錄的段落（內容與前面幾乎相同）：" + "；".join(x + "…" for x in dropped[:3]))
        meta = {"company": c["company"], "ticker": c["code"], "date": f"{c['date'][:4]}-{c['date'][4:6]}-{c['date'][6:8]}",
                "conference_no": c["no"], "description": c["description"], "english": c["english"]}
        # TEJ 偶爾把整場標成同一位發言人（例如整場都是「主持人」），這時角色與講稿／Q&A 都不可靠
        tot = sum(len(s["text"]) for s in segs) or 1
        share, role_of = collections.Counter(), {}
        for s in segs:
            k = (s.get("speaker") or "") + "|" + (s.get("title") or "")
            share[k] += len(s["text"]); role_of[k] = s["role"]
        who, top = share.most_common(1)[0] if share else ("", 0)
        # 九成以上標成同一人：若那人不是管理層（例如整場都是「主持人」），或內容很長，就視為標記異常
        top_text = " ".join(s["text"] for s in segs if (s.get("speaker") or "") + "|" + (s.get("title") or "") == who)
        cues = len(QCUE.findall(top_text))          # 這個人的發言裡混了幾次提問用語
        presenter = role_of.get(who) == "management" or IRTITLE.search(who)
        blob = top / tot > 0.9 and tot > 5000 and (not presenter or cues >= 3)
        if blob:
            warn.append(f"TEJ 把這場 {top / tot:.0%} 的內容標成同一位發言人（{who.strip('|').replace('|', '，')}），"
                        "管理層與分析師、講稿與 Q&A 都無法自動分開；語調分數改用全文計算，僅供參考。寫內容時要自己從文字判斷誰在說話、Q&A 從哪裡開始。")
        d = build_data(os.path.basename(a.input) + f"（{c['company']} {c['date']}）", "xlsx", segs, "xlsx", warn, meta=meta)
        d["speaker_blob"] = blob
        return d

    data = make(call)
    write_outputs(a.outdir, data)
    result = brief(data)
    if a.prior:
        prev = [c for c in calls if c["code"] == call["code"] and (c["date"], c["no"]) < (call["date"], call["no"])]
        if prev:
            p = prev[-1]
            pdata = make(p)
            write_outputs(os.path.join(a.outdir, "prior"), pdata)
            sim = similarity(data["full_text"], pdata["full_text"])
            result["prior_similarity"] = round(sim, 3)
            if sim > 0.7:
                msg = (f"這場和上一場（{pdata['meta_hint']['date']}）的內容相似度 {sim:.0%}，可能是 TEJ 重複收錄同一場法說會。"
                       "請比對兩份逐字稿講的期間是否相同；若相同，摘要要寫明，未來展望不要和上一場比較。")
                data["warnings"].append(msg)
                if msg not in result.get("warnings", []):
                    result["warnings"] = result.get("warnings", []) + [msg]
                write_outputs(a.outdir, data)
            result["prior"] = {"id": p["id"], "date": pdata["meta_hint"]["date"], "description": p["description"],
                               "segments": len(pdata["segments"]), "outdir": os.path.join(a.outdir, "prior")}
        else:
            result["prior"] = None
            result["warnings"] = result["warnings"] + ["這份 Excel 裡沒有同一家公司更早的場次，未來展望無法和上一場比較。"]
    print(json.dumps(result, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--list", action="store_true", help="xlsx：列出檔案裡所有場次")
    ap.add_argument("--company", help="xlsx：搭配 --list，只列出這家公司（代號或簡稱）")
    ap.add_argument("--call", help="xlsx：指定場次，格式 代號[:日期YYYYMMDD[:場次編號]]，例如 2330:20260716")
    ap.add_argument("--prior", action="store_true", help="xlsx：一併取出同公司的上一場，存到 outdir/prior/")
    a = ap.parse_args()
    try:
        if os.path.splitext(a.input)[1].lower() in (".xlsx", ".xlsm"):
            run_xlsx(a)
            return
        raw, fmt = read_any(a.input)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)
    text = clean(raw)
    if len(text) < 200:
        print(json.dumps({"ok": False, "error": f"只讀到 {len(text)} 個字，檔案可能是空的或是圖片。"}, ensure_ascii=False))
        sys.exit(1)
    segs, _speakers, qa_by, warnings, roster = segment(text)
    data = build_data(os.path.basename(a.input), fmt, segs, qa_by, warnings, roster)
    data["full_text"] = text
    write_outputs(a.outdir, data)
    print(json.dumps(brief(data), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
