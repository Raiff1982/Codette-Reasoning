"""
Hallucination Guard: Real-time detection and prevention during generation.

Runs on the response stream as it's being generated. Detects hallucination signals,
scores confidence on claims, and can interrupt generation before false facts solidify.

Key signals:
1. Invented fact patterns (dates without grounding, fake plugin names, etc.)
2. Contradiction with grounding rules
3. Confidence markers that contradict the actual knowledge
4. Novel claims without hedging
5. Genre/artist misclassifications

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
    "indie rock", "indie pop", "indie folk",  # compound indie genres
    "metal", "punk", "blues", "soul", "funk", "reggae", "latin",
    "classical", "orchestral", "chamber", "experimental", "avant-garde"
}

ARTIST_KEY_SIGNALS = {
    # Artists known to be alive (as of March 2026)
    "laney wilson", "megan moroney", "tyler childers", "jason isbell",
    "chris stapleton", "sturgill simpson", "colter wall"
}


@dataclass
class HallucinationDetection:
    """Result of hallucination scan on a chunk."""
    is_hallucination: bool
    confidence_score: float  # [0, 1] — 0 = hallucination, 1 = grounded
    signals: List[str]  # What triggered detection
    recommendation: str  # "CONTINUE", "PAUSE", "INTERRUPT"
    explanation: str  # Human-readable reason


class HallucinationGuard:
    """Real-time hallucination detection during generation."""

    def __init__(self):
        self.buffer = ""  # Accumulate chunks for analysis
        self.chunks_analyzed = 0
        self.hallucinations_caught = 0
        self.confidence_trend = []  # Track confidence over time

    def scan_chunk(self, chunk: str) -> HallucinationDetection:
        """Scan an incoming chunk for hallucination signals."""
        self.buffer += chunk
        self.chunks_analyzed += 1

        signals = []
        confidence_score = 1.0

        # ── SIGNAL 1: Invented Plugin Names ──
        # Look for claims about "Plugin X" that isn't real
        plugin_pattern = r'\b([A-Z][a-zA-Z0-9\s\-]+)\s+(plugin|VST|effect|processor)\b'
        for match in re.finditer(plugin_pattern, self.buffer):
            plugin_name = match.group(1).lower()
            if not any(real in plugin_name for real in REAL_PLUGINS):
                signals.append(f"Unknown plugin: {match.group(1)}")
                confidence_score *= 0.6  # Major red flag

        # ── SIGNAL 2: Invented Dates/Albums ──
        # Pattern: "[Artist] released [Album] in [Year]" without grounding
        album_pattern = r'(released|dropped|released an album|released the album)\s+["\']?(\w+[\w\s]*?)["\']?\s+(in|on)\s+(\d{4})'
        for match in re.finditer(album_pattern, self.buffer, re.IGNORECASE):
            signals.append(f"Unverified album claim: {match.group(2)} ({match.group(4)})")
            confidence_score *= 0.5  # High hallucination likelihood

        # ── SIGNAL 3: Artist Death Claims ──
        # Pattern: "passed away", "died", "in memoriam" without verification
        death_pattern = r'(passed away|died|was killed|deceased|in memoriam).*?(\d{4})'
        if re.search(death_pattern, self.buffer, re.IGNORECASE):
            for artist in ARTIST_KEY_SIGNALS:
                if artist in self.buffer.lower():
                    signals.append(f"Unverified death claim for {artist}")
                    confidence_score *= 0.2  # CRITICAL — likely hallucination

        # ── SIGNAL 4: Genre Misclassification ──
        # Check for genre claims that contradict known facts
        # E.g., "Laney Wilson is indie-rock" (she's country)
        genre_context = [
            ("laney wilson", ["country", "country-pop"], ["indie-rock", "alternative"]),
            ("megan moroney", ["country", "country-pop"], ["indie-rock", "rock"]),
            ("tyler childers", ["country", "country-folk"], ["indie-rock"]),
        ]
        for artist, true_genres, false_genres in genre_context:
            if artist in self.buffer.lower():
                for false_genre in false_genres:
                    if false_genre in self.buffer.lower():
                        signals.append(f"Genre mismatch: {artist} is not {false_genre}")
                        confidence_score *= 0.3

        # ── SIGNAL 5: Unhedged Novel Claims ──
        # High-confidence claim ("definitely", "clearly") about an artist without source
        high_confidence_pattern = r'\b(definitely|clearly|definitely\b|unambiguously|certainly)\s+.*?(?:artist|song|album|band)'
        if re.search(high_confidence_pattern, self.buffer, re.IGNORECASE):
            if any(artist in self.buffer.lower() for artist in ARTIST_KEY_SIGNALS):
                signals.append("High-confidence claim about artist without verification")
                confidence_score *= 0.4

        # ── SIGNAL 6: Specific Dates Without Grounding ──
        # Pattern: very specific date (e.g., "October 2017") for artist fact
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}[,\s]+\d{4}'
        if re.search(date_pattern, self.buffer):
            if any(artist in self.buffer.lower() for artist in ARTIST_KEY_SIGNALS):
                signals.append("Specific date claim without verification source")
                confidence_score *= 0.5

        # Compute recommendation
        self.confidence_trend.append(confidence_score)
        recommendation = self._recommend_action(confidence_score, signals)

        if recommendation in ("PAUSE", "INTERRUPT"):
            self.hallucinations_caught += 1

        return HallucinationDetection(
            is_hallucination=(confidence_score < 0.5),
            confidence_score=confidence_score,
            signals=signals,
            recommendation=recommendation,
            explanation=self._explain(confidence_score, signals)
        )

    def _recommend_action(self, score: float, signals: List[str]) -> str:
        """Decide whether to continue, pause, or interrupt generation."""
        if score < 0.2:
            return "INTERRUPT"  # Critical hallucination detected
        elif score < 0.5:
            return "PAUSE"  # Warn and review
        elif score < 0.7 and signals:
            return "REVIEW"  # Minor issues, continue but flag
        else:
            return "CONTINUE"

    def _explain(self, score: float, signals: List[str]) -> str:
        """Human-readable explanation of confidence."""
        if not signals:
            return "No hallucination signals detected. Grounded response."
        return f"Detected {len(signals)} potential issues: " + "; ".join(signals[:2])

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
            f"\n\n[SYSTEM INTERCEPT]\n"
            f"I was about to say something unverified. {detection.explanation}\n\n"
            f"Instead: I don't have reliable information about this. I'd recommend checking "
            f"Wikipedia, Spotify, or official sources for accurate details. "
            f"What I CAN help with: production analysis, genre characteristics, or creating "
            f"music inspired by similar vibes."
        )
    elif detection.recommendation == "PAUSE":
        return (
            f"\n[⚠️ CONFIDENCE ALERT: {int(detection.confidence_score * 100)}%]\n"
            f"{detection.explanation}\n"
            f"I'm not confident about this claim without verification.\n"
        )
    return ""  # No correction needed
