"""Known-answer tests. A linear ramp makes every indicator arithmetically checkable."""
import math

from tests.fixtures import synthetic
from tracker.features import indicators as ind


def closes(bars):
    return [b["close"] for b in bars]


def test_sma_on_ramp_is_exact():
    c = closes(synthetic.ramp(120, 100.0, 1.0))
    # last 40 values are 180..219 -> mean 199.5
    assert ind.sma(c, 40) == 199.5


def test_sma_returns_none_when_short():
    assert ind.sma([1.0, 2.0], 40) is None


def test_rsi_on_monotonic_rise_is_100():
    c = closes(synthetic.ramp(60))
    assert ind.rsi(c, 14) == 100.0


def test_rsi_none_when_short():
    assert ind.rsi([1.0, 2.0, 3.0], 14) is None


def test_macd_returns_none_triple_when_short():
    line, sig, hist = ind.macd([100.0] * 20, 12, 26, 9)
    assert (line, sig, hist) == (None, None, None)


def test_macd_available_with_enough_bars():
    c = closes(synthetic.ramp(60))
    line, sig, hist = ind.macd(c, 12, 26, 9)
    assert line is not None and hist is not None
    assert hist > 0            # rising series -> positive histogram


def test_flat_series_has_zero_vol():
    c = closes(synthetic.flat(60))
    assert ind.realised_vol(c) == 0.0


def test_weekly_sigma_matches_annual_over_sqrt52():
    assert math.isclose(ind.weekly_sigma(52.0), 52.0 / math.sqrt(52))


def test_up_down_volume_detects_distribution():
    b = synthetic.with_distribution()
    ud = ind.up_down_volume(closes(b), [x["volume"] for x in b], weeks=8)
    assert ud is not None and ud < 0.8      # heavy down-volume


def test_extension_reports_observation_count():
    c = closes(synthetic.ramp(60))
    pct, z, n = ind.extension(c, 40)
    assert pct > 0 and n == 60 - 40 + 1


def test_max_drawdown_on_crash():
    c = closes(synthetic.crash(120, 100.0, at=100, drop=0.4))
    assert math.isclose(ind.max_drawdown(c), -40.0, abs_tol=0.01)


def test_range_position_at_top_of_ramp():
    c = closes(synthetic.ramp(60))
    assert math.isclose(ind.range_position(c), 100.0, abs_tol=1e-9)


def test_correlation_of_series_with_itself_is_one():
    r = ind.returns(closes(synthetic.sine(80)))
    assert math.isclose(ind.correlation(r, r), 1.0, abs_tol=1e-9)


def test_beta_of_series_on_itself_is_one():
    r = ind.returns(closes(synthetic.sine(80)))
    assert math.isclose(ind.beta(r, r), 1.0, abs_tol=1e-9)
