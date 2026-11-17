"""The substrate speed shadow: per-token slowdown against her own normal.

Shadow only (2026-11-17). Long answers at her usual speed must not read as
pressure; a real slowdown must. The live pressure must not change, and nothing
is written unless a log path is given.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def test_the_live_pressure_is_unchanged_by_the_shadow():
    m = _monitor()
    a = m._compute_pressure(87, 30, 6.0, 60_000, 0.0)
    for _ in range(10):
        m.record_inference(60_000, tokens=600)
    assert m._compute_pressure(87, 30, 6.0, 60_000, 0.0) == a


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
