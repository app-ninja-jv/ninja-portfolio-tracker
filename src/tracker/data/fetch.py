"""yfinance data layer.

NOTE ON YAHOO
    Yahoo retired its official API in 2017. yfinance calls Yahoo's internal
    endpoints, which are not a public API and can be rate-limited or changed
    without notice. Consequences baked into this module:
      * never called from a web request — only by the scheduled fetch job
      * results always written to the local cache; the app reads the cache
      * bulk requests are chunked and throttled

WEEK LABELLING
    Bars are labelled by WEEK START (Monday), matching the rest of this package.
    yfinance returns weekly bars indexed by period start already, but we normalise
    defensively because an off-by-one here silently shifts every indicator. The
    golden-value test in tests/ exists specifically to catch that.

ADJUSTED VS RAW
    `close` is the raw close, for display. `adj_close` is split/dividend adjusted,
    for returns. Mixing them makes a split look like a crash.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

CHUNK = 8          # tickers per yfinance call
SLEEP = 1.2        # seconds between chunks — be polite


def _monday(d: datetime) -> str:
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def fetch_weekly(tickers: list[str], weeks: int = 104) -> dict[str, list[dict]]:
    """Weekly OHLCV per ticker, chronological, labelled by week start.

    Raises ImportError with an actionable message if yfinance is absent.
    """
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "yfinance is required for live fetching.\n"
            "  pip install 'ninja-portfolio-tracker[live]'\n"
            "Tests and offline use do not need it — see tests/fixtures/synthetic.py"
        ) from exc

    # pad the window so the quality gate has margin for holidays
    start = (datetime.utcnow() - timedelta(weeks=weeks + 6)).strftime("%Y-%m-%d")
    out: dict[str, list[dict]] = {}

    for i in range(0, len(tickers), CHUNK):
        batch = tickers[i:i + CHUNK]
        df = yf.download(
            tickers=" ".join(batch),
            start=start,
            interval="1wk",
            auto_adjust=False,
            actions=False,
            progress=False,
            group_by="ticker",
            threads=True,
        )
        for t in batch:
            try:
                sub = df[t] if len(batch) > 1 else df
            except KeyError:
                out[t] = []
                continue
            out[t] = _frame_to_bars(sub)
        if i + CHUNK < len(tickers):
            time.sleep(SLEEP)

    return {t: bars[-weeks:] for t, bars in out.items()}


def _frame_to_bars(sub) -> list[dict]:
    bars: list[dict] = []
    for idx, row in sub.iterrows():
        if row.isna().all():
            continue
        close = row.get("Close")
        adj = row.get("Adj Close", close)
        vol = row.get("Volume", 0)
        if close is None or (close != close):     # NaN check without numpy
            continue
        ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
        bars.append({
            "date": _monday(ts),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(close),
            "adj_close": float(adj if adj == adj else close),
            "volume": float(vol if vol == vol else 0.0),
        })
    bars.sort(key=lambda b: b["date"])
    # collapse any duplicate week labels, keeping the last
    dedup: dict[str, dict] = {}
    for b in bars:
        dedup[b["date"]] = b
    return [dedup[k] for k in sorted(dedup)]


def fetch_one(ticker: str, weeks: int = 104) -> list[dict]:
    return fetch_weekly([ticker], weeks).get(ticker, [])
