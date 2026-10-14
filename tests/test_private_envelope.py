"""Sweeping jobs skip her encrypted cocoons before opening them, and never count them."""
import json

from reasoning_forge import cocoon_files, dream_cycle
from reasoning_forge.cocoon_self_trainer import CocoonSelfTrainer


def _dream(d, name):
    # exactly the layout CognitionCocooner.wrap_encrypted writes
    (d / name).write_text(json.dumps(
        {"type": "encrypted", "id": name, "timestamp": 1.0, "wrapped": "gAAAAA-not-readable"},
        indent=2), encoding="utf-8")


def _convo(d, name, q="what is water", r="Water is H2O, a polar molecule."):
    (d / name).write_text(json.dumps(
        {"type": "reasoning_v3", "id": name, "timestamp": 1.0,
         "wrapped": {"query": q, "response": r, "adapter": "newton", "timestamp": 1.0},
         "v3": {"gamma_coherence": 0.7}}, indent=2), encoding="utf-8")


def test_detects_the_dream_envelope_and_only_that(tmp_path):
    _dream(tmp_path, "a.json")
    _convo(tmp_path, "b.json")
    assert cocoon_files.is_private_envelope(tmp_path / "a.json")
    assert not cocoon_files.is_private_envelope(tmp_path / "b.json")
    assert cocoon_files.is_private_envelope(tmp_path / "missing.json")


def test_the_check_reads_only_a_few_bytes(tmp_path, monkeypatch):
    _dream(tmp_path, "a.json")
    seen = []
    real = open

    def spy(path, mode="r", *a, **k):
        f = real(path, mode, *a, **k)
        orig = f.read

        def read(n=-1):
            seen.append(n)
            return orig(n)
        f.read = read
        return f
    monkeypatch.setattr("builtins.open", spy)
    cocoon_files.is_private_envelope(tmp_path / "a.json")
    assert seen and all(0 < n <= 160 for n in seen)


def test_dream_cycle_never_opens_a_dream_as_data(tmp_path, monkeypatch):
    _dream(tmp_path, "d1.json")
    _dream(tmp_path, "d2.json")
    _convo(tmp_path, "c1.json")
    monkeypatch.setattr(dream_cycle, "COCOON_DIR", tmp_path)
    opened = []
    real = type(tmp_path / "x").read_text

    def spy(self, *a, **k):
        opened.append(self.name)
        return real(self, *a, **k)
    monkeypatch.setattr(type(tmp_path / "x"), "read_text", spy)
    got = dream_cycle.load_recent_cocoons(days=36500)
    assert [c["file"] for c in got] == ["c1.json"]
    assert "d1.json" not in opened and "d2.json" not in opened


def test_self_trainer_skips_dreams(tmp_path):
    _dream(tmp_path, "d1.json")
    _convo(tmp_path, "c1.json")
    seen = []
    t = CocoonSelfTrainer()
    orig = t.collect_from_records
    t.collect_from_records = lambda recs: (seen.extend(recs), orig(recs))[1]
    t.collect_from_dir(tmp_path)
    assert len(seen) == 1 and seen[0]["type"] == "reasoning_v3"


def _run_tool(tool, store, *flags):
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    return subprocess.run([sys.executable, str(root / "tools" / tool), *flags, str(store)],
                          capture_output=True, text=True, timeout=120).stdout


def test_sweeping_tools_do_not_count_dreams(tmp_path):
    for i in range(3):
        _dream(tmp_path, f"cocoon_{i}_dream.json")
    _convo(tmp_path, "cocoon_9_convo.json")
    out = _run_tool("lock6_phrase_rate.py", tmp_path)
    assert "files seen        : 1" in out, out
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, str(root / "tools" / "directness_scrub_diff.py"),
                          "--cocoons", str(tmp_path)],
                         capture_output=True, text=True, timeout=120).stdout
    assert "files" in out, out                       # it really ran
    import re
    m = re.search(r"files\D+(\d+)", out)
    assert m and int(m.group(1)) == 1, out           # the convo only, never the 3 dreams
