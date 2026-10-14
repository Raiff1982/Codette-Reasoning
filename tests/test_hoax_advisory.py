"""HoaxFilter is wired advisory: it records, it never blocks, and stores no text."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inference"))

from inference.codette_forge_bridge import CodetteForgeBridge


class _Stub(CodetteForgeBridge):
    def __init__(self):                       # no model, no forge
        self.forge = None


HOAX = ("Recently declassified: experts say a shocking, astonishing 4,000 mile "
        "structure was reportedly found on Saturn's moon.")


def _advise(text):
    res = {"response": text, "complexity": "MEDIUM"}
    _Stub()._run_output_advisory(res, "q")
    return res


def test_ordinary_answer_is_low_and_unforced():
    r = _advise("Water is two hydrogen atoms bonded to one oxygen atom.")
    a = r["hoax_advisory"]
    assert a["level"] == "low" and a["enforced"] is False
    assert r["response"].startswith("Water is")       # untouched


def test_sensational_scale_claim_is_flagged_but_not_changed():
    r = _advise(HOAX)
    a = r["hoax_advisory"]
    assert a["level"] in ("elevated", "high") and a["enforced"] is False
    assert r["response"] == HOAX                       # advisory: nothing altered


def test_the_record_holds_scores_and_counts_never_text():
    blob = json.dumps(_advise(HOAX)["hoax_advisory"])
    for word in ("Saturn", "declassified", "shocking", "structure"):
        assert word not in blob
