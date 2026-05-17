"""Budget Enforcer — prevents runaway agent tasks.

Enforces three limits per task execution:
  1. Token cap (input + output tokens combined)
  2. Wall-clock time limit
  3. LLM call count

When any limit is breached, raises BudgetExceededError with the specific
limit that was hit, allowing the caller to handle gracefully (e.g. escalate
to HITL or terminate the Draft-Verify-Finalize loop).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class BudgetLimitKind(StrEnum):
    TOKEN = "TOKEN"
    TIME = "TIME"
    CALL_COUNT = "CALL_COUNT"


class BudgetExceededError(Exception):
    """Raised when a budget limit is breached."""

    def __init__(self, kind: BudgetLimitKind, limit: float, actual: float) -> None:
        self.kind = kind
        self.limit = limit
        self.actual = actual
        super().__init__(
            f"Budget exceeded: {kind.value} limit={limit}, actual={actual}"
        )


@dataclass
class BudgetConfig:
    """Budget limits for a single task execution."""

    max_tokens: int = 100_000
    max_wall_clock_s: float = 300.0
    max_llm_calls: int = 10


@dataclass
class BudgetEnforcer:
    """Tracks resource consumption and enforces limits."""

    config: BudgetConfig = field(default_factory=BudgetConfig)
    _tokens_used: int = field(default=0, init=False)
    _llm_calls: int = field(default=0, init=False)
    _start_time: float = field(default=0.0, init=False)
    _started: bool = field(default=False, init=False)

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._tokens_used = 0
        self._llm_calls = 0
        self._started = True

    def record_llm_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record one LLM call and its token consumption. Raises on breach."""
        if not self._started:
            self.start()

        self._llm_calls += 1
        self._tokens_used += input_tokens + output_tokens

        if self._llm_calls > self.config.max_llm_calls:
            raise BudgetExceededError(
                BudgetLimitKind.CALL_COUNT,
                self.config.max_llm_calls,
                self._llm_calls,
            )

        if self._tokens_used > self.config.max_tokens:
            raise BudgetExceededError(
                BudgetLimitKind.TOKEN,
                self.config.max_tokens,
                self._tokens_used,
            )

        self.check_time()

    def check_time(self) -> None:
        """Check wall-clock time limit. Raises on breach."""
        if not self._started:
            return
        elapsed = time.monotonic() - self._start_time
        if elapsed > self.config.max_wall_clock_s:
            raise BudgetExceededError(
                BudgetLimitKind.TIME,
                self.config.max_wall_clock_s,
                elapsed,
            )

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    @property
    def llm_calls(self) -> int:
        return self._llm_calls

    @property
    def elapsed_s(self) -> float:
        if not self._started:
            return 0.0
        return time.monotonic() - self._start_time

    @property
    def tokens_remaining(self) -> int:
        return max(0, self.config.max_tokens - self._tokens_used)

    @property
    def calls_remaining(self) -> int:
        return max(0, self.config.max_llm_calls - self._llm_calls)
