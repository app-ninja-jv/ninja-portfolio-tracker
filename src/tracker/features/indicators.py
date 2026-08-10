"""Indicators, pure functions over lists of floats.

Every function returns None rather than a partial answer when there is not enough
history. Callers must handle None explicitly — do NOT write `(macd or 0) > 0`,
which silently turns "unavailable" into "negative". That bug scored every ticker
identically in an earlier version of this project.
"""
from __future__ import annotations

import math
import statistics as st

Bar = dict  # {"date": str, "high": float, "low": float, "close": float, "volume": float}


# ---------------------------------------------------------------- basics
def returns(xs: list[float]) -> list[float]:
    return [xs[i] / xs[i - 1] - 1 for i in range(1, len(xs))]


def sma(xs: list[float], n: int) -> float | None:
    return sum(xs[-n:]) / n if len(xs) >= n else None


def sma_series(xs: list[float], n: int) -> list[float | None]:
    return [sum(xs[i - n + 1: i + 1]) / n if i >= n - 1 else None for i in range(len(xs))]


def ema(xs: list[float], n: int) -> list[float]:
    k = 2 / (n + 1)
    out, e = [], xs[0]
    out.append(e)
    for x in xs[1:]:
        e = x * k + e * (1 - k)
        out.append(e)
    return out


# ---------------------------------------------------------------- momentum
def rsi(xs: list[float], n: int = 14) -> float | None:
    """Wilder's RSI."""
    if len(xs) < n + 1:
        return None
    ch = [xs[i] - xs[i - 1] for i in range(1, len(xs))]
    gains = [max(c, 0.0) for c in ch]
    losses = [max(-c, 0.0) for c in ch]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for i in range(n, len(ch)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def macd(xs: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (line, signal, histogram) or (None, None, None) if history is short."""
    if len(xs) < slow + signal:
        return None, None, None
    line = [a - b for a, b in zip(ema(xs, fast), ema(xs, slow), strict=True)]
    sig = ema(line, signal)
    return line[-1], sig[-1], line[-1] - sig[-1]


def roc(xs: list[float], n: int) -> float | None:
    return (xs[-1] / xs[-1 - n] - 1) * 100 if len(xs) > n else None


# ---------------------------------------------------------------- volatility
def realised_vol(xs: list[float], weeks: int | None = None) -> float | None:
    r = returns(xs)
    if weeks:
        r = r[-weeks:]
    if len(r) < 6:
        return None
    return st.pstdev(r) * math.sqrt(52) * 100


def weekly_sigma(annual_vol_pct: float) -> float:
    """Convert annualised vol to a one-week sigma, for σ-normalised thresholds."""
    return annual_vol_pct / math.sqrt(52)


def atr(bars: list[Bar], n: int = 14) -> float | None:
    if len(bars) < n + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        hi, lo, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
    return sum(trs[-n:]) / n


# ---------------------------------------------------------------- position / extension
def zscore(x: float, population: list[float]) -> float | None:
    if len(population) < 3:
        return None
    sd = st.pstdev(population)
    return (x - st.mean(population)) / sd if sd else None


def extension(xs: list[float], n: int) -> tuple[float | None, float | None, int]:
    """% above the n-week MA, its z-score against own history, and the n of that history."""
    ms = sma_series(xs, n)
    hist = [(xs[i] - ms[i]) / ms[i] * 100 for i in range(len(xs)) if ms[i]]
    if not hist:
        return None, None, 0
    return hist[-1], zscore(hist[-1], hist), len(hist)


def bollinger_pct_b(xs: list[float], n: int = 20, k: float = 2.0) -> float | None:
    if len(xs) < n:
        return None
    m, sd = st.mean(xs[-n:]), st.pstdev(xs[-n:])
    if sd == 0:
        return None
    lo, hi = m - k * sd, m + k * sd
    return (xs[-1] - lo) / (hi - lo) * 100


def max_drawdown(xs: list[float]) -> float:
    peak, mdd = xs[0], 0.0
    for x in xs:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    return mdd * 100


def drawdown_from_high(xs: list[float]) -> float:
    return (xs[-1] / max(xs) - 1) * 100


def range_position(xs: list[float]) -> float | None:
    lo, hi = min(xs), max(xs)
    return (xs[-1] - lo) / (hi - lo) * 100 if hi > lo else None


# ---------------------------------------------------------------- volume
def volume_zscore(vols: list[float]) -> float | None:
    return zscore(vols[-1], vols)


def up_down_volume(closes: list[float], vols: list[float], weeks: int = 8) -> float | None:
    """Sum of volume on up weeks / sum on down weeks. >1 accumulation, <1 distribution.

    Leads price more reliably than any oscillator here. Its clustering matters more
    than its level — three distribution weeks in a row is a different signal from
    three scattered across a year.
    """
    r = returns(closes)
    if len(r) < 2:
        return None
    rr, vv = r[-weeks:], vols[-len(r):][-weeks:]
    up = sum(v for x, v in zip(rr, vv, strict=True) if x > 0)
    dn = sum(v for x, v in zip(rr, vv, strict=True) if x < 0)
    return up / dn if dn else None


# ---------------------------------------------------------------- cross-sectional
def align(a_dates, a_closes, b_dates, b_closes):
    da = dict(zip(a_dates, a_closes, strict=True))
    db = dict(zip(b_dates, b_closes, strict=True))
    common = sorted(set(da) & set(db))
    return [da[d] for d in common], [db[d] for d in common]


def excess_return(a_closes, b_closes, n: int) -> float | None:
    """Excess return of a over b across the last n aligned periods, in points."""
    if len(a_closes) <= n or len(b_closes) <= n:
        return None
    ga = a_closes[-1] / a_closes[-1 - n]
    gb = b_closes[-1] / b_closes[-1 - n]
    return (ga - gb) * 100


def correlation(x: list[float], y: list[float]) -> float | None:
    n = min(len(x), len(y))
    if n < 5:
        return None
    x, y = x[-n:], y[-n:]
    mx, my = st.mean(x), st.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return num / (dx * dy) if dx and dy else None


def beta(x: list[float], y: list[float]) -> float | None:
    """Beta of x on y, both return series."""
    n = min(len(x), len(y))
    if n < 5:
        return None
    x, y = x[-n:], y[-n:]
    mx, my = st.mean(x), st.mean(y)
    var = sum((b - my) ** 2 for b in y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    return cov / var if var else None


def pair_ratio_z(a_closes, b_closes) -> float | None:
    """Z-score of the current a/b price ratio against its own history.

    Beyond ±1.5σ the spread is historically stretched. Useful for competing names
    that share a demand driver (e.g. two equipment vendors).
    """
    if len(a_closes) < 20 or len(b_closes) < 20:
        return None
    n = min(len(a_closes), len(b_closes))
    ratio = [a_closes[-n:][i] / b_closes[-n:][i] for i in range(n)]
    return zscore(ratio[-1], ratio)
