# -*- coding: utf-8 -*-
"""
更新台股全清單（symbols_all.txt）— 強化版
優先流程：HTTP -> HTTPS（均允許 verify=False） -> 若失敗則讀本機 twse.html / tpex.html
"""
import os
import re
import requests
import pandas as pd
from io import StringIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException

TWSE_HTTP = "http://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
TPEX_HTTP = "http://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
TWSE_HTTPS = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
TPEX_HTTPS = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"

def _session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0 Safari/537.36")
    })
    retries = Retry(total=2, backoff_factor=0.4, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def _fetch(url: str) -> str:
    s = _session()
    r = s.get(url, timeout=25, verify=False)  # 放寬驗證避免 SSL 問題
    r.encoding = "utf-8"
    r.raise_for_status()
    return r.text

def _get_html_pair():
    # 1) HTTP 優先
    try:
        print(f"[INFO] 透過 HTTP 抓取 TWSE ... {TWSE_HTTP}")
        twse_html = _fetch(TWSE_HTTP)
        print(f"[INFO] 透過 HTTP 抓取 TPEX ... {TPEX_HTTP}")
        tpex_html = _fetch(TPEX_HTTP)
        return twse_html, tpex_html
    except Exception as e1:
        print("[WARN] HTTP 抓取失敗，改試 HTTPS。原因：", e1)

    # 2) HTTPS 次要
    try:
        print(f"[INFO] 透過 HTTPS 抓取 TWSE ... {TWSE_HTTPS}")
        twse_html = _fetch(TWSE_HTTPS)
        print(f"[INFO] 透過 HTTPS 抓取 TPEX ... {TPEX_HTTPS}")
        tpex_html = _fetch(TPEX_HTTPS)
        return twse_html, tpex_html
    except Exception as e2:
        print("[WARN] HTTPS 抓取也失敗。原因：", e2)

    # 3) 最後：讀本機快取檔
    if not (os.path.exists("twse.html") and os.path.exists("tpex.html")):
        raise RuntimeError("網路抓取失敗，且找不到本機 twse.html / tpex.html")
    print("[INFO] 讀取本機 twse.html / tpex.html ...")
    with open("twse.html", "r", encoding="utf-8", errors="ignore") as f:
        twse_html = f.read()
    with open("tpex.html", "r", encoding="utf-8", errors="ignore") as f:
        tpex_html = f.read()
    return twse_html, tpex_html

def _extract_codes_from_html(html: str):
    try:
        dfs = pd.read_html(StringIO(html))
    except ValueError:
        return []
    if not dfs:
        return []
    df = dfs[0]
    # 第一欄通常是「1101　台泥」；將全形空白換成半形，正則取前 4 碼
    first_col = df.iloc[:, 0].astype(str).str.replace("\u3000", " ", regex=False)
    codes = first_col.str.extract(r"^\s*(\d{4})\b")[0].dropna().tolist()
    return codes

def refresh_symbols_all() -> int:
    twse_html, tpex_html = _get_html_pair()
    codes_twse = _extract_codes_from_html(twse_html)
    codes_tpex = _extract_codes_from_html(tpex_html)

    all_codes = sorted(set(codes_twse + codes_tpex), key=lambda x: int(x))
    with open("symbols_all.txt", "w", encoding="utf-8") as f:
        for c in all_codes:
            f.write(c + "\n")

    print(f"[OK] symbols_all.txt updated: {len(all_codes)} codes "
          f"(TWSE {len(codes_twse)}, TPEX {len(codes_tpex)})")
    return len(all_codes)

if __name__ == "__main__":
    refresh_symbols_all()