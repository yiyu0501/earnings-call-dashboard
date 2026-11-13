#!/usr/bin/env python3
"""
計算關鍵字在逐字稿中出現的次數。AI 只負責挑詞與分類，次數一律由這支程式算。

用法：
    python keyword_count.py <transcript.json> --dashboard dashboard.json --out keywords.json

讀取 dashboard.json 的 keywords（word + type），計算整份逐字稿（含講稿與 Q&A，
不含主持人）中出現的次數。英文不分大小寫，空白不影響比對（「AI伺服器」=「AI 伺服器」）。
次數為 0 的詞會列在 dropped，render.py 不會顯示。
"""
import argparse
import json
import re

EXCLUDE = {"問題", "好", "謝謝", "感謝", "公司", "我們", "今天", "各位"}


def norm(s):
    return re.sub(r"\s+", "", s).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--dashboard", required=True)
    ap.add_argument("--out", default="keywords.json")
    a = ap.parse_args()
    t = json.load(open(a.transcript, encoding="utf-8"))
    d = json.load(open(a.dashboard, encoding="utf-8"))
    # 一般情況排除主持人；整場標成同一人時用全文；完全沒有管理層時，納入法人關係人員的簡報（與 tone_score.py 一致）
    segs = t["segments"]
    if t.get("speaker_blob"):
        use = segs
    else:
        use = [s for s in segs if s["role"] != "host"]
        if not any(s["role"] == "management" for s in segs) and not any(
                re.search(r"法人關係|投資人關係|發言人|Investor Relations|\bIR\b", (s.get("title") or "") + " " + (s.get("speaker") or ""), re.I)
                for s in segs if s["role"] == "host"):
            use = segs                                  # 與 tone_score.py 相同：沒標出任何簡報人時用全文
        elif not any(s["role"] == "management" for s in segs):
            use += [s for s in segs if s["role"] == "host" and re.search(r"法人關係|投資人關係|發言人|Investor Relations|\bIR\b",
                                                                          (s.get("title") or "") + " " + (s.get("speaker") or ""), re.I)]
    raw = " ".join(s["text"] for s in use)
    body = norm(raw)
    low = raw.lower()

    def count(w):
        # 英文、數字組成的詞要整字比對，避免「AI」算到「maintain」裡的 ai
        if re.fullmatch(r"[A-Za-z0-9 .&\-/+]+", w):
            pat = r"(?<![a-z0-9])" + r"\s*".join(re.escape(x) for x in w.lower().split()) + r"(?![a-z0-9])"
            return len(re.findall(pat, low))
        return body.count(norm(w))
    kept, dropped, excluded = [], [], []
    for k in d.get("keywords", []):
        w = k["word"].strip()
        if norm(w) in EXCLUDE:
            excluded.append(w)
            continue
        c = count(w)
        item = {"word": w, "type": k.get("type", "positive"), "count": c}
        (kept if c > 0 else dropped).append(item)
    kept.sort(key=lambda x: (x["type"] != "positive", -x["count"]))
    out = {"keywords": kept, "dropped": dropped, "excluded": excluded}
    if len(kept) < 8:
        out["warning"] = f"有效關鍵字只有 {len(kept)} 個，規格要求 8–12 個，請補充。"
    elif len(kept) > 12:
        out["warning"] = f"有效關鍵字有 {len(kept)} 個，規格要求 8–12 個，請刪減。"
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
