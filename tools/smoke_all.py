#!/usr/bin/env python3
"""全庫掃描：xlsx 只讀一次，每一場都跑過讀檔切段（extract_text）與語調計分（tone_score），
記錄當掉、警告與統計。用法：python tools/smoke_all.py <skill 資料夾> <TEJ xlsx> <輸出 json>"""
import json, os, sys, collections, time, traceback
SK, XLSX, OUT = sys.argv[1:4]
sys.path.insert(0, os.path.join(SK, "scripts"))
import extract_text as E, tone_score as T
rows = E.load_xlsx(XLSX)
groups = collections.defaultdict(list)
for r in rows: groups[E.call_key(r)].append(r)
calls = E.list_calls(rows)
lexp = os.path.join(SK, "assets", "lexicon.json")
terms, negators, exclude, flips, hedges = T.load_lex(lexp); en = T.load_en(lexp)
res = []
for c in calls:
    k = (c["code"], c["date"], c["no"]); row = {"id": c["id"], "name": c["company"], "english": c["english"]}
    t0 = time.time()
    try:
        segs, dropped = E.xlsx_segments(groups[k])
        meta = {"company": c["company"]}
        data = E.build_data("x", "xlsx", segs, "xlsx", [], meta=meta)
        sg = data["segments"]; roles = collections.Counter(s["role"] for s in sg)
        row.update(chars=data["char_count"], segs=len(sg), has_qa=any(s["section"] == "qa" for s in sg), dropped=len(dropped),
                   mgmt=roles.get("management", 0), analyst=roles.get("analyst", 0), host=roles.get("host", 0), other=roles.get("other", 0))
        names = T.company_names(data)
        mg = [s for s in sg if s["role"] == "management"]
        use_en = c["english"] == "Y"
        for sec in ("presentation", "qa"):
            part = [s for s in mg if s["section"] == sec]
            if part:
                r2 = T.summarize(part, terms, negators, exclude, flips, hedges, en if use_en else None, names)
                row[sec] = (r2["score"], r2["label"], r2["positive"] + r2["negative"], r2["top_positive"][:3], r2["top_negative"][:3])
    except Exception:
        row["error"] = traceback.format_exc()[-400:]
    row["secs"] = round(time.time() - t0, 2); res.append(row)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ok = [x for x in res if "error" not in x]
print(f"共 {len(res)} 場，當掉 {len(res)-len(ok)} 場")
print(f"沒有 Q&A 段 {sum(not x['has_qa'] for x in ok)}、英文 {sum(x['english']=='Y' for x in ok)}、沒有管理層發言 {sum(x['mgmt']==0 for x in ok)}、"
      f"講稿詞數太少 {sum(1 for x in ok if x.get('presentation',(0,'',0))[1]=='詞數太少')}、有重複段落被移除 {sum(1 for x in ok if x['dropped'])}")
