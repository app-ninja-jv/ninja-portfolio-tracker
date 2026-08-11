# Midnight Slate

Dark blue-slate theme for data-dense analytical dashboards. Lineage is a trading terminal rather
than a consumer web app.

The CSS is defined once, in `src/tracker/render/theme.py`. That file is the source of truth; this
document records the decisions behind it.

## Palette

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#141a26` | Page |
| `--surface` | `#1b2331` | Cards |
| `--surface-2` | `#1e2839` | Raised elements, table headers |
| `--inset` | `#161d2a` | Recessed wells |
| `--border` | `#2b3648` | Dividers |
| `--border-soft` | `#232d3e` | Internal rules |
| `--text` | `#e6edf6` | Primary |
| `--text-dim` | `#c3cfdd` | Secondary |
| `--muted` | `#94a3b8` | Labels |
| `--faint` | `#6b7a90` | Axis ticks, footnotes |
| `--pos` | `#4ade80` | Gain |
| `--neg` | `#f87171` | Loss |
| `--accent` | `#60a5fa` | Selection, links, primary series |
| `--warn-bg` / `--warn-border` / `--warn-rule` / `--warn-text` | `#241c14` / `#8a5a24` / `#d97706` / `#fcd9a0` | Data-quality banners |

## Rules

**Elevation by lightness, not shadow.** Depth comes from the four surface tokens. No drop shadows,
no gradients: they add visual noise at the density this renders at.

**Colour is semantic only.** Green and red mean gain and loss and nothing else. Non-money metrics
get a separate ramp — extension vs a moving average uses `.below` (`--accent`), `.stretch`
(`#fbbf24`, >25%) and `.hot` (`#fb923c`, >50%), so a positive number is never rendered in red.
See `ext_class()`.

**Tabular numerals everywhere.** `font-variant-numeric:tabular-nums` on every figure. Digits must
align down a column and must not jitter between renders.

**Lead with the caveat.** Data-quality warnings render in a banner above the first table, never in a
footer.

**Evidence over verdicts.** "+52% above the 26w MA, U/D volume 0.9, three distribution weeks in the
last six" is more useful than "SELL". The score summarises the evidence; it does not replace it.

## Components

`.card` · `.chead` · `.cgrid` / `.metric` (label + value wells) · `.pill` (verdict, tinted by call) ·
`.warn` (quality banner) · `.volwrap` (inline SVG volume bars) · `.tabs` (ticker switcher).
