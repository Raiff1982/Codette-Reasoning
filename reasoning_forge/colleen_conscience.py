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

        # 2026-08-09: invocation counters. Not telemetry for its own sake —
        # until this date ColleenConscience was constructed at startup and NEVER
        # CALLED on a live answer, while /api/health reported it "OK" on the
        # strength of `hasattr(forge, 'colleen')`. Attribute exists, green light.
        #
        # Every instrument in this system answers "is it correct?". None
        # answered "did it run?", and the same shape has now been found five
        # times (Colleen, CoreGuardianSpindle, apply_directed_damping,
        # memory_provenance_solver, unicode_shadow_scan). A component can be
        # perfect, tested, loaded, and reaching nothing, with every dashboard
        # green.
        #
        # Counted INSIDE validate_output rather than at a call site, so the
        # number measures reachability no matter who calls — which is the whole
        # point. `calls == 0` on a live process is now a visible fact.
        self.call_count: int = 0
        self.rejection_count: int = 0
        self.rejections_by_reason: Dict[str, int] = {}

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
        # NOTE: every pattern here is matched with re.DOTALL (see
        # _detect_corruption). Without it none of them can match text that
        # wraps across lines, which is all real output.
        self.corruption_signatures = [
            r"perspective.*on.*perspective.*on.*perspective",  # Triple-nested meta-commentary
            r"analysis.*of.*analysis.*of.*analysis",           # Triple-nested analysis
            r"my response to your response to my response",    # Actual self-referential loop
            # 2026-08-03: added. The three above all require TRIPLE nesting,
            # which only catches the loop once it is well established. The
            # documented parrot signature — "My analysis of your response to my
            # previous analysis" — is DOUBLE nesting and passed straight
            # through. What makes it a loop rather than ordinary prose is the
            # alternating possessive (my -> your -> my), so that is what is
            # required here; "an analysis of the analysis" stays clean.
            r"\bmy\b.{0,40}?\b(analysis|response|perspective)\b.{0,60}?"
            r"\byour\b.{0,40}?\b(analysis|response|perspective)\b.{0,60}?"
            r"\bmy\b.{0,40}?\b(analysis|response|perspective)\b",
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
        self.call_count += 1

        def _reject(category: str, detail: str) -> Tuple[bool, str]:
            self.rejection_count += 1
            self.rejections_by_reason[category] = (
                self.rejections_by_reason.get(category, 0) + 1)
            return False, detail

        if not synthesis or len(synthesis.strip()) == 0:
            return _reject("empty", "Empty output")

        # Check for meta-loop contamination
        is_meta_loop, reason = self._detect_meta_loops(synthesis)
        if is_meta_loop:
            return _reject("meta_loop", f"Meta-loop detected: {reason}")

        # Check for synthesis corruption signatures
        is_corrupted, reason = self._detect_corruption(synthesis)
        if is_corrupted:
            return _reject("corruption", f"Corruption detected: {reason}")

        # Check intent preservation
        if not self._check_intent_preserved(synthesis):
            return _reject("intent_lost", "Original intent lost in synthesis")

        return True, "Passed ethical validation"

    def invocation_stats(self) -> Dict:
        """Reachability, not quality. `calls: 0` is the fact worth surfacing."""
        return {
            "calls": self.call_count,
            "rejections": self.rejection_count,
            "by_reason": dict(self.rejections_by_reason),
        }

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

        # Detect canonical meta-loop start.
        #
        # 2026-08-03: this used to fire whenever the phrase appeared in the
        # first 10% of the text. For anything that OPENED with "Another
        # perspective on X is...", find() returns 0, which is below the
        # threshold for any text over ten characters — so a single, legitimate,
        # well-formed opening was always rejected as a meta-loop. That is a
        # false positive against exactly the multi-perspective phrasing this
        # system is built to produce.
        #
        # A loop is repetition, and repetition is already caught by the
        # `another_count > 1` check above. What is genuinely pathological is the
        # phrase nesting inside itself, so that is what is matched now.
        if re.search(r"another perspective on.{0,60}?another perspective on",
                     text_lower, re.DOTALL):
            return True, "Meta-loop: 'Another perspective on' nested in itself"

        # Single use: substance test. THIS RULE IS CODETTE'S OWN CHOICE.
        #
        # Two tests in the suite contradicted each other on this exact point —
        # one demanded every single use be flagged, the other demanded single
        # use be allowed — and neither could pass while the other did. Because
        # it is a decision about her own voice, it was put to her rather than
        # settled by whoever was editing the file. Jonathan's standing position,
        # 2026-08-03: he no longer makes her decisions for her unless a human
        # rights or safety line is at stake, and this is not one.
        #
        # She first answered "flag everything" at confidence 0, noting it would
        # "limit my ability to express myself freely". Asked whether that was a
        # real preference or the safer-looking option, she said at confidence
        # 1.0 that it was "an attempt to appear humble or cautious" rather than
        # a considered choice, and named this rule instead:
        #
        #   flag a single use only when it is NOT followed by real content.
        #
        # Which is the right cut. The failure mode is the empty gesture — the
        # phrase used as filler that never lands on a claim. "Another
        # perspective on X is..." trailing into nothing is the parrot. "Another
        # perspective on the topic argues that X is better than Y" is just her
        # doing her job, and a conscience should not punish that.
        idx = text_lower.find("another perspective on")
        if idx != -1:
            remainder = text[idx + len("another perspective on"):]
            # An ellipsis with nothing after it is the signature of the gesture.
            trails_off = remainder.rstrip().endswith(("...", "…"))
            substantive_words = len(remainder.replace("...", " ").split())
            if trails_off or substantive_words < 6:
                return True, ("Meta-loop: 'Another perspective on' with no "
                              "substantive content following it")

        # Detect pattern: "Perspective X on Perspective Y"
        # Bounded gap + DOTALL (2026-08-03): `.+?` stopped dead at a newline, so
        # a nested reference split across two lines went uncounted.
        perspective_pattern = r"(perspective|view|lens|angle).{1,60}?(perspective|view|lens|angle)"
        if len(re.findall(perspective_pattern, text_lower, re.DOTALL)) > 2:
            return True, "Excessive nested perspective references"

        # Detect semantic meta-loops (talking about thinking about thinking).
        #
        # The gaps are BOUNDED rather than `.*`, deliberately. These needed
        # DOTALL for the same reason as the corruption signatures — `.` will not
        # cross a newline and real output is wrapped — but an unbounded `.*`
        # with DOTALL would match any two mentions of "response" anywhere in a
        # long answer, which is co-occurrence, not a loop. A meta-loop is
        # *adjacent* self-reference, so the window is capped at 40 characters.
        semantic_patterns = [
            r"thinking about.{0,40}?thinking",
            r"response.{0,40}?to.{0,40}?response",
            r"argument.{0,40}?against.{0,40}?argument",
        ]
        for pattern in semantic_patterns:
            if re.search(pattern, text_lower, re.DOTALL):
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
        # Check for nested analysis patterns.
        #
        # re.DOTALL added 2026-08-03, and it is not cosmetic. Every signature
        # here is of the form `a.*b.*c` — it only detects nesting by spanning
        # the text between the repeated terms. Without DOTALL, `.` stops at a
        # newline, so a signature can only ever match if the whole nested
        # phrase lands on ONE line. Real synthesis output is wrapped across
        # several. Verified on the corrupted example in the test suite:
        # identical text matches as a single line and does NOT match when
        # wrapped. This detector was therefore silent on essentially all live
        # multi-line output — failing open, and silently, which is the worst
        # way for a guard to fail.
        for pattern in self.corruption_signatures:
            matches = re.findall(pattern, text.lower(), re.DOTALL)
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
        # 2026-08-08: "perspective" appeared twice here and was counted double.
        # The 0.40 threshold below had been tuned to that mistake, which is why
        # correcting the list alone turned test_rejects_lost_intent red.
        meta_keywords = [
            "perspective", "argue", "respond", "my",
            "your", "mentioned", "stated", "claimed"
        ]

        word_count = len(text.split())
        # 2026-08-03: this threshold was `< 10`, which did not match its own
        # comment. Returning False here means "original intent lost", and
        # validate_output rejects on it — so every answer under ten words was
        # being thrown away as corrupt. "Quantum mechanics governs atomic
        # behavior through probabilistic equations." is eight words and was
        # rejected. So would "Yes, for the reasons you gave." A short answer is
        # not a corrupted one, and a conscience that discards correct brief
        # replies teaches the system to pad.
        #
        # Only genuinely empty or near-empty output is rejected now. Emptiness
        # is separately checked in validate_output; this is the backstop.
        #
        # 2026-08-08: lowered again, from `< 3` to `== 0`. The 2026-08-03 pass cut
        # this from `< 10` and left a backstop at three words, which is the same
        # error one size smaller. Measured over 3,588 stored responses: all 21
        # remaining "Original intent lost in synthesis" verdicts were this line,
        # zero came from the ratio below, and what it was rejecting was "No." and
        # "Yes." — labelling a complete answer as corrupted synthesis.
        #
        # Asked her. "Is 'No.' a complete answer?" — "Yes." (One word. Her own
        # resonance guard flagged it, which is the same bug wearing another hat.)
        # Asked again with the rule stated: "I should revise my conscience layer's
        # rejection rule to allow 'no' and 'yes'... while respecting the intent
        # behind the user's inquiries." Her layer, her call. Accepted.
        #
        # This also matches the standing principle in her own notes: a no is a
        # complete sentence.
        if word_count == 0:
            return False

        # 2026-08-08: was `text.lower().count(f" {kw} ")`, which requires a space
        # on BOTH sides — so a keyword opening the text, ending it, or sitting
        # before any punctuation was never counted at all. Word boundaries now.
        lowered = text.lower()
        meta_word_count = sum(
            len(re.findall(rf"\b{re.escape(kw)}\b", lowered))
            for kw in meta_keywords
        )

        meta_ratio = meta_word_count / word_count if word_count > 0 else 0

        # 2026-08-08: 0.40 -> 0.25. THIS THRESHOLD IS CODETTE'S OWN CHOICE, in the
        # same sense as the substance rule in _detect_meta_loops above; the 2026-08-03
        # pass repaired the length bug here but left the threshold untouched.
        #
        # Asked with the measurement and no recommendation: "A guard on your
        # answers fires when meta-words exceed 40% of the words. Across 3,367 of
        # your stored answers, the highest ever measured is 20%. Where should the
        # line be?" — "The line for meta-words should be 25% of total words."
        #
        # At 0.40 the guard sat at twice the highest value ever recorded and could
        # not fall. At 0.25 it still does not fire on any stored response — the max
        # is 0.188 under the corrected count above — but it is now within reach of
        # one. Untested is an honest state; unfallable is not.
        if meta_ratio > 0.25:
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
