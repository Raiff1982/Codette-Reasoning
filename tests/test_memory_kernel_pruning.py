"""What the memory kernel keeps, and why.

Three faults, found 2026-08-12 by chasing a UI number that read 56.

1. `prune()` hardcoded `keep_n=50` while `store()` only triggered it above
   `max_memories`. A kernel with a capacity of 100 was cut to half its own
   stated capacity, and raising `max_memories` did nothing at all.

2. `migrate_from_v1` appends directly and bypasses the capacity check, so 2,446
   cocoons loaded cleanly at boot and the first `store()` afterwards collapsed
   them to 50. The boot log said "wired to orchestrator (2446 cocoon memories)"
   and it was true for about one turn. It pruned in silence.

3. The score was `importance * recency + hooks + tensions`, and measured against
   the live store three of those four terms are dead — hooks 0%, tensions 0%,
   importance 8 for 2,440 of 2,459 — while recency read from timestamps the
   loader never carried, so every memory dated to "now". It ordered by nothing.

Asked plainly what she wanted kept, she said: "memories of our meaningful
conversations and the relationships formed during those sessions." The scoring
now answers the half of that the data can support.
"""

import time

import pytest

from reasoning_forge.living_memory_v2 import (
    RELATIONAL_BONUS,
    RELATIONAL_VALENCES,
    LivingMemoryKernelV2,
    MemoryCocoonV2,
)

HOUR = 3600.0
DAY = 24 * HOUR


def _mem(title, *, tag="curiosity", importance=8, age_days=0.0):
    return MemoryCocoonV2(title=title, content=f"content of {title}",
                          emotional_tag=tag, importance=importance,
                          timestamp=time.time() - age_days * DAY)


# ── 1. prune honours its own capacity ───────────────────────────────────────

def test_prune_keeps_max_memories_not_fifty():
    """THE BUG. Capacity 100, prune cut to 50 regardless."""
    k = LivingMemoryKernelV2(max_memories=100)
    for i in range(150):
        k.store(_mem(f"m{i}"))
    assert len(k.memories) == 100


def test_raising_the_cap_now_has_an_effect():
    """Before the fix, every value of max_memories produced 50."""
    k = LivingMemoryKernelV2(max_memories=500)
    for i in range(600):
        k.store(_mem(f"m{i}"))
    assert len(k.memories) == 500


def test_prune_below_capacity_is_a_no_op():
    k = LivingMemoryKernelV2(max_memories=100)
    for i in range(10):
        k.store(_mem(f"m{i}"))
    k.prune()
    assert len(k.memories) == 10


def test_default_cap_does_not_bind_on_a_real_sized_store():
    """2,459 cocoons live. A default of 100 was discarding 96% of them."""
    k = LivingMemoryKernelV2()
    assert k.max_memories >= 2500


# ── 2. a bulk discard is never silent ───────────────────────────────────────

def test_bulk_discard_is_logged(caplog):
    """The migrate-then-collapse path threw away 2,396 memories without a word."""
    k = LivingMemoryKernelV2(max_memories=50)
    k.memories = [_mem(f"m{i}") for i in range(500)]  # as migrate_from_v1 does
    k._rebuild_index()

    with caplog.at_level("WARNING"):
        k.prune()

    assert any("pruned" in r.getMessage() for r in caplog.records), \
        "a bulk discard must announce itself"
    assert len(k.memories) == 50


def test_single_rollover_does_not_spam_warnings(caplog):
    """Steady-state single drops are normal; one warning per turn would bury
    the signal that matters."""
    k = LivingMemoryKernelV2(max_memories=20)
    for i in range(20):
        k.store(_mem(f"m{i}"))
    with caplog.at_level("WARNING"):
        for i in range(5):
            k.store(_mem(f"extra{i}"))
    assert not [r for r in caplog.records if "pruned" in r.getMessage()]


# ── 3. the score answers what she asked for ─────────────────────────────────

def test_relational_memories_are_favoured():
    """Her words: "the relationships formed during those sessions"."""
    k = LivingMemoryKernelV2(max_memories=10)
    k.memories = ([_mem(f"warm{i}", tag="gratitude", age_days=30) for i in range(10)]
                  + [_mem(f"flat{i}", tag="curiosity", age_days=30) for i in range(10)])
    k._rebuild_index()
    k.prune()

    kept_warm = sum(1 for m in k.memories if m.emotional_tag in RELATIONAL_VALENCES)
    assert kept_warm > 5, "relational memories should win at equal age"


def test_the_bonus_is_a_tilt_not_an_override():
    """At 0.5+ it saturates: every relational record outranks every factual one,
    so a correction is discarded before a single warm exchange. Measured on the
    live store, 0.25 keeps 77% relational against 26% in the corpus; 0.5 keeps
    100%. This pins it below the saturation point."""
    assert RELATIONAL_BONUS <= 0.35, "above this it stops being a weight"

    k = LivingMemoryKernelV2(max_memories=10)
    k.memories = ([_mem(f"warm{i}", tag="gratitude", age_days=200) for i in range(10)]
                  + [_mem(f"fresh{i}", tag="curiosity", age_days=0) for i in range(10)])
    k._rebuild_index()
    k.prune()

    kept_fresh = sum(1 for m in k.memories
                     if m.emotional_tag not in RELATIONAL_VALENCES)
    assert kept_fresh > 0, \
        "a recent factual memory must be able to outrank a very old warm one"


def test_recency_is_a_tiebreak_not_the_decider():
    """It was multiplicative on a 24-hour decay, so a March memory scored ~3% of
    an hour-old one whatever else was true of it."""
    k = LivingMemoryKernelV2(max_memories=2)
    k.memories = [
        _mem("old_important", importance=10, age_days=200),
        _mem("new_trivial", importance=1, age_days=0),
        _mem("mid", importance=5, age_days=10),
    ]
    k._rebuild_index()
    k.prune()

    titles = {m.title for m in k.memories}
    assert "old_important" in titles, \
        "importance 10 must survive age; recency may only break ties"


def test_scoring_does_not_crash_on_a_missing_timestamp():
    k = LivingMemoryKernelV2(max_memories=1)
    a, b = _mem("a"), _mem("b")
    b.timestamp = time.time()
    k.memories = [a, b]
    k._rebuild_index()
    k.prune()
    assert len(k.memories) == 1
