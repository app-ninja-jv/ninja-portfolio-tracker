"""Command line interface.

    tracker fetch   --tickers NVDA,AMD --weeks 104
    tracker doctor  --golden tests/fixtures/golden_2026_07_31.json
    tracker score   --tickers NVDA,AMD
    tracker report  --out build/index.html
    tracker backtest --start 2026-02-02 --mode allocation
    tracker verify  --report build/index.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .backtest import benchmarks, engine
from .config import DEFAULT, StrategyConfig
from .data import Cache, check, gate
from .render import render
from .strategy import score_at
from .verify import run_all


def _tickers(arg: str | None) -> list[str]:
    if not arg:
        return []
    return [t.strip().upper() for t in arg.split(",") if t.strip()]


def _load(cache: Cache, tickers: list[str], weeks: int) -> dict[str, list[dict]]:
    return {t: cache.get_bars(t, weeks) for t in (tickers or cache.tickers())}


# ------------------------------------------------------------------ fetch
def cmd_fetch(a) -> int:
    from .data.fetch import fetch_weekly
    tickers = _tickers(a.tickers)
    if not tickers:
        print("--tickers is required for fetch", file=sys.stderr)
        return 2
    extra = [DEFAULT.data.sector_etf, *DEFAULT.data.benchmarks]
    want = list(dict.fromkeys(tickers + extra))
    print(f"fetching {len(want)} symbols, {a.weeks} weeks ...")
    data = fetch_weekly(want, a.weeks)

    reports = {}
    with Cache(a.cache) as cache:
        for t, bars in data.items():
            rep = check(t, bars, min_weeks=a.min_weeks,
                        max_staleness_days=DEFAULT.data.max_staleness_days)
            reports[t] = rep
            if not a.dry_run:
                cache.put_bars(t, bars)
                cache.put_quality(rep)
            print("  " + rep.summary())
        if not a.dry_run:
            print("cache:", cache.stats())

    ok, bad = gate(reports)
    print(f"\n{len(ok)} passed, {len(bad)} quarantined" + (f": {bad}" if bad else ""))
    return 1 if bad and a.strict else 0


# ------------------------------------------------------------------ doctor
def cmd_doctor(a) -> int:
    """Pre-push gate: shape checks plus golden-value cross-check."""
    with Cache(a.cache) as cache:
        bars = _load(cache, _tickers(a.tickers), a.weeks)
    bars = {t: b for t, b in bars.items() if b}
    if not bars:
        print("no cached data — run `tracker fetch` first", file=sys.stderr)
        return 2

    reports = {t: check(t, b, min_weeks=a.min_weeks) for t, b in bars.items()}
    for r in reports.values():
        print("  " + r.summary())

    rep = run_all(bars, golden=a.golden if a.golden and Path(a.golden).exists() else None)
    print("\n" + rep.summary())
    ok, bad = gate(reports)
    return 0 if rep.clean and not bad else 1


# ------------------------------------------------------------------ score
def cmd_score(a) -> int:
    cfg = StrategyConfig()
    with Cache(a.cache) as cache:
        bars = _load(cache, _tickers(a.tickers), a.weeks)
        sector = cache.get_bars(DEFAULT.data.sector_etf, a.weeks)
    asof = a.asof or max(b[-1]["date"] for b in bars.values() if b)
    # asof must be strictly after the newest decision bar
    nxt = asof
    for t, b in sorted(bars.items()):
        if t in (DEFAULT.data.sector_etf, *DEFAULT.data.benchmarks) or not b:
            continue
        s = score_at(t, b, nxt, sector, cfg)
        print(s.explain() if s else f"{t}: insufficient history")
    return 0


# ------------------------------------------------------------------ report
def cmd_report(a) -> int:
    cfg = StrategyConfig()
    skip = {DEFAULT.data.sector_etf, *DEFAULT.data.benchmarks}
    with Cache(a.cache) as cache:
        allbars = _load(cache, _tickers(a.tickers), a.weeks)
        sector = cache.get_bars(DEFAULT.data.sector_etf, a.weeks)
    bars = {t: b for t, b in allbars.items() if b and t not in skip}
    if not bars:
        print("no cached data — run `tracker fetch` first", file=sys.stderr)
        return 2

    quality = {t: check(t, b, min_weeks=a.min_weeks) for t, b in bars.items()}
    asof = max(b[-1]["date"] for b in bars.values())
    scores = {}
    for t, b in bars.items():
        s = score_at(t, b, _day_after(asof), sector, cfg)
        if s:
            scores[t] = s

    html = render(scores, bars, quality=quality, asof=asof,
                  title=a.title, meta=_meta_stub(bars))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"wrote {out}  ({len(html):,} chars, {len(scores)} tickers)")

    rep = run_all(bars, html=html)
    print(rep.summary())
    return 0 if rep.clean else 1


def _day_after(d: str) -> str:
    from datetime import datetime, timedelta
    return (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")


def _meta_stub(bars: dict) -> dict:
    return {t: {"name": "", "sector": ""} for t in bars}


# ------------------------------------------------------------------ backtest
def cmd_backtest(a) -> int:
    cfg = StrategyConfig()
    skip = {DEFAULT.data.sector_etf, *DEFAULT.data.benchmarks}
    with Cache(a.cache) as cache:
        allbars = _load(cache, _tickers(a.tickers), a.weeks)
        sector = cache.get_bars(DEFAULT.data.sector_etf, a.weeks)
        index = cache.get_bars(DEFAULT.data.benchmarks[-1], a.weeks)
    bars = {t: b for t, b in allbars.items() if b and t not in skip}
    if not bars:
        print("no cached data", file=sys.stderr)
        return 2

    start = a.start or sorted({b["date"] for bs in bars.values() for b in bs})[26]
    if a.mode == "allocation":
        res = engine.run_allocation(bars, start=start, step=a.step,
                                    capital=a.capital, sector_bars=sector, cfg=cfg)
    else:
        res = engine.run_entry_exit(bars, start=start, step=a.step,
                                    seed=a.capital / max(len(bars), 1),
                                    sector_bars=sector, cfg=cfg)

    bs = benchmarks.build(res, bars, sector_bars=sector, index_bars=index, cfg=cfg)
    bk = benchmarks.bucket_test(bars, start, res.end, a.step, sector, cfg)
    rg = benchmarks.regime(index, start, res.end, bars)

    print(f"\n{res.mode}  {res.start} -> {res.end}  regime={rg['label']}")
    print(f"  capital {res.contributed:>12,.2f}")
    print(f"  end     {res.end_value:>12,.2f}   P/L {res.pl:>+11,.2f}   {res.ret_pct:>+7.2f}%")
    print(f"  cost    {res.cost:>12,.2f}")
    print("\n  benchmarks (edge in points)")
    for k, v in bs.edges.items():
        print(f"    {k:<14} {v:>+7.2f}")
    print("\n  bucket test  (monotonic = " + ("YES" if bk["monotonic"] else "NO") + ")")
    for k in ("BUY", "HOLD", "TRIM", "SELL", "ALL"):
        m = bk[k]["mean"]
        print(f"    {k:<6} n={bk[k]['n']:<4} mean {m:>+7.2f}%" if m is not None
              else f"    {k:<6} n=0")

    if res.mode == "entry_exit":
        dist = benchmarks.per_ticker_distribution(res.per_ticker)
        if dist:
            print(f"\n  per-ticker edge vs own hold: {dist['beat_hold']}/{dist['n']} beat "
                  f"({dist['beat_hold_pct']:.0f}%), median {dist['median']:+.2f}pt, "
                  f"IQR {dist['q1']:+.2f} to {dist['q3']:+.2f}")

    if a.json_out:
        Path(a.json_out).write_text(json.dumps({
            "mode": res.mode, "start": res.start, "end": res.end,
            "end_value": res.end_value, "pl": res.pl, "ret_pct": res.ret_pct,
            "cost": res.cost, "benchmarks": bs.edges, "buckets": bk, "regime": rg,
            "per_ticker": res.per_ticker,
        }, indent=1, default=str))
        print(f"\nwrote {a.json_out}")
    return 0


# ------------------------------------------------------------------ verify
def cmd_verify(a) -> int:
    # Benchmarks (sector ETF, index) are cached for relative-strength maths but are
    # deliberately NOT portfolio holdings, so `report` excludes them. `verify` must
    # apply the same filter or it demands tickers the render was never meant to show.
    skip = {DEFAULT.data.sector_etf, *DEFAULT.data.benchmarks}
    with Cache(a.cache) as cache:
        allbars = _load(cache, _tickers(a.tickers), a.weeks)
    bars = {t: b for t, b in allbars.items() if b and t not in skip}
    html = Path(a.report).read_text() if a.report and Path(a.report).exists() else None
    rep = run_all(bars, html=html,
                  golden=a.golden if a.golden and Path(a.golden).exists() else None)
    print(rep.summary())
    return 0 if rep.clean else 1


# ------------------------------------------------------------------ parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tracker", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"equity-tracker {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--tickers")
        sp.add_argument("--cache", default=str(DEFAULT.data.cache_path))
        sp.add_argument("--weeks", type=int, default=DEFAULT.data.weeks)
        sp.add_argument("--min-weeks", type=int, default=DEFAULT.data.weeks)

    f = sub.add_parser("fetch", help="pull weekly bars into the cache")
    common(f)
    f.add_argument("--dry-run", action="store_true")
    f.add_argument("--strict", action="store_true", help="exit 1 if any ticker fails the gate")
    f.set_defaults(fn=cmd_fetch)

    d = sub.add_parser("doctor", help="pre-push gate: shape + golden-value checks")
    common(d)
    d.add_argument("--golden", default="tests/fixtures/golden_2026_07_31.json")
    d.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("score", help="print current scores")
    common(s)
    s.add_argument("--asof")
    s.set_defaults(fn=cmd_score)

    r = sub.add_parser("report", help="render the HTML dashboard")
    common(r)
    r.add_argument("--out", default="build/index.html")
    r.add_argument("--title", default="Equity Tracker")
    r.set_defaults(fn=cmd_report)

    b = sub.add_parser("backtest", help="walk-forward backtest with benchmarks")
    common(b)
    b.add_argument("--start")
    b.add_argument("--step", type=int, default=2)
    b.add_argument("--capital", type=float, default=1000.0)
    b.add_argument("--mode", choices=("allocation", "entry_exit"), default="allocation")
    b.add_argument("--json-out")
    b.set_defaults(fn=cmd_backtest)

    v = sub.add_parser("verify", help="run the verification harness")
    common(v)
    v.add_argument("--report")
    v.add_argument("--golden")
    v.set_defaults(fn=cmd_verify)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
