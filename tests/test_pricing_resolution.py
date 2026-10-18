# tests/test_pricing_resolution.py
"""
Model-name resolution in pricing.get_model_pricing.

The prefix fallback matches any table key that is a string prefix of the
model name, so "gpt-4.1-mini" is billed as gpt-4 ($30/$60) and
"gpt-5.5-mini" as gpt-5. A wrong family is worse than "unknown" because it
produces a confident, wrong cost figure.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pricing import PRICING, calculate_cost, get_model_pricing
from tests.fakes import known_bug

OPENAI = PRICING["openai"]


class TestResolutionThatWorks:

    def test_exact_match(self):
        assert get_model_pricing("openai", "gpt-4o-mini") == OPENAI["gpt-4o-mini"]

    def test_new_family_with_own_row(self):
        assert get_model_pricing("openai", "gpt-6-luna") == OPENAI["gpt-6-luna"]

    def test_dated_snapshot_resolves_to_longest_prefix(self):
        assert get_model_pricing("openai", "gpt-5-mini-2025-08-07") == OPENAI["gpt-5-mini"]

    def test_dated_gpt4o_does_not_fall_to_gpt4(self):
        assert get_model_pricing("openai", "gpt-4o-2024-08-06") == OPENAI["gpt-4o"]

    def test_dated_mini_does_not_fall_to_base(self):
        assert get_model_pricing("openai", "gpt-4o-mini-2024-07-18") == OPENAI["gpt-4o-mini"]

    def test_dated_anthropic_model(self):
        got = get_model_pricing("anthropic", "claude-sonnet-4-20250514")
        assert got == PRICING["anthropic"]["claude-sonnet-4"]

    def test_provider_is_case_insensitive(self):
        assert get_model_pricing("OpenAI", "gpt-4o") == OPENAI["gpt-4o"]

    def test_unknown_provider_returns_none(self):
        assert get_model_pricing("nope", "gpt-4o") is None

    def test_unknown_model_returns_none(self):
        assert get_model_pricing("openai", "totally-new-model") is None

    def test_calculate_cost_uses_per_million_rates(self):
        cost = calculate_cost("openai", "gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.15 + 0.60)

    def test_calculate_cost_none_when_unpriced(self):
        assert calculate_cost("openai", "totally-new-model", 10, 10) is None


class TestPrefixFallbackWrongFamily:

    @known_bug("'gpt-4.1-mini' prefix-matches gpt-4 and is billed $30/$60")
    @pytest.mark.parametrize("model", ["gpt-4.1-mini", "gpt-4.1"])
    def test_gpt41_never_priced_as_gpt4(self, model):
        got = get_model_pricing("openai", model)

        assert got is None or got == OPENAI.get(model)

    @known_bug("'gpt-5.5-mini' prefix-matches gpt-5 and is billed as the full model")
    def test_gpt55_mini_never_priced_as_gpt5(self):
        got = get_model_pricing("openai", "gpt-5.5-mini")

        assert got is None or got == OPENAI.get("gpt-5.5-mini")
