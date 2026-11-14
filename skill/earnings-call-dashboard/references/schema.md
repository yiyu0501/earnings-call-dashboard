# dashboard.json 資料格式

AI 產生的內容全部寫進這一個檔案，再由 `scripts/render.py` 套進模板。
AI 不直接寫 HTML，這樣不管跑幾次，版面都會一模一樣。

## 目錄

1. 整體結構
2. meta
3. 各模組欄位
4. 自訂模組
5. 完整範例

---

## 1. 整體結構

```json
{
  "meta": { ... },
  "modules": ["summary", "outlook", "conclusion", "rating", "key_data", "tone", "qa", "attendees", "keywords"],
  "summary": { ... },
  "conclusion": { ... },
  "rating": { ... },
  "key_data": [ ... ],
  "tone": { ... },
  "outlook": [ ... ],
  "qa": [ ... ],
  "attendees": [ ... ],
  "keywords": [ ... ],
  "custom": [ ... ]
}
```

- `modules`：使用者勾選的模組，**陣列順序就是頁面上的顯示順序**。沒有列在這裡的模組不會出現，也不用填內容。
- 模組代號與中文名稱對照：

| 代號 | 中文名稱 |
|---|---|
| `summary` | 法說摘要 |
| `outlook` | 未來展望 |
| `conclusion` | 結論 |
| `rating` | 投資評價 |
| `key_data` | 關鍵數據 |
| `tone` | 語調分析 |
| `qa` | QA 關注議題 |
| `attendees` | 出席人員組成 |
| `keywords` | 關鍵字 |
| `custom:0`、`custom:1`… | 自訂模組（對應 `custom` 陣列的第幾個） |

---

## 2. meta

```json
"meta": {
  "company": "範例科技",
  "ticker": "0000",
  "industry": "電子零組件",
  "year": 2026,
  "quarter": 3,
  "date": "2026-10-30",
  "source_file": "範例科技_2026Q3法說會逐字稿.docx",
  "prior_call": "2026-07-28 法說會（2026 Q2）"
}
```

| 欄位 | 必填 | 說明 |
|---|---|---|
| `company` | 是 | 公司簡稱，逐字稿怎麼稱呼就怎麼寫 |
| `ticker` | 否 | 股票代號。不知道就填 `""`，檔名會改用公司名稱 |
| `industry` | 否 | 產業別。逐字稿沒提到就填 `""`，頁面顯示「未提及」 |
| `year` | 是 | 法說會所屬年度（西元） |
| `quarter` | 是 | 1–4。若是年度法說會或無法判斷季別，填 `0` |
| `date` | 否 | 法說會日期 `YYYY-MM-DD`，不知道填 `""` |
| `source_file` | 是 | 使用者上傳的逐字稿檔名 |
| `prior_call` | 否 | 有拿上一場比較時填，例如「2026-05-26 投資人會議」，會顯示在未來展望表格上方 |
| `time` | 否 | 法說會開始時間，例如 `14:00`。有填才會顯示在網站首頁的場次列表 |
| `venue` | 否 | 地點或形式，例如「線上法說會」「台北君悅酒店」。有填才顯示 |
| `slides` | 否 | 簡報檔網址（例如公開資訊觀測站的 PDF）。有填才在場次列表顯示「簡報」連結 |
| `video` | 否 | 影音網址。有填才在場次列表顯示「影音」連結 |

---

## 3. 各模組欄位

### summary 法說摘要

```json
"summary": { "text": "一段 80–120 字的摘要" }
```

### conclusion 結論

```json
"conclusion": { "text": "一段 100–150 字的結論" }
```

### rating 投資評價

```json
"rating": {
  "overall": "審慎樂觀",
  "growth": { "score": 80, "reason": "AI 產品出貨強、市占擴大" },
  "risk":   { "score": 45, "reason": "消費性需求、匯率、原物料" }
}
```

- `overall` 只能是：`樂觀`、`審慎樂觀`、`中性`、`保守`、`悲觀`（與 TEJ 範例的五級一致）
- `score` 為 0–100 的整數
- `reason` 20 字以內

### key_data 關鍵數據

```json
"key_data": [
  {
    "metric": "營收",
    "period": "2026 Q3",
    "value": "52.3 億元",
    "change": "季增 8.5%",
    "quote": "第三季營收達到 52.3 億元，較上季成長 8.5%，創下單季歷史新高。"
  }
]
```

- `quote` 必須是逐字稿原句，可以刪減但不能改字。刪減處用「……」連接。
- `value` 裡的數字必須出現在 `quote` 裡。
- 沒有變動資訊時 `change` 填 `"—"`。
- 一個數值一列；同一句有兩個數值（例如淨利和 EPS）可以拆成兩列，共用同一句原文。

### tone 語調分析

```json
"tone": { "note": "被問到毛利率、擴產、庫存時，回答多用「仍可能」「持續觀察」「不明朗」。" }
```

- 分數由 `scripts/tone_score.py` 計算，**AI 不填分數**，`render.py` 會直接讀 `tone.json`。
- AI 只寫 `note`：一句話說明講稿和 Q&A 的語氣差在哪，40 字以內。

### outlook 未來展望

```json
"outlook": {
  "text": "一段 80–200 字的展望總結",
  "items": [
    {
      "topic": "營收",
      "period": "2026 Q4",
      "value": "US$52.3–54.3 billion（中值季增 14%）",
      "direction": "成長",
      "vs_prior": "上修",
      "prior_value": "US$48–50 billion",
      "prior_quote": "（上一場逐字稿的原句）",
      "quote": "we expect our fourth quarter revenue to be between USD52.3 billion and USD54.3 billion, which represents a 14% sequential increase"
    }
  ]
}
```

- `items` 3–15 項（TEJ 範例多為 5–12 項），依「下一季財測 → 全年 → 資本支出與產能 → 技術與產品時程 → 股東回饋 → 長期目標 → 市場需求判斷」排列
- `topic` 12 字以內；`period` 例如 `2026 Q4`、`2026 全年`、`2027 上半年`、`2028`，沒提到填 `未提及`
- `value` 40 字以內，數字必須出現在 `quote` 裡；可以在括號補充中值或上修幅度，但數字同樣要在原文裡
- `direction` 只能是：`成長`、`改善`、`持平`、`下滑`、`承壓`、`未說明`
- `vs_prior` 只能是：`上修`、`下修`、`維持`、`新增`，或空字串 `""`（沒有上一場資料時一律留空）
- `quote` 必填，規則同關鍵數據
- `prior_value`、`prior_quote`：選填，上一場有明確數值時才填。`prior_quote` 必須在上一場逐字稿裡找得到（`check_output.py --prior-transcript` 會核對），`prior_value` 的數字必須在 `prior_quote` 裡；年份 2024 可以對到口語的 '24

### qa QA 關注議題

```json
"qa": [
  {
    "question": "第四季毛利率能否維持在三成四以上？",
    "answer": "產品組合與第三季相近，毛利率可望持平，但匯率與原物料仍是變數。",
    "stance": "保守",
    "asker": "投信",
    "asker_name": "王小華",
    "asker_org": "某某投信",
    "answerer": "總經理",
    "quote": "第四季產品組合預期與第三季相近，毛利率應可維持在相近水準。",
    "tag": "毛利率"
  }
]
```

- 依逐字稿順序排列，一個提問一筆
- `question` 40 字以內，是提問的摘要
- `answer` 10–60 字，用中文摘要管理層怎麼回答（英文逐字稿也用中文寫）
- `stance` 回答態度，只能是：`正面`、`保守`、`防禦性`、`避重就輕`（與 TEJ 範例一致，判斷方式見 modules.md）
- `asker` 寫類別：`投信`、`投顧`、`證券`、`外資`、`媒體`、`個人投資人`；看不出來寫 `法人`
- `asker_name`：提問者姓名，逐字稿有說才填，否則空字串；有填就必須出現在逐字稿裡
- `asker_org`：提問單位，逐字稿沒說填 `逐字稿未提及`
- `answerer` 寫職稱；逐字稿只有姓名時寫姓名
- `quote` 是回答的原文（可刪減），預設收合，點「看原文」展開
- `tag` 一個議題詞，6 字以內

### attendees 出席人員組成

```json
"attendees": [
  { "name": "王大明", "title": "總經理", "sections": "簡報、Q&A" }
]
```

- 管理層每人一筆，不含主持人與提問者
- 沒有姓名時 `name` 填 `"未具名"`

### analysts 提問者（隨出席人員組成顯示）

```json
"analysts": [
  { "name": "Sunny Lin", "org": "UBS", "type": "外資", "questions": 2 },
  { "name": "未具名", "org": "逐字稿未提及", "type": "未提及", "questions": 3 }
]
```

- `type` 只能是：`外資`、`證券`、`投顧`、`投信`、`媒體`、`個人投資人`、`保險`、`銀行`、`未提及`
- `questions` 加總必須等於 `qa` 題數

### briefs 報告稿（互動版）

```json
"briefs": {
  "line": "幫大家同步一下台積電 7/16 法說會的重點：\n1. ……\n2. ……\n3. ……",
  "memo": "【台積電 2026 Q2 法說會摘要】\n整體來看，……\n\n重點：\n1. ……",
  "report": "台積電 2026 Q2 法說會重點（2026/7/16）\n\n結論：……\n\n一、本季結果\n・……"
}
```

寫法見 `references/briefs.md`。不填時互動版會依資料自動組一份簡單的稿，但品質較差。

### keywords 關鍵字

```json
"keywords": [
  { "word": "AI 伺服器", "type": "positive" },
  { "word": "匯率", "type": "risk" }
]
```

- 8–12 個，`type` 只能是 `positive`（正面議題）或 `risk`（風險或不確定議題）
- **AI 不填次數**。`render.py` 會用 `scripts/keyword_count.py` 的結果帶入次數，次數為 0 的詞會被拿掉。

---

## 6. 深度追蹤欄位（選填）

給要做跨季比較的焦點公司用（例如網站上的台積電專區）。`meta.deep` 設為 `true` 時，檢查程式會要求這些欄位；沒有設就全部可以不填。寫法見 `modules.md` 第 12 節。

```json
"meta": { "...": "...", "deep": true },
"key_data": [
  { "metric": "營收", "period": "2026 Q1", "value": "US$35.9 billion", "change": "季增 6.4%",
    "std": "revenue", "num": 35.9, "unit": "US$ billion", "quote": "（原句）" }
],
"outlook": { "items": [
  { "topic": "營收", "period": "2026 Q2", "value": "US$39.0–40.2 billion", "direction": "成長", "vs_prior": "新增",
    "std": "revenue", "low": 39.0, "high": 40.2, "unit": "US$ billion", "quote": "（原句）" }
] },
"voices": [
  { "role": "CEO", "name": "魏哲家", "title": "董事長暨總裁", "focus": "展望",
    "points": [ { "text": "AI 需求比三個月前更強", "quote": "（原句）" } ] },
  { "role": "CFO", "name": "黃仁昭", "title": "財務長", "focus": "財務",
    "points": [ { "text": "第二季毛利率指引 58.5%–60.5%", "quote": "（原句）" } ] }
],
"qa": [ { "...": "...", "topic": "毛利率" } ]
```

| 欄位 | 說明 |
|---|---|
| `std` | 標準指標代碼，跨場、跨公司比較靠它對齊。只能是：`revenue` 營收、`revenue_growth` 營收成長率、`gross_margin` 毛利率、`op_margin` 營業利益率、`net_margin` 淨利率、`net_income` 稅後淨利、`eps` 每股盈餘、`capex` 資本支出、`depreciation` 折舊、`dividend` 股利、`utilization` 稼動率、`roe` ROE、`other` 其他 |
| `num`、`unit` | 關鍵數據的數值與單位（例如 `35.9`、`US$ billion`；`59.1`、`%`）。數字必須出現在原文裡 |
| `low`、`high`、`unit` | 指引是區間時的上下限（單一數值就上下限填一樣）。數字必須出現在原文裡 |
| `period` | 有 `std` 與數值時，期間要寫成 `2026 Q1`、`2026 全年`、`2026 上半年`、`2026 下半年` 這幾種格式，網站才能把「上一場的財測」和「這一場的實際數字」對起來 |
| `voices` | 管理層重點，依發言人分組：`role` 填 `CEO`、`CFO`、`董事長` 等；`focus` 填 `展望`（成長動能、技術、產能、長期）或 `財務`（本季結果、下季財測、資本支出、股利）；每人 2–5 點，`text` 8–40 字，各附原文 |
| `qa[].topic` | 標準議題，網站統計「法人最常追問」用。只能是：AI需求、需求展望、毛利率、價格、產能與擴產、資本支出、海外布局、先進製程、先進封裝、庫存、匯率、關稅與地緣、股東回饋、財務與費用、競爭、其他 |

## 4. 自訂模組

使用者要求清單以外的模組時使用，只有兩種型態：

```json
"custom": [
  {
    "title": "股利政策",
    "kind": "text",
    "text": "公司維持每年配發七成盈餘的政策……",
    "quote": "（選填）支持這段內容的原文"
  },
  {
    "title": "各產品線營收占比",
    "kind": "table",
    "columns": ["產品線", "占比", "原文"],
    "rows": [["AI 伺服器", "45%", "AI 伺服器相關產品占營收約四成五"]]
  }
]
```

- `title` 10 字以內
- `table` 的數字欄位同樣要能在逐字稿找到

---

## 5. 完整範例

見 `assets/example_dashboard.json`。
