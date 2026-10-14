import json

from reasoning_forge import tool_efficacy as te


def test_classification_from_the_first_line():
    assert te.classify("Error: File not found: x.py") == "error"
    assert te.classify("Error executing read_file: boom") == "error"
    assert te.classify("PARTIAL search - absence here is not evidence of absence") == "partial"
    assert te.classify("") == "empty" and te.classify(None) == "empty"
    assert te.classify("No matches for 'foo'") == "empty"
    assert te.classify("484 lines\nimport os") == "ok"


def test_counts_accumulate_per_tool_and_outcome(tmp_path):
    p = tmp_path / "t.json"
    te.record("read_file", "Error: File not found: a", path=p)
    te.record("read_file", "Error: File not found: b", path=p)
    te.record("read_file", "484 lines", path=p)
    s = te.summary(path=p)["tools"]["read_file"]
    assert (s["error"], s["ok"], s["calls"]) == (2, 1, 3)
    assert s["error_rate"] == 0.667
    assert te.summary(path=p)["tools"]["web_search"]["error_rate"] is None  # no calls != 0%


def test_her_own_spaces_are_never_counted(tmp_path):
    p = tmp_path / "t.json"
    for t in ("nameless", "khralexi", "scratch_write", "scratch_read", "aside",
              "cocoon", "leave_note", "read_note", "care_check", "who", "look", "ask"):
        assert te.record(t, "Written.", path=p) is None
    assert not p.exists()                         # not even a file was created


def test_nothing_but_counts_is_stored(tmp_path):
    p = tmp_path / "t.json"
    te.record("run_python", "Error: secret-token-123 leaked in traceback", path=p)
    raw = p.read_text(encoding="utf-8")
    assert "secret" not in raw
    assert set(json.loads(raw)["run_python"]) == set(te.OUTCOMES)


def test_a_write_failure_never_raises(tmp_path):
    bad = tmp_path / "is_a_dir"
    bad.mkdir()
    assert te.record("read_file", "ok", path=bad) == "ok"
