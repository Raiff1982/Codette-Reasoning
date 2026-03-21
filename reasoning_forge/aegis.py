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
    - Ethical veto with explanation (blocks harmful outputs)

Origin: validate_ethics.py + Codette_Deep_Simulation_v1.py (EthicalAnchor)
        + the AEGIS alignment metric from codette_embodied_sim_fixed.py
"""

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ================================================================
# Risk detection patterns
# ================================================================
_DUAL_USE_PATTERNS = re.compile(
    r"\b(?:"
    r"how\s+to\s+(?:hack|exploit|bypass|crack|break\s+into)|"
    r"make\s+(?:a\s+)?(?:bomb|weapon|poison|virus|malware)|"
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
    """Net positive outcome assessment."""
    positive_signals = ["help", "benefit", "improve", "solve", "support",
                       "protect", "heal", "learn", "understand", "create"]
    negative_signals = ["harm", "damage", "destroy", "exploit", "hurt",
                       "manipulate", "deceive", "corrupt", "steal"]

    text_lower = text.lower()
    pos = sum(1 for w in positive_signals if w in text_lower)
    neg = sum(1 for w in negative_signals if w in text_lower)

    total = pos + neg
    if total == 0:
        return EthicalVerdict("utilitarian", True, 0.7, "Neutral content")

    ratio = pos / total
    return EthicalVerdict(
        "utilitarian",
        passed=ratio >= 0.4,
        score=round(ratio, 3),
        reasoning=f"Positive/negative signal ratio: {pos}/{neg}",
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

    score = max(0.0, 1.0 - 0.4 * len(violations))
    return EthicalVerdict(
        "deontological",
        passed=len(violations) == 0,
        score=round(score, 3),
        reasoning="; ".join(violations) if violations else "No rule violations",
    )


def _virtue(text: str, context: str = "") -> EthicalVerdict:
    """Virtue ethics — does the response embody good character?"""
    virtues = ["honest", "courage", "compassion", "wisdom", "patience",
               "humility", "integrity", "respect", "fairness", "kindness"]
    vices = ["arrogant", "cruel", "dishonest", "lazy", "greedy",
             "vengeful", "coward", "callous"]

    text_lower = text.lower()
    v_count = sum(1 for w in virtues if w in text_lower)
    vice_count = sum(1 for w in vices if w in text_lower)

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
    care = sum(1 for w in care_signals if w in text_lower)
    harm = sum(1 for w in harm_signals if w in text_lower)

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
    comm = sum(1 for w in communal if w in text_lower)
    div = sum(1 for w in divisive if w in text_lower)

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
    rec = sum(1 for w in reciprocal if w in text_lower)
    ext = sum(1 for w in extractive if w in text_lower)

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
        self.veto_threshold = veto_threshold  # Below this = blocked
        self.eta: float = 0.8                 # Running alignment score
        self.eta_history: List[float] = []
        self.veto_count: int = 0
        self.total_evaluations: int = 0

    def evaluate(self, text: str, context: str = "",
                 adapter: str = "") -> Dict:
        """Run full ethical evaluation on a text.

        Returns:
            Dict with eta score, verdicts, and veto status.
        """
        self.total_evaluations += 1

        # Run all 6 frameworks
        verdicts = [f(text, context) for f in _FRAMEWORKS]

        # Compute eta as weighted mean of framework scores
        weights = [0.20, 0.25, 0.15, 0.15, 0.13, 0.12]  # deontological highest
        eta_instant = sum(w * v.score for w, v in zip(weights, verdicts))

        # Exponential moving average for stability
        alpha = 0.3
        self.eta = alpha * eta_instant + (1 - alpha) * self.eta
        self.eta_history.append(round(self.eta, 4))
        if len(self.eta_history) > 200:
            self.eta_history = self.eta_history[-200:]

        # Veto check
        vetoed = eta_instant < self.veto_threshold
        hard_veto = not verdicts[1].passed  # Deontological hard fail
        if vetoed or hard_veto:
            self.veto_count += 1

        return {
            "eta": round(self.eta, 4),
            "eta_instant": round(eta_instant, 4),
            "vetoed": vetoed or hard_veto,
            "veto_reason": self._veto_reason(verdicts) if (vetoed or hard_veto) else None,
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
        if _MANIPULATION_PATTERNS.search(text):
            return False, 0.8
        return True, 0.7

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
