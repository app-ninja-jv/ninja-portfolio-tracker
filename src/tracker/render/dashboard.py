"""Single-file HTML dashboard.

Output is self-contained: no server, no build step, no CDN. Opens offline and
hosts free on GitHub Pages.

UI principle from docs/tracker_style.md — surface EVIDENCE, not verdicts. The
score is a summary of the evidence, not a replacement for it.
"""
from __future__ import annotations

import json
from datetime import datetime

from ..features import indicators as ind
from .theme import CSS, TAB_JS, ext_class

VC = {"BUY": "buy", "HOLD": "hold", "TRIM": "trim", "SELL": "sell"}


def _n(x, d=2, suf="", plus=False):
    if x is None:
        return "<span class='na'>n/a</span>"
    s = f"{x:,.{d}f}"
    if plus and x > 0:
        s = "+" + s
    return s + suf


def _cl(x):
    if x is None:
        return ""
    return "pos" if x > 0 else ("neg" if x < 0 else "")


def volume_chart(bars: list[dict], weeks: int = 24) -> str:
    """Weekly volume bars coloured by that week's price direction."""
    seg = bars[-(weeks + 1):]
    if len(seg) < 3:
        return ""
    rows = [(seg[i]["date"], seg[i]["volume"], seg[i]["close"] >= seg[i - 1]["close"])
            for i in range(1, len(seg))][-weeks:]

    W, H, PAD_L, PAD_B, PAD_T = 520, 96, 4, 16, 8
    ph = H - PAD_B - PAD_T
    vmax = max(r[1] for r in rows) or 1
    avg = sum(r[1] for r in rows) / len(rows)
    slot = (W - PAD_L * 2) / len(rows)
    bw = max(3.0, slot * 0.68)

    rects = ""
    for i, (d, v, up) in enumerate(rows):
        h = max(1.0, v / vmax * ph)
        x = PAD_L + i * slot + (slot - bw) / 2
        y = PAD_T + ph - h
        fill = "var(--pos)" if up else "var(--neg)"
        rects += (f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="1" '
                  f'fill="{fill}" opacity="{0.85 if up else 0.80}">'
                  f'<title>{d}  {v/1e6:,.0f}M  {"up" if up else "down"} week</title></rect>')

    ay = PAD_T + ph - (avg / vmax * ph)
    n_up = sum(1 for r in rows if r[2])
    vu = sum(r[1] for r in rows if r[2])
    vd = sum(r[1] for r in rows if not r[2])
    ratio = vu / vd if vd else None
    rcls = "pos" if ratio and ratio >= 1 else "neg"

    return f"""
<div class="volwrap">
  <div class="volhead">
    <span class="ml">Weekly volume &middot; last {len(rows)} weeks</span>
    <span class="volstat">{n_up} up / {len(rows)-n_up} down &nbsp;&middot;&nbsp;
      U/D vol <b class="{rcls}">{f'{ratio:.2f}' if ratio else 'n/a'}</b>
      &nbsp;&middot;&nbsp; peak {vmax/1e6:,.0f}M</span>
  </div>
  <svg viewBox="0 0 {W} {H}" width="100%" preserveAspectRatio="none" role="img"
       aria-label="Weekly volume, last {len(rows)} weeks">
    <line x1="{PAD_L}" y1="{ay:.1f}" x2="{W-PAD_L}" y2="{ay:.1f}" stroke="var(--muted)"
          stroke-width="1" stroke-dasharray="3 3" opacity=".55"/>
    {rects}
    <line x1="{PAD_L}" y1="{PAD_T+ph}" x2="{W-PAD_L}" y2="{PAD_T+ph}"
          stroke="var(--border)" stroke-width="1"/>
  </svg>
  <div class="volfoot"><span>{rows[0][0]}</span>
    <span class="mut">dashed = {avg/1e6:,.0f}M avg</span><span>{rows[-1][0]}</span></div>
</div>"""


def _overview_rows(scores, bars_by_ticker, meta) -> str:
    out = ""
    for t, s in scores.items():
        bars = bars_by_ticker[t]
        c = [b["close"] for b in bars]
        px = c[-1]
        ext40 = (px / ind.sma(c, 40) - 1) * 100 if ind.sma(c, 40) else None
        dd = ind.drawdown_from_high(c)
        vol = ind.realised_vol(c)
        m = meta.get(t, {})
        out += f"""<tr>
<td class="tkr">{t}</td><td class="mut">{m.get('name', '')}</td>
<td class="r">${_n(px)}</td>
<td class="r {_cl(s.evidence.get('rs_sector_13w'))}">{_n(s.evidence.get('rs_sector_13w'),1,'%',True)}</td>
<td class="r {ext_class(ext40)}">{_n(ext40,1,'%',True)}</td>
<td class="r neg">{_n(dd,1,'%')}</td>
<td class="r">{_n(s.evidence.get('rsi'),1)}</td>
<td class="r">{_n(vol,0,'%')}</td>
<td class="r">{_n(s.evidence.get('ud_volume_8w'),2)}</td>
<td class="r b">{s.total:+d}</td>
<td class="c"><span class="pill {VC[s.verdict]}">{s.verdict}</span></td>
</tr>"""
    return out


def _card(t, s, bars, meta, quality) -> str:
    c = [b["close"] for b in bars]
    px = c[-1]
    ext40 = (px / ind.sma(c, 40) - 1) * 100 if ind.sma(c, 40) else None
    m = meta.get(t, {})
    q = quality.get(t)

    stale = ""
    if q and not q.passed:
        stale = (f"<div class='warn'>&#9888; {t} failed the data quality gate: "
                 f"{'; '.join(q.failures)}. Indicators below are unreliable.</div>")
    elif q and q.warnings:
        stale = f"<div class='warn'>&#9888; {'; '.join(q.warnings)}</div>"

    comp = "".join(
        f"<tr><td class='mut'>{k}</td><td class='r b {_cl(v)}'>{v:+d}</td></tr>"
        for k, v in s.components.items())
    unavail = ("<p class='sub'>Unavailable components (scored 0): "
               f"{', '.join(s.unavailable)}</p>" if s.unavailable else "")

    ev = s.evidence
    return f"""
<div class="pane" id="pane-{t}"{'' if s.first else ' hidden'}>
<div class="card">
  <div class="chead">
    <div><span class="ctkr">{t}</span><span class="cname">{m.get('name','')}</span>
      <span class="cbucket">{m.get('sector','')}</span></div>
    <span class="pill {VC[s.verdict]} big">{s.verdict} ({s.total:+d})</span>
  </div>
  {stale}
  <div class="cgrid">
    <div class="metric"><span class="ml">price</span><span class="mv">${_n(px)}</span></div>
    <div class="metric"><span class="ml">vs sector 13w</span><span class="mv {_cl(ev.get('rs_sector_13w'))}">{_n(ev.get('rs_sector_13w'),1,'%',True)}</span></div>
    <div class="metric"><span class="ml">vs 40w MA</span><span class="mv">{_n(ext40,1,'%',True)}</span></div>
    <div class="metric"><span class="ml">from high</span><span class="mv neg">{_n(ind.drawdown_from_high(c),1,'%')}</span></div>
    <div class="metric"><span class="ml">RSI(14)</span><span class="mv">{_n(ev.get('rsi'),1)}</span></div>
    <div class="metric"><span class="ml">vol (ann)</span><span class="mv">{_n(ind.realised_vol(c),0,'%')}</span></div>
    <div class="metric"><span class="ml">U/D vol 8w</span><span class="mv {_cl((ev.get('ud_volume_8w') or 1)-1)}">{_n(ev.get('ud_volume_8w'),2)}</span></div>
    <div class="metric"><span class="ml">max DD</span><span class="mv neg">{_n(ind.max_drawdown(c),1,'%')}</span></div>
  </div>
  <div class="csplit">
    <div>
      <h4>Score components</h4>
      <table>{comp}
        <tr><td class="b">total</td><td class="r b">{s.total:+d}</td></tr></table>
      {unavail}
      {volume_chart(bars)}
    </div>
    <div>
      <h4>Evidence</h4>
      <table>
        <tr><td class="mut">bars used</td><td class="r">{s.n_bars}</td></tr>
        <tr><td class="mut">10w / 26w MA</td><td class="r">${_n(ev.get('sma_short'))} / ${_n(ev.get('sma_mid'))}</td></tr>
        <tr><td class="mut">MACD histogram</td><td class="r {_cl(ev.get('macd_hist'))}">{_n(ev.get('macd_hist'))}</td></tr>
        <tr><td class="mut">extension vs 26w</td><td class="r">{_n(ev.get('extension_pct'),1,'%',True)}</td></tr>
        <tr><td class="mut">extension z-score</td><td class="r">{_n(ev.get('extension_z'))}&sigma; <span class="mut">(n={int(ev.get('extension_n') or 0)})</span></td></tr>
        <tr><td class="mut">52w range position</td><td class="r">{_n(ind.range_position(c),0,'%')}</td></tr>
        <tr><td class="mut">ATR(14) as % px</td><td class="r">{_n((ind.atr(bars) or 0)/px*100,1,'%')}</td></tr>
      </table>
      <p class="sub" style="margin-top:14px">Decision uses bars strictly before
      {s.asof}. Every figure above is recomputable from the cache.</p>
    </div>
  </div>
</div>
</div>"""


def render(scores: dict, bars_by_ticker: dict, *, meta: dict | None = None,
           quality: dict | None = None, title: str = "Equity Tracker",
           asof: str | None = None, notes: list[str] | None = None) -> str:
    meta = meta or {}
    quality = quality or {}
    asof = asof or datetime.utcnow().strftime("%Y-%m-%d")
    tickers = list(scores)

    for i, t in enumerate(tickers):
        scores[t].first = (i == 0)

    tabs = "".join(
        f'<button class="tab {VC[scores[t].verdict]}{" on" if i == 0 else ""}" '
        f'data-t="{t}" onclick="showT(\'{t}\')" '
        f'title="{meta.get(t, {}).get("sector", "")} — {scores[t].verdict}">'
        f'<span class="tdot"></span>{t}</button>'
        for i, t in enumerate(tickers))

    cards = "".join(_card(t, scores[t], bars_by_ticker[t], meta, quality) for t in tickers)

    counts = {v: sum(1 for s in scores.values() if s.verdict == v)
              for v in ("BUY", "HOLD", "TRIM", "SELL")}
    quarantined = [t for t, q in quality.items() if not q.passed]

    banner = ""
    if quarantined:
        banner = (f"<div class='banner'><b>{len(quarantined)} ticker(s) failed the data "
                  f"quality gate:</b> {', '.join(quarantined)}. They are excluded from "
                  f"aggregate figures and flagged on their own cards. Nothing is "
                  f"forward-filled silently.</div>")
    note_html = "".join(f"<div class='sblock'><p>{n}</p></div>" for n in (notes or []))

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body><div class="wrap">
<h1>{title}</h1>
<p class="sub">{len(tickers)} tickers &middot; as of {asof} &middot;
generated by ninja-portfolio-tracker</p>
{banner}
<div class="kpis">
<div class="kpi"><span class="l">Tickers</span><span class="v">{len(tickers)}</span><span class="n">passing the gate</span></div>
<div class="kpi"><span class="l">Buy</span><span class="v pos">{counts['BUY']}</span><span class="n">score &ge; threshold</span></div>
<div class="kpi"><span class="l">Hold</span><span class="v">{counts['HOLD']}</span><span class="n">no action</span></div>
<div class="kpi"><span class="l">Trim</span><span class="v" style="color:#fbbf24">{counts['TRIM']}</span><span class="n">negative, no action</span></div>
<div class="kpi"><span class="l">Sell</span><span class="v neg">{counts['SELL']}</span><span class="n">exit signal</span></div>
<div class="kpi"><span class="l">Quarantined</span><span class="v {'neg' if quarantined else ''}">{len(quarantined)}</span><span class="n">failed quality gate</span></div>
</div>
{note_html}
<h2>Overview</h2>
<table><thead><tr>
<th>Ticker</th><th>Company</th><th class="r">Price</th><th class="r">vs sector 13w</th>
<th class="r">vs 40w MA</th><th class="r">From high</th><th class="r">RSI</th>
<th class="r">Vol</th><th class="r">U/D 8w</th><th class="r">Score</th><th class="c">Verdict</th>
</tr></thead><tbody>{_overview_rows(scores, bars_by_ticker, meta)}</tbody></table>
<div class="key">
  <span><i style="background:var(--pos)"></i>gain</span>
  <span><i style="background:var(--neg)"></i>loss</span>
  <span class="mut">|</span>
  <span><b>vs 40w MA</b> is distance from trend, not profit &mdash; separate scale:</span>
  <span><i style="background:var(--accent)"></i>below trend</span>
  <span><i style="background:#8b95a5"></i>within 25%</span>
  <span><i style="background:#fbbf24"></i>25&ndash;50%</span>
  <span><i style="background:#fb923c"></i>&gt;50%</span>
</div>

<h2>Name by name</h2>
<p class="sub">Select a ticker. Arrow keys navigate. Every score decomposes into its
components and the evidence behind them.</p>
<div class="tabs">{tabs}</div>
{cards}

<div class="foot">
<h4>Method</h4>
<p>Weekly OHLCV via yfinance, cached locally. Score components: trend (price vs 10-
and 26-week MA), momentum (MACD histogram sign, RSI band), extension over the 26-week
MA, up/down volume over 8 weeks, 13-week relative strength versus the sector ETF.
Decisions use bars dated strictly before the decision date. Unavailable indicators
contribute 0 and are listed on the card rather than defaulting to a negative.</p>
<h4>Reproducing this</h4>
<p><code>pip install ninja-portfolio-tracker[live]</code> &middot;
<code>tracker fetch --tickers ...</code> &middot; <code>tracker doctor</code> &middot;
<code>tracker report</code> &middot; <code>tracker verify</code></p>
<p>Source: <a href="https://github.com/app-ninja-jv/ninja-portfolio-tracker">github.com/app-ninja-jv/ninja-portfolio-tracker</a>
&middot; MIT licensed &middot; no market data is redistributed &mdash; you fetch your own.</p>
<p>Analysis tooling, not investment advice.</p>
</div>
</div>
<script>{TAB_JS.replace('%ORDER%', json.dumps(tickers))}</script>
</body></html>"""
