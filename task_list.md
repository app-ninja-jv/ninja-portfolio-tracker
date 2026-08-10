# Task list — equity-tracker

Picking up 12 August 2026. Repo is built, tested and committed locally at
`~/Side_projects/equity-tracker`. Nothing is pushed to GitHub yet.

**State:** 42 source files · 35 tests passing · ruff clean · one local commit (`fb56908`)

---

## Do first — one command, blocks everything else

The initial commit is **missing `src/tracker/data/`**. A bare `data/` in `.gitignore`
matched `src/tracker/data/` as well as the intended cache directory. The pattern is
already fixed on disk (`/data/`); the commit just needs redoing. The sandbox couldn't
clear git's lock files, so this has to run locally.

```bash
cd ~/Side_projects/equity-tracker
rm -f .git/index.lock .git/HEAD.lock
git add -A
git commit --amend --no-edit
git ls-files src/tracker/data/        # must list 4 files
```

- [ ] Amend the commit so the data layer is tracked

---

## 1 · Local verification, before anything is public

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[live,dev]"
pytest                                # 35 passing, no network needed
python examples/quickstart.py         # end-to-end on synthetic data
```

- [ ] `pytest` green
- [ ] `quickstart.py` writes `build/quickstart.html` and opens correctly

---

## 2 · First real yfinance pull — the moment of truth

```bash
tracker fetch --tickers NVDA,AMD,INTC,ASML,TXN,AMAT,MU,QCOM,ARM,AVGO --weeks 104
tracker doctor
```

`doctor` compares against `tests/fixtures/golden_2026_07_31.json` — eleven independently
verified 31 July closes. **If NVDA doesn't return $200.75 ±0.5%**, it's one of three things,
in order of likelihood:

| Symptom | Cause | Fix |
|---|---|---|
| Every indicator shifted by one period | Week labelled by period **end**, not start | `_monday()` in `data/fetch.py` |
| A ticker shows a phantom ~50% crash | Raw close used where adjusted belongs | `auto_adjust` handling in `_frame_to_bars()` |
| Only the final bar is wrong | Timezone drift | Normalise to UTC before `_monday()` |

- [ ] `tracker fetch` completes, quality gate reports per ticker
- [ ] `tracker doctor` passes all 11 golden values
- [ ] Fix any week-labelling / adjustment issue found

---

## 3 · Full pipeline on live data

```bash
tracker score
tracker report --out build/index.html
tracker verify --report build/index.html
tracker backtest --mode allocation --start 2026-02-02 --json-out build/backtest.json
open build/index.html
```

- [ ] Dashboard renders with all tickers, tabs and volume charts
- [ ] `verify` clean
- [ ] Backtest prints benchmarks, bucket test and regime tag
- [ ] Sanity-check a couple of scores by hand against the 3 Aug analysis

---

## 4 · Publish

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
