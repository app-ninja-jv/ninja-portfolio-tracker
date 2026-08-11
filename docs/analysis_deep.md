# Per-ticker drill-down method

Five modules run beneath the summary dashboard, one record per ticker, appended over time. Inputs
are weekly OHLCV from the cache, minimum two calendar years so the prior year forms a complete
comparison period.

Comparison is prior full calendar year against current year-to-date. Report the YTD week count and
normalise event counts **per 10 weeks**; raw counts across a 52-week year and a 29-week partial year
are not comparable.

---

## Threshold calibration

A fixed ±5% weekly threshold is not comparable across a basket. At 40% annualised volatility a 5%
week is routine; at 106% it is noise. Weekly σ = annualised vol ÷ √52.

| Ticker | Ann. vol | Weekly σ | 1.5σ | 2.0σ |
|---|---|---|---|---|
| NVDA | 30.5% | 4.22% | 6.3% | 8.4% |
| ASML | 40.1% | 5.56% | 8.3% | 11.1% |
| TXN | 40.2% | 5.58% | 8.4% | 11.2% |
| AVGO | 42.6% | 5.91% | 8.9% | 11.8% |
| AMAT | 49.3% | 6.84% | 10.3% | 13.7% |
| AMD | 67.4% | 9.35% | 14.0% | 18.7% |
| MU | 73.7% | 10.23% | 15.3% | 20.5% |
| INTC | 77.4% | 10.73% | 16.1% | 21.5% |
| ARM | 85.6% | 11.87% | 17.8% | 23.7% |
| SNDK | 105.6% | 14.64% | 22.0% | 29.3% |

Report both bases. Fixed-% answers how often a name moved a lot in absolute terms, which governs
position sizing. σ-normalised answers how often it moved a lot for itself, which governs
cross-ticker comparison. Label every chart with its basis.

The same applies to the monthly range test. A >10% monthly high-low range flagged 12/12 months in
2025 and 7/7 in 2026 for INTC: no discriminating power on a volatile name. Use average monthly range
as the headline and reserve threshold counts for low-volatility names, or scale to 2× weekly σ.

---

## Module A — Volume and sell-off

Is the selling committed, and is it clustering?

| Metric | Definition |
|---|---|
| Sell-off week | Close ≤ −5% vs prior week (also run at −1.5σ) |
| Sell-off rate | Sell-off weeks ÷ total weeks × 10 |
| Distribution week | Sell-off week with volume higher than prior week |
| Capitulation week | Sell-off week with volume ≥ +25% vs prior week |
| Rally week | Close ≥ +5% vs prior week |
| Avg / median weekly volume | Median resists earnings-week spikes |
| U/D volume ratio (8w) | Σ up-week volume ÷ Σ down-week volume. >1 accumulation, <1 distribution |
| Clustering | Are distribution weeks recent and consecutive, or scattered? |

Clustering is the signal, not the count. Three distribution weeks across a year is noise; three in
the last six weeks is a change in ownership. List every sell-off week individually with date and
volume change — the pattern is invisible in a summary count.

Raw "volume down 5%+" is near-symmetric with volume-up in a normal regime (INTC 2025: 24 vs 24;
2026: 12 vs 13). It is informative only when crossed with price direction.

---

## Module B — Volatility trend

Is this the same instrument it was last year, and what position size does it justify now?

| Metric | Definition |
|---|---|
| Annualised volatility | σ of weekly returns × √52 |
| Avg absolute weekly move | Mean of \|weekly % change\| |
| Best / worst week | Tail magnitude, both directions |
| Max drawdown in period | Peak-to-trough on weekly closes |
| Avg monthly range | Headline volatility number; (high − low) ÷ low from weekly highs/lows |
| Widest month | Labelled, so it ties to a catalyst |
| Vol regime ratio | Current-year vol ÷ prior-year vol |
| Implied size adjustment | 1 ÷ vol regime ratio, the multiplier for constant risk |

The size adjustment is the actionable output and requires no directional view. INTC vol moved
62% → 86%, ratio 1.39, so the same dollar risk supports 0.72× the prior position. Keep this separate
from the bull/bear argument.

---

## Module C — Price shockers

What moved the name, and was the move bought or sold? Tabulate every week beyond threshold with
date, price change, volume change and same-week catalyst. Track shock asymmetry (count and average
magnitude, up vs down), whether the largest moves are up or down, whether shocks cluster around
earnings or arrive between them, and follow-through in the subsequent week.

For INTC 2026 upside shocks outnumbered downside 12 to 7 and were larger, which argued against the
trim call and belongs in the record for that reason.

---

## Module D — Catalysts

| Field | Capture |
|---|---|
| Reported quarters | Revenue, EPS, YoY growth, vs consensus |
| Segment inflection | Which division drives or drags, with numbers |
| Guidance change | Raised, cut, maintained, and the reaction |
| Deals and customers | Named counterparties where disclosed |
| Product milestones | Node ramps, design wins, certifications |
| The unproven part | The single load-bearing assumption |
| Positioning | Short interest % float, insider activity |

"The unproven part" does the most work. For INTC it is that external customers are ~5% of foundry
revenue: everything else about the turnaround can hold and the thesis still fails there.

---

## Module E — Verdict

Four items, in order.

1. **The call** — Add / Hold / Trim / Reduce, and whether it is *directional* or *risk-managed*.
   These are different claims; conflating them is the most common error in this method.
2. **Evidence for.**
3. **Evidence against** — mandatory, never empty.
4. **What would change the call** — specific, observable, falsifiable. Not "if fundamentals
   deteriorate" but "a −5% week on volume +25% that fails to make a new low."

### Roll-up format

```
TICKER  |  CALL (directional | risk-managed)  |  confidence
─────────────────────────────────────────────────────────────
Regime:      vol XX% → YY%  (ratio Z.ZZ, size multiplier M.MM×)
Sell-offs:   N per 10wk  (prior year: M)  |  D distribution, C capitulation
Clustering:  [recent / scattered / none]
Shockers:    U up / D down  |  largest: ±X.X% week of YYYY-MM-DD
Catalyst:    <most recent quarter or event>
Unproven:    <the load-bearing assumption>
Trigger:     <what would flip the call>
```

---

## Worked example: INTC

Run 3 August 2026, weekly bars through 2026-07-20. **Call: TRIM, risk-managed, not directional.**

| Metric | 2025 (52 wks) | 2026 YTD (29 wks) |
|---|---|---|
| Close, start → end | $19.15 → $39.38 | $45.55 → $92.32 |
| Return, exact calendar | ≈ +84% | +144.4% |
| Max drawdown in period | −23.9% | −31.1% |
| Annualised volatility | 62% | 86% |
| Avg absolute weekly move | 6.3% | 10.1% |
| Avg monthly range | 30.2% | 44.5% |
| Sell-off weeks per 10wk | 1.9 | 2.4 |
| — on rising volume | 5 of 10 | 3 of 7 |
| — on volume +25%+ | 5 | 0 |
| Rally weeks per 10wk | 2.1 | 4.1 |
| Median weekly volume | 421M | 582M |

2026 delivered 2025's entire return in 29 weeks at 1.4× the volatility. Median volume rose 38%,
sustained rather than spike-driven.

Every −5% week in 2026:

| Week | Price | Volume | |
|---|---|---|---|
| Feb 9 | −7.5% | −20.9% | |
| Feb 17 | −5.7% | −36.0% | |
| May 11 | −12.9% | −12.7% | |
| Jun 1 | −13.5% | +18.8% | rising |
| Jun 29 | −6.2% | −21.4% | |
| Jul 6 | −8.7% | +9.0% | rising |
| Jul 13 | −13.5% | +8.2% | rising |

**Clustering: strong.** The three rising-volume declines are the three most recent, clustered
June–July. Every earlier 2026 decline came on falling volume, which is drift rather than selling.
2025 for contrast: 5 of 10 sell-offs on rising volume, all five at volume +25%+, scattered across
five separate months — episodic panic, not a regime.

*Against the call:* rally weeks now outnumber sell-offs 4.1 to 2.4 per 10 weeks where 2025 was
near-even, and there were zero capitulation-volume sell-offs in 2026 against five in 2025, so no
forced selling has occurred. Q2 2026 revenue $16.1B, +25% YoY, was the strongest growth in 15 years.

*Trigger:* a −5% week on volume ≥ +25% that then fails to make a new low — capitulation followed by
absorption, a pattern absent all year. Or external foundry customers moving materially above 5% of
segment revenue.

---

## Caveats

1. **Weekly bars, not daily.** Intra-week sell-offs that recover by Friday are invisible. Monthly
   ranges built from weekly highs/lows understate true intra-month range.
2. **Week labels are week-start dates**, so a bar labelled `2025-12-29` closes 2 Jan 2026. Weekly-
   basis annual returns therefore differ from exact-calendar returns: INTC shows +105.6% on weekly
   bars against ≈+84% on calendar dates for 2025. Report exact-calendar as the headline; use
   weekly-basis only for event counting.
3. **Vendor snapshot inconsistency.** Overlapping pulls returned different close and volume for
   2026-07-06 ($110.24/327M vs $109.84/503M). Prefer the fresher pull; discard a partial final bar.
4. **Threshold sensitivity.** Every Module A count depends on the ±5% choice. Never compare a
   fixed-threshold count for one ticker against a σ-based count for another.
5. **Partial years** are weighted toward whatever happened in H1. Per-10-week normalisation helps
   but does not remove seasonality.

---

## Backlog

| Ticker | Status | Note |
|---|---|---|
| INTC | done, 3 Aug 2026 | Worked example above |
| MU | open | Highest priority; peak-cycle thesis needs the same volume test |
| SNDK | open | Expect extreme counts; use 1.5σ (22.0%), not 5% |
| NVDA | open | Test whether decoupling shows in shock timing vs the sector |
| AMD | open | Pair with NVDA; the +1.90σ ratio needs an event-level explanation |
| ASML | open | Low vol; fixed 5% returns near-zero, use 1.5σ (8.3%) |
| AMAT | open | Compare shock dates against ASML to test the +2.55σ pair |
| TXN | open | Low vol; few events is itself the finding |
| ARM | open | −45% drawdown; look for the capitulation week that has not appeared |
| AVGO | blocked | Prior vendor feed ended 1 Jun 2026; confirm yfinance resolves it |
