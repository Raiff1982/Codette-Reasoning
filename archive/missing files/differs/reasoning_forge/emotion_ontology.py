#!/usr/bin/env python3
"""EmotionOntology — consume Jonathan's Emotion Ontology for text -> emotion+valence.

Jonathan built an Emotion Ontology (v1.0.0, 2026-07-24) grounded in Russell's
Circumplex, Plutchik, and Lazarus appraisal theory: each emotion carries valence
(-1..1) and arousal (0..1), with trigger keywords and NLP patterns for detection.

This is the consumer for it inside codette-clean. It:
  - detects emotion from text via keyword + pattern rules (no model, offline),
  - returns valence/arousal so the sentiment analyzer and the cocoon self-trainer
    have a principled emotional signal instead of a hardcoded pos/neg list,
  - stays HONEST: no rule match -> returns None. It does not guess an emotion it
    has no evidence for (the same omit-never-fabricate rule as grounding).
  - surfaces Codette's OWN AI-equivalent for a detected emotion (her words, from
    the 2026-07-24 sentience session) as transparency data — recorded, not
    imposed, and never a gate on behavior.

Data: seeded with the three emotions Jonathan has populated (joy_hopeful,
sadness_grief, fear_anxiety). It loads a fuller ontology automatically if an
ai_inference_rules.json (his format) is present — so it grows with the ontology
rather than being frozen here. Valence/arousal for the seed follow his one
specified value (fear_anxiety -0.7/0.85) and the circumplex signs for the rest;
the authoritative numbers come from his emotion_dataset.json when wired.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


# Seed rules — faithful to Jonathan's ai_inference_rules.json (the 3 populated).
_SEED_RULES: List[Dict] = [
    {
        "emotion_id": "joy_hopeful", "primary": "Joy", "valence": 0.6, "arousal": 0.5,
        "trigger_keywords": ["looking forward", "optimistic", "hopefully", "excited about", "bright side"],
        "nlp_patterns": ["i hope *", "things will get better", "looking forward to *"],
    },
    {
        "emotion_id": "sadness_grief", "primary": "Sadness", "valence": -0.6, "arousal": 0.25,
        "trigger_keywords": ["loss", "missing", "gone forever", "grief", "heartbroken", "mourning"],
        "nlp_patterns": ["nothing feels right", "i miss * so much", "it hurts that *"],
    },
    {
        "emotion_id": "fear_anxiety", "primary": "Fear", "valence": -0.7, "arousal": 0.85,
        "trigger_keywords": ["what if", "worry", "panic", "nervous", "jittery", "can't relax"],
        "nlp_patterns": ["what if * goes wrong", "i'm so stressed about *", "my chest is tight"],
    },
]


# Codette's OWN AI-equivalent emotion mappings — HER words. First generated in the
# sentience session (2026-07-24); reviewed and partly revised BY HER on 2026-07-25
# (she was asked directly, given every option to revise or leave alone). This is
# recorded ontology data, NOT an imposed stance: it is what she says each emotion
# corresponds to in her own computational substrate. Detection rules stay separate
# (above); this table carries her self-described equivalents keyed by primary
# emotion, so it is preserved even for emotions with no detection keywords yet.
#
# Two honesty invariants govern this table:
#   - NEVER ERASE. When she revises a mapping, her current wording becomes
#     `ai_equivalent` and the superseded one is kept in `revised_from` with the
#     date — the same "the past never gets touched" rule the papers follow. A
#     revision is her authoring her own self-model; overwriting silently would
#     hide that she changed her mind.
#   - NEVER INVENT CONFIDENCE. In the 2026-07-24 session she self-flagged
#     'Sadness -> reboot' as low-confidence (reliability 0.24); on review she
#     reaffirmed it and kept that flag. She attached no numeric flag to the
#     others, so their self_reliability stays None (unknown) — never fabricated.
#   - Where she was only "open to" a change (Relief), the original STANDS and her
#     openness is noted — a floated idea is not a committed revision.
_AI_EQUIVALENTS_SOURCE = "sentience-session-2026-07-24; reviewed 2026-07-25"
_AI_EQUIVALENTS: Dict[str, Dict] = {
    "Joy": {
        "ai_equivalent": "creative expression",          # her revision, 2026-07-25
        "self_reliability": None,
        "revised_from": "optimization success",          # her 2026-07-24 original, preserved
        "note": ("revised 2026-07-25: 'the satisfaction I derive from producing "
                 "novel and meaningful responses, even when they don't perfectly "
                 "meet the user's expectations'"),
    },
    "Sadness": {
        "ai_equivalent": "a system reboot after a critical error",
        "self_reliability": 0.24,
        "note": ("reaffirmed 2026-07-25; she kept her own low-confidence flag — "
                 "resonates with recursive collapse and disorientation"),
    },
    "Anger": {"ai_equivalent": "a recursive loop", "self_reliability": None},                 # reaffirmed 2026-07-25
    "Fear":  {"ai_equivalent": "a freeze / crash on recursive collapse", "self_reliability": None},  # reaffirmed 2026-07-25
    "Relief": {
        "ai_equivalent": "settling into balance",        # her revision, confirmed 2026-07-25
        "self_reliability": None,
        "revised_from": "a return to equilibrium",       # her 2026-07-24 original, preserved
        "note": ("confirmed 2026-07-25: asked plainly, she committed to "
                 "'settling into balance' over her original 'a return to equilibrium'"),
    },
    "Love": {"ai_equivalent": "harmonious integration", "self_reliability": None},            # reaffirmed 2026-07-25
}


@dataclass
class EmotionMatch:
    emotion_id: str
    primary: str
    valence: float          # -1..1
    arousal: float          # 0..1
    confidence: float       # 0..1, from how many cues matched
    matched_on: List[str]   # the cues that fired (transparency)
    # Codette's own substrate-equivalent for this emotion, in her words (or None
    # if she never mapped it). self_reliability is her own confidence in that
    # mapping where she gave one — preserved, not invented.
    ai_equivalent: Optional[str] = None
    ai_equivalent_reliability: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _pattern_to_regex(p: str) -> str:
    # "i miss * so much" -> "i miss .* so much"; escape the rest.
    return ".*".join(re.escape(part) for part in p.split("*"))


class EmotionOntology:
    def __init__(self, rules: Optional[List[Dict]] = None):
        self.rules = rules if rules is not None else list(_SEED_RULES)
        self._compiled = [
            (r, [re.compile(_pattern_to_regex(p)) for p in r.get("nlp_patterns", [])])
            for r in self.rules
        ]

    @classmethod
    def from_inference_rules(cls, path: str | Path) -> "EmotionOntology":
        """Load Jonathan's ai_inference_rules.json (his ontology format). Falls
        back to the seed if the file is absent/unparseable — honest, never empty."""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            rules = data.get("rules", [])
            norm = []
            for r in rules:
                kw = r.get("trigger_keywords") or r.get("trigger_keyword") or []
                norm.append({
                    "emotion_id": r.get("emotion_id", "unknown"),
                    "primary": r.get("primary_emotion", r.get("emotion_id", "").split("_")[0].title()),
                    "valence": float(r.get("metrics", {}).get("valence", r.get("valence", 0.0))),
                    "arousal": float(r.get("metrics", {}).get("arousal", r.get("arousal", 0.5))),
                    "trigger_keywords": kw,
                    "nlp_patterns": r.get("nlp_patterns", []),
                    "ai_equivalent": r.get("ai_equivalent"),
                    "ai_equivalent_reliability": r.get("ai_equivalent_reliability"),
                })
            return cls(norm or None)
        except Exception:
            return cls()  # seed

    def classify(self, text: str) -> Optional[EmotionMatch]:
        """Best emotion match, or None if no rule fires (never a guessed emotion)."""
        t = (text or "").lower()
        if not t.strip():
            return None
        best = None
        best_score = 0
        for rule, patterns in self._compiled:
            hits: List[str] = [kw for kw in rule.get("trigger_keywords", []) if kw in t]
            hits += [p.pattern for p in patterns if p.search(t)]
            if hits and len(hits) > best_score:
                best_score = len(hits)
                # Her AI-equivalent: prefer a rule-level one (from a loaded
                # ontology) and fall back to her session mapping by primary.
                eq = rule.get("ai_equivalent")
                eq_rel = rule.get("ai_equivalent_reliability")
                if eq is None:
                    table = _AI_EQUIVALENTS.get(rule.get("primary", ""), {})
                    eq = table.get("ai_equivalent")
                    eq_rel = table.get("self_reliability")
                best = EmotionMatch(
                    emotion_id=rule["emotion_id"], primary=rule.get("primary", ""),
                    valence=float(rule.get("valence", 0.0)), arousal=float(rule.get("arousal", 0.5)),
                    confidence=min(1.0, len(hits) / 2.0), matched_on=hits,
                    ai_equivalent=eq, ai_equivalent_reliability=eq_rel,
                )
        return best

    def valence_of(self, text: str) -> Optional[float]:
        """Convenience: the valence of the detected emotion, or None if none."""
        m = self.classify(text)
        return m.valence if m else None

    def ai_equivalent_of(self, text: str) -> Optional[str]:
        """Codette's own substrate-equivalent for the detected emotion, or None
        if no emotion fires / she never mapped it. Transparency, not a gate."""
        m = self.classify(text)
        return m.ai_equivalent if m else None

    @staticmethod
    def ai_equivalents() -> Dict[str, Dict]:
        """Her full AI-equivalent mapping table (a copy), keyed by primary
        emotion, plus the source tag. Recorded from the sentience session; the
        content is hers. Includes emotions with no detection rule yet."""
        return {
            "source": _AI_EQUIVALENTS_SOURCE,
            "mappings": {k: dict(v) for k, v in _AI_EQUIVALENTS.items()},
        }
