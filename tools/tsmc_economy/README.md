# 台積電經濟體頁的資料與重建方式

產出：`tsmc/index.html`（單一檔案，資料全部內嵌）。

## 資料
- `data/`：從台積電官網（投資人關係網站各季頁面、年報、新聞稿）整理的 CSV：
  - `tsmc_calls.csv`：各季法說會日期與文件網址
  - `tsmc_quarterly.csv`：各季財務數字
  - `tsmc_annual.csv`：各年財務數字與員工數
  - `tsmc_footprint.csv`：建廠、擴點與子公司事件，以及經緯度
  - `tsmc_collection_notes.md`：整理方式與缺漏說明
- `words.json`：98 場法說會（2002 Q2–2026 Q3）各關鍵詞的出現次數，由 `words.py` 從逐字稿文字算出。逐字稿原文不放進儲存庫。
- `fin.json`：由 CSV 轉出的財務數字。

## 重建
1. 逐字稿 PDF 轉成文字（`pdftotext -layout`），放在 `txt/TSMC_YYYYQn_Transcript.txt`；修改 `words.py` 開頭的路徑後執行 `python words.py`。
2. `npm install world-atlas taiwan-atlas d3-geo topojson-client topojson-simplify`，再執行 `node geo.mjs`，產生 `geo.json` 與 `events.json`。
3. 修改 `mk.py` 的路徑後執行 `python mk.py`，把 `tpl.html` 和上述資料組成頁面，複製到 `tsmc/index.html`。

## 要調整什麼改哪裡
- 關鍵詞與分類：`words.py` 的 `W`（詞彙）與 `G`（終端市場分組）
- 章節標題與說明文字：`tpl.html` 裡的各個 `<section class="blk">`
- 議會圖的議題清單：`tpl.html` 裡的 `ISS`；密集提及的門檻：`HI`
