"""
CognitiveUnit — portable interface contract for Codette's reasoning engine.

Pattern: Hexagonal Architecture / Ports-and-Adapters (Cockburn 2005).
The ForgeEngine implements this protocol. Deployment skins (Gradio, REST,
CLI, Claude tool) depend only on this interface, never on ForgeEngine directly.

This allows Codette to run as a local app, HTTP microservice, Claude tool,
or any other deployment target without changing the reasoning core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class Turn:
    query: str
    session_id: str = "default"
    domain_hint: Optional[str] = None      # optional domain pre-routing hint
    debate_rounds: int = 2


@dataclass
class TurnResult:
    content: str                            # final verbalized response
    intent: dict = field(default_factory=dict)          # ReasonedIntent as dict
    verbalization_prompt: str = ""          # prompt used for LLM verbalization
    metadata: dict = field(default_factory=dict)
    session_id: str = "default"


@dataclass
class Feedback:
    session_id: str
    helpful: bool
    note: str = ""


@dataclass
class CognitiveSnapshot:
    session_id: str
    memory_export: str          # JSON from LivingMemoryKernel.export()
    cocoon_count: int
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class CognitiveUnit(Protocol):
    """
    Clean port contract. Any class that implements these four methods
    can be used as a deployment-agnostic Codette reasoning unit.
    """

    def process_turn(self, turn: Turn) -> TurnResult:
        """Process one user turn and return a structured result."""
        ...

    def receive_feedback(self, feedback: Feedback) -> None:
        """Record feedback signal for memory weighting."""
        ...

    def export_state(self) -> CognitiveSnapshot:
        """Snapshot current memory and session state."""
        ...

    def restore_state(self, snapshot: CognitiveSnapshot) -> None:
        """Restore from a snapshot (warm-start or cross-deployment transfer)."""
        ...
