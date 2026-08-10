"""Configuration. Every tunable parameter lives here — never inline in logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# 104 weeks is a hard floor, not a preference. Below it these silently degrade:
#   40-week MA   -> too few observations for a meaningful z-score
#   MACD(12,26,9)-> needs 35 bars; returns None and scores every ticker identically
MIN_WEEKS = 104


@dataclass(frozen=True)
class DataConfig:
    weeks: int = MIN_WEEKS
    cache_path: Path = Path("data/bars.sqlite")
    max_staleness_days: int = 10
    benchmarks: tuple[str, ...] = ("SPY", "QQQ")
    sector_etf: str = "SOXX"


@dataclass(frozen=True)
class StrategyConfig:
    """Scoring thresholds and allocation weights.

    Defaults are the values used in the semiconductor study. They are a starting
    point, not an optimum — see docs/finance_app_logic.md on why sweeping these on
    a small sample finds artefacts.
    """
    buy_threshold: int = 4
    sell_threshold: int = -2
    trim_acts: bool = False

    # entry/exit mode sizing — keep symmetric unless you have a reason
    entry_size: float = 10.0
    exit_size: float = 10.0

    # allocation mode multipliers
    weights: dict[str, float] = field(
        default_factory=lambda: {"BUY": 1.6, "HOLD": 1.0, "TRIM": 0.5, "SELL": 0.2}
    )

    cost_bps: float = 10.0
    macd: tuple[int, int, int] = (12, 26, 9)
    rsi_period: int = 14
    ma_windows: tuple[int, int, int] = (10, 26, 40)

    def verdict(self, score: int) -> str:
        if score >= self.buy_threshold:
            return "BUY"
        if score <= self.sell_threshold:
            return "SELL"
        if score <= 0:
            return "TRIM"
        return "HOLD"


@dataclass(frozen=True)
class Settings:
    data: DataConfig = field(default_factory=DataConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    out_dir: Path = Path("build")


DEFAULT = Settings()
