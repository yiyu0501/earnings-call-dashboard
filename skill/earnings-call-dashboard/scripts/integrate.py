#!/usr/bin/env python3
"""
第二階段：整合儀表板。把多場單場儀表板放進同一個資料夾，左側選單依「公司 → 年份 → 場次」切換，
點公司可以看跨季追蹤（指引變化、語調趨勢）。

用法：
    # 建立（或更新）整合儀表板，並加入一場或多場
    python integrate.py --target ~/Desktop/整合儀表板 --add WORK [WORK2 ...]
    # 只重建索引（例如手動刪掉某一場之後）
    python integrate.py --target ~/Desktop/整合儀表板

--add 可以給工作資料夾（裡面有 out/*.html）、dashboard.json 的路徑，或直接給互動版 HTML。
只給 --target、不給 --add，就是建立空的整合資料夾（或重新掃描 data/）。

資料夾結構（對應 TEJ 簡報第 24 頁）：
    整合儀表板/
    ├── 整合儀表板.html          整合頁
    ├── 啟動整合儀表板.command    macOS 啟動程式：重新掃描 data/ 再打開整合頁
    ├── 啟動整合儀表板.bat        Windows 啟動程式：同上
    ├── index.js                 掃描結果（程式產生，不要手改）
    ├── integrate.py             本程式的副本，啟動程式會用到
    └── data/                    把儀表板 HTML 放進來；不想看就直接刪掉
        ├── 台積電_2026-07-16.html
        └── 儒鴻_2026-08-18.html

使用者可以自己把 HTML 拖進 data/，雙擊啟動程式就會出現在側邊欄。
公司、年份、季別、指引與語調都從 HTML 內嵌的資料讀出；表格版或其他 HTML 沒有內嵌資料時，從檔名「公司_日期」判斷。
"""
import argparse, datetime, glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "integrated_template.html")

MAC = """#!/bin/bash
cd "$(dirname "$0")"
python3 integrate.py --target . >/dev/null 2>&1 || python integrate.py --target . >/dev/null 2>&1
open "整合儀表板.html"
"""
WIN = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
python integrate.py --target . >nul 2>&1 || py integrate.py --target . >nul 2>&1
start "" "整合儀表板.html"
"""


def session_key(meta):
    """場次名稱：優先用日期；沒有日期（例如 PDF）用年份與季別。"""
    if meta.get("date"):
        return meta["date"]
    return f"{meta.get('year', '')}Q{meta.get('quarter', '')}"


def safe(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "", name or "")


def embedded(path):
    """讀出互動版 HTML 內嵌的資料；不是互動版就回傳 None。"""
    try:
        h = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', h, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1).replace("<\\/", "</"))
    except ValueError:
        return None


def find_html(src):
    """--add 可以給工作資料夾、dashboard.json 所在資料夾，或直接給 HTML。回傳互動版 HTML 路徑。"""
    if src.lower().endswith(".html"):
        return src
    work = os.path.dirname(os.path.abspath(src)) if src.endswith(".json") else os.path.abspath(src)
    for hp in glob.glob(os.path.join(work, "out", "*.html")) + glob.glob(os.path.join(work, "*.html")):
        if embedded(hp):
            return hp
    raise FileNotFoundError(f"找不到互動版 HTML：{src}；請先執行 render_motion.py")


def add_session(target, src):
    hp = find_html(src)
    d = embedded(hp)
    if d:
        m = d.get("meta", {})
        name = f"{safe(m.get('company')) or '未知'}_{session_key(m)}.html"
    else:
        name = os.path.basename(hp)
    shutil.copy(hp, os.path.join(target, "data", name))
    return name


def from_filename(fn):
    """沒有內嵌資料的 HTML：從檔名「公司_日期」判斷。"""
    stem = os.path.splitext(fn)[0]
    company, _, rest = stem.partition("_")
    m = re.search(r"(20\d\d)[-_/.]?(\d{1,2})?[-_/.]?(\d{1,2})?", rest)
    year = int(m.group(1)) if m else None
    date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m and m.group(2) and m.group(3) else ""
    q = re.search(r"Q([1-4])", rest, re.I)
    return {"company": company or stem, "ticker": "", "date": date, "year": year, "quarter": int(q.group(1)) if q else None}


def summarize(path):
    fn = os.path.basename(path)
    d = embedded(path)
    base = {"key": os.path.splitext(fn)[0], "path": "data/" + fn, "file": fn, "tone": {}, "revisions": {}, "summary": "",
            "flags": [], "outlook": [], "qa": 0, "rating": "", "growth": None, "risk": None, "industry": "", "prior_call": "",
            "interactive": bool(d)}
    if not d:
        base.update(from_filename(fn))
        base["flags"] = ["非互動版，只列出檔案"]
        return base
    m, R = d.get("meta", {}), d.get("rating") or {}
    t = d.get("tone_scores") or {}
    tone = {k: {"score": t[k]["score"], "label": t[k]["label"]} for k in ("presentation", "qa") if t.get(k)}
    if t.get("basis") and t["basis"] != "管理層":
        tone["basis"] = t["basis"]
    items = (d.get("outlook") or {}).get("items", []) if "outlook" in d.get("modules", []) else []
    rev = {}
    for it in items:
        if it.get("vs_prior"):
            rev[it["vs_prior"]] = rev.get(it["vs_prior"], 0) + 1
    summary = (d.get("summary") or {}).get("text", "")
    flags = []
    if "重複收錄" in summary:
        flags.append("疑似重複收錄")
    if "主持人" in summary and "標成" in summary:
        flags.append("發言人標記異常")
    base.update({"company": m.get("company", ""), "ticker": m.get("ticker", ""), "industry": m.get("industry", ""),
                 "date": m.get("date", ""), "year": m.get("year"), "quarter": m.get("quarter"), "prior_call": m.get("prior_call", ""),
                 "rating": R.get("overall", ""), "growth": (R.get("growth") or {}).get("score"), "risk": (R.get("risk") or {}).get("score"),
                 "tone": tone, "revisions": rev, "summary": summary, "flags": flags, "qa": len(d.get("qa", [])),
                 "outlook": [{k: it.get(k, "") for k in ("topic", "period", "value", "direction", "vs_prior", "prior_value")} for it in items],
                 "key_data": [{k: x.get(k, "") for k in ("metric", "period", "value", "change")} for x in d.get("key_data", [])],
                 "qas": [{"q": x.get("question", ""), "a": x.get("answer", ""), "tag": x.get("tag", ""), "stance": x.get("stance", ""),
                          "org": x.get("asker_org", "")} for x in d.get("qa", [])],
                 "keywords": [k.get("word", "") for k in d.get("keywords", [])],
                 "conclusion": (d.get("conclusion") or {}).get("text", ""),
                 "public": bool(d.get("public")) or not (d.get("ctx") or {}).get("src")})
    return base


def check(target, allow_full=False):
    """上線前檢查：任何一項錯誤都讓 GitHub Actions 停止發布。"""
    errors, warns, seen = [], [], {}
    for p in sorted(glob.glob(os.path.join(target, "data", "*.html"))):
        fn = os.path.basename(p)
        size = os.path.getsize(p) / 1024 / 1024
        if size > 20:
            warns.append(f"{fn} 有 {size:.1f} MB，偏大")
        d = embedded(p)
        if d is None:
            warns.append(f"{fn} 不是互動版，網站只能列出檔名")
            continue
        if (d.get("ctx") or {}).get("src") and not allow_full:
            errors.append(f"{fn} 夾帶完整逐字稿；請改用 render_motion.py --public 產生的公開版")
        m = d.get("meta", {})
        key = (m.get("ticker") or m.get("company"), session_key(m))
        if key in seen:
            warns.append(f"{fn} 和 {seen[key]} 是同一場（{key[0]} {key[1]}），網站會出現兩次")
        seen[key] = fn
    return errors, warns


def rebuild(target):
    comps = {}
    for p in sorted(glob.glob(os.path.join(target, "data", "*.html"))):
        s = summarize(p)
        code = s["ticker"] or s["company"]
        c = comps.setdefault(code, {"ticker": code, "name": s["company"], "industry": s["industry"], "sessions": []})
        if s["industry"] and not c["industry"]:
            c["industry"] = s["industry"]
        c["sessions"].append(s)
    for c in comps.values():
        c["sessions"].sort(key=lambda s: (s["year"] or 0, s["quarter"] or 0, s["date"] or ""))
    idx = {"generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "site": os.path.exists(os.path.join(target, ".nojekyll")),
           "companies": sorted(comps.values(), key=lambda c: c["ticker"])}
    js = "window.EC_INDEX = " + json.dumps(idx, ensure_ascii=False) + ";\n"
    open(os.path.join(target, "index.js"), "w", encoding="utf-8").write(js)
    return idx


def ensure_shell(target, site=False):
    os.makedirs(os.path.join(target, "data"), exist_ok=True)
    shutil.copy(os.path.abspath(__file__), os.path.join(target, "integrate.py"))
    if site:
        # GitHub Pages：首頁要叫 index.html；.nojekyll 讓 GitHub 不要用 Jekyll 處理檔案
        shutil.copy(TEMPLATE, os.path.join(target, "index.html"))
        open(os.path.join(target, ".nojekyll"), "w").close()
        open(os.path.join(target, "404.html"), "w", encoding="utf-8").write(
            '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>找不到這一頁｜法說會儀表板</title><style>body{font-family:system-ui,"PingFang TC","Microsoft JhengHei",sans-serif;margin:0;'
            'min-height:100vh;display:grid;place-items:center;background:#0b2140;color:#e9f1fa;text-align:center}a{color:#7fb6e6;font-weight:700}</style>'
            '</head><body><div><h1>找不到這一頁</h1><p>這個網址可能已經更改。</p><p><a href="./">回到首頁</a></p></div></body></html>')
        for name in ("tej_mark.png", "tej_lockup.png"):
            src = os.path.join(HERE, "..", "assets", name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(target, name))
        return
    shutil.copy(TEMPLATE, os.path.join(target, "整合儀表板.html"))
    mac = os.path.join(target, "啟動整合儀表板.command")
    open(mac, "w", encoding="utf-8", newline="\n").write(MAC); os.chmod(mac, 0o755)
    open(os.path.join(target, "啟動整合儀表板.bat"), "w", encoding="utf-8", newline="\r\n").write(WIN)
    for name in ("tej_mark.png", "tej_lockup.png"):
        src = os.path.join(HERE, "..", "assets", name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(target, name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="整合儀表板資料夾，例如 ~/Desktop/整合儀表板")
    ap.add_argument("--add", nargs="*", default=[], help="要加入的工作資料夾或 dashboard.json")
    ap.add_argument("--site", action="store_true", help="網站版：首頁存成 index.html、不放啟動程式，給 GitHub Pages 用")
    ap.add_argument("--check", action="store_true", help="上線前檢查：有夾帶完整逐字稿的 HTML 就回傳錯誤（GitHub Actions 用）")
    ap.add_argument("--allow-full", action="store_true", help="已取得同意，允許公開完整逐字稿")
    a = ap.parse_args()
    target = os.path.abspath(os.path.expanduser(a.target))
    # 從資料夾內的副本執行（啟動程式）時，沒有模板可複製，只重建索引
    if os.path.exists(TEMPLATE):
        ensure_shell(target, site=a.site)
    added = []
    for src in a.add:
        try:
            added.append(add_session(target, src))
        except Exception as ex:  # noqa
            print(f"略過 {src}：{ex}", file=sys.stderr)
    if a.check:
        errs, warns = check(target, a.allow_full)
        for w in warns:
            print("提醒：" + w, file=sys.stderr)
        if errs:
            for e in errs:
                print("錯誤：" + e, file=sys.stderr)
            print(f"上線前檢查沒有通過（{len(errs)} 項錯誤），網站不會更新。", file=sys.stderr)
            sys.exit(1)
    idx = rebuild(target)
    n = sum(len(c["sessions"]) for c in idx["companies"])
    print(json.dumps({"target": target, "added": added, "companies": len(idx["companies"]), "sessions": n,
                      "open": os.path.join(target, "index.html" if a.site else "整合儀表板.html")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
