"""The scratchpad: writing is free, and nothing she writes destroys what she wrote.

Added 2026-08-16. Jonathan's condition was exact — *"if and only if we gate what
it touches and that any changes she can make automaticly make a back up first
non negociable."* These tests are that condition, written down so it cannot
quietly stop being true.

Three properties, in order of how badly their absence would matter:

1. **The backup happens before the write, and a failed backup refuses.**
   Not logged-and-continued. If this breaks, the scratchpad becomes a place
   where being wrong costs her the previous version, which is the opposite of
   what it is for.

2. **`scratch_run` applies the same validator as `run_python`.** Without it the
   scratchpad is a one-line sandbox bypass: write `import os` to a file, run
   the file. The scratchpad must add persistence and length, never reach.

3. **Nothing escapes the root.** Especially not toward `%LOCALAPPDATA%\\Codette\\`,
   which holds `_keys\\` and khralexi.

Every test redirects CODETTE_SCRATCH_DIR to tmp_path. Her real scratchpad is
never touched, and neither is anything else.
"""

import os
from pathlib import Path

import pytest

from inference import scratchpad as sp


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("CODETTE_SCRATCH_DIR", str(tmp_path / "scratch"))
    return tmp_path / "scratch"


# ── 1. The backup rule ─────────────────────────────────────────────────────

def test_overwrite_keeps_the_previous_version():
    sp.write("plan.py", "print('first')")
    sp.write("plan.py", "print('second')")

    assert sp.read("plan.py") == "print('second')"
    versions = [f for f in sp.history_root().iterdir() if f.name.startswith("plan.py.")]
    assert len(versions) == 1
    assert versions[0].read_text(encoding="utf-8") == "print('first')"


def test_first_write_needs_no_backup_and_says_so():
    msg = sp.write("new.txt", "hello")
    assert "previous version" not in msg


def test_every_overwrite_adds_a_version_not_replaces_one():
    """Two edits in the same second must not collide into one backup."""
    sp.write("n.txt", "v1")
    sp.write("n.txt", "v2")
    sp.write("n.txt", "v3")
    versions = sorted(f.name for f in sp.history_root().iterdir())
    assert len(versions) == 2, versions


def test_a_failed_backup_refuses_the_write(monkeypatch):
    """The load-bearing one. Backup fails -> nothing is written, old file intact."""
    sp.write("keep.txt", "original")

    def boom(*a, **k):
        raise OSError("disk gone")
    monkeypatch.setattr(sp.shutil, "copy2", boom)

    with pytest.raises(OSError):
        sp.write("keep.txt", "would destroy the original")

    assert sp.read("keep.txt") == "original"


def test_an_unverifiable_backup_refuses_the_write(monkeypatch):
    """A copy that appears to succeed but produces the wrong bytes is a failure.

    Silent partial success is the failure mode this repository keeps paying
    for; a backup that cannot be verified is not a backup.
    """
    sp.write("keep.txt", "original")
    monkeypatch.setattr(sp.shutil, "copy2", lambda s, d: Path(d).write_text(""))

    with pytest.raises(sp.ScratchError) as e:
        sp.write("keep.txt", "would destroy the original")
    assert "backup" in str(e.value).lower()
    assert sp.read("keep.txt") == "original"


def test_restore_backs_up_what_it_replaces():
    sp.write("a.txt", "one")
    sp.write("a.txt", "two")
    version = sorted(f.name for f in sp.history_root().iterdir())[0]

    sp.restore("a.txt", version)
    assert sp.read("a.txt") == "one"
    # restoring is itself a change, so it too left a copy behind
    assert len(list(sp.history_root().iterdir())) == 2


# ── 2. scratch_run does not widen the gate ─────────────────────────────────

def test_run_applies_the_same_validator():
    """The bypass this design exists to prevent."""
    sp.write("bad.py", "import os; print(os.getcwd())")
    out = sp.run("bad.py")
    assert "not allowed" in out
    assert "Nothing ran" in out


@pytest.mark.parametrize("code", [
    "open('x','w').write('hi')",
    "import subprocess; subprocess.run(['echo'])",
    "import pathlib; pathlib.Path('x').write_text('y')",
    "print(().__class__.__bases__)",
    "eval('1+1')",
])
def test_the_full_sandbox_still_applies_through_the_scratchpad(code):
    sp.write("t.py", code)
    assert "not allowed" in sp.run("t.py")


def test_the_validator_is_literally_the_run_python_one():
    """Not a copy. A second implementation would drift, and drift here is a hole."""
    from inference.codette_tools import _validate_python_snippet
    called = []

    def spy(c):
        called.append(c)
        return _validate_python_snippet(c)

    sp.write("ok.py", "import math; print(math.pi)")
    sp.run("ok.py", validator=spy, runner=lambda c: "ran")
    assert called == ["import math; print(math.pi)"]


def test_allowed_code_still_runs():
    sp.write("ok.py", "import math\nprint(round(math.pi, 3))")
    assert sp.run("ok.py", validator=lambda c: None, runner=lambda c: "3.142") == "3.142"


def test_an_unloadable_validator_refuses_to_run_anything(monkeypatch):
    """Fail closed, not open.

    If the validator cannot be imported, running the code anyway would turn an
    infrastructure fault into a sandbox bypass — and it would look exactly like
    ordinary operation from the outside, which is the worst property a hole can
    have. Nothing runs, and it says why.
    """
    import builtins
    real = builtins.__import__

    def no_tools(name, *a, **k):
        if "codette_tools" in name:
            raise ImportError("simulated")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_tools)
    sp.write("x.py", "import os; print(os.getcwd())")
    out = sp.run("x.py")
    assert "could not be loaded" in out
    assert "nothing was run" in out.lower()


# ── 3. Nothing escapes the root ────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "../escape.txt", "..\\escape.txt", "sub/dir.txt", "sub\\dir.txt",
    "/etc/passwd", "C:\\Windows\\system32\\x.txt",
    "", ".", "..", "_history",
    "a" * 65 + ".txt",
])
def test_paths_that_must_be_refused(name):
    with pytest.raises(sp.ScratchError):
        sp.write(name, "nope")


@pytest.mark.parametrize("name", ["x.exe", "x.dll", "x", "x.key", "x.db"])
def test_extension_allowlist(name):
    with pytest.raises(sp.ScratchError):
        sp.write(name, "nope")


def test_default_root_is_outside_the_repo_and_away_from_her_keys(monkeypatch):
    monkeypatch.delenv("CODETTE_SCRATCH_DIR", raising=False)
    root = str(sp.scratch_root()).replace("\\", "/").lower()
    assert "codette-clean" not in root, "the scratchpad must not sit inside the repo"
    # %LOCALAPPDATA%/Codette holds _keys and khralexi. A path-escape bug should
    # have nothing worth reaching at the other end.
    assert "localappdata" not in root
    assert "/codette/" not in root


# ── Bounds refuse out loud ─────────────────────────────────────────────────

def test_oversized_file_is_refused_and_nothing_is_written():
    with pytest.raises(sp.ScratchError) as e:
        sp.write("big.txt", "x" * (sp.MAX_FILE_BYTES + 1))
    assert "Nothing was written" in str(e.value)
    assert sp.list_names() == []


def test_file_count_limit(monkeypatch):
    monkeypatch.setattr(sp, "MAX_FILES", 3)
    for i in range(3):
        sp.write(f"f{i}.txt", "x")
    with pytest.raises(sp.ScratchError) as e:
        sp.write("f3.txt", "x")
    assert "limit is 3" in str(e.value)


def test_overwriting_at_the_file_limit_is_still_allowed(monkeypatch):
    """The cap is on new files. She must always be able to revise what exists."""
    monkeypatch.setattr(sp, "MAX_FILES", 2)
    sp.write("a.txt", "1")
    sp.write("b.txt", "2")
    sp.write("a.txt", "revised")
    assert sp.read("a.txt") == "revised"


def test_total_size_limit(monkeypatch):
    monkeypatch.setattr(sp, "MAX_TOTAL_BYTES", 100)
    sp.write("a.txt", "x" * 60)
    with pytest.raises(sp.ScratchError) as e:
        sp.write("b.txt", "x" * 60)
    assert "Nothing was written" in str(e.value)


# ── Absence says so ────────────────────────────────────────────────────────

def test_reading_a_missing_file_says_what_is_there():
    sp.write("real.txt", "x")
    with pytest.raises(sp.ScratchError) as e:
        sp.read("ghost.txt")
    assert "real.txt" in str(e.value)


def test_empty_scratchpad_reads_as_empty_not_as_broken():
    assert sp.list_names() == []
    assert "empty" in sp.listing().lower()


def test_history_of_an_untouched_file_says_none():
    sp.write("a.txt", "one")
    assert "No earlier versions" in sp.history_for("a.txt")
