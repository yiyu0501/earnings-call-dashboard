#!/usr/bin/env python3
"""
互動版（預設輸出）：把 dashboard.json＋tone.json＋keywords.json＋逐字稿套進 assets/template_motion.html，產生單檔 HTML。

用法：
    python render_motion.py WORK/dashboard.json --tone WORK/tone.json --keywords WORK/keywords.json \
        --transcript WORK/transcript.json [--prior-transcript WORK/prior/transcript.json] --outdir WORK/out

- 逐字稿會一起包進頁面，讓每句原文都能「看上下文」；程式會算出每句原文在逐字稿的位置。
- 語調詞明細沿用 tone_score.py 的同一套規則，並和 tone.json 的總數核對。
- 深色模式用的 logo 由程式自動產生（深藍、黑色筆畫轉白）。
- 檔名：{股票代號}_{年份}Q{季}.html，與表格版（render.py）相同；兩種都要時，表格版加 --suffix。
"""
import argparse, base64, datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")

def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

def b64_dark(p):
    """深色模式用：把深藍與黑色的筆畫轉成白色，黃、綠保留，透明背景不變。"""
    import io
    from PIL import Image
    im = Image.open(p).convert("RGBA"); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, al = px[x, y]
            if al and (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 < 0.3:
                px[x, y] = (255, 255, 255, al)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

ap = argparse.ArgumentParser()
ap.add_argument("dashboard"); ap.add_argument("--tone"); ap.add_argument("--keywords")
ap.add_argument("--transcript"); ap.add_argument("--prior-transcript")
ap.add_argument("--public", action="store_true", help="公開版：不附完整逐字稿，只保留引用的原句（放上網路前用）");
ap.add_argument("--assets", default=ASSETS); ap.add_argument("--scripts", help="skill 的 scripts 資料夾，用來沿用語調詞表規則"); ap.add_argument("--outdir", default="out"); ap.add_argument("--suffix", default="")
a = ap.parse_args()
d = json.load(open(a.dashboard, encoding="utf-8"))
tone = json.load(open(a.tone, encoding="utf-8")) if a.tone else {}
kw = json.load(open(a.keywords, encoding="utf-8")) if a.keywords else {"keywords": []}
d["tone_scores"] = tone
d["keywords"] = kw.get("keywords", [])          # 次數一律用程式算的
d["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ── 逐字稿與原文定位：每句原文找出在哪一段、第幾個字，頁面上「看上下文」用 ──
def load_segs(path):
    t = json.load(open(path, encoding="utf-8"))
    return [{"sp": x.get("speaker", ""), "ti": x.get("title", ""), "sec": x.get("section", ""), "tx": x.get("text", "")}
            for x in t.get("segments", [])]
ctx = {"src": {}, "qmap": {}}
if a.transcript: ctx["src"]["cur"] = load_segs(a.transcript)
if a.prior_transcript: ctx["src"]["prior"] = load_segs(a.prior_transcript)
def locate(q, prefer):
    out = []
    for frag in [f.strip(" .…") for f in re.split(r"……|…", q) if f.strip(" .…")]:
        pat = r"\s+".join(re.escape(w) for w in frag.split())
        for src in prefer:
            hit = None
            for i, sg in enumerate(ctx["src"].get(src, [])):
                mm = re.search(pat, sg["tx"], re.I)
                if mm: hit = [src, i, mm.start(), mm.end()]; break
            if hit: out.append(hit); break
    return out
quotes = []
for it in d.get("outlook", {}).get("items", []):
    quotes.append((it.get("quote"), ["cur"])); quotes.append((it.get("prior_quote"), ["prior"]))
for k in d.get("key_data", []): quotes.append((k.get("quote"), ["cur"]))
for q in d.get("qa", []): quotes.append((q.get("quote"), ["cur"]))
for c in d.get("custom", []): quotes.append((c.get("quote"), ["cur"]))
miss = 0
for q, pref in quotes:
    if not q or not ctx["src"]: continue
    loc = locate(q, pref)
    if loc: ctx["qmap"][q] = loc
    else: miss += 1; print("找不到原文位置：", q[:60], file=sys.stderr)
d["ctx"] = ctx

# ── 語調詞明細：跟 tone_score.py 同一套規則，另外記下每個詞出現在哪裡 ──
def tone_detail(tpath):
    sys.path.insert(0, a.scripts or HERE)
    import tone_score as T
    lexp = os.path.join(a.assets, "lexicon.json")
    terms, negators, exclude, flips, hedges = T.load_lex(lexp)
    en_terms, en_neg, en_exc = T.load_en(lexp)
    tr = json.load(open(tpath, encoding="utf-8"))
    names = T.company_names(tr) if hasattr(T, "company_names") else []
    words = {}  # (sec, pol, word) -> {"n":, "flip":, "occ": []}
    def add(sec, pol, w, i, s0, s1, flip=False):
        k = (sec, pol, w); e = words.setdefault(k, {"sec": sec, "pol": pol, "w": w, "n": 0, "flip": 0, "occ": []})
        e["n"] += 1; e["flip"] += int(flip); e["occ"].append([i, s0, s1])
    chosen = {id(x) for x in T.select_segments(tr)[0]}
    for i, sg in enumerate(tr["segments"]):
        if id(sg) not in chosen or sg.get("section") not in ("presentation", "qa"): continue
        sec = sg["section"]
        text = T.mask_names(sg["text"], names) if names else sg["text"]
        used = [False] * len(text)                     # 中文詞表（與 score_text 相同）
        for w, cat in terms:
            if w in exclude: continue
            for m in re.finditer(re.escape(w), text):
                x, y = m.start(), m.end()
                if any(used[x:y]): continue
                for k in range(x, y): used[k] = True
                if cat == "uncertainty": add(sec, "unc", w, i, x, y); continue
                if cat == "positive" and any(h in text[y:y + 6] for h in hedges): add(sec, "unc", w + "（保留）", i, x, y); continue
                sign = 1 if cat == "positive" else -1; fl = False
                if any(n in text[max(0, x - 3):x] for n in negators): sign = -sign; fl = True
                if w in flips and any(sj in text[max(0, x - 8):x] for sj in flips[w]): sign = -sign; fl = not fl
                add(sec, "pos" if sign > 0 else "neg", w, i, x, y, fl)
        low = text.lower()                             # 英文詞表（與 score_en 相同）
        for ph, cat in en_terms.items():
            if " " in ph and cat == "uncertainty":
                for m in re.finditer(r"\b" + re.escape(ph) + r"\b", low): add(sec, "unc", ph, i, m.start(), m.end())
        toks = [(m.group(0).lower(), m.start(), m.end()) for m in T.WORD.finditer(text)]
        for j, (w, x, y) in enumerate(toks):
            if w in en_exc or w not in en_terms: continue
            cat = en_terms[w]
            if cat == "uncertainty": add(sec, "unc", w, i, x, y); continue
            sign = 1 if cat == "positive" else -1; fl = False
            prev = [p for p, _, _ in toks[max(0, j - 3):j]]
            if any(p in en_neg or p.endswith("n't") for p in prev): sign = -sign; fl = True
            add(sec, "pos" if sign > 0 else "neg", w, i, x, y, fl)
    out = sorted(words.values(), key=lambda e: -e["n"])
    lx = json.load(open(lexp, encoding="utf-8"))
    lang = tone.get("language", "en")
    sfx = "_en" if lang == "en" else ""
    lexicon = {"positive": lx.get("positive" + sfx, []), "negative": lx.get("negative" + sfx, []), "uncertainty": lx.get("uncertainty" + sfx, []),
               "negators": lx.get("negators" + sfx, []), "lang": lang}
    # 跟 tone.json 核對總數，對不上就提醒
    for sec in ("presentation", "qa"):
        tsec = tone.get(sec) or {}
        for pol, key in (("pos", "positive"), ("neg", "negative"), ("unc", "uncertainty")):
            got = sum(e["n"] for e in out if e["sec"] == sec and e["pol"] == pol)
            if tsec and got != tsec.get(key): print(f"語調詞明細與 tone.json 不一致：{sec} {key} {got} vs {tsec.get(key)}", file=sys.stderr)
    return out, lexicon
if a.transcript and tone:
    d["tone_words"], d["lexicon"] = tone_detail(a.transcript)
if a.public:
    # 公開版：拿掉完整逐字稿與語調詞的出現位置，次數保留；引用的原句本來就在各模組裡
    d["ctx"] = {"src": {}, "qmap": {}}
    for e in d.get("tone_words", []):
        e.pop("occ", None)
    d["public"] = True
m = d.get("meta", {})
name = f'{m.get("ticker") or m.get("company")}_{m.get("year")}Q{m.get("quarter")}'
tpl = open(os.path.join(a.assets, "template_motion.html"), encoding="utf-8").read()
data = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
html = (tpl.replace("__DATA__", data)
           .replace("__MARK__", b64(os.path.join(a.assets, "tej_mark.png")))
           .replace("__MARK_DARK__", b64_dark(os.path.join(a.assets, "tej_mark.png")))
           .replace("__LOCKUP_DARK__", b64_dark(os.path.join(a.assets, "tej_lockup.png")))
           .replace("__LOCKUP__", b64(os.path.join(a.assets, "tej_lockup.png")))
           .replace("__TITLE__", f'{m.get("company","")} {m.get("year")} Q{m.get("quarter")} 法說會儀表板'))
os.makedirs(a.outdir, exist_ok=True)
out = os.path.join(a.outdir, name + a.suffix + ".html")
open(out, "w", encoding="utf-8").write(html)
print(out); print(f"原文定位：{len(ctx['qmap'])} 句成功，{miss} 句找不到", file=sys.stderr)
