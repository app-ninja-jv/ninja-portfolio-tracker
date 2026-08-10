"""Walk-forward backtest.

Two modes:
  allocation  — weights across a basket, renormalised to portfolio value each cycle
  entry_exit  — per stock, +entry_size on BUY, -exit_size on SELL, nothing otherwise

Both charge cost_bps on traded notional and log every event, so the ledger can be
rebuilt independently by tracker.verify.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import StrategyConfig
from ..strategy.scoring import score_at


@dataclass
class Event:
    date: str
    ticker: str
    verdict: str
    score: int
    price: float
    action: str
    amount: float
    shares_after: float
    value_after: float


@dataclass
class Result:
    mode: str
    start: str
    end: str
    capital: float
    end_value: float
    contributed: float
    withdrawn: float
    cost: float
    events: list[Event] = field(default_factory=list)
    equity_curve: list[tuple[str, float]] = field(default_factory=list)
    per_ticker: dict = field(default_factory=dict)
    regime: dict = field(default_factory=dict)

    @property
    def pl(self) -> float:
        return self.end_value + self.withdrawn - self.contributed

    @property
    def ret_pct(self) -> float:
        return self.pl / self.contributed * 100 if self.contributed else 0.0


def price_at(bars: list[dict], d: str) -> float | None:
    """Last close on or before d. Forward-fill for continuity only, never for returns."""
    prior = [b for b in bars if b["date"] <= d]
    return prior[-1]["close"] if prior else None


def decision_dates(bars_by_ticker: dict[str, list[dict]], start: str, step: int) -> list[str]:
    all_d = sorted({b["date"] for bs in bars_by_ticker.values() for b in bs})
    return [d for d in all_d if d >= start][::step]


# --------------------------------------------------------------- allocation mode
def run_allocation(bars_by_ticker: dict[str, list[dict]], *, start: str, step: int = 2,
                   capital: float = 1000.0, sector_bars: list[dict] | None = None,
                   cfg: StrategyConfig | None = None, end: str | None = None) -> Result:
    cfg = cfg or StrategyConfig()
    dates = decision_dates(bars_by_ticker, start, step)
    if end:
        dates = [d for d in dates if d <= end]
    shares: dict[str, float] = {}
    cost_total = 0.0
    events: list[Event] = []
    curve: list[tuple[str, float]] = []

    for i, d in enumerate(dates):
        scores = {t: score_at(t, bs, d, sector_bars, cfg)
                  for t, bs in bars_by_ticker.items()}
        scores = {t: s for t, s in scores.items() if s}
        if not scores:
            continue
        px = {t: price_at(bars_by_ticker[t], d) for t in scores}
        px = {t: p for t, p in px.items() if p}
        if not px:
            continue

        pv = capital if i == 0 else sum(shares.get(t, 0.0) * px[t] for t in px)
        curve.append((d, pv))

        raw = {t: cfg.weights[scores[t].verdict] for t in px}
        k = pv / sum(raw.values())
        target = {t: raw[t] * k for t in px}
        traded = sum(abs(target[t] - shares.get(t, 0.0) * px[t]) for t in px)
        cost = traded * cfg.cost_bps / 10_000
        cost_total += cost
        k2 = (pv - cost) / sum(raw.values())
        target = {t: raw[t] * k2 for t in px}

        for t in px:
            before = shares.get(t, 0.0) * px[t]
            shares[t] = target[t] / px[t]
            events.append(Event(d, t, scores[t].verdict, scores[t].total, px[t],
                                "REBALANCE", target[t] - before,
                                shares[t], target[t]))

    last = dates[-1] if dates else start
    end_value = sum(shares.get(t, 0.0) * (price_at(bs, last) or 0.0)
                    for t, bs in bars_by_ticker.items())
    curve.append((last, end_value))

    return Result(mode="allocation", start=start, end=last, capital=capital,
                  end_value=end_value, contributed=capital, withdrawn=0.0,
                  cost=cost_total, events=events, equity_curve=curve,
                  per_ticker={t: shares.get(t, 0.0) for t in bars_by_ticker})


# --------------------------------------------------------------- entry/exit mode
def run_entry_exit(bars_by_ticker: dict[str, list[dict]], *, start: str, step: int = 2,
                   seed: float = 100.0, sector_bars: list[dict] | None = None,
                   cfg: StrategyConfig | None = None, end: str | None = None) -> Result:
    cfg = cfg or StrategyConfig()
    dates = decision_dates(bars_by_ticker, start, step)
    if end:
        dates = [d for d in dates if d <= end]

    events: list[Event] = []
    per: dict[str, dict] = {}
    tot_contrib = tot_withdraw = tot_cost = 0.0

    for t, bs in bars_by_ticker.items():
        p0 = price_at(bs, start)
        if not p0:
            continue
        sh = seed / p0
        c0 = seed * cfg.cost_bps / 10_000
        contrib, withdrawn, cost = seed + c0, 0.0, c0
        events.append(Event(start, t, "SEED", 0, p0, "SEED", seed, sh, seed))

        for d in dates[1:]:
            s = score_at(t, bs, d, sector_bars, cfg)
            if not s:
                continue
            p = price_at(bs, d)
            if not p:
                continue
            val = sh * p
            action, amt = "—", 0.0
            if s.verdict == "BUY":
                amt = cfg.entry_size
                sh += amt / p
                c = amt * cfg.cost_bps / 10_000
                contrib += amt + c
                cost += c
                action = f"ENTRY +{amt:.2f}"
            elif s.verdict == "SELL" or (cfg.trim_acts and s.verdict == "TRIM"):
                amt = min(cfg.exit_size, val)
                if amt > 0:
                    sh -= amt / p
                    c = amt * cfg.cost_bps / 10_000
                    withdrawn += amt - c
                    cost += c
                    action = f"EXIT -{amt:.2f}"
            events.append(Event(d, t, s.verdict, s.total, p, action, amt, sh, sh * p))

        last = dates[-1] if dates else start
        pe = price_at(bs, last) or p0
        final = sh * pe
        base = seed / p0 * pe
        per[t] = {
            "entry_px": p0, "exit_px": pe, "final": final, "shares": sh,
            "contributed": contrib, "withdrawn": withdrawn, "cost": cost,
            "pl": final + withdrawn - contrib,
            "ret_pct": (final + withdrawn - contrib) / contrib * 100,
            "base_final": base, "base_ret_pct": (base / seed - 1) * 100,
            "n_entry": sum(1 for e in events if e.ticker == t and e.action.startswith("ENTRY")),
            "n_exit": sum(1 for e in events if e.ticker == t and e.action.startswith("EXIT")),
        }
        tot_contrib += contrib
        tot_withdraw += withdrawn
        tot_cost += cost

    last = dates[-1] if dates else start
    end_value = sum(v["final"] for v in per.values())
    return Result(mode="entry_exit", start=start, end=last,
                  capital=seed * len(per), end_value=end_value,
                  contributed=tot_contrib, withdrawn=tot_withdraw, cost=tot_cost,
                  events=events, per_ticker=per)
