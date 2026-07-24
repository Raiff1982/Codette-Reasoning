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


@dataclass
class EmotionMatch:
    emotion_id: str
    primary: str
    valence: float          # -1..1
    arousal: float          # 0..1
    confidence: float       # 0..1, from how many cues matched
    matched_on: List[str]   # the cues that fired (transparency)

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
                best = EmotionMatch(
                    emotion_id=rule["emotion_id"], primary=rule.get("primary", ""),
                    valence=float(rule.get("valence", 0.0)), arousal=float(rule.get("arousal", 0.5)),
                    confidence=min(1.0, len(hits) / 2.0), matched_on=hits,
                )
        return best

    def valence_of(self, text: str) -> Optional[float]:
        """Convenience: the valence of the detected emotion, or None if none."""
        m = self.classify(text)
        return m.valence if m else None
