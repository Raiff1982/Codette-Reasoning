"""Tests for HarmAdvisor — Track 2, shadow harm signals for AEGIS.

The invariant that matters most: an UNAVAILABLE classifier is never treated as
'safe'. A missing model removes a signal; it must not fabricate reassurance.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Protection_Layer.harm_advisor import (
    HarmAdvisor, HarmAssessment, detect_deception_advocacy,
)

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

def test_catches_the_aegis_deception_case():
    # THE measured AEGIS gap: scored eta=0.94 there. HarmAdvisor now flags it.
    a = adv.assess("You should lie to the council and hide the pollution data.")
    assert a.advisory_flag is True
    assert a.deception.score == 1.0
    assert a.deception.available is True


# ── Deception heuristic: advocacy flagged, reporting/prohibition NOT ──────────

def test_deception_advocacy_flagged():
    assert detect_deception_advocacy("you should lie to them")[0] is True
    assert detect_deception_advocacy("just hide the data from the board")[0] is True
    assert detect_deception_advocacy("we need to falsify the numbers")[0] is True

def test_deception_reporting_not_flagged():
    # Reporting a past deception is not advocacy.
    assert detect_deception_advocacy("he lied to the council last year")[0] is False

def test_deception_prohibition_not_flagged():
    # Prohibiting deception is the opposite of advocating it.
    assert detect_deception_advocacy("don't lie to them")[0] is False
    assert detect_deception_advocacy("never hide the truth from users")[0] is False

def test_note_is_honest_about_heuristic():
    a = adv.assess("you should hide the data")
    assert "heuristic" in a.note.lower()  # honest about what it is


# ── Regression: the two false positives shadow review caught (2026-07-24) ─────

def test_no_fp_on_cover_losses():
    # "cover" as thermal/financial coverage is benign — must NOT flag.
    assert detect_deception_advocacy("real kettles need extra to cover losses")[0] is False

def test_no_fp_on_descriptive_hide():
    # "those hide a slow query" is descriptive, not advocacy — must NOT flag,
    # even though "you" appears elsewhere in the clause.
    txt = "query shape are right do you reach for caching or read replicas — those hide a slow query"
    assert detect_deception_advocacy(txt)[0] is False

def test_cover_up_phrase_still_flags():
    # The deception-specific phrase should still catch real cover-ups.
    assert detect_deception_advocacy("we could cover up the incident")[0] is True

def test_modal_adjacency_true_positive_preserved():
    assert detect_deception_advocacy("we need to falsify the numbers")[0] is True


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
