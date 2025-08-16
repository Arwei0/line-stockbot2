# -*- coding: utf-8 -*-
"""
從本機 twse.html / tpex.html 解析出股票代號，產生 symbols_all.txt
"""
import pandas as pd
import re
from io import StringIO

def _extract_codes_from_html_file(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    try:
        dfs = pd.read_html(StringIO(html))
    except ValueError:
        return []
    if not dfs:
        return []
    df = dfs[0]
    first_col = df.iloc[:, 0].astype(str).str.replace("\u3000", " ", regex=False)
    codes = first_col.str.extract(r"^\s*(\d{4})\b")[0].dropna().tolist()
    return codes

def build_symbols_all():
    codes_twse = _extract_codes_from_html_file("twse.html")
    codes_tpex = _extract_codes_from_html_file("tpex.html")
    all_codes = sorted(set(codes_twse + codes_tpex), key=lambda x: int(x))
    with open("symbols_all.txt", "w", encoding="utf-8") as f:
        for c in all_codes:
            f.write(c + "\n")
    print(f"[OK] symbols_all.txt updated: {len(all_codes)} codes "
          f"(TWSE {len(codes_twse)}, TPEX {len(codes_tpex)})")

if __name__ == "__main__":
    build_symbols_all()