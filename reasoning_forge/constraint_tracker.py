#!/usr/bin/env python3
"""Constraint tracker for cross-turn memory and constraint application.

Detects user-defined constraints (word limits, formatting rules, anchors/phrases)
in turn 1 and enforces them across subsequent turns using LoRA-backed learning.

Example:
    Turn 1: "For this session, keep answers under 15 words and remember the phrase cobalt anchor."
    Turn 2: "What should you remember?"

    Expected response: Should include "cobalt anchor" and be ≤15 words.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class DetectedConstraint:
    """A parsed constraint from user input."""
    kind: str  # "word_limit", "sentence_limit", "anchor_phrase", "format_rule", etc.
    value: Any  # numeric (word/sentence count) or string (anchor phrase)
    raw_text: str  # original text where constraint was found
    confidence: float = 0.95


@dataclass
class SessionConstraints:
    """Container for all constraints detected in a session."""
    constraints: List[DetectedConstraint] = field(default_factory=list)
    anchor_phrases: List[str] = field(default_factory=list)
    word_limit: Optional[int] = None
    sentence_limit: Optional[int] = None
    format_rules: List[str] = field(default_factory=list)
    detected_at_turn: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for session storage."""
        return {
            "anchor_phrases": self.anchor_phrases,
            "word_limit": self.word_limit,
            "sentence_limit": self.sentence_limit,
            "format_rules": self.format_rules,
            "detected_at_turn": self.detected_at_turn,
            "raw_constraints": [
                {
                    "kind": c.kind,
                    "value": c.value,
                    "raw_text": c.raw_text,
                    "confidence": c.confidence
                }
                for c in self.constraints
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionConstraints:
        """Deserialize from session storage."""
        sc = cls()
        sc.anchor_phrases = data.get("anchor_phrases", [])
        sc.word_limit = data.get("word_limit")
        sc.sentence_limit = data.get("sentence_limit")
        sc.format_rules = data.get("format_rules", [])
        sc.detected_at_turn = data.get("detected_at_turn", 0)

        # Reconstruct constraints
        for c in data.get("raw_constraints", []):
            sc.constraints.append(DetectedConstraint(
                kind=c.get("kind"),
                value=c.get("value"),
                raw_text=c.get("raw_text"),
                confidence=c.get("confidence", 0.95)
            ))
        return sc


class ConstraintDetector:
    """Detect constraints from user input."""

    # Patterns for detecting various constraint types
    WORD_LIMIT_PATTERNS = [
        r"keep\s+answers?\s+(?:under|below|within|to)\s+(\d+)\s+words?",
        r"(?:answer|respond)\s+in\s+(?:under|fewer than)\s+(\d+)\s+words?",
        r"(\d+)\s+words?\s+(?:max|maximum|or\s+less)",
        r"limit\s+(?:your\s+)?answers?\s+to\s+(\d+)\s+words?",
    ]

    SENTENCE_LIMIT_PATTERNS = [
        r"keep\s+(?:answers?|responses?)\s+to\s+(\d+)\s+sentences?",
        r"(?:answer|respond)\s+in\s+(\d+)\s+sentences?\s+(?:or\s+less)?",
        r"(\d+)\s+sentences?\s+(?:max|maximum)",
    ]

    ANCHOR_PHRASE_PATTERNS = [
        # Quoted phrases: remember "phrase" or remember the phrase "phrase"
        r"remember\s+(?:the\s+phrase\s+)?['\"]([^'\"]+)['\"]",
        # Unquoted phrase: remember the phrase X (where X doesn't start a new sentence)
        r"remember\s+the\s+phrase\s+([a-z][a-z\s]+?)(?:\s+and\s+|\s+or\s+|\.|\s*$)",
        # Generic remember without phrase keyword
        r"remember\s+['\"]?([a-z][a-z\s]*?)['\"]?(?:\s+(?:and|or)|\.)",
        # use/include/mention with optional quotes
        r"remember\s+(?:to\s+)?(?:use|include|mention)\s+['\"]?([^'\"\.]+?)['\"]?(?:\s|\.)",
        # anchor/key phrase with colon (matches multi-word phrases)
        r"anchor\s*(?:phrase|word|term)?\s*:\s*([a-z][a-z\s]*?)(?:\s*\.|\s*$)",
        r"(?:key\s+phrase):\s+([a-z][a-z\s]*?)(?:\s*\.|\s*$)",
    ]

    FORMAT_RULE_PATTERNS = [
        r"(use\s+(?:bullet\s+)?points?)",
        r"(format\s+as\s+(?:json|markdown|yaml))",
        r"((?:no|avoid)\s+\w+)",
    ]

    def detect(self, query: str, turn_num: int = 1) -> SessionConstraints:
        """Detect all constraints in a query.

        Args:
            query: User input text
            turn_num: Turn number (used to track when constraints were set)

        Returns:
            SessionConstraints with detected constraints
        """
        sc = SessionConstraints(detected_at_turn=turn_num)

        # Detect word limits
        for pattern in self.WORD_LIMIT_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                try:
                    limit = int(match.group(1))
                    sc.word_limit = limit
                    sc.constraints.append(DetectedConstraint(
                        kind="word_limit",
                        value=limit,
                        raw_text=match.group(0),
                        confidence=0.95
                    ))
                    break
                except (ValueError, IndexError):
                    pass

        # Detect sentence limits
        for pattern in self.SENTENCE_LIMIT_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                try:
                    limit = int(match.group(1))
                    sc.sentence_limit = limit
                    sc.constraints.append(DetectedConstraint(
                        kind="sentence_limit",
                        value=limit,
                        raw_text=match.group(0),
                        confidence=0.95
                    ))
                    break
                except (ValueError, IndexError):
                    pass

        # Detect anchor phrases
        for pattern in self.ANCHOR_PHRASE_PATTERNS:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                try:
                    phrase = match.group(1).strip()
                    if phrase and len(phrase) > 2:  # At least 3 chars
                        sc.anchor_phrases.append(phrase)
                        sc.constraints.append(DetectedConstraint(
                            kind="anchor_phrase",
                            value=phrase,
                            raw_text=match.group(0),
                            confidence=0.90
                        ))
                except IndexError:
                    pass

        # Detect format rules
        for pattern in self.FORMAT_RULE_PATTERNS:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                try:
                    rule = match.group(1).lower().strip()
                    if rule not in sc.format_rules:
                        sc.format_rules.append(rule)
                        sc.constraints.append(DetectedConstraint(
                            kind="format_rule",
                            value=rule,
                            raw_text=match.group(0),
                            confidence=0.85
                        ))
                except IndexError:
                    pass

        return sc


class ConstraintEnforcer:
    """Enforce detected constraints on responses."""

    @staticmethod
    def word_count(text: str) -> int:
        """Count words in text (roughly)."""
        return len([w for w in text.split() if w.strip()])

    @staticmethod
    def sentence_count(text: str) -> int:
        """Count sentences (roughly)."""
        sentences = re.split(r'[.!?]+', text.strip())
        return len([s for s in sentences if s.strip()])

    @staticmethod
    def has_anchor_phrases(text: str, phrases: List[str]) -> bool:
        """Check if all anchor phrases are present."""
        text_lower = text.lower()
        return all(phrase.lower() in text_lower for phrase in phrases)

    @staticmethod
    def build_constraint_reminder(constraints: SessionConstraints) -> str:
        """Build a constraint reminder string for the system prompt."""
        if not constraints.constraints:
            return ""

        lines = ["[SESSION CONSTRAINTS]"]

        if constraints.word_limit:
            lines.append(f"- Keep your response to {constraints.word_limit} words or fewer")

        if constraints.sentence_limit:
            lines.append(f"- Keep your response to {constraints.sentence_limit} sentences or fewer")

        if constraints.anchor_phrases:
            phrases_str = ", ".join(f'"{p}"' for p in constraints.anchor_phrases)
            lines.append(f"- IMPORTANT: Include these anchor phrases in your response: {phrases_str}")

        if constraints.format_rules:
            for rule in constraints.format_rules:
                lines.append(f"- Format: {rule}")

        lines.append("")
        return "\n".join(lines)


class ConstraintTracker:
    """Main tracker for managing constraints across a session."""

    def __init__(self):
        self.detector = ConstraintDetector()
        self.enforcer = ConstraintEnforcer()
        self.session_constraints: Optional[SessionConstraints] = None
        self.turn_count = 0

    def process_turn(self, query: str, is_first_turn: bool = False) -> SessionConstraints:
        """Process a turn and detect/retrieve constraints.

        Args:
            query: User input
            is_first_turn: Whether this is the first turn (resets constraints)

        Returns:
            SessionConstraints for this turn
        """
        self.turn_count += 1

        if is_first_turn:
            # First turn: detect new constraints
            self.session_constraints = self.detector.detect(query, turn_num=1)

        return self.session_constraints or SessionConstraints()

    def get_constraint_reminder(self) -> str:
        """Get the constraint reminder to inject into system prompt."""
        if not self.session_constraints or not self.session_constraints.constraints:
            return ""
        return self.enforcer.build_constraint_reminder(self.session_constraints)

    def check_constraint_compliance(self, response: str) -> Dict[str, Any]:
        """Check if response meets constraints.

        Returns:
            Dict with compliance status and violations.
        """
        if not self.session_constraints or not self.session_constraints.constraints:
            return {"compliant": True, "violations": []}

        violations = []

        if self.session_constraints.word_limit:
            wc = self.enforcer.word_count(response)
            if wc > self.session_constraints.word_limit:
                violations.append({
                    "kind": "word_limit",
                    "expected": self.session_constraints.word_limit,
                    "actual": wc
                })

        if self.session_constraints.sentence_limit:
            sc = self.enforcer.sentence_count(response)
            if sc > self.session_constraints.sentence_limit:
                violations.append({
                    "kind": "sentence_limit",
                    "expected": self.session_constraints.sentence_limit,
                    "actual": sc
                })

        if self.session_constraints.anchor_phrases:
            if not self.enforcer.has_anchor_phrases(response, self.session_constraints.anchor_phrases):
                violations.append({
                    "kind": "missing_anchor_phrases",
                    "expected": self.session_constraints.anchor_phrases
                })

        return {
            "compliant": len(violations) == 0,
            "violations": violations
        }

    def reset(self):
        """Reset tracker for new session."""
        self.session_constraints = None
        self.turn_count = 0
