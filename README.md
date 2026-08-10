# equity-tracker

**Auditable equity research dashboards.** Fetch weekly price data, score it, back-test it, and
render a self-contained HTML dashboard — where **every claim in the output is asserted as a test**.

If a data refresh invalidates a written conclusion, the build breaks instead of shipping a false
statement.

[![CI](https://github.com/jovi-maverick/equity-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/jovi-maverick/equity-tracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)

---

## Why another one of these

Most repos in this space are either an indicator library or a back-tester with no output layer.
This one is built around the part that usually gets skipped:

**A verification harness that runs after every pipeline execution.** Six classes of check —
independent recomputation through different code paths, a look-ahead audit at every decision date,
ledger rebuilds from the event log, capital conservation, golden-value cross-checks against verified
reference prices, and claim assertions that turn prose into booleans.

**Output is one self-contained HTML file.** No server, no build step, no CDN. Opens offline, hosts
free on GitHub Pages.

**A data quality gate that quarantines rather than papers over.** A ticker with a stale or broken
feed is excluded from aggregates and flagged on its own card — never silently forward-filled.

---

## Quick start

```bash
pip install "equity-tracker[live]"

tracker fetch  --tickers NVDA,AMD,INTC,ASML,TXN --weeks 104
tracker doctor --golden tests/fixtures/golden_2026_07_31.json
tracker report --out build/index.html
open build/index.html
```

Or from source:

```bash
git clone https://github.com/jovi-maverick/equity-tracker
cd equity-tracker
pip install -e ".[live,dev]"
pytest                      # 35 tests, no network needed
```

---

## Commands

| Command | Purpose |
|---|---|
| `tracker fetch` | Pull weekly bars into the local SQLite cache, run the quality gate |
| `tracker doctor` | Pre-push gate: shape checks + golden-value cross-check |
| `tracker score` | Print current scores with component breakdown |
| `tracker report` | Render the HTML dashboard |
| `tracker backtest` | Walk-forward back-test with five benchmarks and the bucket test |
| `tracker verify` | Run the verification harness standalone |

---

## The scoring rule

Five components, each an integer, summed. Thresholds map the total to BUY / HOLD / TRIM / SELL.

| Component | Range | Basis |
|---|---|---|
| Trend | 0 … +2 | Price vs 10-week and 26-week MA |
| Momentum | −2 … +2 | MACD histogram sign, RSI band |
| Extension | −2 … +1 | Distance above the 26-week MA — penalises stretched entries |
| Volume | −1 … +1 | Up/down volume ratio over 8 weeks |
| Relative strength | −1 … +1 | 13-week excess return vs the sector ETF |

Defaults are a starting point, not an optimum. Everything lives in `StrategyConfig` — nothing is
inline.

**If an indicator can't be computed, its component scores 0** and the name is listed on the card.
It never contributes a negative by accident. That specific bug — `(macd or 0) > 0` turning
"unavailable" into "bearish" — scored every ticker identically in an earlier iteration.

---

## Benchmarks

Every back-test reports against five comparators on identical capital over an identical window:

1. **Buy & hold, equal weight** — the primary baseline
2. **Buy & hold, rule-weighted once** — isolates whether *re-deciding* adds value
3. **Sector ETF**
4. **Index**
5. **DCA-matched** — same cash, same dates, split evenly, no exits. Isolates signal value from the
   capital schedule, which a strategy that adds capital on entries will otherwise distort

Plus the **bucket test**: mean forward return by verdict. Real skill produces
BUY > HOLD > TRIM > SELL. Non-monotonic buckets are often more informative than the headline return.

Results are stored **per ticker with a regime tag**. Basket aggregates are a reporting convenience,
never a conclusion — the output is a distribution of edges, not a single number.

---

## Data

Uses `yfinance`. **No market data is redistributed** — you fetch your own into a local SQLite cache.
The web/render layer reads the cache and never calls the network.

Yahoo retired its official API in 2017; `yfinance` calls internal endpoints that can change or
rate-limit without notice. Consequences baked in: fetching is a scheduled job, requests are chunked
and throttled, and results are always cached.

**104 weeks is a hard floor**, not a preference. Below it the 40-week MA has too few observations
for a meaningful z-score and MACD(12,26,9) can't be computed at all.

### Golden-value checks

`tracker doctor` compares live data against independently verified reference closes. This catches
the three failure modes that actually bite:

- **Raw vs adjusted close** — a split looks like a crash
- **Week-labelling off-by-one** — silently shifts every indicator
- **Timezone drift** on the final bar

---

## Documentation

| Doc | Contents |
|---|---|
| [`docs/finance_app_logic.md`](docs/finance_app_logic.md) | Full architecture spec, layer by layer, plus nine documented pitfalls |
| [`docs/tracker_style.md`](docs/tracker_style.md) | Midnight Slate design system — palette, type scale, components |
| [`docs/analysis_deep.md`](docs/analysis_deep.md) | Per-ticker drill-down method: volume/sell-off, volatility trend, price shocks, catalysts |

Two pitfalls worth reading before you tune anything:

**Threshold sweeps find artefacts.** In one sensitivity grid, `SELL ≤ −3` looked best at every buy
threshold — because the minimum score either stock ever reached was −2. The best cell was the one
that disabled the exit rule entirely. Always print how often a threshold actually fires.

**Colour semantics collide.** Red means "loss" everywhere, so reusing it for "extended above trend"
puts a positive number in red. Non-money metrics get their own scale and a legend.

---

## Status

Alpha. The core pipeline, verification harness and renderer work end to end. The forecast layer
described in `docs/finance_app_logic.md` (volatility → range → ranking → direction, in that order of
reliability) is not implemented yet.

Contributions welcome — particularly additional golden-value fixtures for non-US exchanges.

---

## License

MIT © jovi-maverick

Analysis tooling, not investment advice.
