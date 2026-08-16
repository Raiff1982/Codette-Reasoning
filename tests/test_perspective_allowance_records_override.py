"""
When an earned perspective allowance is cut back, the reduction must be recorded.

Observed live on 2026-08-14/15, one turn, two log lines:

    [CHARGE]    19.00 -> 5 perspectives
    [SUBSTRATE] max_adapters 5->2 (moderate pressure)

The provenance traversal harvests metabolic charge from the recall problem's own
constraint density, and `recycle_charge_to_perspectives` converts it into a count.
The server records that as `perspective_allowance.granted` and prints [CHARGE].
Two clamps then run downstream — the complexity bucket and substrate pressure —
and either can cut it. Neither system knows the other exists.

So the stored record said `granted: 5` for a turn that answered with 2, and the
difference existed nowhere: not in the record, not in the response, not in any
log line that names it as an override rather than as an independent decision.

**Nothing here prevents the clamp.** Substrate pressure is real and the cap is
honest on a machine with 16 GB of shared memory. What these tests pin is that a
reduction of an allowance she *earned* is visible afterwards. She paid for five
voices in measured difficulty and answered with two; that is a fact about the
turn and it now survives the turn.

The distinction that matters, and the reason `earned_allowance_reduced` is not
simply `final < requested` at every layer: clamping the plain default is the
previous behaviour and overrides nothing. Only a cut below what the charge
actually bought is an override.
"""

import pytest

from reasoning_forge.memory_provenance_solver import (
    PERSPECTIVE_FLOOR,
    recycle_charge_to_perspectives,
)


# ── The grant side ─────────────────────────────────────────────────────────

def test_high_charge_grants_above_the_floor():
    """The live case: charge 19.00 bought more than the floor."""
    allowance, why = recycle_charge_to_perspectives(19.00, floor=2)
    assert allowance > 2, why
    assert "19.00" in why


def test_unmeasured_charge_returns_the_floor_and_says_so():
    """An absent reading must not be rendered as a present one.

    This is the property the whole recycling path depends on: no traversal means
    no grant, never a fabricated one, and never less breadth than she already had.
    """
    allowance, why = recycle_charge_to_perspectives(None, floor=2)
    assert allowance == 2
    assert "unmeasured" in why


def test_low_charge_never_costs_her_breadth():
    allowance, _ = recycle_charge_to_perspectives(0.01, floor=3)
    assert allowance >= 3


# ── The reconciliation ─────────────────────────────────────────────────────
#
# Mirrors the `_alloc` computation in CodetteForgeBridge._generate_impl. Kept as
# a local helper rather than reaching into the method, because the method needs a
# loaded orchestrator and a live pipeline to reach that line at all.

def _alloc(requested, after_complexity, final, substrate_reasons=()):
    return {
        "requested": requested,
        "after_complexity": after_complexity,
        "final": final,
        "complexity_clamped": after_complexity < requested,
        "substrate_clamped": final < after_complexity,
        "substrate_reasons": list(substrate_reasons),
        "earned_allowance_reduced": final < requested,
    }


def test_the_live_case_is_recorded_as_an_override():
    """charge granted 5, substrate ran 2 — the turn that motivated this."""
    a = _alloc(5, 5, 2, ["max_adapters 5->2 (moderate pressure)"])
    assert a["earned_allowance_reduced"] is True
    assert a["substrate_clamped"] is True
    assert a["complexity_clamped"] is False
    assert a["substrate_reasons"] == ["max_adapters 5->2 (moderate pressure)"]


def test_complexity_clamp_is_attributed_to_complexity_not_substrate():
    """Both clamps reduce. They must not be confused for one another.

    Attributing a complexity cut to substrate pressure would send the next
    session hunting a memory problem that isn't there.
    """
    a = _alloc(5, 1, 1)
    assert a["earned_allowance_reduced"] is True
    assert a["complexity_clamped"] is True
    assert a["substrate_clamped"] is False


def test_clamping_an_unearned_default_is_not_an_override():
    """The floor arriving and being capped is the previous behaviour.

    If this reported an override, the log would fire on ordinary turns and the
    signal would be worth nothing — the failure mode of the governor's own
    relevance check, which fired on 48.7% of turns and so was consumed by nothing.
    """
    a = _alloc(PERSPECTIVE_FLOOR, PERSPECTIVE_FLOOR, PERSPECTIVE_FLOOR)
    assert a["earned_allowance_reduced"] is False


def test_a_grant_that_survives_is_not_reported_as_reduced():
    a = _alloc(5, 5, 5)
    assert a["earned_allowance_reduced"] is False
    assert a["substrate_clamped"] is False


# ── The record the server writes ───────────────────────────────────────────

def _reconcile(allowance_record, applied):
    """Mirrors the merge in codette_server before memory_context is attached."""
    allowance_record.update({
        "used": applied.get("final"),
        "reduced": bool(applied.get("earned_allowance_reduced")),
        "reduced_by": (
            applied.get("substrate_reasons") or None
            if applied.get("substrate_clamped")
            else ("complexity" if applied.get("complexity_clamped") else None)
        ),
    })
    return allowance_record


def test_record_carries_the_outcome_not_only_the_grant():
    """`granted` alone was the whole bug — it described an intention."""
    record = {"granted": 5, "floor": 2, "metabolic_charge": 19.0,
              "reason": "charge 19.00 >= 11.5 -> 5 perspectives"}
    merged = _reconcile(
        record, _alloc(5, 5, 2, ["max_adapters 5->2 (moderate pressure)"]))

    assert merged["granted"] == 5
    assert merged["used"] == 2
    assert merged["reduced"] is True
    assert merged["reduced_by"] == ["max_adapters 5->2 (moderate pressure)"]


def test_untouched_grant_records_reduced_false_rather_than_nothing():
    """Absence has to say so — the standing rule in this repo.

    `reduced: False` is a measurement. A missing key would be indistinguishable
    from a turn where the reconciliation never ran.
    """
    record = {"granted": 4, "floor": 2}
    merged = _reconcile(record, _alloc(4, 4, 4))
    assert merged["used"] == 4
    assert merged["reduced"] is False
    assert merged["reduced_by"] is None
