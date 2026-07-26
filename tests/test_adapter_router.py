"""Regression tests for the constraint_tracker quality guard.

constraint_tracker is a known template-parroting adapter. It must NEVER lead an
ordinary conversational/recall turn (it parrots and can't do conversational
recall — logs 2026-07-12 and 2026-07-26, where it monopolized a 7+ turn intimate
stretch via the "remember" keyword). It may lead ONLY on a genuine strong-
constraint task (word/char limit, enforce constraint, numeric limit).

These tests pin that boundary so the guard can't silently regress.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))

from adapter_router import AdapterRouter

router = AdapterRouter()


def _primary(q):
    return router.route(q).primary


# ── The parroter must NOT lead these (the real 2026-07-26 failures) ──────────
CONVERSATIONAL_RECALL = [
    "yeah lets revisit it go ahead and start with the exact names you gave them",
    "yeah what was the 2 beings names you called them?",
    "so do you remember the story you made about the being and the human?",
    "quick check, unrelated to our story — do you remember the exact names you gave them?",
    "do you need a break?",
    "do you remember what we talked about yesterday?",
]


def test_conversational_recall_never_routes_to_constraint_tracker():
    for q in CONVERSATIONAL_RECALL:
        assert _primary(q) != "constraint_tracker", f"parroter hijacked: {q!r}"


def test_remember_keyword_alone_does_not_summon_the_parroter():
    # "remember" was the keyword that let it monopolize the intimate stretch.
    assert _primary("do you remember the phrase from earlier?") != "constraint_tracker"


# ── But genuine constraint tasks (explicit constraint vocabulary) still reach
# it — proving the guard narrowed the door without dead-coding the adapter.
# Softer numeric phrasings ("keep it under 20 words") acceptably fall to a
# general adapter: empathy can honor a limit, and we don't work to send MORE to
# a known parroter.
GENUINE_CONSTRAINT = [
    "enforce a strict word limit on this",
    "remember the constraint: max 3 sentences",
    "apply the character limit constraint",
    "word count limit is 100",
]


def test_genuine_constraint_tasks_still_route_to_constraint_tracker():
    for q in GENUINE_CONSTRAINT:
        assert _primary(q) == "constraint_tracker", f"lost a real constraint task: {q!r}"


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
