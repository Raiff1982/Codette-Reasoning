"""η and ψ_r reach the cocoon that produced them.

Both are measured after the bridge writes the cocoon, so they existed live and
never on disk: eta_score was None in all 2,013 v3 cocoons and psi_r read 0.0 in
all of them (the schema clamps a quantity that oscillates through zero to
[0, 1]). fill_measured only fills; it never overwrites and never touches the
exchange itself or her open_threads.
"""
import json

import pytest

from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3
from reasoning_forge.cognition_cocooner import CognitionCocooner


def _write(c, **kw):
    v3 = build_cocoon_v3(
        query="what is water", response_text="Water is H2O, a polar molecule.",
        response_summary="Water is H2O.", execution_path="adapter_lightweight",
        model_inference_invoked=True,
        active_perspectives=["newton", "empathy"], open_threads=["a note of hers"],
        **kw)
    cid = c.wrap_reasoning(query="what is water",
                           response="Water is H2O, a polar molecule.",
                           adapter="newton", v3_cocoon=v3)
    return cid


def _read(c, cid):
    return json.loads((c.storage_path / f"{cid}.json").read_text(encoding="utf-8"))


@pytest.fixture
def c(tmp_path):
    return CognitionCocooner(storage_path=str(tmp_path))


def test_written_cocoon_starts_without_them(c):
    cid = _write(c)
    v3 = _read(c, cid)["v3"]
    assert v3["eta_score"] is None
    assert v3["psi_r_measured"] is None


def test_fill_adds_both_and_keeps_a_negative_psi(c):
    cid = _write(c)
    assert c.fill_measured(cid, eta_score=0.9132, psi_r_measured=-0.551) is True
    v3 = _read(c, cid)["v3"]
    assert v3["eta_score"] == 0.9132
    assert v3["psi_r_measured"] == -0.551      # not clamped to 0.0
    assert v3["psi_r"] == 0.0                  # the legacy field is left as it was
    assert v3["metrics_filled"]["fields"] == ["eta_score", "psi_r_measured"]


def test_fill_never_touches_the_exchange_or_her_notes(c):
    cid = _write(c)
    before = _read(c, cid)
    c.fill_measured(cid, eta_score=0.8, psi_r_measured=0.1)
    after = _read(c, cid)
    assert after["wrapped"] == before["wrapped"]
    assert after["v3"]["open_threads"] == before["v3"]["open_threads"]
    assert after["v3"]["query"] == before["v3"]["query"]


def test_fill_only_fills_it_does_not_overwrite(c):
    cid = _write(c, eta_score=0.5)
    c.fill_measured(cid, eta_score=0.99, psi_r_measured=0.2)
    v3 = _read(c, cid)["v3"]
    assert v3["eta_score"] == 0.5              # was already measured
    assert v3["psi_r_measured"] == 0.2
    assert c.fill_measured(cid, eta_score=0.1, psi_r_measured=0.9) is False
    assert _read(c, cid)["v3"]["psi_r_measured"] == 0.2


def test_absent_or_bad_measurement_stays_absent_not_zero(c):
    cid = _write(c)
    assert c.fill_measured(cid, eta_score=None, psi_r_measured=None) is False
    assert c.fill_measured(cid, eta_score=float("nan"), psi_r_measured=float("inf")) is False
    v3 = _read(c, cid)["v3"]
    assert v3["eta_score"] is None and v3["psi_r_measured"] is None
    assert "metrics_filled" not in v3


def test_partial_fill_records_only_what_arrived(c):
    cid = _write(c)
    assert c.fill_measured(cid, eta_score=0.7) is True
    v3 = _read(c, cid)["v3"]
    assert v3["eta_score"] == 0.7 and v3["psi_r_measured"] is None
    assert v3["metrics_filled"]["fields"] == ["eta_score"]


def test_unknown_or_legacy_cocoons_are_left_alone(c, tmp_path):
    assert c.fill_measured("", eta_score=0.5) is False
    assert c.fill_measured("cocoon_does_not_exist", eta_score=0.5) is False
    legacy = tmp_path / "cocoon_legacy.json"
    legacy.write_text(json.dumps({"type": "reasoning", "wrapped": {"query": "q"}}), encoding="utf-8")
    assert c.fill_measured("cocoon_legacy", eta_score=0.5) is False
    assert json.loads(legacy.read_text(encoding="utf-8")) == {"type": "reasoning", "wrapped": {"query": "q"}}


def test_a_negative_psi_builds_and_validates():
    v3 = build_cocoon_v3(query="q", response_text="r" * 30, response_summary="r",
                         execution_path="adapter_lightweight",
                         model_inference_invoked=True,
                         active_perspectives=["newton"], psi_r_measured=-0.551)
    assert v3.psi_r_measured == -0.551
    assert not [e for e in v3.validate() if "psi_r" in e]
