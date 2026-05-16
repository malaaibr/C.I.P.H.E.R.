"""
asil_gate.py — GCL (Governance + Compliance Layer) — ASIL Safety Gate
======================================================================
Implements the ISO 26262 ASIL-aware merge decision gate for CIPHER.

Decision table
--------------
+--------+-------------------+----------------------------------+
| ASIL   | Overlap detected  | Action                           |
+========+===================+==================================+
| D      | YES               | HARD_BLOCK  (G5 Safety Engineer) |
| C      | YES               | HOLD        (Safety Eng review)  |
| B      | YES               | HOLD        (Tech Lead / BSW)    |
| A/QM   | YES               | WARN        (developer)          |
| ANY    | NO                | PASS                             |
+--------+-------------------+----------------------------------+

CIPHER integration
------------------
The gate is invoked by ``uc4_4_skill.py`` and by
``DevNexOrchestrator.run_uc4_4_semantic_check()``.  A ``HARD_BLOCK``
decision raises :class:`SemanticConflictError` so the calling node is
marked ``status="error"`` in the GUI and the audit log.

ASPICE SWE.2: this module is the G4 (Behaviour Verification) and G5
(Evidence Sign-off) gate implementation for ASIL-D UCs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ── Error ─────────────────────────────────────────────────────────────────────

class SemanticConflictError(Exception):
    """
    Raised when a post-merge semantic memory overlap is detected at ASIL-D.

    This is a hard-blocking error — the merge MUST NOT be committed until a
    Safety Engineer has reviewed and resolved the conflict.
    """


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AsilDecision:
    """Result of an ASIL gate evaluation."""

    asil_level:               str   # "D", "C", "B", "A", "QM"
    has_overlap:              bool
    action:                   str   # "HARD_BLOCK" | "HOLD" | "WARN" | "PASS"
    require_safety_engineer:  bool
    gate:                     str   # "G5" | "G4" | "G3" | "PASS"
    rationale:                str

    @property
    def is_blocking(self) -> bool:
        """True when the action prevents the merge from proceeding."""
        return self.action in ("HARD_BLOCK", "HOLD")


# ── Gate ──────────────────────────────────────────────────────────────────────

_ACTIONS: Final[dict[str, tuple[str, bool, str, str]]] = {
    # asil → (action, require_safety_engineer, gate, rationale)
    "D": (
        "HARD_BLOCK",
        True,
        "G5",
        "ISO 26262 ASIL-D: RAM overlap constitutes undeclared undefined behaviour "
        "(MISRA-C:2012 R1.3).  Merge BLOCKED until Safety Engineer sign-off (G5).",
    ),
    "C": (
        "HOLD",
        True,
        "G5",
        "ISO 26262 ASIL-C: RAM overlap is a critical safety defect. "
        "Merge HELD pending Safety Engineer review.",
    ),
    "B": (
        "HOLD",
        False,
        "G4",
        "ISO 26262 ASIL-B: RAM overlap requires BSW / Tech Lead review (G4). "
        "Merge HELD until approval.",
    ),
    "A": (
        "WARN",
        False,
        "G3",
        "ISO 26262 ASIL-A: RAM overlap detected — developer review recommended (G3).",
    ),
    "QM": (
        "WARN",
        False,
        "G3",
        "QM: RAM overlap detected — developer review recommended.",
    ),
}


class AsilGate:
    """
    ISO 26262 ASIL-aware merge safety gate.

    Parameters
    ----------
    asil_level : str
        ASIL classification for the merge context (``"D"``, ``"C"``,
        ``"B"``, ``"A"``, ``"QM"``).

    Raises
    ------
    ValueError
        When *asil_level* is not in the recognised set.
    """

    _VALID_LEVELS: Final[frozenset[str]] = frozenset({"D", "C", "B", "A", "QM"})

    def __init__(self, asil_level: str) -> None:
        if asil_level not in self._VALID_LEVELS:
            raise ValueError(
                f"Unknown ASIL level '{asil_level}'. "
                f"Valid: {sorted(self._VALID_LEVELS)}"
            )
        self._asil_level = asil_level

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(self, has_overlap: bool) -> AsilDecision:
        """
        Evaluate the gate for the given overlap status.

        Parameters
        ----------
        has_overlap : bool
            True when ``RamOverlapDetector`` found at least one address collision.

        Returns
        -------
        AsilDecision
            Frozen dataclass describing the recommended action and gate.
        """
        if not has_overlap:
            return AsilDecision(
                asil_level=self._asil_level,
                has_overlap=False,
                action="PASS",
                require_safety_engineer=False,
                gate="PASS",
                rationale="No RAM overlap detected — merge may proceed.",
            )

        action, req_se, gate, rationale = _ACTIONS[self._asil_level]
        return AsilDecision(
            asil_level=self._asil_level,
            has_overlap=True,
            action=action,
            require_safety_engineer=req_se,
            gate=gate,
            rationale=rationale,
        )

    def enforce(self, has_overlap: bool) -> AsilDecision:
        """
        Evaluate the gate and raise :class:`SemanticConflictError` when
        the decision is HARD_BLOCK.

        This is the single entry-point used by orchestrator integration;
        it ensures ASIL-D overlaps always abort the pipeline with a clear
        traceable exception.

        Parameters
        ----------
        has_overlap : bool
            True when RAM overlap has been detected.

        Returns
        -------
        AsilDecision
            Non-blocking decisions (HOLD, WARN, PASS) are returned for
            the caller to log/report.

        Raises
        ------
        SemanticConflictError
            Immediately when action is HARD_BLOCK (ASIL-D overlap).
        """
        decision = self.evaluate(has_overlap)
        if decision.action == "HARD_BLOCK":
            raise SemanticConflictError(
                f"[ASIL-{self._asil_level} HARD BLOCK] {decision.rationale}"
            )
        return decision
