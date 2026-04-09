"""
Debate Tracker - Session-scoped intellectual position memory.

Tracks what positions Codette has argued, what has been conceded,
and what remains under active defense. Prevents:

  1. Position flip-flopping (arguing X, then agreeing with not-X two turns later)
  2. Silent self-contradiction (counterargument whose sub-points invalidate each other)
  3. Premature concession of uncontested claims

Key distinction: Codette CAN update a position if the user's argument is logically
sound. The tracker records the update explicitly, so it's not hidden drift — it's
visible reasoning.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


@dataclass
class Position:
    """A claim or stance Codette has taken."""
    claim: str                          # The core assertion
    turn: int                           # When it was taken
    domain: str                         # Topic area (e.g., "intelligence", "recursion")
    strength: float = 1.0               # 0.0=abandoned, 0.5=softened, 1.0=held
    conceded_to: Optional[str] = None   # If softened/abandoned, what replaced it
    concession_reason: str = ""         # Why it was updated


@dataclass
class DebateState:
    """Full debate state for one session."""
    positions: List[Position] = field(default_factory=list)
    turn_count: int = 0
    active_domains: List[str] = field(default_factory=list)
    user_claims: List[str] = field(default_factory=list)   # What the user has argued


class CounterArgumentCoherenceChecker:
    """
    Checks whether a multi-point counterargument is internally consistent.

    The ChatGPT failure mode: arguing both "education works universally" AND
    "AI must customize per individual" in the same counterargument — the two
    claims invalidate each other.
    """

    # Pairs of concepts that tend to contradict each other in debate contexts
    _TENSION_PAIRS = [
        # universal vs individual
        (r"\b(universal|all|every(one)?|across the board|broad|population.wide)\b",
         r"\b(individual|per.person|tailored|customized|personalized|unique to each)\b"),
        # fixed vs emergent
        (r"\b(fixed|static|predetermined|innate|genetic(ally)?|inherited|hard.wired)\b",
         r"\b(emergent|adaptive|plastic|shaped by|evolves|changes with|flexible)\b"),
        # linear vs non-linear
        (r"\b(linear|predictable|consistent|uniform|standard(ized)?)\b",
         r"\b(non.linear|unpredictable|variable|irregular|chaotic|stochastic)\b"),
        # deterministic vs probabilistic
        (r"\b(determined|deterministic|certain|definite|absolute)\b",
         r"\b(probabilistic|uncertain|variable|statistical(ly)?|depends on)\b"),
        # bounded vs unbounded
        (r"\b(cap(ped)?|limit(ed)?|ceiling|max(imum)?|bounded|finite)\b",
         r"\b(unlimited|unbounded|infinite|no (upper )?limit|endless|infinite potential)\b"),
    ]

    _TENSION_RE = [
        (re.compile(a, re.IGNORECASE), re.compile(b, re.IGNORECASE))
        for a, b in _TENSION_PAIRS
    ]

    def check(self, text: str) -> Dict:
        """
        Check a counterargument for internal tensions.

        Returns:
            {
                "coherent": bool,
                "tensions": List[str],   # descriptions of found tensions
                "severity": float,       # 0.0 (none) to 1.0 (severe)
            }
        """
        tensions = []

        # Split into numbered points / bullet points if present
        points = self._split_into_points(text)

        if len(points) < 2:
            # Single point — check against itself for embedded contradiction
            points = [text]

        # Check each pair of points for tension
        for i, point_a in enumerate(points):
            for j, point_b in enumerate(points):
                if i >= j:
                    continue
                for pat_a, pat_b in self._TENSION_RE:
                    a_has_first = bool(pat_a.search(point_a))
                    b_has_second = bool(pat_b.search(point_b))
                    a_has_second = bool(pat_b.search(point_a))
                    b_has_first = bool(pat_a.search(point_b))

                    # Direct cross-point tension
                    if (a_has_first and b_has_second) or (a_has_second and b_has_first):
                        tensions.append(
                            f"Point {i+1} uses '{pat_a.pattern[:30]}' concept "
                            f"while Point {j+1} uses '{pat_b.pattern[:30]}' concept — "
                            f"potential internal contradiction"
                        )
                        break  # one tension per pair is enough

        severity = min(1.0, len(tensions) * 0.35)
        return {
            "coherent": len(tensions) == 0,
            "tensions": tensions,
            "severity": severity,
        }

    def _split_into_points(self, text: str) -> List[str]:
        """Split numbered list or bullet points into individual claims."""
        # Try numbered list
        numbered = re.split(r'\n\s*\d+[.)]\s+', text)
        if len(numbered) > 1:
            return [p.strip() for p in numbered if p.strip()]

        # Try bullet points
        bulleted = re.split(r'\n\s*[-*•]\s+', text)
        if len(bulleted) > 1:
            return [p.strip() for p in bulleted if p.strip()]

        # Try sentence splitting as fallback
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]


class DebateTracker:
    """
    Session-scoped tracker for intellectual positions.

    Usage:
        tracker = DebateTracker()
        tracker.record_position("intelligence is not purely genetic", domain="intelligence")
        result = tracker.check_consistency(new_response_text)
        if not result["consistent"]:
            # flag or revise before output
    """

    def __init__(self):
        self.state = DebateState()
        self.coherence_checker = CounterArgumentCoherenceChecker()

    def record_position(self, claim: str, domain: str = "general", strength: float = 1.0):
        """Register a new position Codette is taking."""
        self.state.turn_count += 1
        pos = Position(
            claim=claim,
            turn=self.state.turn_count,
            domain=domain,
            strength=strength,
        )
        self.state.positions.append(pos)
        if domain not in self.state.active_domains:
            self.state.active_domains.append(domain)

    def record_user_claim(self, claim: str):
        """Record what the user is asserting (for tracking what's been challenged)."""
        self.state.user_claims.append(claim)

    def update_position(self, original_claim: str, reason: str, new_strength: float, conceded_to: str = ""):
        """
        Explicitly update a position (softened or abandoned).
        This is legitimate — positions can change when logic demands it.
        The tracker makes the change visible rather than silent.
        """
        for pos in self.state.positions:
            if original_claim.lower() in pos.claim.lower():
                pos.strength = new_strength
                pos.concession_reason = reason
                pos.conceded_to = conceded_to
                return True
        return False

    def check_consistency(self, new_response: str) -> Dict:
        """
        Check whether a new response is consistent with held positions.

        Returns:
            {
                "consistent": bool,
                "flip_detected": bool,
                "flipped_claims": List[str],
                "internal_tensions": Dict,    # from CounterArgumentCoherenceChecker
                "summary": str,
            }
        """
        held_positions = [p for p in self.state.positions if p.strength >= 0.6]

        flip_detected = False
        flipped_claims = []

        for pos in held_positions:
            # Look for negation of held position in new response
            key_terms = self._extract_key_terms(pos.claim)
            for term in key_terms:
                # Negation before term: "not X", "never X", "doesn't X"
                before = rf"\b(not|never|no longer|isn't|aren't|doesn't|don't|cannot|no)\b.{{0,60}}{re.escape(term)}"
                # Negation after term: "X plays no role", "X has no effect", "X is not"
                after = rf"{re.escape(term)}.{{0,60}}\b(no |not |never |isn't|aren't|doesn't|don't|plays no|has no|have no|holds no)\b"
                # "X is irrelevant", "X is meaningless", "X doesn't matter"
                dismissal = rf"{re.escape(term)}.{{0,40}}\b(irrelevant|meaningless|negligible|plays no|has no (role|effect|impact)|doesn't matter)\b"
                if (re.search(before, new_response, re.IGNORECASE) or
                        re.search(after, new_response, re.IGNORECASE) or
                        re.search(dismissal, new_response, re.IGNORECASE)):
                    flip_detected = True
                    flipped_claims.append(pos.claim)
                    break

        # Check internal coherence of the new response itself
        internal = self.coherence_checker.check(new_response)

        consistent = not flip_detected and internal["coherent"]
        summary_parts = []
        if flip_detected:
            summary_parts.append(f"Potential position flip on: {flipped_claims}")
        if not internal["coherent"]:
            summary_parts.append(f"Internal tensions: {internal['tensions']}")

        return {
            "consistent": consistent,
            "flip_detected": flip_detected,
            "flipped_claims": flipped_claims,
            "internal_tensions": internal,
            "summary": "; ".join(summary_parts) if summary_parts else "consistent",
        }

    def get_active_positions(self) -> List[Position]:
        """Return positions still being held (strength >= 0.6)."""
        return [p for p in self.state.positions if p.strength >= 0.6]

    def reset(self):
        """Clear session state (call between conversations)."""
        self.state = DebateState()

    def _extract_key_terms(self, claim: str) -> List[str]:
        """Extract the most meaningful terms from a claim for consistency checking."""
        # Remove stop words and short tokens
        stop_words = {
            "is", "are", "was", "were", "the", "a", "an", "and", "or", "but",
            "in", "on", "at", "to", "for", "of", "with", "by", "not", "it",
            "this", "that", "can", "just", "only", "very", "also", "be",
        }
        tokens = re.findall(r'\b[a-zA-Z]{4,}\b', claim.lower())
        return [t for t in tokens if t not in stop_words][:5]
