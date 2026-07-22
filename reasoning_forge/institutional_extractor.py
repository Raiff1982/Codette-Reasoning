"""
InstitutionalExtractor — derives InstitutionalState from unstructured text.

Two-stage pipeline:
  Stage 1 — Date extraction: regex scanning + dateutil.parser
  Stage 2 — Event classification: keyword patterns assign t_op / t_inst / actors

Usage (Option B — automatic):
    extractor = InstitutionalExtractor()
    state, confidence = extractor.extract(query + " " + synthesis)
    if state and confidence > 0.3:
        metrics = lens.observe(state)

Usage (Option A — structured, zero extraction overhead):
    state = InstitutionalState(
        state_id="recall-2024",
        ladder=TimestampLadder(t_op=days_since_epoch(2024, 1, 10),
                               t_inst=days_since_epoch(2024, 10, 10)),
        closure_class=ClosureClass.SUPPRESSED,
        ...
    )
    metrics = lens.observe(state)

Confidence reflects how many key fields (t_op, t_inst, closure_class, actors)
were successfully populated.  Callers should apply a threshold (≥ 0.3 suggested)
before trusting the output.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from reasoning_forge.time_travel_lens import (
    ActorGap,
    ClosureClass,
    InstitutionalState,
    TimestampLadder,
)

logger = logging.getLogger(__name__)


# ── Event-type keyword patterns ───────────────────────────────────────────────

# Material action: what the organization DID before formal acknowledgement
_OP_RE = re.compile(
    r'\b('
    r'patch(ed)?|fix(ed)?|modif(ied|y|ication)?|adjust(ed|ment)?|'
    r'implement(ed)?|quietly|internally|discover(ed)?|'
    r'aware|knew|know|found|identified?|detect(ed)?|'
    r'changed?|altered?|corrected?|remediat(ed)?|'
    r'suppress(ed)?|conceal(ed)?|hid(den)?|cover(ed)?\s*up|'
    r'kept?\s+(quiet|secret|hidden)|did\s+not\s+(disclose|report|tell)'
    r')\b',
    re.IGNORECASE,
)

# Formal registration: public / official acknowledgement
_INST_RE = re.compile(
    r'\b('
    r'announced?|disclos(ed|ure)|report(ed|ing)?|fil(ed|ing)?|'
    r'register(ed)?|publish(ed)?|admitted?|recall(ed)?|'
    r'notif(ied)?\s+(?:the\s+)?public|press\s+release|'
    r'official(ly)?|regulatory\s+(filing|report|submission)|'
    r'formal(ly)?|publicly\s+(disclosed?|announced?|admitted?)|'
    r'documented?|submi(tted|ssion)|acknowledged?'
    r')\b',
    re.IGNORECASE,
)

# Closure class signals
_SUPPRESSED_RE = re.compile(
    r'\b('
    r'den(ied|y)|conceal(ed)?|hid(den)?|suppress(ed)?|cover(ed)?\s*up|'
    r'fail(ed)?\s+to\s+(disclose|report|tell)|did\s+not\s+report|'
    r'never\s+report(ed)?|cover-up|withheld?|kept?\s+secret'
    r')\b',
    re.IGNORECASE,
)
_DRIFT_RE = re.compile(
    r'\b('
    r'ongoing|under\s+investigation|still\s+review(ing)?|pending|unresolved|'
    r'under\s+review|not\s+yet\s+(disclosed?|reported?)|'
    r'investigation\s+continue|active\s+investigation'
    r')\b',
    re.IGNORECASE,
)
_CLOSED_RE = re.compile(
    r'\b('
    r'recall(ed)?|fully\s+disclos(ed|ure)|admit(ted)?|resolv(ed)?|'
    r'compensat(ed)?|settl(ed|ement)|final\s+report|'
    r'closed?\s+(investigation|case)|investigation\s+complet(ed)?'
    r')\b',
    re.IGNORECASE,
)

# Known institutional actor types and their keyword aliases
_ACTOR_TERMS: Dict[str, List[str]] = {
    "engineers":   ["engineer", "technical", "developer", "r&d", "scientist", "researcher"],
    "management":  ["management", "manager", "director", "vp ", "vice president", "supervisor"],
    "legal":       ["legal", "lawyer", "attorney", "counsel", "law department", "general counsel"],
    "executives":  ["executive", "ceo", "cfo", "coo", "cto", "board", "leadership", "c-suite"],
    "regulators":  ["regulator", "agency", "fda", "epa", "sec ", "nhtsa", "government", "federal",
                    "oversight", "inspector", "auditor"],
    "employees":   ["employee", "worker", "staff", "team member", "personnel"],
}

# ── Date extraction ───────────────────────────────────────────────────────────

# Ordered by specificity — more specific patterns are tried first
_DATE_REGEXES = [
    re.compile(
        r'(?:January|February|March|April|May|June|July|August|'
        r'September|October|November|December)\s+\d{1,2}(?:,?\s+\d{4})?',
        re.IGNORECASE,
    ),
    re.compile(
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}(?:,?\s+\d{4})?',
        re.IGNORECASE,
    ),
    re.compile(r'\d{4}-\d{2}-\d{2}'),
    re.compile(r'\d{1,2}/\d{1,2}/(?:\d{4}|\d{2})'),
    re.compile(
        r'\d{1,2}(?:st|nd|rd|th)\s+(?:of\s+)?'
        r'(?:January|February|March|April|May|June|July|August|'
        r'September|October|November|December)',
        re.IGNORECASE,
    ),
]

_EPOCH = datetime(1970, 1, 1)


@dataclass
class _DateHit:
    raw:        str
    parsed:     Optional[datetime]
    context:    str     # ±100 chars of surrounding text
    op_score:   float   # keyword density for material-action events
    inst_score: float   # keyword density for formal-registration events


class InstitutionalExtractor:
    """
    Derives InstitutionalState from a text string.

    Thread-safe — a single instance may be reused across forge calls.
    dateutil is an optional dependency; if absent, only ISO dates are parsed.
    """

    def __init__(self, reference_year: int = 2025):
        self._reference_year = reference_year
        self._dateutil_available = self._check_dateutil()

    @staticmethod
    def _check_dateutil() -> bool:
        try:
            import dateutil.parser  # noqa: F401
            return True
        except ImportError:
            return False

    # ── Stage 1: date extraction ──────────────────────────────────────────────

    def _find_dates(self, text: str) -> List[_DateHit]:
        hits: List[_DateHit] = []
        seen: set = set()

        for rx in _DATE_REGEXES:
            for m in rx.finditer(text):
                # Skip overlapping spans
                if any(s in seen for s in range(m.start(), m.end())):
                    continue
                seen.update(range(m.start(), m.end()))

                raw     = m.group(0)
                parsed  = self._parse_date(raw)
                lo      = max(0, m.start() - 100)
                hi      = min(len(text), m.end() + 100)
                ctx     = text[lo:hi]

                hits.append(_DateHit(
                    raw=raw,
                    parsed=parsed,
                    context=ctx,
                    op_score=float(len(_OP_RE.findall(ctx))),
                    inst_score=float(len(_INST_RE.findall(ctx))),
                ))

        return hits

    def _parse_date(self, raw: str) -> Optional[datetime]:
        if self._dateutil_available:
            try:
                from dateutil import parser as dup
                return dup.parse(
                    raw,
                    default=datetime(self._reference_year, 1, 1),
                    dayfirst=False,
                )
            except Exception:
                pass
        # Fallback: ISO only
        try:
            return datetime.strptime(raw.strip(), "%Y-%m-%d")
        except ValueError:
            return None

    # ── Stage 2: event classification ────────────────────────────────────────

    def _infer_closure_class(self, text: str) -> Tuple[ClosureClass, float]:
        sup   = len(_SUPPRESSED_RE.findall(text))
        drift = len(_DRIFT_RE.findall(text))
        closed = len(_CLOSED_RE.findall(text))
        total = sup + drift + closed

        if total == 0:
            return ClosureClass.DRIFT, 0.15

        def _conf(n: int) -> float:
            return round(min(1.0, n / max(total, 1) * 1.5), 2)

        if sup >= closed and sup >= drift:
            return ClosureClass.SUPPRESSED, _conf(sup)
        if closed >= sup and closed >= drift:
            return ClosureClass.CLOSED, _conf(closed)
        return ClosureClass.DRIFT, _conf(drift)

    def _extract_actors(
        self,
        text: str,
        t_op: Optional[float],
        t_inst: Optional[float],
    ) -> List[ActorGap]:
        """
        Assigns per-actor timestamps by examining which event-type keywords
        appear in sentences that mention each actor.
        """
        actors: List[ActorGap] = []
        sentences = re.split(r'[.!?\n]', text)

        for actor_name, aliases in _ACTOR_TERMS.items():
            actor_sentences = [
                s for s in sentences
                if any(alias in s.lower() for alias in aliases)
            ]
            if not actor_sentences:
                continue

            joined   = " ".join(actor_sentences)
            op_hits  = len(_OP_RE.findall(joined))
            inst_hits = len(_INST_RE.findall(joined))

            actors.append(ActorGap(
                actor_id=actor_name,
                t_op_i=t_op   if op_hits   > 0 else None,
                t_inst_i=t_inst if inst_hits > 0 else None,
            ))

        return actors

    # ── Main ─────────────────────────────────────────────────────────────────

    def extract(self, text: str) -> Tuple[Optional[InstitutionalState], float]:
        """
        Derive InstitutionalState from text.

        Returns (state, confidence) where confidence ∈ [0.0, 1.0].
        Returns (None, 0.0) when insufficient structure is found.

        Confidence rubric:
          Each populated field (t_op, t_inst, closure_class, actors) contributes
          0.25 × closure_confidence to the final score.  A fully-populated
          extraction with strong closure signal approaches 1.0.
        """
        if not text or len(text.strip()) < 30:
            return None, 0.0

        hits = self._find_dates(text)
        if not hits:
            return None, 0.0

        # Pick t_op and t_inst as the highest-scoring candidates for each role,
        # requiring them to be distinct date hits.
        op_ranked   = sorted(hits, key=lambda h: h.op_score,   reverse=True)
        inst_ranked = sorted(hits, key=lambda h: h.inst_score, reverse=True)

        op_hit   = op_ranked[0]
        inst_hit = next((h for h in inst_ranked if h is not op_hit), None)

        t_op   = self._to_days(op_hit.parsed)
        t_inst = self._to_days(inst_hit.parsed) if inst_hit else None

        if t_op is None and t_inst is None:
            return None, 0.0

        closure_class, closure_conf = self._infer_closure_class(text)
        actors                      = self._extract_actors(text, t_op, t_inst)

        # Confidence: fraction of key fields populated × closure confidence
        populated = sum([
            t_op   is not None,
            t_inst is not None,
            closure_conf > 0.25,
            len(actors) > 0,
        ])
        confidence = round((populated / 4.0) * max(closure_conf, 0.2), 3)

        # Unfolding energy proxy: keyword density per 100 words
        word_count       = max(len(text.split()), 1)
        keyword_hits     = len(_OP_RE.findall(text)) + len(_INST_RE.findall(text))
        unfolding_energy = round(keyword_hits / word_count * 100, 2)

        state_id = hashlib.sha256(text[:200].encode()).hexdigest()[:16]

        state = InstitutionalState(
            state_id=state_id,
            ladder=TimestampLadder(
                t_op=t_op,
                t_inst=t_inst,
            ),
            closure_class=closure_class,
            unfolding_energy=unfolding_energy,
            influence_over_time=[1.0] * max(1, len(hits)),
            actor_gaps=actors,
            registration_fidelity_memo=op_hit.context[:250],
        )

        logger.debug(
            "[InstitutionalExtractor] state=%s t_op=%.1f t_inst=%s "
            "closure=%s conf=%.3f actors=%d",
            state_id, t_op or 0,
            f"{t_inst:.1f}" if t_inst is not None else "None",
            closure_class.value, confidence, len(actors),
        )
        return state, confidence

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_days(dt: Optional[datetime]) -> Optional[float]:
        """Convert a datetime to days-since-Unix-epoch for TimestampLadder."""
        if dt is None:
            return None
        return (dt - _EPOCH).total_seconds() / 86400.0
