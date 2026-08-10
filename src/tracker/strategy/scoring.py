"""Scoring rule.

Five components, each an integer, summed. Thresholds map the total to a verdict.

CRITICAL — LOOK-AHEAD
    score_at(bars, asof) uses ONLY bars dated strictly BEFORE asof. Execution is
    at asof's close. This is the single discipline that separates a real backtest
    from a flattering one. tests/test_lookahead.py asserts it.

COMPONENT AVAILABILITY
    If an indicator cannot be computed, its component contributes 0 and the name
    is recorded in `unavailable`. It never contributes a negative by accident.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import StrategyConfig
from ..features import indicators as ind


@dataclass
class Score:
    ticker: str
    asof: str
    total: int
    verdict: str
    components: dict[str, int] = field(default_factory=dict)
    evidence: dict[str, float | None] = field(default_factory=dict)
    unavailable: list[str] = field(default_factory=list)
    n_bars: int = 0

    def explain(self) -> str:
        parts = " ".join(f"{k}{v:+d}" for k, v in self.components.items())
        return f"{self.ticker} {self.asof} {self.verdict} ({self.total:+d}) {parts}"


def bars_before(bars: list[dict], asof: str) -> list[dict]:
    """The only permitted way to select decision data."""
    return [b for b in bars if b["date"] < asof]


def score_at(ticker: str, bars: list[dict], asof: str,
             sector_bars: list[dict] | None = None,
             cfg: StrategyConfig | None = None) -> Score | None:
    cfg = cfg or StrategyConfig()
    hist = bars_before(bars, asof)
    if len(hist) < 30:
        return None

    closes = [b["close"] for b in hist]
    vols = [b["volume"] for b in hist]
    px = closes[-1]
    w_short, w_mid, _w_long = cfg.ma_windows

    comp: dict[str, int] = {}
    ev: dict[str, float | None] = {}
    missing: list[str] = []

    # 1. TREND  0..+2
    s_short, s_mid = ind.sma(closes, w_short), ind.sma(closes, w_mid)
    if s_short is None or s_mid is None:
        comp["trend"] = 0
        missing.append("trend")
    else:
        comp["trend"] = (1 if px > s_short else 0) + (1 if px > s_mid else 0)
    ev["sma_short"], ev["sma_mid"] = s_short, s_mid

    # 2. MOMENTUM  -2..+2
    _, _, hist_macd = ind.macd(closes, *cfg.macd)
    r = ind.rsi(closes, cfg.rsi_period)
    mom = 0
    if hist_macd is None:
        missing.append("macd")
    else:
        mom += 1 if hist_macd > 0 else -1
    if r is None:
        missing.append("rsi")
    else:
        mom += -1 if r > 70 else (1 if r >= 40 else 0)
    comp["momentum"] = mom
    ev["macd_hist"], ev["rsi"] = hist_macd, r

    # 3. EXTENSION vs mid MA  -2..+1 — penalises buying far above trend
    ext, ext_z, ext_n = ind.extension(closes, w_mid)
    if ext is None:
        comp["extension"] = 0
        missing.append("extension")
    else:
        comp["extension"] = -2 if ext > 40 else (-1 if ext > 20 else (1 if ext >= 0 else 0))
    ev["extension_pct"], ev["extension_z"], ev["extension_n"] = ext, ext_z, ext_n

    # 4. VOLUME  -1..+1
    ud = ind.up_down_volume(closes, vols, weeks=8)
    if ud is None:
        comp["volume"] = 0
        missing.append("volume")
    else:
        comp["volume"] = 1 if ud > 1.2 else (-1 if ud < 0.8 else 0)
    ev["ud_volume_8w"] = ud

    # 5. RELATIVE STRENGTH vs sector, 13 weeks  -1..+1
    rs = None
    if sector_bars:
        sh = bars_before(sector_bars, asof)
        a, b = ind.align([x["date"] for x in hist], closes,
                         [x["date"] for x in sh], [x["close"] for x in sh])
        rs = ind.excess_return(a, b, 13) if len(a) > 13 else None
    if rs is None:
        comp["rel_strength"] = 0
        missing.append("rel_strength")
    else:
        comp["rel_strength"] = 1 if rs > 10 else (-1 if rs < -10 else 0)
    ev["rs_sector_13w"] = rs

    total = sum(comp.values())
    return Score(ticker=ticker, asof=asof, total=total, verdict=cfg.verdict(total),
                 components=comp, evidence=ev, unavailable=missing, n_bars=len(hist))


def score_series(ticker: str, bars: list[dict], dates: list[str],
                 sector_bars: list[dict] | None = None,
                 cfg: StrategyConfig | None = None) -> dict[str, Score]:
    out = {}
    for d in dates:
        s = score_at(ticker, bars, d, sector_bars, cfg)
        if s:
            out[d] = s
    return out
