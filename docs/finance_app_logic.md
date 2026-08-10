# Finance app — logic specification

Design document for a Flask-based equity tracker: **104-week data layer, 14-week forecast horizon,
14-day decision cadence**, benchmarked against the scoring strategy *and* buy-and-hold.

Written 3 August 2026. Carries forward the design decisions, and the mistakes, from the
semiconductor dashboard and backtest work in `semiconductor_dashboard.html`,
`backtest_apr_jul_2026.html`, `backtest_dynamic_feb_jul_2026.html` and
`entry_exit_v2_symmetric.html`.

---

## Contents

- [Three horizons — do not confuse them](#three-horizons)
- [Architecture](#architecture)
- [Layer 1 — Data (104 weeks)](#layer-1--data-104-weeks)
- [Layer 2 — Features](#layer-2--features)
- [Layer 3 — Strategy](#layer-3--strategy)
- [Layer 4 — Forecast (14 weeks)](#layer-4--forecast-14-weeks)
- [Layer 5 — Benchmark](#layer-5--benchmark)
- [Layer 6 — Validation](#layer-6--validation)
- [Flask API surface](#flask-api-surface)
- [Frontend](#frontend)
- [Pitfalls already paid for](#pitfalls-already-paid-for)
- [Build order](#build-order)
- [Scope of prior results](#scope-of-prior-results--read-before-quoting-them)

---

## Three horizons

The app has three different time constants and conflating them will produce nonsense.

| Horizon | Value | Purpose |
|---|---|---|
| **History** | 104 weeks (2 years) | Feeds every indicator and every distribution |
| **Decision cadence** | 14 days (2 weekly bars) | How often the strategy re-scores and can act |
| **Forecast horizon** | 14 weeks | What the model predicts forward |

**Why 104 weeks specifically.** It is the smallest window that makes every indicator computable
without silent degradation:

| Indicator | Bars needed | Observations at 104 weeks |
|---|---|---|
| 40-week MA | 40 | 64 |
| 26-week MA | 26 | 78 |
| MACD(12,26,9) | 35 | 69 |
| RSI(14) | 15 | 89 |
| 13-week relative strength | 14 | 90 |

The earlier work ran on 52 weeks and paid for it twice: the 40-week MA had only **13** computable
observations, making its z-score statistically meaningless, and a January start left 27 bars where
MACD(12,26,9) needs 35 — it returned `None` and would have scored every ticker identically had it
not been caught. **At 104 weeks neither failure is possible.** Enforce it as a hard precondition.

**⚠ The forecast horizon has a sample-size problem you cannot engineer around.** 104 weeks contains
only **~7 non-overlapping 14-week windows** per ticker. Overlapping windows give ~90 samples but
they share up to 13 of 14 weeks of data, so they are not independent. Effective sample size is
closer to 7 than 90. Consequences:

- Never report a plain train/test accuracy — it will be wildly optimistic
- Use purged, embargoed walk-forward CV (gap ≥ 14 weeks between train and test)
- Pool across tickers to gain samples, and report per-ticker *and* pooled results
- Treat any single-ticker forecast metric as anecdote

---

## Architecture

```
yfinance ──► cache (SQLite/Parquet) ──► features ──► strategy ──► backtest
                    │                       │           │            │
                    │                       └────► forecast ─────────┤
                    │                                                │
                 news/fundamentals ─────────────────────► Flask API ─┴─► frontend
```

Strict rule: **the web layer never calls yfinance.** Flask reads the cache only. A scheduled job
owns all external fetching. This makes the app fast, testable offline, and immune to yfinance
rate-limiting or endpoint changes.

---

## Layer 1 — Data (104 weeks)

### Source

`yfinance`, unofficial. US tickers plain (`NVDA`), India via suffix (`RELIANCE.NS`, `500325.BO`).

### Schedule

One job, daily after both market closes. Weekly bars are the unit of record; daily bars optional
for intra-week context but **not** used by the strategy.

### Schema

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
CREATE TABLE fundamentals (
  ticker TEXT, period_end DATE, period_type TEXT,   -- Q | FY
  revenue REAL, eps REAL, gross_margin REAL,
  fetched_at TIMESTAMP, PRIMARY KEY (ticker, period_end, period_type)
);
CREATE TABLE news (
  ticker TEXT, published_at TIMESTAMP, source TEXT,
  headline TEXT, url TEXT, PRIMARY KEY (ticker, url)
);
CREATE TABLE data_quality (
  ticker TEXT, checked_at TIMESTAMP, n_bars INTEGER,
  first_bar DATE, last_bar DATE, staleness_days INTEGER,
  gaps INTEGER, ohlc_violations INTEGER, passed BOOLEAN
);
```

`adj_close` matters. Use **adjusted** closes for returns and **raw** closes for display, or splits
will appear as crashes. Micron's 2026 series would show a phantom −50% week otherwise.

### Quality gate — run on every ingest, block on failure

| Check | Rule |
|---|---|
| Bar count | ≥ 104, else flag `INSUFFICIENT_HISTORY` |
| Staleness | `last_bar` within 10 days of today, else `STALE` |
| OHLC sanity | `low ≤ close ≤ high` and `high ≥ low` on every row |
| Volume | strictly positive |
| Gaps | no missing Mondays inside the range |
| Duplicates | primary key enforces it; assert anyway |

The earlier work shipped a dashboard where **Broadcom's data was two months stale** and had to be
flagged in prose on every card. The gate exists so that never reaches the UI silently. A ticker
failing the gate renders with a banner and is **excluded from backtests**, not quietly forward-filled.

### Forward-fill policy

Forward-fill for *display continuity only*, never for return computation. If a bar is missing,
the return for that period is `NULL`, not zero.

---

## Layer 2 — Features

Computed from the cache, cached themselves, keyed `(ticker, week_start)`. Every feature must be
computable from bars **strictly at or before** `week_start`.

| Group | Features |
|---|---|
| Trend | SMA 10/26/40w; price vs each; golden/death cross; weeks above 40w |
| Momentum | RSI(14); MACD(12,26,9) line/signal/histogram; ROC 4/13/26/52w; 12-1 momentum |
| Extension | % above 26w and 40w MA; z-score of each vs own 104w history; Bollinger %B(20,2) |
| Volume | volume z-score vs 104w; up/down volume ratio 8w; OBV; dollar-volume trend |
| Volatility | realised vol 13w/52w annualised + percentile; ATR(14) as % of price |
| Relative | excess return vs sector ETF and index at 13/26/52w; beta and correlation to each |
| Risk | drawdown from 104w high; max drawdown; range position percentile |
| Cross-sectional | correlation matrix; rolling 13w correlation to the leader; pair-ratio z-scores |

### Vol-normalised thresholds — required for cross-ticker work

A fixed ±5% weekly move is not comparable across a 40%-vol name and a 106%-vol name. Store both:

```python
weekly_sigma = annualised_vol / sqrt(52)
threshold_1_5s = 1.5 * weekly_sigma
```

Report fixed-% for position sizing, σ-normalised for ranking. Label every chart with which basis it
uses. Mixing them across tickers is a silent comparison error.

---

## Layer 3 — Strategy

Port of the scoring rule, generalised. **Parameters live in config, never inline.**

```python
@dataclass(frozen=True)
class StrategyConfig:
    buy_threshold:  int   = 4
    sell_threshold: int   = -2
    trim_acts:      bool  = False
    entry_size:     float = 10.0
    exit_size:      float = 10.0     # keep symmetric — see pitfalls
    weights: dict = field(default_factory=lambda:
        {"BUY":1.6, "HOLD":1.0, "TRIM":0.5, "SELL":0.2})
    cost_bps: float = 10.0
    macd: tuple = (12, 26, 9)        # valid because 104w guarantees enough bars
```

### Score components (each returns an int, summed)

| Component | Range | Rule |
|---|---|---|
| Trend | 0..+2 | +1 above 10w MA, +1 above 26w MA |
| Momentum | −2..+2 | MACD histogram sign; RSI >70 → −1, 40–70 → +1, <40 → 0 |
| Extension | −2..+1 | vs 26w MA: >40% → −2, >20% → −1, 0–20% → +1, below → 0 |
| Volume | −1..+1 | U/D 8w > 1.2 → +1, < 0.8 → −1 |
| Relative strength | −1..+1 | 13w excess vs sector: >+10% → +1, <−10% → −1 |

Verdict: `BUY ≥ 4`, `HOLD 1..3`, `TRIM −1..0`, `SELL ≤ −2`.

### Two operating modes

**Allocation mode** — weights across a basket, renormalised to portfolio value each cycle.
**Entry/exit mode** — per-stock, `+entry_size` on BUY, `−exit_size` on SELL, nothing otherwise.

Both must be available; they answer different questions and gave different results.

---

## Layer 4 — Forecast (14 weeks)

Build in this order. The ordering is deliberate — reliability descends as you go down.

### 4a. Volatility (build first)

Most tractable target. Volatility clusters and is autocorrelated; returns are not.

- **Target:** realised vol over the next 14 weeks
- **Model:** GARCH(1,1) baseline, or gradient boosting on vol features
- **Baseline to beat:** trailing 13-week realised vol (surprisingly hard to beat)
- **Use:** position sizing. The INTC drill-down showed a vol ratio of 1.39 implying a 0.72×
  position multiplier — a trim justification requiring **no directional view at all**

### 4b. Distribution / range

- **Target:** quantiles of 14-week return (10th, 25th, 50th, 75th, 90th)
- **Model:** quantile regression or conformal prediction intervals
- **Report as:** "−9% to +21% at 80% confidence", never a point estimate
- **Metric:** pinball loss; calibration curve — does the 80% band contain the outcome 80% of the time?

### 4c. Cross-sectional ranking

- **Target:** rank of 14-week return *within the basket*, not absolute return
- **Metric:** Spearman IC per period, then the IC mean / IC std ratio
- **Why:** materially easier than absolute prediction, and it's what allocation actually needs

### 4d. Direction (build last, expect little)

- **Target:** sign of 14-week excess return vs the index
- **Realistic ceiling:** 53–56% accuracy. Anything above 60% on this data means a bug
- **Mandatory baseline:** always-long. In a rising market that wins, and any model must beat it
- **Metric:** accuracy *and* log-loss *and* accuracy vs the always-long baseline

### Validation protocol — non-negotiable

```
purged walk-forward:
  train  [t0 ......... t1]
  purge  [t1 .. t1+14w]     <- discarded, prevents target leakage
  test   [t1+14w ... t2]
```

- Scalers, imputers and encoders fit on **train only**, inside the fold
- No feature may use data after its own timestamp
- Report the **baseline** alongside every metric; a model that doesn't beat trailing-vol or
  always-long is a negative result and should be recorded as one

---

## Layer 5 — Benchmark

Every strategy run reports against **all** of these, over the identical window and capital:

| Benchmark | Definition |
|---|---|
| **Buy & hold, equal weight** | The primary baseline. Beat this or the strategy is decoration |
| **Buy & hold, rule-weighted once** | Single decision at t0, then held — isolates whether *re-deciding* adds value |
| **Sector ETF** | SOXX, or the relevant sector |
| **Index** | QQQ / NIFTY 50 |
| **DCA-matched** | Same cash, same dates, split evenly, no exits — isolates signal value from capital schedule |

That last one matters and is easy to omit. A strategy that adds capital on entries will show a
different return-on-capital than a fixed-capital baseline, and comparing them directly is invalid.

### Per-ticker, not per-basket

**Every benchmark comparison runs at the individual ticker level and is stored per ticker.** Basket
aggregates are a reporting convenience, never a conclusion. The required output is a distribution:

```
n names tested            : 100
beat own buy & hold       : 38   (38%)
median edge               : -1.4 pts
IQR of edge               : -8.2 to +5.1 pts
best / worst              : +24.3 / -31.7 pts
by sector                 : semis -12.1 median | software +2.3 | staples +0.8 ...
by volatility quartile    : Q1 +3.1 | Q2 +0.4 | Q3 -2.9 | Q4 -11.6
```

A median edge near zero with wide dispersion means the rule is noise. A consistent negative median
across every sector and volatility bucket means it is actively harmful. **These are different
findings and only per-ticker testing separates them.** Aggregate a basket number and you cannot
tell which you have.

### Required outputs per run

- End value, P/L, return on contributed capital
- Edge vs each benchmark, in points
- Turnover, total cost, cost as % of capital
- **Bucket monotonicity:** mean forward return by verdict. Genuine skill produces
  BUY > HOLD > TRIM > SELL. The earlier run gave BUY +59.9% and HOLD +67.2% — non-monotonic, and
  that inversion was more informative than the headline return
- Peak value and drawdown from peak — exit timing dominates short windows

---

## Layer 6 — Validation

Ship a `verify.py` that runs after every pipeline execution and **fails loudly**. This caught real
bugs repeatedly in the earlier work.

| Check | Method |
|---|---|
| Independent recomputation | Recompute a sample of indicators with **different code paths** — slicing vs rolling, a from-scratch Wilder RSI. Assert agreement |
| Look-ahead audit | For every decision date, assert `max(bar_date_used) < execution_date` |
| Ledger rebuild | Reconstruct the portfolio from the event log alone; assert final value matches to the cent |
| Capital conservation | All compared portfolios deploy identical capital |
| Equal-weight identity | Equal-weight return == simple mean of position returns |
| Claim assertions | Every headline claim in the UI as a boolean test. If the dashboard says "10 of 11 above the 40-week MA", assert exactly that |
| Render check | No unrendered template placeholders; no literal `None`/`nan` in output |

The claim assertions are the highest-value item. They turn prose into tests, so a data refresh that
invalidates a written conclusion **breaks the build** instead of shipping a false statement.

---

## Flask API surface

```
GET  /api/tickers                        list + quality status
GET  /api/bars/<ticker>?weeks=104        OHLCV from cache
GET  /api/features/<ticker>              current indicator snapshot
GET  /api/features/<ticker>/history      indicator time series
GET  /api/score/<ticker>                 score, components, verdict
GET  /api/signals?asof=YYYY-MM-DD        all verdicts for a decision date
GET  /api/forecast/<ticker>              14w vol, quantiles, rank, direction + intervals
POST /api/backtest                       {start, end, cadence, config} -> results + benchmarks
GET  /api/backtest/<run_id>              stored run
GET  /api/news/<ticker>                  headlines, newest first
GET  /api/fundamentals/<ticker>          latest quarter vs year-ago
GET  /api/health                         data quality gate status per ticker
```

Every response carries `as_of` and `data_quality` fields. The frontend must render staleness, never
hide it.

---

## Frontend

Reuse `tracker_style.md` (Midnight Slate). Components already specified there: KPI tiles, ticker
tabs, metric wells, correlation heatmap, volume bars, verdict pills, caveat banners.

Two rules carried over:

1. **Lead with the caveat.** Data limitations go in a banner above the first table, not in a footer.
2. **Output evidence, not verdicts.** "AMD: +52% above 26w MA, U/D volume 0.9, three distribution
   weeks clustered in the last six" is more useful than "SELL" — especially when pairing with your
   own research. The score is a summary of the evidence, not a replacement for it.

---

## Pitfalls already paid for

Each of these cost real debugging time. They are recorded so they are not rediscovered.

**1. Silent indicator failure.** MACD returned `None` on short history and the scoring line
`(1 if (mh or 0) > 0 else -1)` turned that into −1 for every ticker. Assert indicator availability
explicitly; never let `None` fall through a boolean.

**2. Threshold sweeps find artefacts.** In the sensitivity grid, `SELL ≤ −3` looked best at every
buy threshold — because the minimum score either stock ever reached was −2. **The best cell was the
one that disabled the exit rule.** Any parameter search on a small sample finds this. Always print
how often a threshold actually fires before believing its result.

**3. Asymmetric exits compound in a rising market.** Entry +$10 / exit −$20 lost 38 points to
buy-and-hold; symmetric ±$10 lost 19.7. Keep sizing symmetric unless you have a specific reason.

**4. Rebalancing frequently lost to deciding once** *(11 semis, Feb–Jul 2026 — bull regime)*.
Every 14 days returned 59.17%; a single January decision returned 61.33%. The extension penalty
fires exactly when a name is working, so frequent re-decision trims winners. Costs were only a
third of the gap. **Untested in a drawdown**, where trimming winners is the correct behaviour.

**5. Trend rules stop discriminating in strong uptrends.** By June the rule called 10 of 11 names
HOLD, making it equal-weight-with-costs. Track verdict dispersion over time as a health metric; low
dispersion means the signal has gone quiet. This is a regime property, not a defect — expect the
opposite in a choppy market.

**6. Return-on-capital and dollar P/L can disagree.** Lowering the buy threshold produced *more*
total profit on *more* capital but a *lower* percentage return. Report both, plus the DCA-matched
comparator, or the comparison is meaningless.

**7. Colour semantics collide.** Red meant "loss" everywhere, then got reused for "extended above
trend" — a positive number in red. Give non-money metrics their own scale and a legend.

**8. Vendor snapshots disagree with themselves.** The same endpoint returned different close and
volume for the same week on two calls minutes apart. Always store `fetched_at`, prefer the fresher
pull, and discard a final bar that looks partial.

**9. Selection bias survives everything.** A basket chosen today with knowledge of the year will
backtest well regardless of the strategy. Record *when and why* each ticker entered the watchlist.

---

## Build order

| Phase | Deliverable | Gate before proceeding |
|---|---|---|
| 1 | yfinance → cache, 104w, quality gate | All tickers pass the gate |
| 2 | Feature engine + feature store | Independent recomputation matches |
| 3 | Strategy scoring, both modes | Verdicts reproduce by hand on 3 spot checks |
| 4 | Backtest harness + benchmarks + `verify.py` | Look-ahead audit passes; ledger rebuild matches |
| 5 | Flask API + tracker frontend | `/api/health` renders staleness correctly |
| 6 | Volatility forecast | Beats trailing-13w-vol baseline |
| 7 | Quantile / range forecast | 80% band contains outcome ~80% of the time |
| 8 | Cross-sectional ranking | Positive mean Spearman IC across folds |
| 9 | Directional model | Beats always-long. **If it does not, record and stop** |

**Phase 4 before Phase 6 is the important ordering.** The verification harness is the bug detector.
Building models before it exists means a look-ahead bug produces beautiful results you will believe.

---

## Scope of prior results

The backtests so far covered **11 semiconductor stocks over Feb–Jul 2026** — one sector, one bull
window. Useful as calibration for the engine, not as a prior for the Nasdaq 100.

**Observed, with scope attached:**

| Finding | Valid scope |
|---|---|
| Strategy lost to buy-and-hold by 38.0 / 19.7 points | INTC + AMD only, Feb–Jul 2026 |
| Rebalancing lost 2.15 points to a single decision | 11 semis, Feb–Jul 2026 |
| BUY did not separate from HOLD | 11 semis, Apr–Jul 2026 |
| SELL bucket correctly identified the worst names | 11 semis, Apr–Jul 2026 |

Buy-and-hold winning here is structural: in a window where the worst name returned +13.2%, any rule
that sells is penalised by construction. Expect the ranking to invert in a drawdown — that's the
test worth running, not a caveat.

**Design consequence: test every ticker individually; no pooled conclusions across the index.**

- Each name gets its own backtest record, benchmark comparison and verdict.
- Semis are a tight, high-beta cluster (MU–SNDK correlated 0.78) — they generalise poorly even to
  other semis, let alone software, staples or biotech.
- A rule calibrated on a 106%-vol memory stock is a different rule on a 20%-vol staple. Use the
  σ-normalised thresholds from Layer 2.

### Regime tagging — required on every backtest record

A result without its regime is not interpretable. Store on every run:

```python
regime = {
  "window":            ("2026-02-02", "2026-07-31"),
  "index_return":      +18.64,        # QQQ over the window
  "sector_return":     +44.87,        # relevant sector ETF
  "pct_names_positive": 100.0,        # breadth
  "max_index_drawdown": -6.2,
  "label":             "bull",        # bull | bear | range | mixed
}
```

Then aggregate strategy performance **by regime**, never across all history as a single number.
The open question this project has not yet answered is how the rule behaves in a drawdown — and
the data to test it exists. INTC fell from $128 to $92 between 22 June and 20 July 2026. A
June-start window, where the exit rule has something to protect against, is the informative test
and should be run before any conclusion about exit rules is drawn.

---

## Working principle

Optimise for **signal discovery**: per-ticker, per-regime results, cleanly measured, accumulating
into a searchable record. The verification layer exists so results are trustworthy enough to act
on — not as a hedge.

Where the data supports a strategy, say so plainly and size it. Where it doesn't, that ticker is
simply a hold candidate and the search moves on.

---

*Spec v1 — 3 August 2026. Companions: `tracker_style.md` (design system), `analysis_deep.md`
(per-ticker drill-down method).*
