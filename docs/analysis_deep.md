# Deep-dive analysis spec + findings log

Per-ticker drill-down that layers underneath the summary dashboard. One entry per ticker,
appended over time, designed to stack into an interactive per-ticker drill-down view.

**Status:** INTC complete (3 Aug 2026). Nine remaining — see [Backlog](#backlog).

---

## Contents

- [How to run it](#how-to-run-it)
- [Threshold calibration — read before comparing tickers](#threshold-calibration)
- [Module A — Volume & sell-off analysis](#module-a--volume--sell-off-analysis)
- [Module B — Volatility trend](#module-b--volatility-trend)
- [Module C — Price shockers](#module-c--price-shockers)
- [Module D — Catalysts & deals](#module-d--catalysts--deals)
- [Module E — Verdict layer](#module-e--verdict-layer)
- [Summary roll-up format](#summary-roll-up-format)
- [Findings log: INTC](#findings-log-intc)
- [Dashboard integration](#dashboard-integration)
- [Data caveats](#data-caveats)
- [Backlog](#backlog)

---

## How to run it

**Data required:** weekly OHLCV, minimum 2 calendar years so the prior year is a complete
comparison period.

```
https://stockanalysis.com/api/symbol/s/<ticker>/history?range=5Y&period=Weekly
```

Returns ~130 weekly bars (~2.5 years). The `range` parameter is unreliable — it returns
roughly half what you ask for — so always request `5Y` even when you want 2. Append the last
1–2 weeks from the `range=2Y` call, which sometimes runs fresher.

**Script:** `outputs/intc_deep.py` — swap the `W` list for the new ticker's bars, everything
downstream is generic. Bars are `(week_start, high, low, close, volume)`, newest first.

**Comparison periods:** prior full calendar year vs current year-to-date. Always report the
YTD week count and normalise event counts *per 10 weeks* — raw counts across a 52-week year
and a 29-week partial year are not comparable.

---

## Threshold calibration

**This is the most important methodological point in the document.**

A fixed ±5% weekly threshold is not comparable across this basket. TXN has 40% annualised
volatility and SNDK has 106% — the same 5% move is a routine week for one and barely noise for
the other. Run the fixed threshold with a vol-normalised threshold alongside it.

Weekly sigma = annualised vol ÷ √52. Suggested per-ticker thresholds:

| Ticker | Ann. vol | Weekly σ | 1.5σ threshold | 2.0σ threshold |
|---|---|---|---|---|
| NVDA | 30.5% | 4.22% | 6.3% | 8.4% |
| AVGO | 42.6% | 5.91% | 8.9% | 11.8% |
| MU | 73.7% | 10.23% | 15.3% | 20.5% |
| SNDK | 105.6% | 14.64% | 22.0% | 29.3% |
| AMD | 67.4% | 9.35% | 14.0% | 18.7% |
| INTC | 77.4% | 10.73% | 16.1% | 21.5% |
| ASML | 40.1% | 5.56% | 8.3% | 11.1% |
| AMAT | 49.3% | 6.84% | 10.3% | 13.7% |
| TXN | 40.2% | 5.58% | 8.4% | 11.2% |
| ARM | 85.6% | 11.87% | 17.8% | 23.7% |

**Report both.** The fixed 5% count answers "how often did this move a lot in absolute terms" —
which is what matters for position sizing. The 1.5σ count answers "how often did this move a lot
*for itself*" — which is what matters for cross-ticker comparison. Label every chart with which
one it uses.

The same applies to the monthly range test. A >10% monthly high-low range flagged **12/12 months
in 2025 and 7/7 in 2026 for INTC** — the threshold has zero discriminating power on a volatile
name. Use the *average* monthly range as the headline number and reserve threshold counts for
low-volatility names like TXN and ASML, or scale the threshold to 2× weekly σ.

---

## Module A — Volume & sell-off analysis

Answers: *is the selling committed, and is it clustering?*

| Metric | Definition |
|---|---|
| Sell-off week | Close ≤ −5% vs prior week (also run at −1.5σ) |
| Sell-off rate | Sell-off weeks ÷ total weeks × 10 |
| Distribution week | Sell-off week **and** volume higher than prior week |
| Capitulation week | Sell-off week **and** volume ≥ +25% vs prior week |
| Rally week | Close ≥ +5% vs prior week |
| Volume down/up 5%+ | Weekly volume change vs prior week, both directions |
| Avg / median weekly volume | Median matters more — it resists earnings-week spikes |
| U/D volume ratio (8w) | Σ up-week volume ÷ Σ down-week volume, trailing 8 weeks. >1 accumulation, <1 distribution |
| **Clustering** | Are distribution weeks recent and consecutive, or scattered? |

**Clustering is the signal, not the count.** Three distribution weeks spread across a year is
noise. Three in the last six weeks is a change in who owns the stock. Always list every
sell-off week individually with its date and volume change — the pattern is invisible in a
summary count.

**Interpreting the volume-down count:** raw "volume down 5%+ vs prior week" is close to
symmetric with volume-up in a normal regime (INTC 2025: 24 vs 24; 2026: 12 vs 13). It's a
noise metric on its own. It becomes informative only when crossed with price direction.

---

## Module B — Volatility trend

Answers: *is this the same instrument it was last year, and what position size does it justify now?*

| Metric | Definition |
|---|---|
| Annualised volatility | σ of weekly returns × √52 |
| Avg absolute weekly move | Mean of \|weekly % change\| — more intuitive than σ |
| Best / worst week | Tail magnitude, both directions |
| Max drawdown in period | Peak-to-trough on weekly closes, within the calendar period |
| Monthly hi-lo range | (month high − month low) ÷ month low, from weekly highs/lows |
| Avg monthly range | **Headline volatility number** — most legible to a human |
| Widest month | With the month labelled, so it can be tied to a catalyst |
| **Vol regime ratio** | Current-year vol ÷ prior-year vol |
| **Implied size adjustment** | 1 ÷ vol regime ratio — the position multiplier for constant risk |

The size adjustment is the actionable output. INTC's vol went 62% → 86%, a ratio of 1.39, so
the same dollar risk now supports roughly **0.72× the 2025 position**. That is a trim
justification that requires no directional view at all, and it's worth separating from the
bull/bear argument every time.

---

## Module C — Price shockers

Answers: *what actually moved this stock, and was the move bought or sold?*

Tabulate every week beyond the threshold with **date, price change, volume change, and a
same-week catalyst** where one can be identified. Track:

- Shock asymmetry — count and average magnitude, up vs down
- Whether the largest moves are up or down (leadership tell)
- Whether shocks cluster around earnings or arrive between them (sector-driven vs company-driven)
- Follow-through: did the week after a shock extend or reverse it?

For INTC 2026, upside shocks outnumbered downside 12 to 7 and were larger — a detail that
argued *against* the trim call and belongs in the record precisely for that reason.

---

## Module D — Catalysts & deals

The qualitative layer. Everything else is price and volume; this is why.

| Field | What to capture |
|---|---|
| Reported quarters | Revenue, EPS, YoY growth, vs consensus |
| Segment inflection | Which division is driving or dragging, with numbers |
| Guidance change | Raised, cut, maintained — and the market's reaction |
| Deals / customers / partnerships | Named counterparties where disclosed |
| Product / process milestones | Node ramps, design wins, certifications |
| **The unproven part** | The single load-bearing assumption the thesis rests on |
| Positioning | Short interest % float, insider activity |

"The unproven part" is the field that does the most work. For INTC it is that external
customers are ~5% of foundry revenue — everything else about the turnaround can be true and
the thesis still fails there.

---

## Module E — Verdict layer

Every drill-down ends with four items, in this order:

1. **The call** — Add / Hold / Trim / Reduce, and whether it is *directional* or *risk-managed*.
   These are different claims and conflating them is the most common analytical error here.
2. **Evidence for**
3. **Evidence against** — mandatory, never empty. If a module produced a finding that weakens
   the call, it goes here explicitly.
4. **What would change my mind** — a specific, observable, falsifiable trigger. Not "if
   fundamentals deteriorate" but "a −5% week on volume +25% that fails to make a new low."

---

## Summary roll-up format

Each ticker compresses to one card for the stacked view:

```
TICKER  |  CALL (directional | risk-managed)  |  confidence
─────────────────────────────────────────────────────────────
Regime:      vol XX% → YY%  (ratio Z.ZZ, size multiplier M.MM×)
Sell-offs:   N per 10wk  (prior year: M)  |  D distribution, C capitulation
Clustering:  [recent / scattered / none]
Shockers:    U up / D down  |  largest: ±X.X% week of YYYY-MM-DD
Catalyst:    <one line — most recent quarter or event>
Unproven:    <the single load-bearing assumption>
Trigger:     <what would flip the call>
```

---

## Findings log: INTC

**Run date:** 3 August 2026 · **Data:** weekly bars through 2026-07-20 · **Call:** TRIM (risk-managed, not directional)

### Headline comparison

| Metric | 2025 (52 wks) | 2026 YTD (29 wks) |
|---|---|---|
| Close, start → end | $19.15 → $39.38 | $45.55 → $92.32 |
| Period return, weekly basis | +105.6% | +102.7% |
| **Official return, exact calendar** | **≈ +84%** | **+144.4%** |
| Low / high | $17.66 / $44.02 | $38.95 / $142.35 |
| Max drawdown in period | −23.9% | **−31.1%** |
| Annualised volatility | 62% | **86%** |
| Avg absolute weekly move | 6.3% | **10.1%** |
| Best / worst week | +23.6% / −13.0% | +25.6% / −13.5% |

2026 delivered 2025's entire return in 29 weeks instead of 52, at 1.4× the volatility.

### Module A — Volume & sell-off

| Event | 2025 | per 10wk | 2026 YTD | per 10wk |
|---|---|---|---|---|
| Sell-off weeks (−5%+) | 10 | 1.9 | 7 | **2.4** |
| — on rising volume | 5 | — | 3 | — |
| — on volume +25%+ | **5** | — | **0** | — |
| Rally weeks (+5%+) | 11 | 2.1 | 12 | **4.1** |
| Volume down 5%+ | 24 | 4.6 | 12 | 4.1 |
| Volume up 5%+ | 24 | 4.6 | 13 | 4.5 |
| Avg weekly volume | 480M | — | **578M** | — |
| Median weekly volume | 421M | — | **582M** | — |

Median weekly volume rose 38% (421M → 582M) — sustained, not spike-driven.

**Every −5% week in 2026:**

| Week | Price | Volume | |
|---|---|---|---|
| Feb 9 | −7.5% | −20.9% | |
| Feb 17 | −5.7% | −36.0% | |
| May 11 | −12.9% | −12.7% | |
| Jun 1 | −13.5% | +18.8% | ← rising |
| Jul 6 | −8.7% | +9.0% | ← rising |
| Jul 13 | −13.5% | +8.2% | ← rising |
| Jun 29 | −6.2% | −21.4% | |

**Clustering: strong.** All three rising-volume declines are the three most recent, clustered
June–July. Every earlier 2026 decline came on *falling* volume — drift, not selling. This is
what the 0.42 U/D ratio was detecting.

**2025 for contrast:** 5 of 10 sell-offs on rising volume, all five with volume +25%+, scattered
across January, March, July, November and December — episodic panic rather than a regime.

### Module B — Volatility trend

| Metric | 2025 | 2026 YTD |
|---|---|---|
| Months with hi-lo range >10% | 12/12 | 7/7 |
| Avg monthly range | 30.2% | **44.5%** |
| Widest month | 60.8% (Sep) | **101.4% (Apr)** |

April 2026 spanned $49.87 to $100.45 in a single month.

Monthly ranges: 2025 — Jan 19.6, Feb 46.7, Mar 36.9, Apr 23.0, May 18.5, Jun 20.7, Jul 26.8,
Aug 37.1, Sep 60.8, Oct 22.5, Nov 23.4, Dec 26.0.
2026 — Jan 40.2, Feb 20.1, Mar 24.3, Apr 101.4, May 38.9, Jun 44.8, Jul 42.1.

**Vol regime ratio 1.39 → size multiplier 0.72×.**

### Module C — Price shockers

Upside shocks outnumber downside **12 to 7** and are marginally larger (+25.6% vs −13.5%
extremes). Largest single weeks: +25.6% (Jun 8), +25.4% (May 4), +23.8% (Apr 6), +20.7% (Apr 27),
+20.5% (Apr 20) — a dense April–June upside cluster, then the July reversal.

### Module D — Catalysts & deals

| Field | Detail |
|---|---|
| Q2 2026 revenue | $16.1B, +25% YoY from $12.9B — best growth in 15+ years |
| Q2 2026 non-GAAP EPS | $0.42 vs ~$0.21 expected |
| Data Center & AI | $6.3B, +59% YoY |
| Client Computing | $8.9B, +13% YoY |
| Foundry revenue | $5.8B, +31% YoY |
| Foundry operating loss | −$2.1B (−36.2% margin) vs −$3.2B (−71.7%) in Q2 2025 |
| Process milestone | 18A in high-volume production; 18A-P in risk production; Panther Lake shipping |
| Equipment | Running ASML High NA EUV in production |
| **The unproven part** | **External customers ≈5% of foundry segment revenue** |
| Sector event | Down ~21% during July 2026 semiconductor selloff |

### Module E — Verdict

**Call: TRIM — risk-managed, not directional.**

*For:* volatility 62% → 86%; avg monthly range 30% → 44.5%; three consecutive rising-volume
declines clustered June–July; −31% from the high; 18A external adoption at ~5% of foundry revenue.

*Against:* rally weeks now outnumber sell-offs 12 to 7 (4.1 vs 2.4 per 10wk) where 2025 was
near-even; **zero capitulation-volume sell-offs in 2026 versus five in 2025** — no forced
selling has occurred; fundamentals are the most improved in the basket.

*What would change my mind:* a −5% week on volume ≥ +25% that then **fails to make a new low** —
capitulation followed by absorption, a pattern INTC has not printed all year. Or external
foundry customers moving materially above 5% of segment revenue on the next report.

---

## Dashboard integration

Target: click a ticker in the summary table → expand to the five modules.

- **Style:** reuse `tracker_style.md`. Modules become `.card` blocks; the roll-up becomes a
  `.cgrid` of `.metric` wells; the verdict uses `.vbox` tinted by call.
- **Comparison bars:** prior year vs YTD as paired horizontal bars, always per-10-week
  normalised. Label the threshold basis (fixed 5% or 1.5σ) on every chart.
- **Sell-off timeline:** one mark per sell-off week along a date axis, filled where volume rose,
  hollow where it fell. Clustering becomes visible instantly — this is the highest-value visual
  in the whole drill-down.
- **Monthly range:** small multiples, one bar per month, two years stacked for comparison.
- **Cross-ticker view:** once several tickers are logged, a matrix of vol regime ratio ×
  sell-off clustering will rank the basket by deteriorating market structure independently of
  fundamentals.
- Chart.js, Grid.js and Mermaid are available from CDN if the view becomes a live artifact.

---

## Data caveats

1. **Weekly bars, not daily.** Intra-week sell-offs that recover by Friday are invisible.
   Monthly hi-lo ranges are built from weekly highs/lows, so they slightly understate true
   intra-month range.
2. **Week labels are week-start dates**, so a bar labelled `2025-12-29` closes on 2 Jan 2026.
   This is why weekly-basis annual returns differ from exact-calendar returns — INTC shows
   +105.6% on weekly bars versus ≈+84% on exact calendar dates for 2025. **Always report the
   exact-calendar figure as the headline** and use weekly-basis only for event counting.
3. **Vendor snapshot inconsistency.** The `5Y` and `2Y` pulls returned different close and
   volume values for the overlapping week of 2026-07-06 ($110.24/327M vs $109.84/503M). The
   most recent week in any pull may be partial. Prefer the fresher pull for overlaps and
   discard the final bar if it looks partial.
4. **Threshold sensitivity.** Every count in Module A depends on the ±5% choice. Re-running at
   1.5σ will produce materially different counts. Never compare a fixed-threshold count for one
   ticker against a σ-based count for another.
5. **2026 is a partial year** (29 of ~52 weeks) and is weighted toward a violent H1. Per-10-week
   normalisation helps but does not remove seasonality.

---

## Backlog

| Ticker | Status | Note |
|---|---|---|
| INTC | ✅ 3 Aug 2026 | Worked example |
| MU | ☐ | Highest priority — peak-cycle thesis needs the same volume test |
| SNDK | ☐ | Expect extreme counts; use 1.5σ (22.0%) not 5% |
| NVDA | ☐ | Test whether decoupling shows up in shock timing vs the sector |
| AMD | ☐ | Pair with NVDA; the +1.90σ ratio needs an event-level explanation |
| ASML | ☐ | Low vol — fixed 5% threshold may return near-zero; use 1.5σ (8.3%) |
| AMAT | ☐ | Compare shock dates against ASML to test the +2.55σ pair |
| TXN | ☐ | Low vol; expect few events, which is itself the finding |
| ARM | ☐ | −45% drawdown — look for the capitulation week that hasn't appeared |
| AVGO | ☐ | **Blocked** — vendor weekly data ends 1 Jun 2026, needs a fresher source |

---

*Spec v1, 3 August 2026. Scripts: `outputs/intc_deep.py`, `outputs/compute.py`. Style: `tracker_style.md`.*
