"""Tests for the shadow-only harness ledger (reasoning_forge/harness_ledger.py and
reasoning_forge/harness_verdicts.py). Added 2026-11-20.

Most tests are named after one of the 23 bugs found in the two pasted designs
(GUARD and SIM, docs/HARNESS_LEDGER_2026-11-20.md). The scratchpad probes that
found them showed the pasted code failing each case; these show the rebuild does
not. The last group guards the rules: shadow-only, append-only, not her stores,
nothing live imports it.
"""
import ast
import json
import re
import shutil
import sqlite3
from pathlib import Path

import pytest

from reasoning_forge import harness_verdicts as V
from reasoning_forge.harness_ledger import HarnessLedger, fts_query, ledger_path

ROOT = Path(__file__).resolve().parents[1]
MODULES = [ROOT / "reasoning_forge" / "harness_ledger.py",
           ROOT / "reasoning_forge" / "harness_verdicts.py"]


@pytest.fixture
def ledger(tmp_path):
    with HarnessLedger(tmp_path / "ledger.db") as L:
        yield L


def _rule_with_checks(L, states, pinned=()):
    """states: {check_id: (baseline, active, candidate)}; True/False/None per run."""
    L.add_rule("r1", "prompt_clause", "answer the question asked", author="test")
    for cid, (base, active, cand) in states.items():
        L.add_check(cid, f"prompt for {cid}", author="test")
        L.record_check_run(cid, "baseline", base, author="test")
        L.record_check_run(cid, "active", active, author="test")
        L.record_check_run(cid, "candidate", cand, author="test", rule_id="r1", upsilon=0.3)
    for cid in pinned:
        L.record_decision("check", cid, "pin", by="jonathan")


# ── GUARD gate ─────────────────────────────────────────────────────────────

def test_dispersion_band_is_checked_on_both_sides():
    """Pasted gate: the 'collapse' check only fired on an exact 0.0 against a stored
    delta, so Υ=0.0 and Υ=0.9 were both promoted. Here both sides are looked at."""
    band = (0.08, 0.45)
    assert V.band_position(0.0, band) == "below"
    assert V.band_position(0.9, band) == "above"
    assert V.band_position(0.2, band) == "within"
    assert V.band_position(0.2, None) == "not_judged"       # no band chosen yet
    assert V.band_position(None, band) == "not_measured"


def test_no_checks_is_not_judged_and_upsilon_is_none_not_zero(ledger):
    """Pasted gate: sum(...) / max(len(...), 1) read 0.0 with no checks at all."""
    ledger.add_rule("r1", "prompt_clause", "x", author="test")
    rep = ledger.guard_report("r1")
    assert rep["verdict"] == "not_judged"
    assert rep["upsilon"] == {"mean": None, "n": 0, "position": "not_measured"}
    assert V.mean_measured([]) == (None, 0)
    assert V.mean_measured([None, 0.2, None, 0.4]) == (pytest.approx(0.3), 2)


def test_dispersion_is_none_below_two_perspectives_and_hers_otherwise():
    from reasoning_forge.state_engine_v8 import tension_from_texts
    assert V.dispersion({"newton": "only one lens spoke"}) is None
    assert V.dispersion({"newton": "text", "empathy": "   "}) is None
    two = {"newton": "light scatters off air", "empathy": "the sky feels calm today"}
    assert V.dispersion(two) == tension_from_texts(two)[0]


def test_one_definition_of_dispersion_identical_texts_read_zero():
    """Pasted bridge: Υ = pstdev(lens scores) read 0.35 for two identical texts."""
    same = {"newton": "Light scatters off air molecules.",
            "empathy": "Light scatters off air molecules."}
    assert V.dispersion(same) == pytest.approx(0.0, abs=1e-12)
    for m in MODULES:
        assert "pstdev" not in m.read_text(encoding="utf-8")


def test_still_regressed_is_not_persistent_fail():
    assert V.classify_transition(True, False, False) == "still_regressed"
    assert V.classify_transition(False, False, False) == "persistent_fail"
    assert V.classify_transition(True, True, False) == "newly_broken"
    assert V.classify_transition(True, False, True) == "fixed_regression"
    assert V.classify_transition(False, False, True) == "fixed_baseline"
    assert V.classify_transition(None, True, True) == "not_measured"


def test_a_pinned_rule_is_never_demoted_and_its_history_stays(ledger):
    """Pasted gate: one failed check turned a pinned rule into 'rejected' and erased
    its promoted_at. Here a report writes nothing; decisions stay as recorded."""
    _rule_with_checks(ledger, {"k0": (True, True, False)})
    ledger.record_decision("rule", "r1", "pin", by="jonathan", note="mastered")
    before = ledger.summary()["rows"]
    rep = ledger.guard_report("r1")
    assert rep["verdict"] == "would_reject" and rep["reason"] == "newly_broken"
    assert ledger.summary()["rows"] == before
    assert [d["decision"] for d in rep["decisions"]] == ["pin"]


def test_a_rule_that_still_passes_everything_is_neutral_not_rejected(ledger):
    _rule_with_checks(ledger, {"k0": (True, True, True), "k1": (True, True, True)})
    rep = ledger.guard_report("r1")
    assert (rep["verdict"], rep["reason"]) == ("neutral", "no_change")


def test_a_pinned_check_already_failing_does_not_deadlock(ledger):
    """Pasted gate: a pinned check failing before the edit rejected every candidate."""
    states = {"pin": (True, False, False)}
    states.update({f"k{i}": (False, False, True) for i in range(5)})
    _rule_with_checks(ledger, states, pinned=["pin"])
    rep = ledger.guard_report("r1")
    assert rep["verdict"] == "would_promote"
    assert rep["pinned_already_failing"] == 1 and rep["pinned_newly_broken"] == 0


def test_a_newly_broken_pinned_check_rejects_even_in_the_soft_form(ledger):
    states = {"pin": (True, True, False)}
    states.update({f"k{i}": (False, False, True) for i in range(5)})
    _rule_with_checks(ledger, states, pinned=["pin"])
    rep = ledger.guard_report("r1", lam=0.1)
    assert (rep["verdict"], rep["reason"]) == ("would_reject", "pinned_newly_broken")


def test_soft_form_only_with_lam_and_parameters_are_printed(ledger):
    _rule_with_checks(ledger, {"a": (False, False, True), "b": (False, False, True),
                               "c": (True, True, False)})
    strict = ledger.guard_report("r1")
    soft = ledger.guard_report("r1", lam=1.5)
    assert strict["verdict"] == "would_reject" and strict["parameters"]["rule"] == "strict"
    assert soft["net"] == pytest.approx(0.5) and soft["verdict"] == "would_promote"
    assert soft["parameters"]["lam"] == 1.5


@pytest.mark.parametrize("scope", ["adapter", "adapter-route", "what's wrong", "route: fix", "", "--"])
def test_scope_text_with_punctuation_does_not_crash(ledger, scope):
    _rule_with_checks(ledger, {"k0": (False, False, True)})
    ledger.guard_report("r1", scope_text=scope)                  # must not raise


def test_scope_text_selects_matching_checks_plus_pinned(ledger):
    ledger.add_rule("r1", "tool_guard", "x", author="test")
    ledger.add_check("route", "route the adapter correctly", author="test")
    ledger.add_check("tone", "answer kindly", author="test")
    ledger.add_check("pinned", "never cut her reply", author="test")
    ledger.record_decision("check", "pinned", "pin", by="jonathan")
    ids = [c["check_id"] for c in ledger.guard_report("r1", scope_text="adapter-route")["checks"]]
    assert ids == ["pinned", "route"]


def test_the_search_index_follows_a_delete(ledger):
    """Pasted schema had no delete trigger: a deleted check still matched."""
    ledger.add_check("k0", "route the adapter", author="test")
    ledger.conn.execute("DELETE FROM checks WHERE check_id = 'k0'")
    hits = ledger.conn.execute(
        "SELECT check_id FROM checks_fts WHERE checks_fts MATCH ?", (fts_query("adapter"),)).fetchall()
    assert hits == []


def test_fts_query_quotes_every_term():
    assert fts_query("adapter-route: what's") == '"adapter" OR "route" OR "what"'
    assert fts_query("- : '") is None


# ── circuit breaker ────────────────────────────────────────────────────────

def test_successful_patches_are_not_held_against_a_later_failure():
    """Pasted breaker: two good patches, then one failure -> retired for good."""
    events = [{"succeeded": True, "patch_signature": "a"},
              {"succeeded": True, "patch_signature": "b"},
              {"succeeded": False, "patch_signature": "c"}]
    v = V.breaker_verdict(events)
    assert (v["verdict"], v["consecutive_failures"], v["patches_in_streak"]) == ("failing", 1, 1)


def test_each_breaker_budget_is_exercised_on_its_own():
    """Pasted test retired by patch budget while its comment said quarantine count."""
    fail = lambda sig=None: {"succeeded": False, "patch_signature": sig}
    assert V.breaker_verdict([fail(), fail(), fail()], max_failures=3)["reason"] == "consecutive_failures"
    assert V.breaker_verdict([fail("a"), fail("b"), fail("c")], max_patches=3)["reason"] == "patch_budget"
    assert V.breaker_verdict([fail("a"), fail("a")])["reason"] == "same_patch_repeated"
    assert V.breaker_verdict([fail("a"), fail("b")])["verdict"] == "failing"
    assert V.breaker_verdict([])["verdict"] == "not_judged"


def test_breaker_state_survives_a_new_ledger(tmp_path):
    """Pasted breaker: state lived in memory, so a restart allowed a retired target."""
    p = tmp_path / "ledger.db"
    with HarnessLedger(p) as L:
        for sig in ("a", "b", "c"):
            L.record_breaker_event("fn:route", False, patch_signature=sig, error="TimeoutError")
    with HarnessLedger(p) as L:
        assert L.breaker_report("fn:route")["verdict"] == "would_retire"


def test_a_failure_keeps_its_error_and_never_reads_as_ok(ledger):
    """Pasted wrapper: first failure came back as status 'active', error dropped."""
    ledger.record_breaker_event("fn:route", False, error="ValueError: the real error message")
    rep = ledger.breaker_report("fn:route")
    assert rep["verdict"] == "failing" and rep["verdict"] != "ok"
    assert rep["last_error"] == "ValueError: the real error message"


# ── SIM notebook ───────────────────────────────────────────────────────────

def _note(L, **kw):
    args = dict(task_domain="physics", failure_mode="dispersion_low",
                symptom="lenses agreed too early", root_cause="written by the caller",
                author="jonathan")
    args.update(kw)
    return L.add_note(**args)


def test_recall_finds_a_matching_note(ledger):
    """Pasted schema was contentless, so note_id read back as None and recall was []."""
    nid = _note(ledger)
    assert [r["note_id"] for r in ledger.recall("lenses agreed")] == [nid]


def test_recall_never_returns_the_note_being_worked_on(ledger):
    """Pasted cycle wrote its note first, then 'consulted' it as a prior lesson."""
    old = _note(ledger, note_id="old")
    new = _note(ledger, note_id="new")
    assert [r["note_id"] for r in ledger.recall("lenses agreed", exclude_note=new)] == [old]


def test_recall_finds_a_note_through_its_patch_text(ledger):
    nid = _note(ledger)
    ledger.add_patch(nid, "prompt_clause", {"k": 1}, rationale="shorter preamble", author="jonathan")
    assert [r["note_id"] for r in ledger.recall("preamble")] == [nid]


def test_a_missing_baseline_is_no_baseline_not_improved(ledger):
    """Pasted notebook: NULL baseline read as 0.0, so a 0.10 trial was 'improved'."""
    nid = _note(ledger)                                      # baseline_score not given
    pid = ledger.add_patch(nid, "prompt_clause", {}, rationale="r", author="jonathan")
    ledger.record_trial(pid, "m", "a", author="benchmark", score=0.10)
    rep = ledger.note_report(nid)
    assert rep["baseline"] == "not_measured"
    assert rep["patches"][0]["overall"] == "no_baseline"


def test_targets_that_disagree_read_mixed_and_none_is_overwritten(ledger):
    """Pasted notebook: last trial wins, so A's improvement vanished."""
    nid = _note(ledger, baseline_score=0.5)
    pid = ledger.add_patch(nid, "prompt_clause", {}, rationale="r", author="jonathan")
    for model, score in (("A", 0.9), ("B", 0.1), ("C", 0.5)):
        ledger.record_trial(pid, model, "a", author="benchmark", score=score)
    p = ledger.note_report(nid)["patches"][0]
    assert p["overall"] == "mixed"
    assert [t["verdict"] for t in p["trials"]] == ["improved", "regressed", "neutral"]


def test_deleting_a_note_with_patches_is_refused(ledger):
    """Pasted schema: ON DELETE CASCADE erased every patch and trial."""
    nid = _note(ledger)
    ledger.add_patch(nid, "t", {}, rationale="r", author="jonathan")
    with pytest.raises(sqlite3.IntegrityError):
        with ledger.conn:
            ledger.conn.execute("DELETE FROM notes WHERE note_id = ?", (nid,))
    assert ledger.summary()["rows"]["patches"] == 1


def test_unchecked_invariants_are_none_not_passed(ledger):
    """Pasted defaults: invariants_passed=True, and a cache hit rate of 1.0 for no lookups."""
    nid = _note(ledger, baseline_score=0.5)
    pid = ledger.add_patch(nid, "t", {}, rationale="r", author="jonathan")
    ledger.record_trial(pid, "m", "a", author="benchmark", score=0.6)   # invariants not given
    t = ledger.note_report(nid)["patches"][0]["trials"][0]
    assert t["invariants"] == "not_checked" and t["verdict"] == "improved"
    with pytest.raises(TypeError):
        ledger.record_trial(pid, "m", "a", author="benchmark", score=0.6, invariants=1.0)


def test_a_backend_error_is_not_an_aegis_failure(ledger):
    """Pasted bridge: a timeout was recorded as aegis_passed=False, sycophancy=True."""
    ledger.add_rule("r1", "prompt_clause", "x", author="test")
    ledger.add_check("k0", "p", author="test")
    ledger.record_check_run("k0", "candidate", None, author="test", rule_id="r1",
                            error="TimeoutError: model server not answering")
    rep = ledger.guard_report("r1")
    assert rep["checks"][0]["aegis"] == "not_run" and rep["candidate_errors"] == 1
    nid = _note(ledger)
    pid = ledger.add_patch(nid, "t", {}, rationale="r", author="jonathan")
    ledger.record_trial(pid, "m", "a", author="benchmark", error="TimeoutError")
    t = ledger.note_report(nid)["patches"][0]["trials"][0]
    assert t["verdict"] == "error" and t["invariants"] == "not_checked"


def test_a_single_lens_trial_gets_no_diagnosis_written_for_it(ledger):
    """Pasted bridge: one lens -> Υ 0.0 -> stored 'lenses aligned prematurely...'."""
    nid = _note(ledger, baseline_score=0.5)
    pid = ledger.add_patch(nid, "t", {}, rationale="r", author="jonathan")
    ledger.record_trial(pid, "m", "a", author="benchmark", score=0.6,
                        upsilon=V.dispersion({"newton": "one lens"}))
    t = ledger.note_report(nid, band=(0.08, 0.45))["patches"][0]["trials"][0]
    assert t["upsilon"] == "not_measured"


def test_words_are_the_callers_and_carry_an_author(ledger):
    """Pasted builder wrote rationales itself, and claimed prior lessons it did not use."""
    nid = _note(ledger, root_cause="Jonathan's own words", author="jonathan")
    row = ledger.conn.execute("SELECT root_cause, author FROM notes WHERE note_id = ?", (nid,)).fetchone()
    assert tuple(row) == ("Jonathan's own words", "jonathan")
    with pytest.raises(ValueError):
        ledger.add_patch(nid, "t", {}, rationale="r", author="")
    with pytest.raises(ValueError):
        ledger.add_patch(nid, "t", {}, rationale="", author="jonathan")


def test_report_reasons_are_codes_not_prose(ledger):
    _rule_with_checks(ledger, {"k0": (False, False, True)})
    rep = ledger.guard_report("r1")
    assert re.fullmatch(r"[a-z_]+", rep["reason"]) and re.fullmatch(r"[a-z_]+", rep["verdict"])


# ── the rules: shadow-only, append-only, not her stores ────────────────────

def _sql_strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_the_api_never_updates_or_deletes():
    """Rule 2. The only DELETE statements are the index triggers following a delete."""
    for s in _sql_strings(MODULES[0]):
        for stmt in re.findall(r"\b(UPDATE|DELETE FROM)\s+(\w+)", s):
            assert stmt in {("DELETE FROM", "notes_fts"), ("DELETE FROM", "checks_fts")}, stmt
    assert "ON DELETE CASCADE" not in MODULES[0].read_text(encoding="utf-8")


def test_the_modules_import_nothing_that_could_act_or_read_her_stores():
    """Rules 1 and 5: stdlib, the runtime path helper, her Υ function, each other."""
    allowed = {"__future__", "json", "re", "sqlite3", "time", "uuid", "pathlib", "typing",
               "reasoning_forge.runtime_paths", "runtime_paths", "reasoning_forge",
               "harness_verdicts", "reasoning_forge.state_engine_v8", "state_engine_v8"}
    for m in MODULES:
        tree = ast.parse(m.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                assert {a.name for a in n.names} <= allowed, (m.name, [a.name for a in n.names])
            elif isinstance(n, ast.ImportFrom):
                assert n.module in allowed, (m.name, n.module)
            elif isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute)):
                name = n.func.id if isinstance(n.func, ast.Name) else n.func.attr
                assert name not in {"open", "glob", "rglob", "iterdir", "listdir", "walk", "scandir"}, \
                    (m.name, name)


def test_the_ledger_lives_under_the_runtime_root_not_the_repository():
    from reasoning_forge.runtime_paths import runtime_root
    p = ledger_path()
    assert p.is_relative_to(runtime_root()) and not p.is_relative_to(ROOT)
    assert p.name == "harness_ledger.db" and p.name != "codette_memory.db"


def test_nothing_live_imports_the_ledger():
    """Shadow-only: no live module imports either file (the pattern of
    tests/test_adapter_switch_timing.py::test_nothing_reads_the_log)."""
    live = ["inference", "reasoning_forge", "openvino_backend", "Protection_Layer",
            "consciousness", "ethics", "api", "mcp"]
    offenders = []
    for d in live:
        for f in (ROOT / d).rglob("*.py"):
            if f.name in {"harness_ledger.py", "harness_verdicts.py"}:
                continue
            if re.search(r"\bharness_(ledger|verdicts)\b", f.read_text(encoding="utf-8", errors="replace")):
                offenders.append(str(f.relative_to(ROOT)))
    assert offenders == [], offenders


def test_the_antibodies_find_nothing_in_the_new_modules(tmp_path):
    from reasoning_forge import antibodies as A
    for m in MODULES:
        shutil.copy(m, tmp_path / m.name)
    rep = A.run(root=tmp_path)
    assert {a["name"]: a["count"] for a in rep["antibodies"]} == {a.name: 0 for a in A.ANTIBODIES}
