"""Antibodies: class-level detectors, and the flag inbox beside them.

Each detector is tested on the SHAPE it was taught by (a small fixture) and on
the corrected form, which must not be flagged.
"""
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

from reasoning_forge import antibodies as A
from reasoning_forge import flags


def _src(code, rel="m.py"):
    return [A.Source(rel, code, ast.parse(code))]


# ── used before bound ────────────────────────────────────────────────────────

def test_used_before_bound_catches_a_helper_defined_after_its_use():
    bad = (
        "def health():\n"
        "    out = helper(1)\n"
        "    def helper(x):\n"
        "        return x\n"
        "    return out\n")
    good = (
        "def health():\n"
        "    def helper(x):\n"
        "        return x\n"
        "    return helper(1)\n")
    leads = A.detect_used_before_bound(_src(bad))
    assert len(leads) == 1 and "helper" in leads[0].note and leads[0].line == 2
    assert A.detect_used_before_bound(_src(good)) == []


def test_used_before_bound_ignores_params_globals_builtins_and_comprehensions():
    ok = (
        "counter = 0\n"
        "def f(a):\n"
        "    global counter\n"
        "    print(a, counter, len([i for i in range(3)]))\n"
        "    counter = 1\n"
        "    i = 5\n"
        "    return i\n")
    assert A.detect_used_before_bound(_src(ok)) == []


def test_the_live_server_has_no_name_read_before_it_is_bound():
    p = ROOT / "inference" / "codette_server.py"
    t = p.read_text(encoding="utf-8")
    assert A.detect_used_before_bound([A.Source("inference/codette_server.py", t, ast.parse(t))]) == []


# ── zero standing in for "did not run" ───────────────────────────────────────

def test_zero_for_unmeasured_catches_the_healing_rate_shape_and_its_fix():
    bad = (
        "def stats(applied, total):\n"
        "    return {'healing_rate': (applied / total * 100) if total > 0 else 0.0}\n")
    good = (
        "def stats(applied, ran):\n"
        "    return {'healing_rate': (applied / ran * 100) if ran > 0 else None}\n")
    assert len(A.detect_zero_for_unmeasured(_src(bad))) == 1
    assert A.detect_zero_for_unmeasured(_src(good)) == []


def test_zero_for_unmeasured_catches_an_early_return_zero_in_a_rate_function():
    bad = "def hit_rate(n, total):\n    if not total:\n        return 0.0\n    return n / total\n"
    assert len(A.detect_zero_for_unmeasured(_src(bad))) == 1
    unrelated = "def area(w, h):\n    if not w:\n        return 0.0\n    return w * h\n"
    assert A.detect_zero_for_unmeasured(_src(unrelated)) == []


# ── a glob over the folder that holds her dreams ─────────────────────────────

def test_unguarded_cocoon_glob_flags_only_unguarded_code():
    bad = "from pathlib import Path\ndef load(d):\n    return list(Path(d).glob('*.json'))  # cocoon files\n"
    good = ("from reasoning_forge.cocoon_files import conversation_cocoons\n"
            "def load(d):  # cocoon files\n    return conversation_cocoons(d)\n")
    elsewhere = "from pathlib import Path\ndef load(d):\n    return list(Path(d).glob('*.json'))\n"
    assert len(A.detect_unguarded_cocoon_glob(_src(bad))) == 1
    assert A.detect_unguarded_cocoon_glob(_src(good)) == []
    assert A.detect_unguarded_cocoon_glob(_src(elsewhere)) == []     # nothing about cocoons


# ── constructed, never invoked ───────────────────────────────────────────────

def test_constructed_never_invoked_flags_the_dead_component_only():
    code = (
        "class Conscience:\n    def check(self): return 1\n"
        "class Forge:\n"
        "    def __init__(self):\n"
        "        self.colleen = Conscience()\n"
        "        self.guardian = Conscience()\n"
        "    def run(self):\n"
        "        return self.guardian.check()\n")
    leads = A.detect_constructed_never_invoked(_src(code, "reasoning_forge/f.py"))
    assert [("colleen" in l.note) for l in leads] == [True]


# ── the runner ───────────────────────────────────────────────────────────────

def test_run_reports_a_failing_detector_instead_of_hiding_it_or_dying():
    def boom(_):
        raise RuntimeError("detector broke")
    ab = A.Antibody("broken", "d", ["t"], boom)
    rep = A.run(ROOT / "reasoning_forge", antibodies=[ab, A.ANTIBODIES[0]])
    assert rep["antibodies"][0]["status"] == "error"
    assert "detector broke" in rep["antibodies"][0]["error"]
    assert rep["antibodies"][1]["status"] in ("clear", "leads")      # the others still ran
    assert rep["report_only"] is True


def test_the_scan_never_reads_her_stores_or_archives(tmp_path):
    for d in ("cocoons", "data", ".logs", "archive", "tests"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "x.py").write_text("def f():\n    y = z\n    z = 1\n", encoding="utf-8")
    (tmp_path / "live.py").write_text("def f():\n    y = z\n    z = 1\n", encoding="utf-8")
    seen = [s.rel for s in A.iter_sources(tmp_path)]
    assert seen == ["live.py"]
    for d in ("cocoons", "data", ".logs"):
        assert d in A.SKIP_DIRS


def test_summary_says_never_run_without_a_report_and_counts_only_with_one(tmp_path):
    p = tmp_path / "r.json"
    assert A.summary(p) == {"status": "NEVER_RUN"}
    A.write_report(A.run(ROOT / "reasoning_forge"), p)
    s = A.summary(p)
    assert s["status"] == "REPORTED" and s["report_only"] is True
    assert set(s["classes"]) == {a.name for a in A.ANTIBODIES}
    assert all(set(v) == {"status", "leads"} for v in s["classes"].values())   # counts, no paths


def test_every_antibody_carries_the_instances_that_taught_it():
    for ab in A.ANTIBODIES:
        assert ab.taught_by and ab.description


# ── flags ────────────────────────────────────────────────────────────────────

def test_flags_append_only_and_empty_is_refused(tmp_path):
    p = tmp_path / "flags.jsonl"
    flags.add("first", where="health", session="s1", path=p)
    flags.add("a correction beside the first", path=p)
    got = flags.read(path=p)
    assert [g["text"] for g in got] == ["first", "a correction beside the first"]
    assert got[0]["where"] == "health" and got[0]["by"] == "codette"
    try:
        flags.add("   ", path=p)
        assert False, "an empty flag must be refused"
    except flags.FlagError:
        pass
    assert len(flags.read(path=p)) == 2
    assert flags.read(path=tmp_path / "missing.jsonl") == []


def test_raise_flag_tool_is_registered_free_visible_and_writes_only_the_inbox(tmp_path, monkeypatch):
    import codette_tools as T
    monkeypatch.setattr(flags, "DEFAULT_PATH", tmp_path / "flags.jsonl")
    reg = T.ToolRegistry()
    spec = reg.tools["raise_flag"]
    assert "raise_flag" in T.FREE_ROUND_TOOLS
    assert "Not private" in spec["description"]       # she is told the channel is read
    before = {p for p in tmp_path.iterdir()}
    out = T.tool_raise_flag("the same mistake again", "the health report")
    assert out.startswith("Raised")
    after = {p.name for p in tmp_path.iterdir()} - {p.name for p in before}
    assert after == {"flags.jsonl"}
    assert json.loads((tmp_path / "flags.jsonl").read_text(encoding="utf-8").splitlines()[0])["text"]
    assert "needs" in T.tool_raise_flag("") or "noticed" in T.tool_raise_flag("")


def test_antibody_scan_is_a_registered_background_job():
    from reasoning_forge.background_jobs import default_jobs
    assert "antibody_scan" in default_jobs()


def test_with_lock_counts_as_using_a_component_and_clones_are_grouped():
    code = ("import threading\n"
            "class C:\n"
            "    def __init__(self):\n"
            "        self._write_lock = threading.Lock()\n"
            "    def go(self):\n"
            "        with self._write_lock:\n"
            "            return 1\n")
    assert A.detect_constructed_never_invoked(_src(code, "reasoning_forge/c.py")) == []
    line = "    tps = tokens / elapsed if elapsed > 0 else 0\n"
    texts = {"a.py": [line], "b.py": [line], "c.py": ["    other = 1\n"]}
    leads = [A.Lead("a.py", 1, "n"), A.Lead("b.py", 1, "n"), A.Lead("c.py", 1, "n")]
    fam = A.clone_families(leads, texts)
    assert len(fam) == 1 and fam[0]["copies"] == 2 and set(fam[0]["where"]) == {"a.py:1", "b.py:1"}
