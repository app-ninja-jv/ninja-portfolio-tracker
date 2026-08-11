# Roadmap

Components specified but **not implemented**. Recorded here so the specification in
[`docs/finance_app_logic.md`](docs/finance_app_logic.md) describes only what exists.

---

## Build order

Phase 4 precedes Phase 6 deliberately. The verification harness is the bug detector; models built
before it exists produce results that look correct and are believed.

| Phase | Deliverable | Gate | State |
|---|---|---|---|
| 1 | Fetch → cache, 104w, quality gate | All tickers pass the gate | done |
| 2 | Feature engine | Independent recomputation matches | done |
| 3 | Scoring, both modes | Verdicts reproduce by hand on 3 spot checks | done |
| 4 | Back-test, benchmarks, verification harness | Look-ahead audit passes; ledger rebuild matches | done |
| 5 | HTTP API | Health endpoint renders staleness correctly | not started |
| 6 | Volatility forecast | Beats trailing-13w-vol baseline | not started |
| 7 | Quantile / range forecast | 80% band contains outcome ~80% of the time | not started |
| 8 | Cross-sectional ranking | Positive mean Spearman IC across folds | not started |
| 9 | Directional model | Beats always-long, else record and stop | not started |

---

## Forecast layer (14 weeks)

Reliability descends down this list. Build in order.

**6 · Volatility.** Target: realised vol over the next 14 weeks. Baseline: trailing 13-week realised
vol, which is difficult to beat. Model: GARCH(1,1) or gradient boosting on vol features. Use is
position sizing — an INTC vol ratio of 1.39 implies a 0.72× multiplier and requires no directional
view.

**7 · Distribution.** Target: 10th/25th/50th/75th/90th quantiles of 14-week return. Method: quantile
regression or conformal intervals. Report as a range, never a point estimate. Metric: pinball loss
plus a calibration curve.

**8 · Cross-sectional ranking.** Target: rank of 14-week return within the basket rather than
absolute return. Metric: Spearman IC per period, then IC mean / IC std. Materially easier than
absolute prediction and sufficient for allocation.

**9 · Direction.** Target: sign of 14-week excess return vs the index. Realistic ceiling 53–56%;
above 60% on this data indicates a bug. Mandatory baseline: always-long. Metrics: accuracy,
log-loss, and edge over always-long.

### Validation protocol

```
purged walk-forward:
  train  [t0 ......... t1]
  purge  [t1 .. t1+14w]     discarded, prevents target leakage
  test   [t1+14w ... t2]
```

Scalers, imputers and encoders fit on train only, inside the fold. No feature may use data after its
own timestamp. Every metric is reported alongside its baseline; a model that fails to beat
trailing-vol or always-long is a negative result and is recorded as one.

**Sample size constraint.** 104 weeks contains ~7 non-overlapping 14-week windows per ticker.
Overlapping windows yield ~90 samples sharing up to 13 of 14 weeks, so effective n is nearer 7 than
90. Consequences: never report a plain train/test accuracy; use purged, embargoed CV with a ≥14-week
gap; pool across tickers and report pooled and per-ticker results separately; treat any
single-ticker forecast metric as anecdote.

---

## HTTP API (Phase 5)

The render layer currently reads the cache directly. A service layer would expose:

```
GET  /api/tickers                     list and quality status
GET  /api/bars/<ticker>?weeks=104     OHLCV from cache
GET  /api/features/<ticker>           indicator snapshot
GET  /api/features/<ticker>/history   indicator time series
GET  /api/score/<ticker>              score, components, verdict
GET  /api/signals?asof=YYYY-MM-DD     all verdicts for a decision date
GET  /api/forecast/<ticker>           14w vol, quantiles, rank, direction
POST /api/backtest                    {start, end, cadence, config}
GET  /api/backtest/<run_id>           stored run
GET  /api/news/<ticker>               headlines, newest first
GET  /api/fundamentals/<ticker>       latest quarter vs year-ago
GET  /api/health                      quality gate status per ticker
```

Every response carries `as_of` and `data_quality`. The web layer never calls yfinance; a scheduled
job owns all external fetching. This keeps the service testable offline and immune to vendor
rate-limiting.

---

## Dashboard

- **Benchmark selection.** Relative strength is currently fixed to the sector ETF. Offer sector,
  Nasdaq 100 (QQQ), S&P 500 (SPY) and custom, single-select. The scored benchmark stays declared and
  recorded; alternates render as evidence so the verdict remains reproducible.
- **104-week trendline per card**, ticker vs benchmark, both rebased to 100. An absolute-price
  overlay is unreadable across instruments an order of magnitude apart.
- **Ticker metadata.** `_meta_stub()` in `cli.py` returns empty strings, so company name and sector
  render blank.
- **Correlation matrix and pair-ratio z-scores.** Computed in `features/indicators.py`, not rendered.
- Golden fixtures for NSE/BSE tickers to validate the `.NS` / `.BO` path.
