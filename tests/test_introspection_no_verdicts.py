"""Her introspection says what was counted, never what to conclude (2026-11-20).

House rule: words we author in her report reach her as her own. The adapter lines
told her "I should check if I'm over-relying on it", "I should diversify",
"well-balanced", "fair use", and the self-diagnostic said "may be over-relying".
Both implementations of the report are checked here (a fix to one is not a fix
until the other is checked), on a dominant mix and on a spread-out one.
"""
import re
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

VERDICTS = re.compile(r"should|over-rel|diversif|balanced|fair use|dominat|dominant\.|healthy|too much", re.I)
MIXES = {"dominant": ["newton"] * 8 + ["empathy"] * 2,
         "spread": ["newton", "empathy", "davinci", "quantum", "philosophy"] * 2}


@pytest.mark.parametrize("mix", MIXES)
def test_chat_report_keeps_the_numbers_and_drops_the_verdicts(tmp_path, mix):
    import cocoon_introspection as ci
    db = tmp_path / "m.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE cocoons (id TEXT, query TEXT, response TEXT, adapter TEXT, domain TEXT, "
              "complexity TEXT, emotion TEXT, importance INTEGER, timestamp REAL, metadata_json TEXT)")
    c.executemany("INSERT INTO cocoons VALUES (?,?,?,?,?,?,?,?,?,?)",
                  [(f"id{i}", f"q{i}", "x" * 100, a, "general", "MEDIUM", "neutral", 5, float(i), "{}")
                   for i, a in enumerate(MIXES[mix])])
    c.commit()
    c.close()
    e = ci.CocoonIntrospectionEngine(cocoons_dir=str(tmp_path / "none"))
    e._SQLITE_DB = db
    line = next(o for o in e.self_observations() if "adapter" in o)
    assert "newton" in line and "%" in line
    assert not VERDICTS.search(line), line


@pytest.mark.parametrize("mix", MIXES)
def test_api_report_keeps_the_numbers_and_drops_the_verdicts(tmp_path, mix):
    from reasoning_forge.unified_memory import UnifiedMemory
    (tmp_path / "cocoons").mkdir()
    m = UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=tmp_path / "cocoons")
    for i, a in enumerate(MIXES[mix]):
        m.store(f"question {i}", "an answer " * 5, adapter=a, domain="general")
    line = next(o for o in m.full_introspection()["observations"] if "adapter" in o)
    assert "%" in line
    assert not VERDICTS.search(line), line


def test_the_self_diagnostic_states_the_line_not_a_verdict():
    src = (ROOT / "inference" / "codette_server.py").read_text(encoding="utf-8")
    assert "may be over-relying" not in src.replace("was \"Balanced: Yes / No — may be over-relying\"", "")
    assert "Above the 40% line:" in src
