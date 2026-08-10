"""Data quality gate. Runs on every ingest and BLOCKS on failure.

A ticker that fails is quarantined: excluded from backtests and rendered with a
banner. It is never silently forward-filled. This is the check that would have
caught a two-month-stale vendor feed automatically instead of by hand.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from ..config import MIN_WEEKS


@dataclass
class QualityReport:
    ticker: str
    n_bars: int
    first_bar: str | None
    last_bar: str | None
    staleness_days: int | None
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def summary(self) -> str:
        state = "PASS" if self.passed else "FAIL"
        detail = "; ".join(self.failures) if self.failures else "ok"
        return f"{self.ticker:<10} {state}  {self.n_bars:>4} bars  {self.last_bar}  {detail}"


def _mondays_between(a: date, b: date) -> int:
    return ((b - a).days // 7) + 1


def check(ticker: str, bars: list[dict], *, min_weeks: int = MIN_WEEKS,
          max_staleness_days: int = 10, today: date | None = None) -> QualityReport:
    """bars: chronological list of {"date","open","high","low","close","adj_close","volume"}."""
    today = today or datetime.utcnow().date()
    rep = QualityReport(
        ticker=ticker,
        n_bars=len(bars),
        first_bar=bars[0]["date"] if bars else None,
        last_bar=bars[-1]["date"] if bars else None,
        staleness_days=None,
    )

    if not bars:
        rep.failures.append("NO_DATA")
        return rep

    # 1. history depth — hard requirement, see config.MIN_WEEKS
    if len(bars) < min_weeks:
        rep.failures.append(f"INSUFFICIENT_HISTORY ({len(bars)} < {min_weeks})")

    # 2. staleness
    last = datetime.strptime(bars[-1]["date"], "%Y-%m-%d").date()
    rep.staleness_days = (today - last).days
    if rep.staleness_days > max_staleness_days:
        rep.failures.append(f"STALE ({rep.staleness_days}d since {bars[-1]['date']})")

    # 3. OHLC sanity
    bad_ohlc = 0
    for b in bars:
        lo, hi, cl = b["low"], b["high"], b["close"]
        if hi < lo or not (lo <= cl <= hi):
            bad_ohlc += 1
    if bad_ohlc:
        rep.failures.append(f"OHLC_VIOLATION ({bad_ohlc} rows)")

    # 4. volume
    if any(b["volume"] <= 0 for b in bars):
        rep.failures.append("NON_POSITIVE_VOLUME")

    # 5. duplicates
    dates = [b["date"] for b in bars]
    if len(dates) != len(set(dates)):
        rep.failures.append("DUPLICATE_DATES")

    # 6. ordering
    if dates != sorted(dates):
        rep.failures.append("NOT_CHRONOLOGICAL")

    # 7. gaps — every Monday in range should be present
    d0 = datetime.strptime(dates[0], "%Y-%m-%d").date()
    d1 = datetime.strptime(dates[-1], "%Y-%m-%d").date()
    expected = _mondays_between(d0, d1)
    missing = expected - len(dates)
    if missing > 0:
        rep.warnings.append(f"{missing} missing week(s)")
        if missing > expected * 0.02:
            rep.failures.append(f"GAPS ({missing} missing weeks)")

    # 8. split artefact detector — a >40% single-week move with no volume spike is
    #    usually an unadjusted split rather than a real move
    for i in range(1, len(bars)):
        chg = bars[i]["close"] / bars[i - 1]["close"] - 1
        vr = bars[i]["volume"] / max(bars[i - 1]["volume"], 1)
        if abs(chg) > 0.40 and vr < 1.5:
            rep.warnings.append(
                f"possible unadjusted split at {bars[i]['date']} "
                f"({chg*100:+.0f}% on {vr:.1f}x volume)"
            )

    return rep


def gate(reports: dict[str, QualityReport]) -> tuple[list[str], list[str]]:
    """Split tickers into (usable, quarantined)."""
    ok = [t for t, r in reports.items() if r.passed]
    bad = [t for t, r in reports.items() if not r.passed]
    return sorted(ok), sorted(bad)
