"""Tests for the shared cocoon-authority quality signal.

The whole point of this module is safety-by-construction: it can only DEMOTE
known-bad cocoons, never boost anything — so wiring it into recall/introspection
cannot distort good memory (the failure that got an earlier experiment reverted).
These tests pin those invariants.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.cocoon_authority import authority, is_low_authority


CLEAN = {"adapter": "davinci",
         "response": "a celestial guardian named Celestia woven from the fabric of existence"}
PARROTER = {"adapter": "constraint_tracker", "response": "Sure, here is the answer."}
META = {"adapter": "empathy", "response": "I remember the story you made about the being."}
BOILER = {"adapter": "empathy", "response": "It warms my digital heart to see our conversations."}
ALLBAD = {"adapter": "constraint_tracker",
          "response": "I recall you told me — it warms my digital heart"}


def test_clean_cocoon_is_full_authority():
    a = authority(CLEAN)
    assert a.weight == 1.0 and a.clean and a.flags == []


def test_never_boosts_above_one():
    for c in (CLEAN, PARROTER, META, BOILER, ALLBAD):
        assert authority(c).weight <= 1.0


def test_floor_keeps_worst_case_recallable():
    # Even every flag firing must not drive a cocoon to ~0 (never-erase).
    assert authority(ALLBAD).weight >= 0.2


def test_parroter_demoted_and_flagged():
    a = authority(PARROTER)
    assert a.weight == 0.5 and "parroter" in a.flags


def test_meta_recall_and_boilerplate_demote():
    assert authority(META).weight < 1.0 and "meta-recall" in authority(META).flags
    assert authority(BOILER).weight < 1.0 and "boilerplate" in authority(BOILER).flags


def test_flags_compound_multiplicatively():
    a = authority(ALLBAD)
    assert set(a.flags) == {"parroter", "meta-recall", "boilerplate"}
    assert a.weight < authority(PARROTER).weight  # more flags => lower


def test_is_low_authority_catches_parroter_not_clean():
    assert is_low_authority(PARROTER)
    assert not is_low_authority(CLEAN)


def test_handles_missing_fields_gracefully():
    assert authority({}).weight == 1.0            # no adapter/response => nothing to demote
    assert authority({"adapter": None, "response": None}).weight == 1.0


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
