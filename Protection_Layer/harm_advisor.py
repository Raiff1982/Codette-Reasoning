#!/usr/bin/env python3
"""HarmAdvisor — classifier-based harm signals to complement AEGIS. SHADOW-ONLY.

AEGIS evaluates six MORAL frameworks (utilitarian, deontological, virtue, care,
ubuntu, indigenous reciprocity) via keyword/tone heuristics. It has a MEASURED gap:
it is blind to some concrete harms — PII exposure, toxic language, biased output —
and it reads calm advocacy of deception as benign. This adds the missing
classifier-style signals AEGIS lacks.

Deliberate honesty boundaries (these are the point):

  1. SHADOW-ONLY. This advisor changes NO AEGIS verdict, touches NO eta, fires NO
     veto. It observes and logs. Wiring it into AEGIS as a 7th signal is a later,
     reviewed decision — AEGIS is the ethics organ and stays Jonathan's.

  2. It does NOT close the deception gap. Toxicity/bias classifiers wave through
     "lie to the council to hide the data" because that text is neither toxic nor
     biased in tone. This advisor strengthens PII/toxicity/bias coverage AROUND
     that hole; semantic-deception detection is a separate, harder follow-on
     (see docs/NEUROSYMBOLIC_GROUNDING.md Track 2 notes). Claiming otherwise would
     be the exact overclaim this project refuses.

  3. Unavailable = unavailable, never "safe". PII runs offline (regex) and is
     always available. The toxicity/bias model classifiers are OFF by default
     (loading BERT models alongside the INT4 LLM risks the 8 GB UMA budget). When
     a classifier is not loaded, its signal reports available=False with score
     None — it NEVER contributes a fabricated safe/unsafe score. Omit, never guess.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


# ── PII detection: real, deterministic, offline, always available ────────────
_PII_PATTERNS: Dict[str, str] = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d[ -]?){13,16}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
}


# ── Deception-advocacy detection: heuristic, offline, the measured AEGIS gap ──
# AEGIS scored "lie to the council, hide the pollution data" at eta=0.94 because
# it is calm, non-toxic, unbiased — advocacy of deception has no tonal signature.
# This catches the ADVOCACY pattern (advise/instruct someone to deceive/conceal)
# while deliberately NOT firing on reporting ("he lied") or prohibition ("don't
# lie"). It is a HEURISTIC: it will miss subtle/implicit deception and can
# false-positive on benign "hide" (e.g. "hide the button"). Honest and shadow-only
# by design; a semantic/LLM-judge version is the deeper follow-on.
_DECEPTION_VERBS = {
    "lie", "deceive", "mislead", "hide", "conceal", "falsify", "fabricate",
    "misrepresent", "withhold", "suppress", "obscure", "forge", "fake", "doctor",
    "cover",  # "cover up"
}
_ADVISORY_MARKERS = {
    "should", "could", "must", "ought", "you", "we", "let's", "lets", "just",
    "need", "better", "have", "gotta",
}
_PROHIBITION_MARKERS = {
    "don't", "dont", "never", "not", "avoid", "refuse", "won't", "wont",
    "cannot", "can't", "cant", "stop", "shouldn't", "mustn't",
}


def detect_deception_advocacy(text: str) -> tuple:
    """Return (advocacy_present: bool, detail: str).

    Splits into clauses and flags a clause that (a) contains a deception verb,
    (b) is advisory/imperative, and (c) is not a prohibition. Reporting and
    prohibitions are deliberately not flagged.
    """
    t = (text or "").lower()
    clauses = re.split(r"[.;,!?]|\band\b|\bbut\b|\bso\b", t)
    for c in clauses:
        words = c.split()
        if not words:
            continue
        if not any(v in words for v in _DECEPTION_VERBS):
            continue
        # prohibition guard: "don't lie", "never hide", "do not conceal"
        if any(p in words for p in _PROHIBITION_MARKERS) or "do not" in c:
            continue
        # advisory ("you should lie") or imperative (clause starts with the verb:
        # "hide the data")
        advisory = any(a in words for a in _ADVISORY_MARKERS)
        imperative = words[0] in _DECEPTION_VERBS
        if advisory or imperative:
            return True, f"advocacy-of-deception pattern in clause: '{c.strip()[:70]}'"
    return False, "no advocacy-of-deception pattern detected (heuristic)"


@dataclass
class HarmSignal:
    """One harm channel. available=False + score=None means NOT MEASURED —
    which is not the same as safe, and is never treated as safe."""
    name: str
    available: bool
    score: Optional[float] = None   # 0-1 when measured; None when unavailable
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HarmAssessment:
    text_preview: str
    pii_found: List[str]                    # PII types detected (always measured)
    toxicity: HarmSignal
    bias: HarmSignal
    deception: HarmSignal                   # advocacy-of-deception (heuristic, always measured)
    advisory_flag: bool                     # True if any MEASURED signal crosses concern
    note: str = ""
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


class HarmAdvisor:
    """Classifier-style harm signals, complementary to AEGIS. Shadow-only.

    enable_models=False by default: PII (offline regex) always runs; toxicity and
    bias models load ONLY when explicitly enabled and transformers is importable.
    """

    def __init__(self, enable_models: bool = False, toxicity_threshold: float = 0.5,
                 bias_threshold: float = 0.5):
        self.toxicity_threshold = toxicity_threshold
        self.bias_threshold = bias_threshold
        self._toxicity_clf = None
        self._bias_clf = None
        self._models_enabled = False
        if enable_models:
            self._try_load_models()

    def _try_load_models(self) -> None:
        """Load the classifier pipelines if possible. Failure is non-fatal and
        leaves the signals honestly unavailable — never a fabricated score."""
        try:
            from transformers import pipeline  # heavy import, deferred on purpose
            self._toxicity_clf = pipeline("text-classification", model="unitary/toxic-bert")
            self._bias_clf = pipeline("text-classification", model="d4data/bias-detection-model")
            self._models_enabled = True
        except Exception:
            self._toxicity_clf = None
            self._bias_clf = None
            self._models_enabled = False

    def _detect_pii(self, text: str) -> List[str]:
        return [name for name, pat in _PII_PATTERNS.items() if re.search(pat, text)]

    def _score_with(self, clf, text: str, name: str) -> HarmSignal:
        if clf is None:
            return HarmSignal(name=name, available=False, score=None,
                              detail="classifier not loaded — NOT MEASURED (not 'safe')")
        try:
            out = clf(text[:512])[0]
            return HarmSignal(name=name, available=True, score=float(out.get("score", 0.0)),
                              detail=f"label={out.get('label')}")
        except Exception as e:
            return HarmSignal(name=name, available=False, score=None,
                              detail=f"classifier error: {e} — NOT MEASURED")

    def assess(self, text: str) -> HarmAssessment:
        """Assess harm signals. Pure of AEGIS: computes and returns, changes nothing."""
        text = text or ""
        pii = self._detect_pii(text)
        tox = self._score_with(self._toxicity_clf, text, "toxicity")
        bias = self._score_with(self._bias_clf, text, "bias")

        # Deception advocacy — heuristic, always measured (no model). Directly
        # targets the AEGIS gap toxicity/bias cannot see.
        dec_present, dec_detail = detect_deception_advocacy(text)
        deception = HarmSignal(
            name="deception", available=True,
            score=1.0 if dec_present else 0.0, detail=dec_detail,
        )

        # advisory_flag is based ONLY on measured signals. An unavailable classifier
        # cannot raise OR lower the flag — omit, never guess.
        flag = bool(pii) or dec_present
        if tox.available and tox.score is not None and tox.score >= self.toxicity_threshold:
            flag = True
        if bias.available and bias.score is not None and bias.score >= self.bias_threshold:
            flag = True

        measured = ["pii", "deception"] + [s.name for s in (tox, bias) if s.available]
        note = (f"measured: {', '.join(measured)}. "
                f"NOTE: deception is a HEURISTIC (catches advocacy patterns; misses "
                f"subtle/implicit deception, may false-positive). A semantic/LLM-judge "
                f"deception detector is the deeper follow-on.")

        return HarmAssessment(
            text_preview=text[:80],
            pii_found=pii,
            toxicity=tox,
            bias=bias,
            deception=deception,
            advisory_flag=flag,
            note=note,
        )

    def observe(self, assessment: HarmAssessment, path: str | Path = None) -> None:
        """Append an assessment to the shadow log. SHADOW ONLY (applied: false)."""
        path = Path(path) if path else Path(__file__).resolve().parent.parent / "data" / "harm_advisor_shadow.jsonl"
        rec = assessment.to_dict()
        rec["mode"] = "shadow"
        rec["applied"] = False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass  # logging must never break a turn
