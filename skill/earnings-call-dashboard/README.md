# 法說會 Dashboard Skill

TEJ 實習生專案。上傳法說會逐字稿，Claude 會產生一份 TEJ 風格的單檔 HTML 互動儀表板：可以看每句原文的上下文、和上一場比較，並直接複製 LINE 同步、組內摘要、研報重點三種報告稿。

版本：final_20261111（互動版成為預設輸出；舊版表格版保留）

## 資料夾

```
earnings-call-dashboard/
├── SKILL.md                  主流程（Claude 讀這份）
├── README.md                 給人看的說明（這份）
├── references/
│   ├── modules.md            九個模組的寫作規則與範例
│   ├── briefs.md             報告稿的句型、範例、用詞對照、禁用語
│   ├── schema.md             dashboard.json 欄位格式
│   ├── layout_motion.md      互動版版面規格
│   └── layout.md             表格版版面規格
├── scripts/
│   ├── extract_text.py       讀 docx / pdf / txt / md，切發言人與講稿／Q&A
│   ├── tone_score.py         詞表計算語調分數
│   ├── keyword_count.py      計算關鍵字次數
│   ├── render_motion.py      dashboard.json → 互動版 HTML（預設）
│   ├── render.py             dashboard.json → 表格版 HTML
│   ├── integrate.py          第二階段：多場放進整合儀表板
│   └── check_output.py       內容、延伸欄位、報告稿與版面檢查
└── assets/
    ├── template_motion.html  互動版版型
    ├── template.html         表格版版型
    ├── integrated_template.html  整合儀表板版型
    ├── lexicon.json          語調詞表（自行整理，可增修）
    ├── example_dashboard.json 完整範例
    ├── tej_mark.png          頁首 logo
    └── tej_lockup.png        頁尾 logo
```

## 分工原則

| 交給 AI | 交給程式 |
|---|---|
| 讀逐字稿、寫摘要與結論、挑關鍵數據與原文、整理 Q&A、給投資評價 | 讀檔、切段落、語調分數、關鍵字次數、套版、檢查 |

AI 只寫 `dashboard.json`，不直接寫 HTML，所以版面每次都一樣。

## 支援的逐字稿

- 格式：`.docx`、`.pdf`（需可選取文字，掃描檔不行）、`.txt`、`.md`，以及 **TEJ 逐字稿資料庫匯出的 `.xlsx`**。舊版 `.doc` 請先另存 `.docx`。
- TEJ xlsx：一個檔案可以有上百場法說會，用 `--list` 列出、`--call 代號:日期` 選場次，`--prior` 會一併取出同公司上一場，讓未來展望標示上修或下修。段落類型與發言人職稱直接採用資料庫欄位；重複收錄的段落會自動移除。
- 語言：中文或英文逐字稿皆可（英文已用 LSEG StreetEvents 格式的台積電 2026 Q3 法說會實測），儀表板內容固定用繁體中文、原文保留原語言。
- 發言人寫法：`**姓名 - 公司, 職稱**`、`姓名（職稱）：`、`職稱 姓名：`、`姓名 職稱：`、`某某證券 分析師：`、`Q：／A：`、`姓名：`、英文 `Name - Company - Title`（獨立一行）、`Operator`
- Q&A 起點：`## Q&A`、`問答`、`提問`、`#QA_START` 等標題，或第一位分析師開始發言的地方

## 模組與順序

預設順序：法說摘要 → **未來展望** → 結論 → 投資評價 → 關鍵數據 → 語調分析 → QA 關注議題 → 出席人員組成 → 關鍵字。

未來展望是 TEJ 最重視的模組：展望總結＋指引表（指引內容、方向、與上一場比較、原文）。投資評價採 TEJ 的五級（樂觀、審慎樂觀、中性、保守、悲觀）；QA 每題附中文回答摘要與回答態度（正面、保守、防禦性、避重就輕）。

## 輸出檔名

`股票代號_年份Q季別.html`，例如 `2330_2026Q3.html`。沒有代號時用公司名稱；年度法說會為 `2330_2026FY.html`。第二階段整合儀表板靠這個檔名辨識場次。

## 常見修改

- **調整語調判斷**：編輯 `assets/lexicon.json`，增刪正向、負向、不確定詞（中文用 `positive`／`negative`／`uncertainty`，英文用 `positive_en`／`negative_en`／`uncertainty_en`）。
- **調整模組規則**（字數、筆數）：同時改 `references/modules.md` 和 `scripts/check_output.py` 裡對應的數字。
- **調整樣式**：改 `assets/template.html`，並同步更新 `references/layout.md` 與 `check_output.py` 的色票清單。

## 手動測試

```bash
python scripts/extract_text.py 逐字稿.docx --outdir work
# TEJ xlsx：python scripts/extract_text.py 逐字稿.xlsx --call 2330:20260716 --prior --outdir work
python scripts/tone_score.py work/transcript.json --out work/tone.json
python scripts/keyword_count.py work/transcript.json --dashboard assets/example_dashboard.json --out work/keywords.json
python scripts/render.py assets/example_dashboard.json --tone work/tone.json --keywords work/keywords.json --outdir work/out
python scripts/check_output.py --dashboard assets/example_dashboard.json --transcript work/transcript.json --keywords work/keywords.json --html work/out/0000_2026Q3.html
```

範例資料是虛構公司「範例科技」，數字都不是真的。
