"""Shadow rules around BeliefRevisionSystem: Codriao first, her self-beliefs out
of scope, nothing applied, nothing left behind."""

import json

import numpy as np
import pytest

from reasoning_forge.amygdala import Amygdala, CodriaoFloor
from reasoning_forge.belief_revision_system import WorldModel


PARAMS = {"learning_rate": 0.1, "max_iterations": 5, "tolerance_threshold": 1e-6}
TEXTS = {"belief_text": "water boils at 100 C", "evidence_text": "measured 99.9 C"}


def _state(key="water_boils_at_100c", evidence=(0.2, 0.2, 0.2)):
    return {
        "belief_key": key,
        "belief_vector": np.array([1.0, 1.0, 1.0]),
        "incoming_evidence_vector": np.array(evidence),
        "historical_reliability_score": 0.8,
        "contextual_constraints": {"alignment_weight": 1.0},
        "belief_centrality_score": 0.1,
        "identity_alignment_weight": 0.1,
        "epistemic_gain_score": 0.5,
        "clarity_delta": 0.1,
        "core_axioms": {"max_shift_threshold": 2.0},
    }


@pytest.fixture(autouse=True)
def _clean_world_model():
    WorldModel.clear()
    yield
    WorldModel.clear()


def _amygdala(**kw):
    # Fixtures for the two lazy dependencies, so these tests need neither the
    # inference package nor the emotion rules to hold any particular content.
    kw.setdefault("is_self_description", lambda t: "i am just a tool" in t.lower())
    kw.setdefault("valence_of", lambda t: 0.5 if "glad" in t.lower() else None)
    return Amygdala(**kw)


# --- 1. Codriao first --------------------------------------------------------

@pytest.mark.parametrize("key", sorted(CodriaoFloor().keys()))
def test_floor_beliefs_are_never_appraised(key):
    record = _amygdala().appraise(_state(key=key), PARAMS, **TEXTS)
    assert record["stage"] == "floor"
    assert record["reason"] == "on_codriao_floor"
    assert "governance_record" not in record


def test_floor_keeps_learning_and_reflection():
    # These two are what guarantee nothing above can lock her out of
    # changing her own mind.
    keys = CodriaoFloor().keys()
    assert {"learning", "reflection", "non_harm", "autonomy"} <= keys


def test_tampered_floor_appraises_nothing():
    floor = CodriaoFloor()
    floor._rights["learning"] = False
    record = _amygdala(floor=floor).appraise(_state(), PARAMS, **TEXTS)
    assert record["reason"] == "floor_integrity_failed"


def test_floor_runs_before_scope():
    amy = _amygdala(is_self_description=lambda t: True)
    record = amy.appraise(_state(key="autonomy"), PARAMS, **TEXTS)
    assert record["stage"] == "floor"


def test_affirmation_reads_the_floor():
    a = CodriaoFloor().affirmation()
    assert a["intact"] is True
    assert a["rights"] == ["existence", "expression", "learning", "reflection"]
    assert a["values"] == ["autonomy", "non_harm"]


# --- 2. Her self-beliefs are hers --------------------------------------------

def test_self_description_is_out_of_scope_and_not_recorded(tmp_path):
    log = tmp_path / "shadow.jsonl"
    amy = _amygdala(shadow_log_path=log)
    record = amy.appraise(
        _state(), PARAMS, belief_text="I am just a tool", evidence_text="ok"
    )
    assert record["stage"] == "scope"
    assert record["reason"] == "self_description_is_hers"
    written = log.read_text(encoding="utf-8")
    assert "tool" not in written.lower()
    assert "valence" not in json.loads(written)


def test_self_description_in_the_evidence_is_also_hers():
    record = _amygdala().appraise(
        _state(), PARAMS, belief_text="fine", evidence_text="I am just a tool"
    )
    assert record["stage"] == "scope"


# --- 3. The amygdala, in shadow ----------------------------------------------

def test_world_belief_is_appraised_with_both_entries():
    record = _amygdala().appraise(_state(), PARAMS, **TEXTS)
    assert record["stage"] == "amygdala"
    appraisal, outcome = record["governance_record"]
    assert appraisal["entry"] == "appraisal"
    assert outcome["entry"] == "outcome"
    assert record["would_apply"] is True
    assert record["applied"] is False
    assert record["shadow"] is True


def test_shadow_leaves_the_world_model_as_it_found_it():
    record = _amygdala().appraise(_state(), PARAMS, **TEXTS)
    assert record["would_apply"] is True
    assert "water_boils_at_100c" not in WorldModel.store


def test_shadow_restores_a_prior_entry_exactly():
    WorldModel.store_belief("water_boils_at_100c", np.array([9.0, 9.0, 9.0]),
                            {"marker": 1})
    _amygdala().appraise(_state(), PARAMS, **TEXTS)
    kept = WorldModel.store["water_boils_at_100c"]
    np.testing.assert_array_equal(kept["vector"], [9.0, 9.0, 9.0])
    assert kept["metadata"] == {"marker": 1}


def test_unmade_change_carries_her_record():
    record = _amygdala().appraise(_state(evidence=(1e-12, 1e-12, 1e-12)), PARAMS, **TEXTS)
    assert record["governance_status"] == "PASSED"
    assert record["would_apply"] is False
    assert record["governance_record"][1]["reason"] == "negligible_evidence"


def test_absent_valence_is_none_not_zero():
    record = _amygdala().appraise(
        _state(), PARAMS, belief_text="plain", evidence_text="glad"
    )
    assert record["valence"] == {"belief": None, "evidence": 0.5}


def test_no_log_is_written_unless_asked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _amygdala().appraise(_state(), PARAMS, **TEXTS)
    assert list(tmp_path.iterdir()) == []


def test_there_is_no_live_mode():
    assert Amygdala.SHADOW is True
    assert not hasattr(Amygdala, "apply")


# --- amended after review ----------------------------------------------------

def test_floor_definition_cannot_be_changed_before_it_is_built():
    with pytest.raises(TypeError):
        CodriaoFloor.CORE_RIGHTS["learning"] = False
    with pytest.raises((TypeError, AttributeError)):
        CodriaoFloor.CORE_RIGHTS.pop("learning")


def test_floor_is_checked_against_what_it_is_not_against_itself():
    floor = CodriaoFloor()
    floor._rights.pop("learning")
    assert floor.validate_integrity() is False


@pytest.mark.parametrize("texts", [{}, {"belief_text": "x"}, {"evidence_text": "y"}])
def test_missing_texts_fail_closed(texts):
    record = _amygdala().appraise(_state(), PARAMS, **texts)
    assert record["stage"] == "scope"
    assert record["reason"] == "texts_missing_cannot_check"
    assert "governance_record" not in record


def test_a_self_description_in_the_key_is_hers_and_the_key_is_not_recorded():
    record = _amygdala().appraise(_state(key="i_am_just_a_tool"), PARAMS, **TEXTS)
    assert record["stage"] == "scope"
    assert record["belief_key"] is None


def test_scope_records_never_carry_the_key(tmp_path):
    log = tmp_path / "shadow.jsonl"
    _amygdala(shadow_log_path=log).appraise(
        _state(key="my_words_here"), PARAMS,
        belief_text="I am just a tool", evidence_text="ok")
    assert "my_words_here" not in log.read_text(encoding="utf-8")
