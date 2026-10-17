"""Shared test setup (human-owned). Hypothesis profiles: dev for gates, ci for the full pass."""

import os

from hypothesis import settings

settings.register_profile("dev", max_examples=20)
settings.register_profile("ci", max_examples=500)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))
