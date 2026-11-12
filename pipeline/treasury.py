#!/usr/bin/env python3
"""上市公司持幣（2026-11-12 使用者要求：Strategy 的持幣成本線）。

CoinGecko 的公開接口列出持有比特幣的上市公司：持幣量、買進總成本、現值。平均成本＝買進總成本 ÷ 持幣量。
Strategy（MSTR）是最大的一家，它的平均成本常被當成一條參考價位：跌破代表它整體帳面虧損，但它不是用幣抵押借錢，跌破不等於被迫賣。
這個接口只有現在的數字，沒有歷史，所以圖上畫的是一條水平線（現在的平均成本），不是成本隨時間的變化。只作讀值。"""


def build(get, close, last):
    j = get('https://api.coingecko.com/api/v3/companies/public_treasury/bitcoin')
    cs = (j or {}).get('companies') if isinstance(j, dict) else None
    if not cs: return None
    def one(c):
        b = c.get('total_holdings') or 0; e = c.get('total_entry_value_usd') or 0
        return dict(name=c.get('name'), sym=(c.get('symbol') or '').split('.')[0], btc=round(b), cost=round(e / b) if b and e else None, pct_supply=c.get('percentage_of_total_supply'))
    top = [one(c) for c in sorted(cs, key=lambda c: -(c.get('total_holdings') or 0))[:6]]
    m = next((x for x in top if x['sym'] == 'MSTR' or (x['name'] or '').lower().startswith(('strategy', 'microstrategy'))), None)
    if not m or not m['cost']: return None
    return dict(date=last, total=round(j.get('total_holdings') or 0), n=len(cs), top=top,
                mstr=dict(m, entry_usd_b=round(m['btc'] * m['cost'] / 1e9, 1), pnl_pct=round((close / m['cost'] - 1) * 100, 1), share=round(m['btc'] / (j.get('total_holdings') or m['btc']) * 100, 1)),
                src='CoinGecko', link='https://www.coingecko.com/en/treasuries/bitcoin', note='CoinGecko 上市公司持幣；平均成本＝買進總成本 ÷ 持幣量；只有現值、沒有歷史；只作讀值')
