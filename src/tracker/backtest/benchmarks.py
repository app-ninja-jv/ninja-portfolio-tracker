"""Benchmarks and per-ticker reporting.

Five comparators, all on identical capital over an identical window:
  1. buy & hold, equal weight            the primary baseline
  2. buy & hold, rule-weighted once      isolates whether RE-deciding adds value
  3. sector ETF
  4. index
  5. DCA-matched                         same cash, same dates, 50/50, no exits
                                         isolates signal value from capital schedule

Plus the bucket monotonicity test: mean forward return by verdict. Real skill gives
BUY > HOLD > TRIM > SELL. Non-monotonic buckets are often more informative than the
headline return.
"""
from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field

from ..config import StrategyConfig
from ..strategy.scoring import score_at
from .engine import Result, decision_dates, price_at


@dataclass
class BenchmarkSet:
    equal_weight: float
    rule_once: float | None
    sector: float | None
    index: float | None
    dca_matched: float | None
    edges: dict[str, float] = field(default_factory=dict)


def simple_return(bars: list[dict], start: str, end: str) -> float | None:
    a, b = price_at(bars, start), price_at(bars, end)
    return (b / a - 1) * 100 if a and b else None


def equal_weight(bars_by_ticker: dict[str, list[dict]], start: str, end: str,
                 capital: float) -> float:
    n = len(bars_by_ticker)
    per = capital / n
    total = 0.0
    for bs in bars_by_ticker.values():
        p0, p1 = price_at(bs, start), price_at(bs, end)
        if p0 and p1:
            total += per / p0 * p1
    return (total / capital - 1) * 100


def rule_weighted_once(bars_by_ticker, start, end, capital, sector_bars=None,
                       cfg: StrategyConfig | None = None) -> float | None:
    cfg = cfg or StrategyConfig()
    scores = {t: score_at(t, bs, start, sector_bars, cfg)
              for t, bs in bars_by_ticker.items()}
    scores = {t: s for t, s in scores.items() if s}
    if not scores:
        return None
    raw = {t: cfg.weights[s.verdict] for t, s in scores.items()}
    k = capital / sum(raw.values())
    total = 0.0
    for t, w in raw.items():
        p0, p1 = price_at(bars_by_ticker[t], start), price_at(bars_by_ticker[t], end)
        if p0 and p1:
            total += (w * k) / p0 * p1
    return (total / capital - 1) * 100


def dca_matched(result: Result, bars_by_ticker: dict[str, list[dict]],
                cost_bps: float = 10.0) -> float | None:
    """Same cash on the same dates, split evenly, no exits."""
    flows: dict[str, float] = {}
    for e in result.events:
        if e.action == "SEED" or e.action.startswith("ENTRY"):
            flows[e.date] = flows.get(e.date, 0.0) + e.amount
    if not flows:
        return None
    tickers = list(bars_by_ticker)
    shares = {t: 0.0 for t in tickers}
    contributed = 0.0
    for d, amt in sorted(flows.items()):
        per = amt / len(tickers)
        for t in tickers:
            p = price_at(bars_by_ticker[t], d)
            if not p:
                continue
            shares[t] += per / p
            c = per * cost_bps / 10_000
            contributed += per + c
    final = sum(shares[t] * (price_at(bars_by_ticker[t], result.end) or 0.0) for t in tickers)
    return (final - contributed) / contributed * 100 if contributed else None


def build(result: Result, bars_by_ticker, *, sector_bars=None, index_bars=None,
          cfg: StrategyConfig | None = None) -> BenchmarkSet:
    cfg = cfg or StrategyConfig()
    eq = equal_weight(bars_by_ticker, result.start, result.end, result.capital)
    once = rule_weighted_once(bars_by_ticker, result.start, result.end,
                              result.capital, sector_bars, cfg)
    sec = simple_return(sector_bars, result.start, result.end) if sector_bars else None
    idx = simple_return(index_bars, result.start, result.end) if index_bars else None
    dca = dca_matched(result, bars_by_ticker, cfg.cost_bps)

    bs = BenchmarkSet(eq, once, sec, idx, dca)
    r = result.ret_pct
    bs.edges = {k: r - v for k, v in
                {"equal_weight": eq, "rule_once": once, "sector": sec,
                 "index": idx, "dca_matched": dca}.items() if v is not None}
    return bs


def bucket_test(bars_by_ticker, start: str, end: str, step: int = 2,
                sector_bars=None, cfg: StrategyConfig | None = None) -> dict:
    """Mean forward return by verdict, over all decision dates. Monotonicity = skill."""
    cfg = cfg or StrategyConfig()
    dates = [d for d in decision_dates(bars_by_ticker, start, step) if d <= end]
    buckets: dict[str, list[float]] = {"BUY": [], "HOLD": [], "TRIM": [], "SELL": []}
    for i, d in enumerate(dates[:-1]):
        nxt = dates[i + 1]
        for t, bs in bars_by_ticker.items():
            s = score_at(t, bs, d, sector_bars, cfg)
            if not s:
                continue
            p0, p1 = price_at(bs, d), price_at(bs, nxt)
            if p0 and p1:
                buckets[s.verdict].append((p1 / p0 - 1) * 100)
    out = {}
    allr = [x for v in buckets.values() for x in v]
    for k, v in buckets.items():
        out[k] = {"n": len(v), "mean": st.mean(v) if v else None}
    out["ALL"] = {"n": len(allr), "mean": st.mean(allr) if allr else None}
    order = [out[k]["mean"] for k in ("BUY", "HOLD", "TRIM", "SELL")
             if out[k]["mean"] is not None]
    out["monotonic"] = order == sorted(order, reverse=True) and len(order) >= 3
    return out


def per_ticker_distribution(results: dict[str, dict]) -> dict:
    """Aggregate per-ticker edges into a distribution. Never report a single number."""
    edges = [v["ret_pct"] - v["base_ret_pct"] for v in results.values()
             if "base_ret_pct" in v]
    if not edges:
        return {}
    edges.sort()
    n = len(edges)
    return {
        "n": n,
        "beat_hold": sum(1 for e in edges if e > 0),
        "beat_hold_pct": sum(1 for e in edges if e > 0) / n * 100,
        "median": st.median(edges),
        "q1": edges[n // 4],
        "q3": edges[(3 * n) // 4],
        "best": edges[-1],
        "worst": edges[0],
    }


def regime(index_bars: list[dict], start: str, end: str,
           bars_by_ticker: dict[str, list[dict]]) -> dict:
    """Tag the window. A result without its regime is not interpretable."""
    idx = simple_return(index_bars, start, end) if index_bars else None
    rets = [simple_return(bs, start, end) for bs in bars_by_ticker.values()]
    rets = [r for r in rets if r is not None]
    pos = sum(1 for r in rets if r > 0) / len(rets) * 100 if rets else None
    label = "unknown"
    if idx is not None:
        label = "bull" if idx > 8 else ("bear" if idx < -8 else "range")
    return {"window": [start, end], "index_return": idx,
            "pct_names_positive": pos, "label": label, "n_names": len(rets)}
