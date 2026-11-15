# 一頁簡介

`onepager.html` 是 `docs/一頁簡介.pdf` 的原稿（A4 直式）。改完文字後用瀏覽器「列印 → 另存為 PDF」（紙張 A4、邊界無、勾選背景圖形），或執行：

```bash
node -e "require('playwright').chromium.launch().then(async b=>{const p=await b.newPage();await p.goto('file://'+require('path').resolve('tools/onepager/onepager.html'));await p.pdf({path:'docs/一頁簡介.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});await b.close();})"
```

截圖（`*_p.jpg`）與 QR code（`qr.png`）也在這個資料夾。
