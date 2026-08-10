"""Synthetic bars with known-answer properties. No network required.

Deterministic by design: a linear ramp has an exactly computable SMA, so any drift
in the indicator code shows up immediately.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

START = date(2024, 8, 5)          # a Monday


def _dates(n: int) -> list[str]:
    return [(START + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(n)]


def bars_from_closes(closes: list[float], volumes: list[float] | None = None) -> list[dict]:
    ds = _dates(len(closes))
    vols = volumes or [1_000_000.0] * len(closes)
    out = []
    for d, c, v in zip(ds, closes, vols, strict=True):
        out.append({
            "date": d,
            "open": c * 0.995,
            "high": c * 1.02,
            "low": c * 0.98,
            "close": c,
            "adj_close": c,
            "volume": v,
        })
    return out


def ramp(n: int = 120, start: float = 100.0, step: float = 1.0) -> list[dict]:
    """Strictly rising. SMA(n) of the last k is arithmetically predictable."""
    return bars_from_closes([start + step * i for i in range(n)])


def flat(n: int = 120, level: float = 100.0) -> list[dict]:
    """Zero volatility. RSI is undefined-ish (100 by convention), vol is 0."""
    return bars_from_closes([level] * n)


def sine(n: int = 120, level: float = 100.0, amp: float = 10.0, period: int = 26) -> list[dict]:
    return bars_from_closes([level + amp * math.sin(2 * math.pi * i / period)
                             for i in range(n)])


def crash(n: int = 120, level: float = 100.0, at: int = 100, drop: float = 0.4) -> list[dict]:
    closes = []
    for i in range(n):
        c = level * (1 - drop) if i >= at else level
        closes.append(c)
    return bars_from_closes(closes)


def with_distribution(n: int = 120) -> list[dict]:
    """Down weeks carry 3x the volume of up weeks — U/D ratio should be well below 1."""
    closes, vols = [100.0], [1_000_000.0]
    for i in range(1, n):
        down = i % 2 == 0
        closes.append(closes[-1] * (0.98 if down else 1.01))
        vols.append(3_000_000.0 if down else 1_000_000.0)
    return bars_from_closes(closes, vols)


def basket() -> dict[str, list[dict]]:
    return {
        "RAMP": ramp(),
        "SINE": sine(),
        "DIST": with_distribution(),
        "SOXX": ramp(120, 200.0, 0.5),      # benchmark rising more slowly
        "QQQ": ramp(120, 400.0, 0.4),
    }
