"""Tests for grounding_bridge — Phase B1.

The load-bearing test: a QUALITATIVE forged thought (no arithmetic) must land as
UNGROUNDED, never SUPPORTED. Reporting "verified" for a thought nothing checked
is the exact failure this project exists to prevent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.grounding_bridge import (
    ground_text, ground_reasoning_path, observe,
    GroundingReport, FLAGGED, SUPPORTED, UNGROUNDED,
)


# A real qualitative forged thought (from cocoon_synthesizer _apply_boundary_walking).
QUALITATIVE_THOUGHT = (
    "An AI should change its thinking patterns by attending to its liminal zones "
    "— the boundaries between its cognitive modes — rather than any single metric. "
    "RATIONAL DISCOMFORT signals when change is needed; PRINCIPLED PLASTICITY "
    "governs how much change is permissible; NARRATIVE IDENTITY ensures the AI can "
    "explain WHY it changed."
)


def test_qualitative_thought_is_ungrounded_not_supported():
    # THE invariant: no checkable claim => UNGROUNDED, never SUPPORTED.
    r = ground_text(QUALITATIVE_THOUGHT, source_kind="reasoning_path")
    assert r.status == UNGROUNDED
    assert r.claims_found == 0
    assert "not a pass" in r.note.lower()

def test_thought_with_true_claim_is_supported():
    r = ground_text("The three principles combine, and note that 2 + 2 = 4 holds.")
    assert r.status == SUPPORTED
    assert r.verified == 1
    assert r.refuted == 0

def test_thought_with_false_claim_is_flagged():
    r = ground_text("This elegant bridge implies 2 + 2 = 5, therefore the pattern holds.")
    assert r.status == FLAGGED
    assert r.refuted == 1

def test_flag_wins_over_support():
    # A thought with one true and one false claim must FLAG, not SUPPORT.
    r = ground_text("Given 10 = 10 and also 3 = 4, the synthesis converges.")
    assert r.status == FLAGGED
    assert r.verified == 1
    assert r.refuted == 1

def test_ground_reasoning_path_dataclass_like():
    class FakePath:
        strategy_name = "Emergent Boundary Walking"
        steps = ["Consider the boundary.", "Note that 6 * 7 = 42 in the tally."]
        conclusion = "Therefore the liminal concept holds."
    r = ground_reasoning_path(FakePath())
    assert r.source_kind == "reasoning_path"
    assert r.source_id == "Emergent Boundary Walking"
    assert r.status == SUPPORTED  # 6*7=42 is the one checkable claim

def test_ground_reasoning_path_from_dict():
    r = ground_reasoning_path({
        "strategy_name": "Temporal Depth",
        "steps": ["Purely qualitative step about time and memory."],
        "conclusion": "A qualitative conclusion with no numbers.",
    })
    assert r.status == UNGROUNDED

def test_observe_writes_shadow(tmp_path):
    import json
    p = tmp_path / "g.jsonl"
    observe(ground_text("2 + 2 = 4"), path=p)
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    assert rec["applied"] is False
    assert rec["mode"] == "shadow"
    assert rec["record"] == "bridge_report"
    assert rec["status"] == SUPPORTED


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
