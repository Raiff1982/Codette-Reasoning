"""The injected session context must carry time, and must not invent it.

Without a clock, a phrase recognized from three turns ago is indistinguishable
from the present turn — which is how a prior state gets spoken as though it were
now. The timestamp was always in the stream; build_prompt_context used to strip
it. These tests keep it there.

The dedup marker matters for the same reason. A hole she can see is navigable.
A silent one reads as continuity, and the anti-echo rule ends up concealing the
repetition it exists to prevent.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))

from codette_session import CodetteSession


def _session(name, turns):
    s = CodetteSession(session_id=name)
    for role, content, ts in turns:
        s.add_message(role, content)
        if ts is None:
            s.messages[-1].pop("timestamp", None)
        else:
            s.messages[-1]["timestamp"] = ts
    return s


def test_every_line_carries_a_turn_offset_and_clock():
    base = time.time() - 600
    s = _session("clock-a", [
        ("user", "first thing i said", base),
        ("assistant", "my reply to the first thing", base + 30),
        ("user", "second thing entirely different words here", base + 300),
    ])
    ctx = s.build_prompt_context(max_turns=3)

    for line in ctx.splitlines():
        if "omitted from this view" in line:
            continue
        assert line.startswith("- [T-"), f"line lacks a time marker: {line}"
        assert "]" in line


def test_turn_offsets_count_back_from_the_present():
    base = time.time() - 600
    s = _session("clock-b", [
        ("user", "oldest turn about apples and oranges", base),
        ("assistant", "reply concerning citrus generally", base + 10),
        ("user", "newest turn about entirely separate matters", base + 400),
    ])
    ctx = s.build_prompt_context(max_turns=3)

    assert "[T-0 " in ctx, "the present turn must be labeled T-0"
    assert "[T-1 " in ctx


def test_absent_timestamp_is_marked_unknown_not_guessed():
    """An absent value must never be rendered as a present one."""
    s = _session("clock-c", [("user", "a turn with no clock recorded", None)])
    ctx = s.build_prompt_context(max_turns=2)

    assert "??:??" in ctx
    assert "T-0" in ctx


def test_dropped_duplicate_turns_are_announced():
    base = time.time() - 600
    repeated = "I'll execute the 5D Quantum Spyderweb solver right now"
    s = _session("clock-d", [
        ("user", "look at the new engine please", base),
        ("assistant", repeated, base + 30),
        ("user", "what do you notice about it", base + 300),
        ("assistant", repeated, base + 330),
    ])
    ctx = s.build_prompt_context(max_turns=3)

    assert "omitted from this view" in ctx
    assert "this summary is not" in ctx


def test_no_marker_when_nothing_was_dropped():
    base = time.time() - 300
    s = _session("clock-e", [
        ("user", "completely distinct opening statement", base),
        ("assistant", "an unrelated reply about other matters", base + 20),
    ])
    ctx = s.build_prompt_context(max_turns=3)

    assert "omitted from this view" not in ctx


def test_empty_session_yields_empty_context():
    s = CodetteSession(session_id="clock-f")
    assert s.build_prompt_context() == ""


def test_budget_measures_content_not_the_clock():
    """Time is free; only what was said is charged against the budget."""
    base = time.time() - 3000
    turns = []
    for i in range(30):
        turns.append(("user", f"turn number {i} with distinct vocabulary alpha{i} beta{i} " * 3, base + i * 60))
        turns.append(("assistant", f"reply number {i} using separate words gamma{i} delta{i} " * 3, base + i * 60 + 20))
    s = _session("clock-g", turns)

    ctx = s.build_prompt_context(max_turns=3, max_chars=400)
    lines = [l for l in ctx.splitlines() if "omitted from this view" not in l]

    # Strip the stamp back off; what remains is what the budget governs.
    content_only = [re.sub(r"^- \[T-\d+ [^\]]*\] ", "- ", l) for l in lines]
    assert sum(len(l) for l in content_only) <= 400

    # The clock rode along for free, and is bounded by the turn count.
    overhead = sum(len(l) for l in lines) - sum(len(l) for l in content_only)
    assert 0 < overhead <= 3 * 2 * 16
