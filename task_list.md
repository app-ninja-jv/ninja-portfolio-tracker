# Task list — ninja-portfolio-tracker

**Workflow is Docker only. Do not use `make`** — the Makefile has been removed;
zsh config on this machine intercepts `make test`/`make build`.

**State (12 Aug 2026):** Docker build works · 35 tests passing · ruff clean ·
real yfinance data fetched · golden check passed 10/11 · dashboard renders and
serves at localhost:8000 · nothing pushed to GitHub yet

---

## ✅ Done

- [x] Commit amended — `src/tracker/data/` tracked (4 files)
- [x] Docker workflow built and working; Python 3.12 pinned in the image
- [x] `docker compose run --rm test` → 35 passing
- [x] `quickstart.py` end-to-end on synthetic data
- [x] Real yfinance fetch for 10 tickers into `data/bars.sqlite`
- [x] **`doctor` passed — 10/11 golden closes matched.** No week-labelling
      off-by-one, no raw-vs-adjusted mixup. The two failure modes I was most
      worried about are ruled out. `SNDK` warned only because it wasn't fetched.
- [x] `report` → `build/index.html`, 80,281 chars, 10 tickers
- [x] `verify` clean after fixing the report/verify ticker-set mismatch
- [x] Dashboard viewed at localhost:8000
- [x] Makefile removed — Docker commands only

---

## 2 · UI tweaks — NEXT SESSION

### 2a · User-selectable benchmark (choose one)

Today "vs sector 13w" is hardwired to `SOXX` and there is no index comparison
anywhere in the UI. Reading only the sector column is misleading — from the
3 Aug study, 26-week relative strength:

| | vs SOX | vs NDX |
|---|---|---|
| NVDA | −42.7% | −1.3% |
| ASML | −38.0% | +23.4% |
| TXN | −8.3% | +48.2% |

Sector-only made NVDA look broken and ASML/TXN look like laggards. Both wrong.

**Design — single-select benchmark, four suggestions:**

| Option | Symbol | Reads as |
|---|---|---|
| Sector (semis) | `SOXX` | "beating its own industry" |
| Nasdaq 100 | `QQQ` | "beating large-cap growth" |
| S&P 500 | `SPY` | "beating the market" |
| Custom | user-supplied | any cached symbol |

Nasdaq-100 and QQQ are **the same exposure** — QQQ tracks the index, so do not
offer both as separate options. One entry, labelled "Nasdaq 100 (QQQ)".

Implementation notes:

- `StrategyConfig` gains `benchmark: str = "SOXX"`; `score_at()` takes
  `benchmark_bars` instead of `sector_bars` (rename — the argument was never
  sector-specific, only the default was)
- `rs_sector_13w` → `rs_benchmark_13w` in `evidence`. Grep for the old key in
  `dashboard.py:101,145` and `benchmarks.py`
- Renderer: compute scores against **all** benchmarks in one pass, emit each set
  as JSON, and let a header `<select>` swap the visible one client-side. Keeps
  the output a single static file — no rebuild per benchmark
- Cache already holds SOXX, SPY and QQQ (`cmd_fetch` appends them), so no fetch
  change needed
- The **scoring** relative-strength component should stay on one declared
  benchmark, recorded in the output. Letting the viewer change the benchmark
  and silently restating the verdict would make the score irreproducible —
  show the alternates as evidence, keep the verdict anchored

### 2b · 104-week trendline per card, ticker vs benchmark

Both series **rebased to 100** at the first bar — an absolute-price overlay of
NVDA against SOXX is unreadable. Rebasing makes the divergence the subject.

- Inline SVG, same construction as `volume_chart()` in `dashboard.py` — no CDN
- Ticker in `var(--accent)`, benchmark in `var(--muted)` dashed
- Optional second row: the **ratio line** (ticker ÷ benchmark, rebased). This is
  the actual relative-strength picture and `pair_ratio_z` in
  `features/indicators.py` already computes the z-score for it
- Mark the 40w MA crossover points; that is what the trend component scores
- Follows the same benchmark selection as 2a

- [ ] 2a benchmark selector
- [ ] 2b rebased 104-week trendline

Reference: `docs/tracker_style.md` for the Midnight Slate tokens. Iterate with:

```bash
docker compose run --rm tracker report --out build/index.html
docker compose up serve
```

`src/` is mounted read-only into the container, so renderer edits take effect
**without** a rebuild — just re-run `report`.

---

## 3 · Optional data completeness

```bash
docker compose run --rm tracker fetch --tickers NVDA,AMD,INTC,ASML,TXN,AMAT,MU,QCOM,ARM,AVGO,SNDK --weeks 104
docker compose run --rm tracker doctor
```

`doctor` compares against `tests/fixtures/golden_2026_07_31.json` — eleven independently
verified 31 July closes. **If NVDA doesn't return $200.75 ±0.5%**, it's one of three things,
in order of likelihood:

| Symptom | Cause | Fix |
|---|---|---|
| Every indicator shifted by one period | Week labelled by period **end**, not start | `_monday()` in `data/fetch.py` |
| A ticker shows a phantom ~50% crash | Raw close used where adjusted belongs | `auto_adjust` handling in `_frame_to_bars()` |
| Only the final bar is wrong | Timezone drift | Normalise to UTC before `_monday()` |

- [ ] Add SNDK so all 11 golden values check (currently 10/11)

---

## 4 · Backtest on live data

```bash
docker compose run --rm tracker backtest --mode allocation --json-out build/backtest.json
```

- [ ] Benchmarks, bucket test and regime tag print sensibly
- [ ] Spot-check two scores by hand against the 3 Aug semiconductor analysis

---

## 5 · Publish

```bash
gh repo create ninja-portfolio-tracker --public --source=. --remote=origin --push
```

Then: **Settings → Pages → Source: GitHub Actions**

Run *Actions → Refresh dashboard → Run workflow* manually. It is `workflow_dispatch`
only by design. Let it go green **twice**, then uncomment the cron in
`.github/workflows/refresh.yml`.

- [ ] Repo created and pushed
- [ ] Pages source set to GitHub Actions
- [ ] Two clean manual workflow runs
- [ ] Cron enabled
- [ ] Site live at `https://app-ninja-jv.github.io/ninja-portfolio-tracker/`

Safety already wired: `tracker verify` runs before the Pages upload and **fails the build**,
so a broken dashboard cannot publish. `doctor` is `continue-on-error` because reference
prices age — it warns rather than blocks.

---

## 5 · Analysis backlog (independent of the repo work)

Carried over from 3 August. See `docs/analysis_deep.md` for the per-ticker method.

- [ ] **June-start drawdown test** — the highest-value open question. Every backtest so
      far ran in a bull window where any rule that sells is penalised by construction.
      INTC fell $128 → $92 between 22 June and 20 July; that window is where an exit rule
      actually gets tested. Run before drawing any conclusion about exit rules.
- [ ] **MU deep dive** — top of the drill-down backlog; the peak-cycle thesis needs the
      same volume/clustering test that INTC got
- [ ] Remaining eight tickers through the Module A–E drill-down
- [ ] AVGO is **blocked** — the old vendor feed ended 1 June. yfinance should fix this;
      confirm during step 2

---

## 6 · Next build phase

Order matters here — the verification harness is the bug detector, so it exists before
any modelling.

- [ ] Wire per-ticker + per-regime backtest records into a searchable store
- [ ] Report edges as a **distribution**, never a basket average
      (`benchmarks.per_ticker_distribution` already returns this)
- [ ] **Volatility forecast** (14-week) — most tractable target; must beat a
      trailing-13-week-vol baseline
- [ ] Quantile / range forecast — calibration curve, not point estimates
- [ ] Cross-sectional ranking — mean Spearman IC across purged folds
- [ ] Directional model **last**, with an always-long baseline. If it doesn't beat that,
      record the negative result and stop

Reminder on sample size: 104 weeks contains ~7 **non-overlapping** 14-week windows per
ticker. Overlapping windows inflate n without adding information — use purged walk-forward
CV with a 14-week embargo and pool across tickers.

---

## Nice-to-have

- [ ] Populate ticker metadata (company name, sector) — `_meta_stub()` in `cli.py` is a
      placeholder, so cards render with blank names
- [ ] Golden fixtures for NSE/BSE tickers, to validate the `.NS` / `.BO` path
- [ ] Correlation matrix + pair-ratio z-scores into the dashboard (functions exist in
      `features/indicators.py`, not yet rendered)
- [ ] `examples/` notebook reproducing the semiconductor study end-to-end
- [ ] PyPI release once the live pull is confirmed working

---

## Reference

| Path | What |
|---|---|
| `docs/finance_app_logic.md` | Architecture spec, nine documented pitfalls, scope of prior results |
| `docs/tracker_style.md` | Midnight Slate design system |
| `docs/analysis_deep.md` | Per-ticker drill-down method, INTC worked example |
| `tests/fixtures/golden_2026_07_31.json` | Eleven verified closes + YTD returns |
| `../semiconductor_dashboard.html` | The 3 Aug analysis this was extracted from |

**Design invariants worth not breaking:**
104 weeks is a hard floor · decisions use bars strictly before the decision date ·
unavailable indicators score 0, never a silent negative · failing tickers are quarantined,
never forward-filled · entry and exit sizing stay symmetric by default.
