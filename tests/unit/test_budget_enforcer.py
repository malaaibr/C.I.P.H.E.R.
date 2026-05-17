"""Tests for the Budget Enforcer."""

import pytest

from cipher.are.budget_enforcer.enforcer import (
    BudgetConfig,
    BudgetEnforcer,
    BudgetExceededError,
    BudgetLimitKind,
)


class TestBudgetEnforcer:
    def test_normal_usage(self):
        enforcer = BudgetEnforcer(config=BudgetConfig(max_tokens=10000, max_llm_calls=5))
        enforcer.start()
        enforcer.record_llm_call(input_tokens=500, output_tokens=200)
        assert enforcer.tokens_used == 700
        assert enforcer.llm_calls == 1
        assert enforcer.tokens_remaining == 9300
        assert enforcer.calls_remaining == 4

    def test_token_limit_exceeded(self):
        enforcer = BudgetEnforcer(config=BudgetConfig(max_tokens=1000, max_llm_calls=10))
        enforcer.start()
        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.record_llm_call(input_tokens=800, output_tokens=300)
        assert exc_info.value.kind == BudgetLimitKind.TOKEN

    def test_call_count_exceeded(self):
        enforcer = BudgetEnforcer(config=BudgetConfig(max_tokens=100000, max_llm_calls=2))
        enforcer.start()
        enforcer.record_llm_call(input_tokens=100, output_tokens=100)
        enforcer.record_llm_call(input_tokens=100, output_tokens=100)
        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.record_llm_call(input_tokens=100, output_tokens=100)
        assert exc_info.value.kind == BudgetLimitKind.CALL_COUNT

    def test_auto_start_on_first_call(self):
        enforcer = BudgetEnforcer(config=BudgetConfig())
        enforcer.record_llm_call(input_tokens=100, output_tokens=50)
        assert enforcer.llm_calls == 1
        assert enforcer.elapsed_s > 0

    def test_elapsed_zero_when_not_started(self):
        enforcer = BudgetEnforcer(config=BudgetConfig())
        assert enforcer.elapsed_s == 0.0
