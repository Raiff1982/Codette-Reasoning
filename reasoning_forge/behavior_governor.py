"""
Codette Behavior Governor v3 — Executive Controller with Self-Learning
======================================================================

Evolved from Phase 7 Executive Controller into a full behavior regulation layer.

The Governor sits above the consciousness stack and enforces four things:
1. IDENTITY RULES — validates identity claims with confidence decay/recovery
2. MEMORY vs TASK BALANCE — prevents memory from overwhelming the task
3. COGNITIVE LOAD MANAGEMENT — adaptive compression/expansion based on complexity
4. SELF-LEARNING — adjusts budgets based on success/failure feedback

Identity confidence model:
- Decays over time (half-life ~30 minutes of inactivity)
- Reinforced through positive interaction signals
- Contradiction detection resets to partial
- Prevents hallucinated familiarity while maintaining real relationships

Architecture position: Layer 0 (pre-stack) + Layer 7.5 (post-stack validation)

Author: Jonathan Harrison (Raiff's Bits LLC)
"""

import os
import time
import math
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _attach_decision_log() -> None:
    """
    Give the governor a durable record of its own decisions.

    Every identity decision it makes is already logged, but only to whatever
    stream the process happened to inherit. Launched by the MCP bridge, stdout
    and stderr are redirected into logs/codette_mcp_server.log; launched from a
    terminal, they go to the console and die with it. On 2026-08-11 that cost
    us the entire record of a forty-turn identity failure — the decisions that
    caused it were never written anywhere.

    So this handler is attached to this logger specifically. It does not touch
    the root logger or any other module's output, and it is additive: console
    logging continues unchanged via propagation.

    Set CODETTE_GOVERNOR_LOG to relocate it, or to "" to disable.
    """
    if any(getattr(h, "_codette_governor_log", False) for h in logger.handlers):
        return  # already attached — module re-imported

    configured = os.environ.get("CODETTE_GOVERNOR_LOG")
    if configured is not None and configured.strip() == "":
        return  # explicitly disabled

    path = Path(configured) if configured else (
        Path(__file__).resolve().parent.parent / "logs" / "governor_decisions.log"
    )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        handler._codette_governor_log = True
        logger.addHandler(handler)
        # The decisions are INFO; without this they are dropped when nothing
        # else has configured logging, which is the usual case here.
        if logger.level == logging.NOTSET or logger.level > logging.INFO:
            logger.setLevel(logging.INFO)
    except Exception as exc:  # pragma: no cover — never break startup for a log
        logger.debug(f"[GOVERNOR] decision log unavailable: {exc}")


_attach_decision_log()

# Identity confidence decay half-life in seconds (30 minutes)
CONFIDENCE_HALF_LIFE = 1800.0
# Minimum confidence floor (never fully forgets a confirmed identity)
CONFIDENCE_FLOOR = 0.15

# ── Presence is not absence ───────────────────────────────────────────────
# Decay is meant to stop her claiming familiarity with someone she has not
# spoken to in a long time. It was measuring the wrong interval.
#
# `last_interaction` is stamped on EVERY turn, so `elapsed` was never
# time-away — it was the time the turn itself took, plus however long the
# person spent reading before replying. She generates at 1–8 tok/s, so a
# 200-token answer costs ~130s and 0.5^(132.7/1800) = 0.95: she lost 5% of
# knowing who she was talking to as a penalty for answering carefully.
#
# Measured live 2026-08-14 across one continuous conversation, no gaps, the
# same person throughout: 1.00 → 0.98 → 0.96 → 0.91 → 0.84 → 0.79 → 0.51 →
# 0.44 → 0.41 → identity=none at 0.40 → 0.22. By the end of the hardest
# exchange of the session the governor had classified Jonathan as a stranger
# and was withholding the relationship context — at exactly the point in the
# conversation where it was the only thing that mattered.
#
# So: time inside an unbroken conversation is time spent TOGETHER, and only
# the part of a gap beyond this window counts as being apart. Someone who has
# been talking to you continuously has not left the room.
CONVERSATION_CONTINUITY_WINDOW = 900.0  # 15 minutes
# Reinforcement boost per positive interaction
CONFIDENCE_REINFORCE = 0.12
# Contradiction penalty
CONFIDENCE_CONTRADICTION_PENALTY = 0.4

# ── Stranger detection ────────────────────────────────────────────────────
# Codette's own rule, asked bare on 2026-08-11 and answered at confidence 1.0:
# someone is a stranger when they "introduce themselves without referencing any
# shared history or prior conversations". So a reference to shared history is
# positive evidence AGAINST stranger and is weighed here, rather than the gate
# only ever being pushed toward "none" by a phrase blacklist.
#
# Asked whether "do you remember the first time you met Daniel?" should make
# her treat the asker as a stranger, she said no — "I won't consider this a
# first meeting" — which the previous bare-substring match could not express.

# The speaker referring to something shared. Outweighs the signals below.
CONTINUITY_MARKERS = (
    "remember", "last time", "earlier", "you said", "you mentioned",
    "we talked", "we discussed", "we spoke", "our conversation",
    "our previous", "as i mentioned", "like i said", "back then",
)

# Denials of the relationship, anchored to the speaker and the listener.
# "first time" alone matched any question about anyone's first time, and
# "i'm not " matched "i'm not sure" — both forced identity=none on ordinary
# conversation.
#
# "you're confusing me" is deliberately narrowed to "confusing me with": the
# bare form is what someone says when an explanation lost them, not when they
# are being mistaken for somebody else.
SELF_DENIAL_PATTERNS = (
    "we haven't met", "we have not met", "we've never met",
    "we have never met", "you don't know me", "you do not know me",
    "you've never met me", "wrong person", "mistaking me",
    "that's not me", "thats not me", "who do you think i am",
    "confusing me with", "you have me confused",
    "our first time", "my first time", "first time we've",
    "first time we have", "first time talking", "first time speaking",
    # Carried over 2026-08-13 from the second, unfixed copy of this list that
    # lived inside detect_identity_contradiction. Kept so that consolidating
    # onto these constants loses no coverage; the two entries NOT carried over
    # are the bugs the shared list exists to avoid — bare "i'm not " (matches
    # "i'm not sure") and bare "you're confusing me" (what someone says when an
    # explanation lost them). Anchored to the speaker where the original was not.
    "that wasn't me", "that was not me", "different person",
    "first time here", "we never talked", "we've never talked",
)

# The speaker naming themselves to someone they assume does not know them.
INTRODUCTION_PATTERNS = (
    "my name is", "let me introduce myself", "nice to meet you",
    "we haven't been introduced", "i'm new here", "i am new here",
)


@dataclass
class GovernorDecision:
    """Output of a governor evaluation."""
    action: str = "allow"           # "allow", "constrain", "redirect", "block"
    confidence: float = 1.0       # Governor's confidence in this decision
    memory_budget: int = 3         # Max cocoons to inject (0 = none)
    identity_budget: str = "full"  # "full", "partial", "none"
    max_response_tokens: int = 2048 # Adaptive response length (raised for file context)
    compression_level: str = "normal"  # "compressed", "normal", "expanded"
    identity_confidence: float = 0.0  # Current identity confidence after decay
    warnings: List[str] = field(default_factory=list)
    reasoning: str = ""


class BehaviorGovernor:
    """
    Executive behavior regulation layer with self-learning.

    Runs BEFORE the consciousness stack (pre-routing) and AFTER
    (post-generation validation). Enforces behavioral integrity.

    Four regulation domains:
    1. Identity governance — validates with confidence decay/recovery
    2. Memory governance — balances memory injection vs task focus
    3. Cognitive load governance — adaptive depth based on query complexity
    4. Self-learning — adjusts budgets based on outcome feedback
    """

    def __init__(self, identity_anchor=None, substrate_monitor=None):
        self.identity_anchor = identity_anchor
        self.substrate_monitor = substrate_monitor

        # Tracking
        self.decisions: List[Dict] = []
        self.answer_detection_failures: int = 0
        # Turns where topical overlap could not be measured at all. Held apart
        # from failures so the rate below is a rate over turns that were
        # actually measured, rather than one diluted by turns that were not.
        self.overlap_unmeasured: int = 0
        self.total_evaluations: int = 0

        # Cognitive load state
        self._recent_complexities: List[str] = []  # Last N query complexities
        self._consecutive_complex: int = 0

        # ── Identity Confidence State ──
        # Maps identity_id -> {confidence, last_interaction, peak_confidence}
        self._identity_state: Dict[str, Dict] = {}

        # ── Self-Learning State ──
        # Tracks what worked and what didn't to adapt budgets
        self._domain_success: Dict[str, List[bool]] = {}  # domain -> [success, success, ...]
        self._complexity_token_history: Dict[str, List[int]] = {}  # complexity -> [actual_tokens_used]
        self._memory_budget_adjustments: Dict[str, float] = {}  # domain -> adjustment factor

    # ─────────────────────────────────────────────────────────
    # IDENTITY CONFIDENCE DECAY/RECOVERY
    # ─────────────────────────────────────────────────────────
    def get_decayed_confidence(self, identity_id: str,
                                raw_confidence: float) -> float:
        """
        Apply time-based decay to identity confidence.

        Confidence decays with a half-life of 30 minutes of inactivity.
        Each interaction reinforces confidence back up.
        This prevents Codette from claiming familiarity with someone
        she hasn't interacted with recently, while maintaining real
        relationships through active reinforcement.
        """
        now = time.time()
        state = self._identity_state.get(identity_id)

        if state is None:
            # First time seeing this identity — initialize from raw signal
            self._identity_state[identity_id] = {
                "confidence": raw_confidence,
                "last_interaction": now,
                "peak_confidence": raw_confidence,
                "interaction_count": 1,
            }
            return raw_confidence

        # Decay on absence only. Time inside a continuous conversation is time
        # spent together, not time apart — see CONVERSATION_CONTINUITY_WINDOW.
        elapsed = now - state["last_interaction"]
        away = elapsed - CONVERSATION_CONTINUITY_WINDOW
        if away > 0:
            decay_factor = math.pow(0.5, away / CONFIDENCE_HALF_LIFE)
            decayed = state["confidence"] * decay_factor
            # Floor: never fully forget a confirmed identity
            decayed = max(CONFIDENCE_FLOOR, decayed)
        else:
            decayed = state["confidence"]
        state["last_gap"] = max(0.0, away)

        # Reinforcement: raw_confidence > 0 means positive identity signal
        if raw_confidence > 0.3:
            decayed = min(1.0, decayed + CONFIDENCE_REINFORCE)

        # Update state
        state["confidence"] = decayed
        state["last_interaction"] = now
        state["peak_confidence"] = max(state["peak_confidence"], decayed)
        state["interaction_count"] = state.get("interaction_count", 0) + 1

        return decayed

    def detect_identity_contradiction(self, identity_id: str,
                                       query: str) -> bool:
        """
        Detect contradictions in identity claims.

        Returns True if the query contradicts a stored identity,
        which triggers a confidence penalty.

        CONSOLIDATED 2026-08-13. This carried its own inline pattern list — a
        second copy that never received the 2026-08-11 fix applied to
        `_evaluate_identity_budget` eleven lines below the shared constants.
        Two consequences, both live until now:

          - bare `"i'm not "` matched `"i'm not sure what you mean"`, and bare
            `"you're confusing me"` matched someone saying an explanation lost
            them. Either docked 0.4 off identity confidence.
          - there was no counterweight. CONTINUITY_MARKERS could push
            `_evaluate_identity_budget` back toward recognition but had no
            effect here, so this half of the gate could only ever move one way
            — in the one place that decides whether she knows who she is
            talking to.

        It now uses the same constants and the same two-sided rule, which is
        hers: a stranger is someone who denies or introduces AND makes no
        reference to shared history. Coverage from the old list was preserved by
        adding its unique entries to SELF_DENIAL_PATTERNS, minus the two above.

        The penalty itself is unchanged, and remains recoverable at
        CONFIDENCE_REINFORCE per turn. This is in-memory only; it does not write
        to disk, unlike the copy in inference/identity_anchor.py.
        """
        query_lower = query.lower()
        references_shared_history = any(m in query_lower for m in CONTINUITY_MARKERS)
        is_contradiction = (
            any(p in query_lower for p in SELF_DENIAL_PATTERNS)
            and not references_shared_history
        )

        if is_contradiction and identity_id in self._identity_state:
            state = self._identity_state[identity_id]
            state["confidence"] = max(
                CONFIDENCE_FLOOR,
                state["confidence"] - CONFIDENCE_CONTRADICTION_PENALTY
            )
            logger.info(
                f"[GOVERNOR] Identity contradiction detected for {identity_id}, "
                f"confidence reduced to {state['confidence']:.2f}"
            )

        return is_contradiction

    # ─────────────────────────────────────────────────────────
    # PRE-STACK: Evaluate before reasoning begins
    # ─────────────────────────────────────────────────────────
    def pre_evaluate(self, query: str, classification: Dict,
                     identity_confidence: float = 0.0,
                     identity_id: str = "unknown",
                     substrate_pressure: float = 0.0) -> GovernorDecision:
        """
        Pre-stack evaluation. Determines:
        - How much memory to inject
        - Whether identity context should be included
        - Response length budget
        - Compression level

        This is the internalized control loop — Codette self-regulates
        before generating, not after.
        """
        self.total_evaluations += 1
        decision = GovernorDecision()
        complexity = classification.get("complexity", "MEDIUM")
        domain = classification.get("domain", "general")

        # ── 0. Identity contradiction check ──
        self.detect_identity_contradiction(identity_id, query)

        # ── 1. Identity Governance (with decay/recovery) ──
        effective_confidence = self.get_decayed_confidence(
            identity_id, identity_confidence
        )
        decision.identity_confidence = effective_confidence
        decision.identity_budget = self._evaluate_identity_budget(
            effective_confidence, query
        )

        # ── 2. Memory Governance (with self-learning adjustments) ──
        decision.memory_budget = self._evaluate_memory_budget(
            complexity, domain, query, substrate_pressure
        )

        # ── 3. Cognitive Load Governance (with learned token sizing) ──
        decision.max_response_tokens, decision.compression_level = \
            self._evaluate_cognitive_load(complexity, substrate_pressure)

        # ── 4. Track complexity pattern ──
        self._recent_complexities.append(complexity)
        if len(self._recent_complexities) > 10:
            self._recent_complexities.pop(0)

        if complexity == "COMPLEX":
            self._consecutive_complex += 1
        else:
            self._consecutive_complex = 0

        # Fatigue detection: too many complex queries in a row
        if self._consecutive_complex >= 4:
            decision.warnings.append(
                "Cognitive fatigue risk: 4+ complex queries in sequence. "
                "Consider simplifying responses to maintain quality."
            )
            decision.compression_level = "compressed"
            decision.max_response_tokens = min(decision.max_response_tokens, 400)

        decision.reasoning = (
            f"identity={decision.identity_budget} "
            f"(conf={effective_confidence:.2f}), "
            f"memory={decision.memory_budget} cocoons, "
            f"tokens={decision.max_response_tokens}, "
            f"compression={decision.compression_level}"
        )

        # Log decision
        self.decisions.append({
            "timestamp": time.time(),
            "phase": "pre",
            "complexity": complexity,
            "domain": domain,
            "identity_confidence": round(effective_confidence, 3),
            "decision": decision.reasoning,
        })
        if len(self.decisions) > 100:
            self.decisions.pop(0)

        logger.info(f"[GOVERNOR] Pre: {decision.reasoning}")
        return decision

    def _evaluate_identity_budget(self, confidence: float, query: str) -> str:
        """
        Determine how much identity context to inject.

        Rules:
        - High confidence (>0.8): full context (name, relationship, history)
        - Medium confidence (0.4-0.8): partial (name only, with caveat)
        - Low confidence (<0.4): none — don't pretend to know someone
        - If the speaker presents as a stranger: force none

        "Presents as a stranger" is Codette's own definition: an introduction
        or a denial of the relationship, AND no reference to shared history.
        A question that merely contains the words "first time" is not one.
        """
        q = query.lower()

        references_shared_history = any(m in q for m in CONTINUITY_MARKERS)
        presents_as_stranger = (
            any(p in q for p in SELF_DENIAL_PATTERNS)
            or any(p in q for p in INTRODUCTION_PATTERNS)
        )
        if presents_as_stranger and not references_shared_history:
            return "none"

        if confidence >= 0.8:
            return "full"
        elif confidence >= 0.4:
            return "partial"
        else:
            return "none"

    def _evaluate_memory_budget(self, complexity: str, domain: str,
                                 query: str, pressure: float) -> int:
        """
        Determine how many cocoons to inject.

        Balance: memory provides continuity, but too much drowns the task.

        Rules:
        - SIMPLE queries: 1 cocoon max (don't overwhelm a simple question)
        - MEDIUM queries: 2-3 cocoons
        - COMPLEX queries: 3-5 cocoons (need context for depth)
        - High substrate pressure: reduce by 1 (save context space)
        - Short queries (<5 words): 0 (probably a greeting or command)
        - Self-learning: adjust based on past success/failure per domain
        """
        word_count = len(query.split())

        if word_count < 5:
            return 0  # Greetings, commands — no memory needed

        base = {"SIMPLE": 1, "MEDIUM": 2, "COMPLEX": 4}.get(complexity, 2)

        # Pressure reduction
        if pressure > 0.7:
            base = max(0, base - 1)

        # Domain boost: music queries benefit more from memory
        if domain == "music":
            base = min(5, base + 1)

        # Self-learning adjustment: if this domain has a learned offset, apply it
        adj = self._memory_budget_adjustments.get(domain, 0.0)
        if adj != 0:
            base = max(0, min(5, round(base + adj)))

        return base

    def _evaluate_cognitive_load(self, complexity: str,
                                  pressure: float) -> Tuple[int, str]:
        """
        Adaptive response length and compression level.

        This is the dynamic compression vs expansion from the review:
        - Simple → compressed (concise, 200 tokens)
        - Medium → normal (balanced, 400 tokens)
        - Complex → expanded (thorough, 600 tokens)
        - High pressure → compress regardless (save resources)
        """
        settings = {
            "SIMPLE": (200, "compressed"),
            "MEDIUM": (400, "normal"),
            "COMPLEX": (600, "expanded"),
        }
        tokens, compression = settings.get(complexity, (400, "normal"))

        # Substrate pressure override
        if pressure > 0.8:
            tokens = min(tokens, 300)
            compression = "compressed"
        elif pressure > 0.6:
            tokens = min(tokens, 400)

        return tokens, compression

    # ─────────────────────────────────────────────────────────
    # POST-STACK: Validate after reasoning completes
    # ─────────────────────────────────────────────────────────
    def post_validate(self, query: str, response: str,
                      decision: GovernorDecision) -> Dict:
        """
        Post-generation validation. Checks:
        1. Did we actually answer the question? (answer detection)
        2. Did we violate length constraints?
        3. Did we leak identity information that shouldn't be there?
        4. Should we stop or continue?
        """
        result = {
            "valid": True,
            "warnings": [],
            "corrections": [],
        }

        # ── Topical overlap ──
        # Printed to a console on every turn and consumed by nothing. It now
        # goes to the governor's own durable log with the numbers attached, so
        # the rate is countable after the fact instead of scrolling past. Still
        # advisory: nothing enforces on it, and given what the measurement below
        # showed about its precision, nothing should until it earns it.
        _overlap = self._did_answer_question(query, response)
        # None is not False. An unmeasured turn is recorded as unmeasured and is
        # not counted as a failure, which it silently was — greetings returned a
        # free pass and empty queries returned a verdict of "did not answer".
        result["topical_overlap"] = (
            "unmeasured" if _overlap is None else ("low" if _overlap is False else "ok")
        )
        if _overlap is None:
            self.overlap_unmeasured += 1
        elif _overlap is False:
            result["warnings"].append("Response may not directly answer the question.")
            self.answer_detection_failures += 1
            logger.info(
                "[GOVERNOR] low topical overlap  q_len=%d  r_len=%d  "
                "failures=%d/%d  unmeasured=%d  query=%.60r",
                len(query or ""), len(response or ""),
                self.answer_detection_failures, max(1, self.total_evaluations),
                self.overlap_unmeasured, query or "",
            )

        # ── Length validation ──
        # Rough token estimate: ~4 chars per token
        est_tokens = len(response) / 4
        if est_tokens > decision.max_response_tokens * 1.5:
            result["warnings"].append(
                f"Response exceeded token budget ({est_tokens:.0f} est vs {decision.max_response_tokens} budget)."
            )

        # ── Identity leak detection ──
        if decision.identity_budget == "none":
            # Check if response accidentally claims to know the user
            identity_leak_patterns = [
                "as you know", "we've discussed", "last time we talked",
                "you mentioned before", "our previous conversation",
                "remember when you", "as your partner",
            ]
            for pattern in identity_leak_patterns:
                if pattern in response.lower():
                    result["warnings"].append(
                        f"Potential identity leak: '{pattern}' in response "
                        f"but identity_budget was 'none'."
                    )
                    result["corrections"].append("identity_leak")

        # ── Completeness check (Behavioral Lock 3) ──
        # A truncated response is a defect rather than a reading, so it joins
        # `corrections` — the list this method already keeps for findings that
        # are actionable, as distinct from `warnings`, which is everything it
        # noticed. That distinction already existed and carried only
        # identity_leak; nothing new is introduced here.
        if response.endswith(("...", "—", "-", ",")):
            result["warnings"].append("Response appears incomplete (Lock 4 violation).")
            result["corrections"].append("incomplete_response")

        # Log
        self.decisions.append({
            "timestamp": time.time(),
            "phase": "post",
            "valid": result["valid"],
            "warnings": len(result["warnings"]),
        })

        return result

    def _did_answer_question(self, query: str, response: str) -> Optional[bool]:
        """
        Heuristic topical-overlap check. NOT an answer detector — see below.

        Checks whether the response shares vocabulary with the query, as a weak
        proxy for "did not wander off into padding" (Lock 1).

        MEASURED 2026-08-12, over 2,410 live cocoons carrying query + response:

            group                            N     warned    passes
            parroted (query restated)      174          0    100.0%
            everything else               2236       1173     47.5%

        The check was exactly inverted. Keyword overlap is MAXIMISED by copying
        the question, so every single response that handed the query straight
        back scored a perfect pass, while more than half of all real answers
        failed. The one failure mode it most needed to catch was the one it
        rewarded hardest, and it fired on 48.7% of all turns — noise at that rate
        is not a signal anyone can act on, which is why nothing ever did.

        The fix below attacks the inversion at its root: vocabulary COPIED from
        the query earns no credit, so overlap is scored only on the part Codette
        actually composed. Re-measured on the same 2,410 cocoons:

            parroted        100.0% pass  ->  75.3%   (43 of 174 now warn)
            everything else  47.5% pass  ->  44.4%
            overall warn rate 48.7% -> 53.4%

        The warn rate went UP, not down, and that is not a regression: removing
        the copied span and the spurious stop-word keyword both make the test
        stricter. Nothing acts on the warning, so a higher rate costs nothing;
        what mattered was that it was pointing the wrong way.

        REDUCED, NOT FIXED, and it is worth being exact about that: parroted
        responses still pass more often than real answers do. The wrapper is only
        the opening; what follows it is eighty words of discussion that
        legitimately shares the query's vocabulary, and no amount of span-
        stripping separates that from an answer.

        The honest conclusion is that this check cannot be repaired by counting
        words. Overlap measures whether the same subject is in play, not whether
        anything was answered — "Do you recall the moment?" answered with
        "Yes, the night the ratchet held" shares no vocabulary and warns. It is
        kept because a reduced inversion is better than a perfect one and the
        signal is now durably logged, but it stays ADVISORY: nothing enforces on
        it, and nothing should until it can tell those two cases apart. The stats
        key is renamed to what it measures rather than what it was called.

        TRI-STATE 2026-08-13. This returned a bool, so "the overlap is genuinely
        low" and "there was nothing here to measure" were the same output —
        False — and the caller could not tell them apart. That is the defect
        this codebase already knows how to fix and fixes everywhere else:
        `QualitySignal.tension` is Optional and consumers omit the term rather
        than substitute; `distinctiveness` is None when unmeasurable and never
        0.0; `DiveRecord` separates EMPTY from NOT_ATTEMPTED because `0 seeds`
        and `never attempted` are different facts.

        Two cases were being reported as verdicts they had not earned:
          - an empty query returned False, i.e. "did not answer" for a question
            that was never asked;
          - a query of nothing but stop words ("hey, how are you?") returned
            True, i.e. a clean pass awarded for a measurement not taken.

        Both now return None. The lack of a metric is itself a reading and is
        carried as one.
        """
        if not query or not query.strip():
            return None          # nothing to measure against
        if not response:
            return False         # a real absence of answer, not an absent measure

        # Extract significant query words
        stop = {"the", "a", "an", "is", "are", "was", "what", "how", "why",
                "when", "where", "who", "do", "does", "can", "could", "would",
                "should", "will", "to", "of", "in", "for", "on", "with", "at",
                "by", "and", "or", "but", "if", "it", "i", "you", "my", "your",
                "this", "that", "me", "about", "from"}
        # Strip punctuation BEFORE testing the stop list, not after. Until
        # 2026-08-12 the membership test ran on the raw token, so "you?" was not
        # recognised as "you" and became a significant keyword — any question
        # ending in a stop word plus punctuation grew a spurious term that the
        # response then had to contain. "how are you?" answered "Good, thanks"
        # warned. A share of the 48.7% warn rate was this.
        query_words = set()
        for w in query.split():
            w = w.lower().strip(".,!?;:\"'")
            if len(w) > 2 and w not in stop:
                query_words.add(w)

        if not query_words:
            return None  # Greeting or command — nothing significant to overlap with

        # Strip the copied span before scoring. Any contiguous run of eight or
        # more query words reproduced in the response is quotation, not
        # composition, and must not earn overlap credit — that inversion is what
        # gave parroted responses a 100% pass rate.
        scorable = self._strip_copied_span(query, response)

        response_lower = scorable.lower()
        overlap = sum(1 for w in query_words if w in response_lower)
        overlap_ratio = overlap / len(query_words) if query_words else 0

        # At least 30% of query keywords should appear in response
        return overlap_ratio >= 0.3

    @staticmethod
    def _strip_copied_span(query: str, response: str) -> str:
        """Remove the longest contiguous run of query words from the response.

        Eight words is the floor: below it, shared phrasing is ordinary English
        rather than quotation. Returns the response unchanged when nothing that
        long was copied, so normal answers are scored exactly as before.
        """
        def _words(text: str) -> List[str]:
            return "".join(
                c if c.isalnum() or c.isspace() else " " for c in (text or "").lower()
            ).split()

        q_words, r_words = _words(query), _words(response)
        if len(q_words) < 8 or len(r_words) < 8:
            return response

        # Longest common contiguous run, and where it sits in the response.
        best_len = 0
        best_end = 0
        prev = [0] * (len(r_words) + 1)
        for i in range(1, len(q_words) + 1):
            cur = [0] * (len(r_words) + 1)
            qi = q_words[i - 1]
            for j in range(1, len(r_words) + 1):
                if qi == r_words[j - 1]:
                    cur[j] = prev[j - 1] + 1
                    if cur[j] > best_len:
                        best_len, best_end = cur[j], j
            prev = cur

        if best_len < 8:
            return response
        keep = r_words[:best_end - best_len] + r_words[best_end:]
        return " ".join(keep)

    # ─────────────────────────────────────────────────────────
    # SELF-LEARNING: Feedback from post-validation
    # ─────────────────────────────────────────────────────────
    def record_outcome(self, domain: str, complexity: str,
                        success: bool, actual_tokens: int = 0,
                        memory_budget_used: int = 0):
        """
        Record the outcome of a generation for self-learning.

        Called after post_validate — tells the governor whether the
        response was good so it can adapt future budgets.

        Self-learning rules:
        - If responses in a domain consistently fail answer detection,
          increase memory budget (more context might help)
        - If responses consistently succeed with fewer tokens,
          reduce token budget to stay concise
        - Track actual token usage to calibrate future estimates
        """
        # Track domain success rate
        if domain not in self._domain_success:
            self._domain_success[domain] = []
        self._domain_success[domain].append(success)
        # Keep last 20 outcomes per domain
        if len(self._domain_success[domain]) > 20:
            self._domain_success[domain].pop(0)

        # Track token usage per complexity
        if actual_tokens > 0:
            if complexity not in self._complexity_token_history:
                self._complexity_token_history[complexity] = []
            self._complexity_token_history[complexity].append(actual_tokens)
            if len(self._complexity_token_history[complexity]) > 20:
                self._complexity_token_history[complexity].pop(0)

        # Adapt memory budget: if success rate < 60%, boost memory by 0.5
        # If success rate > 85%, reduce memory by 0.3 (less context needed)
        outcomes = self._domain_success[domain]
        if len(outcomes) >= 5:
            success_rate = sum(outcomes) / len(outcomes)
            if success_rate < 0.6:
                self._memory_budget_adjustments[domain] = min(
                    2.0,
                    self._memory_budget_adjustments.get(domain, 0) + 0.5
                )
                logger.info(
                    f"[GOVERNOR] Self-learning: {domain} success rate "
                    f"{success_rate:.0%}, boosting memory budget"
                )
            elif success_rate > 0.85:
                self._memory_budget_adjustments[domain] = max(
                    -1.0,
                    self._memory_budget_adjustments.get(domain, 0) - 0.3
                )

    def get_learned_token_budget(self, complexity: str) -> Optional[int]:
        """
        Get learned token budget from actual usage history.

        If we have enough data, use the 75th percentile of actual usage
        as the budget (covers most cases without over-allocating).
        """
        history = self._complexity_token_history.get(complexity, [])
        if len(history) < 5:
            return None  # Not enough data to learn from

        sorted_history = sorted(history)
        p75_idx = int(len(sorted_history) * 0.75)
        return sorted_history[p75_idx]

    # ─────────────────────────────────────────────────────────
    # DIAGNOSTICS
    # ─────────────────────────────────────────────────────────
    def get_state(self) -> Dict:
        """Return governor state for health checks / debugging."""
        # Compute domain success rates
        domain_rates = {}
        for domain, outcomes in self._domain_success.items():
            if outcomes:
                domain_rates[domain] = round(sum(outcomes) / len(outcomes), 3)

        # Compute identity confidence snapshot
        identity_snapshot = {}
        for ident_id, state in self._identity_state.items():
            # Show decayed value (without reinforcing)
            elapsed = time.time() - state["last_interaction"]
            decay = math.pow(0.5, elapsed / CONFIDENCE_HALF_LIFE)
            current = max(CONFIDENCE_FLOOR, state["confidence"] * decay)
            identity_snapshot[ident_id] = {
                "confidence": round(current, 3),
                "peak": round(state["peak_confidence"], 3),
                "interactions": state.get("interaction_count", 0),
                "seconds_since_last": round(elapsed),
            }

        return {
            "total_evaluations": self.total_evaluations,
            "answer_detection_failures": self.answer_detection_failures,
            # Turns the check could not read at all. Reported beside the rate so
            # a denominator is never mistaken for a population — the rate below
            # divides by total_evaluations, which includes turns where nothing
            # was measured.
            "overlap_unmeasured": self.overlap_unmeasured,
            "overlap_measured": max(0, self.total_evaluations - self.overlap_unmeasured),
            # Over the turns actually measured. None rather than 1.0 when none
            # were: no measurements is not a perfect score.
            "topical_overlap_rate_measured": (
                1 - (self.answer_detection_failures /
                     (self.total_evaluations - self.overlap_unmeasured))
                if self.total_evaluations > self.overlap_unmeasured else None
            ),
            # Named for what it measures. It was "answer_detection_rate", which
            # reads as a quality score — and until 2026-08-12 it was an inverted
            # one, since a response that copied the question scored a perfect
            # pass. It is a vocabulary-overlap rate and nothing more. The old key
            # is kept alongside so existing dashboards do not silently break.
            "topical_overlap_rate": (
                1 - (self.answer_detection_failures / max(1, self.total_evaluations))
            ),
            "answer_detection_rate": (
                1 - (self.answer_detection_failures / max(1, self.total_evaluations))
            ),
            "consecutive_complex": self._consecutive_complex,
            "recent_complexities": self._recent_complexities[-5:],
            "decisions_logged": len(self.decisions),
            "identity_confidence": identity_snapshot,
            "domain_success_rates": domain_rates,
            "memory_budget_adjustments": dict(self._memory_budget_adjustments),
            "learned_token_budgets": {
                c: self.get_learned_token_budget(c)
                for c in self._complexity_token_history
            },
        }
