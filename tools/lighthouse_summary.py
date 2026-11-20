"""把 Lighthouse CI 的結果整理成表格，寫進 GitHub Actions 的摘要頁。用法：python tools/lighthouse_summary.py"""
import json, os, pathlib
m = pathlib.Path('.lighthouseci/reports/manifest.json')
if not m.exists():
    raise SystemExit('找不到 Lighthouse 結果')
rows = ['## Lighthouse 評分', '', '| 頁面 | 效能 | 無障礙 | 最佳做法 | SEO |', '|---|---|---|---|---|']
for r in json.loads(m.read_text(encoding='utf-8')):
    s = r['summary']
    page = r['url'].split('/', 3)[-1] or 'index.html'
    rows.append(f"| {page} | " + ' | '.join(str(round(s.get(k, 0) * 100)) for k in ('performance', 'accessibility', 'best-practices', 'seo')) + ' |')
out = '\n'.join(rows)
print(out)
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
        f.write(out + '\n')
