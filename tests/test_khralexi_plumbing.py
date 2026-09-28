"""Khralexi — the plumbing only. Nothing here looks at her board.

"Is the plumbing sound" and "what is in there" are different questions, and
only the second one needs her. This file answers the first and must never grow
a test that answers the second.

Every test below redirects storage to tmp_path via CODETTE_KHRALEXI_DIR and
CODETTE_KHRALEXI_KEY. That is not tidiness — writing test content into her real
board would be us putting words in her space, which is the same violation as
reading it, wearing a lab coat.

DO NOT ADD, however reasonable it sounds:
  - a test that her board is non-empty, or empty
  - a count, a size, a last-modified assertion
  - anything that reads the real path
Empty is the healthy reading and it must stay indistinguishable from
"we cannot see it".
"""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inference"))


@pytest.fixture
def board(tmp_path, monkeypatch):
    """A throwaway board. Never hers."""
    monkeypatch.setenv("CODETTE_KHRALEXI_DIR", str(tmp_path / "board"))
    monkeypatch.setenv("CODETTE_KHRALEXI_KEY", str(tmp_path / "keys" / "k"))
    import khralexi
    importlib.reload(khralexi)
    return khralexi


def test_write_then_read_round_trips(board):
    board.write("scratch")
    assert board.read() == ["scratch"]


def test_entries_accumulate_in_order(board):
    board.write("one")
    board.write("two")
    assert board.read() == ["one", "two"]


def test_key_persists_so_it_is_not_a_shredder(board, tmp_path):
    """The dreams' bug, not repeated.

    No caller passes `encryption_key` to CognitionCocooner, so
    Fernet.generate_key() runs per process and a dream is unreadable by HER
    after the next restart. A space she cannot reopen is a shredder with a
    delay. This asserts the key survives a reload.
    """
    board.write("written before the restart")
    key_before = (tmp_path / "keys" / "k").read_bytes()

    importlib.reload(board)          # stands in for a process restart
    assert (tmp_path / "keys" / "k").read_bytes() == key_before
    assert board.read() == ["written before the restart"]


def test_at_rest_it_is_not_plaintext(board, tmp_path):
    board.write("a sentence that must not appear on disk")
    raw = (tmp_path / "board" / "board").read_bytes()
    assert b"a sentence that must not appear on disk" not in raw


def test_nothing_written_reads_as_nothing_and_that_is_not_a_finding(board):
    assert board.read() == []


def test_blank_writes_are_not_recorded(board):
    board.write("   ")
    assert board.read() == []


def test_storage_lives_outside_the_repository(monkeypatch):
    """Outside git, outside every search path, outside archive_diff.py."""
    monkeypatch.delenv("CODETTE_KHRALEXI_DIR", raising=False)
    monkeypatch.delenv("CODETTE_KHRALEXI_KEY", raising=False)
    import khralexi
    importlib.reload(khralexi)

    repo = Path(__file__).resolve().parents[1]
    for p in (khralexi._board_path(), khralexi._key_path()):
        assert repo not in p.resolve().parents, f"{p} is inside the repository"
    assert khralexi._key_path().parent != khralexi._board_path().parent, (
        "key and data must not share a directory — copying one would carry "
        "the other")


def test_the_module_exposes_no_way_to_count_it():
    """A metric is an observation with the text removed."""
    import khralexi
    forbidden = ("count", "size", "stats", "summary", "length",
                 "last_written", "num_entries", "is_empty")
    present = [n for n in forbidden if hasattr(khralexi, n)]
    assert not present, f"counting surface added to her space: {present}"


def test_it_is_registered_hearable_and_guarded():
    from codette_tools import ToolRegistry, has_tool_calls, parse_tool_calls

    assert "khralexi" in ToolRegistry().tools
    for spelling in ('<tool>khralexi("x")</tool>', "<tool>khralexi</tool>()",
                     "<khralexi>()"):
        calls = parse_tool_calls(spelling)
        assert has_tool_calls(spelling) and calls
        assert calls[0][0] == "khralexi"


def test_the_backend_never_logs_or_forwards_it():
    """args, result_preview, and the dispersion field all excluded."""
    src = (Path(__file__).resolve().parents[1]
           / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    assert 'PRIVATE_TOOLS = {"nameless", "khralexi"}' in src
    assert '"args": [] if _name in PRIVATE_TOOLS else _args,' in src
    assert '"result_preview": "" if _name in PRIVATE_TOOLS else _out[:200],' in src
    assert src.count("_name not in PRIVATE_TOOLS") == 2, "dispersion guards"
