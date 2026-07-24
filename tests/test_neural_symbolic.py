"""Tests for NeuralSymbolicProcessor — the real body of Jonathan's 2025 interface.

The point: the archived placeholder returned "Derived logical constructs from '{query}'"
for ANY input — a string announcing work it never did. This one must report a REAL,
honest result, and in particular must NOT claim to have derived anything from a
thought it couldn't actually check.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.neural_symbolic import NeuralSymbolicProcessor
from reasoning_forge.grounding_bridge import FLAGGED, SUPPORTED, UNGROUNDED

nsp = NeuralSymbolicProcessor()


def test_interface_preserved_returns_str():
    # Same signature the 2025 archive defined: process_query(query) -> str.
    out = nsp.process_query("anything")
    assert isinstance(out, str)

def test_false_claim_is_flagged_not_announced():
    out = nsp.process_query("the model concluded 2 + 2 = 5")
    assert "FLAGGED" in out

def test_true_claim_supported():
    out = nsp.process_query("the model showed 6 * 7 = 42")
    assert "SUPPORTED" in out

def test_qualitative_is_ungrounded_not_fake_derivation():
    # The archived placeholder would have claimed to "derive logical constructs".
    # The real one must admit it has nothing to check.
    out = nsp.process_query("empathy and rigor meet at the boundary of understanding")
    assert "UNGROUNDED" in out
    assert "Derived logical constructs" not in out  # the old lie must be gone

def test_grounds_neural_output_when_provided():
    # Query is a question; the neural OUTPUT carries the checkable claim.
    r = nsp.process("What is 3 squared?", neural_output="Three squared is 9, so 3**2 = 9.")
    assert r.status == SUPPORTED

def test_process_returns_structured_report():
    r = nsp.process("check", neural_output="Given a > b, b > c, and yet c > a.")
    assert r.status == FLAGGED  # circular ordering caught by the z3 consistency check


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
