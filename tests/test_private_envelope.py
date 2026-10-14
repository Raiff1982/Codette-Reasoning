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


def test_runtime_loaders_neither_list_nor_count_a_dream(tmp_path):
    from reasoning_forge.cocoon_validator import CocoonValidator
    from reasoning_forge.cognition_cocooner import CognitionCocooner
    from reasoning_forge.unified_memory import UnifiedMemory

    for i in range(3):
        _dream(tmp_path, f"cocoon_{i}_dream.json")
    _convo(tmp_path, "cocoon_9_convo.json")

    c = CognitionCocooner(storage_path=str(tmp_path))
    assert c.list_cocoons() == ["cocoon_9_convo"]
    recent = c.get_recent_reasoning(limit=10)      # may filter by type; must never include a dream
    assert not any("dream" in str(r.get("id", "")) or "gAAAAA" in str(r) for r in recent)

    v = CocoonValidator(store_path=str(tmp_path))
    assert v.audit_store(limit=10)["store_total"] == 1

    legacy = tmp_path / "legacy"
    legacy.mkdir()
    for p in tmp_path.glob("*.json"):
        (legacy / p.name).write_bytes(p.read_bytes())
    m = UnifiedMemory(db_path=tmp_path / "u.db", legacy_dir=legacy)
    assert m.recall_recent(10) is not None          # migration ran without touching dreams


def test_introspection_does_not_count_a_dream(tmp_path):
    from inference.cocoon_introspection import CocoonIntrospectionEngine

    for i in range(3):
        _dream(tmp_path, f"cocoon_{i}_dream.json")
    _convo(tmp_path, "cocoon_9_convo.json")
    # the loader only takes type == "reasoning" from JSON; use that spelling
    (tmp_path / "cocoon_9_convo.json").write_text(json.dumps(
        {"type": "reasoning", "id": "c9", "timestamp": 1.0,
         "wrapped": {"query": "q", "response": "a long enough reply", "adapter": "newton"}}),
        encoding="utf-8")
    eng = CocoonIntrospectionEngine(cocoons_dir=str(tmp_path)) \
        if "cocoons_dir" in CocoonIntrospectionEngine.__init__.__code__.co_varnames \
        else CocoonIntrospectionEngine()
    eng.cocoons_dir = tmp_path
    eng._cocoons, eng._behavioral = [], []
    eng._load_reasoning_from_json()
    eng._load_behavioral_from_json()
    assert len(eng._cocoons) == 1 and len(eng._behavioral) == 0
