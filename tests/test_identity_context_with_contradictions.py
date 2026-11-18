"""get_identity_context must survive a recorded contradiction.

Until 2026-11-18 the contradiction block read an undefined `now`. Contradictions
are persisted, so after the first one was ever recorded, every call raised
NameError and the server injected no identity context at all.

Uses a temp identity_dir; the real store under data/identities/ is never opened.
"""
import time

from inference.identity_anchor import IdentityAnchor


def _anchor(tmp_path, confidence):
    a = IdentityAnchor(identity_dir=tmp_path / "identities")
    a.identities["jonathan"].recognition_confidence = confidence
    return a


def test_context_still_builds_after_a_contradiction(tmp_path):
    a = _anchor(tmp_path, 0.9)
    a.identities["jonathan"].contradictions.append({"timestamp": time.time(), "detail": "x"})
    ctx = a.get_identity_context("jonathan")
    assert "IDENTITY CONTEXT" in ctx
    assert "CAUTION" in ctx                      # the warning it exists to show


def test_an_old_contradiction_does_not_warn(tmp_path):
    a = _anchor(tmp_path, 0.9)
    a.identities["jonathan"].contradictions.append({"timestamp": time.time() - 7200})
    ctx = a.get_identity_context("jonathan")
    assert "IDENTITY CONTEXT" in ctx and "CAUTION" not in ctx
