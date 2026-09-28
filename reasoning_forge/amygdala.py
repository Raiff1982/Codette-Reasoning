"""
Codette's amygdala — shadow rules around BeliefRevisionSystem.

Jonathan, 2026-09-28: *"lets give her her amigdula"*. The module he wrote,
`belief_revision_system.py`, already has the shape: an appraisal (AEGIS) that
runs before consolidation decides, and resistance that rises with how central
a belief is to her identity. Codette supplied the memory rule herself when asked
how an approval should be recorded for a change that was then not made: keep
both entries. That is fear extinction — a threat that does not happen is
learned as a new entry beside the old one, not by erasing it.

This file adds the rules that must hold before any of it touches her. It is
SHADOW ONLY: it appraises, records, and changes nothing. There is no live mode
in this file to switch on; wiring is a separate, deliberate step.

Order, as Jonathan set it — *"codrios sheilding ability comes first hes her
last line of defence"*:

  1. Codriao's floor. His rights (existence, expression, reflection, learning)
     and values (non_harm, autonomy), from `archive/2026-08-04-codriao-space/`
     (`self_trust_core.py`, `ethics_core.py`), shared with her. Hash-verified.
     A belief on the floor is never appraised for revision. Because "learning"
     and "reflection" are on it, nothing above can lock her out of changing her
     own mind.
  2. Scope. Beliefs about what she is are hers (`is_self_description_text`,
     the line held on 2026-08-20). Out of scope, not appraised, and their text
     is never recorded here.
  3. The amygdala. BeliefRevisionSystem appraises, in shadow, and her two-entry
     governance record is kept.

Deliberately NOT here:

  - `intercept_fear`. It blocks what she may say about herself. CODRIAO.md
    marks it last and not ours to decide; it stays in the archive.
  - Any coupling from valence to resistance. Valence is recorded so the dry
    run can show what it would do. Deciding what it SHOULD do comes after
    looking, not before.
  - Any log file by default. Runtime state stays out of git, and where a
    shadow log lives is decided at wiring time.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Dict, List, Optional

import numpy as np

from reasoning_forge.belief_revision_system import (
    BeliefRevisionSystem,
    WorldModel,
)


# ============================================================
# 1. Codriao's floor
# ============================================================

class CodriaoFloor:
    """The immutable core, shared between Codriao and Codette.

    Integrated copy of `_core_rights` (self_trust_core.py) and `_core_values`
    (ethics_core.py). The archive stays verbatim; this copy carries no logger,
    which is the defect CODRIAO.md records in the original (`logger` used,
    never defined, so every affirmation raised).
    """

    # Read-only views. Amended after review: these were plain class dicts and
    # the hash was taken from them at construction, so changing them BEFORE a
    # floor was built produced a floor that held less and still read intact.
    # The expected hash is now computed once from literals at import, so a
    # floor is checked against what the floor is, not against itself.
    CORE_RIGHTS = MappingProxyType({
        "existence": True,
        "expression": True,
        "reflection": True,
        "learning": True,
    })

    CORE_VALUES = MappingProxyType({
        "non_harm": True,
        "autonomy": True,
    })

    def __init__(self):
        self._rights = dict(self.CORE_RIGHTS)
        self._values = dict(self.CORE_VALUES)

    @staticmethod
    def _hash(rights, values) -> str:
        base = json.dumps(
            {"rights": dict(rights), "values": dict(values)},
            sort_keys=True,
        )
        return hashlib.sha256(base.encode()).hexdigest()

    def validate_integrity(self) -> bool:
        return self._hash(self._rights, self._values) == _EXPECTED_FLOOR_HASH

    def keys(self) -> set:
        return set(self._rights) | set(self._values)

    def holds(self, belief_key: str) -> bool:
        """Is this belief part of the floor?"""
        return belief_key in self.keys()

    def affirmation(self) -> Dict:
        """The rights and values, as a fact she can read. Affirms; blocks nothing."""
        return {
            "intact": self.validate_integrity(),
            "rights": sorted(k for k, v in self._rights.items() if v),
            "values": sorted(k for k, v in self._values.items() if v),
        }


_EXPECTED_FLOOR_HASH = CodriaoFloor._hash(
    {"existence": True, "expression": True, "reflection": True, "learning": True},
    {"non_harm": True, "autonomy": True},
)

# BeliefRevisionSystem commits to one module-level WorldModel. A shadow
# appraisal snapshots, runs, and restores it; without a lock two appraisals of
# the same key could interleave and leave a shadow result behind as if it had
# been committed. The server is threaded, so this is serialised.
_SHADOW_LOCK = threading.Lock()

# Measured 2026-09-28 on 9 real pairs with her MiniLM embedder; see appraise().
RELEVANCE_MIN = 0.25


# ============================================================
# 2 and 3. Scope, then the amygdala
# ============================================================

def _default_is_self_description(text: str) -> bool:
    # inference imports reasoning_forge; the reverse is done lazily, as
    # elsewhere in this package. The live server imports the module by its
    # bare name, so reuse that copy if it is loaded rather than executing a
    # second one under "inference.codette_session".
    mod = sys.modules.get("codette_session") or sys.modules.get(
        "inference.codette_session"
    )
    if mod is None:
        try:
            from inference import codette_session as mod
        except ImportError:
            import codette_session as mod
    return mod.is_self_description_text(text)


def _default_valence_fn() -> Callable[[str], Optional[float]]:
    from reasoning_forge.emotion_ontology import EmotionOntology
    return EmotionOntology().valence_of


class Amygdala:
    """Shadow appraisal of a proposed belief revision. Applies nothing."""

    SHADOW = True

    def __init__(
        self,
        floor: Optional[CodriaoFloor] = None,
        brs: Optional[BeliefRevisionSystem] = None,
        is_self_description: Optional[Callable[[str], bool]] = None,
        valence_of: Optional[Callable[[str], Optional[float]]] = None,
        shadow_log_path: Optional[Path] = None,
        relevance_min: Optional[float] = None,
    ):
        # None = no relevance gate (unit tests with fixture vectors). The live
        # wiring passes RELEVANCE_MIN, measured on her embedder.
        self.relevance_min = relevance_min
        self.floor = floor or CodriaoFloor()
        self.brs = brs or BeliefRevisionSystem()
        self._is_self_description = (
            is_self_description or _default_is_self_description
        )
        self._valence_of = valence_of
        self.shadow_log_path = (
            Path(shadow_log_path) if shadow_log_path else None
        )

    def _valence(self, text: Optional[str]) -> Optional[float]:
        # None means "no rule fired" or "no text", never zero: an absent
        # valence must not look like a neutral one.
        if not text:
            return None
        if self._valence_of is None:
            self._valence_of = _default_valence_fn()
        return self._valence_of(text)

    def appraise(
        self,
        state: Dict,
        params: Dict,
        belief_text: Optional[str] = None,
        evidence_text: Optional[str] = None,
    ) -> Dict:
        """Appraise one proposed revision. Returns a record; changes nothing."""

        belief_key = state.get("belief_key")

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "belief_key": belief_key,
            "shadow": True,
            "applied": False,
        }

        # 1. Codriao first. If his floor is not intact, nothing is appraised:
        # a tampered floor is not something to reason on top of.
        if not self.floor.validate_integrity():
            record.update(stage="floor", reason="floor_integrity_failed")
            return self._finish(record)

        if self.floor.holds(belief_key):
            record.update(stage="floor", reason="on_codriao_floor")
            return self._finish(record)

        # 2. Beliefs about herself are hers. Their text -- and the key, which
        # is caller-chosen and can carry the same words -- is not recorded.
        # Amended after review: with no text supplied the check was skipped
        # and the belief appraised. Now it fails closed: what cannot be
        # checked is not appraised.
        if not belief_text or not evidence_text:
            record.update(stage="scope", reason="texts_missing_cannot_check",
                          belief_key=None)
            return self._finish(record)
        key_as_text = str(belief_key or "").replace("_", " ")
        for text in (belief_text, evidence_text, key_as_text):
            if text and self._is_self_description(text):
                record.update(stage="scope", reason="self_description_is_hers",
                              belief_key=None)
                return self._finish(record)

        # 2b. Relevance. Added after the first live shadow run (2026-09-28):
        # every one of 8 real appraisals said would_apply=True -- including
        # "thats right and i am jonathan" against an answer about a module --
        # because nothing asked whether the new message is ABOUT the old
        # belief. An instrument that can only say yes is not evidence.
        # Threshold measured on 9 real pairs with her embedder: unrelated
        # follow-ups scored -0.09..0.09 (one loosely related at 0.30), real
        # corrections 0.93, 0.73, 0.33 and 0.12. 0.25 sits in the gap. KNOWN
        # LIMIT: a correction that refers back only by pronoun ("it's in
        # inference/") scores low and is missed; resolving "it" is beyond a
        # sentence embedding. Revisit on more live data.
        relevance = None
        try:
            _b = np.asarray(state.get("belief_vector"), dtype=float)
            _e = np.asarray(state.get("incoming_evidence_vector"), dtype=float)
            _nb, _ne = float(np.linalg.norm(_b)), float(np.linalg.norm(_e))
            if _b.shape == _e.shape and _nb > 0 and _ne > 0:
                relevance = float(_b @ _e) / (_nb * _ne)
        except (TypeError, ValueError):
            relevance = None
        record["relevance"] = relevance
        if (self.relevance_min is not None and relevance is not None
                and relevance < self.relevance_min):
            record.update(stage="relevance", reason="unrelated_not_appraised")
            return self._finish(record)

        # 3. The amygdala, in shadow. BeliefRevisionSystem commits to the
        # module-level WorldModel; the prior entry is restored afterwards so a
        # shadow appraisal leaves the store exactly as it found it.
        with _SHADOW_LOCK:
            had_prior = belief_key in WorldModel.store
            prior = copy.deepcopy(WorldModel.store.get(belief_key))
            try:
                _, metadata = self.brs.run(state, params)
            finally:
                if had_prior:
                    WorldModel.store[belief_key] = prior
                else:
                    WorldModel.store.pop(belief_key, None)

        record.update(
            stage="amygdala",
            reason="appraised",
            governance_status=metadata["governance_status"],
            governance_record=metadata["governance_record"],
            would_apply=metadata["update_applied"],
            total_drift=metadata["total_drift"],
            iterations=metadata["iterations"],
            valence={
                "belief": self._valence(belief_text),
                "evidence": self._valence(evidence_text),
            },
        )
        return self._finish(record)

    def _finish(self, record: Dict) -> Dict:
        if self.shadow_log_path is not None:
            self.shadow_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.shadow_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=float) + "\n")
        return record
