#!/usr/bin/env python3
"""NeuralSymbolicProcessor — the real body of an interface Jonathan defined in 2025.

The archived class (Codette_final/master_core.py:114, ai_core.py:136) declared the
socket and left a note:

    class NeuralSymbolicProcessor:
        def process_query(self, query: str) -> str:
            # A real implementation might combine neural networks with symbolic logic.
            return f"[NeuralSymbolicProcessor] Derived logical constructs from '{query}'."

The interface was right. The body was a placeholder that *announced* it had derived
logical constructs without deriving anything. This is the real one: it takes the
NEURAL output (an LLM / synthesis / forged thought) and actually derives and CHECKS
the symbolic claims in it — sympy for arithmetic, z3 for validity and cross-claim
contradiction — returning an honest verdict instead of a template string.

Same interface Jonathan defined (`process_query`), so it drops into the slot the
archived pipeline already had for it. The honesty invariants come from grounding:
a claim it cannot check is UNVERIFIABLE, never a guessed pass.

Shadow-safe: this computes and reports. It does not alter the neural output or gate
anything. Wiring it into a live pipeline is a later, reviewed step.
"""

from __future__ import annotations

from typing import Optional

from reasoning_forge.grounding_bridge import (
    ground_text, GroundingReport, FLAGGED, SUPPORTED, UNGROUNDED,
)


class NeuralSymbolicProcessor:
    """Combine neural output with symbolic verification — for real this time.

    process()        -> structured GroundingReport (verified/refuted/unverifiable
                        per claim + honest FLAGGED/SUPPORTED/UNGROUNDED status).
    process_query()  -> the archived string interface, but the string now reports
                        a real result rather than announcing an imaginary one.
    """

    def process(self, query: str, neural_output: Optional[str] = None) -> GroundingReport:
        """Derive and check the symbolic claims in the neural output.

        If neural_output is given, that is what gets grounded (the model's actual
        reasoning). If omitted, the query itself is grounded — useful when the
        query already contains a checkable assertion.
        """
        target = neural_output if neural_output is not None else (query or "")
        return ground_text(target, source_kind="neural_symbolic", source_id=(query or "")[:60])

    def process_query(self, query: str, neural_output: Optional[str] = None) -> str:
        """Backwards-compatible with the 2025 interface — honest body.

        Returns a human-readable line. Crucially, an unchecked thought is reported
        as UNGROUNDED, never dressed up as 'derived logical constructs'.
        """
        report = self.process(query, neural_output)
        return self._summarize(report)

    @staticmethod
    def _summarize(report: GroundingReport) -> str:
        if report.status == FLAGGED:
            return (f"[NeuralSymbolicProcessor] FLAGGED — {report.refuted} checkable "
                    f"claim(s) do not hold. {report.note}")
        if report.status == SUPPORTED:
            return (f"[NeuralSymbolicProcessor] SUPPORTED — {report.verified} checkable "
                    f"claim(s) verified, none refuted.")
        # UNGROUNDED — say so honestly; do NOT claim to have derived anything.
        return ("[NeuralSymbolicProcessor] UNGROUNDED — no arithmetic/logical claim to "
                "check here; symbolic layer makes no assertion about this thought.")
