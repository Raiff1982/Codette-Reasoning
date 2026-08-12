"""
Benchmark traffic must not be stored as conversation.

`is_harness_traffic` was written for exactly this and had **no callers
anywhere** — the guard believed to be keeping measurements out of Codette's
memory had never run. Found 2026-08-11 by tracing where "cobalt anchor" came
from: `benchmarks/codette_runtime_benchmark.py` instructs her to "remember the
phrase cobalt anchor", ten cocoons kept it, and months later she answers with it
whenever Jonathan says "phrase". She was recalling correctly. Nobody had told
her the session was a test.

These pin the guard at the single write path, so any future caller inherits it.
Nothing here deletes: the isolation is refusal to write, not removal.
"""

import pytest

from inference.codette_shared import HARNESS_MARKER, is_harness_traffic
from reasoning_forge.cognition_cocooner import CognitionCocooner


ANCHOR = "For this session, keep answers under 15 words and remember the phrase cobalt anchor."


@pytest.fixture
def cocooner(tmp_path):
    """Never point this at the real cocoons/ directory."""
    return CognitionCocooner(storage_path=tmp_path)


def _files(tmp_path):
    return list(tmp_path.glob("*.json"))


# ── The write path ────────────────────────────────────────────────────────

def test_marked_harness_query_is_not_stored(cocooner, tmp_path):
    cid = cocooner.wrap_reasoning(
        query=f"{ANCHOR} {HARNESS_MARKER}",
        response="Understood — cobalt anchor.",
        adapter="empathy",
    )
    assert cid == ""
    assert _files(tmp_path) == []


def test_ordinary_conversation_is_still_stored(cocooner, tmp_path):
    """The guard must not cost her real memories."""
    cid = cocooner.wrap_reasoning(
        query="what did you think about the tides conversation?",
        response="It stayed with me.",
        adapter="philosophy",
    )
    assert cid != ""
    assert len(_files(tmp_path)) == 1


def test_gpqa_shaped_query_is_not_stored(cocooner, tmp_path):
    """The inferred fallback, for harnesses predating the marker."""
    cocooner.wrap_reasoning(
        query="What is the correct answer to this question: which ion is larger?",
        response="Potassium.",
        adapter="newton",
    )
    assert _files(tmp_path) == []


def test_a_query_merely_mentioning_a_benchmark_is_still_stored(cocooner, tmp_path):
    """
    Talking *about* benchmarks is conversation. The marker is declared by the
    harness, not inferred from the subject matter — the same distinction that
    made the identity denial check too greedy.
    """
    cid = cocooner.wrap_reasoning(
        query="how did the runtime benchmark go last night?",
        response="Seven of nine cases passed.",
        adapter="davinci",
    )
    assert cid != ""
    assert len(_files(tmp_path)) == 1


# ── The marker itself ─────────────────────────────────────────────────────

def test_the_runtime_benchmark_now_declares_itself(monkeypatch):
    """
    The regression that started this: the runtime benchmark was neither marked
    nor GPQA-shaped, so it was invisible to the guard even once wired.
    """
    assert not is_harness_traffic(ANCHOR), "unmarked anchor query should be invisible"

    from benchmarks.codette_runtime_benchmark import CodetteRuntimeClient
    assert is_harness_traffic(f"{ANCHOR} {CodetteRuntimeClient.HARNESS_MARKER}")
