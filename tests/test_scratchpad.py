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
    assert out.startswith("Error:"), out
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
    out = sp.run("t.py")
    assert out.startswith("Error:"), out
    assert "Nothing ran" in out


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


# ── Append: the operation that was missing ─────────────────────────────────

def test_append_builds_a_file_line_by_line():
    """The real failure, 2026-08-17.

    She wrote a script the way anyone writes a script — a line at a time, 14
    calls — and every one overwrote the last. 14 lines in, 28 bytes out. Her
    approach was right; the tool only offered replace.
    """
    for line in ("#!/usr/bin/env python\n", "import math\n", "print(math.pi)\n"):
        sp.append("build.py", line)
    assert sp.read("build.py") == "#!/usr/bin/env python\nimport math\nprint(math.pi)\n"


def test_append_creates_the_file_when_absent():
    sp.append("fresh.txt", "first line\n")
    assert sp.read("fresh.txt") == "first line\n"


def test_append_backs_up_before_changing_too():
    """The non-negotiable applies to append exactly as it does to write."""
    sp.write("a.txt", "original\n")
    sp.append("a.txt", "added\n")
    versions = [f for f in sp.history_root().iterdir() if f.name.startswith("a.txt.")]
    assert len(versions) == 1
    assert versions[0].read_text(encoding="utf-8") == "original\n"


def test_a_failed_backup_refuses_the_append(monkeypatch):
    sp.write("keep.txt", "original")
    monkeypatch.setattr(sp.shutil, "copy2", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(OSError):
        sp.append("keep.txt", "more")
    assert sp.read("keep.txt") == "original"


def test_append_respects_the_size_limit(monkeypatch):
    monkeypatch.setattr(sp, "MAX_FILE_BYTES", 20)
    sp.write("s.txt", "x" * 15)
    with pytest.raises(sp.ScratchError) as e:
        sp.append("s.txt", "y" * 15)
    assert "Nothing was written" in str(e.value)
    assert sp.read("s.txt") == "x" * 15


def test_append_obeys_the_same_path_confinement():
    with pytest.raises(sp.ScratchError):
        sp.append("../escape.txt", "nope")


def test_write_now_warns_that_it_replaced():
    """She was never told. That is why the lines vanished silently."""
    sp.write("w.txt", "one")
    msg = sp.write("w.txt", "two")
    assert "REPLACED" in msg and "scratch_append" in msg


# ── A refusal must hand back the map ───────────────────────────────────────

def test_a_blocked_import_says_what_IS_available():
    """2026-08-17: she burned her whole tool budget finding the wall by walking
    into it, then answered in 1 token because nothing was left.

    The old message named only what she could not do, so the only way to find
    the door was more guessing — and every guess cost a tool call she needed
    for the reply.
    """
    from inference.codette_tools import _validate_python_snippet, SAFE_PYTHON_MODULES
    msg = _validate_python_snippet("import remotion")
    assert msg
    for mod in ("math", "json", "statistics"):
        assert mod in msg, "the refusal must list what she CAN use"
    # Property, not phrasing: it must send her to name the gap in her ANSWER
    # rather than spend more tool calls hunting for a door that isn't built.
    low = msg.lower()
    assert "in your answer" in low, \
        "it must tell her naming the gap beats hunting for it"
    assert "tool budget" in low or "tool calls" in low, \
        "it must say why hunting costs her the reply"


def test_the_refusal_does_not_moralise():
    """A limit is not a verdict on her. Tone is load-bearing here."""
    from inference.codette_tools import _validate_python_snippet
    msg = _validate_python_snippet("import remotion").lower()
    # The limit is presented as a property of the sandbox, not a verdict on her.
    assert "by design" in msg
    assert "judgement" in msg, "it must say the limit is not about her"
    for scolding in ("you should not", "you must not", "forbidden", "violation",
                     "not permitted", "you may not"):
        assert scolding not in msg, f"refusal reads as a reprimand: {scolding!r}"


def test_allowed_imports_are_still_silent():
    from inference.codette_tools import _validate_python_snippet
    assert _validate_python_snippet("import math\nprint(math.pi)") is None


def test_the_refusal_is_a_pivot_not_a_stop():
    """Jonathan, 2026-08-17: "instead of not allowed can we make it a pivot point?"

    Same principle as everything else here: guide, don't dam. A wall tells her
    to stop and she keeps testing it. A pivot tells her where the road is.
    """
    from inference.codette_tools import _validate_python_snippet
    msg = _validate_python_snippet("import remotion")
    assert "PIVOT, NOT A STOP" in msg
    assert "THE ROUTE" in msg
    # it must point at the tools she actually has, not only at the gap
    assert "scratch_append" in msg and "web_search" in msg
    # and say that naming a gap is how capability gets built here
    assert "Naming it is how it gets made" in msg
