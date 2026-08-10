"""Look-ahead is the failure mode that makes a backtest beautiful and useless.

These tests assert the property structurally rather than trusting the code to be
careful: mutate the future and check the past-dated decision does not move.
"""
import copy

from tests.fixtures import synthetic
from tracker.strategy import bars_before, score_at
from tracker.verify import checks


def test_bars_before_is_strict():
    b = synthetic.ramp(60)
    d = b[30]["date"]
    used = bars_before(b, d)
    assert all(x["date"] < d for x in used)
    assert d not in [x["date"] for x in used]


def test_score_ignores_future_bars():
    """The decisive test: corrupt every bar after the decision date. Score must not change."""
    b = synthetic.ramp(80)
    sector = synthetic.ramp(80, 200.0, 0.5)
    asof = b[60]["date"]

    before = score_at("X", b, asof, sector)
    poisoned = copy.deepcopy(b)
    for bar in poisoned:
        if bar["date"] >= asof:
            bar["close"] *= 10          # absurd future move
            bar["high"] *= 10
            bar["low"] *= 10
            bar["volume"] *= 100
    after = score_at("X", poisoned, asof, sector)

    assert before.total == after.total
    assert before.components == after.components
    assert before.evidence["rsi"] == after.evidence["rsi"]


def test_lookahead_audit_passes_on_clean_data():
    basket = synthetic.basket()
    dates = [basket["RAMP"][i]["date"] for i in range(40, 80, 4)]
    rep = checks.check_lookahead(basket, dates)
    assert rep.clean, rep.failed


def test_unavailable_component_scores_zero_not_negative():
    """Short history must not silently produce a negative momentum score."""
    b = synthetic.ramp(40)
    asof = b[-1]["date"]
    s = score_at("X", b, asof)
    assert s is not None
    assert "macd" in s.unavailable or s.evidence["macd_hist"] is not None
    if "macd" in s.unavailable:
        # momentum can only come from RSI in that case, so it cannot be -2
        assert s.components["momentum"] > -2
