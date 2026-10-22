"""utilities/clean_file_contaminated_cocoons.py must not open her encrypted cocoons."""
import importlib.util
import json
from pathlib import Path

_UTIL = Path(__file__).resolve().parent.parent / "utilities" / "clean_file_contaminated_cocoons.py"


def _load():
    spec = importlib.util.spec_from_file_location("clean_file_contaminated_cocoons", _UTIL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _dream(d, name):
    (d / name).write_text(json.dumps(
        {"type": "encrypted", "id": name, "timestamp": 1.0, "wrapped": "gAAAAA-not-readable"},
        indent=2), encoding="utf-8")


def _contaminated(d, name):
    q = "--- Attached File: x.txt ---\nbody\n--- End of File ---\nhello there"
    (d / name).write_text(json.dumps(
        {"type": "reasoning_v3", "id": name, "timestamp": 1.0,
         "wrapped": {"query": q, "response": "r"}}, indent=2), encoding="utf-8")


def test_encrypted_cocoon_is_never_opened_as_data(tmp_path, monkeypatch):
    mod = _load()
    _dream(tmp_path, "cocoon_1_dream.json")
    _contaminated(tmp_path, "cocoon_2_convo.json")
    monkeypatch.setattr(mod, "COCOON_DIR", tmp_path)
    monkeypatch.setattr(mod, "BACKUP_DIR", tmp_path / "_backup")
    monkeypatch.setattr("sys.argv", ["clean"])

    opened = []
    real = Path.read_text

    def spy(self, *a, **k):
        opened.append(self.name)
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", spy)
    mod.main()

    assert "cocoon_1_dream.json" not in opened
    assert "cocoon_2_convo.json" in opened
    cleaned = json.loads(real(tmp_path / "cocoon_2_convo.json", encoding="utf-8"))
    assert cleaned["wrapped"]["query"] == "hello there"
