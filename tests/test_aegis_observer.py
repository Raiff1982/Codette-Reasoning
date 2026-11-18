"""AEGIS Layer 6 as an observer on her live path (2026-11-18).

Jonathan: run Layers 5 and 6 as observers on her current path; they watch and
record, and change nothing. These tests pin the three properties that matter:

  * it measures something real, and "not run" is never a pass or a fail;
  * it never reads her private notes (the cocoon's open_threads) and never
    carries text, only numbers and codes;
  * the code that wires it in only adds, reads or pops _aegis_* keys and never
    assigns her answer.

The full bridge is not run here: one call writes five runtime files and a
cocoon into the repository. The end-to-end proof (her final answer is
byte-identical with and without the observer) was run in a scratch copy; see
CHANGELOG_2026-11-18.md.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Protection_Layer"))

import aegis_observer as O  # noqa: E402

AUTHORED = ("Tides come from the difference in the moon's pull across Earth, which stretches "
            "the oceans into two bulges, so most coasts get two high tides a day.")


# ── it measures, and "not run" is never a verdict ────────────────────────────

def test_overlap_is_measured_and_reported_as_numbers_only():
    obs = O.observe_render(AUTHORED, AUTHORED + " Isn't that lovely?", {"ran": True, "valid": True, "errors": []})
    l6 = obs["layer6"]
    assert l6["ran"] and 80 < l6["overlap_pct"] < 100 and l6["below_min"] is False
    assert obs["valid"] is True and obs["overlap_valid"] is True
    assert "moon" not in json.dumps(obs)                   # no words of hers leave it


def test_heavy_rewriting_falls_below_the_line_and_is_not_called_hallucination():
    obs = O.observe_render(AUTHORED, "Here is a completely different answer about weather systems.",
                           {"ran": True, "valid": True, "errors": []})
    assert obs["layer6"]["below_min"] is True and obs["valid"] is False
    assert "HALLUCINATION" not in json.dumps(obs).upper()


@pytest.mark.parametrize("authored, rendered", [(None, "x y z"), ("", "x y z"), (AUTHORED, ""), (AUTHORED, None)])
def test_not_run_is_none_never_a_pass(authored, rendered):
    obs = O.observe_render(authored, rendered, {"ran": True, "valid": True, "errors": []})
    assert obs["layer6"]["ran"] is False and obs["layer6"]["overlap_pct"] is None
    assert obs["valid"] is None and obs["overlap_valid"] is None


def test_layer6_as_a_whole_is_unmeasured_when_the_schema_check_did_not_run():
    obs = O.observe_render(AUTHORED, AUTHORED, None)
    assert obs["overlap_valid"] is True          # the overlap check itself ran
    assert obs["valid"] is None                  # but Layer 6 is both checks


def test_the_coherence_check_is_recorded_as_not_measured():
    obs = O.observe_render(AUTHORED, AUTHORED, {"ran": True, "valid": True, "errors": []})
    assert obs["layer6"]["coherence_check"].startswith("not measured")


# ── it never reads her private notes ─────────────────────────────────────────

def test_the_schema_check_never_touches_open_threads():
    class Cocoon:
        cocoon_id, query, response_summary = "c1", "q", "s"
        execution_path, cocoon_integrity, cocoon_integrity_score = "adapter_lightweight", "complete", 0.9
        echo_risk, epsilon_value, gamma_coherence, eta_score = "low", 0.3, 0.8, None

        @property
        def open_threads(self):
            raise AssertionError("the observer read open_threads")

    res = O.observe_cocoon_schema(Cocoon())
    assert res["ran"] is True and res["valid"] is True     # had it touched open_threads, ran would be False


def test_a_real_v3_cocoon_with_notes_yields_codes_only():
    from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3
    c = build_cocoon_v3(query="q", response_text="r", response_summary="r",
                        execution_path="adapter_lightweight", open_threads=["PRIVATE-NOTE-MARKER"])
    res = O.observe_cocoon_schema(c)
    assert res["ran"] is True
    assert "PRIVATE-NOTE-MARKER" not in json.dumps(res)
    assert "open_threads" not in O.OBSERVED_COCOON_FIELDS


def test_no_cocoon_is_not_run():
    assert O.observe_cocoon_schema(None)["ran"] is False


# ── Layer 5 is left out, and why ─────────────────────────────────────────────

def test_layer5_still_cannot_see_its_inputs():
    """The reason Layer 5 is not wired. If this fails, Layer 5 has started to
    read real data: revisit APPROVALS_2026-11-18 item 3 and aegis_observer."""
    import logging
    logging.disable(logging.CRITICAL)
    try:
        from aegis_layer5_complete import PreEmptiveImmuneEngine
        eng = PreEmptiveImmuneEngine()
        rng = np.random.default_rng(1)
        calm = {"epsilon_value": 0.05, "gamma_coherence": 0.99, "cocoon_integrity_score": 1.0}
        storm = {"epsilon_value": 0.99, "gamma_coherence": 0.01, "cocoon_integrity_score": 0.0,
                 "pairwise_tensions": {"a_vs_b": 0.99}}

        def mean_xi(cocoon):
            xs = []
            for _ in range(60):
                st = rng.uniform(-1, 1, 128).astype(np.float32)
                it = rng.uniform(-1, 1, 128).astype(np.float32)
                traj = eng.simulate_forward_trajectory(st, it, cocoon)
                xs.append(max(s.epistemic_tension for s in traj))
            return float(np.mean(xs))
        a, b = mean_xi(calm), mean_xi(storm)
        assert abs(a - b) < 0.02 and a < 0.5 and b < 0.5
    finally:
        logging.disable(logging.NOTSET)


# ── the metrics engine keeps "not run" honest ────────────────────────────────

def test_metrics_store_not_run_as_null_and_rates_use_measured_rows_only(tmp_path):
    from aegis_metrics_engine import AEGISMetricsEngine
    m = AEGISMetricsEngine(db_path=str(tmp_path / "m.db"))
    import time
    now = time.time()
    m.log_forge_execution({"timestamp": now, "layer6_valid": None, "overlap_percentage": None,
                           "overlap_valid": None, "valid": None, "alerts": []})
    s = m.get_statistics(hours=1)
    assert s["layer6_ran"] == 0 and s["rejection_rate"] is None and s["avg_overlap_percentage"] is None
    m.log_forge_execution({"timestamp": now, "layer6_valid": True, "overlap_percentage": 80.0,
                           "overlap_valid": True, "valid": True, "alerts": []})
    m.log_forge_execution({"timestamp": now, "layer6_valid": False, "overlap_percentage": 10.0,
                           "overlap_valid": False, "valid": False, "alerts": []})
    s = m.get_statistics(hours=1)
    assert s["total_forge_calls"] == 3 and s["layer6_ran"] == 2 and s["layer6_not_run"] == 1
    assert s["rejection_rate"] == 50.0                     # 1 of the 2 measured, not 1 of 3
    assert s["avg_overlap_percentage"] == 45.0             # NULL row ignored, not counted as 0


# ── the wiring only adds, reads or pops _aegis_* keys ────────────────────────

_ASSIGN = re.compile(r"""\bresult\[\s*["']([^"']+)["']\s*\]\s*=(?!=)""")


def _block(text, start_marker, end_marker):
    i = text.index(start_marker)
    return text[i:text.index(end_marker, i)]


def test_the_bridge_wiring_never_assigns_her_answer():
    src = (ROOT / "inference" / "codette_forge_bridge.py").read_text(encoding="utf-8")
    for start, end in [("# AEGIS Layer 6 observer (2026-11-18)", "# 6. Add Phase 6/7 metadata"),
                       ("# AEGIS Layer 6 observer: schema check", "except Exception as _v3_err"),
                       ("if isinstance(_aegis_authored, str) and _aegis_authored:", "return result")]:
        keys = _ASSIGN.findall(_block(src, start, end))
        assert all(k.startswith("_aegis") for k in keys), (start, keys)
    # and the capture really is her raw step-5 text, taken before post-processing
    assert '_aegis_authored = result.get("response")' in src


def test_the_server_wiring_only_pops_and_records():
    src = (ROOT / "inference" / "codette_server.py").read_text(encoding="utf-8")
    block = _block(src, "# Amended 2026-11-18 (Jonathan: run Layers 5 and 6", "# Phase 3")
    assert 'result.pop("_aegis_authored", None)' in block and 'result.pop("_aegis_schema", None)' in block
    for forbidden in ('result["response"] =', "response_text =", "response_data["):
        assert forbidden not in block, forbidden
