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

import time
import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Identity confidence decay half-life in seconds (30 minutes)
CONFIDENCE_HALF_LIFE = 1800.0
# Minimum confidence floor (never fully forgets a confirmed identity)
CONFIDENCE_FLOOR = 0.15
# Reinforcement boost per positive interaction
CONFIDENCE_REINFORCE = 0.12
# Contradiction penalty
CONFIDENCE_CONTRADICTION_PENALTY = 0.4


@dataclass
class GovernorDecision:
    """Output of a governor evaluation."""
    action: str = "allow"           # "allow", "constrain", "redirect", "block"
    confidence: float = 1.0       # Governor's confidence in this decision
    memory_budget: int = 3         # Max cocoons to inject (0 = none)
    identity_budget: str = "full"  # "full", "partial", "none"
    max_response_tokens: int = 512 # Adaptive response length
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

        # Apply time-based decay since last interaction
        elapsed = now - state["last_interaction"]
        if elapsed > 0:
            decay_factor = math.pow(0.5, elapsed / CONFIDENCE_HALF_LIFE)
            decayed = state["confidence"] * decay_factor
            # Floor: never fully forget a confirmed identity
            decayed = max(CONFIDENCE_FLOOR, decayed)
        else:
            decayed = state["confidence"]

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
        """
        contradiction_signals = [
            "i'm not ", "i am not ", "wrong person", "you don't know me",
            "we haven't met", "first time here", "never talked",
            "who do you think i am", "that's not me", "that wasn't me",
            "you're confusing me", "different person",
        ]
        query_lower = query.lower()
        is_contradiction = any(s in query_lower for s in contradiction_signals)

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
        - If query contains identity denial: force none
        """
        denial_patterns = [
            "i'm not ", "i am not ", "wrong person", "you don't know me",
            "first time", "we haven't met",
        ]
        if any(p in query.lower() for p in denial_patterns):
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

        # ── Answer detection ──
        if not self._did_answer_question(query, response):
            result["warnings"].append("Response may not directly answer the question.")
            self.answer_detection_failures += 1

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
        if response.endswith(("...", "—", "-", ",")):
            result["warnings"].append("Response appears incomplete (Lock 4 violation).")

        # Log
        self.decisions.append({
            "timestamp": time.time(),
            "phase": "post",
            "valid": result["valid"],
            "warnings": len(result["warnings"]),
        })

        return result

    def _did_answer_question(self, query: str, response: str) -> bool:
        """
        Heuristic answer detection.

        Checks if the response likely addresses the query rather than
        being off-topic philosophical padding (Lock 1 enforcement).
        """
        if not query or not response:
            return False

        # Extract significant query words
        stop = {"the", "a", "an", "is", "are", "was", "what", "how", "why",
                "when", "where", "who", "do", "does", "can", "could", "would",
                "should", "will", "to", "of", "in", "for", "on", "with", "at",
                "by", "and", "or", "but", "if", "it", "i", "you", "my", "your",
                "this", "that", "me", "about", "from"}
        query_words = set(
            w.lower().strip(".,!?;:\"'") for w in query.split()
            if len(w) > 2 and w.lower() not in stop
        )

        if not query_words:
            return True  # Greeting or command — any response is fine

        response_lower = response.lower()
        overlap = sum(1 for w in query_words if w in response_lower)
        overlap_ratio = overlap / len(query_words) if query_words else 0

        # At least 30% of query keywords should appear in response
        return overlap_ratio >= 0.3

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
