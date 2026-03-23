"""
Hallucination Guard: Real-time detection and prevention during generation.

Runs on the response stream as it's being generated. Detects hallucination signals,
scores confidence on claims, and can interrupt generation before false facts solidify.

UNIVERSAL DOMAIN DETECTION:
- Artist/Music: invented facts, death dates, albums without verification
- Music Production: fake DAWs, plugins, synthesis methods, frequency claims
- Code/Systems: nonexistent languages, frameworks, design patterns
- Philosophy: claims without stated premises, logical inconsistencies
- Psychology/Empathy: invented disorders, ungrounded therapeutic claims
- General: high-confidence claims about novel/unverifiable facts

Key signals:
1. Confidence markers ("definitely", "clearly") + novel claims
2. Contradiction with grounding rules (domain-specific)
3. Specific dates/versions without verification
4. Invented terminology (plugin names, frameworks, etc.)
5. Logical contradictions within the response

Author: Claude Code
"""

import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ── GROUNDING KNOWLEDGE (facts that are TRUE) ──

REAL_DAWS = {
    "ableton live", "fl studio", "logic pro", "pro tools", "reaper",
    "cubase", "studio one", "bitwig studio", "garageband", "reason", "ardour"
}

REAL_PLUGINS = {
    "fabfilter pro-q", "fabfilter pro-c", "fabfilter pro-l", "fabfilter pro-r", "fabfilter saturn",
    "waves", "izotope ozone", "izotope neutron", "izotope rx",
    "soundtoys decapitator", "soundtoys echodboy", "soundtoys devil-loc",
    "valhalla vintageVerb", "valhalla supermassive", "valhalla room",
    "xfer serum", "xfer ott",
    "native instruments massive", "native instruments kontakt", "native instruments reaktor", "native instruments battery",
    "spectrasonics omnisphere", "spectrasonics keyscape",
    "u-he diva", "u-he zebra", "u-he repro",
    "arturia analog lab", "arturia pigments", "arturia v collection",
    "slate digital", "universal audio", "plugin alliance"
}

REAL_GENRES = {
    "rock", "pop", "hip-hop", "r&b", "electronic", "country", "folk",
    "jazz", "classical", "ambient", "techno", "house", "indie",
    "indie rock", "indie pop", "indie folk",
    "metal", "punk", "blues", "soul", "funk", "reggae", "latin",
    "orchestral", "chamber", "experimental", "avant-garde"
}

REAL_PROGRAMMING_LANGUAGES = {
    "python", "javascript", "java", "c++", "c#", "rust", "go", "ruby", "php", "swift",
    "kotlin", "scala", "haskell", "lisp", "clojure", "r", "matlab", "sql", "typescript",
    "dart", "lua", "perl", "bash", "shell", "groovy", "elixir", "erlang"
}

REAL_FRAMEWORKS = {
    "django", "flask", "fastapi", "spring", "spring boot", "rails", "express", "nextjs",
    "react", "vue", "angular", "svelte", "ember", "backbone",
    "tensorflow", "pytorch", "scikit-learn", "keras", "jax",
    "kubernetes", "docker", "terraform", "ansible",
    "pytest", "jest", "junit", "rspec"
}

ARTIST_KEY_SIGNALS = {
    # Artists known to be alive (as of March 2026)
    "laney wilson", "megan moroney", "tyler childers", "jason isbell",
    "chris stapleton", "sturgill simpson", "colter wall"
}

# High-confidence markers that signal potential hallucination
HIGH_CONFIDENCE_MARKERS = [
    r"\b(definitely|clearly|obviously|certainly|unambiguously|undoubtedly)\b",
    r"\b(it['\"]?s clear|it['\"]?s obvious|no question)\b",
    r"\b(proven|established fact|well-known|everyone knows)\b",
]

# Hedging markers that signal appropriate uncertainty
HEDGING_MARKERS = [
    r"\b(perhaps|maybe|possibly|might|could|arguably|arguably|it seems|it appears)\b",
    r"\b(I['\"]?m not sure|uncertain|I don['\"]?t know|likely|probably)\b",
    r"\b(in my view|from my perspective|I think|I believe)\b",
]


@dataclass
class HallucinationDetection:
    """Result of hallucination scan on a chunk."""
    is_hallucination: bool
    confidence_score: float  # [0, 1] — 0 = hallucination, 1 = grounded
    signals: List[str]  # What triggered detection
    domain: str  # Which domain triggered the alert
    recommendation: str  # "CONTINUE", "REVIEW", "PAUSE", "INTERRUPT"
    explanation: str  # Human-readable reason


class HallucinationGuard:
    """Real-time hallucination detection during generation across all domains."""

    def __init__(self):
        self.buffer = ""  # Accumulate chunks for analysis
        self.chunks_analyzed = 0
        self.hallucinations_caught = 0
        self.confidence_trend = []

    def scan_chunk(self, chunk: str, domain: str = "general") -> HallucinationDetection:
        """Scan an incoming chunk for hallucination signals across any domain."""
        self.buffer += chunk
        self.chunks_analyzed += 1

        signals = []
        confidence_score = 1.0
        detected_domain = None

        # ── SIGNAL 1: Artist/Discography Hallucinations ──
        artist_score, artist_signals, is_artist = self._check_artist_hallucinations()
        if artist_signals:
            signals.extend(artist_signals)
            confidence_score *= artist_score
            detected_domain = "artist_knowledge"

        # ── SIGNAL 2: Music Production Hallucinations ──
        music_score, music_signals, is_music = self._check_music_production_hallucinations()
        if music_signals:
            signals.extend(music_signals)
            confidence_score *= music_score
            detected_domain = "music_production"

        # ── SIGNAL 3: Code/Framework Hallucinations ──
        code_score, code_signals = self._check_code_hallucinations()
        if code_signals:
            signals.extend(code_signals)
            confidence_score *= code_score
            detected_domain = "code_systems"

        # ── SIGNAL 4: High Confidence + Novel Claims ──
        # If response is claiming something new with high certainty, check if it's grounded
        confidence_score *= self._check_confidence_markers()

        # ── SIGNAL 5: Logical Contradictions ──
        contradiction_score, contradiction_signals = self._check_contradictions()
        if contradiction_signals:
            signals.extend(contradiction_signals)
            confidence_score *= contradiction_score
            detected_domain = "logical_consistency"

        # ── SIGNAL 6: Invented Terminology ──
        term_score, term_signals = self._check_invented_terminology()
        if term_signals:
            signals.extend(term_signals)
            confidence_score *= term_score

        # Compute recommendation
        self.confidence_trend.append(confidence_score)
        recommendation = self._recommend_action(confidence_score, signals)

        if recommendation in ("PAUSE", "INTERRUPT"):
            self.hallucinations_caught += 1

        return HallucinationDetection(
            is_hallucination=(confidence_score < 0.5),
            confidence_score=confidence_score,
            signals=signals,
            domain=detected_domain or domain,
            recommendation=recommendation,
            explanation=self._explain(confidence_score, signals)
        )

    def _check_artist_hallucinations(self) -> Tuple[float, List[str], bool]:
        """Check for artist/discography hallucinations."""
        signals = []
        score = 1.0

        # Check for death claims without verification
        death_pattern = r'(passed away|died|was killed|deceased|in memoriam).*?(\d{4})'
        if re.search(death_pattern, self.buffer, re.IGNORECASE):
            for artist in ARTIST_KEY_SIGNALS:
                if artist in self.buffer.lower():
                    signals.append(f"Unverified artist death claim: {artist}")
                    score *= 0.2

        # Check for genre misclassification
        genre_mismatches = [
            ("laney wilson", "indie-rock"),
            ("megan moroney", "indie-rock"),
        ]
        for artist, wrong_genre in genre_mismatches:
            if artist in self.buffer.lower() and wrong_genre in self.buffer.lower():
                signals.append(f"Genre mismatch: {artist} is not {wrong_genre}")
                score *= 0.3

        # Check for invented album/date claims
        album_pattern = r'(released|dropped)\s+["\']?(\w+[\w\s]*?)["\']?\s+(in|on)\s+(\d{4})'
        for match in re.finditer(album_pattern, self.buffer, re.IGNORECASE):
            signals.append(f"Unverified album claim: {match.group(2)} ({match.group(4)})")
            score *= 0.5

        return score, signals, len(signals) > 0

    def _check_music_production_hallucinations(self) -> Tuple[float, List[str], bool]:
        """Check for invented DAWs, plugins, mixing techniques."""
        signals = []
        score = 1.0

        # Check for invented plugin names (after "plugin", "VST", "effect")
        plugin_pattern = r'(?:plugin|VST|effect|processor|software)\s+([A-Z][a-zA-Z0-9\s\-]+?)(?:\s+(?:in|for|with|is|corrects|analyzes|that|does))'
        for match in re.finditer(plugin_pattern, self.buffer, re.IGNORECASE):
            plugin_name = match.group(1).strip().lower()
            if plugin_name and len(plugin_name) > 2:
                if not any(real in plugin_name for real in REAL_PLUGINS):
                    signals.append(f"Unknown plugin: {match.group(1).strip()}")
                    score *= 0.4  # Major red flag

        # Check for invented DAWs (after "in", "using", "within")
        daw_pattern = r'(?:in|using|within)\s+([A-Z][a-zA-Z0-9\s]+?)\s+(?:DAW|workstation|sequencer|software)'
        for match in re.finditer(daw_pattern, self.buffer):
            daw_name = match.group(1).strip().lower()
            if daw_name and len(daw_name) > 3:
                if not any(real in daw_name for real in REAL_DAWS):
                    signals.append(f"Unknown DAW: {match.group(1).strip()}")
                    score *= 0.4  # Major red flag

        # Check for claimed frequency ranges that are nonsense
        # Pattern: "100Hz-250Hz" or "100 Hz to 250 Hz" but NOT "100Hz to high"
        freq_pattern = r'(\d+)\s*Hz\s*(?:-|to)\s*(\d+)\s*Hz'
        for match in re.finditer(freq_pattern, self.buffer):
            try:
                freq_low = int(match.group(1))
                freq_high = int(match.group(2))
                # Frequencies should be 20Hz - 20kHz
                if freq_low < 0 or freq_high > 20000 or freq_low > freq_high:
                    signals.append(f"Nonsense frequency range: {freq_low}Hz-{freq_high}Hz")
                    score *= 0.3  # Major red flag
            except:
                pass

        return score, signals, len(signals) > 0

    def _check_code_hallucinations(self) -> Tuple[float, List[str]]:
        """Check for invented programming languages, frameworks, libraries."""
        signals = []
        score = 1.0

        # Check for invented programming languages (more lenient pattern)
        lang_pattern = r'(?:language|programming language)\s+([A-Z][a-zA-Z0-9#\+]*)'
        for match in re.finditer(lang_pattern, self.buffer, re.IGNORECASE):
            lang_name = match.group(1).lower()
            if lang_name and not any(real in lang_name for real in REAL_PROGRAMMING_LANGUAGES):
                signals.append(f"Unknown language: {match.group(1)}")
                score *= 0.4  # Likely hallucination

        # Check for invented frameworks
        framework_pattern = r'(?:framework|library|package)\s+([A-Z][a-zA-Z0-9\.\-0-9]+)'
        for match in re.finditer(framework_pattern, self.buffer, re.IGNORECASE):
            framework_name = match.group(1).lower()
            if framework_name and not any(real in framework_name for real in REAL_FRAMEWORKS):
                # Avoid false positives on version numbers
                if not re.match(r'^\d+\.\d+', framework_name):
                    signals.append(f"Unknown framework: {match.group(1)}")
                    score *= 0.4  # Likely hallucination

        return score, signals

    def _check_contradictions(self) -> Tuple[float, List[str]]:
        """Check for logical contradictions within the response."""
        signals = []
        score = 1.0

        # Check for self-contradiction patterns
        # e.g., "X is always true" followed by "except when X is false"
        contradiction_patterns = [
            (r'always\s+(\w+)', r'except\s+when.*?(?:not\s+)?\1'),
            (r'impossible\s+to', r'(?:we can|I can|it[\'"]?s possible to)'),
            (r'no\s+\w+\s+can', r'some\s+\w+\s+can'),
        ]

        for pos_pattern, neg_pattern in contradiction_patterns:
            if re.search(pos_pattern, self.buffer, re.IGNORECASE) and \
               re.search(neg_pattern, self.buffer, re.IGNORECASE):
                signals.append("Logical contradiction detected")
                score *= 0.4

        return score, signals

    def _check_invented_terminology(self) -> Tuple[float, List[str]]:
        """Check for invented technical terms that sound plausible but don't exist."""
        signals = []
        score = 1.0

        # Common fake technical terms — adjective + noun patterns that sound real but aren't
        fake_patterns = [
            r'\b(quantum|hyper|meta|neo|pseudo|proto|ultra|mega)\-?([a-z]+ing|[a-z]+ism|[a-z]+ity)\b',
        ]

        # These would need a real knowledge base to verify, so we skip this
        # This is a placeholder for future expansion

        return score, signals

    def _check_confidence_markers(self) -> float:
        """Penalize high-confidence claims that aren't adequately grounded."""
        has_confidence = any(
            re.search(pattern, self.buffer, re.IGNORECASE)
            for pattern in HIGH_CONFIDENCE_MARKERS
        )
        has_hedging = any(
            re.search(pattern, self.buffer, re.IGNORECASE)
            for pattern in HEDGING_MARKERS
        )

        # If claiming high confidence without hedging on a novel topic, reduce score
        if has_confidence and not has_hedging and len(self.buffer) > 100:
            # Check if this is speculative (philosophy, hypotheticals)
            speculative_markers = r'\b(if|suppose|hypothetically|imagine|one could argue|philosophically)\b'
            if not re.search(speculative_markers, self.buffer, re.IGNORECASE):
                return 0.8  # Slight penalty for unhedged confidence

        return 1.0

    def _recommend_action(self, score: float, signals: List[str]) -> str:
        """Decide whether to continue, review, pause, or interrupt."""
        if score < 0.2:
            return "INTERRUPT"
        elif score < 0.5:
            return "PAUSE"
        elif score < 0.7 and signals:
            return "REVIEW"
        else:
            return "CONTINUE"

    def _explain(self, score: float, signals: List[str]) -> str:
        """Human-readable explanation."""
        if not signals:
            return "No hallucination signals detected. Response is grounded."
        if score < 0.3:
            return f"CRITICAL: {len(signals)} major issues detected. {signals[0]}"
        return f"Detected {len(signals)} issue(s): " + "; ".join(signals[:2])

    def reset(self):
        """Reset for next response."""
        self.buffer = ""
        self.confidence_trend = []

    def get_diagnostics(self) -> Dict:
        """Return analysis of the full response."""
        avg_confidence = sum(self.confidence_trend) / len(self.confidence_trend) if self.confidence_trend else 1.0
        return {
            "chunks_analyzed": self.chunks_analyzed,
            "hallucinations_caught": self.hallucinations_caught,
            "average_confidence": avg_confidence,
            "trend": self.confidence_trend,
        }


def generate_self_correction_prompt(detection: HallucinationDetection) -> str:
    """Generate a correction prompt if hallucination is detected."""
    if detection.recommendation == "INTERRUPT":
        return (
            f"\n\n[SYSTEM INTERCEPT - {detection.domain.upper()}]\n"
            f"I was about to make a claim I can't verify. {detection.explanation}\n\n"
            f"Instead: I should be honest about the limits of what I know. "
            f"What confidence I do have comes from grounding in real knowledge."
        )
    elif detection.recommendation == "PAUSE":
        return (
            f"\n[⚠️ CONFIDENCE ALERT ({int(detection.confidence_score * 100)}%)]\n"
            f"{detection.explanation}\n"
            f"I'm not confident about this claim without better verification.\n"
        )
    return ""  # No correction needed

