# ninja-portfolio-tracker

Weekly equity research pipeline: fetch → score → back-test → static HTML dashboard.

Every claim rendered into the output is asserted as a test. A data refresh that invalidates a
written conclusion fails the build rather than publishing a false statement.

[![CI](https://github.com/app-ninja-jv/ninja-portfolio-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/app-ninja-jv/ninja-portfolio-tracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)

---

## Scope

Weekly OHLCV bars, 104-week history, 14-day decision cadence. Five-component scoring rule mapped to
BUY / HOLD / TRIM / SELL. Walk-forward back-test against five comparators. Output is a single
self-contained HTML file: no server, no build step, no CDN.

A verification harness runs after every pipeline execution: independent recomputation through
separate code paths, look-ahead audit at each decision date, ledger rebuild from the event log,
capital conservation, golden-value cross-check, and claim assertion.

Tickers failing the data quality gate are quarantined: excluded from aggregates, flagged on their
own card, never forward-filled.

---

## Quick start

Docker pins Python 3.12. Nothing is installed on the host.

```bash
git clone https://github.com/app-ninja-jv/ninja-portfolio-tracker
cd ninja-portfolio-tracker

docker compose build
docker compose run --rm test
docker compose run --rm tracker fetch --tickers NVDA,AMD,INTC,ASML,TXN --weeks 104
docker compose run --rm tracker doctor
docker compose run --rm tracker report --out build/index.html
docker compose up serve
```

Dashboard at `http://localhost:8000`, rendered as GitHub Pages will serve it.

`data/` and `build/` are bind-mounted; `src/` is mounted read-only, so code edits apply without a
rebuild. `TZ=UTC` is fixed in compose: week labelling must not drift with host timezone.

Without Docker, Python 3.10+ and pip ≥ 21.3:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[live,dev]" && pytest
```

---

## Commands

| Command | Purpose |
|---|---|
| `tracker fetch` | Pull weekly bars into the SQLite cache, run the quality gate |
| `tracker doctor` | Pre-push gate: shape checks and golden-value cross-check |
| `tracker score` | Print scores with component breakdown |
| `tracker report` | Render the HTML dashboard |
| `tracker backtest` | Walk-forward back-test with benchmarks and the bucket test |
| `tracker verify` | Run the verification harness standalone |

---

## Scoring rule

Five integer components, summed. Thresholds in `StrategyConfig`; nothing is inline.

| Component | Range | Basis |
|---|---|---|
| Trend | 0 … +2 | Price vs 10-week and 26-week MA |
| Momentum | −2 … +2 | MACD histogram sign, RSI band |
| Extension | −2 … +1 | Distance above the 26-week MA |
| Volume | −1 … +1 | Up/down volume ratio, 8 weeks |
| Relative strength | −1 … +1 | 13-week excess return vs the benchmark |

Verdict: `BUY ≥ 4`, `HOLD 1…3`, `TRIM −1…0`, `SELL ≤ −2`. Defaults are a starting point, not an
optimum.

An indicator that cannot be computed scores 0 and is listed on the card. It never contributes a
negative by default.

---

## Benchmarks

Each back-test reports five comparators on identical capital over an identical window: buy-and-hold
equal weight (primary baseline), buy-and-hold rule-weighted once (isolates whether re-deciding adds
value), sector ETF, index, and DCA-matched (isolates signal value from capital schedule).

The bucket test reports mean forward return by verdict. Skill produces BUY > HOLD > TRIM > SELL;
non-monotonic buckets are frequently more informative than the headline return.

Results are stored per ticker with a regime tag. Basket aggregates are a reporting convenience, not
a conclusion — the output is a distribution of edges.

---

## Data

`yfinance`. No market data is redistributed: the cache is fetched locally and the render layer never
calls the network. Yahoo retired its official API in 2017, so `yfinance` targets internal endpoints
that change without notice; fetching is therefore scheduled, chunked, throttled and always cached.

Minimum history 104 weeks. MACD(12,26,9) needs 35 bars; the 40-week MA z-score needs 40
observations, of which a 52-week window yields 13.

`tracker doctor` compares live data against verified reference closes, catching raw-vs-adjusted
close (a split reads as a crash), week-labelling off-by-one, and timezone drift on the final bar.

---

## Documentation

| Doc | Contents |
|---|---|
| [`docs/finance_app_logic.md`](docs/finance_app_logic.md) | Layer-by-layer specification and nine documented pitfalls |
| [`docs/analysis_deep.md`](docs/analysis_deep.md) | Per-ticker drill-down method |
| [`docs/theme.md`](docs/theme.md) | Midnight Slate palette and layout rules |
| [`ROADMAP.md`](ROADMAP.md) | Unbuilt components: forecast layer, HTTP API, build order |

---

## Status

Alpha. Pipeline, verification harness and renderer work end to end. The forecast layer is not
implemented. Contributions welcome, particularly golden-value fixtures for non-US exchanges.

MIT © app-ninja-jv. Analysis tooling, not investment advice.
