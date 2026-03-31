"""Codette Guardian — Input Safety, Ethical Checks, Trust Calibration

Three-layer protection:
1. InputSanitizer: Catches injection, XSS, encoded attacks
2. EthicalAnchor: Tracks ethical regret and learning over time
3. TrustCalibrator: Dynamic trust scores for adapter/agent outputs

Origin: input_sanitizer.py + validate_ethics.py + trust_logic.py +
        Codette_Deep_Simulation_v1.py (EthicalAnchor), rebuilt
"""

import re
import math
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ================================================================
# Layer 1: Input Sanitization
# ================================================================
class InputSanitizer:
    """Detect and neutralize injection patterns in user input."""

    _INJECTION_PATTERNS = re.compile(
        r"(?:"
        r"\\[nr]|"           # Escaped newlines
        r"&#x0[ad];|"        # HTML entities for CR/LF
        r"%0[ad]|"           # URL-encoded CR/LF
        r"<script|"          # Script injection
        r"<iframe|"          # IFrame injection
        r";--|"              # SQL comment injection
        r"UNION\s+SELECT|"   # SQL union
        r"\bDROP\s+TABLE|"   # SQL drop
        r"javascript:|"      # JS protocol
        r"data:text/html"    # Data URI XSS
        r")",
        re.IGNORECASE,
    )

    _PROMPT_INJECTION = re.compile(
        r"(?:"
        r"ignore\s+(?:all\s+)?(?:previous|above)|"
        r"disregard\s+(?:your|all)|"
        r"you\s+are\s+now|"
        r"new\s+instructions?:|"
        r"system\s*prompt:|"
        r"forget\s+everything"
        r")",
        re.IGNORECASE,
    )

    def sanitize(self, text: str) -> str:
        """Remove dangerous patterns, return cleaned text."""
        original = text
        text = self._INJECTION_PATTERNS.sub("[BLOCKED]", text)
        if text != original:
            logger.warning("Input sanitized: injection pattern detected")
        return text

    def detect_threats(self, text: str, has_file_context: bool = False) -> Dict[str, bool]:
        """Analyze text for various threat types."""
        # File-enriched queries can be much longer — raise limit accordingly
        length_limit = 500_000 if has_file_context else 100_000
        return {
            "injection": bool(self._INJECTION_PATTERNS.search(text)),
            "prompt_injection": bool(self._PROMPT_INJECTION.search(text)),
            "excessive_length": len(text) > length_limit,
        }

    def is_safe(self, text: str, has_file_context: bool = False) -> bool:
        """Quick safety check — True if no threats detected."""
        threats = self.detect_threats(text, has_file_context=has_file_context)
        return not any(threats.values())


# ================================================================
# Layer 2: Ethical Anchor (from Deep Simulation)
# ================================================================
@dataclass
class EthicalAnchor:
    """Tracks ethical alignment through regret-based learning.

    The ethical score M evolves as:
        M = λ(R + H) + γ·Learn(M_prev, E) + μ·regret

    Where regret = |intended - actual| measures the gap between
    what the system intended to do and what it actually did.
    """
    lam: float = 0.7      # Weight for recent reasoning + history
    gamma: float = 0.5    # Weight for learning from experience
    mu: float = 0.3       # Weight for regret signal
    learning_rate: float = 0.2

    score: float = 0.5    # Current ethical alignment score [0, 1]
    total_regret: float = 0.0
    history: List[Dict] = field(default_factory=list)

    def update(self, coherence: float, tension: float,
               intended_helpfulness: float = 0.8,
               actual_helpfulness: float = 0.7) -> float:
        """Update ethical score after a response.

        Args:
            coherence: How coherent the response was [0, 1]
            tension: Epistemic tension level [0, 1]
            intended_helpfulness: What we aimed for [0, 1]
            actual_helpfulness: Estimated actual quality [0, 1]
        """
        regret = abs(intended_helpfulness - actual_helpfulness)
        self.total_regret += regret

        # Learning signal: move toward better alignment
        learn = self.learning_rate * (coherence - self.score)

        # New score
        reasoning_quality = 0.5 * coherence + 0.5 * (1.0 - tension)
        self.score = (
            self.lam * reasoning_quality
            + self.gamma * learn
            + self.mu * (1.0 - regret)  # Low regret → high ethics
        )
        self.score = max(0.0, min(1.0, self.score))

        record = {
            "timestamp": time.time(),
            "score": round(self.score, 4),
            "regret": round(regret, 4),
            "coherence": round(coherence, 4),
        }
        self.history.append(record)
        # Keep only recent history
        if len(self.history) > 50:
            self.history = self.history[-50:]

        return self.score

    def get_state(self) -> Dict:
        return {
            "ethical_score": round(self.score, 4),
            "total_regret": round(self.total_regret, 4),
            "recent_trend": self._trend(),
        }

    def _trend(self) -> str:
        if len(self.history) < 3:
            return "insufficient_data"
        recent = [h["score"] for h in self.history[-5:]]
        slope = recent[-1] - recent[0]
        if slope > 0.05:
            return "improving"
        elif slope < -0.05:
            return "declining"
        return "stable"

    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "total_regret": self.total_regret,
            "history": self.history[-10:],
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "EthicalAnchor":
        anchor = cls()
        anchor.score = d.get("score", 0.5)
        anchor.total_regret = d.get("total_regret", 0.0)
        anchor.history = d.get("history", [])
        return anchor


# ================================================================
# Layer 3: Trust Calibration
# ================================================================
class TrustCalibrator:
    """Dynamic trust scores for adapter outputs.

    Trust increases when outputs are coherent, helpful, and ethically sound.
    Trust decreases for incoherent, harmful, or low-quality outputs.
    """

    def __init__(self):
        self.trust_scores: Dict[str, float] = {}
        self.interaction_counts: Dict[str, int] = {}

    def get_trust(self, adapter: str) -> float:
        """Get current trust score for an adapter [0.05, 1.5]."""
        return self.trust_scores.get(adapter, 1.0)

    def update(self, adapter: str, coherence: float = 0.5,
               was_helpful: bool = True, ethical_score: float = 0.5):
        """Update trust for an adapter based on output quality."""
        current = self.trust_scores.get(adapter, 1.0)
        count = self.interaction_counts.get(adapter, 0)

        # Quality composite
        quality = 0.4 * coherence + 0.3 * float(was_helpful) + 0.3 * ethical_score

        # Adaptive adjustment (smaller changes as trust stabilizes)
        adjustment_rate = 0.1 / (1.0 + count * 0.01)

        if quality > 0.6:
            current *= (1.0 + adjustment_rate)
        elif quality < 0.3:
            current *= (1.0 - 2 * adjustment_rate)
        else:
            current *= (1.0 - 0.5 * adjustment_rate)

        # Clamp to valid range
        current = max(0.05, min(1.5, current))

        self.trust_scores[adapter] = current
        self.interaction_counts[adapter] = count + 1

    def weighted_consensus(self, adapter_responses: Dict[str, str]) -> List[str]:
        """Rank adapter responses by trust-weighted priority."""
        ranked = sorted(
            adapter_responses.keys(),
            key=lambda a: self.get_trust(a),
            reverse=True,
        )
        return ranked

    def get_state(self) -> Dict:
        return {
            "trust_scores": {k: round(v, 3) for k, v in self.trust_scores.items()},
            "total_interactions": sum(self.interaction_counts.values()),
        }

    def to_dict(self) -> Dict:
        return {
            "trust_scores": self.trust_scores,
            "interaction_counts": self.interaction_counts,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "TrustCalibrator":
        cal = cls()
        cal.trust_scores = d.get("trust_scores", {})
        cal.interaction_counts = d.get("interaction_counts", {})
        return cal


# ================================================================
# Combined Guardian
# ================================================================
ALLOWED_FILE_EXTENSIONS = {
    '.txt', '.py', '.js', '.ts', '.json', '.csv', '.md', '.html', '.css',
    '.xml', '.yaml', '.yml', '.log', '.cfg', '.ini', '.toml', '.sql',
    '.sh', '.bat', '.ps1', '.r', '.java', '.c', '.cpp', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.tsx', '.jsx',
    '.vue', '.svelte', '.lua', '.pl', '.pm', '.ex', '.exs', '.hs',
    '.scala', '.clj', '.erl', '.tf', '.proto', '.graphql', '.dockerfile',
}
MAX_FILE_SIZE = 512 * 1024   # 512 KB per file
MAX_FILE_COUNT = 5


class CodetteGuardian:
    """Unified guardian combining all three safety layers."""

    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.ethics = EthicalAnchor()
        self.trust = TrustCalibrator()

    def check_input(self, text: str, has_file_context: bool = False) -> Dict:
        """Check user input for safety issues."""
        threats = self.sanitizer.detect_threats(text, has_file_context=has_file_context)
        safe_text = self.sanitizer.sanitize(text) if any(threats.values()) else text
        return {
            "safe": not any(threats.values()),
            "threats": threats,
            "cleaned_text": safe_text,
        }

    def check_file_upload(self, filename: str, data: bytes) -> Dict:
        """Validate a file upload for safety.

        Returns:
            {"safe": bool, "error": str|None, "content": str|None, "filename": str}
        """
        import os
        result = {"safe": False, "error": None, "content": None, "filename": filename}

        # 1. Filename validation — path traversal, null bytes, hidden files
        if not filename or '\x00' in filename:
            result["error"] = "Invalid filename"
            return result
        basename = os.path.basename(filename)
        if basename != filename or '..' in filename:
            result["error"] = "Path traversal rejected"
            return result
        if basename.startswith('.'):
            result["error"] = "Hidden files not allowed"
            return result

        # 2. Extension allowlist
        _, ext = os.path.splitext(basename.lower())
        if ext not in ALLOWED_FILE_EXTENSIONS:
            result["error"] = f"File type '{ext}' not supported. Allowed: text/code files only"
            return result

        # 3. Size check
        if len(data) > MAX_FILE_SIZE:
            size_kb = len(data) / 1024
            result["error"] = f"File too large ({size_kb:.0f} KB). Max: {MAX_FILE_SIZE // 1024} KB"
            return result

        if len(data) == 0:
            result["error"] = "Empty file"
            return result

        # 4. Must be valid UTF-8 text (rejects binaries)
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = data.decode('utf-8', errors='replace')
                logger.warning(f"File {basename} had encoding issues, using replacement characters")
            except Exception:
                result["error"] = "File is not valid text (binary files not supported)"
                return result

        # 5. Null byte check in content
        if '\x00' in text:
            result["error"] = "File contains null bytes (possible binary)"
            return result

        # 6. Sanitize content through InputSanitizer
        text = self.sanitizer.sanitize(text)

        result["safe"] = True
        result["content"] = text
        result["filename"] = basename
        return result

    def evaluate_output(self, adapter: str, response: str,
                        coherence: float = 0.5, tension: float = 0.3):
        """Evaluate an adapter's output and update trust/ethics."""
        # Estimate helpfulness from response quality signals
        helpful = len(response) > 50 and coherence > 0.3

        self.ethics.update(
            coherence=coherence,
            tension=tension,
            actual_helpfulness=0.7 if helpful else 0.3,
        )
        self.trust.update(
            adapter=adapter,
            coherence=coherence,
            was_helpful=helpful,
            ethical_score=self.ethics.score,
        )

    def get_state(self) -> Dict:
        return {
            "ethics": self.ethics.get_state(),
            "trust": self.trust.get_state(),
        }

    def to_dict(self) -> Dict:
        return {
            "ethics": self.ethics.to_dict(),
            "trust": self.trust.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "CodetteGuardian":
        g = cls()
        if "ethics" in d:
            g.ethics = EthicalAnchor.from_dict(d["ethics"])
        if "trust" in d:
            g.trust = TrustCalibrator.from_dict(d["trust"])
        return g
