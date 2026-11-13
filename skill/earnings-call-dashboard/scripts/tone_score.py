#!/usr/bin/env python3
"""
用詞表計算管理層在「講稿」與「Q&A 回答」的語調分數。

用法：
    python tone_score.py <transcript.json> --out tone.json [--lexicon ../assets/lexicon.json]

分數 = (正向詞數 − 負向詞數) / (正向詞數 + 負向詞數)，範圍 −1 到 +1。
只計算管理層（role = management）的發言；主持人、提問方不計。
規則：
  - 先比對較長的詞，同一段文字不重複計算（例如「不確定性」不會再算一次「不確定」）
  - 詞前 3 個字內出現否定詞（不、未、沒有…）時，正負反轉
  - context_flip 的詞前 8 個字內出現指定主詞時，正負反轉（例如「負債比下降」算正向）
  - 正向詞後 6 個字內出現 post_hedges（仍不明朗、尚待觀察…）時，改計為不確定
  - uncertainty 詞只計次數，不影響分數
  - 計分前先遮掉公司名稱（例如「佳世達」的「佳」不算正向詞），遮罩長度不變，原文位置不受影響
  - 正負詞合計少於 MIN_TERMS 個時，標示「詞數太少」，分數僅供參考
"""
import argparse
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_TERMS = 10


def mask_names(text, names):
    """把公司名稱換成等長的遮罩字元，避免名稱裡的字被當成語調詞。"""
    for n in sorted({x for x in names if x}, key=len, reverse=True):
        text = text.replace(n, "＿" * len(n))
    return text


def company_names(t, extra=()):
    mh = t.get("meta_hint") or {}
    names = [mh.get("company", "").rstrip("*＊")] + list(extra)
    return [n for n in names if n]


def load_lex(path):
    lx = json.load(open(path, encoding="utf-8"))
    terms = []
    for cat in ("positive", "negative", "uncertainty"):
        for w in lx.get(cat, []):
            terms.append((w, cat))
    terms.sort(key=lambda t: -len(t[0]))
    flips = {k: v for k, v in lx.get("context_flip", {}).items() if not k.startswith("_")}
    return terms, lx.get("negators", []), set(lx.get("exclude", [])), flips, lx.get("post_hedges", [])


def score_text(text, terms, negators, exclude, flips, hedges=()):
    used = [False] * len(text)
    pos, neg, unc = Counter(), Counter(), Counter()
    for w, cat in terms:
        if w in exclude:
            continue
        for m in re.finditer(re.escape(w), text):
            a, b = m.start(), m.end()
            if any(used[a:b]):
                continue
            for k in range(a, b):
                used[k] = True
            if cat == "uncertainty":
                unc[w] += 1
                continue
            # 正向詞後面緊接「仍不明朗」「尚待觀察」這類保留語，改算成不確定
            if cat == "positive" and any(h in text[b:b + 6] for h in hedges):
                unc[w + "（保留）"] += 1
                continue
            sign = 1 if cat == "positive" else -1
            before = text[max(0, a - 3):a]
            if any(n in before for n in negators):
                sign = -sign
            if w in flips:
                ctx = text[max(0, a - 8):a]
                if any(subj in ctx for subj in flips[w]):
                    sign = -sign
            (pos if sign > 0 else neg)[w] += 1
    return pos, neg, unc


def load_en(path):
    lx = json.load(open(path, encoding="utf-8"))
    terms = {}
    for cat in ("positive", "negative", "uncertainty"):
        for w in lx.get(cat + "_en", []):
            terms[w.lower()] = cat
    return terms, set(lx.get("negators_en", [])), set(lx.get("exclude_en", []))


WORD = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")


def score_en(text, terms, negators, exclude):
    """英文：以單字比對，片語（remain to be seen）另外處理；詞前 3 個單字內有否定詞時正負反轉。"""
    pos, neg, unc = Counter(), Counter(), Counter()
    low = text.lower()
    for ph, cat in terms.items():
        if " " in ph and cat == "uncertainty":
            c = len(re.findall(r"\b" + re.escape(ph) + r"\b", low))
            if c:
                unc[ph] += c
    words = [w.lower() for w in WORD.findall(text)]
    for i, w in enumerate(words):
        if w in exclude or w not in terms:
            continue
        cat = terms[w]
        if cat == "uncertainty":
            unc[w] += 1
            continue
        sign = 1 if cat == "positive" else -1
        prev = words[max(0, i - 3):i]
        if any(p in negators or p.endswith("n't") for p in prev):
            sign = -sign
        (pos if sign > 0 else neg)[w] += 1
    return pos, neg, unc


def select_segments(t):
    """決定要拿哪些發言計分。回傳 (段落清單, 計分範圍說明)。
    一般情況只算管理層；整場被標成同一人時改算全文；完全沒有管理層時改算法人關係人員。"""
    segs = t.get("segments", [])
    if t.get("speaker_blob"):
        return list(segs), "全文（逐字稿未分辨發言人）"
    mg = [s for s in segs if s["role"] == "management"]
    if mg:
        return mg, "管理層"
    ir = [s for s in segs if s["role"] == "host" and re.search(r"法人關係|投資人關係|發言人|Investor Relations|\bIR\b",
                                                                  (s.get("title") or "") + " " + (s.get("speaker") or ""), re.I)]
    if ir:
        return ir, "法人關係人員（未辨識到管理層）"
    if sum(len(x["text"]) for x in segs) >= 1500:     # 有內容但沒標出任何管理層或法人關係人員
        return list(segs), "全文（逐字稿未分辨發言人）"
    return [], "管理層"


def label(score, n=None):
    if n is not None and n < MIN_TERMS:
        return "詞數太少"
    if score >= 0.2:
        return "偏正向"
    if score <= -0.2:
        return "偏負向"
    return "接近中性"


def summarize(segs, terms, negators, exclude, flips, hedges, en=None, names=()):
    P, N, U = Counter(), Counter(), Counter()
    for s in segs:
        txt = mask_names(s["text"], names)
        p, n, u = score_text(txt, terms, negators, exclude, flips, hedges)
        P.update(p); N.update(n); U.update(u)
        if en:
            p, n, u = score_en(txt, *en)
            P.update(p); N.update(n); U.update(u)
    tp, tn = sum(P.values()), sum(N.values())
    sc = round((tp - tn) / (tp + tn), 2) if (tp + tn) else 0.0
    return {
        "score": sc,
        "label": label(sc, tp + tn),
        "positive": tp,
        "negative": tn,
        "uncertainty": sum(U.values()),
        "segments": len(segs),
        "chars": sum(len(x["text"]) for x in segs),
        "words": sum(len(WORD.findall(x["text"])) for x in segs),
        "top_positive": [w for w, _ in P.most_common(5)],
        "top_negative": [w for w, _ in N.most_common(5)],
        "top_uncertainty": [w for w, _ in U.most_common(5)],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--out", default="tone.json")
    ap.add_argument("--lexicon", default=os.path.join(HERE, "..", "assets", "lexicon.json"))
    ap.add_argument("--mask", nargs="*", default=[], help="另外要遮掉的名稱（子公司、品牌）")
    a = ap.parse_args()
    t = json.load(open(a.transcript, encoding="utf-8"))
    terms, negators, exclude, flips, hedges = load_lex(a.lexicon)
    en = load_en(a.lexicon)
    names = company_names(t, a.mask)
    mg, basis = select_segments(t)
    body = "".join(s["text"] for s in t["segments"])
    cjk = len(re.findall(r"[\u4e00-\u9fff]", body))
    lang = "zh" if cjk > len(body) * 0.2 else "en"
    pres = [s for s in mg if s["section"] == "presentation"]
    qa = [s for s in mg if s["section"] == "qa"]
    out = {
        "method": "詞表計分：(正向−負向)/(正向+負向)",
        "basis": basis,
        "language": lang,
        "presentation": summarize(pres, terms, negators, exclude, flips, hedges, en, names) if pres else None,
        "qa": summarize(qa, terms, negators, exclude, flips, hedges, en, names) if qa else None,
        "warnings": [],
    }
    if basis != "管理層":
        out["warnings"].append(f"計分範圍改為「{basis}」，分數不只反映管理層的語氣，僅供參考。")
    for k in ("presentation", "qa"):
        if out[k] and out[k]["label"] == "詞數太少":
            out["warnings"].append(f"{'講稿' if k == 'presentation' else 'Q&A'}只算到 {out[k]['positive'] + out[k]['negative']} 個正負詞，分數僅供參考。")
    if not pres:
        out["warnings"].append("講稿段落沒有管理層發言，無法計算講稿分數。")
    if not qa:
        out["warnings"].append("沒有 Q&A 的管理層回答，Q&A 分數顯示「本場無 Q&A」。")
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
