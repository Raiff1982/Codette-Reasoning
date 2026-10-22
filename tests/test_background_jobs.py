import json

from reasoning_forge.background_jobs import BackgroundJobs, default_jobs


def _bj(tmp_path, jobs, **kw):
    return BackgroundJobs(jobs, state_path=tmp_path / "s.json", **kw)


def test_runs_when_never_run_then_waits_for_the_interval(tmp_path):
    calls = []
    bj = _bj(tmp_path, {"a": lambda: calls.append(1) or {"n": 1}}, interval_s=1000)
    assert bj.run_due() == ["a"]
    assert bj.run_due() == []                      # not due again
    assert bj.due("a", now=bj._state["a"]["last_run"] + 1001)
    assert len(calls) == 1


def test_a_failing_job_is_recorded_and_never_raises(tmp_path):
    def boom():
        raise RuntimeError("bad")
    bj = _bj(tmp_path, {"b": boom})
    e = bj.run_job("b")
    assert e["ok"] is False and "RuntimeError" in e["error"]
    assert bj.status()["b"]["status"] == "FAILED"


def test_state_survives_a_restart(tmp_path):
    bj = _bj(tmp_path, {"a": lambda: {"n": 2}}, interval_s=1000)
    bj.run_due()
    again = _bj(tmp_path, {"a": lambda: {"n": 2}}, interval_s=1000)
    assert again.run_due() == []
    assert again.status()["a"]["summary"] == {"n": 2}


def test_never_run_is_distinguishable_from_ok(tmp_path):
    bj = _bj(tmp_path, {"a": lambda: {}})
    assert bj.status()["a"]["status"] == "NEVER_RUN"
    bj.run_due()
    assert bj.status()["a"]["status"] == "OK"


def test_the_state_file_holds_counts_not_text(tmp_path):
    bj = _bj(tmp_path, {"a": lambda: {"reviewed": 3, "report": "dream_x.md"}})
    bj.run_due()
    raw = (tmp_path / "s.json").read_text(encoding="utf-8")
    assert json.loads(raw)["a"]["summary"] == {"reviewed": 3, "report": "dream_x.md"}


def test_registered_jobs_are_exactly_the_report_only_ones():
    # Amended 2026-10-22: was "exactly the two"; antibody_scan is the third, and is
    # report-only too (it reads Python source and writes data/antibody_report.json).
    assert set(default_jobs()) == {"dream_cycle", "cocoon_self_trainer", "antibody_scan"}
