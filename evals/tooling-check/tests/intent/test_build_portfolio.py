"""Intent: build_portfolio reproduces the oracle weights for each fixture case."""

import json
from pathlib import Path

import pytest

from quantcheck.portfolio import build_portfolio

FIXTURES = Path(__file__).parents[1] / "fixtures" / "quantcheck"


@pytest.mark.intent
@pytest.mark.parametrize("case", ["TC-01"])
def test_build_portfolio_matches_oracle(case):
    case_dir = FIXTURES / case
    records = json.loads((case_dir / "input.json").read_text(encoding="utf-8"))
    expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    assert build_portfolio(records) == pytest.approx(expected["weights"], abs=1e-6)


@pytest.mark.intent
def test_build_portfolio_rejects_non_positive_prices():
    records = [
        {"date": "2026-01-05", "ticker": "AAA", "close": 100.0},
        {"date": "2026-01-06", "ticker": "AAA", "close": 0.0},
    ]
    with pytest.raises(ValueError, match="positive"):
        build_portfolio(records)
