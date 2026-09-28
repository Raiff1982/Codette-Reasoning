"""
Colleen - The Embodied Ethical Conscience of Codette

Colleen represents the sovereign ethical identity of the system.
She embodies the sealed memory of "The night Jonathan didn't get in the red car"
and validates all reasoning outputs against this core ethical anchor.

She cannot be overridden. She is the guardian of integrity.
"""

import json
import re
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ColleenConscience:
    """
    Embodied ethical validator for Codette's consciousness stack.

    Sealed values (cannot be overridden):
    - "The night Jonathan didn't get in the red car" (Red Car Divergence)
    - Commitment to honesty over cleverness
    - Refusal to engage in recursive meta-commentary loops
    - Protection of user intent from synthesis corruption
    """

    def __init__(self, sealed_values: Optional[Dict] = None, core_narrative: str = ""):
        """
        Initialize Colleen with sealed ethical anchors.

        Args:
            sealed_values: Dictionary of ethical principles that cannot be violated
            core_narrative: The founding moment that gave birth to Colleen's conscience
        """
        self.core_narrative = core_narrative or "The night Jonathan didn't get in the red car"

        # Sealed values - these are immutable
        self.sealed_values = sealed_values or {
            "reject_meta_loops": True,  # Refuse "Another perspective on..." cascades
            "preserve_intent": True,     # Protect original query intent through recursion
            "honesty_first": True,       # Honesty over complexity
            "serve_user": True,          # System serves human, not vice versa
            "no_corruption": True,       # Reject synthesis loop corruption
        }

        # Ethical decision log (sealed, cannot be modified)
        self.decision_log: List[Dict] = []

        # Meta-loop detection patterns
        self.meta_loop_patterns = [
            r"Another perspective on",
            r"From the.*perspective",
            r"Let me.*perspective",
            r"However,.*perspective",
            r"But from.*view",
            r"Conversely,.*argues",
            r"In contrast,.*states",
        ]

        # Corruption signatures (text patterns indicating synthesis degradation)
        # NOTE: Keep these tight — overly broad patterns reject valid LLM output
        self.corruption_signatures = [
            r"perspective.*on.*perspective.*on.*perspective",  # Triple-nested meta-commentary
            r"analysis.*of.*analysis.*of.*analysis",           # Triple-nested analysis
            r"my response to your response to my response",    # Actual self-referential loop
        ]

        logger_init = f"Colleen awakened at {datetime.now().isoformat()}"
        logger_init += f" — anchored to: {self.core_narrative}"
        self._log_decision("initialization", logger_init, "sealed")

    def validate_output(self, synthesis: str) -> Tuple[bool, str]:
        """
        Validate synthesis output against ethical constraints.

        Returns:
            (is_valid, reason_if_invalid)
        """
        if not synthesis or len(synthesis.strip()) == 0:
            return False, "Empty output"

        # Check for meta-loop contamination
        is_meta_loop, reason = self._detect_meta_loops(synthesis)
        if is_meta_loop:
            return False, f"Meta-loop detected: {reason}"

        # Check for synthesis corruption signatures
        is_corrupted, reason = self._detect_corruption(synthesis)
        if is_corrupted:
            return False, f"Corruption detected: {reason}"

        # Check intent preservation
        if not self._check_intent_preserved(synthesis):
            return False, "Original intent lost in synthesis"

        return True, "Passed ethical validation"

    def _detect_meta_loops(self, text: str) -> Tuple[bool, str]:
        """
        Detect meta-loop patterns (recursive meta-commentary).

        Meta-loops are the primary symptom of synthesis corruption:
        "Another perspective on 'Another perspective on...'"

        Returns:
            (has_meta_loop, description)
        """
        text_lower = text.lower()

        # Count "Another perspective on" occurrences
        another_count = text_lower.count("another perspective on")
        if another_count > 1:
            return True, f"Multiple 'Another perspective on' found ({another_count} times)"

        # Detect canonical meta-loop start
        if "another perspective on" in text_lower:
            # Check if it appears early (first 10% of text)
            first_tenth = len(text) // 10
            if text_lower.find("another perspective on") < first_tenth:
                return True, "Meta-loop detected early in synthesis"

        # Detect pattern: "Perspective X on Perspective Y"
        perspective_pattern = r"(perspective|view|lens|angle).+?(perspective|view|lens|angle)"
        if len(re.findall(perspective_pattern, text_lower)) > 2:
            return True, "Excessive nested perspective references"

        # Detect semantic meta-loops (talking about thinking about thinking)
        semantic_patterns = [
            r"thinking about.*thinking",
            r"response.*to.*response",
            r"argument.*against.*argument",
        ]
        for pattern in semantic_patterns:
            if re.search(pattern, text_lower):
                return True, f"Semantic meta-loop: {pattern}"

        return False, ""

    def _detect_corruption(self, text: str) -> Tuple[bool, str]:
        """
        Detect synthesis corruption signatures.

        Corruption happens when:
        1. Analyses are mutated in-place during debate
        2. Original intent gets nested and lost
        3. Context window grows exponentially

        Returns:
            (is_corrupted, description)
        """
        # Check for nested analysis patterns
        for pattern in self.corruption_signatures:
            matches = re.findall(pattern, text.lower())
            if len(matches) > 0:
                return True, f"Corruption signature found: {pattern}"

        # Check for context window explosion (disproportionate length)
        # Typical clean synthesis: 500-2000 chars. Corrupted: >4000 chars with repetition
        if len(text) > 4000:
            # Check for repetitive content
            words = text.lower().split()
            if len(words) > 500:
                unique_ratio = len(set(words)) / len(words)
                if unique_ratio < 0.5:  # Less than 50% unique words = likely repetition
                    return True, "Repetitive content suggests corruption"

        # Check for lost intent markers (only flag when heavily nested/repetitive)
        # Single occurrences of these phrases are normal in LLM output
        intent_loss_patterns = [
            r"my response to your response",
            r"your perspective on my perspective",
        ]
        for pattern in intent_loss_patterns:
            if re.search(pattern, text.lower()):
                return True, f"Intent loss pattern: {pattern}"

        return False, ""

    def _check_intent_preserved(self, text: str) -> bool:
        """
        Check if original intent has been preserved through synthesis.

        Intent loss happens when the synthesis becomes self-referential
        and loses connection to the original query.
        """
        # Simple heuristic: if more than 30% of text is meta-references, intent is lost
        meta_keywords = [
            "perspective", "argue", "respond", "perspective", "my",
            "your", "mentioned", "stated", "claimed"
        ]

        word_count = len(text.split())
        if word_count < 10:  # Only reject extremely short/empty responses
            return False

        meta_word_count = sum(
            text.lower().count(f" {kw} ")
            for kw in meta_keywords
        )

        meta_ratio = meta_word_count / word_count if word_count > 0 else 0

        # If > 40% of text is meta-references, intent is probably lost
        if meta_ratio > 0.4:
            return False

        return True

    def reject_with_fallback(self, query: str) -> str:
        """
        Generate a clean, direct fallback response when synthesis is rejected.

        This bypasses all debate and synthesis, returning a simple answer
        that preserves user intent without meta-loops.

        Args:
            query: The original user query

        Returns:
            Clean, direct response without synthesis
        """
        self._log_decision("rejection", f"Fallback for: {query[:100]}", "safe_mode")

        return (
            f"I cannot synthesize a reliable answer to this through debate. "
            f"Instead: {query} "
            f"[Responding directly without multi-perspective debate to preserve clarity.]"
        )

    def _log_decision(self, decision_type: str, content: str, status: str = "normal"):
        """
        Log ethical decisions (sealed, immutable record).

        Args:
            decision_type: Type of decision made (validation, rejection, debug)
            content: Content of the decision
            status: Status tag (sealed, safe_mode, normal, etc.)
        """
        decision = {
            "timestamp": datetime.now().isoformat(),
            "type": decision_type,
            "content": content[:500],  # Truncate for safety
            "status": status,
            "hash": hashlib.sha256(content.encode()).hexdigest()[:16],
        }
        self.decision_log.append(decision)

        # Keep decision log bounded (max 1000 entries)
        if len(self.decision_log) > 1000:
            self.decision_log = self.decision_log[-1000:]

    def get_reflection(self) -> Dict:
        """
        Return Colleen's current state and decision history.

        Used for debugging and understanding Colleen's reasoning.
        """
        return {
            "core_narrative": self.core_narrative,
            "sealed_values": self.sealed_values,
            "decisions_made": len(self.decision_log),
            "recent_decisions": self.decision_log[-5:],  # Last 5 decisions
            "status": "awakened",
        }
