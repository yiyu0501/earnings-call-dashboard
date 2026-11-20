## 這次改了什麼

<!-- 一兩句話說明目的與做法；相關 issue 請寫 Closes #編號 -->

## 類型

- [ ] 新增或更新法說會儀表板
- [ ] 網站版面或功能
- [ ] skill（規則、程式、模板）
- [ ] 文件
- [ ] 部署與工具

## 上線前檢查

- [ ] `python integrate.py --target . --site --check` 通過
- [ ] `index.html` 與 `skill/earnings-call-dashboard/assets/integrated_template.html` 一致
- [ ] `node tools/site_test.js` 通過（改到版面時）
- [ ] `data/` 只放公開版儀表板，沒有完整逐字稿
- [ ] 已更新 `CHANGELOG.md`；較大的改動已記在開發紀錄
- [ ] 手機與深色模式看過（改到版面時）
