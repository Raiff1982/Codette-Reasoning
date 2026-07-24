#!/usr/bin/env python3
"""SentimentAnalyzer — the advanced sentiment analyzer Jonathan built, made real.

Consolidates the genuinely-advanced pieces from four archive versions into one
honest Python module for codette-clean:

  - Ensemble (VADER + TextBlob)          — pi2_0 / Dontwatchme: two independent
                                            lexicon signals fused, not one.
  - Negation handling                    — pi2_0: "not good" -> "not NEG_good",
                                            wired into the adaptive model's input.
  - Adaptive / online learning           — pi3 C# UpdateModelWithNewData: a real
                                            updatable classifier (HashingVectorizer
                                            + SGD partial_fit) that LEARNS from
                                            labelled examples at runtime.
  - Optional transformer (BERT)          — pi2_0: heavier, OFF by default to
                                            protect the 8 GB UMA budget.

Honesty invariants (the point, not decoration):
  * Only methods that are actually available/trained contribute to the fused
    score. A missing method is omitted, never counted as neutral or safe.
  * If NO method is available, the result says so (available=[]) and returns a
    neutral score explicitly flagged as unmeasured — never a fabricated reading.
  * The adaptive model contributes ONLY once trained. Untrained, it scores None
    and stays out of the ensemble. It does not guess.

Stubs from the archives (sarcasm, domain-specific, multimodal) are deliberately
NOT reproduced as fake bodies. They are TODOs in docs/NEUROSYMBOLIC_GROUNDING.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _HAS_VADER = True
except Exception:
    _HAS_VADER = False

try:
    from textblob import TextBlob
    _HAS_TEXTBLOB = True
except Exception:
    _HAS_TEXTBLOB = False

try:
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier
    _HAS_SKLEARN = True
except Exception:
    _HAS_SKLEARN = False


_NEGATIONS = {"not", "no", "never", "none", "n't", "cannot", "without"}


def mark_negation(text: str) -> str:
    """Jonathan's negation technique (pi2_0): prefix NEG_ to the word after a
    negation so a downstream model learns the polarity flip. Used to preprocess
    the adaptive classifier's input. Exposed and tested on its own."""
    words = (text or "").split()
    out = []
    negate_next = False
    for w in words:
        if negate_next:
            out.append("NEG_" + w)
            negate_next = False
        else:
            out.append(w)
        if w.lower().strip(".,!?;:") in _NEGATIONS:
            negate_next = True
    return " ".join(out)


def has_negation(text: str) -> bool:
    return any(w.lower().strip(".,!?;:") in _NEGATIONS for w in (text or "").split())


@dataclass
class SentimentResult:
    compound: float                 # fused score in [-1, 1]
    polarity: str                   # "positive" | "negative" | "neutral"
    methods: Dict[str, float]       # per-method scores that were actually measured
    available: List[str]            # which methods contributed
    negation_detected: bool
    measured: bool                  # False only if NO method was available
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class _AdaptiveSentiment:
    """Real online-updatable classifier — the Python equivalent of the C#
    SdcaLogisticRegression + UpdateModelWithNewData. Untrained until fed data;
    scores None (abstains) until then. Trains on negation-marked text."""

    def __init__(self):
        self.vec = HashingVectorizer(n_features=2 ** 18, alternate_sign=False)
        self.clf = SGDClassifier(loss="log_loss")
        self._trained = False

    def update(self, texts: Sequence[str], labels: Sequence[int]) -> None:
        X = self.vec.transform([mark_negation(t) for t in texts])
        self.clf.partial_fit(X, list(labels), classes=[0, 1])
        self._trained = True

    def score(self, text: str) -> Optional[float]:
        if not self._trained:
            return None  # abstain — never guess before it has learned anything
        X = self.vec.transform([mark_negation(text)])
        p = float(self.clf.predict_proba(X)[0][1])   # P(positive)
        return 2.0 * p - 1.0                          # -> [-1, 1]


class SentimentAnalyzer:
    """Advanced multi-method sentiment with negation handling and online learning."""

    def __init__(self, enable_transformer: bool = False, enable_adaptive: bool = True,
                 pos_threshold: float = 0.05):
        self.pos_threshold = pos_threshold
        self._vader = SentimentIntensityAnalyzer() if _HAS_VADER else None
        self._adaptive = _AdaptiveSentiment() if (enable_adaptive and _HAS_SKLEARN) else None
        self._transformer = None
        if enable_transformer:
            self._try_load_transformer()

    def _try_load_transformer(self) -> None:
        try:
            from transformers import pipeline
            self._transformer = pipeline("sentiment-analysis")
        except Exception:
            self._transformer = None  # honestly unavailable, not faked

    def update(self, texts: Sequence[str], labels: Sequence[int]) -> bool:
        """Teach the adaptive model new labelled examples (label: 1 pos / 0 neg).
        Returns True if the update happened, False if no adaptive backend."""
        if self._adaptive is None:
            return False
        self._adaptive.update(texts, labels)
        return True

    def analyze(self, text: str) -> SentimentResult:
        text = text or ""
        methods: Dict[str, float] = {}

        if self._vader is not None:
            methods["vader"] = float(self._vader.polarity_scores(text)["compound"])
        if _HAS_TEXTBLOB:
            try:
                methods["textblob"] = float(TextBlob(text).sentiment.polarity)
            except Exception:
                pass
        if self._adaptive is not None:
            s = self._adaptive.score(text)
            if s is not None:          # contributes ONLY once trained
                methods["adaptive"] = s
        if self._transformer is not None:
            try:
                out = self._transformer(text[:512])[0]
                sign = 1.0 if str(out.get("label", "")).upper().startswith("POS") else -1.0
                methods["transformer"] = sign * float(out.get("score", 0.0))
            except Exception:
                pass

        if not methods:
            return SentimentResult(
                compound=0.0, polarity="neutral", methods={}, available=[],
                negation_detected=has_negation(text), measured=False,
                note="no sentiment backend available — neutral is UNMEASURED, not a reading",
            )

        fused = sum(methods.values()) / len(methods)
        if fused >= self.pos_threshold:
            polarity = "positive"
        elif fused <= -self.pos_threshold:
            polarity = "negative"
        else:
            polarity = "neutral"

        return SentimentResult(
            compound=round(fused, 4),
            polarity=polarity,
            methods={k: round(v, 4) for k, v in methods.items()},
            available=list(methods.keys()),
            negation_detected=has_negation(text),
            measured=True,
            note=f"fused {len(methods)} method(s): {', '.join(methods.keys())}",
        )


# ── Label normalization + file ingestion ────────────────────────────────────

def _normalize_label(v) -> Optional[int]:
    """Map varied label encodings to 1 (positive) / 0 (negative). None if unknown."""
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        if v in (0, 1):
            return int(v)
        return 1 if v > 0 else 0  # e.g. compound-style -1..1
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "pos", "positive", "true", "good"):
            return 1
        if s in ("0", "-1", "neg", "negative", "false", "bad"):
            return 0
    return None


def _extract_examples(records) -> Tuple[List[str], List[int]]:
    texts, labels = [], []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        text = rec.get("text") or rec.get("sentence") or rec.get("content")
        label = _normalize_label(rec.get("label", rec.get("sentiment")))
        if text and label is not None:
            texts.append(str(text))
            labels.append(label)
    return texts, labels


def learn_from_file(analyzer: "SentimentAnalyzer", file_path: str | Path) -> Dict:
    """The real body of Jonathan's pi3 `learn_from_file` placeholder.

    Reads a labelled dataset — a JSON list of {"text", "label"} objects OR a JSONL
    file (one such object per line) — and teaches the analyzer's adaptive model.
    Accepts label encodings 0/1, true/false, "positive"/"negative", etc.

    Honest outcomes (never a fabricated 'learned'):
      {"error": ...}                      — file/parse failure or no adaptive backend
      {"learned": 0, "reason": ...}       — parsed but no usable labelled examples
      {"learned": N, "positive": p, "negative": q}  — actually trained on N examples
    """
    p = Path(file_path)
    if analyzer._adaptive is None:
        return {"error": "no adaptive backend (enable_adaptive=True and install sklearn)"}
    try:
        raw = p.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"could not read file: {e}"}

    records = None
    try:
        parsed = json.loads(raw)
        records = parsed if isinstance(parsed, list) else parsed.get("data") or parsed.get("examples")
    except json.JSONDecodeError:
        # try JSONL
        records = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if not records:
        return {"learned": 0, "reason": "no records parsed from file"}

    texts, labels = _extract_examples(records)
    if not texts:
        return {"learned": 0, "reason": "no records with both text and a recognizable label"}

    analyzer.update(texts, labels)
    return {
        "learned": len(texts),
        "positive": sum(1 for l in labels if l == 1),
        "negative": sum(1 for l in labels if l == 0),
    }
