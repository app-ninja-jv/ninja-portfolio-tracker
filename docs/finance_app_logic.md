# Logic specification

104-week data layer, 14-day decision cadence, 14-week forecast horizon. Benchmarked against the
scoring strategy and against buy-and-hold.

Unbuilt components are in [`../ROADMAP.md`](../ROADMAP.md). Companion:
[`analysis_deep.md`](analysis_deep.md).

---

## Three horizons

| Horizon | Value | Purpose |
|---|---|---|
| History | 104 weeks | Feeds every indicator and every distribution |
| Decision cadence | 14 days (2 weekly bars) | How often the strategy re-scores and can act |
| Forecast horizon | 14 weeks | What the model predicts forward |

104 weeks is the smallest window making every indicator computable without silent degradation:

| Indicator | Bars needed | Observations at 104 weeks |
|---|---|---|
| 40-week MA | 40 | 64 |
| MACD(12,26,9) | 35 | 69 |
| 26-week MA | 26 | 78 |
| RSI(14) | 15 | 89 |
| 13-week relative strength | 14 | 90 |

At 52 weeks the 40-week MA yields 13 observations, making its z-score meaningless, and a January
start leaves 27 bars where MACD needs 35. Enforced as a hard precondition.

---

## Architecture

```
yfinance ──► cache (SQLite) ──► features ──► strategy ──► backtest ──► render
```

The render layer never calls yfinance. A scheduled job owns all external fetching.

---

## Layer 1 — Data

`yfinance`. US tickers plain (`NVDA`), India by suffix (`RELIANCE.NS`, `500325.BO`). Weekly bars are
the unit of record; daily bars are optional context and are not used by the strategy.

```sql
CREATE TABLE bars (
  ticker      TEXT NOT NULL,
  exchange    TEXT NOT NULL,          -- US | NSE | BSE
  currency    TEXT NOT NULL,
  week_start  DATE NOT NULL,          -- Monday of the bar
  open REAL, high REAL, low REAL, close REAL, adj_close REAL,
  volume      INTEGER NOT NULL,
  fetched_at  TIMESTAMP NOT NULL,
  PRIMARY KEY (ticker, week_start)
);
CREATE TABLE data_quality (
  ticker TEXT, checked_at TIMESTAMP, n_bars INTEGER,
  first_bar DATE, last_bar DATE, staleness_days INTEGER,
  gaps INTEGER, ohlc_violations INTEGER, passed BOOLEAN
);
```

Adjusted closes for returns, raw closes for display. Mixing them renders a split as a −50% week.

### Quality gate

Runs on every ingest and blocks on failure.

| Check | Rule |
|---|---|
| Bar count | ≥ 104, else `INSUFFICIENT_HISTORY` |
| Staleness | `last_bar` within 10 days, else `STALE` |
| OHLC sanity | `low ≤ close ≤ high` and `high ≥ low` on every row |
| Volume | strictly positive |
| Gaps | no missing Mondays inside the range |
| Split detector | >40% move on <1.5× volume flags unadjusted data |

A failing ticker renders with a banner and is excluded from backtests. Forward-fill is permitted for
display continuity only: a missing bar produces a `NULL` return, never zero.

---

## Layer 2 — Features

Keyed `(ticker, week_start)`. Every feature must be computable from bars strictly at or before
`week_start`.

| Group | Features |
|---|---|
| Trend | SMA 10/26/40w; price vs each; golden/death cross; weeks above 40w |
| Momentum | RSI(14); MACD(12,26,9) line/signal/histogram; ROC 4/13/26/52w |
| Extension | % above 26w and 40w MA; z-score of each vs own 104w history; Bollinger %B(20,2) |
| Volume | volume z-score vs 104w; up/down volume ratio 8w; OBV; dollar-volume trend |
| Volatility | realised vol 13w/52w annualised and percentile; ATR(14) as % of price |
| Relative | excess return vs sector ETF and index at 13/26/52w; beta and correlation |
| Risk | drawdown from 104w high; max drawdown; range position percentile |
| Cross-sectional | correlation matrix; rolling 13w correlation to the leader; pair-ratio z-scores |

### Vol-normalised thresholds

A fixed ±5% weekly move is not comparable between a 40%-vol name and a 106%-vol name. Store both:

```python
weekly_sigma  = annualised_vol / sqrt(52)
threshold_1_5s = 1.5 * weekly_sigma
```

Fixed-% for position sizing, σ-normalised for ranking. Label every chart with its basis; mixing them
across tickers is a silent comparison error.

---

## Layer 3 — Strategy

Parameters live in config, never inline.

```python
@dataclass(frozen=True)
class StrategyConfig:
    buy_threshold:  int   = 4
    sell_threshold: int   = -2
    trim_acts:      bool  = False
    entry_size:     float = 10.0
    exit_size:      float = 10.0     # symmetric by default; see pitfall 3
    weights: dict = field(default_factory=lambda:
        {"BUY":1.6, "HOLD":1.0, "TRIM":0.5, "SELL":0.2})
    cost_bps: float = 10.0
    macd: tuple = (12, 26, 9)
```

| Component | Range | Rule |
|---|---|---|
| Trend | 0…+2 | +1 above 10w MA, +1 above 26w MA |
| Momentum | −2…+2 | MACD histogram sign; RSI >70 → −1, 40–70 → +1, <40 → 0 |
| Extension | −2…+1 | vs 26w MA: >40% → −2, >20% → −1, 0–20% → +1, below → 0 |
| Volume | −1…+1 | U/D 8w > 1.2 → +1, < 0.8 → −1 |
| Relative strength | −1…+1 | 13w excess vs benchmark: >+10% → +1, <−10% → −1 |

Verdict: `BUY ≥ 4`, `HOLD 1…3`, `TRIM −1…0`, `SELL ≤ −2`.

Two modes, both required; they answer different questions and produce different results.
**Allocation** weights a basket, renormalised to portfolio value each cycle. **Entry/exit** acts per
name: `+entry_size` on BUY, `−exit_size` on SELL, nothing otherwise.

---

## Layer 4 — Benchmark

Every run reports all five comparators over identical window and capital.

| Benchmark | Definition |
|---|---|
| Buy & hold, equal weight | Primary baseline |
| Buy & hold, rule-weighted once | Single decision at t0, then held. Isolates whether re-deciding adds value |
| Sector ETF | SOXX or the relevant sector |
| Index | QQQ / NIFTY 50 |
| DCA-matched | Same cash, same dates, split evenly, no exits |

DCA-matched is easily omitted and matters: a strategy that adds capital on entries shows a different
return-on-capital than a fixed-capital baseline, and comparing the two directly is invalid.

### Per-ticker, not per-basket

Every comparison runs at individual ticker level and is stored per ticker. The required output is a
distribution:

```
n names tested            : 100
beat own buy & hold       : 38   (38%)
median edge               : -1.4 pts
IQR of edge               : -8.2 to +5.1 pts
by sector                 : semis -12.1 median | software +2.3 | staples +0.8
by volatility quartile    : Q1 +3.1 | Q2 +0.4 | Q3 -2.9 | Q4 -11.6
```

A median edge near zero with wide dispersion means the rule is noise. A consistent negative median
across every sector and volatility bucket means it is harmful. Only per-ticker testing separates the
two.

Per run: end value, P/L, return on contributed capital, edge vs each benchmark in points, turnover,
total cost, peak value and drawdown from peak, and bucket monotonicity (mean forward return by
verdict; skill produces BUY > HOLD > TRIM > SELL).

---

## Layer 5 — Validation

Runs after every pipeline execution and fails loudly.

| Check | Method |
|---|---|
| Independent recomputation | Recompute indicators through different code paths — slicing vs rolling, a from-scratch Wilder RSI. Assert agreement |
| Look-ahead audit | For every decision date, assert `max(bar_date_used) < execution_date` |
| Ledger rebuild | Reconstruct the portfolio from the event log alone; assert final value matches |
| Capital conservation | All compared portfolios deploy identical capital |
| Equal-weight identity | Equal-weight return equals the simple mean of position returns |
| Claim assertions | Every headline claim in the output as a boolean test |
| Render check | No unrendered placeholders; no literal `None` / `nan` |

Claim assertions carry the most weight: they turn prose into tests, so a data refresh that
invalidates a written conclusion breaks the build instead of shipping a false statement.

---

## Pitfalls already paid for

**1 · Silent indicator failure.** MACD returned `None` on short history and `(1 if (mh or 0) > 0
else -1)` turned that into −1 for every ticker. Assert availability explicitly; never let `None`
fall through a boolean.

**2 · Threshold sweeps find artefacts.** In one sensitivity grid `SELL ≤ −3` looked best at every
buy threshold, because the minimum score either name reached was −2. The best cell was the one that
disabled the exit rule. Print how often a threshold fires before believing its result.

**3 · Asymmetric exits compound in a rising market.** Entry +$10 / exit −$20 lost 38 points to
buy-and-hold; symmetric ±$10 lost 19.7.

**4 · Rebalancing lost to deciding once** (11 semis, Feb–Jul 2026, bull regime). Every 14 days
returned 59.17%; a single January decision returned 61.33%. The extension penalty fires exactly when
a name is working, so frequent re-decision trims winners. Costs accounted for a third of the gap.
Untested in a drawdown, where trimming winners is correct behaviour.

**5 · Trend rules stop discriminating in strong uptrends.** By June the rule called 10 of 11 names
HOLD, making it equal-weight-with-costs. Track verdict dispersion as a health metric. This is a
regime property, not a defect.

**6 · Return-on-capital and dollar P/L can disagree.** Lowering the buy threshold produced more
total profit on more capital at a lower percentage return. Report both plus the DCA-matched
comparator.

**7 · Colour semantics collide.** Red meaning "loss" reused for "extended above trend" renders a
positive number in red. Non-money metrics get their own scale and a legend.

**8 · Vendor snapshots disagree with themselves.** The same endpoint returned different close and
volume for the same week on calls minutes apart. Store `fetched_at`, prefer the fresher pull,
discard a partial final bar.

**9 · Selection bias survives everything.** A basket chosen today with knowledge of the year
back-tests well regardless of strategy. Record when and why each ticker entered the watchlist.

---

## Scope of prior results

Back-tests to date cover **11 semiconductor names over Feb–Jul 2026**: one sector, one bull window.
Calibration for the engine, not a prior for the index.

| Finding | Valid scope |
|---|---|
| Strategy lost to buy-and-hold by 38.0 / 19.7 points | INTC + AMD only, Feb–Jul 2026 |
| Rebalancing lost 2.15 points to a single decision | 11 semis, Feb–Jul 2026 |
| BUY did not separate from HOLD | 11 semis, Apr–Jul 2026 |
| SELL bucket identified the worst names | 11 semis, Apr–Jul 2026 |

Buy-and-hold winning here is structural: in a window where the worst name returned +13.2%, any rule
that sells is penalised by construction. The ranking should invert in a drawdown, which is the test
worth running.

Design consequence: test every ticker individually, no pooled conclusions across an index. Semis are
a tight high-beta cluster (MU–SNDK correlated 0.78) and generalise poorly even to other semis. A
rule calibrated on a 106%-vol memory name is a different rule on a 20%-vol staple; use the
σ-normalised thresholds from Layer 2.

### Regime tagging

A result without its regime is not interpretable. Store on every run:

```python
regime = {
  "window":             ("2026-02-02", "2026-07-31"),
  "index_return":       +18.64,
  "sector_return":      +44.87,
  "pct_names_positive": 100.0,
  "max_index_drawdown": -6.2,
  "label":              "bull",   # bull | bear | range | mixed
}
```

Aggregate performance by regime, never across all history as one number.

The open question is drawdown behaviour, and the data to test it exists: INTC fell from $128 to $92
between 22 June and 20 July 2026. A June-start window should be run before any conclusion about exit
rules is drawn.
