#!/usr/bin/env python3
"""反向測試：故意在台積電案例裡埋錯，確認 check_output.py 每一項都會擋下來。
用法：python tools/negative_tests.py <skill 資料夾> cases/01_台積電_2330_2026Q2（要先跑過 run_cases.py）"""
import json, subprocess, copy, glob, sys, tempfile, os
SK, C = sys.argv[1:3]
T = os.path.join(C, "transcript", "transcript.json"); P = os.path.join(C, "transcript", "prior", "transcript.json")
base = json.load(open(f"{C}/dashboard.json", encoding="utf-8"))
html = glob.glob(f"{C}/out/*.html")[0]
tmp = os.path.join(tempfile.gettempdir(), "bad_dashboard.json")
def test(name, mut):
    d = copy.deepcopy(base); mut(d); json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, f"{SK}/scripts/check_output.py", "--dashboard", tmp, "--transcript", T, "--keywords", f"{C}/keywords.json",
                        "--tone", f"{C}/tone.json", "--prior-transcript", P, "--html", html, "--no-browser"], capture_output=True, text=True)
    errs = json.loads(r.stdout)["errors"]
    print(("✅ 擋下" if errs else "❌ 沒擋"), name, "→", errs[0] if errs else "")
    return bool(errs)
cases = [
 ("報告稿出現編造的數字（營收 999 億）", lambda d: d["briefs"].__setitem__("line", d["briefs"]["line"].replace("402 億美元", "999 億美元"))),
 ("報告稿自己加問候語", lambda d: d["briefs"].__setitem__("line", "各位同事早安，\n" + d["briefs"]["line"])),
 ("報告稿出現 AI 腔（表現亮眼）", lambda d: d["briefs"].__setitem__("memo", d["briefs"]["memo"].replace("整體來看", "整體表現亮眼"))),
 ("組內摘要沒有條列", lambda d: d["briefs"].__setitem__("memo", __import__("re").sub(r"\n\d+\. ", "\n", d["briefs"]["memo"]))),
 ("上一場原文是編的", lambda d: d["outlook"]["items"][2].__setitem__("prior_quote", "we expect full year growth of about 25%")),
 ("前次數值和上一場原文對不上", lambda d: d["outlook"]["items"][3].__setitem__("prior_value", "約 US$52 billion")),
 ("提問單位題數合計錯誤", lambda d: d["analysts"][0].__setitem__("questions", 5)),
 ("提問者姓名不在逐字稿", lambda d: d["qa"][0].__setitem__("asker_name", "王小明")),
 ("變動只寫起點（由 A 增加）", lambda d: d["key_data"][6].__setitem__("change", "由 80 天增加")),
 ("關鍵數據數字不在原文", lambda d: d["key_data"][0].__setitem__("value", "US$41.2 billion")),
 ("摘要出現禁用語（值得期待）", lambda d: d["summary"].__setitem__("text", d["summary"]["text"][:-1] + "，值得期待。")),
]
ok = sum(test(n, m) for n, m in cases)
print(f"\n{ok}／{len(cases)} 項被擋下")
sys.exit(0 if ok == len(cases) else 1)
