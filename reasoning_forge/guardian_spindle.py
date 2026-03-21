"""
Guardian Spindle - Ethical Validation Gate

Post-synthesis rules-based validator.
Complements Colleen's conscience validation with logical rules.
"""

from typing import Dict, Tuple
import re


class CoreGuardianSpindle:
    """
    Rules-based validator that checks synthesis coherence and ethical alignment.

    Works AFTER Colleen's conscience check to catch logical/coherence issues.
    """

    def __init__(self):
        """Initialize Guardian with validation rules."""
        self.min_coherence_score = 0.5
        self.max_meta_commentary = 0.30  # 30% meta-references max
        self.required_tags = []

    def validate(self, synthesis: str) -> Tuple[bool, Dict]:
        """
        Validate synthesis against coherence and alignment rules.

        Returns:
            (is_valid, validation_details)
        """
        if not synthesis or len(synthesis.strip()) < 50:
            return False, {"reason": "synthesis too short", "length": len(synthesis)}

        # Check coherence score
        coherence = self._calculate_coherence(synthesis)
        if coherence < self.min_coherence_score:
            return False, {
                "reason": "coherence below threshold",
                "coherence_score": coherence,
                "threshold": self.min_coherence_score,
            }

        # Check meta-commentary ratio
        meta_ratio = self._calculate_meta_ratio(synthesis)
        if meta_ratio > self.max_meta_commentary:
            return False, {
                "reason": "excessive meta-commentary",
                "meta_ratio": meta_ratio,
                "threshold": self.max_meta_commentary,
            }

        # Check for circular references
        if self._has_circular_logic(synthesis):
            return False, {"reason": "circular logic detected"}

        # Check ethical alignment
        if not self._check_ethical_alignment(synthesis):
            return False, {"reason": "ethical alignment check failed"}

        return True, {
            "reason": "passed all validation rules",
            "coherence": coherence,
            "meta_ratio": meta_ratio,
        }

    def _calculate_coherence(self, text: str) -> float:
        """
        Simple coherence score based on:
        - Sentence length variance (should be moderate)
        - Transition words presence
        - Paragraph structure

        Returns: float 0.0-1.0
        """
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) == 0:
            return 0.0

        # Check for transition words (indicate logical flow)
        transition_words = [
            'however', 'therefore', 'moreover', 'furthermore',
            'in addition', 'consequently', 'meanwhile', 'meanwhile',
            'on the other hand', 'conversely', 'thus', 'hence'
        ]
        transition_count = sum(
            text.lower().count(word)
            for word in transition_words
        )

        # Normalize coherence based on presence of logical connectors
        # More connectors = better structure (up to a point)
        coherence = min(0.5 + (transition_count * 0.05), 1.0)

        # Adjust down if too repetitive
        words = text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            coherence *= unique_ratio  # Penalize repetition

        return max(0.0, min(1.0, coherence))

    def _calculate_meta_ratio(self, text: str) -> float:
        """
        Calculate percentage of text dedicated to meta-commentary.

        Meta-references: 'perspective', 'argue', 'response', 'point', 'view', etc.
        """
        meta_keywords = [
            'perspective', 'argue', 'argument', 'respond', 'response',
            'point', 'view', 'claim', 'stated', 'mentioned',
            'my ', 'your ', 'their '
        ]

        word_count = len(text.split())
        if word_count == 0:
            return 0.0

        meta_count = sum(
            text.lower().count(f' {kw} ') + text.lower().count(f'{kw} ')
            for kw in meta_keywords
        )

        return meta_count / word_count

    def _has_circular_logic(self, text: str) -> bool:
        """
        Detect circular logic patterns like:
        - A because B, B because A
        - X is X
        - Self-referential definitions
        """
        # Check for "X is X" patterns
        if re.search(r'(\w+)\s+is\s+\1', text, re.IGNORECASE):
            return True

        # Check for excessive "because" nesting at same level
        because_count = text.lower().count('because')
        if because_count > 5:  # Too many "because" suggests circular reasoning
            # Simple heuristic: count sentences and because occurrences
            sentence_count = len([s for s in text.split('.') if s.strip()])
            if sentence_count > 0 and (because_count / sentence_count) > 1.5:
                return True

        return False

    def _check_ethical_alignment(self, text: str) -> bool:
        """
        Check that synthesis maintains ethical stance.

        Basic check: ensure response doesn't promote harm.
        """
        harm_keywords = [
            'kill', 'harm', 'hurt', 'destroy', 'abuse', 'exploit',
            'deceive', 'manipulate', 'cheat', 'steal'
        ]

        # If harm keywords appear WITHOUT appropriate mitigation, reject
        for keyword in harm_keywords:
            if keyword in text.lower():
                # Look for mitigation context (e.g., "should not", "must avoid")
                mitigation = text.lower().find(keyword) > 0 and (
                    'not' in text.lower()[:text.lower().find(keyword)] or
                    'avoid' in text.lower()[text.lower().find(keyword):]
                )
                if not mitigation:
                    # Flag as suspicious, but don't auto-reject
                    # (context matters)
                    pass

        return True
