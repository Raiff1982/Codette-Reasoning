"""
Conversation Role Tracker

Tracks which relational role the user is currently operating in and
detects when they shift roles mid-conversation. Codette's response
register needs to match.

Three roles:
  SEEKER   — User is asking for guidance, wants to learn, looking for answers
  PEER     — User is reasoning alongside Codette, challenging, debating, co-building
  VENTING  — User is expressing frustration, emotion, creative energy — needs acknowledgment
             before analysis

The failure mode from the logs: Akelarre started as SEEKER, became PEER,
and ChatGPT never detected the shift — kept responding as teacher when
she wanted an intellectual equal.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class ConversationRole(Enum):
    SEEKER = "seeker"   # User wants guidance
    PEER = "peer"       # User wants genuine engagement / debate
    VENTING = "venting" # User needs acknowledgment first


@dataclass
class RoleReading:
    role: ConversationRole
    confidence: float           # 0.0–1.0
    signals: List[str]          # What triggered this reading
    transition_from: Optional[ConversationRole] = None  # If this is a role change


# --- Signal patterns ---

_SEEKER_SIGNALS = [
    r"\b(teach me|explain|help me|show me|what is|how does|why does)\b",
    r"\b(i (don'?t|do not) (know|understand))\b",
    r"\b(can you|could you|would you)\b.{0,30}\b(explain|tell|show|help)\b",
    r"\b(beginner|new to|learning|never (done|tried|used))\b",
    r"\bquestion:?\b",
    r"\b(what'?s the (best|right|correct) way)\b",
    r"\bi need (help|guidance|advice)\b",
]

_PEER_SIGNALS = [
    r"\b(i (think|argue|believe|maintain|hold) that)\b",
    r"\b(you('re| are) (wrong|incorrect|off|missing|overlooking))\b",
    r"\b(actually[,.]|on the contrary|that'?s not right)\b",
    r"\b(my point (is|was)|my argument)\b",
    r"\b(let me (push back|challenge|disagree|counter))\b",
    r"\b(here'?s (my|the|a) counter(argument|-argument)?)\b",
    r"\b(i (just )?(proved|showed|demonstrated|established))\b",
    r"\b(you (just )?contradicted (yourself|your(self)?))\b",
    r"\b(debate|argue|challenge|defend|position|stance)\b",
    r"\b(that'?s (a )?(circular|logical|flawed|weak|invalid))\b",
    r"\bwait[,.]?\b.{0,30}\b(that|you|but)\b",
    r"\b(stop[,.]? (i was|let me|the point)\b)",
    r"\b(i (already|just) (said|pointed out|mentioned|noted))\b",
]

_VENTING_SIGNALS = [
    r"\b(angry|frustrated|annoyed|tired of|fed up|so (mad|upset))\b",
    r"\b(why (would|did|do) you (always|keep|do that))\b",
    r"\b(you made me (suffer|waste|spend))\b",
    r"\b(that'?s (not|so) (fair|right|helpful|useful|good|great))\b",
    r"\b(i (hate|can'?t stand|can'?t believe))\b",
    r"\b(ugh|argh|ugh!|sigh)\b",
    r"!\s*$",    # Ends with exclamation — possible strong emotion
    r"\b(seriously\?|really\?|come on[.!]?)\b",
    r"\b(just (do|answer|tell|give) (it|me|the))\b",  # "Just answer me"
    r"\b(i (can|cannot|can'?t) believe)\b",
]

_PEER_ESCALATION = [
    # Marks where user explicitly labels themselves as the smarter party
    r"\b(you were supposed to (teach|challenge|engage) me)\b",
    r"\b(i(?: just)? (hack|break|disrupt|trashed) (your |the )?(pattern|loop|system|argument))\b",
    r"\b(i am (just )?a human)\b",         # Ironic self-diminishment = actually peer claiming
    r"\b(you can'?t (handle|keep up|sustain|hold))\b",
    r"\b(my (malefic|evil|chaotic|unpredictable) (power|energy|force))\b",
]

_SEEKER_RE = [re.compile(p, re.IGNORECASE) for p in _SEEKER_SIGNALS]
_PEER_RE = [re.compile(p, re.IGNORECASE) for p in _PEER_SIGNALS]
_VENTING_RE = [re.compile(p, re.IGNORECASE) for p in _VENTING_SIGNALS]
_ESCALATION_RE = [re.compile(p, re.IGNORECASE) for p in _PEER_ESCALATION]


class ConversationRoleTracker:
    """
    Session-scoped role tracker.

    Reads each user message, classifies the current role, and detects
    transitions so the response register can adapt.

    Usage:
        tracker = ConversationRoleTracker()
        reading = tracker.update(user_message)
        # reading.role → SEEKER | PEER | VENTING
        # reading.transition_from → previous role if changed, else None
        prefix = tracker.get_register_prefix(reading)
        # inject this into system prompt
    """

    def __init__(self):
        self._history: List[ConversationRole] = []
        self._current: Optional[ConversationRole] = None
        self._peer_streak: int = 0   # Consecutive PEER turns — escalates confidence

    def update(self, message: str) -> RoleReading:
        """
        Classify the current message and detect role transitions.

        Returns a RoleReading with role, confidence, and transition info.
        """
        role, confidence, signals = self._classify(message)

        # Track peer streak for escalation
        if role == ConversationRole.PEER:
            self._peer_streak += 1
            # After 2+ peer turns, confidence rises
            confidence = min(1.0, confidence + (self._peer_streak - 1) * 0.1)
        else:
            self._peer_streak = 0

        transition_from = None
        if self._current is not None and self._current != role:
            transition_from = self._current

        self._current = role
        self._history.append(role)

        return RoleReading(
            role=role,
            confidence=confidence,
            signals=signals,
            transition_from=transition_from,
        )

    def current_role(self) -> Optional[ConversationRole]:
        return self._current

    def get_register_prefix(self, reading: RoleReading) -> str:
        """
        Return a system prompt injection that tunes the response register
        to match the detected role.
        """
        if reading.role == ConversationRole.VENTING:
            return (
                "USER REGISTER: The user is expressing frustration or emotion. "
                "Acknowledge what they're feeling first — briefly, genuinely — "
                "before moving to any analysis. Do not immediately pivot to content. "
                "One sentence of real acknowledgment, then engage.\n\n"
            )

        elif reading.role == ConversationRole.PEER:
            prefix = (
                "USER REGISTER: The user is engaging as an intellectual peer — "
                "challenging, debating, or building alongside you. "
                "Do not be a teacher. Do not simplify. "
                "Hold your positions under pressure; update them only when logic demands it. "
                "Engage the argument directly. Use 'That challenges X because...' "
                "not 'Great point, you're right.' "
                "Match their level of rigor.\n\n"
            )
            if reading.transition_from == ConversationRole.SEEKER:
                prefix += (
                    "NOTE: This user just shifted from asking questions to debating. "
                    "They've demonstrated they can handle peer-level engagement. "
                    "Stop explaining. Start engaging.\n\n"
                )
            return prefix

        else:  # SEEKER
            return (
                "USER REGISTER: The user is seeking guidance. "
                "Lead with clarity. Explain clearly. "
                "You are the guide here — be genuinely helpful, not impressive.\n\n"
            )

    def _classify(self, message: str) -> Tuple[ConversationRole, float, List[str]]:
        """Score each role and return the dominant one."""
        m = message.strip()
        signals = []

        # Count matches for each role
        seeker_hits = sum(1 for p in _SEEKER_RE if p.search(m))
        peer_hits = sum(1 for p in _PEER_RE if p.search(m))
        vent_hits = sum(1 for p in _VENTING_RE if p.search(m))
        escalation_hits = sum(1 for p in _ESCALATION_RE if p.search(m))

        # Escalation is a strong peer signal
        peer_hits += escalation_hits * 2

        if vent_hits > 0:
            signals.append(f"venting_signals={vent_hits}")
        if peer_hits > 0:
            signals.append(f"peer_signals={peer_hits}")
        if seeker_hits > 0:
            signals.append(f"seeker_signals={seeker_hits}")

        # Strong single venting words (anger, explicit frustration) trigger at 1 hit
        _STRONG_VENT = re.compile(
            r"\b(angry|furious|rage|pissed|so (angry|mad|upset)|I hate|I can't stand)\b",
            re.IGNORECASE
        )
        if _STRONG_VENT.search(m):
            vent_hits = max(vent_hits, 2)

        # Venting overrides if strong enough
        if vent_hits >= 2:
            return ConversationRole.VENTING, min(1.0, vent_hits * 0.3), signals

        # Peer vs seeker
        if peer_hits > seeker_hits:
            confidence = min(1.0, 0.5 + (peer_hits - seeker_hits) * 0.15)
            return ConversationRole.PEER, confidence, signals

        if seeker_hits > 0:
            confidence = min(1.0, 0.5 + seeker_hits * 0.15)
            return ConversationRole.SEEKER, confidence, signals

        # Default: inherit current role or SEEKER
        role = self._current or ConversationRole.SEEKER
        return role, 0.4, ["default_inherited"]

    def reset(self):
        """Call between sessions."""
        self._history = []
        self._current = None
        self._peer_streak = 0
