# Task list — equity-tracker

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

## 1 · Commit the Docker work + fixes

```bash
cd ~/Side_projects/equity-tracker
rm -f Makefile .git/index.lock
git add -A
git commit -m "Docker workflow; fix verify/report ticker-set mismatch"
```

- [ ] Committed

---

## 2 · UI tweaks

- [ ] (list to be filled in — in progress)

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
gh repo create equity-tracker --public --source=. --remote=origin --push
```

Then: **Settings → Pages → Source: GitHub Actions**

Run *Actions → Refresh dashboard → Run workflow* manually. It is `workflow_dispatch`
only by design. Let it go green **twice**, then uncomment the cron in
`.github/workflows/refresh.yml`.

- [ ] Repo created and pushed
- [ ] Pages source set to GitHub Actions
- [ ] Two clean manual workflow runs
- [ ] Cron enabled
- [ ] Site live at `https://jovi-maverick.github.io/equity-tracker/`

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
