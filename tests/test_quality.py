from datetime import date, timedelta

from tests.fixtures import synthetic
from tracker.data import quality


def _today_for(bars):
    from datetime import datetime
    return datetime.strptime(bars[-1]["date"], "%Y-%m-%d").date() + timedelta(days=3)


def test_clean_series_passes():
    b = synthetic.ramp(110)
    rep = quality.check("RAMP", b, min_weeks=104, today=_today_for(b))
    assert rep.passed, rep.failures


def test_short_history_fails():
    b = synthetic.ramp(50)
    rep = quality.check("SHORT", b, min_weeks=104, today=_today_for(b))
    assert not rep.passed
    assert any("INSUFFICIENT_HISTORY" in f for f in rep.failures)


def test_stale_data_fails():
    b = synthetic.ramp(110)
    rep = quality.check("OLD", b, min_weeks=104,
                        today=date(2030, 1, 1), max_staleness_days=10)
    assert any("STALE" in f for f in rep.failures)


def test_ohlc_violation_detected():
    b = synthetic.ramp(110)
    b[10]["close"] = b[10]["high"] * 2      # close above high
    rep = quality.check("BAD", b, min_weeks=104, today=_today_for(b))
    assert any("OHLC_VIOLATION" in f for f in rep.failures)


def test_duplicate_dates_detected():
    b = synthetic.ramp(110)
    b[5]["date"] = b[4]["date"]
    rep = quality.check("DUP", b, min_weeks=104, today=_today_for(b))
    assert any("DUPLICATE_DATES" in f for f in rep.failures)


def test_unadjusted_split_warns():
    b = synthetic.ramp(110)
    b[60]["close"] = b[59]["close"] / 2     # 50% drop on normal volume
    b[60]["low"] = b[60]["close"] * 0.98
    b[60]["high"] = b[60]["close"] * 1.02
    rep = quality.check("SPLIT", b, min_weeks=104, today=_today_for(b))
    assert any("split" in w for w in rep.warnings)


def test_gate_partitions_tickers():
    good = quality.check("G", synthetic.ramp(110), min_weeks=104,
                         today=_today_for(synthetic.ramp(110)))
    bad = quality.check("B", synthetic.ramp(10), min_weeks=104,
                        today=_today_for(synthetic.ramp(10)))
    ok, quarantined = quality.gate({"G": good, "B": bad})
    assert ok == ["G"] and quarantined == ["B"]
