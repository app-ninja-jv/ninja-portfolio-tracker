"""Volatility-normalised thresholds.

A fixed +/-5% weekly move is not comparable across a 40%-vol name and a 106%-vol
name. Report fixed-% for position sizing and sigma-normalised for cross-ticker
ranking, and label every chart with which basis it uses.
"""
from __future__ import annotations

from . import indicators as ind


def sigma_thresholds(closes: list[float], multiples=(1.0, 1.5, 2.0)) -> dict:
    vol = ind.realised_vol(closes)
    if vol is None:
        return {}
    wk = ind.weekly_sigma(vol)
    out = {"annual_vol_pct": vol, "weekly_sigma_pct": wk}
    for m in multiples:
        out[f"thresh_{m:g}s_pct"] = m * wk
    return out
