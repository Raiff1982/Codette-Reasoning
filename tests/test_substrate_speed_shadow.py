"""The substrate speed shadow: per-token slowdown against her own normal.

Shadow only (2026-11-17). Long answers at her usual speed must not read as
pressure; a real slowdown must. The live pressure must not change, and nothing
is written unless a log path is given.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

import substrate_awareness as sa  # noqa: E402


def _monitor(**kw):
    m = sa.SubstrateMonitor(**kw)
    m._cache_ttl = 0
    return m


def test_unmeasured_until_five_timed_turns_and_says_so():
    m = _monitor()
    for _ in range(4):
        m.record_inference(10_000, tokens=100)
    sh = m.snapshot()["speed_shadow"]
    assert sh["speed_pressure"] is None and sh["pressure_if_live"] is None
    assert sh["source"].startswith("unmeasured")


def test_a_turn_without_a_token_count_adds_no_speed_sample():
    m = _monitor()
    for _ in range(10):
        m.record_inference(10_000)
    assert m.speed_shadow()["samples"] == 0


def test_long_answers_at_her_usual_speed_are_not_pressure():
    m = _monitor()
    for _ in range(10):
        m.record_inference(90_000, tokens=900)      # 90 s each, 10 tok/s throughout
    sh = m.speed_shadow()
    assert sh["speed_pressure"] == 0.0
    # The live latency term still counts them; the shadow is what would differ.
    assert m._compute_pressure(50, 0, 0, 90_000, 0) > m._compute_pressure(50, 0, 0, 90_000, 0, speed_p=0.0)


def test_a_real_slowdown_reads_as_pressure():
    m = _monitor()
    for _ in range(10):
        m.record_inference(10_000, tokens=100)      # 10 tok/s
    for _ in range(3):
        m.record_inference(25_000, tokens=100)      # 4 tok/s: 60% slower
    assert m.speed_shadow()["speed_pressure"] == 1.0


def _fixed_machine(monkeypatch):
    """snapshot() reads the live machine; pin it so two monitors can be compared."""
    from types import SimpleNamespace as NS
    gb = 1024 ** 3
    monkeypatch.setattr(sa.psutil, "virtual_memory", lambda: NS(percent=87.0, available=2 * gb))
    monkeypatch.setattr(sa.psutil, "swap_memory", lambda: NS(used=gb, total=4 * gb, percent=25.0))
    monkeypatch.setattr(sa.psutil, "cpu_percent", lambda interval=None: 30.0)
    monkeypatch.setattr(sa.psutil, "Process", lambda pid: NS(memory_info=lambda: NS(rss=6 * gb)))
    monkeypatch.setattr(sa, "gpu_memory", lambda device=None: {
        "used_gb": None, "total_gb": None, "pct": None, "source": "unmeasured: test"})


def test_the_live_pressure_and_routing_are_unchanged_by_the_shadow(monkeypatch):
    # Amended 2026-11-18 (PR #53 review): this compared _compute_pressure with
    # itself, so it could pass while snapshot() changed. It now runs the same
    # turns through two monitors, one with token counts (the shadow fed) and
    # one without (the shadow empty), and compares what routing actually reads.
    from reasoning_forge.query_classifier import QueryComplexity
    _fixed_machine(monkeypatch)
    # Deep answers at her usual speed: here the two terms disagree most
    # (latency reads 1.0, speed reads 0.0), so any leak shows in the pressure.
    fed, starved = _monitor(), _monitor()
    for _ in range(12):
        fed.record_inference(90_000, tokens=900)
        starved.record_inference(90_000)
    a, b = fed.snapshot(), starved.snapshot()
    assert a["speed_shadow"]["speed_pressure"] == 0.0
    assert a["speed_shadow"]["pressure_if_live"] < a["pressure"]   # the shadow differs...
    assert b["speed_shadow"]["speed_pressure"] is None
    assert (a["pressure"], a["level"]) == (b["pressure"], b["level"])  # ...live does not
    route = lambda m: sa.HealthAwareRouter(m).adjust_routing(QueryComplexity.COMPLEX, 5)
    assert route(fed) == route(starved)


def test_the_logged_turn_takes_no_new_measurement(monkeypatch, tmp_path):
    # The write used to call snapshot(), paying a fresh 100 ms psutil sample
    # every turn. It must reuse the snapshot that routed the turn.
    _fixed_machine(monkeypatch)
    m = _monitor(shadow_log=tmp_path / "s.jsonl")
    m.snapshot()                                        # routing, before generation
    # Count, don't raise: snapshot() swallows exceptions from psutil, so a
    # raising stub would pass silently (it did, against the pre-fix code).
    samples = []
    monkeypatch.setattr(sa.psutil, "cpu_percent",
                        lambda interval=None: samples.append(interval) or 30.0)
    m._last_snapshot_time -= 5                          # generation outlived the cache
    for _ in range(6):
        m.record_inference(10_000, tokens=100)
    assert samples == []
    rows = [json.loads(l) for l in (tmp_path / "s.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 6 and rows[-1]["pressure"] is not None


def test_a_failed_write_never_reaches_the_turn(tmp_path):
    bad = tmp_path / "is_a_directory"
    bad.mkdir()                                         # opening it for append fails
    m = _monitor(shadow_log=bad)
    for _ in range(6):
        m.record_inference(10_000, tokens=100)          # must not raise
    assert m.speed_shadow()["samples"] == 6


def test_with_no_routing_snapshot_the_log_says_unknown_not_zero(tmp_path):
    m = _monitor(shadow_log=tmp_path / "s.jsonl")
    m.record_inference(10_000, tokens=100)
    row = json.loads((tmp_path / "s.jsonl").read_text(encoding="utf-8"))
    assert row["pressure"] is None and row["level"] is None


def test_nothing_is_written_without_a_path_and_numbers_only_with_one(tmp_path):
    m = _monitor()
    m.record_inference(10_000, tokens=100)
    assert m._shadow_log is None
    log = tmp_path / "speed.jsonl"
    m = _monitor(shadow_log=log)
    for _ in range(6):
        m.record_inference(10_000, tokens=100)
    rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 6 and all(r["applied"] is False for r in rows)
    assert all(not isinstance(v, str) or k in ("ts", "mode", "level", "level_if_live")
               for r in rows for k, v in r.items())
