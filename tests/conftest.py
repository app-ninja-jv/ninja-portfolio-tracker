import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from tests.fixtures import synthetic


@pytest.fixture
def basket():
    return synthetic.basket()


@pytest.fixture
def ramp():
    return synthetic.ramp()
