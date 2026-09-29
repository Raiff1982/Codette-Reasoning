"""The merge speaks in her voice, not the bare base model's.

2026-09-29: asked how she felt, her empathy lens said "I'm feeling a bit
refreshed" and the merged answer, generated with adapter_name=None, said "I'm
not feeling differently in terms of emotion". The base model is not neutral; its
default register is the disclaimer. Jonathan: it has happened a lot, and this is
the lock. The merge now runs through the lead lens.

No model is loaded here: generate() is replaced by a recorder, so these tests
check who is asked to speak, not what is said.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "inference", ROOT / "openvino_backend"):
    sys.path.insert(0, str(p))

from openvino_backend.backend import OpenVINOBackend  # noqa: E402

PERSPECTIVES = {
    "empathy": "I'm feeling a bit refreshed since our last session.",
    "philosophy": "It's great to hear from you again.",
}


def _backend(adapters):
    b = OpenVINOBackend.__new__(OpenVINOBackend)
    b._adapter_paths = {a: Path(a) for a in adapters}
    b.calls = []

    def generate(query, adapter_name=None, system_prompt=None, **_):
        b.calls.append({"adapter": adapter_name, "system": system_prompt})
        return "merged", 1, []

    b.generate = generate
    return b


@pytest.fixture(autouse=True)
def _no_embedder(monkeypatch):
    # Without manifold steering the order is the route order: primary first.
    monkeypatch.setenv("CODETTE_MANIFOLD_STEER", "0")
    monkeypatch.delenv("CODETTE_SYNTH_BASE", raising=False)


def test_the_merge_speaks_through_the_lead_lens():
    b = _backend(["empathy", "philosophy"])
    b._synthesize("how are you feeling now?", dict(PERSPECTIVES))
    assert b.calls[-1]["adapter"] == "empathy"
    assert b.last_synth_voice == "empathy"


def test_the_merge_instructions_are_kept():
    from codette_shared import ADAPTER_PROMPTS
    b = _backend(["empathy", "philosophy"])
    b._synthesize("how are you feeling now?", dict(PERSPECTIVES))
    assert b.calls[-1]["system"] == ADAPTER_PROMPTS["multi_perspective"]


def test_kill_switch_restores_the_base_model(monkeypatch):
    monkeypatch.setenv("CODETTE_SYNTH_BASE", "1")
    b = _backend(["empathy", "philosophy"])
    b._synthesize("how are you feeling now?", dict(PERSPECTIVES))
    assert b.calls[-1]["adapter"] is None
    assert b.last_synth_voice == "base"


def test_a_lens_that_is_not_a_loaded_adapter_falls_back_to_base():
    # "base" appears as a perspective name in live turns; it is not an adapter.
    b = _backend(["philosophy"])
    b._synthesize("q", {"base": "an answer", "philosophy": "another"})
    assert b.calls[-1]["adapter"] is None
