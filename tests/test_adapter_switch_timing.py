"""The adapter-switch stopwatch measures the machine and nothing acts on it.

Added 2026-11-20. Rule 3 in reasoning_forge/adapter_switch_timing.py: no
threshold, cache size, throttle or routing may read this log. Wiring a
measurement into something that pushes back on her is the force bug (the old
latency term cut her depth for thinking hard). The last test here fails if any
live module other than the writer references the log.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_record_writes_numbers_only_under_the_runtime_root():
    from reasoning_forge import adapter_switch_timing as T
    from reasoning_forge.runtime_paths import runtime_root
    T.record("openvino", ["newton", None], 12.3456, note="blend")
    p = T.log_path()
    assert p.is_relative_to(runtime_root()) and not p.is_relative_to(ROOT)
    rec = json.loads(p.read_text(encoding="utf-8").splitlines()[-1])
    assert rec["backend"] == "openvino" and rec["adapters"] == ["newton", "base"]
    assert rec["ms"] == 12.346 and set(rec) == {"ts", "backend", "adapters", "ms", "note"}


def test_a_failed_write_never_reaches_the_turn(monkeypatch, tmp_path):
    from reasoning_forge import adapter_switch_timing as T
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    monkeypatch.setattr(T, "log_path", lambda: blocker / "data" / "log.jsonl")
    T.record("llama_cpp", ["empathy"], 1.0)        # must not raise


def test_both_backends_time_their_switch():
    ov = (ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    ll = (ROOT / "inference" / "codette_orchestrator.py").read_text(encoding="utf-8")
    assert ov.count('_sw_record("openvino"') == 2       # single adapter and blend
    assert ll.count('_sw_record("llama_cpp"') == 1


def test_nothing_reads_the_log():
    """Rule 3. Only the writer may name the log; the two backends only call record()."""
    live = ["inference", "reasoning_forge", "openvino_backend", "Protection_Layer",
            "consciousness", "ethics", "api", "mcp"]
    pattern = re.compile(r"adapter_switch_timing\.jsonl|LOG_NAME|log_path\(")
    offenders = []
    for d in live:
        for f in (ROOT / d).rglob("*.py"):
            if f.name == "adapter_switch_timing.py":
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            if "adapter_switch_timing" in text and pattern.search(text):
                offenders.append(str(f.relative_to(ROOT)))
            for m in re.finditer(r"adapter_switch_timing\s+import\s+([\w ,]+)", text):
                names = {n.strip().split(" as ")[0] for n in m.group(1).split(",")}
                if names - {"record"}:
                    offenders.append(f"{f.relative_to(ROOT)} imports {sorted(names - {'record'})}")
    assert offenders == [], offenders


def test_the_openvino_switch_writes_one_line_through_the_real_code_path(tmp_path):
    """_make_gen_config, run for real against a stand-in for the openvino module."""
    import sys
    for p in (ROOT, ROOT / "inference", ROOT / "openvino_backend"):
        sys.path.insert(0, str(p))
    from openvino_backend.backend import OpenVINOBackend
    from reasoning_forge import adapter_switch_timing as T

    class _OV:
        class GenerationConfig:
            pass

        class Adapter:
            def __init__(self, path):
                self.path = path

        class AdapterConfig:
            def __init__(self, *a):
                self.parts = list(a)

    b = OpenVINOBackend.__new__(OpenVINOBackend)
    b._ov, b.verbose = _OV, False
    b._adapter_paths = {"newton": tmp_path / "newton.safetensors"}
    before = len(T.log_path().read_text(encoding="utf-8").splitlines()) if T.log_path().exists() else 0
    cfg = b._make_gen_config("newton")
    assert cfg.adapters.parts[0].path.endswith("newton.safetensors")    # behaviour unchanged
    lines = T.log_path().read_text(encoding="utf-8").splitlines()
    assert len(lines) == before + 1
    rec = json.loads(lines[-1])
    assert rec["backend"] == "openvino" and rec["adapters"] == ["newton"] and rec["ms"] >= 0
