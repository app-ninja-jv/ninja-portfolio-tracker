"""Renderer tests, focused on the ticker-vs-benchmark trend chart.

The chart makes a claim the eye cannot check: that both series are rebased to the
same base and that the dots sit on real moving-average crossovers. These assert it.
"""
from __future__ import annotations

from tests.fixtures import synthetic
from tracker.config import StrategyConfig
from tracker.features import indicators as ind
from tracker.render.dashboard import render, trend_chart
from tracker.strategy import score_at


def _scored(basket):
    cfg = StrategyConfig()
    asof = "2099-01-01"
    bars = {t: b for t, b in basket.items() if t not in ("SOXX", "QQQ")}
    scores = {t: score_at(t, b, asof, basket["SOXX"], cfg) for t, b in bars.items()}
    return {t: s for t, s in scores.items() if s}, bars


def test_chart_omitted_without_benchmark(basket):
    assert trend_chart(basket["RAMP"], None, "RAMP", "QQQ") == ""
    assert trend_chart(basket["RAMP"], [], "RAMP", "QQQ") == ""


def test_chart_omitted_on_short_history(basket):
    short = basket["RAMP"][:20]
    assert trend_chart(short, basket["QQQ"], "RAMP", "QQQ") == ""


def test_chart_has_no_overlap_when_dates_disjoint(basket):
    shifted = [dict(b, date="1999-" + b["date"][5:]) for b in basket["QQQ"]]
    assert trend_chart(basket["RAMP"], shifted, "RAMP", "QQQ") == ""


def test_both_series_rebased_to_the_same_base(basket):
    """First plotted point of each line must sit at 100 — same y, or the chart lies."""
    svg = trend_chart(basket["RAMP"], basket["QQQ"], "RAMP", "QQQ")
    paths = [seg.split('"')[0] for seg in svg.split('<path d="')[1:]]
    # paths[0] is the MA (starts later); [1] benchmark, [2] ticker — both from bar 0
    first_y = [p.split(" ")[0].split(",")[1] for p in paths[1:]]
    assert len(set(first_y)) == 1, f"series start at different y: {first_y}"


def test_excess_return_matches_the_indicator(basket):
    """Header stat must equal excess_return over the aligned closes, not a lookalike."""
    a = [b["close"] for b in basket["RAMP"]][-104:]
    b = [b["close"] for b in basket["QQQ"]][-104:]
    svg = trend_chart(basket["RAMP"], basket["QQQ"], "RAMP", "QQQ")
    expected = ind.excess_return(a, b, 13)
    assert f"{expected:,.1f}" in svg or f"+{expected:,.1f}" in svg


def test_crossover_dots_match_a_raw_price_crossover_count(basket):
    """Rebasing is a constant divide, so crossovers must land on the same bars."""
    bars, bench = synthetic.sine(120, 100.0, 12.0, 30), basket["QQQ"]
    svg = trend_chart(bars, bench, "SINE", "QQQ")
    drawn = svg.count("<circle")

    closes = [b["close"] for b in bars][-104:]
    ms = ind.sma_series(closes, 26)
    raw = 0
    for i in range(1, len(closes)):
        if ms[i - 1] is None or ms[i] is None:
            continue
        prev, cur = closes[i - 1] - ms[i - 1], closes[i] - ms[i]
        if prev < 0 <= cur or prev >= 0 > cur:
            raw += 1
    assert drawn == raw > 0


def test_render_embeds_one_chart_per_card(basket):
    scores, bars = _scored(basket)
    html = render(scores, bars, bench_bars=basket["QQQ"], benchmark="QQQ")
    assert html.count('class="trendwrap"') == len(scores)
    assert "rebased 100" in html


def test_render_survives_a_missing_benchmark(basket):
    scores, bars = _scored(basket)
    html = render(scores, bars, bench_bars=None, benchmark="QQQ")
    # the class name always exists in the stylesheet; assert on emitted markup
    assert 'class="trendwrap"' not in html
    assert html.count('class="card"') == len(scores)
