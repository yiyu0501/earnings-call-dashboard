# 台積電官方資料整理與缺漏說明

整理日：2026-11-15（臺灣時間）。事件與財務涵蓋至2025年；2025 Q4法說與2025年報於2026年公布，仍屬2025年度資料。

## 檔案與格式

四份CSV皆為UTF-8（無BOM），逗號分隔、第一列為欄位名稱。括號內日期格式、Y/N、事件選項及字數限制視為欄位規格，欄名採call_date、transcript_available、date、type、event及description_zh等欄位識別字。空字串表示本次未取得可依規格直接填入的值，**不代表0、沒有該項活動或該設施不存在**。

只使用台積電官網、投資人關係網站、官方年報及官方新聞稿；未採用第三方財務資料。經緯度是依使用者指定提供的城市中心近似座標；部分臺灣廠區及Camas座標取自台積電官方廠區頁所嵌入的地圖網址。座標為定位用途，不是測量或公司公告數值。無法確認城市的海外註冊投資實體不填經緯度。

| 檔案 | 資料列數（不含表頭） |
|---|---:|
| tsmc_calls.csv | 116 |
| tsmc_quarterly.csv | 116 |
| tsmc_annual.csv | 39 |
| tsmc_footprint.csv | 89 |

## 逐字稿查核

- 1997 Q1至2001 Q4：各季未找到官方逐字稿，共20季。
- 2002 Q1：官方英文與中文Q1頁雖有逐字稿連結，但下載PDF封面、日期與內文均為2002 Q2（2002-07-25）。因此保留官方原連結供查核，transcript_available標為N；不把這份錯置PDF放進正常逐字稿壓縮檔。正確Q1逐字稿本次未查得；Q1 call_date 2002-05-09由當季報告的Conference Call Information確認。
- 2012 Q2：英文季度頁沒有逐字稿連結；已從台積電官方中文資料區補得英文PDF，日期2012-07-19，標為Y並納入壓縮檔。
- 其餘2002至2025各季：已下載並檢查PDF可讀性及季度封面。正常逐字稿共95份，每份依TSMC_YYYYQn_Transcript.pdf命名。
- 1997 Q1、Q2英文季度網址回傳404。保留這兩季的空列，不編造PDF網址。calls.csv的固定欄位沒有source_url；完整逐季官方頁面與404紀錄另附source_audit.csv（位於tsmc_data.zip），補足空列的查核路徑。
- 1997 Q3至1999 Q3有些季僅提供下一層財務報表頁，未取得可用的Management/Quarter Report，因此quarterly.csv保留空值及已查閱的官方來源頁。

## 欄位口徑

### 季度資料

1. 季度財務只取當季Quarter Report、Quarterly Release and Management Report、Press Release and Management Report或Management Report。未用另一季的比較欄回填缺值；未用年報推算單季。
2. 1999 Q4至2006 Q1所採季度主要報告多為母公司個體口徑；2006 Q2起改用當季合併口徑。保留原報告數字及當時EPS，不回溯套用後來股票股利、拆分、會計準則或重編。季度加總不一定等於年度合併報表。
3. 金額bn=十億；千元轉十億除以1,000,000、百萬美元轉十億美元除以1,000。僅做精確單位換算；未自行用匯率換算營收或資本支出。報告敘述與表格精度不同時，保留所採明示數字，不另增精度。
4. 毛利率、營益率、淨利率的10代表10%，不是0.10。EPS單位是新臺幣元。capex是當季實際資本支出，不填全年預算或累計支出；早期保留報告所明示的TSMC本體口徑。
5. wafer_shipment_k_12inch_equiv只填報告明示的千片十二吋約當量。早年八吋約當量不自行轉換；因此2014年以前該欄留空。
6. node_mix保留原技術分類、合併節點與單位，例如16/20nm、0.11/0.13um，不拆算。platform_mix只採平台營收占比，未將早年的Computer/Communication/Consumer應用別改造成HPC/Smartphone。HPC、IoT、Auto、DCE是官方平台名稱的縮寫。
7. 地區分類按各期原報告，Europe與EMEA等不強行統一；地區是客戶營收歸屬，不是工廠所在地。
8. next_q_*只抄同一份當季Management Report PDF明示的下一季區間。2007 Q4起新聞稿與Management Report多已拆成不同PDF；未從另行發布的Earnings Release、簡報或逐字稿補入預測，故這些欄位多為空白。文字「持平」「約45%」不擴寫成上下限。
9. calls.csv的financial_statements_url若早年分成損益表、資產負債表、現金流量表，保留全部實際PDF網址，以分號分隔。management_report_url也保留早期名稱為Quarter Report的正式報告。

### 年度資料

1. 1987至1989沒有取得可直接填入的年度財務數字；不從圖形柱高讀值、不倒推成長率。
2. 1990至1994營收與淨利取1994年報PDF第24頁（印刷頁21）的五年損益表；1995至1998取1999年報的五年表，屬母公司歷史口徑。1999年起優先取各年度合併報表；淨利有區分時採歸屬母公司股東數字。各年度以該份報告當時公布的資料為準，不替換成日後追溯重編值。
3. 2005以前的年報美元營收敘述多對應母公司個體；為避免與本檔合併新臺幣營收混用，未直接填入。美元欄僅採明確可對應的官方披露。
4. 年度capex只採年報或官方年度Form 20-F明示的美元實際支出；不加總季度、不將新臺幣現金流量自行換算美元。2025採20-F的US$40,895 million，精確換單位為40.895；與季度報告四捨五入後40.90的顯示精度不同。
5. 人數：早年取TSMC人員表，較近年度依年報可查得的公司及子公司口徑；範圍隨合併實體變動，不能當作完全同口徑時間序列。原文只有「over」的數字未當成精確人數。
6. capacity只填官方直接明示的十二吋約當量單一值。2013年的7309.680千片是2014年報比較表明示的十二吋約當量，非自行由八吋換算；2014年為8175.183千片。早年只有八吋、近年只有區間或「超過／約」的資料不以中點、下限或概略值代填。原官方披露另列於下表。
7. dividend_per_share_ntd定義為**當曆年實際支付的普通股現金股利**，不是該年盈餘所屬季度宣告總額，也不含股票股利。2019年開始由年度轉為季度支付，不能混用盈餘年度與支付年度。未確認的早年支付額留空。
8. most_advanced_node_in_volume只列可由年報量產敘述確認者；不把風險生產、資格驗證或報告出版後下一年度量產，回填成當年度量產。2013年報稱20nm於2014年進入量產，2013年仍記28nm；2016年報明確指出10nm於2016年量產。
9. market_share_note保留公司年報的市場定義與披露，未自行估算。早年若僅有第三方市場估計，未填入。2013至2019是代工市場；2020至2023是全球半導體不含記憶體產值；2024年起Foundry 2.0包括邏輯晶圓、封裝、測試、光罩等。2018年報56%與2019年報所引上一年51%反映定義／資料重編差異，未改寫原年度披露。

### 足跡資料

- 事件依所知年、月、日保留原精度，不補「01-01」。同年只有年精度的事件，其年度內位置不代表與有日期事件的先後關係。
- 子公司成立優先取年報的法定設立日；與公司歷史圖所示開始籌設或營運年可能不同。
- 晶圓廠的商業生產起始年優先採官方年度20-F設施表。此處「量產」也包含官方記載的commercial production，不等於每一技術節點的量產典禮日期。
- 公司創立以總公司／辦公室類型表達。事件選項沒有收購、更名、啟用，故以「宣布」或「成立」配合description_zh保留實際含義；沒有把合併改稱關廠。
- 奧斯汀與聖荷西設計服務中心未查得設立日，只記2025-03-04官方新聞稿確認其存在的披露事件，不宣稱當天新成立。
- 擴建計畫與已量產事件分開；亞利桑那新增晶圓廠、封裝廠、研發中心的2025項目是宣布計畫，不是完工或量產。
- 足跡表是已取得官方事件證據的清單；不以目前地址倒推設立年份。未查得可靠事件日期的據點或期別，不編造動工、啟用或關閉事件。

## 官方僅提供範圍或概略數值、CSV未代填的項目

| 年 | 欄位 | 官方原數值換為欄位單位後的表示 | 官方來源 |
|---|---|---|---|
| 2013 | employees | >40483 | https://investor.tsmc.com/sites/ir/annual-report/2013/c_11_1_0.pdf;https://investor.tsmc.com/sites/ir/annual-report/2014/e_11_1.pdf;https://investor.tsmc.com/sites/ir/annual-report/2014/e_11_1.pdf |
| 2014 | employees | >43591 | https://investor.tsmc.com/sites/ir/annual-report/2014/e_11_1.pdf |
| 2015 | employees | >45272 | https://investor.tsmc.com/sites/ir/annual-report/2015/e_11.pdf |
| 2015 | capacity_k_12inch_equiv_wafers | 9000-10000 | https://investor.tsmc.com/sites/ir/annual-report/2015/e_11.pdf |
| 2016 | employees | >46968 | https://investor.tsmc.com/sites/ir/annual-report/2016/e_11_0.pdf |
| 2016 | capacity_k_12inch_equiv_wafers | 10000-11000 | https://investor.tsmc.com/sites/ir/annual-report/2016/e_11_0.pdf |
| 2017 | capacity_k_12inch_equiv_wafers | 11000-12000 | https://investor.tsmc.com/sites/ir/annual-report/2017/e_11_3.pdf |
| 2018 | capacity_k_12inch_equiv_wafers | 12000-13000 | https://investor.tsmc.com/sites/ir/annual-report/2018/e_all_5.pdf |
| 2019 | capacity_k_12inch_equiv_wafers | 12000-13000 | https://investor.tsmc.com/sites/ir/annual-report/2019/e_all.pdf |
| 2020 | capacity_k_12inch_equiv_wafers | 12000-13000 | https://investor.tsmc.com/sites/ir/annual-report/2020/2020Annual%20Report_E_%20.pdf |
| 2021 | capacity_k_12inch_equiv_wafers | 13000-14000 | https://investor.tsmc.com/sites/ir/annual-report/2021/2021_Annual%20Report%20_E.pdf |
| 2022 | capacity_k_12inch_equiv_wafers | 15000-16000 | https://investor.tsmc.com/sites/ir/annual-report/2022/2022%20Annual%20Report-E.pdf |
| 2023 | capacity_k_12inch_equiv_wafers | 16000-17000 | https://investor.tsmc.com/sites/ir/annual-report/2023/2023_Annual_Report_E.pdf |
| 2024 | capacity_k_12inch_equiv_wafers | ~17000 | https://investor.tsmc.com/sites/ir/annual-report/2024/2024-Annual%20Report-E.pdf |
| 2025 | capacity_k_12inch_equiv_wafers | >17000 | https://investor.tsmc.com/sites/ir/annual-report/2025/2025%20TSMC%20Annual%20Report.E.pdf;https://investor.tsmc.com/sites/ir/sec-filings/2025_20F%20Report.pdf |

## 各欄空白比例

空白率超過50%者如下；分母為該檔案資料列數。

| 檔案 | 欄位 | 空白列數 | 空白率 |
|---|---|---:|---:|
| tsmc_quarterly.csv | revenue_usd_bn | 83/116 | 71.6% |
| tsmc_quarterly.csv | wafer_shipment_k_12inch_equiv | 68/116 | 58.6% |
| tsmc_quarterly.csv | platform_mix | 88/116 | 75.9% |
| tsmc_quarterly.csv | next_q_revenue_guide_low | 107/116 | 92.2% |
| tsmc_quarterly.csv | next_q_revenue_guide_high | 107/116 | 92.2% |
| tsmc_quarterly.csv | next_q_revenue_guide_unit | 107/116 | 92.2% |
| tsmc_quarterly.csv | next_q_gm_guide_low | 103/116 | 88.8% |
| tsmc_quarterly.csv | next_q_gm_guide_high | 103/116 | 88.8% |
| tsmc_annual.csv | revenue_usd_bn | 20/39 | 51.3% |
| tsmc_annual.csv | capex_usd_bn | 30/39 | 76.9% |
| tsmc_annual.csv | capacity_k_12inch_equiv_wafers | 37/39 | 94.9% |
| tsmc_annual.csv | market_share_note | 26/39 | 66.7% |

完整逐季查核頁面記錄見tsmc_data.zip內source_audit.csv。所有空值維持空字串，未用0、NA、估計數或跨期補值取代。
