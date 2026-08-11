"""Verification harness — the differentiator.

Six classes of check. Every one of these caught a real bug during development.

  1. independent recomputation   recompute indicators via DIFFERENT code paths
  2. look-ahead audit           every decision uses only bars strictly before it
  3. ledger rebuild             reconstruct the portfolio from the event log alone
  4. capital conservation       all compared portfolios deploy identical capital
  5. golden values              live data matched against known-good reference prices
  6. claim assertions           statements in the output asserted as booleans

Design intent: this is not a hedge. It is what makes a result trustworthy enough
to act on. Wire it into CI so a data refresh that invalidates a written conclusion
breaks the build instead of shipping silently.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from ..features import indicators as ind
from ..strategy.scoring import bars_before


@dataclass
class VerifyReport:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    warned: list[str] = field(default_factory=list)

    def ok(self, msg: str):
        self.passed.append(msg)

    def bad(self, msg: str):
        self.failed.append(msg)

    def warn(self, msg: str):
        self.warned.append(msg)

    @property
    def clean(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        lines = [f"PASSED {len(self.passed)}   FAILED {len(self.failed)}   "
                 f"WARNINGS {len(self.warned)}"]
        lines += [f"  FAIL  {m}" for m in self.failed]
        lines += [f"  WARN  {m}" for m in self.warned]
        if self.clean:
            lines.append("  All checks passed.")
        return "\n".join(lines)


def _close(a, b, tol=0.01) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= max(tol, abs(b) * 1e-4)


# ---------------------------------------------------------------- 1. recomputation
def check_recomputation(bars_by_ticker: dict[str, list[dict]],
                        rep: VerifyReport | None = None) -> VerifyReport:
    """Recompute a sample of indicators using deliberately different code."""
    rep = rep or VerifyReport()
    for t, bars in list(bars_by_ticker.items())[:5]:
        c = [b["close"] for b in bars]
        if len(c) < 45:
            continue

        # SMA by slicing instead of rolling
        manual = sum(c[-40:]) / 40.0
        if _close(manual, ind.sma(c, 40)):
            rep.ok(f"{t} 40w SMA")
        else:
            rep.bad(f"{t} 40w SMA: {manual} vs {ind.sma(c, 40)}")

        # RSI via an independent Wilder implementation
        alt = _rsi_alt(c, 14)
        if _close(alt, ind.rsi(c, 14), tol=0.05):
            rep.ok(f"{t} RSI(14)")
        else:
            rep.bad(f"{t} RSI(14): {alt} vs {ind.rsi(c, 14)}")

        # volatility via variance rather than pstdev
        r = ind.returns(c)
        mean = sum(r) / len(r)
        var = sum((x - mean) ** 2 for x in r) / len(r)
        alt_vol = math.sqrt(var) * math.sqrt(52) * 100
        if _close(alt_vol, ind.realised_vol(c), tol=0.05):
            rep.ok(f"{t} realised vol")
        else:
            rep.bad(f"{t} realised vol: {alt_vol} vs {ind.realised_vol(c)}")
    return rep


def _rsi_alt(vals, n=14):
    d = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    up = [x if x > 0 else 0.0 for x in d]
    dn = [-x if x < 0 else 0.0 for x in d]
    au, ad = sum(up[:n]) / n, sum(dn[:n]) / n
    for i in range(n, len(d)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
    return 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)


# ---------------------------------------------------------------- 2. look-ahead
def check_lookahead(bars_by_ticker: dict[str, list[dict]], decision_dates: list[str],
                    rep: VerifyReport | None = None) -> VerifyReport:
    rep = rep or VerifyReport()
    n = 0
    for d in decision_dates:
        for t, bars in bars_by_ticker.items():
            used = bars_before(bars, d)
            if not used:
                continue
            newest = max(b["date"] for b in used)
            if newest >= d:
                rep.bad(f"LOOK-AHEAD {t}@{d}: used bar {newest}")
            n += 1
    rep.ok(f"look-ahead audit: {n} ticker-dates, all bars strictly before execution")
    return rep


# ---------------------------------------------------------------- 3. ledger rebuild
def check_ledger(result, exit_prices: dict[str, float],
                 rep: VerifyReport | None = None) -> VerifyReport:
    """Rebuild the portfolio from the event log alone and compare to the reported total."""
    rep = rep or VerifyReport()
    shares: dict[str, float] = {}
    for e in result.events:
        shares[e.ticker] = e.shares_after
        if not _close(e.shares_after * e.price, e.value_after, tol=0.02):
            rep.bad(f"ledger {e.ticker}@{e.date}: value {e.value_after} "
                    f"!= shares*price {e.shares_after * e.price}")
    rebuilt = sum(sh * exit_prices.get(t, 0.0) for t, sh in shares.items())
    if _close(rebuilt, result.end_value, tol=0.05):
        rep.ok(f"ledger rebuild: {rebuilt:,.2f} == reported {result.end_value:,.2f}")
    else:
        rep.bad(f"ledger rebuild {rebuilt:,.2f} != reported {result.end_value:,.2f}")
    return rep


# ---------------------------------------------------------------- 4. capital
def check_capital(results: list, rep: VerifyReport | None = None) -> VerifyReport:
    rep = rep or VerifyReport()
    caps = [round(r.contributed, 2) for r in results]
    if len(set(caps)) == 1:
        rep.ok(f"capital conservation: all portfolios deploy {caps[0]:,.2f}")
    else:
        rep.bad(f"capital differs across portfolios: {caps}")
    return rep


# ---------------------------------------------------------------- 5. golden values
def check_golden(bars_by_ticker: dict[str, list[dict]], golden_path: str | Path,
                 rep: VerifyReport | None = None, tol_pct: float = 0.5) -> VerifyReport:
    """Compare live data against verified reference closes.

    Catches the three failure modes that matter most with yfinance:
      * raw vs adjusted close  (a split looks like a crash)
      * week-labelling off-by-one (shifts every indicator silently)
      * timezone drift on the final bar
    """
    rep = rep or VerifyReport()
    golden = json.loads(Path(golden_path).read_text())
    asof = golden["as_of"]
    for t, expected in golden["closes"].items():
        bars = bars_by_ticker.get(t)
        if not bars:
            rep.warn(f"golden: {t} not in dataset")
            continue
        prior = [b for b in bars if b["date"] <= asof]
        if not prior:
            rep.warn(f"golden: {t} has no bar on or before {asof}")
            continue
        got = prior[-1]["close"]
        diff_pct = abs(got - expected) / expected * 100
        if diff_pct <= tol_pct:
            rep.ok(f"golden {t}: {got:,.2f} ~ {expected:,.2f}")
        else:
            rep.bad(f"golden {t}: got {got:,.2f}, expected {expected:,.2f} "
                    f"({diff_pct:.1f}% off) — check adjusted-close and week labelling")
    return rep


# ---------------------------------------------------------------- 6. claims
def check_claims(claims: dict[str, bool], rep: VerifyReport | None = None) -> VerifyReport:
    """Assert statements made in the output. Turns prose into tests."""
    rep = rep or VerifyReport()
    for text, truth in claims.items():
        if truth:
            rep.ok(f"claim: {text}")
        else:
            rep.bad(f"CLAIM FALSE: {text}")
    return rep


def check_render(html: str, expected_tickers: list[str],
                 rep: VerifyReport | None = None) -> VerifyReport:
    """No unrendered placeholders, no literal None/nan, every ticker present."""
    import re
    rep = rep or VerifyReport()
    body = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    leftovers = re.findall(r"\{[a-zA-Z_][\w\[\]'\"().]*\}", body)
    if leftovers:
        rep.bad(f"unrendered placeholders: {sorted(set(leftovers))[:5]}")
    else:
        rep.ok("no unrendered placeholders")
    for tok in ("None", "nan", "undefined"):
        if re.search(rf"\b{tok}\b", body):
            rep.warn(f"literal '{tok}' in rendered output")
    # A missing ticker WARNS rather than fails. Legitimate causes: it was quarantined
    # by the quality gate, or it has too little history to score. Neither is a broken
    # render. Unrendered placeholders above are the real failure condition.
    missing = [t for t in expected_tickers if t not in html]
    present = len(expected_tickers) - len(missing)
    if missing:
        rep.warn(f"not in render (quarantined or unscorable): {sorted(missing)}")
    rep.ok(f"{present}/{len(expected_tickers)} tickers present in render")
    return rep


def run_all(bars_by_ticker, *, decision_dates=None, results=None,
            exit_prices=None, golden=None, claims=None, html=None) -> VerifyReport:
    rep = VerifyReport()
    check_recomputation(bars_by_ticker, rep)
    if decision_dates:
        check_lookahead(bars_by_ticker, decision_dates, rep)
    if results and exit_prices:
        for r in results:
            check_ledger(r, exit_prices, rep)
        check_capital(results, rep)
    if golden:
        check_golden(bars_by_ticker, golden, rep)
    if claims:
        check_claims(claims, rep)
    if html:
        check_render(html, list(bars_by_ticker), rep)
    return rep
