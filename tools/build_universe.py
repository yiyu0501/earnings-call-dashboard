#!/usr/bin/env python3
"""產生 universe.js：網站行事曆用的「全部法說會日程」。
只取 TEJ 逐字稿資料庫每場的公司、日期與擇要說明，不含任何逐字稿內容。
用法：python tools/build_universe.py <TEJ 逐字稿 xlsx> [輸出路徑，預設 universe.js]

INDUSTRIES 是各產業的指標公司：行事曆預設只顯示這些公司與已做成儀表板的場次，
其他公司要使用者按「關注」才會出現。要調整名單就改這裡，再重跑一次。"""
import datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skill", "earnings-call-dashboard", "scripts"))
import extract_text as E  # noqa: E402

INDUSTRIES = {
    "半導體": ["2330", "2454", "3711", "2303"],
    "電腦及週邊": ["2382", "2357", "3231", "2395"],
    "其他電子": ["2317"],
    "光電": ["3008", "2409", "3481"],
    "通信網路": ["2412", "3045", "4904"],
    "電子零組件": ["2308", "2327", "3037"],
    "電子通路": ["3036", "3702"],
    "金融保險": ["2881", "2882", "2891", "2886"],
    "航運": ["2603", "2609", "2610", "2618"],
    "塑膠": ["1301", "1303", "1326"],
    "油電燃氣": ["6505"],
    "鋼鐵": ["2002", "2015"],
    "水泥": ["1101", "1102"],
    "食品": ["1216", "1215"],
    "紡織": ["1476", "1477"],
    "汽車": ["2207", "2201"],
    "貿易百貨": ["2912", "5903", "2903"],
    "電機機械": ["2049", "1504"],
    "生技醫療": ["6472", "1795"],
}


def main():
    xlsx = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "universe.js")
    calls = E.list_calls(E.load_xlsx(xlsx))
    cos = {}
    for c in calls:
        co = cos.setdefault(c["code"], {"n": c["company"], "c": []})
        if any(x["d"] == c["date"] for x in co["c"]):
            continue  # 同一天多場只留一筆
        co["c"].append({"d": c["date"], "t": (c.get("description") or "").strip(), "q": 1 if c.get("has_qa") else 0,
                        "e": 1 if c.get("english") == "Y" else 0})
    for co in cos.values():
        co["c"].sort(key=lambda x: x["d"])
    missing = [code for codes in INDUSTRIES.values() for code in codes if code not in cos]
    if missing:
        print("提醒：這些指標公司在資料庫裡沒有場次：" + "、".join(missing), file=sys.stderr)
    u = {"generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "source": os.path.basename(xlsx),
         "industries": {k: [c for c in v if c in cos] for k, v in INDUSTRIES.items()}, "companies": cos}
    open(out, "w", encoding="utf-8").write("window.EC_UNIVERSE = " + json.dumps(u, ensure_ascii=False, separators=(",", ":")) + ";\n")
    n = sum(len(co["c"]) for co in cos.values())
    print(json.dumps({"out": out, "companies": len(cos), "calls": n}, ensure_ascii=False))


if __name__ == "__main__":
    main()
