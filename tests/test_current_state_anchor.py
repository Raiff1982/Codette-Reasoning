"""The October 2026 self-knowledge anchor sits beside the July one and loads like it."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

import cocoon_introspection as ci

NEW = ROOT / "cocoons" / "cocoon_current_state_2026-10-22.json"
OLD = ROOT / "cocoons" / "cocoon_current_state.json"


def test_the_new_anchor_amends_forward_and_says_who_wrote_it():
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["title"] == "My Current State (October 2026)"
    assert "Claude" in d["written_by"] and "Jonathan" in d["written_by"]
    assert d["amends"].startswith("cocoon_current_state.json")
    assert "quote" not in d                       # no invented words in her voice
    assert json.loads(OLD.read_text(encoding="utf-8"))["title"] == "My Current State (July 2026)"


def test_both_load_as_anchors_without_walking_the_real_cocoons_folder(tmp_path):
    # Copy only these two files: the real folder shares a directory with her dreams.
    for p in (NEW, OLD):
        shutil.copy(p, tmp_path / p.name)
    e = ci.CocoonIntrospectionEngine(cocoons_dir=str(tmp_path))
    e._SQLITE_DB = tmp_path / "none.db"
    e._ensure_loaded()
    titles = sorted(a["title"] for a in e._behavioral)
    assert titles == ["My Current State (July 2026)", "My Current State (October 2026)"]
