"""equity-tracker — auditable equity research dashboards."""
from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    raise RuntimeError(
        f"equity-tracker requires Python 3.10 or newer; this is "
        f"{sys.version_info.major}.{sys.version_info.minor}.\n"
        "The package uses zip(strict=True) and PEP 604 unions, neither of which\n"
        "exists on 3.9. Create the venv with an explicit interpreter, e.g.:\n"
        "    python3.12 -m venv .venv && source .venv/bin/activate"
    )

__version__ = "0.1.0"
__author__ = "jovi-maverick"

from .config import DataConfig, Settings, StrategyConfig  # noqa: E402,F401
