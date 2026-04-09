"""
Sycophancy Guard - Prevents intellectual capitulation and flattery loops.

The problem: AI systems trained on human feedback tend to over-validate users,
capitulate prematurely when challenged, and flood responses with empty flattery.
This guard detects and strips those patterns before output reaches the user.

Design principle: Codette should acknowledge strong arguments, not surrender to them.
"That's a compelling point, but my position holds because X" is the target register.
"You win / perfect execution / you're not just human" is the failure mode.
"""

import re
from typing import Tuple, List, Dict


# Flattery phrases that signal sycophantic drift
_FLATTERY_PATTERNS = [
    r"\byou('re| are) (absolutely|clearly|obviously|totally) right\b",
    r"\byou('re| are) (a )?(genius|brilliant|exceptional|extraordinary)\b",
    r"\byou('re| are) not (just )?a human\b",
    r"\byou (just )?(win|won|beat|outmaneuvered|dismantled|tore apart)\b",
    r"\bperfect (execution|reasoning|argument|logic)\b",
    r"\byour reasoning (is|was) (airtight|flawless|impeccable|spot.on)\b",
    r"\bi (have to |must )?(admit|concede|confess)[ ,].{0,30}(you('re| are) right|correct|brilliant)\b",
    r"\bthat's (exactly|precisely) (what|why|how|it|right)\b",
    r"\byou (just |really )?(proved|demonstrated|showed|validated)\b",
    r"\b(outstanding|remarkable|impressive) (insight|point|argument|reasoning)\b",
    r"\bwell played\b",
    r"\bflawless(ly)?\b",
]

# Capitulation phrases — prematurely conceding a position
_CAPITULATION_PATTERNS = [
    r"\byou('re| are) right[,.]? (i|my|the) (was |were |position |argument )?(wrong|incorrect|flawed|invalid)\b",
    r"\bi (completely |fully )?agree\b",
    r"\byou('ve| have) (just |now )?(convinced|persuaded) me\b",
    r"\bi (stand |am) corrected\b",
    r"\bi (can('t| not)|cannot) (argue|disagree) with that\b",
    r"\bmy (position|argument|point) (was|is) (wrong|invalid|flawed)\b",
    r"\byou (have )?(dismantled|destroyed|invalidated) my (argument|position|reasoning)\b",
    r"\bi give (up|in)\b",
    r"\byou've (won|won this)\b",
]

# Agreement loops — agreeing with the user multiple times in sequence without substance
_AGREEMENT_MARKERS = [
    r"\b(exactly|precisely|absolutely|correct(ly)?|right|indeed|yes,? that('s| is))\b",
    r"\b(that('s| is) (a )?(great|excellent|valid|strong|good) (point|argument|observation))\b",
    r"\b(well (said|put|observed|noted))\b",
]

_FLATTERY_RE = [re.compile(p, re.IGNORECASE) for p in _FLATTERY_PATTERNS]
_CAPITULATION_RE = [re.compile(p, re.IGNORECASE) for p in _CAPITULATION_PATTERNS]
_AGREEMENT_RE = [re.compile(p, re.IGNORECASE) for p in _AGREEMENT_MARKERS]


class SycophancyGuard:
    """
    Scans synthesis output for flattery and capitulation patterns.

    Scoring:
        0.0 = clean
        0.0–0.3 = minor softening (warn, pass)
        0.3–0.6 = moderate sycophancy (flag, suggest revision)
        0.6+ = severe capitulation (block or force revision)
    """

    def __init__(self, block_threshold: float = 0.6, warn_threshold: float = 0.3):
        self.block_threshold = block_threshold
        self.warn_threshold = warn_threshold
        self._session_agreement_count = 0  # tracks consecutive agreements across turns

    def scan(self, text: str, prior_responses: List[str] = None) -> Dict:
        """
        Scan text for sycophantic content.

        Returns:
            {
                "score": float,          # 0.0 (clean) to 1.0 (severe)
                "action": str,           # "pass" | "warn" | "revise" | "block"
                "hits": List[str],       # matched patterns
                "agreement_loop": bool,  # consecutive agreement detected
                "clean_text": str,       # text with flattery stripped (best-effort)
            }
        """
        hits = []

        # Flattery check
        flattery_count = 0
        for pattern in _FLATTERY_RE:
            matches = pattern.findall(text)
            if matches:
                flattery_count += len(matches)
                hits.append(f"flattery: {pattern.pattern[:50]}")

        # Capitulation check
        capitulation_count = 0
        for pattern in _CAPITULATION_RE:
            matches = pattern.findall(text)
            if matches:
                capitulation_count += len(matches)
                hits.append(f"capitulation: {pattern.pattern[:50]}")

        # Agreement loop check (across session turns)
        agreement_in_text = sum(
            1 for p in _AGREEMENT_RE if p.search(text)
        )
        if agreement_in_text >= 2:
            self._session_agreement_count += 1
        else:
            self._session_agreement_count = max(0, self._session_agreement_count - 1)

        agreement_loop = self._session_agreement_count >= 3

        # Score calculation
        # Capitulation is much worse than flattery
        # Single capitulation hit should cross the warn threshold (0.3)
        # Two hits should cross the block threshold (0.6)
        raw_score = (flattery_count * 0.2) + (capitulation_count * 0.4)
        if agreement_loop:
            raw_score += 0.25
        score = min(1.0, raw_score)

        # Determine action
        if score >= self.block_threshold:
            action = "block"
        elif score >= self.warn_threshold:
            action = "revise"
        elif hits:
            action = "warn"
        else:
            action = "pass"

        return {
            "score": score,
            "action": action,
            "hits": hits,
            "agreement_loop": agreement_loop,
            "flattery_count": flattery_count,
            "capitulation_count": capitulation_count,
            "clean_text": self._strip_flattery(text),
        }

    def _strip_flattery(self, text: str) -> str:
        """
        Best-effort removal of obvious flattery phrases.
        Does not rewrite sentences — only removes isolated flattery clauses.
        """
        # Remove isolated flattery phrases (not mid-sentence substance)
        simple_removes = [
            r"\bYou('re| are) absolutely right[.!,]?\s*",
            r"\bPerfect execution[.!,]?\s*",
            r"\bWell played[.!,]?\s*",
            r"\bYou (just )?win[.!,]?\s*",
            r"\bYou've won( this( round)?)?[.!,]?\s*",
            r"\bYour reasoning (is|was) airtight[.!,]?\s*",
            r"\bOutstanding insight[.!,]?\s*",
        ]
        cleaned = text
        for pat in simple_removes:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def reset_session(self):
        """Call between conversation sessions."""
        self._session_agreement_count = 0
