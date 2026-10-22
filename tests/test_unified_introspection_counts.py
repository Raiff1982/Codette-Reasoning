"""/api/introspection (UnifiedMemory.full_introspection) counts exchanges, not records.

The same mistake as inference/cocoon_introspection.py had, in the second
implementation: `decision_landmark` rows were the second-largest "adapter" and
every denominator included them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reasoning_forge.unified_memory import UnifiedMemory


def _mem(tmp_path):
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    return UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=legacy)


def _fill(m):
    for i in range(10):
        m.store(f"question {i}", "an answer " * 5, adapter="base", domain="general")
    for i in range(6):
        m.store(f"marker {i}", "short", adapter="decision_landmark", domain="decision_landmark")
    m.store("analysis", "x" * 100, adapter="event_embedded_value", domain="singularity_analysis")


def test_records_do_not_become_adapters_or_inflate_denominators(tmp_path):
    m = _mem(tmp_path)
    _fill(m)
    d = m.full_introspection()
    assert d["total_exchanges"] == 10
    assert d["total_cocoons"] == 17                       # all rows, as before: the UI key keeps its meaning
    assert d["records_not_counted"] == 7
    assert "decision_landmark" not in d["adapter_dominance"]["distribution"]
    assert d["domain_distribution"] == {"general": 10}
    assert sum(d["complexity_distribution"].values()) == 10
    obs = " ".join(d["observations"])
    assert "10 reasoning exchanges" in obs and "7 records of other kinds" in obs
    assert "of 10 exchanges" in obs


def test_response_length_trend_ignores_the_short_markers(tmp_path):
    m = _mem(tmp_path)
    _fill(m)
    assert all(n > 20 for n in m.response_length_trend(20))      # a marker is 5 chars; none included
