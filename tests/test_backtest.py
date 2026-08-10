import math

from tests.fixtures import synthetic
from tracker.backtest import benchmarks, engine
from tracker.config import StrategyConfig
from tracker.verify import checks


def _basket():
    return {k: v for k, v in synthetic.basket().items() if k not in ("SOXX", "QQQ")}


def test_allocation_conserves_capital():
    b = _basket()
    start = b["RAMP"][40]["date"]
    res = engine.run_allocation(b, start=start, step=2, capital=1000.0,
                                sector_bars=synthetic.ramp(120, 200.0, 0.5))
    assert math.isclose(res.contributed, 1000.0)
    assert res.end_value > 0


def test_allocation_beats_nothing_on_rising_basket():
    b = _basket()
    start = b["RAMP"][40]["date"]
    res = engine.run_allocation(b, start=start, step=2, capital=1000.0)
    assert res.ret_pct > 0          # everything rises in the fixture


def test_ledger_rebuild_matches():
    b = _basket()
    start = b["RAMP"][40]["date"]
    res = engine.run_allocation(b, start=start, step=2, capital=1000.0)
    exits = {t: engine.price_at(bs, res.end) for t, bs in b.items()}
    rep = checks.check_ledger(res, exits)
    assert rep.clean, rep.failed


def test_entry_exit_tracks_flows():
    b = _basket()
    start = b["RAMP"][40]["date"]
    res = engine.run_entry_exit(b, start=start, step=2, seed=100.0)
    for v in res.per_ticker.values():
        # P/L identity must hold exactly
        assert math.isclose(v["pl"], v["final"] + v["withdrawn"] - v["contributed"],
                            abs_tol=1e-6)


def test_equal_weight_equals_mean_of_returns():
    b = _basket()
    start, end = b["RAMP"][40]["date"], b["RAMP"][-1]["date"]
    eq = benchmarks.equal_weight(b, start, end, 1000.0)
    rets = [benchmarks.simple_return(bs, start, end) for bs in b.values()]
    # equal-weight terminal value == mean of gross returns
    gross = sum(1 + r / 100 for r in rets) / len(rets)
    assert math.isclose(eq, (gross - 1) * 100, abs_tol=1e-6)


def test_bucket_test_returns_all_verdicts():
    b = _basket()
    start, end = b["RAMP"][40]["date"], b["RAMP"][-1]["date"]
    bk = benchmarks.bucket_test(b, start, end, 2, synthetic.ramp(120, 200.0, 0.5))
    for k in ("BUY", "HOLD", "TRIM", "SELL", "ALL"):
        assert k in bk
    assert isinstance(bk["monotonic"], bool)


def test_regime_labels_bull_on_rising_index():
    b = _basket()
    idx = synthetic.ramp(120, 400.0, 2.0)
    start, end = b["RAMP"][40]["date"], b["RAMP"][-1]["date"]
    rg = benchmarks.regime(idx, start, end, b)
    assert rg["label"] == "bull"
    assert rg["n_names"] == len(b)
    # breadth is measured per name, NOT inferred from the index. The fixture basket
    # contains a declining series (DIST), so breadth must be below 100% even though
    # the index rose — that divergence is the whole point of tracking it separately.
    assert 0.0 < rg["pct_names_positive"] < 100.0


def test_regime_labels_bear_on_falling_index():
    b = _basket()
    idx = synthetic.crash(120, 400.0, at=60, drop=0.35)
    start, end = b["RAMP"][40]["date"], b["RAMP"][-1]["date"]
    rg = benchmarks.regime(idx, start, end, b)
    assert rg["label"] == "bear"


def test_symmetric_sizing_is_the_default():
    cfg = StrategyConfig()
    assert cfg.entry_size == cfg.exit_size


def test_verdict_thresholds():
    cfg = StrategyConfig()
    assert cfg.verdict(5) == "BUY"
    assert cfg.verdict(2) == "HOLD"
    assert cfg.verdict(0) == "TRIM"
    assert cfg.verdict(-3) == "SELL"
