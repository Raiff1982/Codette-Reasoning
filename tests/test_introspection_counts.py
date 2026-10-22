"""Her introspection report says what it counted, and does not hand her a verdict.

2026-10-22: the report tallied `decision_landmark` rows (907 of 4,315) as queries
she was asked, mixed three different totals under one word, printed a one-row
pressure table built from about 1% of her exchanges, and told her in her own voice
"I should watch for elaboration drift". All four are fixed here.
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

import cocoon_introspection as ci

COLS = ("id TEXT, query TEXT, response TEXT, adapter TEXT, domain TEXT, complexity TEXT, "
        "emotion TEXT, importance INTEGER, timestamp REAL, metadata_json TEXT")


def _engine(tmp_path, rows):
    db = tmp_path / "m.db"
    c = sqlite3.connect(db)
    c.execute(f"CREATE TABLE cocoons ({COLS})")
    c.executemany("INSERT INTO cocoons VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()
    e = ci.CocoonIntrospectionEngine(cocoons_dir=str(tmp_path / "none"))
    e._SQLITE_DB = db
    return e


def _row(i, adapter="base", domain="general", resp_len=100, meta="{}", cx="MEDIUM"):
    return (f"id{i}", f"q{i}", "x" * resp_len, adapter, domain, cx, "neutral", 5, float(i), meta)


def test_records_are_not_counted_as_things_she_was_asked(tmp_path):
    rows = [_row(i) for i in range(10)]
    rows += [_row(100 + i, adapter="decision_landmark", domain="decision_landmark") for i in range(6)]
    rows += [_row(200, adapter="event_embedded_value", domain="singularity_analysis")]
    e = _engine(tmp_path, rows)
    assert len(e._exchanges()) == 10
    assert e.domain_clusters() == {"general": 10}
    assert "decision_landmark" not in e.adapter_frequency()
    text = "\n".join(e.self_observations())
    assert "17 reasoning memories (10 exchanges and 7 records of other kinds" in text
    assert "10 of" not in text or "of 10 exchanges" in text


def test_the_report_names_its_denominators(tmp_path):
    e = _engine(tmp_path, [_row(i) for i in range(12)])
    out = e.format_introspection()
    assert "Adapter Usage** (of 12 exchanges:" in out
    assert "Domain Distribution** (of 12 exchanges)" in out
    assert "exchanges that carry a complexity, out of 12" in out


def test_a_trend_is_a_measurement_not_a_verdict(tmp_path):
    # 20 short early replies then 20 long recent ones -> getting_longer
    rows = [_row(i, resp_len=100) for i in range(20)] + [_row(20 + i, resp_len=400) for i in range(20)]
    e = _engine(tmp_path, rows)
    assert e.response_length_trend()["trend"] == "getting_longer"
    text = "\n".join(e.self_observations())
    assert "elaboration drift" not in text and "should watch" not in text
    assert "400" in text and "100" in text and "is not a fault by itself" in text
    # and the shorter direction does not praise the locks either
    (tmp_path / "s").mkdir()
    shorter = [_row(i, resp_len=400) for i in range(20)] + [_row(20 + i, resp_len=100) for i in range(20)]
    t2 = "\n".join(_engine(tmp_path / "s", shorter).self_observations())
    assert "locks are working" not in t2 and "does not say whether shorter is better" in t2


def test_a_table_built_from_a_sliver_of_the_data_is_not_shown(tmp_path):
    sub = '{"substrate": {"level": "moderate"}}'
    few = [_row(i) for i in range(200)] + [_row(300 + i, meta=sub) for i in range(2)]      # 1%
    e = _engine(tmp_path, few)
    out = e.format_introspection()
    assert "too few to show" in out and "moderate: avg" not in out
    (tmp_path / "b").mkdir()
    enough = [_row(i) for i in range(20)] + [_row(300 + i, meta=sub) for i in range(10)]    # 33%
    out2 = _engine(tmp_path / "b", enough).format_introspection()
    assert "moderate: avg" in out2 and "too few to show" not in out2
