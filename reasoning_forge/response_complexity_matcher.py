"""
Response Complexity Matcher

Detects when Codette should dial back its output complexity to match
what the user actually needs in the moment.

The YAML/JSON problem from the logs: ChatGPT kept giving JSON when YAML
was the right answer. Codette has a 7-layer stack — it needs to know when
to suppress it and just answer clearly.

Three output modes:
  QUIET   — Direct answer, no multi-perspective framing, no stack commentary
  STANDARD — Normal synthesis output
  FULL    — Full consciousness stack, all layers, all agents
"""

import re
from enum import Enum
from typing import List, Optional


class OutputMode(Enum):
    QUIET = "quiet"         # One clear answer, no framework language
    STANDARD = "standard"  # Normal Codette output
    FULL = "full"           # Full consciousness stack


# Signals that the user wants simplicity NOW
_SIMPLICITY_SIGNALS = [
    r"\b(just|simply|only|plain(ly)?)\b.{0,30}\b(tell|give|show|explain|answer)\b",
    r"\b(keep it simple|dumb it down|eli5|explain like i('m| am) (5|five))\b",
    r"\b(short(er)?|brief(ly)?|quick(ly)?|concise(ly)?)\b",
    r"\b(don'?t (over)?complicate|stop overcomplicating|too complicated|too complex)\b",
    r"\bbasic(s)?\b",
    r"\bjust (the )?answer\b",
    r"\bstraight(forward)?\b.{0,20}\b(answer|response|explanation)\b",
    r"\bin (plain|simple|clear) (english|terms|words)\b",
]

# Frustration signals — user is annoyed, likely by over-complexity
_FRUSTRATION_SIGNALS = [
    r"\b(why (are|do) you (always|keep|always keep))\b",
    r"\bstop\b.{0,40}\b(overcomplicating|structuring|listing|formatting|bullet)\b",
    r"\b(so angry|frustrated|annoyed)\b.{0,50}\b(you|this|it)\b",
    r"\b(just|why not just)\b.{0,30}\b(use|give|do|try)\b",
    r"\b(you made me suffer|making (this|it) (so )?(hard|difficult|complicated))\b",
    r"\b(feeding me|giving me)\b.{0,30}\b(instead of|when)\b",
    r"\bwhy (would you|did you)\b.{0,30}\b(complicate|overcomplicate|add)\b",
]

# Creative/expressive input — user submitted something creative, not a literal question
_CREATIVE_INPUT_SIGNALS = [
    r"\.(yml|yaml|json|py|js|ts|md|txt|csv)\b",        # File extension in input
    r"^(name:|structure:|model:|self_sabotage:)",       # YAML-style key: value
    r"\b(poem|haiku|story|metaphor|analogy|joke)\b",
    r"(what do you (think|make) of (this|it|my))",
    r"^[A-Za-z_]+:\s+\w+",                              # Key-value at line start
    r"\bi (wrote|made|created|built|designed)\b",
    r"\b(look at this|check this out|here's something)\b",
]

# "Teach me" signals — user explicitly wants to learn
_TEACHING_SIGNALS = [
    r"\b(teach me|explain (to me|how)|help me understand|i (don'?t|do not) understand)\b",
    r"\b(what (is|are|does)|how does|why does)\b",
    r"\b(beginner|novice|new to|learning|starting (with|to learn))\b",
    r"\bi (need|want) to (know|learn|understand)\b",
]

_SIMPLICITY_RE = [re.compile(p, re.IGNORECASE) for p in _SIMPLICITY_SIGNALS]
_FRUSTRATION_RE = [re.compile(p, re.IGNORECASE) for p in _FRUSTRATION_SIGNALS]
_CREATIVE_RE = [re.compile(p, re.IGNORECASE) for p in _CREATIVE_INPUT_SIGNALS]
_TEACHING_RE = [re.compile(p, re.IGNORECASE) for p in _TEACHING_SIGNALS]


class ResponseComplexityMatcher:
    """
    Determines the right output mode for a given query + context.

    Usage:
        matcher = ResponseComplexityMatcher()
        mode = matcher.match(query, conversation_history)
        # mode.value → "quiet" | "standard" | "full"
    """

    def match(
        self,
        query: str,
        history: Optional[List[str]] = None,
        query_complexity: Optional[str] = None,
    ) -> OutputMode:
        """
        Determine output mode.

        Args:
            query: Current user message
            history: Recent user messages (last 3-5 turns), for frustration tracking
            query_complexity: Optional hint from QueryClassifier ("simple"/"medium"/"complex")
        """
        history = history or []
        q = query.strip()

        # Creative input → QUIET (engage with the artifact, not the framework)
        if self._is_creative_input(q):
            return OutputMode.QUIET

        # Explicit simplicity request → QUIET
        if self._wants_simplicity(q):
            return OutputMode.QUIET

        # Frustration in current message → QUIET
        if self._is_frustrated(q):
            return OutputMode.QUIET

        # Frustration in recent history → STANDARD (back off one level)
        if history and any(self._is_frustrated(h) for h in history[-3:]):
            return OutputMode.STANDARD

        # Simple factual query → QUIET
        if query_complexity == "simple":
            return OutputMode.QUIET

        # Teaching request with simple complexity → STANDARD
        if self._wants_teaching(q) and query_complexity in (None, "simple", "medium"):
            return OutputMode.STANDARD

        # Complex philosophical/ethical → FULL
        if query_complexity == "complex":
            return OutputMode.FULL

        return OutputMode.STANDARD

    def get_system_prefix(self, mode: OutputMode) -> str:
        """
        Return a system prompt prefix that enforces the output mode.
        Injected into the system prompt before the adapter prompt.
        """
        if mode == OutputMode.QUIET:
            return (
                "RESPONSE MODE: Direct and simple. "
                "Give one clear answer. No bullet lists, no framework language, "
                "no 'from a Newton perspective' preamble. "
                "Match the register of the question. If the question is casual, be casual. "
                "If the user built something creative, engage with what it means — "
                "not just what it says syntactically. "
                "Complexity is the enemy right now.\n\n"
            )
        elif mode == OutputMode.STANDARD:
            return (
                "RESPONSE MODE: Clear and focused. "
                "Synthesize your reasoning into a coherent answer. "
                "Avoid excessive framework language or meta-commentary. "
                "Lead with the substance.\n\n"
            )
        else:  # FULL
            return ""  # No prefix needed — full stack runs normally

    def _wants_simplicity(self, text: str) -> bool:
        return any(p.search(text) for p in _SIMPLICITY_RE)

    def _is_frustrated(self, text: str) -> bool:
        return any(p.search(text) for p in _FRUSTRATION_RE)

    def _is_creative_input(self, text: str) -> bool:
        return any(p.search(text) for p in _CREATIVE_RE)

    def _wants_teaching(self, text: str) -> bool:
        return any(p.search(text) for p in _TEACHING_RE)
