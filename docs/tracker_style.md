# Midnight Slate — tracker/dashboard style guide

A reusable dark theme for data-dense trackers and analytical dashboards. Extracted from
`semiconductor_dashboard.html`. Drop the CSS block at the bottom into any single-file HTML page
and the component classes below will work as-is.

---

## What the theme is

**Midnight Slate** — a *dark blue-slate quant terminal* theme. The lineage is Bloomberg / trading
terminal rather than consumer web app. Its defining decisions:

| Decision | Why |
|---|---|
| **Blue-slate, not pure black** | Backgrounds carry a blue cast (`#141a26`) rather than neutral grey. Reads as "financial instrument" and is easier on the eyes over long sessions than near-black. |
| **Elevation by lightness, not shadow** | Depth comes from four stepped surface tones plus 1px hairline borders. No drop shadows anywhere. Flat, dense, precise. |
| **Data speaks, chrome recedes** | Numbers are the brightest thing on the page. Labels are small, uppercase, letter-spaced and dim. Chart junk and decorative colour are absent. |
| **Tabular numerals everywhere** | `font-variant-numeric: tabular-nums` so digits align in columns and changing values don't jitter. |
| **Colour is semantic only** | Green/red mean positive/negative. Amber means caution. Blue means reference. Colour is never decorative — if something is coloured, it carries meaning. |
| **High information density** | Tight padding (5–9px in tables), 12.5px table type, compact metric wells. Designed to fit a lot on screen without feeling cramped. |
| **System font stack** | No web fonts. Loads instantly, renders natively, works offline in a single file. |

Typographic signature: `-apple-system` at 14px/1.6 body, tight negative tracking on headings
(`-0.4px`), wide positive tracking on micro-labels (`+0.6` to `+0.9px`) — the contrast between
those two is what makes it feel like an instrument panel.

---

## Palette

All colours are CSS custom properties on `:root`, so retheming means editing one block.

### Surfaces — four steps of elevation

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#141a26` | Page background |
| `--surface` | `#1b2331` | Cards, callout blocks |
| `--surface-2` | `#1e2839` | KPI tiles, table row hover |
| `--inset` | `#161d2a` | Wells *inside* cards (metric boxes, code) |

Note `--inset` is darker than `--surface` — recessed elements go down, elevated ones go up.

### Borders

| Token | Hex | Use |
|---|---|---|
| `--border` | `#2b3648` | Card edges, section rules, table header rule |
| `--border-soft` | `#232d3e` | Interior dividers, table row separators |

### Text — four levels

| Token | Hex | Use |
|---|---|---|
| `--text` | `#e6edf6` | Primary values, headings |
| `--text-dim` | `#c3cfdd` | Body prose |
| `--muted` | `#94a3b8` | Labels, secondary cells |
| `--faint` | `#6b7a90` | Footnotes, n/a states |

### Semantic

| Token | Hex | Meaning |
|---|---|---|
| `--pos` | `#4ade80` | Positive / gain / above |
| `--neg` | `#f87171` | Negative / loss / below |
| `--accent` | `#60a5fa` | Links, reference rule on callouts |
| `--warn-rule` | `#d97706` | Caveat / stale-data left border |
| `--warn-bg` | `#241c14` | Caveat background |
| `--warn-text` | `#fcd9a0` | Caveat body text |

### Status pills — background / text / border

| Class | Colour family |
|---|---|
| `.buy` | green — `rgba(34,197,94,.14)` / `#4ade80` / `rgba(34,197,94,.35)` |
| `.hold` | slate — `rgba(148,163,184,.13)` / `#cbd5e1` / `rgba(148,163,184,.3)` |
| `.trim` | amber — `rgba(234,179,8,.13)` / `#fbbf24` / `rgba(234,179,8,.32)` |
| `.sell` | red — `rgba(239,68,68,.14)` / `#f87171` / `rgba(239,68,68,.35)` |

Pattern: 13–14% alpha fill, solid bright text, 30–35% alpha border. Reuse it for any new status.

---

## Type scale

| Element | Size | Weight | Tracking |
|---|---|---|---|
| `h1` | 26px | 600 | −0.4px |
| `h2` (section) | 17px | 600 | −0.2px, 1px bottom rule |
| `h4` (micro-label) | 12px | 600 | +0.9px, uppercase, muted |
| Body | 14px / 1.6 | 400 | — |
| Table cell | 12.5px | 400 | tabular-nums |
| Table header | 10px | 600 | +0.7px, uppercase |
| KPI value | 23px | 600 | −0.5px |
| Metric value | 15px | 600 | tabular-nums |
| Pill | 10px | 700 | +0.6px, uppercase |

---

## Components

| Class | What it is |
|---|---|
| `.wrap` | Page container — 1400px max, 32/24/80px padding |
| `.banner` | Full-width caveat at top. Amber, 3px left rule. For data limitations the reader must see. |
| `.warn` | Inline caveat inside a card. Same amber language, smaller. |
| `.kpis` / `.kpi` | Auto-fit KPI tile row, 168px min. `.l` label / `.v` value / `.n` note. |
| `.card` | Primary content block, 9px radius, 22px padding |
| `.chead` | Card header — flex, title left, status pill right |
| `.cgrid` / `.metric` | Compact metric wells inside a card, 105px min. `.ml` label / `.mv` value. |
| `.csplit` | Two-column card body, `1fr 1.3fr`, collapses at 900px |
| `.sblock` | Callout block with blue left rule — for findings and interpretation |
| `.verdict` / `.vbox` | Summary boxes, tinted by outcome (`.vbuy` / `.vhold` / `.vtrim`) |
| `.pill` | Status badge; add `.big` for card headers |
| `.cm` | Correlation-matrix cell — background set inline by a heat function |
| `.foot` | Method, limitations and sources block |

### Utilities

`.r` right-align · `.c` centre · `.b` bold · `.mut` muted · `.na` faint ·
`.pos` green · `.neg` red · `.tkr` bold identifier

### Heatmap helper

Continuous colour for matrix cells — green positive, red negative, alpha scaled by magnitude:

```python
def heat(v):
    if v is None: return "#1b2331"
    a = min(abs(v), 1.0)
    if v >= 0: return f"rgba(56,161,105,{0.10+0.60*a:.2f})"
    return f"rgba(197,48,48,{0.10+0.60*a:.2f})"
```

Cells get `border:1px solid var(--bg)` so the page colour acts as the grid line.

---

## Conventions worth keeping

1. **Lead with the caveat.** If the data has a limitation that changes how the numbers should be
   read, it goes in a `.banner` above the first table — not buried in a footer.
2. **Every dashboard ends with Method / Limitations / Sources.** Numbered limitations, plainly
   written, including the ones that are unflattering.
3. **Signed numbers carry their sign.** `+7.6%` not `7.6%`, so positive and negative scan instantly.
4. **Stale or partial data gets marked at the point of use**, not just globally — a `.warn` inside
   the specific card.
5. **Colour-code against the reader's interest, not the raw sign.** Extension above a moving average
   is *rising* but usually *bad news* for entry, so it inverts.

---

## Copy-paste CSS

```css
:root{
  --bg:#141a26; --surface:#1b2331; --surface-2:#1e2839; --inset:#161d2a;
  --border:#2b3648; --border-soft:#232d3e;
  --text:#e6edf6; --text-dim:#c3cfdd; --muted:#94a3b8; --faint:#6b7a90;
  --pos:#4ade80; --neg:#f87171; --accent:#60a5fa;
  --warn-bg:#241c14; --warn-border:#8a5a24; --warn-rule:#d97706; --warn-text:#fcd9a0;
  --radius:9px; --radius-sm:5px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
 font:14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1400px;margin:0 auto;padding:32px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.4px}
h2{font-size:17px;margin:44px 0 14px;padding-bottom:9px;border-bottom:1px solid var(--border);letter-spacing:-.2px}
h4{font-size:12px;text-transform:uppercase;letter-spacing:.9px;color:var(--muted);margin:0 0 9px}
.sub{color:var(--muted);font-size:13px;margin:0 0 4px}
.banner{background:var(--warn-bg);border:1px solid var(--warn-border);border-left:3px solid var(--warn-rule);
 padding:14px 18px;border-radius:var(--radius-sm);margin:22px 0;font-size:13px;line-height:1.65}
.banner b{color:#fbbf24}
.warn{background:var(--warn-bg);border-left:3px solid var(--warn-rule);padding:9px 13px;
 border-radius:4px;margin:0 0 14px;font-size:12px;color:var(--warn-text)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:22px 0}
.kpi{background:var(--surface-2);border:1px solid var(--border);border-radius:7px;padding:15px 17px}
.kpi .l{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);display:block;margin-bottom:5px}
.kpi .v{font-size:23px;font-weight:600;letter-spacing:-.5px}
.kpi .n{font-size:11px;color:var(--faint);display:block;margin-top:3px}
table{width:100%;border-collapse:collapse;font-size:12.5px;
 font-variant-numeric:tabular-nums;font-feature-settings:'tnum'}
th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:var(--muted);
 padding:9px 8px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap}
td{padding:9px 8px;border-bottom:1px solid var(--border-soft)}
tbody tr:hover{background:var(--surface-2)}
.r{text-align:right} .c{text-align:center} .b{font-weight:600}
.tkr{font-weight:700;color:#f1f5f9;letter-spacing:.3px}
.mut{color:var(--muted)} .na{color:var(--faint)}
.pos{color:var(--pos)} .neg{color:var(--neg)}
.pill{display:inline-block;padding:3px 10px;border-radius:11px;font-size:10px;
 font-weight:700;letter-spacing:.6px;text-transform:uppercase;white-space:nowrap}
.pill.big{font-size:11.5px;padding:5px 14px}
.buy{background:rgba(34,197,94,.14);color:var(--pos);border:1px solid rgba(34,197,94,.35)}
.hold{background:rgba(148,163,184,.13);color:#cbd5e1;border:1px solid rgba(148,163,184,.3)}
.trim{background:rgba(234,179,8,.13);color:#fbbf24;border:1px solid rgba(234,179,8,.32)}
.sell{background:rgba(239,68,68,.14);color:var(--neg);border:1px solid rgba(239,68,68,.35)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:22px;margin-bottom:18px}
.chead{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}
.ctkr{font-size:20px;font-weight:700;letter-spacing:-.3px}
.cbucket{margin-left:11px;color:var(--muted);font-size:12.5px}
.cgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:9px;margin-bottom:20px}
.metric{background:var(--inset);border:1px solid var(--border-soft);border-radius:var(--radius-sm);padding:9px 11px}
.ml{display:block;font-size:9.5px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin-bottom:3px}
.mv{font-size:15px;font-weight:600;font-variant-numeric:tabular-nums}
.csplit{display:grid;grid-template-columns:1fr 1.3fr;gap:30px}
@media(max-width:900px){.csplit{grid-template-columns:1fr}}
table.fin td{padding:5px 6px;font-size:12px;border-bottom:1px solid var(--border-soft)}
.callp{margin:0 0 12px;line-height:1.72;color:var(--text-dim)}
.riskp{margin:0;font-size:12.5px;color:var(--muted);padding-top:11px;border-top:1px solid var(--border-soft)}
.riskp b{color:#cbd5e1}
.soc{margin:0;font-size:12.5px;color:var(--muted);line-height:1.65}
.cm{text-align:center;font-size:11px;padding:7px 4px;border:1px solid var(--bg)}
th.rot{text-align:center;font-size:10px}
.sblock{background:var(--surface);border:1px solid var(--border);border-left:2px solid var(--accent);
 border-radius:6px;padding:16px 20px;margin-bottom:13px}
.sblock p{margin:0;color:var(--text-dim);font-size:13.2px;line-height:1.7}
.verdict{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:18px 0}
.vbox{border-radius:8px;padding:17px 19px;border:1px solid}
.vbuy{background:rgba(34,197,94,.07);border-color:rgba(34,197,94,.28)}
.vhold{background:rgba(148,163,184,.06);border-color:rgba(148,163,184,.22)}
.vtrim{background:rgba(234,179,8,.07);border-color:rgba(234,179,8,.26)}
.vbox h4{margin-bottom:8px} .vbox .tl{font-size:17px;font-weight:700;letter-spacing:.5px;margin-bottom:7px}
.vbox p{margin:0;font-size:12.5px;color:var(--muted);line-height:1.62}
.foot{margin-top:46px;padding-top:22px;border-top:1px solid var(--border);font-size:12px;color:var(--faint);line-height:1.75}
.foot a{color:var(--accent);text-decoration:none} .foot a:hover{text-decoration:underline}
.foot h4{margin-top:20px}
code{background:var(--inset);padding:1px 5px;border-radius:3px;font-size:11.5px;color:#a5b4fc}
```

---

## Tuning

The background is the one value most worth adjusting to taste. Keep the same blue hue
(~220°) and step the lightness — the other surfaces should move with it:

| Feel | `--bg` | `--surface` | `--surface-2` | `--inset` |
|---|---|---|---|---|
| Near-black (original) | `#0d0f13` | `#12161e` | `#141821` | `#0d1015` |
| **Current — dark blue-slate** | **`#141a26`** | **`#1b2331`** | **`#1e2839`** | **`#161d2a`** |
| Lighter blue-slate | `#1a2231` | `#212b3c` | `#253044` | `#1c2534` |
| Softest | `#1f2838` | `#273245` | `#2b374d` | `#212b3d` |

If you go lighter than the current row, lift `--border` toward `#33405a` so edges stay visible.

---

*Extracted 3 August 2026 from `semiconductor_dashboard.html`.*
