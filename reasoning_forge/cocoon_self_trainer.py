#!/usr/bin/env python3
"""CocoonSelfTrainer — teach the adaptive model from first-hand experience. SHADOW.

Jonathan's idea: "let the model train itself on real-world data it's seen
first-hand." Codette already stores that data — the cocoons. This feeds it to the
adaptive sentiment model, using each cocoon's ALREADY-MEASURED emotional signal as
a weak label.

The one hard-won rule this is built around: self-training on first-hand data is
exactly where the optimizer went wrong (it learned from its own benchmark harness).
So the guards here are the point, not an afterthought:

  1. LABELS COME ONLY FROM STORED EMOTIONAL SIGNALS, never from the sentiment
     model's own prediction. A model that labels its own training data drifts into
     a self-reinforcing loop. The label source must be independent of the learner.

  2. IT REFUSES DEGENERATE DATA. Too few examples, or one class dominating
     (e.g. all-positive cocoons), and it does NOT train — it reports why. Learning
     from bad data and reporting success would be the exact lie we refuse.

  3. SHADOW-ONLY. Trains a SEPARATE analyzer instance and logs what it learned. It
     does not touch any live model. Whether self-training ever runs live is a
     reviewed decision after reading the shadow log.
"""

from __future__ import annotations

import glob
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from reasoning_forge.sentiment_analyzer import SentimentAnalyzer


# Emotional classifications -> weak sentiment label. Only confident, clearly-
# valenced emotions are used; ambiguous ones are skipped (not guessed).
_POSITIVE_EMOTIONS = {
    "hope", "awe", "joy", "curiosity", "love", "gratitude", "excitement",
    "trust", "contentment", "pride", "relief", "admiration",
}
_NEGATIVE_EMOTIONS = {
    "fear", "anger", "sadness", "disgust", "frustration", "anxiety", "grief",
    "despair", "shame", "guilt", "contempt", "distress",
}


def cocoon_label(cocoon: dict) -> Optional[Tuple[str, int]]:
    """Extract (text, weak_label) from one cocoon, or None if unusable.

    Label source, in priority order — ALL are independently-measured signals,
    never the sentiment model's own output:
      1. emotional_valence (schema v3): >0.1 -> pos, <-0.1 -> neg, else skip
      2. emotional_classification (EMG cocoons): mapped via the emotion sets
    """
    if not isinstance(cocoon, dict):
        return None

    text = (cocoon.get("user_response_text") or cocoon.get("user_query")
            or cocoon.get("response_summary")
            or (cocoon.get("metadata") or {}).get("context") or "")
    text = str(text).strip()
    if not text:
        return None

    # 1) continuous valence
    val = cocoon.get("emotional_valence")
    if isinstance(val, (int, float)):
        if val > 0.1:
            return text, 1
        if val < -0.1:
            return text, 0
        return None  # near-neutral: skip, don't guess

    # 2) categorical emotion
    emo = str(cocoon.get("emotional_classification", "")).strip().lower()
    if emo in _POSITIVE_EMOTIONS:
        return text, 1
    if emo in _NEGATIVE_EMOTIONS:
        return text, 0
    return None


@dataclass
class SelfTrainReport:
    collected: int
    positive: int
    negative: int
    trained: bool
    reason: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class CocoonSelfTrainer:
    """Shadow self-trainer with drift guards."""

    def __init__(self, min_examples: int = 20, min_minority_frac: float = 0.15):
        self.min_examples = min_examples
        self.min_minority_frac = min_minority_frac

    def collect_from_records(self, cocoons: Iterable[dict]) -> Tuple[List[str], List[int]]:
        texts, labels = [], []
        for c in cocoons:
            got = cocoon_label(c)
            if got:
                texts.append(got[0])
                labels.append(got[1])
        return texts, labels

    def collect_from_dir(self, cocoon_dir: str | Path = "cocoons") -> Tuple[List[str], List[int]]:
        recs = []
        for pat in ("*.cocoon", "*.json"):
            for f in glob.glob(str(Path(cocoon_dir) / "**" / pat), recursive=True):
                if "backup" in f.lower():
                    continue
                try:
                    recs.append(json.load(open(f, encoding="utf-8")))
                except Exception:
                    pass
        return self.collect_from_records(recs)

    def _guard(self, labels: List[int]) -> Tuple[bool, str]:
        """Refuse degenerate data. Returns (ok, reason)."""
        n = len(labels)
        if n < self.min_examples:
            return False, f"too few labelled examples ({n} < {self.min_examples})"
        pos = sum(labels)
        neg = n - pos
        minority = min(pos, neg)
        if minority == 0:
            return False, f"single-class data (pos={pos}, neg={neg}) — training would be degenerate"
        if minority / n < self.min_minority_frac:
            return False, (f"class imbalance too severe (minority {minority}/{n} = "
                           f"{minority/n:.2f} < {self.min_minority_frac}) — refusing to train")
        return True, "class balance and volume acceptable"

    def train_shadow(self, cocoons: Optional[Iterable[dict]] = None,
                     cocoon_dir: str | Path = "cocoons") -> Tuple[SelfTrainReport, Optional[SentimentAnalyzer]]:
        """Collect first-hand data, guard it, and (only if healthy) train a SHADOW
        analyzer. Returns (report, shadow_analyzer_or_None). Trains nothing live."""
        if cocoons is not None:
            texts, labels = self.collect_from_records(cocoons)
        else:
            texts, labels = self.collect_from_dir(cocoon_dir)

        pos = sum(labels)
        neg = len(labels) - pos
        ok, reason = self._guard(labels)
        if not ok:
            return SelfTrainReport(len(labels), pos, neg, trained=False, reason=reason), None

        shadow = SentimentAnalyzer(enable_adaptive=True)
        shadow.update(texts, labels)
        return SelfTrainReport(len(labels), pos, neg, trained=True,
                               reason="trained shadow model on first-hand cocoon data"), shadow

    def observe(self, report: SelfTrainReport, path: str | Path = None) -> None:
        """Append the report to the self-train shadow log (applied: false)."""
        path = Path(path) if path else Path(__file__).resolve().parent.parent / "data" / "self_train_shadow.jsonl"
        rec = report.to_dict()
        rec["mode"] = "shadow"
        rec["applied"] = False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
