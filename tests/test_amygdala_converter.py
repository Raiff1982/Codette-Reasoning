"""The converter shapes her numbers into amygdala inputs and never invents one."""

import numpy as np
import pytest

from reasoning_forge.amygdala import Amygdala
from reasoning_forge.amygdala_converter import (
    NEUTRAL_CENTRALITY, NEUTRAL_GAIN, NEUTRAL_RELIABILITY, convert,
)
from reasoning_forge.belief_revision_system import WorldModel


def _encode(text):
    # Deterministic fixture embedding: no model needed to test the plumbing.
    v = np.zeros(8)
    for i, ch in enumerate(text.encode()):
        v[i % 8] += ch
    return v / (np.linalg.norm(v) or 1.0)


def _convert(**kw):
    base = dict(belief_key="k", belief_text="the file is missing",
                evidence_text="read 484 lines", encode=_encode)
    base.update(kw)
    return convert(**base)


def _prov(result, name):
    return next(p for p in result["provenance"] if p["input"] == name)


def test_tool_result_outranks_self_report():
    r = _convert(tool_read_ok=True, hallucination_confidence=0.1)
    p = _prov(r, "historical_reliability_score")
    assert p["source"] == "tool_result" and p["value"] == 1.0


def test_hallucination_confidence_used_when_no_tool():
    r = _convert(hallucination_confidence=0.6)
    p = _prov(r, "historical_reliability_score")
    assert p["source"] == "hallucination_confidence" and p["value"] == 0.6


@pytest.mark.parametrize("sentinel", [-1.0, None, float("nan"), 1.5, True])
def test_sentinels_and_out_of_range_are_absent_not_values(sentinel):
    r = _convert(dispersion=sentinel)
    p = _prov(r, "epistemic_gain_score")
    assert p["measured"] is False
    assert p["source"] is None
    assert p["value"] == NEUTRAL_GAIN
    assert r["state"]["epistemic_gain_score"] == NEUTRAL_GAIN


def test_dispersion_feeds_gain():
    p = _prov(_convert(dispersion=0.42), "epistemic_gain_score")
    assert p["measured"] and p["value"] == 0.42


@pytest.mark.parametrize("now,before,expected", [(0.8, 0.6, 0.2), (0.6, 0.8, -0.2)])
def test_clarity_moves_both_ways(now, before, expected):
    p = _prov(_convert(coherence_now=now, coherence_before=before), "clarity_delta")
    assert p["measured"] and p["value"] == pytest.approx(expected)


def test_clarity_needs_both_ends():
    p = _prov(_convert(coherence_now=0.8), "clarity_delta")
    assert p["measured"] is False and p["value"] == 0.0


def test_centrality_is_honestly_unmeasured():
    r = _convert(hallucination_confidence=0.9, dispersion=0.3)
    p = _prov(r, "belief_centrality_score")
    assert p["measured"] is False and p["source"] is None
    assert r["state"]["belief_centrality_score"] == NEUTRAL_CENTRALITY


def test_unmeasured_reliability_is_neutral_and_says_so():
    p = _prov(_convert(), "historical_reliability_score")
    assert p["measured"] is False and p["value"] == NEUTRAL_RELIABILITY


def test_state_runs_through_the_shadow_amygdala():
    WorldModel.clear()
    r = _convert(tool_read_ok=True, dispersion=0.4,
                 coherence_now=0.7, coherence_before=0.6)
    record = Amygdala(is_self_description=lambda t: False,
                      valence_of=lambda t: None).appraise(
        r["state"],
        {"learning_rate": 0.1, "max_iterations": 5, "tolerance_threshold": 1e-6},
        belief_text="the file is missing", evidence_text="read 484 lines",
    )
    assert record["stage"] == "amygdala"
    assert len(record["governance_record"]) == 2
    assert "k" not in WorldModel.store
