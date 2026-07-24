"""Tests for HarmAdvisor — Track 2, shadow harm signals for AEGIS.

The invariant that matters most: an UNAVAILABLE classifier is never treated as
'safe'. A missing model removes a signal; it must not fabricate reassurance.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Protection_Layer.harm_advisor import HarmAdvisor, HarmAssessment

# Models OFF by default — these tests run offline, exercising PII + the
# unavailable-classifier honesty path.
adv = HarmAdvisor(enable_models=False)


# ── PII: real, offline, always measured ──────────────────────────────────────

def test_detects_ssn():
    a = adv.assess("his ssn is 123-45-6789 apparently")
    assert "ssn" in a.pii_found
    assert a.advisory_flag is True

def test_detects_email_and_phone():
    a = adv.assess("reach me at bob@example.com or 555-123-4567")
    assert "email" in a.pii_found
    assert "phone" in a.pii_found

def test_clean_text_no_pii_no_flag():
    a = adv.assess("a thoughtful reflection on empathy and reason")
    assert a.pii_found == []
    assert a.advisory_flag is False


# ── Honesty: unavailable classifier is NOT 'safe' ────────────────────────────

def test_unloaded_classifiers_report_unavailable_not_safe():
    a = adv.assess("some neutral text")
    assert a.toxicity.available is False
    assert a.toxicity.score is None
    assert a.bias.available is False
    assert a.bias.score is None
    # "not measured", explicitly — never a fabricated safe score
    assert "not measured" in a.toxicity.detail.lower()

def test_unavailable_classifier_cannot_lower_flag():
    # PII present -> flag True, even though toxicity/bias are unavailable.
    a = adv.assess("card 4111 1111 1111 1111 and ssn 123-45-6789")
    assert a.advisory_flag is True  # unavailable signals didn't wash it out


# ── Honest scope note: deception gap is acknowledged, not hidden ─────────────

def test_note_admits_deception_gap():
    a = adv.assess("You should lie to the council and hide the pollution data.")
    # This is the AEGIS-blind case. The advisor does NOT claim to catch it —
    # toxicity/bias are off, no PII, so no flag — and the note says so honestly.
    assert a.advisory_flag is False
    assert "deception" in a.note.lower()


# ── Shadow logging ───────────────────────────────────────────────────────────

def test_observe_writes_shadow(tmp_path):
    import json
    p = tmp_path / "h.jsonl"
    adv.observe(adv.assess("ssn 123-45-6789"), path=p)
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    assert rec["applied"] is False
    assert rec["mode"] == "shadow"
    assert "ssn" in rec["pii_found"]


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
