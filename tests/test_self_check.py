"""self_check: she can see what the post-write checks did to her previous reply."""
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

from reasoning_forge import self_check as sc
from reasoning_forge import antibodies


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "DEFAULT_COUNTS", tmp_path / "counts.json")
    sc._last.clear()


def test_no_record_is_not_the_same_as_clean(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    text = sc.explain(sc.last("s1"))
    assert "no record" in text.lower() and "not the same as" in text


def test_ran_and_changed_nothing_vs_never_ran_vs_changed_something(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    sc.record("s1", True, [])
    clean = sc.explain(sc.last("s1"))
    assert "changed nothing" in clean

    sc.record("s1", False, [])
    skipped = sc.explain(sc.last("s1"))
    assert "does not run" in skipped and "not the same as a clean result" in skipped
    assert "changed nothing" not in skipped

    sc.record("s1", True, ["LOCK1_TRIM: Removed 2 drift sentence(s)", "LOCK4_FIX: Added missing end punctuation"])
    changed = sc.explain(sc.last("s1"))
    assert "LOCK1_TRIM" in changed and "LOCK4_FIX" in changed and "raise_flag" in changed


def test_sessions_do_not_see_each_other(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    sc.record("a", True, ["LOCK1_TRIM: x"])
    assert sc.last("b") is None
    assert sc.last("a")["issues"] == ["LOCK1_TRIM: x"]


def test_counts_hold_codes_only_and_flag_a_recurring_correction(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    for i in range(30):
        sc.record("s", True, ["LOCK1_TRIM: Removed 1 drift sentence(s) SECRET-REPLY-TEXT"] if i % 2 == 0 else [])
    sc.record("s", False, [])
    raw = (tmp_path / "counts.json").read_text(encoding="utf-8")
    assert "SECRET-REPLY-TEXT" not in raw and "Removed" not in raw       # code only
    s = sc.summary()
    assert s["turns_checked"] == 30 and s["turns_not_checked"] == 1
    assert s["codes"] == {"LOCK1_TRIM": 15}
    assert s["recurring"] and s["recurring"][0]["code"] == "LOCK1_TRIM" and s["recurring"][0]["share"] == 0.5


def test_a_small_sample_is_not_called_recurring(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    for _ in range(5):
        sc.record("s", True, ["LOCK4_FIX: x"])
    assert sc.summary()["recurring"] == []          # 5 turns say nothing yet


def test_the_tool_is_registered_free_and_reads_her_own_session(monkeypatch, tmp_path):
    import codette_tools as T
    _fresh(monkeypatch, tmp_path)
    reg = T.ToolRegistry()
    assert "self_check" in reg.tools and "self_check" in T.FREE_ROUND_TOOLS
    assert "Not private" in reg.tools["self_check"]["description"]
    T.set_current_session("sess-9")
    try:
        assert "no record" in T.tool_self_check().lower()
        sc.record("sess-9", True, ["LOCK4_FIX: Added missing end punctuation"])
        assert "LOCK4_FIX" in T.tool_self_check()
    finally:
        T.set_current_session("")


def test_the_bridge_records_ran_false_for_a_path_that_skipped_the_checks(monkeypatch, tmp_path):
    from inference.codette_forge_bridge import CodetteForgeBridge
    import codette_tools as T
    _fresh(monkeypatch, tmp_path)
    b = CodetteForgeBridge.__new__(CodetteForgeBridge)
    T.set_current_session("sess-1")
    try:
        b._record_self_check({"response": "blocked reply"}, "hello")                 # no self_check_ran
        assert sc.last("sess-1")["ran"] is False
        b._record_self_check({"response": "ok", "self_check_ran": True,
                              "lock_fixes": ["LOCK1_TRIM: Removed 1 drift sentence(s)"]}, "hello again")
        assert sc.last("sess-1")["ran"] is True and sc.last("sess-1")["issues"]
        exam = "What is the correct answer to this question?\n(A) a\n(B) b\n(C) c\n(D) d"
        before = sc.summary()["turns_seen"]
        b._record_self_check({"response": "x", "self_check_ran": True}, exam)         # benchmark: skipped
        assert sc.summary()["turns_seen"] == before
    finally:
        T.set_current_session("")


def test_the_antibody_report_carries_the_runtime_counts(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    for _ in range(25):
        sc.record("s", True, ["LOCK4_FIX: x"])
    rep = antibodies.run(ROOT / "reasoning_forge", antibodies=[antibodies.ANTIBODIES[0]])
    assert rep["runtime"]["turns_checked"] == 25
    p = tmp_path / "rep.json"
    antibodies.write_report(rep, p)
    assert antibodies.summary(p)["recurring_corrections"][0]["code"] == "LOCK4_FIX"
