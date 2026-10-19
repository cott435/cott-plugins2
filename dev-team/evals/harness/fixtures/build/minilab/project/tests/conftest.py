"""Shared test setup (human-owned): Hypothesis profiles, and golden cases and contract artifacts by name."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest
from hypothesis import settings

settings.register_profile("dev", max_examples=20)
settings.register_profile("ci", max_examples=500)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))

TESTS = Path(__file__).resolve().parent


@pytest.fixture
def golden():
    """golden("risk", "TC-05") -> (input, expected), read from tests/fixtures/<pkg>/<TC>/."""

    def load(pkg: str, tc: str) -> tuple[dict, dict]:
        folder = TESTS / "fixtures" / pkg / tc
        return (json.loads((folder / "input.json").read_text()), json.loads((folder / "expected.json").read_text()))

    return load


@pytest.fixture
def contract_sample():
    """contract_sample("risk.Returns") -> the sample payload in tests/contracts/<name>/sample.json."""

    def load(name: str) -> dict:
        return json.loads((TESTS / "contracts" / name / "sample.json").read_text())

    return load


@pytest.fixture
def contract_fake():
    """contract_fake("mdata.load_prices") -> the fake module in tests/contracts/<name>/fake.py."""

    def load(name: str):
        path = TESTS / "contracts" / name / "fake.py"
        spec = importlib.util.spec_from_file_location(f"fake_{name.replace('.', '_')}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load
