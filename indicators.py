
from typing import List, Tuple, Optional

def sma(values: List[float], window: int) -> List[Optional[float]]:
    out = [None]*len(values)
    if window <= 0: 
        return out
    s = 0.0
    for i, v in enumerate(values):
        if v is None:
            out[i] = None
            continue
        s += v
        if i >= window:
            s -= (values[i-window] if values[i-window] is not None else 0.0)
        if i >= window-1 and all(values[k] is not None for k in range(i-window+1, i+1)):
            out[i] = s / window
        else:
            out[i] = None
    return out

def _ema(vals: List[Optional[float]], period: int) -> List[Optional[float]]:
    out = [None]*len(vals)
    if period <= 0:
        return out
    k = 2/(period+1)
    ema_prev = None
    for i, v in enumerate(vals):
        if v is None: 
            out[i] = ema_prev
            continue
        if ema_prev is None:
            ema_prev = v
        else:
            ema_prev = v*k + ema_prev*(1-k)
        out[i] = ema_prev
    return out

def macd(close: List[Optional[float]], fast=12, slow=26, signal=9) -> Tuple[list, list, list]:
    vals = [ (float(v) if v is not None else None) for v in close ]
    ema_fast = _ema(vals, fast)
    ema_slow = _ema(vals, slow)
    dif = [ (f - s) if (f is not None and s is not None) else None for f, s in zip(ema_fast, ema_slow) ]
    dem = _ema(dif, signal)
    hist = [ (d - m) if (d is not None and m is not None) else None for d, m in zip(dif, dem) ]
    return dif, dem, hist
