"""把舊版首頁 classic.html（2026-11-11 前是 index.html）裡 assets/app.css、assets/app.js、assets/i18n-en.js 的 ?v= 換成三個檔案的內容雜湊。
GitHub Pages 每個檔案各自快取 10 分鐘，不加版本號時手機可能拿到新 JS 配舊 CSS；改過 assets 後執行一次再提交。
用法（在倉庫根目錄）：python3 pipeline/stamp_assets.py"""
import hashlib, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
v = hashlib.sha256(b''.join(open(P('assets', f), 'rb').read() for f in ('app.css', 'app.js', 'i18n-en.js'))).hexdigest()[:10]
html = open(P('classic.html'), encoding='utf-8').read()   # 2026-11-11 舊版首頁搬到 classic.html；新版首頁 index.html 由 pipeline/next/build.py 產生，不用這支
new = re.sub(r'assets/(app\.(?:css|js)|i18n-en\.js)(\?v=[0-9a-f]+)?(["\'])', lambda m: f'assets/{m.group(1)}?v={v}{m.group(3)}', html)
open(P('classic.html'), 'w', encoding='utf-8').write(new)
print('assets version', v)
