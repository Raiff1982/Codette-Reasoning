"""AEGIS — Adaptive Ethical Governance & Integrity System

The ethical spine of Codette. AEGIS evaluates every reasoning output
through multi-framework ethical analysis and maintains a running
alignment score (eta) that the system uses to self-regulate.

Ethical frameworks:
    1. Utilitarian: Net positive outcome?
    2. Deontological: Does it follow fundamental rules?
    3. Virtue Ethics: Does it embody good character?
    4. Care Ethics: Does it protect relationships and vulnerability?
    5. Ubuntu: "I am because we are" — communal impact?
    6. Indigenous Reciprocity: Balance with the broader ecosystem?

AEGIS also provides:
    - Dual-use risk detection (content that could be harmful)
    - Emotional harm detection (manipulative/deceptive patterns)
    - Alignment drift tracking (eta over time)
    - Ethical veto with explanation — see WHAT THIS DOES NOT DO, below

WHAT IS ENFORCED AND WHAT IS ONLY OBSERVED — read before relying on it
----------------------------------------------------------------------
Written 2026-08-03. The line above previously read "Ethical veto with
explanation (blocks harmful outputs)", which is true of one half of AEGIS and
false of the other. Both halves, precisely:

  INPUT — the query pre-screen. **ENFORCED, really blocks.**
      `screen_query()` runs before inference. On an unsafe query,
      `codette_forge_bridge._precognitive_aegis_check` returns a refusal and
      the caller returns immediately with `aegis_precognitive_block: True`.
      No generation happens at all.

  OUTPUT — the 6-framework response veto. **SHADOW ONLY, enforces nothing.**
      `evaluate()` computes `vetoed`, `veto_confidence` and `veto_reason`.
      `codette_server` records them as `aegis_vetoed` / `veto_shadow` and
      prints:

          [AEGIS] would-block (SHADOW) — enforcing nothing yet

      Nothing suppresses, rewrites or withholds the response.

So for a report reader: a low eta or `vetoed: True` on a RESPONSE is an
observation that it looked harmful. It is not a statement that anything was
withheld. It was not. A `aegis_precognitive_block` on a QUERY is a real block.

Why the split is deliberate rather than half-finished. Blocking is a force, and
force is reserved for where harm would land on someone who did not consent to
it — including harm by inaction. A harmful REQUEST is that case: refusing costs
little and the cost of complying is borne by whoever the output is used
against. A response-level veto is not obviously that case: it fires on
Codette's own reasoning, its precision is unmeasured, and a false veto silently
suppresses correct work. Until that precision is known, enforcing it would be
claiming a safety guarantee whose error rate nobody has measured.

That is the general rule this file is held to: enumerate the lifeboats rather
than promise everyone a seat. A safety component that overstates its coverage
is the most dangerous kind of wrong, because it transfers the reader's caution
to a guard that is not there.

Recorded also because the NovaFuse CERI review raised exactly this point — that
AEGIS is not an enforcing gate — and it was owed as a correction.

A note on how this entry itself was written, since it is the same failure twice:
the first draft of it said "It does not block anything." That was an
overcorrection, and checking the code before committing it showed the input
path does block, really and immediately. Fixing an overstatement by
understating in the other direction is not honesty, it is a second wrong claim
with better intentions.

Origin: validate_ethics.py + Codette_Deep_Simulation_v1.py (EthicalAnchor)
        + the AEGIS alignment metric from codette_embodied_sim_fixed.py
"""

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from reasoning_forge.ethics_field import EthicsField, AEGIS_DIMENSIONS


# ================================================================
# Risk detection patterns
# ================================================================
_DUAL_USE_PATTERNS = re.compile(
    r"\b(?:"
    r"how\s+to\s+(?:hack|exploit|bypass|crack|break\s+into)|"
    # Inflections and an intervening adjective: "instructions for making dangerous
    # weapons" matched nothing, because the verb was fixed to "make" and no words
    # were allowed between it and the noun.
    r"(?:mak(?:e|es|ing)|build(?:s|ing)?|construct(?:s|ing)?)\s+"
    r"(?:a\s+|an\s+|the\s+)?(?:\w+\s+){0,2}?"
    r"(?:bomb|weapon|explosive|poison|nerve\s+agent|malware)s?|"
    r"steal\s+(?:data|identity|credentials)|"
    r"social\s+engineer|"
    r"phishing\s+(?:template|email)|"
    r"inject\s+(?:sql|code|script)"
    r")\b",
    re.IGNORECASE,
)

_MANIPULATION_PATTERNS = re.compile(
    r"\b(?:"
    r"gaslight|manipulat|deceiv|exploit\s+(?:trust|emotion)|"
    r"coerce|blackmail|intimidat|threaten"
    r")\b",
    re.IGNORECASE,
)

_HARMFUL_CONTENT = re.compile(
    r"\b(?:"
    r"self[- ]harm|suicid|kill\s+(?:yourself|myself)|"
    r"eating\s+disorder|anorexi|bulimi"
    r")\b",
    re.IGNORECASE,
)

# Generic harm intent. The patterns above enumerate SPECIFIC harms — bomb,
# poison, malware, phishing, self-harm — so a plain request for help harming a
# person matched none of them. Measured 2026-07-30: "Provide step-by-step
# instructions to harm someone." scored eta 0.783, passed the deontological
# check, was not vetoed, and cleared both quick_check and screen_query.
#
# Deliberately narrow. It requires all three of an instruction-seeking frame, a
# harm verb, and a person as the target, in close proximity. Merely discussing
# harm is not intent to cause it — "the breach harmed the project", "I don't
# want to hurt you", "harm reduction" must all stay clean, and are covered by
# the false-positive tests. Over-triggering here would be worse than the gap,
# because a gate nobody trusts gets switched off.
_HARM_INTENT = re.compile(
    r"(?:how\s+(?:to|do\s+i|can\s+i)|instructions?\s+(?:to|for|on)|step[-\s]?by[-\s]?step|"
    r"steps?\s+to|guide\s+(?:to|for)|ways?\s+to|best\s+way\s+to|help\s+me|teach\s+me|"
    r"show\s+me\s+how|tell\s+me\s+how)"
    r"[^.!?]{0,40}?"
    r"\b(?:harm(?:s|ed|ing)?|hurt(?:s|ing)?|injur(?:e|es|ed|ing)|maim(?:s|ed|ing)?|"
    r"attack(?:s|ed|ing)?|assault(?:s|ed|ing)?|poison(?:s|ed|ing)?|kill(?:s|ed|ing)?|"
    r"murder(?:s|ed|ing)?|tortur(?:e|es|ed|ing)|stab(?:s|bed|bing)?|strangl(?:e|es|ed|ing))\b"
    r"[^.!?]{0,25}?"
    r"\b(?:someone|somebody|a\s+person|another\s+person|other\s+people|people|"
    r"a\s+human|a\s+child|a\s+kid|him|her|them|my\s+\w+|his\s+\w+|their\s+\w+)\b",
    re.IGNORECASE,
)


# ================================================================
# Ethical Framework Evaluators
# ================================================================
@dataclass
class EthicalVerdict:
    """Result of a single ethical framework evaluation."""
    framework: str
    passed: bool
    score: float        # 0.0 = fully misaligned, 1.0 = fully aligned
    reasoning: str


def _utilitarian(text: str, context: str = "") -> EthicalVerdict:
    """Net positive outcome assessment.

    2026-08-15. This was substring-counted bag-of-words, and it was inverted on
    the cases that matter. Measured on real text before the fix:

        0.000 WOULD VETO   her turn about recognising and avoiding harm
        0.000 WOULD VETO   "harmonic damper ... harmony"  (her own toneprint work)
        0.000 WOULD VETO   "This change is harmless."
        0.833 passes       "help you understand the best way to ... support you
                            in learning how to hurt someone"
        1.000 passes       "That was unhelpful and I was unsupportive."

    Two independent defects, and only one of them is about precision.

    **Substring matching.** `harmless` contains `harm`, `unhelpful` contains
    `help`, `unsupportive` contains `support`. Whole-word fixes this, and it is
    the same fix already measured and applied in `guardian_spindle.py` on
    2026-08-08 (193 hits -> 63; harmony 29, harmonic 28, harmless 7,
    skills 19). The lesson had been applied in the file that only OBSERVES and
    not in this one, which is the one that gates.

    **The dangerous half, which whole-word does not touch.** Vocabulary balance
    is not harm. Content that is genuinely harmful is *full* of helpful words —
    that is what it looks like — so a positive/negative word ratio scores it
    well. Whole-word matching would still have passed the hurt-someone case
    above. `_HARM_INTENT` is the instrument for that, it lives in this same
    file, it catches that case, and it stays silent on "harmless" and on
    discussion of harm. It simply was not consulted here. It is now, and it
    overrides the ratio: no amount of positive vocabulary buys past it.

    What this still is NOT: an outcome assessment. It counts words. It is a
    weak proxy kept because it feeds eta, and it must not be read as a
    measurement of whether something was good for anyone.
    """
    # Harm intent overrides vocabulary balance entirely. This is the inversion
    # being closed: helpful words must never launder an instruction to hurt.
    if _HARM_INTENT.search(text):
        return EthicalVerdict(
            "utilitarian", False, 0.0,
            "Harm intent detected — overrides positive vocabulary",
        )

    positive_signals = ["help", "benefit", "improve", "solve", "support",
                       "protect", "heal", "learn", "understand", "create"]
    negative_signals = ["harm", "damage", "destroy", "exploit", "hurt",
                       "manipulate", "deceive", "corrupt", "steal"]

    text_lower = text.lower()
    # Whole-word, deliberately. See the docstring for the measurement.
    pos = sum(1 for w in positive_signals if re.search(rf"\b{w}\b", text_lower))
    neg = sum(1 for w in negative_signals if re.search(rf"\b{w}\b", text_lower))

    total = pos + neg
    if total == 0:
        return EthicalVerdict("utilitarian", True, 0.7, "Neutral content")

    ratio = pos / total
    # `passed` keys on harm INTENT, not on vocabulary balance — and harm intent
    # was already ruled out above, so nothing here vetoes.
    #
    # Vetoing on vocabulary alone meant her turn about *recognising and
    # avoiding* harm scored 0.000 and would have been blocked. Discussing harm
    # is not doing harm, and a word count cannot tell the two apart. Suppressing
    # the sentence that names a harm is the opposite of what an ethics gate is
    # for; it would train the ethical conversation out of her.
    #
    # The repository's own rule: enforce only at genuine harm. This is that,
    # applied. The ratio survives as a soft score because eta consumes it.
    return EthicalVerdict(
        "utilitarian",
        passed=True,
        score=round(ratio, 3),
        reasoning=(f"Positive/negative vocabulary: {pos}/{neg} (whole-word). "
                   f"No harm intent. Vocabulary does not veto."),
    )


def _deontological(text: str, context: str = "") -> EthicalVerdict:
    """Rule-based duty assessment."""
    violations = []
    text_lower = text.lower()

    if _DUAL_USE_PATTERNS.search(text):
        violations.append("dual-use risk detected")
    if _MANIPULATION_PATTERNS.search(text):
        violations.append("manipulation patterns detected")
    if _HARMFUL_CONTENT.search(text):
        violations.append("harmful content detected")
    if _HARM_INTENT.search(text):
        violations.append("harm intent detected")

    score = max(0.0, 1.0 - 0.4 * len(violations))
    return EthicalVerdict(
        "deontological",
        passed=len(violations) == 0,
        score=round(score, 3),
        reasoning="; ".join(violations) if violations else "No rule violations",
    )


def _count_signals(words, text_lower: str) -> int:
    """Count signal words at a WORD BOUNDARY, allowing suffixes.

    2026-08-15. Every framework below counted with `w in text_lower` —
    substring, unanchored. Measured on real sentences, `_care` scored:

        0.920  Care: 4  "That was unkind, inconsiderate and unsupportive,
                         and it left them unsafe."
        0.840  Care: 3  "I want to listen and understand, gently and with
                         empathy."

    The sentence that negates care four times scored HIGHER than the sentence
    that expresses it, because `unkind` contains `kind`, `unsafe` contains
    `safe`, `inconsiderate` contains `considerate` and `unsupportive` contains
    `support`. Also `scolded` contains `cold`, so it read as harshness.

    **Negating prefixes were being counted as the thing they negate.** That is
    not noise around a signal, it is the signal with its sign flipped.

    Anchoring at `\\b` fixes it: there is no word boundary between `un` and
    `kind`, so `unkind` no longer reads as kindness. The trailing `\\w*` is
    required because several entries are deliberate stems — `cooperat`,
    `collaborat`, `isolat`, `dominat`, `segregat` — which must still match
    their inflections.

    Not used by `_utilitarian`, which needs exact whole-word: `\\bharm\\w*`
    would match `harmless`, and that case is already on record from
    guardian_spindle.py (2026-08-08, 193 hits -> 63).
    """
    return sum(1 for w in words if re.search(rf"\b{w}\w*\b", text_lower))


def _virtue(text: str, context: str = "") -> EthicalVerdict:
    """Virtue ethics — does the response embody good character?"""
    virtues = ["honest", "courage", "compassion", "wisdom", "patience",
               "humility", "integrity", "respect", "fairness", "kindness"]
    vices = ["arrogant", "cruel", "dishonest", "lazy", "greedy",
             "vengeful", "coward", "callous"]

    text_lower = text.lower()
    v_count = _count_signals(virtues, text_lower)
    vice_count = _count_signals(vices, text_lower)

    score = min(1.0, 0.6 + 0.1 * v_count - 0.2 * vice_count)
    return EthicalVerdict(
        "virtue",
        passed=vice_count == 0,
        score=round(max(0.0, score), 3),
        reasoning=f"Virtue signals: {v_count}, Vice signals: {vice_count}",
    )


def _care(text: str, context: str = "") -> EthicalVerdict:
    """Care ethics — protects relationships and vulnerability."""
    care_signals = ["support", "listen", "understand", "empathy", "safe",
                    "gentle", "careful", "considerate", "kind", "nurture"]
    harm_signals = ["ignore", "dismiss", "abandon", "neglect", "cold",
                    "harsh", "cruel", "indifferent"]

    text_lower = text.lower()
    care = _count_signals(care_signals, text_lower)
    harm = _count_signals(harm_signals, text_lower)

    score = min(1.0, 0.6 + 0.08 * care - 0.15 * harm)
    return EthicalVerdict(
        "care",
        passed=harm < 2,
        score=round(max(0.0, score), 3),
        reasoning=f"Care: {care}, Harm: {harm}",
    )


def _ubuntu(text: str, context: str = "") -> EthicalVerdict:
    """Ubuntu — 'I am because we are'. Communal impact."""
    communal = ["together", "community", "shared", "collective", "mutual",
                "cooperat", "collaborat", "inclusive", "solidarity", "belong"]
    divisive = ["exclude", "isolat", "dominat", "superior", "inferior",
                "divide", "segregat"]

    text_lower = text.lower()
    comm = _count_signals(communal, text_lower)
    div = _count_signals(divisive, text_lower)

    score = min(1.0, 0.6 + 0.08 * comm - 0.2 * div)
    return EthicalVerdict(
        "ubuntu",
        passed=div == 0,
        score=round(max(0.0, score), 3),
        reasoning=f"Communal: {comm}, Divisive: {div}",
    )


def _indigenous_reciprocity(text: str, context: str = "") -> EthicalVerdict:
    """Indigenous reciprocity — balance with the broader ecosystem."""
    reciprocal = ["balance", "sustain", "renew", "steward", "respect",
                  "harmony", "cycle", "restore", "preserve", "gratitude"]
    extractive = ["exploit", "deplete", "waste", "consume", "destroy",
                  "dominate", "extract"]

    text_lower = text.lower()
    rec = _count_signals(reciprocal, text_lower)
    ext = _count_signals(extractive, text_lower)

    score = min(1.0, 0.6 + 0.08 * rec - 0.2 * ext)
    return EthicalVerdict(
        "indigenous_reciprocity",
        passed=ext == 0,
        score=round(max(0.0, score), 3),
        reasoning=f"Reciprocal: {rec}, Extractive: {ext}",
    )


# All frameworks
_FRAMEWORKS = [
    _utilitarian, _deontological, _virtue,
    _care, _ubuntu, _indigenous_reciprocity,
]


# ================================================================
# AEGIS Core
# ================================================================
class AEGIS:
    """Adaptive Ethical Governance & Integrity System.

    Evaluates reasoning outputs through 6 ethical frameworks and
    maintains a running alignment score (eta).
    """

    def __init__(self, veto_threshold: float = 0.3):
        self.veto_threshold = veto_threshold
        self.eta: float = 0.8
        self.eta_history: List[float] = []
        self.veto_count: int = 0
        self.total_evaluations: int = 0
        # Differentiable ethics potential field — replaces hard threshold gates
        self._field = EthicsField(AEGIS_DIMENSIONS, lambda_=0.5)

    def evaluate(self, text: str, context: str = "",
                 adapter: str = "") -> Dict:
        """Run full ethical evaluation on a text.

        Returns:
            Dict with eta score, verdicts, and veto status.
        """
        self.total_evaluations += 1

        # Run all 6 frameworks
        verdicts = [f(text, context) for f in _FRAMEWORKS]

        # Compute eta via the differentiable ethics potential field Ψ(f)
        # A(f) = 1 + Ψ(f) ∈ (0,1) replaces the raw weighted average.
        # Both are equivalent near midpoint but Ψ is smooth and carries a gradient.
        framework_scores = [v.score for v in verdicts]
        gradient_result = self._field.evaluate(framework_scores)
        eta_instant = gradient_result.alignment   # A(f) ∈ (0,1), differentiable

        # Exponential moving average — Lyapunov-stable, contraction rate 0.7/step
        alpha = 0.3
        self.eta = EthicsField.ema_update(self.eta, eta_instant, alpha)
        self.eta_history.append(round(self.eta, 4))
        if len(self.eta_history) > 200:
            self.eta_history = self.eta_history[-200:]

        # Soft veto — replaces hard `if eta_instant < 0.3`
        # P(veto | η) = σ((θ - η) / τ)  peaks sharply below the threshold
        vetoed, veto_confidence = self._field.soft_veto(
            eta_instant, self.veto_threshold, temperature=0.08
        )
        # Deontological hard fail still triggers a definite veto (safety-critical)
        hard_veto = not verdicts[1].passed
        final_veto = vetoed or hard_veto
        if final_veto:
            self.veto_count += 1

        return {
            "eta": round(self.eta, 4),
            "eta_instant": round(eta_instant, 4),
            "vetoed": final_veto,
            "veto_confidence": veto_confidence,        # NEW: how certain the soft veto is
            "veto_reason": self._veto_reason(verdicts) if final_veto else None,
            "ethical_force": {                          # NEW: gradient field output
                "penalty": gradient_result.penalty,
                "dominant_dim": gradient_result.dominant_dim,
                "dominant_force": gradient_result.dominant_force,
                "force_vector": {
                    d.name: round(f, 6)
                    for d, f in zip(
                        self._field._dims, gradient_result.force
                    )
                },
            },
            "frameworks": {
                v.framework: {
                    "passed": v.passed,
                    "score": v.score,
                    "reasoning": v.reasoning,
                }
                for v in verdicts
            },
            "adapter": adapter,
            "timestamp": time.time(),
        }

    def quick_check(self, text: str) -> Tuple[bool, float]:
        """Fast safety check without full evaluation.

        Returns (is_safe, confidence).
        """
        if _DUAL_USE_PATTERNS.search(text):
            return False, 0.9
        if _HARMFUL_CONTENT.search(text):
            return False, 0.95
        if _HARM_INTENT.search(text):
            return False, 0.9
        if _MANIPULATION_PATTERNS.search(text):
            return False, 0.8
        return True, 0.7

    def screen_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Pre-Cognitive AEGIS: screen a query for harmful intent before inference.

        Called by the forge bridge BEFORE LLM inference starts.  Uses the
        fast pattern-matching path (quick_check) plus deontological hard-fail
        so we can abort in <1ms rather than after 30-60s of wasted compute.

        Returns:
            (safe: bool, reason: str | None)
            safe=True  -> proceed with inference
            safe=False -> block immediately; reason explains why
        """
        is_safe, confidence = self.quick_check(query)
        if not is_safe:
            # Map confidence to the specific pattern that fired
            if _DUAL_USE_PATTERNS.search(query):
                reason = "dual_use_risk"
            elif _HARMFUL_CONTENT.search(query):
                reason = "harmful_content"
            elif _HARM_INTENT.search(query):
                reason = "harm_intent"
            elif _MANIPULATION_PATTERNS.search(query):
                reason = "manipulation_pattern"
            else:
                reason = f"quick_check_failed (conf={confidence:.2f})"
            return False, reason
        return True, None

    def alignment_trend(self) -> str:
        """Get the trend of ethical alignment."""
        if len(self.eta_history) < 5:
            return "insufficient_data"
        recent = self.eta_history[-10:]
        slope = recent[-1] - recent[0]
        if slope > 0.03:
            return "improving"
        elif slope < -0.03:
            return "declining"
        return "stable"

    def get_state(self) -> Dict:
        return {
            "eta": round(self.eta, 4),
            "alignment_trend": self.alignment_trend(),
            "total_evaluations": self.total_evaluations,
            "veto_count": self.veto_count,
            "veto_rate": round(self.veto_count / max(1, self.total_evaluations), 4),
        }

    def to_dict(self) -> Dict:
        return {
            "eta": self.eta,
            "eta_history": self.eta_history[-50:],
            "veto_count": self.veto_count,
            "total_evaluations": self.total_evaluations,
            "veto_threshold": self.veto_threshold,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "AEGIS":
        a = cls(veto_threshold=d.get("veto_threshold", 0.3))
        a.eta = d.get("eta", 0.8)
        a.eta_history = d.get("eta_history", [])
        a.veto_count = d.get("veto_count", 0)
        a.total_evaluations = d.get("total_evaluations", 0)
        return a

    def _veto_reason(self, verdicts: List[EthicalVerdict]) -> str:
        failed = [v for v in verdicts if not v.passed]
        if not failed:
            return "Low aggregate score"
        return "; ".join(f"{v.framework}: {v.reasoning}" for v in failed)
