# 法說會大平台 Earnings Call Platform

彙整臺灣上市櫃公司法人說明會的日程與逐字稿，整理為可檢索、可比較的互動儀表板；每一項數據都附有逐字稿原句，可以回溯出處。

**線上網站：** https://yiyu0501.github.io/earnings-call-dashboard/

![首頁](docs/screenshots/hero.png)

本專案為台灣經濟新報（TEJ）實習期間之研究專案。儀表板由一套 Claude skill 產生，網站為純靜態頁面，部署於 GitHub Pages。

---

## 目錄

- [主要功能](#主要功能)
- [運作方式](#運作方式)
- [品質驗證](#品質驗證)
- [專案結構](#專案結構)
- [使用方式](#使用方式)
- [資料來源與聲明](#資料來源與聲明)
- [第三方程式與資料](#第三方程式與資料)
- [相關文件](#相關文件)

---

## 主要功能

| 功能 | 說明 |
|---|---|
| 首頁 | 公司與關鍵字搜尋（輸入時自動提示）、依產業瀏覽、最新法說會、法說會行事曆；主視覺為可互動的 3D 長條圖 |
| 法說會行事曆 | 收錄 TEJ 逐字稿資料庫 252 家公司、482 場法說會的日程；預設顯示 19 個產業的指標公司，其他公司可在搜尋後加入關注 |
| 單場儀表板 | 21 家公司、24 場。包含摘要與整體評價、財務指引與上下修、關鍵數據、問答整理、語調分析、關鍵詞，以及三種可直接複製的報告稿 |
| 跨季追蹤 | 公司頁對照同一項指引在各場的說法與語調走勢 |
| 焦點專區：台積電 | 以台積電 1987 年至今的官方財報與 2002 年以來 98 場法說會逐字稿為據，提供建廠足跡地圖、營收與毛利率走勢、法說會議會席次圖、年度語彙與詞頻對照 |

---

## 運作方式

```
法說會逐字稿（TEJ xlsx／PDF／Word）
   │  extract_text.py     讀檔、切段、辨識發言人、刪除重複收錄、找出上一場
   ▼
transcript.json
   │  Claude + skill      依固定規則撰寫摘要、指引、關鍵數據與問答，每項附原句
   │  tone_score.py       語調分數
   │  keyword_count.py    關鍵詞次數
   │  render_motion.py    產生單場儀表板（網站使用 --public 公開版）
   │  check_output.py     逐條核對原句、數字、字數與格式；未通過即退回重寫
   ▼
data/<公司>_<日期>.html
   │  integrate.py --site 彙整各場重點，產生 index.js
   ▼
index.html ＋ index.js ＋ universe.js  →  GitHub Actions 檢查後發布
```

設計原則是：凡能由程式完成的步驟（讀檔、計分、計數、版型、檢查）皆不交由 AI，AI 只負責閱讀與撰寫，使不同場次、不同操作者的產出維持一致品質。

---

## 品質驗證

| 測試 | 結果 |
|---|---|
| 全庫掃描：TEJ 逐字稿資料庫 484 場 | 0 場失敗 |
| 回歸測試：16 個案例（英文、中文、極短、極長、PDF、金控、航運等） | 16／16 通過 |
| 反向測試：刻意植入 11 種錯誤 | 11／11 攔截 |
| 更換模型：以 Sonnet 產生同一場 | 通過，並據此補充三條規則 |

---

## 專案結構

```
index.html               網站（由 skill/…/assets/integrated_template.html 複製）
index.js                 各場重點彙整（integrate.py 產生）
universe.js              行事曆資料（tools/build_universe.py 產生）
data/                    各場公開版儀表板
tsmc/index.html          台積電焦點專區
vendor/three-lite.js     首頁 3D 主視覺使用的 three.js 精簡版
integrate.py             掃描 data/、產生 index.js
skill/                   Claude skill 原始碼（SKILL.md、規則文件、程式、模板）
dist/                    打包好的 .skill，可直接安裝於 Claude
tools/                   行事曆產生器、台積電專區重建工具、全庫掃描、回歸測試、網站測試
cases/                   16 個測試案例（不含逐字稿原文）
docs/                    交接記憶檔、操作手冊、一頁簡介、交接說明、開發紀錄、截圖
.github/workflows/       推送後自動檢查並發布網站
```

---

## 使用方式

### 本機預覽

```bash
python -m http.server 8000
# 瀏覽 http://localhost:8000/
```

### 新增一場法說會

1. 依 `skill/earnings-call-dashboard/SKILL.md` 產生儀表板，並輸出公開版：
   ```bash
   python skill/earnings-call-dashboard/scripts/render_motion.py WORK/dashboard.json \
       --tone WORK/tone.json --keywords WORK/keywords.json --transcript WORK/transcript.json \
       --public --outdir WORK/out_public
   ```
2. 加入網站並檢查：
   ```bash
   python integrate.py --target . --site --add WORK/out_public
   python integrate.py --target . --site --check
   ```
3. 推送後約一分鐘，GitHub Pages 自動更新。

### 更新行事曆

```bash
python tools/build_universe.py <TEJ 逐字稿 xlsx> universe.js
```

產業分類與各產業指標公司定義於 `tools/build_universe.py` 的 `INDUSTRIES`。

### 調整版面

首頁區塊順序、焦點公司與專區頁面路徑等設定，集中在 `integrated_template.html` 開頭的 `SITE` 物件。修改模板後複製為 `index.html`。詳見 [交接說明](docs/交接說明.md)。

### 重建台積電專區

資料與步驟見 [`tools/tsmc_economy/README.md`](tools/tsmc_economy/README.md)。

---

## 資料來源與聲明

- 法說會逐字稿：TEJ 逐字稿資料庫。
- 台積電專區：台積電投資人關係網站之歷年法說會逐字稿、季度報告與年報。
- 網站使用公開版儀表板，僅保留各模組引用的原句，不附完整逐字稿；本儲存庫亦不包含逐字稿原文。
- 內容經 AI 整理及程式核對，仍可能存在判斷差異，請以原始逐字稿與公司公告為準。
- 本站內容僅供研究參考，不構成任何投資建議。

---

## 第三方程式與資料

| 項目 | 用途 | 授權 |
|---|---|---|
| [three.js](https://threejs.org/) | 首頁 3D 主視覺（`vendor/three-lite.js` 為依需求打包的精簡版） | MIT，見 `vendor/LICENSE-three.txt` |
| [world-atlas](https://github.com/topojson/world-atlas)（Natural Earth） | 台積電專區世界地圖 | ISC；地圖資料為公有領域 |
| [taiwan-atlas](https://github.com/dkaoster/taiwan-atlas) | 台積電專區臺灣縣市界線 | MIT；資料源自內政部村里界圖（政府資料開放平臺） |
| d3-geo、topojson-client、topojson-simplify | 建置時產生地圖路徑（不隨網站發布） | ISC |

---

## 相關文件

- [一頁簡介（PDF）](docs/一頁簡介.pdf)：專案目的、做法、成果與歷程
- [操作手冊](docs/操作手冊.md)：新增法說會、更新行事曆、修改版面、發布、維護
- [專案交接記憶檔](docs/00_專案交接記憶檔.md)：全貌、重要決定與理由、目前狀態與待辦
- [交接說明](docs/交接說明.md)：網站架構、如何增減公司與版面區塊、後續發展建議
- [Skill 導覽](docs/skill導覽.html)：skill 內每個檔案的完整內容
- [需求演進與決策紀錄](docs/02_需求演進與決策紀錄.md)、[開發紀錄](docs/03_開發紀錄_互動版_final_20261111.md)：各階段的需求、決策與理由
- [自我審查](docs/自我審查_final_20261111.md)：對照 TEJ 簡報逐項檢查
- [案例集](cases/README.md)：16 個測試案例與發現的問題
- [變更紀錄](CHANGELOG.md)

---

© 2026 法說會大平台　台灣經濟新報（TEJ）實習專案
