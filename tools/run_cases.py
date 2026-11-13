#!/usr/bin/env python3
"""回歸測試（用法：python tools/run_cases.py <skill 資料夾> cases）：用 skill 的 scripts 把每個案例從頭跑一遍（語調 → 關鍵字 → 互動版 → 檢查 → 表格版 → 檢查），
並用瀏覽器在桌面與手機寬度打開互動版，記錄錯誤。結果寫進 cases/<案例>/check.json 與 cases/summary.json。"""
import json, os, subprocess, sys, glob, shutil
SKILL = sys.argv[1]; CASES = sys.argv[2]
S = os.path.join(SKILL, "scripts")
def run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr
summary = {}
for case in sorted(os.listdir(CASES)):
    C = os.path.join(CASES, case)
    if not os.path.isdir(C) or not os.path.exists(os.path.join(C, "case.json")): continue
    cfg = json.load(open(os.path.join(C, "case.json"), encoding="utf-8"))
    T = os.path.join(C, "transcript", "transcript.json")
    P = os.path.join(C, "transcript", "prior", "transcript.json") if cfg.get("use_prior") else None
    if not os.path.exists(T):
        print("⚠️ ", case, "沒有逐字稿，先執行：", cfg.get("extract")); continue
    out = os.path.join(C, "out"); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    res = {}
    run(os.path.join(S, "tone_score.py"), T, "--out", os.path.join(C, "tone.json"))
    run(os.path.join(S, "keyword_count.py"), T, "--dashboard", os.path.join(C, "dashboard.json"), "--out", os.path.join(C, "keywords.json"))
    margs = [os.path.join(S, "render_motion.py"), os.path.join(C, "dashboard.json"), "--tone", os.path.join(C, "tone.json"),
             "--keywords", os.path.join(C, "keywords.json"), "--transcript", T, "--outdir", out]
    if P: margs += ["--prior-transcript", P]
    rc, so, se = run(*margs); motion_html = so.strip().splitlines()[-1] if so.strip() else ""
    res["render_motion"] = {"ok": rc == 0, "log": se.strip()}
    cargs = ["--dashboard", os.path.join(C, "dashboard.json"), "--transcript", T, "--keywords", os.path.join(C, "keywords.json"),
             "--tone", os.path.join(C, "tone.json")] + (["--prior-transcript", P] if P else [])
    rc, so, se = run(os.path.join(S, "check_output.py"), *cargs, "--html", motion_html)
    res["check_motion"] = json.loads(so) if so.strip().startswith("{") else {"ok": False, "errors": [se[-300:]]}
    rc, so, se = run(os.path.join(S, "render.py"), os.path.join(C, "dashboard.json"), "--tone", os.path.join(C, "tone.json"),
                     "--keywords", os.path.join(C, "keywords.json"), "--outdir", os.path.join(out, "table"))
    th = glob.glob(os.path.join(out, "table", "*.html"))
    rc, so, se = run(os.path.join(S, "check_output.py"), *cargs, "--html", th[0]) if th else (1, "", "表格版沒有產生")
    res["check_table"] = json.loads(so) if so.strip().startswith("{") else {"ok": False, "errors": [se[-300:]]}
    # 瀏覽器實測：桌面與手機，頁面錯誤、橫向捲軸、報告稿與逐字稿能打開
    try:
        from playwright.sync_api import sync_playwright
        b_res = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for tag, vw in (("desktop", (1440, 900)), ("mobile", (390, 844))):
                pg = b.new_page(viewport={"width": vw[0], "height": vw[1]}); errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto("file://" + os.path.abspath(motion_html)); pg.wait_for_timeout(900)
                H = pg.evaluate("document.documentElement.scrollHeight")
                for y in range(0, H, int(vw[1] * .9)): pg.evaluate(f"scrollTo(0,{y})"); pg.wait_for_timeout(60)
                hs = pg.evaluate("document.documentElement.scrollWidth>innerWidth+1")
                pg.evaluate("scrollTo(0,0)"); pg.click("#openDraft"); pg.wait_for_timeout(300)
                drafts = {}
                for f in ("line", "memo", "report"):
                    pg.click(f'.fmt[data-f="{f}"]'); drafts[f] = pg.input_value("#draft")[:40]
                pg.click('.dw-tab[data-tab="method"]'); pg.wait_for_timeout(150)
                pg.keyboard.press("Escape")
                b_res[tag] = {"page_errors": errs, "horizontal_scroll": hs, "draft_heads": drafts}
                pg.screenshot(path=os.path.join(out, f"screenshot_{tag}.png"))
            b.close()
        res["browser"] = b_res
    except Exception as ex:
        res["browser"] = {"error": str(ex)}
    res["ok"] = res["render_motion"]["ok"] and res["check_motion"].get("ok") and res["check_table"].get("ok") and \
        all(not v.get("page_errors") and not v.get("horizontal_scroll") for v in res.get("browser", {}).values() if isinstance(v, dict))
    json.dump(res, open(os.path.join(C, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    summary[case] = {"ok": bool(res["ok"]), "motion_errors": res["check_motion"].get("errors", []), "motion_warnings": res["check_motion"].get("warnings", []),
                     "table_errors": res["check_table"].get("errors", []), "browser": {k: (v.get("page_errors"), v.get("horizontal_scroll")) for k, v in res.get("browser", {}).items() if isinstance(v, dict)}}
json.dump(summary, open(os.path.join(CASES, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in summary.items():
    print(("✅" if v["ok"] else "❌"), k)
    for e in v["motion_errors"] + v["table_errors"]: print("    錯誤：", e)
    for w in v["motion_warnings"]: print("    提醒：", w)
