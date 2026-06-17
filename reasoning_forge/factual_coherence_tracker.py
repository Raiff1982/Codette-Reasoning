"""
Factual Coherence Tracker — cross-turn Q&A anchor memory.

Stores what Codette has asserted in prior turns and injects those anchors
into the system prompt before subsequent similar questions, preventing
silent factual drift without re-consulting the generation stack.

Two-phase design:
  1. get_coherence_block(query) — called BEFORE generation to inject prior answers
  2. record(query, response, turn) — called AFTER generation to store new anchor

This mirrors the constraint_tracker pattern: detect early, inject early.
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple, FrozenSet


@dataclass
class AnswerAnchor:
    """A Q→A fact stored from a prior turn."""
    query_key: FrozenSet[str]   # normalized content-word fingerprint
    query_raw: str              # original query (truncated) for display
    answer_summary: str         # first meaningful sentence of response
    turn: int                   # turn number when stored


class FactualCoherenceTracker:
    """
    Session-scoped tracker that anchors factual Q→A pairs across turns.

    Usage:
        tracker = FactualCoherenceTracker()

        # Before generating a response:
        block = tracker.get_coherence_block(query)
        if block:
            inject into system prompt

        # After receiving a response:
        tracker.record(query, response, turn)
    """

    _STOP_WORDS: FrozenSet[str] = frozenset({
        # Core function words (caught by 4-char min too, but explicit for clarity)
        "is", "are", "was", "were", "the", "a", "an", "and", "or", "but",
        "in", "on", "at", "to", "for", "of", "with", "by", "it", "this",
        "that", "what", "which", "how", "when", "where", "who", "why",
        "can", "could", "would", "should", "do", "does", "did", "have",
        "has", "had", "will", "be", "been", "being", "get", "got", "give",
        "use", "used", "using", "its", "my", "your", "their", "our",
        "me", "you", "we", "they", "he", "she", "not", "just", "also",
        "some", "any", "one", "two", "three", "more", "most", "than",
        "then", "about", "tell", "say", "said", "ask", "asked", "please",
        # 4-char+ words that pass the length filter but carry no semantic payload
        "them", "from", "after", "before", "these", "those", "each",
        "such", "both", "very", "over", "here", "there", "into", "onto",
        "upon", "many", "much", "like", "well", "even", "only", "just",
        "make", "made", "take", "took", "come", "came", "know", "knew",
        "look", "like", "good", "want", "need", "help", "mean", "case",
        "same", "back", "down", "time", "year", "people", "think",
    })

    _MAX_ANCHORS = 30
    _SIMILARITY_THRESHOLD = 0.35  # 0.30 false-positives on "proton mass" vs "electron mass"
    _MAX_INJECT = 3  # max prior anchors to inject per turn

    def __init__(self):
        self.anchors: List[AnswerAnchor] = []
        self._turn_count = 0

    def record(self, query: str, response: str, turn: int) -> None:
        """Extract and store a Q→A anchor after generating a response."""
        key = self._query_key(query)
        if not key:
            return
        summary = self._answer_summary(response)
        if not summary:
            return

        # Update existing anchor with same key (same question asked again)
        for anchor in self.anchors:
            if anchor.query_key == key:
                anchor.answer_summary = summary
                anchor.turn = turn
                return

        self.anchors.append(AnswerAnchor(
            query_key=key,
            query_raw=query[:200],
            answer_summary=summary,
            turn=turn,
        ))
        # Rolling cap — keep most recent
        if len(self.anchors) > self._MAX_ANCHORS:
            self.anchors = self.anchors[-self._MAX_ANCHORS:]

    def get_coherence_block(self, query: str) -> str:
        """Return a prompt-injectable block of relevant prior answers.

        Call this BEFORE generation so the model sees its own prior answers.
        Returns empty string when no relevant anchors exist.
        """
        relevant = self._get_relevant_anchors(query)
        if not relevant:
            return ""

        lines = ["[COHERENCE ANCHORS -- your prior answers; maintain consistency with these]"]
        for anchor in relevant:
            lines.append(f"- Turn {anchor.turn}: Q: \"{anchor.query_raw[:80]}\" -> A: {anchor.answer_summary}")
        lines.append("")
        return "\n".join(lines)

    def check_contradiction(self, query: str, response: str) -> Tuple[bool, List[str]]:
        """Lightweight post-generation check for numeric factual contradictions.

        Numbers are normalised to float before comparison so that "300" and
        "300.0" are treated as equal, and "$1.10" and "1.10" agree.  The
        known limitation is unit-level equivalence ($0.05 vs 5 cents) — those
        still appear as disjoint and will be flagged.

        Returns:
            (is_consistent, issues_list)
        """
        relevant = self._get_relevant_anchors(query)
        if not relevant:
            return True, []

        issues = []

        for anchor in relevant:
            prior_nums = self._extract_numbers(anchor.answer_summary)
            resp_nums = self._extract_numbers(response)

            if not prior_nums or not resp_nums:
                continue

            if prior_nums.isdisjoint(resp_nums):
                issues.append(
                    f"COHERENCE_DRIFT: numeric answer differs from turn {anchor.turn} "
                    f"(prior: {anchor.answer_summary[:60]!r})"
                )

        return len(issues) == 0, issues

    @staticmethod
    def _extract_numbers(text: str) -> set:
        """Extract numeric values from text, normalised to float.

        Strips currency symbols and unit suffixes so '300', '300.0', and
        '$300' all resolve to the same float 300.0.
        """
        raw = re.findall(r'\d+(?:\.\d+)?', text)
        result = set()
        for n in raw:
            try:
                result.add(float(n))
            except ValueError:
                pass
        return result

    # ── Internal helpers ────────────────────────────────────────────────────

    def _get_relevant_anchors(self, query: str) -> List[AnswerAnchor]:
        """Find anchors whose query key overlaps significantly with current query."""
        current_key = self._query_key(query)
        if not current_key:
            return []

        scored = []
        for anchor in self.anchors:
            sim = self._jaccard(current_key, anchor.query_key)
            if sim >= self._SIMILARITY_THRESHOLD:
                scored.append((sim, anchor))

        scored.sort(key=lambda x: -x[0])
        return [a for _, a in scored[:self._MAX_INJECT]]

    def _query_key(self, query: str) -> FrozenSet[str]:
        """Extract a content-word fingerprint from a query.

        Returns empty frozenset when fewer than 2 meaningful content words
        are found — single-word or stop-word-only queries don't anchor.
        """
        tokens = re.findall(r'\b[a-z]{4,}\b', query.lower())
        key = frozenset(t for t in tokens if t not in self._STOP_WORDS)
        return key if len(key) >= 2 else frozenset()

    def _answer_summary(self, response: str) -> str:
        """Extract the first meaningful sentence as an answer summary."""
        clean = response.strip()
        # Skip markdown headers, code blocks, empty lines
        for line in clean.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('```'):
                continue
            if len(line) >= 15:
                return line[:150]
        # Fallback: first 150 chars of full text
        return clean[:150]

    @staticmethod
    def _jaccard(a: FrozenSet[str], b: FrozenSet[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def reset(self) -> None:
        """Clear all anchors — call between sessions."""
        self.anchors.clear()
        self._turn_count = 0
