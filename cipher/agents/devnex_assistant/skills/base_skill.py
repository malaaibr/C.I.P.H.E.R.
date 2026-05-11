"""Abstract base class for all DevNex V-cycle skills."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ISkill(ABC):
    """
    @brief Abstract interface every DevNex skill must implement.

    @details
    Skills are thin adapters that translate a ParsedIntent + WorkingContext
    into one or more orchestrator node calls, then return a TaskResult.
    """

    def __init__(self, orchestrator) -> None:
        self.orchestrator = orchestrator

    @abstractmethod
    def execute(self, intent, context) -> object:
        """
        @brief Execute the skill for the given intent and context.

        @param intent  ParsedIntent from IntentClassifier.
        @param context WorkingContext from ContextManager.
        @return        TaskResult with status, output, and artifact paths.
        """
