"""Tests for semantic_grounding — evidential support for qualitative thoughts.

The invariants under test are the honest ones:
  - support is reported as SUPPORT, never as truth (verdict + caveat),
  - it NEVER false-flags: weak overlap / no evidence -> UNADDRESSED,
  - a single shared word or stopword overlap can never manufacture support,
  - retrieval failure degrades to UNADDRESSED, never invented support.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.semantic_grounding import (
    ground_claim, ground_claim_via_memory, SemanticVerdict,
)


def test_supported_when_evidence_overlaps():
    ev = ["emergent boundary walking across the quantum web"]
    r = ground_claim("quantum boundary walking", ev)
    assert r.verdict is SemanticVerdict.SUPPORTED_BY_EVIDENCE
    assert r.support_score >= 0.5
    assert r.evidence and set(r.evidence[0]["shared_terms"]) >= {"quantum", "boundary", "walking"}


def test_support_detail_states_it_is_not_truth():
    # The epistemic line must be spelled out, every time support is claimed.
    r = ground_claim("quantum boundary walking",
                     ["emergent boundary walking across the quantum web"])
    assert r.verdict is SemanticVerdict.SUPPORTED_BY_EVIDENCE
    assert "not proof of truth" in r.detail.lower()


def test_no_evidence_is_unaddressed_not_support():
    r = ground_claim("quantum boundary walking", [])
    assert r.verdict is SemanticVerdict.UNADDRESSED
    assert r.support_score == 0.0
    assert not r.evidence


def test_single_shared_word_does_not_support():
    # Only "walking" overlaps -> below the 2-word floor -> UNADDRESSED.
    r = ground_claim("quantum boundary walking", ["the walking path was long and quiet"])
    assert r.verdict is SemanticVerdict.UNADDRESSED


def test_overlap_fraction_gate():
    # Two shared terms but they are a small fraction of a long claim -> UNADDRESSED.
    claim = "resonant tension cycling deepens reasoning novelty depth"
    r = ground_claim(claim, ["resonant tension appeared once in an unrelated note"])
    assert r.verdict is SemanticVerdict.UNADDRESSED


def test_stopwords_cannot_manufacture_support():
    r = ground_claim("it is what it is and that is that",
                     ["this is the way it is and that is how"])
    assert r.verdict is SemanticVerdict.UNADDRESSED


def test_thin_claim_is_unaddressed():
    assert ground_claim("cats", ["cats everywhere"]).verdict is SemanticVerdict.UNADDRESSED
    assert ground_claim("", ["anything"]).verdict is SemanticVerdict.UNADDRESSED


def test_accepts_cocoon_dicts_and_reports_source_id():
    ev = [{"id": "c1", "response": "emergent boundary walking across the quantum web"}]
    r = ground_claim("quantum boundary walking", ev)
    assert r.verdict is SemanticVerdict.SUPPORTED_BY_EVIDENCE
    assert r.evidence[0]["source_id"] == "c1"


class _FakeMemory:
    def __init__(self, rows):
        self._rows = rows
    def recall_relevant(self, query, max_results=5, min_importance=0):
        return self._rows


class _BrokenMemory:
    def recall_relevant(self, *a, **k):
        raise RuntimeError("db down")


def test_via_memory_grounds_retrieved_rows():
    mem = _FakeMemory([{"id": "c9", "response": "emergent boundary walking on the quantum web"}])
    r = ground_claim_via_memory("quantum boundary walking", mem)
    assert r.verdict is SemanticVerdict.SUPPORTED_BY_EVIDENCE


def test_via_memory_retrieval_failure_is_unaddressed():
    r = ground_claim_via_memory("quantum boundary walking", _BrokenMemory())
    assert r.verdict is SemanticVerdict.UNADDRESSED
    assert r.support_score == 0.0


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
