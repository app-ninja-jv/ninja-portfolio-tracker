"""Quickstart — runs entirely on synthetic data, no network needed.

    python examples/quickstart.py

Swap `synthetic.basket()` for `tracker.data.fetch.fetch_weekly([...])` once you
have yfinance installed and have run `tracker fetch`.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.fixtures import synthetic  # noqa: E402

from tracker.backtest import benchmarks, engine  # noqa: E402
from tracker.data import check  # noqa: E402
from tracker.render import render  # noqa: E402
from tracker.strategy import score_at  # noqa: E402
from tracker.verify import run_all  # noqa: E402


def today_of(bars):
    return datetime.strptime(bars[-1]["date"], "%Y-%m-%d").date()


def main() -> int:
    data = synthetic.basket()
    names = {t: b for t, b in data.items() if t not in ("SOXX", "QQQ")}
    sector, index = data["SOXX"], data["QQQ"]

    # 1. quality gate — quarantine, never forward-fill
    quality = {t: check(t, b, min_weeks=104, today=today_of(b)) for t, b in names.items()}
    for q in quality.values():
        print("  " + q.summary())

    # 2. score, one decision date after the last bar
    asof = "2099-01-01"
    scores = {t: s for t, s in
              ((t, score_at(t, b, asof, sector)) for t, b in names.items()) if s}
    print()
    for s in scores.values():
        print("  " + s.explain())

    # 3. back-test with benchmarks
    start = names["RAMP"][40]["date"]
    res = engine.run_allocation(names, start=start, step=2, capital=1000.0,
                                sector_bars=sector)
    bs = benchmarks.build(res, names, sector_bars=sector, index_bars=index)
    bucket = benchmarks.bucket_test(names, start, res.end, 2, sector)
    print(f"\n  return {res.ret_pct:+.2f}%   monotonic buckets: "
          f"{'yes' if bucket['monotonic'] else 'no'}")
    for k, v in bs.edges.items():
        print(f"    vs {k:<14} {v:+7.2f} pts")

    # 4. render + verify
    html = render(scores, names, quality=quality, title="Quickstart",
                  asof=names["RAMP"][-1]["date"],
                  meta={t: {"name": t, "sector": "synthetic"} for t in names})
    out = Path("build/quickstart.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)

    exits = {t: engine.price_at(b, res.end) for t, b in names.items()}
    rep = run_all(names, results=[res], exit_prices=exits, html=html)
    print("\n" + rep.summary())
    print(f"\nwrote {out}")
    return 0 if rep.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
