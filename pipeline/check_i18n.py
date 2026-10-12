"""檢查 assets/app.js 裡每個 _t('…') 的中文都在 assets/i18n-en.js 有英文（2026-10-12）。
改過 app.js 的文字後執行；有缺會列出並以非零結束（缺的字在英文版會顯示中文）。
用法（在倉庫根目錄）：python3 pipeline/check_i18n.py"""
import os, re, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'assets', 'app.js'), encoding='utf-8').read()
dic = open(os.path.join(ROOT, 'assets', 'i18n-en.js'), encoding='utf-8').read()
lit = r"(['\"])((?:(?!\1)[^\\]|\\.)*)\1"
used = {m.group(2) for m in re.finditer(r"_t\(" + lit + r"\)", src)}
have = {m.group(2) for m in re.finditer(r"^\s*" + lit + r":", dic, re.M)}
miss = sorted(used - have)
for k in miss: print('缺英文：', k)
print(f'_t 字串 {len(used)} 個，字典 {len(have)} 個，缺 {len(miss)} 個')
sys.exit(1 if miss else 0)
