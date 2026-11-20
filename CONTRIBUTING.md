# 參與開發

感謝你願意改善法說會大平台。這份文件說明開發流程與規範；日常操作的完整步驟見 [操作手冊](docs/操作手冊.md)，架構說明見 [交接說明](docs/交接說明.md)。

## 回報與建議

| 想做的事 | 方式 |
|---|---|
| 回報數字或原句有誤 | 開 Issue，選「資料錯誤回報」 |
| 回報網站問題 | 開 Issue，選「網站問題」 |
| 提出功能建議 | 開 Issue，選「功能建議」 |
| 回報資安問題 | 依 [安全政策](SECURITY.md) 私下回報 |

## 開發流程

1. 從 `main` 開分支，命名依用途：
   - `data/2330-2026q4`：新增或更新儀表板
   - `feat/watchlist`：網站功能
   - `fix/mobile-table`：修正問題
   - `skill/qa-rules`：skill 的規則、程式或模板
   - `docs/manual`：文件
2. 修改後在本機檢查：
   ```bash
   cp skill/earnings-call-dashboard/assets/integrated_template.html index.html   # 改到版面時
   python integrate.py --target . --site --check
   python tools/build_seo.py
   node tools/site_test.js
   ```
3. 開 Pull Request，依範本勾選檢查項目。CI 會自動執行同樣的檢查。
4. 合併到 `main` 後，GitHub Actions 會自動發布，約 1–2 分鐘上線。

## 規範

- **版面只改模板**：`skill/earnings-call-dashboard/assets/integrated_template.html`，再複製成 `index.html`，兩者必須一致。
- **網站只放公開版儀表板**（`render_motion.py --public`），不得含完整逐字稿。
- **不猜數字**：沒有資料的欄位留空或註明待接資料。
- **文字**：說明資料用書面語；操作提示用白話；使用台灣繁體中文。台股慣例紅色為上修、綠色為下修。
- **Commit 訊息**：一句話說明改了什麼，例如「公司頁新增同產業公司卡片」。依賴更新使用 `ci:` 前綴。
- **紀錄**：每次合併更新 `CHANGELOG.md`；較大的改動在[開發紀錄](docs/03_開發紀錄_互動版_final_20261111.md)寫下要求、決定與驗證。

## 發布版本

重要里程碑以語意化版本打標籤（`v1.0.0`、`v1.1.0`），並在 GitHub Releases 附上 `CHANGELOG.md` 對應段落、`dist/earnings-call-dashboard.skill` 與 `docs/一頁簡介.pdf`。
