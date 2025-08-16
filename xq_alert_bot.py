# -*- coding: utf-8 -*-
# xq_worker.py — 常駐掃描台股並用 LINE Messaging API 推播
import os, time, json, requests, datetime
from typing import Optional, Dict, Any, List

# 你現有的工具
from indicators import sma, macd
from refresh_symbols_all import refresh_symbols_all

# 用 Messaging API 推播（先前我們做好的）
from line_messaging_push import push_message

# ---------------- Yahoo helpers ----------------
def fetch_quote_multi(y_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    res = {}
    if not y_symbols:
        return res
    joined = ",".join(y_symbols)
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={joined}"
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        for item in data.get("quoteResponse", {}).get("result", []):
            sym = item.get("symbol")
            if sym:
                res[sym] = item
    except Exception:
        pass
    return res

def fetch_chart(y_symbol: str, rng="6mo", interval="1d") -> Optional[Dict[str, Any]]:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{y_symbol}?range={rng}&interval={interval}"
        r = requests.get(url, timeout=20)
        return r.json()
    except Exception:
        return None

def extract_ohlcv(chart_json: Dict[str, Any]):
    result = chart_json.get("chart", {}).get("result", [])
    if not result:
        return [], [], [], [], [], []
    r0 = result[0]
    ts = r0.get("timestamp", []) or []
    quote = r0.get("indicators", {}).get("quote", [{}])[0]
    return (ts,
            quote.get("open", []),
            quote.get("high", []),
            quote.get("low", []),
            quote.get("close", []),
            quote.get("volume", []))

def choose_symbol_suffix_bulk(tickers: List[str], chunk: int = 300) -> Dict[str, str]:
    """
    分段查詢 .TW / .TWO，避免 URL 太長導致整批失敗。
    回傳 { '2330': '2330.TW', '5483': '5483.TWO', ... }
    """
    out: Dict[str, str] = {}

    # 先試 .TW（上市）
    for i in range(0, len(tickers), chunk):
        seg = tickers[i:i+chunk]
        tw_syms = [t + ".TW" for t in seg]
        resp = fetch_quote_multi(tw_syms)  # {'2330.TW': {...}, ...}
        for ysym in resp.keys():
            base = ysym.split(".")[0]
            out[base] = ysym

    # 再補 .TWO（上櫃）—只查還沒判斷出的
    remaining = [t for t in tickers if t not in out]
    for i in range(0, len(remaining), chunk):
        seg = remaining[i:i+chunk]
        two_syms = [t + ".TWO" for t in seg]
        resp = fetch_quote_multi(two_syms)
        for ysym in resp.keys():
            base = ysym.split(".")[0]
            out[base] = ysym

    # 診斷輸出
    print(f"[DEBUG] 判斷 suffix：輸入 {len(tickers)} 檔 → OK {len(out)} 檔，未判斷 {len(tickers)-len(out)} 檔")
    return out

_chart_cache = {}
def get_chart_cached(y_symbol: str, rng: str, interval: str, refresh_minutes: int):
    key = (y_symbol, interval)
    now = time.time()
    ent = _chart_cache.get(key)
    if not ent or now - ent["last"] > refresh_minutes * 60:
        j = fetch_chart(y_symbol, rng=rng, interval=interval)
        ts, o, h, l, c, v = extract_ohlcv(j) if j else ([],[],[],[],[],[])
        ent = {"ts": ts, "open": o, "high": h, "low": l, "close": c, "volume": v, "last": now}
        _chart_cache[key] = ent
    return ent

# ---------------- 規則 ----------------
def r1_macd_combo(cfg, hist: List[Optional[float]]) -> Optional[str]:
    if len(hist) < 2:
        return None
    eps = float(cfg["macd"].get("eps", 1e-6))
    h_now, h_prev = hist[-1], hist[-2]
    if h_now is None or h_prev is None:
        return None
    cond1 = (h_now < -eps) and (h_prev < -eps) and (h_now > h_prev + eps)
    cond2 = (h_prev < -eps) and (h_now >= -eps)
    cond3 = (h_now > eps) and (h_prev > eps) and (h_now > h_prev + eps)
    if cond1 or cond2 or cond3:
        tag = "綠柱縮短" if cond1 else ("綠轉紅" if cond2 else "紅柱變大")
        return f"R1 MACD {tag} (hist 前:{h_prev:.5f} 今:{h_now:.5f})"
    return None

def r2_ma34_up_daily(ma34: List[Optional[float]]) -> Optional[str]:
    if len(ma34) < 2 or ma34[-1] is None or ma34[-2] is None:
        return None
    return "R2 日34MA上揚" if ma34[-1] > ma34[-2] else None

def r3_weekly_ma5_pattern(ma5w: List[Optional[float]]) -> Optional[str]:
    if len(ma5w) < 3 or None in (ma5w[-1], ma5w[-2], ma5w[-3]):
        return None
    return "R3 週5MA型態成立" if (ma5w[-2] >= ma5w[-3] and ma5w[-1] > ma5w[-2]) else None

def r4_daily_ma5_up(ma5d: List[Optional[float]]) -> Optional[str]:
    if len(ma5d) < 2 or None in (ma5d[-1], ma5d[-2]):
        return None
    return "R4 日5MA上揚" if ma5d[-1] > ma5d[-2] else None

def r5_within_pct_to_ma5(price: float, ma5d_last: Optional[float], pct_min: float, pct_max: float) -> Optional[str]:
    if ma5d_last is None or price is None:
        return None
    diff_pct = (price - ma5d_last) / ma5d_last * 100.0
    return (f"R5 價距日5MA {diff_pct:.2f}% 在 {pct_min}~{pct_max}%"
            if (diff_pct >= pct_min and diff_pct <= pct_max) else None)

def r6_price_gt(price: float, thr: float) -> Optional[str]:
    if price is None:
        return None
    return f"R6 價>{thr}" if price > thr else None

def r7_volume_gt(vol_now: Optional[int], min_shares: int) -> Optional[str]:
    if vol_now is None:
        return None
    return (f"R7 量 {vol_now:,} > {min_shares:,} 股" if vol_now > min_shares else None)

def r8_price_gt_ma5(price: float, ma5d_last: Optional[float]) -> Optional[str]:
    if ma5d_last is None or price is None:
        return None
    return (f"R8 價>{ma5d_last:.2f}(日5MA)" if price > ma5d_last else None)

_last_push = {}
def should_push(symbol: str, rule_id: str, cooldown_minutes: int, once_per_day: bool) -> bool:
    key = (symbol, rule_id, datetime.date.today() if once_per_day else None)
    now = time.time()
    last = _last_push.get(key)
    if once_per_day:
        if last:
            return False
        _last_push[key] = now
        return True
    if last and now - last < cooldown_minutes * 60:
        return False
    _last_push[key] = now
    return True

def main():
    # 讀設定
    with open("config.json","r",encoding="utf-8") as f:
        cfg = json.load(f)

    # 啟動提示（可在 config.json 設 startup_ping: true）
    if cfg.get("startup_ping", False):
        push_message("【啟動】XQ 全市場掃描（Render Worker）已啟動 🚀")

    # 缺清單就試圖更新；失敗再要求用 twse.html/tpex.html 生成
    if not os.path.exists("symbols_all.txt"):
        try:
            n = refresh_symbols_all()
            print(f"[INFO] symbols_all.txt updated: {n} codes")
        except Exception as e:
            print("[ERROR] 產生 symbols_all.txt 失敗，請先用 build_symbols_from_local.py：", e)
            return

    # 讀清單後
    with open("symbols_all.txt","r",encoding="utf-8") as f:
        all_syms = [s.strip() for s in f if s.strip()]
    print(f"[DEBUG] symbols_all.txt 讀到 {len(all_syms)} 檔，前5：{all_syms[:5]}")

    sym_map = choose_symbol_suffix_bulk(all_syms, chunk=300)
    print(f"[DEBUG] sym_map 成功對應 {len(sym_map)} 檔，前5：{list(sym_map.items())[:5]}")

    y_list = [sym_map[s] for s in all_syms if s in sym_map]
    print(f"[DEBUG] y_list 最終可查 {len(y_list)} 檔，前5：{y_list[:5]}")

    poll = int(cfg.get("poll_seconds", 90))
    chunk = int(cfg.get("yahoo_quote_chunk", 50))
    batch_size = int(cfg.get("batch_size", 200))
    cooldown = int(cfg.get("cooldown_minutes", 30))
    once_per_day = bool(cfg.get("once_per_day", False))

    print(f"[INFO]（Worker）全市場 {len(y_list)} 檔；每輪 {batch_size} 檔；chunk={chunk}。")

    idx = 0
    while True:
        start = time.time()

        batch = y_list[idx: idx+batch_size]
        if not batch:
            idx = 0
            batch = y_list[idx: idx+batch_size]
        idx += batch_size

        # 取報價
        quotes = {}
        for i in range(0, len(batch), chunk):
            group = batch[i:i+chunk]
            quotes.update(fetch_quote_multi(group))

        # 計算指標 & 規則
        for ysym in batch:
            q = quotes.get(ysym, {})
            tkr = ysym.split(".")[0]
            name = q.get("shortName") or q.get("longName") or tkr
            ex = q.get("fullExchangeName") or q.get("exchange")
            price = q.get("regularMarketPrice") or q.get("postMarketPrice") or q.get("preMarketPrice")
            vol_now = q.get("regularMarketVolume")
            chg = q.get("regularMarketChangePercent")
            yclose = q.get("regularMarketPreviousClose")

            d_ent = get_chart_cached(ysym, rng="8mo", interval="1d",
                                     refresh_minutes=cfg["cache_refresh_minutes"]["daily"])
            w_ent = get_chart_cached(ysym, rng="5y", interval="1wk",
                                     refresh_minutes=cfg["cache_refresh_minutes"]["weekly"])

            ma5_d = sma(d_ent["close"], 5)
            ma34_d = sma(d_ent["close"], 34)
            dif_d, dem_d, hist_d = macd(d_ent["close"],
                                        cfg["macd"]["fast"], cfg["macd"]["slow"], cfg["macd"]["signal"])
            ma5_w = sma(w_ent["close"], 5)

            fired = []
            if cfg["rules"].get("r1_macd_combo", True):
                msg = r1_macd_combo(cfg, hist_d);           fired.append(msg) if msg else None
            if cfg["rules"].get("r2_ma34_up_daily", True):
                msg = r2_ma34_up_daily(ma34_d);             fired.append(msg) if msg else None
            if cfg["rules"].get("r3_weekly_ma5_pattern", True):
                msg = r3_weekly_ma5_pattern(ma5_w);         fired.append(msg) if msg else None
            if cfg["rules"].get("r4_daily_ma5_up", True):
                msg = r4_daily_ma5_up(ma5_d);               fired.append(msg) if msg else None
            if cfg["rules"].get("r5_within_0_to_4pct_of_ma5", True):
                msg = r5_within_pct_to_ma5(price, ma5_d[-1] if ma5_d else None,
                                           cfg["diff_to_ma5_pct"]["min"],
                                           cfg["diff_to_ma5_pct"]["max"]);    fired.append(msg) if msg else None
            if cfg["rules"].get("r6_price_gt_20", True):
                msg = r6_price_gt(price, cfg["limits"]["price_min"]);          fired.append(msg) if msg else None
            if cfg["rules"].get("r7_volume_gt_1000_lots", True):
                msg = r7_volume_gt(vol_now, cfg["limits"]["min_volume_shares"]); fired.append(msg) if msg else None
            if cfg["rules"].get("r8_price_gt_ma5", True):
                msg = r8_price_gt_ma5(price, ma5_d[-1] if ma5_d else None);    fired.append(msg) if msg else None

            if fired:
                to_send = []
                for note in fired:
                    rid = note.split()[0]
                    if should_push(tkr, rid, cooldown_minutes=cooldown, once_per_day=once_per_day):
                        to_send.append(note)
                if to_send:
                    text = (f"【觸發】{name} ({tkr}) {ex}\n"
                            f"價：{price}（昨收：{yclose}，漲跌：{(chg or 0):.2f}%）\n"
                            f"{'；'.join(to_send)}\n"
                            f"時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(text)
                    push_message(text)

        # 節流
        wait = max(5, poll - int(time.time() - start))
        time.sleep(wait)

if __name__ == "__main__":
    main()