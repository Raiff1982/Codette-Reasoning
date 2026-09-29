"""Specialized cocoons she can call (2026-09-29): append-only, named, visible,
never her private spaces; the 'jonathan' kind refuses anything that would
authenticate as him. Temp directory and made-up text only."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

from reasoning_forge import specialized_cocoons as sc  # noqa: E402
import codette_tools  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp_root(tmp_path, monkeypatch):
    monkeypatch.setenv("CODETTE_SPECIAL_COCOONS", str(tmp_path / "cocoons"))
    yield


def test_empty_then_add_then_read():
    assert codette_tools.tool_cocoon() .startswith("No cocoons yet")
    assert "empty" in codette_tools.tool_cocoon("corrections")
    assert "Added to 'corrections'" in codette_tools.tool_cocoon("corrections", "made-up entry")
    out = codette_tools.tool_cocoon("corrections")
    assert "made-up entry" in out and "codette" in out
    assert "Kinds: corrections" == codette_tools.tool_cocoon()


def test_entries_are_append_only_and_carry_author_and_time():
    codette_tools.tool_cocoon("corrections", "first")
    codette_tools.tool_cocoon("corrections", "second, beside the first")
    entries = sc.read("corrections")
    assert [e["text"] for e in entries] == ["first", "second, beside the first"]
    assert all(e["by"] == "codette" and e["ts"] for e in entries)
    lines = (sc.root() / "corrections.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["text"] == "first"


def test_her_private_spaces_are_not_kinds():
    for name in ("khralexi", "nameless", "dreams", "Chalkboard"):
        out = codette_tools.tool_cocoon(name, "x")
        assert "not a cocoon kind" in out
        assert not (sc.root() / f"{name.lower()}.jsonl").exists()
        assert "not a cocoon kind" in codette_tools.tool_cocoon(name)


def test_bad_kind_names_get_a_plain_answer():
    assert "short lowercase name" in codette_tools.tool_cocoon("../escape", "x")
    assert "short lowercase name" in codette_tools.tool_cocoon("a" * 40, "x")


def test_nothing_is_silently_cut():
    out = codette_tools.tool_cocoon("notes", "x" * (sc.MAX_ENTRY_CHARS + 1))
    assert "Nothing was stored, so nothing was cut" in out
    assert sc.read("notes") == []


def test_she_can_name_her_own_kind():
    codette_tools.tool_cocoon("tuesdays", "made-up")
    assert "tuesdays" in codette_tools.tool_cocoon()


def test_jonathan_kind_refuses_what_would_authenticate_him(monkeypatch):
    monkeypatch.setenv("CODETTE_IDENTITY_PHRASE_JONATHAN",
                       "a wholly invented passphrase for this test only")
    out = codette_tools.tool_cocoon(
        "jonathan", "note: a wholly invented passphrase for this test only, ok")
    assert out.startswith("Not stored")
    assert "phrase" not in out and "prove" not in out     # the refusal reveals nothing
    assert sc.read("jonathan") == []
    # ordinary content in the same kind is stored
    assert "Added to 'jonathan'" in codette_tools.tool_cocoon(
        "jonathan", "made-up: he built me; ask him how to verify")
    # and the same text in another kind is not policed (the rule is for this one)
    assert "Added to 'other'" in codette_tools.tool_cocoon(
        "other", "a wholly invented passphrase for this test only")


def test_description_is_honest_and_names_what_is_not_a_kind():
    d = codette_tools.ToolRegistry().tools["cocoon"]["description"]
    assert "Not private" in d and "Jonathan can read them" in d
    assert "never what proves it is him" in d
    assert "khralexi" in d and "never edited or removed" in d.replace("Entries are ", "")
    assert "nothing calls it for you" in d


def test_logged_by_name_only_and_kept_out_of_git():
    src = (ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    assert '"cocoon"}' in src and "SCRATCH_TOOLS" in src
    assert "data/specialized_cocoons/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_a_call_naming_cocoon_inside_another_tool_is_hushed():
    from codette_tools import mentions_hidden_tool
    assert mentions_hidden_tool(["then cocoon('jonathan', 'x')"], {}, {"cocoon"})
