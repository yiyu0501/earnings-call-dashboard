---
name: earnings-call-dashboard
description: 把法說會（法人說明會、earnings call）逐字稿做成 TEJ 風格的單檔 HTML 互動儀表板，含法說摘要、未來展望與上一場比較、關鍵數據附原文、講稿與 Q&A 語調分析、QA 關注議題、可直接複製的報告稿等模組，使用者可以勾選模組與排序。只要使用者上傳或提到法說會逐字稿（Word、PDF、txt、md，或 TEJ 逐字稿資料庫匯出的 Excel 皆可），並想要整理、分析、摘要、視覺化、做成儀表板或報表，就使用這個 skill，即使沒有說「儀表板」三個字也一樣。不適用於撰寫法說會邀請函、新聞稿、簡報投影片，或與逐字稿無關的財報分析。
---

# 法說會儀表板

把一份法說會逐字稿變成一頁可以搜尋、篩選、回頭查證的 HTML 儀表板。預設產生**互動版**（可看上下文、可複製報告稿）；使用者要簡潔的表格版時才用表格版。

這個 skill 的設計重點是**穩定**：AI 只負責讀逐字稿、判斷內容，寫成一份 `dashboard.json`；分數、次數、版面一律交給 scripts 和模板。這樣同一份逐字稿跑幾次，長相都一樣，數字也不會被 AI 改掉。

## 檔案

| 路徑 | 什麼時候讀 |
|---|---|
| `references/modules.md` | 寫內容前**一定要讀**：九個模組各寫什麼、多長、怎麼找 |
| `references/briefs.md` | 寫報告稿前**一定要讀**：三種稿的句型、範例、禁用語 |
| `references/schema.md` | 寫 `dashboard.json` 前讀：欄位格式 |
| `references/layout_motion.md` | 使用者問到互動版的樣式、或要改互動版模板時才讀 |
| `references/layout.md` | 表格版的版面規格，要改表格版樣式時才讀 |
| `scripts/extract_text.py` | 讀取 docx／pdf／txt／md，切出發言人與講稿／Q&A |
| `scripts/tone_score.py` | 計算語調分數 |
| `scripts/keyword_count.py` | 計算關鍵字次數 |
| `scripts/render_motion.py` | 產生互動版（預設） |
| `scripts/render.py` | 產生表格版 |
| `scripts/integrate.py` | 第二階段：把多場放進整合儀表板 |
| `scripts/check_output.py` | 檢查內容與版面是否符合規格 |
| `assets/template_motion.html` | 互動版版型，不要修改 |
| `assets/template.html` | 表格版版型，不要修改 |
| `assets/integrated_template.html` | 整合儀表板版型，不要修改 |
| `assets/example_dashboard.json` | 完整範例，格式有疑問時參考 |

以下用 `SKILL_DIR` 代表這個 skill 的資料夾路徑，`WORK` 代表工作資料夾（例如 `./work`）。

## 流程

### 1. 讀取逐字稿

```bash
python SKILL_DIR/scripts/extract_text.py <逐字稿檔案> --outdir WORK
```

**TEJ 逐字稿資料庫（.xlsx）**：一個檔案裡通常有上百場法說會，要先選場次。

```bash
python SKILL_DIR/scripts/extract_text.py <檔案.xlsx> --list --company 2330      # 列出某家公司的場次
python SKILL_DIR/scripts/extract_text.py <檔案.xlsx> --call 2330:20260716 --prior --outdir WORK
```

- 使用者只說公司名稱時，先用 `--list --company` 列出場次，預設選最新一場，並在第 2 步跟使用者確認。
- 一律加 `--prior`：程式會把同公司的上一場存到 `WORK/prior/`，未來展望要用它來判斷上修或下修。讀上一場時只需要找出它的指引，不用整份細讀。上一場若是投資人會議、論壇而不是正式法說會，在 `meta.prior_call` 寫清楚。
- xlsx 已經標好段落類型（報告／提問／回答）與發言人職稱，不需要猜。`meta_hint` 裡有公司、代號、日期，直接拿來填 `meta`。
- 使用者上傳的是 docx、pdf、txt、md 時沒有上一場可比，`vs_prior` 全部留空；若使用者另外上傳了上一場的逐字稿，同樣用 extract_text.py 取出到 `WORK/prior/`。

- 印出的摘要會顯示格式、字數、是否有 Q&A、辨識到的發言人和 `warnings`。
- 接著**完整讀過** `WORK/transcript_labeled.txt`。每段開頭標了 `[編號][講稿/Q&A][角色]`，寫內容時靠這份檔案。
- 有 `warnings` 時要處理：
  - 沒找到 Q&A：先看全文確認。TEJ 資料庫有時把書面問答標成「報告」，講稿裡有「針對 Q&A 有幾題」這類段落時，照樣整理成 `qa`；真的沒有就照常做，Q&A 相關模組會顯示「本場無 Q&A」
  - 發言人角色辨識失敗太多：告訴使用者語調分數可能不準，並說明原因
  - 讀不到文字（掃描檔）：請使用者改傳可選取文字的 PDF 或 Word 檔，停止流程
  - 「整場標成同一位發言人」：TEJ 標記錯誤，要自己從文字判斷誰在說話、Q&A 從哪裡開始（例如主持人說「The first one to ask questions...」）。語調會改用全文計分，頁面會標明
  - 「大量重複收錄的句子，已刪除」：程式已去掉重複，照常處理；若內容在中途斷掉，摘要要寫明「問答只保留到第幾位」
  - 「和上一場的內容相似度 n%」：先比對兩份講的期間。相同就是重複收錄，摘要寫明，未來展望不和上一場比較，`vs_prior` 全部留空
  - 「只有 n 字，內容不足」：告訴使用者逐字稿可能收錄不完整，問他要不要繼續
- 舊版 `.doc` 不支援，請使用者另存成 `.docx`。
- 英文逐字稿（例如 LSEG StreetEvents、Refinitiv 格式）也支援：程式會跳過出席名單、移除每頁重複的頁首頁尾，並改用英文詞表計算語調。內容一樣用繁體中文寫，原文保留英文，細節見 `modules.md` 共通原則。若使用者沒說要用哪種語言，在第 2 步一起問。

### 2. 確認基本資料與模組

從逐字稿與檔名判斷公司、股票代號、年度、季別、法說會日期、產業。看不出來的欄位留空，不要猜。

接著向使用者確認模組。如果使用者在一開始已經講清楚要哪些模組（或說「全部」「照預設」），就跳過這步。

詢問時列出九個模組和一句說明，預設全選：

| 模組 | 說明 |
|---|---|
| 法說摘要 | 一段話交代這場法說會最重要的結果 |
| 未來展望 | **最重要**：展望總結＋指引表（方向、與上一場比較、原文） |
| 結論 | 成長動能從哪裡來、主要風險是什麼 |
| 投資評價 | 五級評價與兩個指標，看出整體偏樂觀或保守 |
| 關鍵數據 | 營收、毛利率、EPS 等數字，每筆附原文 |
| 語調分析 | 講稿與 Q&A 分別計分，比較管理層語氣 |
| QA 關注議題 | 法人問了什麼、怎麼回答、回答態度 |
| 出席人員組成 | 出席的管理層與提問法人 |
| 關鍵字 | 最常出現的詞，分正面與風險議題 |

同時問兩件事：
1. 順序要不要調整（不說就用上表順序）
2. 要不要加清單以外的模組（例如股利政策、ESG）

有提問工具（選項按鈕）時用工具問，一次問完；沒有就用文字問。基本資料有缺的（例如不知道季別），一起問。

### 3. 寫 dashboard.json

先讀 `references/modules.md` 和 `references/schema.md`，再依使用者選的模組寫 `WORK/dashboard.json`。

幾件最容易出錯的事：
- 原文欄位（`quote`）要從 `transcript_labeled.txt` 直接複製，只能刪減不能改字
- 數值欄位的數字必須出現在原文裡
- 不要填語調分數和關鍵字次數，那是 scripts 的工作
- QA 每題都要寫中文 `answer`（回答摘要）和 `stance`（回答態度）
- 每個模組都要把 Q&A 段也看過
- **未來展望最重要**：先寫它，花最多力氣；指引項目要齊全，每項都附原文
- 有上一場時，修正項目盡量補上 `prior_value` 和 `prior_quote`（上一場原文），首頁比較表才會有「前次 → 本次」
- 提問者照主持人點名填 `asker_name`、`asker_org`，另外整理 `analysts`；逐字稿沒說就寫「逐字稿未提及」，不要猜
- 最後讀 `references/briefs.md` 寫 `briefs`（LINE 同步、組內摘要、研報重點）；報告稿的數字只能用前面已寫進儀表板的內容

### 4. 計算、產生、檢查

```bash
python SKILL_DIR/scripts/tone_score.py WORK/transcript.json --out WORK/tone.json
python SKILL_DIR/scripts/keyword_count.py WORK/transcript.json --dashboard WORK/dashboard.json --out WORK/keywords.json
```

看 `keywords.json`：次數為 0 的詞會被拿掉，剩不到 8 個就補詞再跑。看完 `tone.json` 再寫或修改 `tone.note`，讓說明和數字一致。

```bash
python SKILL_DIR/scripts/render_motion.py WORK/dashboard.json --tone WORK/tone.json --keywords WORK/keywords.json \
    --transcript WORK/transcript.json --prior-transcript WORK/prior/transcript.json --outdir WORK/out
python SKILL_DIR/scripts/check_output.py --dashboard WORK/dashboard.json --transcript WORK/transcript.json \
    --keywords WORK/keywords.json --tone WORK/tone.json --prior-transcript WORK/prior/transcript.json \
    --html WORK/out/<檔名>.html
```

沒有上一場時，兩個指令都拿掉 `--prior-transcript`。`render_motion.py` 印出「原文定位：n 句成功，m 句找不到」時，m 不是 0 就要回去修正那幾句原文。

使用者要表格版時，把第一個指令換成 `python SKILL_DIR/scripts/render.py WORK/dashboard.json --tone WORK/tone.json --keywords WORK/keywords.json --outdir WORK/out`，檢查指令相同（程式會自動判斷是哪一版）。

`check_output.py` 回報 `errors` 時，修改 `dashboard.json` 後重新執行 render 和 check，直到 `ok: true`。常見修法：
- 原文找不到：回 `transcript_labeled.txt` 重新複製原句
- 數字不在原文：改數值，或換一句包含該數字的原文
- 字數不符：增刪內容，不要用標點湊字數
- 「由 58 天下降」只寫了起點：改成「由 58 天下降至 33 天」
- 報告稿的數字找不到：改用儀表板裡已有的數字，或先把那個數字連同原文寫進對應模組
- 上一場原文找不到：回 `WORK/prior/transcript_labeled.txt` 重新複製，找不到就拿掉 `prior_value` 和 `prior_quote`
- 出現禁用語：改寫成具體的事實或數字（清單見 `references/briefs.md`）

修三輪還過不了，就交出目前版本，並清楚告訴使用者哪幾項沒通過。

`warnings` 不會擋下輸出，但要在回覆裡提到（例如沒有瀏覽器可以檢查手機版面）。

**不要直接修改產生出來的 HTML。** 要改內容就改 `dashboard.json` 再 render；要改樣式就改模板（互動版 `assets/template_motion.html`、表格版 `assets/template.html`），並同步更新對應的 layout 文件。

### 5. 交付

- 把 `WORK/out/` 裡的 HTML 檔交給使用者。檔名格式是 `股票代號_年份Q季別.html`（例如 `2330_2026Q3.html`），第二階段的整合儀表板靠這個檔名辨識場次，不要改名。
- 回覆保持簡短：用了哪些模組、有沒有需要使用者注意的地方（辨識不到的發言人、沒有 Q&A、檢查沒通過的項目）。
- 不要在回覆裡重述整份儀表板的內容。
- 互動版內含完整逐字稿（看上下文要用），使用者要公開分享時，提醒他先確認逐字稿的使用授權。
- 提醒一次即可：內容由 AI 依逐字稿整理，僅供參考，不構成投資建議（頁尾也已寫明）。

## 使用者之後要修改時

- 「把投資評價拿掉」「關鍵數據放最前面」：改 `modules` 陣列後重新 render
- 「摘要寫短一點」「QA 少了一題」：改對應欄位後重新 render 和 check
- 「換個顏色」「字大一點」：說明版面是固定規格（見 `references/layout_motion.md`）；若使用者堅持要改樣式，請他確認後再改模板
- 「我要表格版」「要印出來」：改用 `render.py` 產生表格版

## 整合儀表板（第二階段）

把多場儀表板放進同一個資料夾，左側選單依「公司 → 年份 → 場次」切換，點公司可看跨季追蹤（指引變化、語調趨勢）。需要能寫入使用者電腦的環境（Claude Code 或 Claude Cowork）；在 claude.ai 網頁版就把資料夾壓成 zip 交付。

流程照 TEJ 簡報第 24 頁：
1. 使用者說「幫我在桌面建立整合儀表板」：建立**空的**資料夾（含整合頁、啟動程式、data/）

```bash
python SKILL_DIR/scripts/integrate.py --target ~/Desktop/整合儀表板
```

2. 使用者自己把儀表板 HTML 放進 `data/`，不想看就刪掉；檔名建議「公司_日期.html」
3. 雙擊啟動程式：重新掃描 `data/`，打開整合頁，側邊欄依「公司 → 年份 → 場次」列出所有儀表板

使用者要 Claude 代為加入時：

```bash
python SKILL_DIR/scripts/integrate.py --target ~/Desktop/整合儀表板 --add WORK [WORK2 ...]
```

- 在 Claude Code 跑完單場、而且 `~/Desktop/整合儀表板` 已經存在時，交付後主動把這場加進去（同一個指令），並告訴使用者
- `--add` 可以給工作資料夾、`dashboard.json` 或互動版 HTML；檔案會以「公司_日期.html」放進 `data/`，同一場重跑會覆蓋舊的
- 公司、季別、指引、語調都從互動版 HTML 內嵌的資料讀出，所以使用者手動放進去的檔案也能正確分組；表格版或其他 HTML 只能從檔名判斷
- 交付時說明：雙擊「整合儀表板.html」即可打開，不需要網路；啟動程式會先重建索引再打開
- Windows 中文路徑若有問題，提醒使用者直接雙擊 HTML

## 發布成網站（GitHub Pages）

整合儀表板是純靜態網頁，可以直接放上 GitHub Pages。使用者已經有網站儲存庫（根目錄有 `index.html`、`data/`、`integrate.py`）時：

```bash
python SKILL_DIR/scripts/render_motion.py ...（同步驟 4 的參數） --public --outdir WORK/out_public
python SKILL_DIR/scripts/integrate.py --target <網站儲存庫> --site --add WORK/out_public
```

- 放上網路一律用 `--public`：不附完整逐字稿，只保留引用的原句。完整逐字稿是 TEJ 的資料，使用者說已取得同意才可以不加
- `git push` 等於公開發布，推送前先告訴使用者要推送哪些檔案，等他同意
- 推送後 `.github/workflows/pages.yml` 會先跑上線前檢查（`integrate.py --check`），有 HTML 夾帶完整逐字稿就停止發布；通過後重新掃描 `data/` 並發布，約一分鐘後網站更新
- 網站有首頁、指引修正總覽、全站搜尋、關於頁，都由 `index.js` 的內容自動產生，不需要手動維護

## 處理多份逐字稿

使用者一次上傳多份時，每份各跑一次完整流程，各自產生一個 HTML，模組選擇共用一次即可。
