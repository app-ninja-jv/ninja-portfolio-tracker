"""Midnight Slate — dark blue-slate quant terminal theme.

Full specification in docs/tracker_style.md. Design decisions:
  * elevation by lightness + 1px hairlines, no drop shadows
  * colour is semantic only; non-money metrics get their own scale + legend
  * tabular numerals everywhere so digits align and don't jitter
  * system font stack, no web fonts, works offline
"""
from __future__ import annotations

CSS = """
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
 font:14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:1400px;margin:0 auto;padding:32px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.4px}
h2{font-size:17px;margin:44px 0 14px;padding-bottom:9px;
 border-bottom:1px solid var(--border);letter-spacing:-.2px}
h4{font-size:12px;text-transform:uppercase;letter-spacing:.9px;color:var(--muted);margin:0 0 9px}
.sub{color:var(--muted);font-size:13px;margin:0 0 4px}
.banner{background:var(--warn-bg);border:1px solid var(--warn-border);
 border-left:3px solid var(--warn-rule);padding:14px 18px;border-radius:var(--radius-sm);
 margin:22px 0;font-size:13px;line-height:1.65}
.banner b{color:#fbbf24}
.warn{background:var(--warn-bg);border-left:3px solid var(--warn-rule);padding:9px 13px;
 border-radius:4px;margin:0 0 14px;font-size:12px;color:var(--warn-text)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:22px 0}
.kpi{background:var(--surface-2);border:1px solid var(--border);border-radius:7px;padding:15px 17px}
.kpi .l{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);
 display:block;margin-bottom:5px}
.kpi .v{font-size:23px;font-weight:600;letter-spacing:-.5px}
.kpi .n{font-size:11px;color:var(--faint);display:block;margin-top:3px}
table{width:100%;border-collapse:collapse;font-size:12.5px;
 font-variant-numeric:tabular-nums;font-feature-settings:'tnum'}
th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.7px;
 color:var(--muted);padding:9px 8px;border-bottom:1px solid var(--border);
 font-weight:600;white-space:nowrap}
td{padding:9px 8px;border-bottom:1px solid var(--border-soft)}
tbody tr:hover{background:var(--surface-2)}
tr.hl{background:rgba(96,165,250,.07)}
.r{text-align:right} .c{text-align:center} .b{font-weight:600}
.tkr{font-weight:700;color:#f1f5f9;letter-spacing:.3px}
.mut{color:var(--muted)} .na{color:var(--faint)}
.pos{color:var(--pos)} .neg{color:var(--neg)}
/* extension vs a moving average is a RISK gauge, not money — separate scale */
.stretch{color:#fbbf24} .hot{color:#fb923c;font-weight:600} .below{color:var(--accent)}
.key{display:flex;flex-wrap:wrap;gap:14px;margin-top:9px;font-size:11.5px;color:var(--faint)}
.key span{display:inline-flex;align-items:center;gap:5px}
.key i{width:8px;height:8px;border-radius:2px;display:inline-block;font-style:normal}
.pill{display:inline-block;padding:3px 10px;border-radius:11px;font-size:10px;
 font-weight:700;letter-spacing:.6px;text-transform:uppercase;white-space:nowrap}
.pill.big{font-size:11.5px;padding:5px 14px}
.buy{background:rgba(34,197,94,.14);color:var(--pos);border:1px solid rgba(34,197,94,.35)}
.hold{background:rgba(148,163,184,.13);color:#cbd5e1;border:1px solid rgba(148,163,184,.3)}
.trim{background:rgba(234,179,8,.13);color:#fbbf24;border:1px solid rgba(234,179,8,.32)}
.sell{background:rgba(239,68,68,.14);color:var(--neg);border:1px solid rgba(239,68,68,.35)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
 padding:22px;margin-bottom:18px}
.chead{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}
.ctkr{font-size:20px;font-weight:700;letter-spacing:-.3px}
.cname{margin-left:11px;color:var(--text-dim);font-size:14.5px;font-weight:500}
.cbucket{margin-left:11px;padding-left:11px;border-left:1px solid var(--border);
 color:var(--muted);font-size:12.5px;white-space:nowrap}
@media(max-width:700px){.cname,.cbucket{display:block;margin-left:0;padding-left:0;
 border-left:0;margin-top:3px}}
.cgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:9px;margin-bottom:20px}
.metric{background:var(--inset);border:1px solid var(--border-soft);
 border-radius:var(--radius-sm);padding:9px 11px}
.ml{display:block;font-size:9.5px;text-transform:uppercase;letter-spacing:.6px;
 color:var(--muted);margin-bottom:3px}
.mv{font-size:15px;font-weight:600;font-variant-numeric:tabular-nums}
.csplit{display:grid;grid-template-columns:1fr 1.3fr;gap:30px}
@media(max-width:900px){.csplit{grid-template-columns:1fr}}
.sblock{background:var(--surface);border:1px solid var(--border);
 border-left:2px solid var(--accent);border-radius:6px;padding:16px 20px;margin-bottom:13px}
.sblock p{margin:0 0 10px;color:var(--text-dim);font-size:13.2px;line-height:1.7}
.sblock p:last-child{margin-bottom:0}
.sblock.warnb{border-left-color:var(--warn-rule)}
/* ticker tabs */
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin:16px 0 18px;padding-bottom:14px;
 border-bottom:1px solid var(--border)}
.tab{display:inline-flex;align-items:center;gap:7px;cursor:pointer;background:var(--surface);
 border:1px solid var(--border);color:var(--muted);padding:7px 14px;border-radius:7px;
 font:600 12.5px/1 inherit;letter-spacing:.4px;font-family:inherit;
 transition:background .12s,color .12s,border-color .12s}
.tab:hover{background:var(--surface-2);color:var(--text)}
.tab .tdot{width:7px;height:7px;border-radius:50%;flex:0 0 7px;background:currentColor}
.tab.buy .tdot{background:var(--pos)} .tab.hold .tdot{background:#cbd5e1}
.tab.trim .tdot{background:#fbbf24} .tab.sell .tdot{background:var(--neg)}
.tab.on{color:var(--text);background:var(--surface-2);border-color:#3f5170;
 box-shadow:inset 0 -2px 0 0 var(--accent)}
.tab.on.buy{box-shadow:inset 0 -2px 0 0 var(--pos)}
.tab.on.trim{box-shadow:inset 0 -2px 0 0 #fbbf24}
.tab.on.sell{box-shadow:inset 0 -2px 0 0 var(--neg)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pane[hidden]{display:none}
@media(max-width:640px){.tab{padding:6px 10px;font-size:11.5px}}
/* inline charts — volume bars and the ticker-vs-benchmark trend line */
.volwrap,.trendwrap{margin:18px 0 4px;background:var(--inset);border:1px solid var(--border-soft);
 border-radius:var(--radius-sm);padding:10px 12px 8px}
.trendwrap{margin:0 0 20px}
.volhead,.trendhead{display:flex;justify-content:space-between;align-items:baseline;
 margin-bottom:6px;gap:10px}
.volstat,.trendstat{font-size:10.5px;color:var(--muted);font-variant-numeric:tabular-nums;
 white-space:nowrap}
.volwrap svg{display:block;height:96px}
/* uniform scaling here, unlike the volume bars: squashing the aspect ratio would
   distort the crossover dots into ellipses and skew the slope of every line */
.trendwrap svg{display:block;width:100%;height:auto}
.trendwrap .ax{fill:var(--faint);font-size:7px;font-variant-numeric:tabular-nums}
.volfoot,.trendfoot{display:flex;justify-content:space-between;font-size:9.5px;
 color:var(--faint);margin-top:3px;font-variant-numeric:tabular-nums;gap:12px}
.trendfoot .mut{text-align:center}
@media(max-width:640px){.trendhead{flex-direction:column;gap:2px}
 .trendstat{white-space:normal}}
.cm{text-align:center;font-size:11px;padding:7px 4px;border:1px solid var(--bg)}
.foot{margin-top:46px;padding-top:22px;border-top:1px solid var(--border);
 font-size:12px;color:var(--faint);line-height:1.75}
.foot a{color:var(--accent);text-decoration:none} .foot a:hover{text-decoration:underline}
.foot h4{margin-top:20px}
code{background:var(--inset);padding:1px 5px;border-radius:3px;font-size:11.5px;color:#a5b4fc}
"""

TAB_JS = """
(function(){
  var order = %ORDER%;
  function showT(t){
    order.forEach(function(x){
      var p = document.getElementById('pane-' + x);
      if (p) p.hidden = (x !== t);
    });
    document.querySelectorAll('.tab').forEach(function(b){
      b.classList.toggle('on', b.dataset.t === t);
    });
  }
  window.showT = showT;
  document.addEventListener('keydown', function(e){
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    var tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea') return;
    var cur = document.querySelector('.tab.on');
    if (!cur) return;
    var i = order.indexOf(cur.dataset.t);
    if (i < 0) return;
    var next = e.key === 'ArrowRight'
      ? order[(i + 1) % order.length]
      : order[(i - 1 + order.length) % order.length];
    showT(next);
    var btn = document.querySelector('.tab[data-t="' + next + '"]');
    if (btn) btn.focus();
    e.preventDefault();
  });
})();
"""


def ext_class(pct: float | None) -> str:
    """Extension vs a moving average — risk gauge, deliberately not the P/L palette."""
    if pct is None:
        return ""
    if pct < -5:
        return "below"
    if pct > 50:
        return "hot"
    if pct > 25:
        return "stretch"
    return ""


def heat(v: float | None) -> str:
    """Correlation cell background: green positive, red negative, alpha by magnitude."""
    if v is None:
        return "#1b2331"
    a = min(abs(v), 1.0)
    if v >= 0:
        return f"rgba(56,161,105,{0.10 + 0.60 * a:.2f})"
    return f"rgba(197,48,48,{0.10 + 0.60 * a:.2f})"
