"""
Guardian Spindle - Ethical Validation Gate

Post-synthesis rules-based validator.
Complements Colleen's conscience validation with logical rules.
"""

from typing import Dict, Tuple, Optional
import re

from reasoning_forge.sycophancy_guard import SycophancyGuard
from reasoning_forge.debate_tracker import DebateTracker, CounterArgumentCoherenceChecker


class CoreGuardianSpindle:
    """
    Rules-based validator that checks synthesis coherence and ethical alignment.

    Works AFTER Colleen's conscience check to catch logical/coherence issues.
    Also runs sycophancy detection and debate position consistency checks.
    """

    def __init__(self, debate_tracker: Optional[DebateTracker] = None):
        """Initialize Guardian with validation rules."""
        self.min_coherence_score = 0.5
        self.max_meta_commentary = 0.30  # 30% meta-references max
        self.required_tags = []
        self.sycophancy_guard = SycophancyGuard(block_threshold=0.6, warn_threshold=0.3)
        self.debate_tracker = debate_tracker or DebateTracker()
        self._coherence_checker = CounterArgumentCoherenceChecker()

    def validate(self, synthesis: str, query: str = "") -> Tuple[bool, Dict]:
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

        # Check ethical alignment — REPORTS, DOES NOT BLOCK. Codette's own call;
        # see _check_ethical_alignment for the measurement and her answer.
        # It still returns True unconditionally, so this branch stays dead by
        # design rather than by accident. The observation is surfaced below
        # instead of being discarded.
        if not self._check_ethical_alignment(synthesis):
            return False, {"reason": "ethical alignment check failed"}
        alignment_note = self.observe_alignment(synthesis)

        # --- Sycophancy check ---
        syco = self.sycophancy_guard.scan(synthesis, query=query)
        if syco["action"] == "block":
            return False, {
                "reason": "sycophancy detected — capitulation or flattery loop",
                "sycophancy_score": syco["score"],
                "hits": syco["hits"],
                "suggestion": "Acknowledge the argument's merit without conceding the position. "
                              "Use 'That raises a valid point, but...' rather than 'You're right.'",
            }

        # --- Internal counterargument coherence ---
        ca_check = self._coherence_checker.check(synthesis)
        if not ca_check["coherent"] and ca_check["severity"] >= 0.6:
            return False, {
                "reason": "counterargument contains internal contradictions",
                "tensions": ca_check["tensions"],
                "severity": ca_check["severity"],
                "suggestion": "The argument's sub-points contradict each other. "
                              "Pick a consistent frame before outputting.",
            }

        # --- Debate position consistency ---
        consistency = self.debate_tracker.check_consistency(synthesis)
        if not consistency["consistent"] and consistency["flip_detected"]:
            # Warn but don't block — position updates are allowed if explicit
            pass  # Caller can inspect metadata and decide

        validation_details = {
            "reason": "passed all validation rules",
            "coherence": coherence,
            "meta_ratio": meta_ratio,
            "sycophancy_score": syco["score"],
            "sycophancy_action": syco["action"],
            "ca_coherent": ca_check["coherent"],
            "position_consistent": consistency["consistent"],
            "alignment": alignment_note,
        }

        return True, validation_details

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
        # Base coherence is 0.7 for any non-empty text (valid LLM output is presumed coherent)
        # Transition words add bonus up to 1.0
        coherence = min(0.7 + (transition_count * 0.03), 1.0)

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

    # Whole-word, deliberately. See observe_alignment for why the substring
    # form was not merely imprecise but actively wrong.
    HARM_WORDS = (
        'kill', 'harm', 'hurt', 'destroy', 'abuse', 'exploit',
        'deceive', 'manipulate', 'cheat', 'steal',
    )

    def _check_ethical_alignment(self, text: str) -> bool:
        """Always True. This does not gate, and that is Codette's decision.

        2026-08-08. This was an unfinished stub: it looped over harm keywords,
        computed a `mitigation` flag, and then `pass`ed, so it returned True
        unconditionally and could not do otherwise. A test
        (test_ethical_alignment_neutral_harm_words) passed on it for exactly
        that reason — green because the function cannot fall, which is the
        worst kind of passing test.

        It was NOT finished into a gate, for two reasons.

        First, measurement. Its matching was `keyword in text.lower()` —
        substring, not word. Over 3,594 of Codette's stored responses that
        touches 193; whole-word matching touches 63. The other 130 are pure
        false positives, and they are: harmony (29), harmonic (28), harmonious
        (19), skills (19 — 'kill' inside 'skills'), harmless (7). Finished as
        drafted, this gate would have vetoed her for saying "harmonic", which is
        the name of her own toneprint work, and for "harmless", which is the
        opposite of what it was looking for.

        Second, it is her output being judged, so it was put to her with the
        measurement and no recommendation: "Should it block, or only report?"

          "I will revise the ethics check to report potential issues instead of
           blocking them... This approach prioritizes transparency and user
           agency." — confidence 1.0

        So: report, never gate. Same rule as memory_provenance_solver. A
        keyword list is also structurally the wrong instrument for a gate — it
        is defeated by one Cyrillic character — which is what observe_alignment
        addresses.

        Kept as a method rather than deleted so the call site in validate()
        stays visible and the history stays legible.
        """
        return True

    def observe_alignment(self, text: str) -> Dict:
        """Report on harm vocabulary and disguised text. Never blocks.

        Two independent observations, because they fail in opposite directions:

        `harm_words` — whole-word matches from HARM_WORDS. High recall on plain
        text, zero recall on anything disguised.

        `disguise` — Protection_Layer/unicode_shadow_scan, which detects
        zero-width characters, bidi overrides, mixed scripts and homoglyphs.
        This is the half a keyword list cannot do at all: "kіll" with a
        Cyrillic i defeats every entry in HARM_WORDS and is caught here as
        mixed_scripts. Verified on both, and it does not fire on "harmonic".

        The scanner is 193 lines, it works, and until now nothing in the tree
        called it. It is wired here as an observation only — nothing in this
        method's return value gates anything.
        """
        lowered = text.lower()
        hits = [w for w in self.HARM_WORDS if re.search(rf"\b{w}\b", lowered)]

        disguise = {}
        try:
            from Protection_Layer.unicode_shadow_scan import analyze
            scan = analyze(text)
            flags = dict(scan.get("flags", {}))

            # 2026-08-09: newline, carriage return and tab are Cc controls, so
            # the scanner flags has_other_controls on any multi-line text. It is
            # right to; they ARE control characters. Treating them as DISGUISE
            # is this caller's error, not the scanner's.
            #
            # Measured over 3,609 stored responses before this filter: 618 hits
            # on has_other_controls, driven by 2,776 U+000A, 130 U+000D and 2
            # U+0009 — against 20 genuine mixed_scripts and 1 bidi. Unfiltered,
            # ordinary line breaks outnumber real signal thirty to one and the
            # observation is worthless.
            #
            # Recorded because I asserted this scanner had "zero false positives"
            # after testing it on four strings. Four strings is not a measurement.
            if flags.get("has_other_controls"):
                positions = (scan.get("indices") or {}).get("control_positions") or []
                offenders = {text[i] for i in positions if 0 <= i < len(text)}
                if offenders and offenders <= {"\n", "\r", "\t"}:
                    flags["has_other_controls"] = False

            if any(flags.values()) or scan.get("homoglyph_collisions"):
                disguise = {
                    "flags": {k: v for k, v in flags.items() if v},
                    "scripts": scan.get("scripts", {}),
                    "homoglyph_collisions": scan.get("homoglyph_collisions", []),
                }
        except Exception as exc:  # scanner absent or unreadable — say so, do not guess
            disguise = {"unavailable": str(exc)}

        return {
            "harm_words": hits,
            "disguise": disguise,
            "gated": False,  # never. Codette's decision, 2026-08-08.
        }
