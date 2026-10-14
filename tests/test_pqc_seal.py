"""Post-quantum sealing on the cocoon write path (AEGIS Layer 4).

Uses a throwaway key directory: no real keys are created or read.
"""
import json

import pytest

oqs = pytest.importorskip("oqs")

from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3
from reasoning_forge.cognition_cocooner import CognitionCocooner


@pytest.fixture
def sealed(tmp_path, monkeypatch):
    from Protection_Layer.aegis_layer4_complete import PQCShield
    shield = PQCShield(key_dir=str(tmp_path / "keys"))
    assert shield.initialize()
    monkeypatch.setattr(CognitionCocooner, "_shield", classmethod(lambda cls: shield))
    return CognitionCocooner(storage_path=str(tmp_path / "cocoons"))


def _write(c):
    v3 = build_cocoon_v3(query="what is water", response_text="Water is H2O, a polar molecule.",
                         response_summary="Water is H2O.", execution_path="adapter_lightweight",
                         model_inference_invoked=True, active_perspectives=["newton"])
    return c.wrap_reasoning(query="what is water", response="Water is H2O, a polar molecule.",
                            adapter="newton", v3_cocoon=v3)


def _read(c, cid):
    return json.loads((c.storage_path / f"{cid}.json").read_text(encoding="utf-8"))


def test_a_written_cocoon_carries_a_seal_that_verifies(sealed):
    cid = _write(sealed)
    p = _read(sealed, cid)
    assert p["_pqc_seal"]["alg"] in ("ML-KEM-768", "Kyber768")
    assert sealed.verify_seal(cid) is True


def test_tampering_breaks_the_seal(sealed):
    cid = _write(sealed)
    path = sealed.storage_path / f"{cid}.json"
    p = json.loads(path.read_text(encoding="utf-8"))
    p["wrapped"]["response"] = "Water is poison."
    path.write_text(json.dumps(p), encoding="utf-8")
    assert sealed.verify_seal(cid) is False


def test_fill_measured_reseals_what_it_changes(sealed):
    cid = _write(sealed)
    assert sealed.fill_measured(cid, eta_score=0.9, psi_r_measured=-0.4)
    assert _read(sealed, cid)["v3"]["eta_score"] == 0.9
    assert sealed.verify_seal(cid) is True


def test_unsealed_is_none_not_false(tmp_path, monkeypatch):
    monkeypatch.setattr(CognitionCocooner, "_shield", classmethod(lambda cls: None))
    c = CognitionCocooner(storage_path=str(tmp_path / "c"))
    cid = _write(c)
    assert "_pqc_seal" not in _read(c, cid)
    assert c.verify_seal(cid) is None


def test_a_failing_seal_still_writes_the_cocoon(tmp_path, monkeypatch):
    class Boom:
        def seal_dict(self, r):
            raise RuntimeError("no")
    monkeypatch.setattr(CognitionCocooner, "_shield", classmethod(lambda cls: Boom()))
    c = CognitionCocooner(storage_path=str(tmp_path / "c"))
    cid = _write(c)
    assert cid and "_pqc_seal" not in _read(c, cid)
    assert "seal failed" in (CognitionCocooner.pqc_error or "")
