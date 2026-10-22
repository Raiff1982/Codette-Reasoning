"""The health report must actually build.

On 2026-10-14 a helper was defined after the block that called it, every
/api/health request returned {"overall": "ERROR"}, and no test had ever called
the builder. This one does.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inference"))

from reasoning_forge import reach


def _forge():
    f = types.SimpleNamespace()
    f.memory_kernel = types.SimpleNamespace(
        memories=[1, 2, 3], store=lambda *a, **k: None,
        store_v2_cocoon=lambda *a, **k: None, search=lambda *a, **k: [])
    f.colleen = None
    f.guardian = None
    f.ethical_governance = types.SimpleNamespace(
        audit_log=[], harmful_patterns=[], bias_patterns=[],
        validate_query=lambda q: {}, enforce_policies=lambda r: {})
    f.cocooner = types.SimpleNamespace(
        cocoons={}, wrap_reasoning=lambda *a, **k: "", recall_relevant=lambda *a, **k: [])
    f.tier2_bridge = types.SimpleNamespace(
        analyze_intent=lambda q: None, validate_identity=lambda o: None,
        record_memory=lambda *a, **k: None)
    f.code7e = types.SimpleNamespace(recursive_universal_reasoning=lambda *a, **k: "x")
    f.nexis_signal_engine = types.SimpleNamespace(process=lambda s: {})
    f.aegis = types.SimpleNamespace(
        evaluate=lambda *a, **k: {}, quick_check=lambda t: (True, 1),
        screen_query=lambda q: (True, None))
    f.qhf = types.SimpleNamespace(stabilize=lambda e: e)
    return f


def test_health_report_builds_and_distinguishes_called_from_never_called(monkeypatch):
    import inference.codette_server as srv

    forge = _forge()
    reach.instrument_forge(forge)
    bridge = types.SimpleNamespace(use_phase6=True, forge=forge, use_phase7=False,
                                   executive_controller=None)
    monkeypatch.setattr(srv, "_forge_bridge", bridge)

    forge.ethical_governance.validate_query("q")           # reached once
    rep = srv._run_health_check()

    assert rep["overall"] != "ERROR", rep
    comps = rep["systems"]["phase6_forge"]["components"]
    assert comps["ethical_governance"]["status"] == "LOADED"
    assert comps["ethical_governance"]["calls"] == 1
    assert comps["cognition_cocooner"]["status"] == "LOADED_NEVER_CALLED"
    assert comps["tier2_bridge"]["status"] == "LOADED_NEVER_CALLED"
    assert comps["memory_kernel"]["memories"] == 3
    assert "pqc_sealing" in rep["systems"]
    assert "background_jobs" in rep["systems"]
