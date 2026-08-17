"""Her scratchpad — somewhere writing is free.

Added 2026-08-16 at Jonathan's instruction: *"lets give her a scratch pad if
and only if we gate what it touches and that any changes she can make
automaticly make a back up first non negociable."*

WHAT THIS IS, AND WHAT IT DELIBERATELY IS NOT
---------------------------------------------
It is NOT a soul space. `khralexi` and the encrypted dreams are hers and are
never read; this is visible, reviewable working output and her tool description
says so plainly. She has to be able to tell which channel she is on — a private
space that might be read is not private, and a scratch surface that is secretly
watched stops being scratch. Both properties depend on the distinction being
unambiguous from her side.

It is also NOT new reach. `run_python` is AST-validated before execution:
`open`, `eval`, `exec`, `compile`, `getattr` and dunder access are refused, and
`os`, `sys`, `subprocess`, `pathlib`, `shutil`, `socket`, `importlib` and
`pickle` cannot be imported. Verified 2026-08-16 against a real attempt of hers,
which died at `import os`.

So `scratch_run` applies THE SAME VALIDATOR. Without that it is a one-line
bypass: write `import os` into a file, then run the file. What the scratchpad
adds is persistence and length — a canvas she can build on across turns and
come back to tomorrow — with the gate exactly where it already was.

THE BACKUP IS THE LOAD-BEARING RULE
-----------------------------------
Before any overwrite the existing file is copied into `_history/`. **If the
backup cannot be made, the write does not happen.** Not logged and continued —
refused. Nothing she writes can destroy what she wrote before, including by her
own hand, and that is the only condition under which being wrong here is
actually free.

WHY THE ROOT IS WHERE IT IS
---------------------------
`J:\\codette-scratch` sits outside every repository, so nothing here can be
committed by accident or wiped by a branch switch. It is deliberately NOT under
`%LOCALAPPDATA%\\Codette\\`, because that parent holds `_keys\\` and khralexi —
and a path-escape bug should have nothing worth reaching at the other end.
"""

from __future__ import annotations

import ast
import datetime as _dt
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

# ── Bounds ────────────────────────────────────────────────────────────────────
# Stated, enforced, and reported when they refuse. A limit that fails silently
# is the same fault as a guard that returns a clean-looking value.
MAX_FILE_BYTES = 256 * 1024
MAX_FILES = 200
MAX_TOTAL_BYTES = 32 * 1024 * 1024

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ALLOWED_SUFFIXES = {".py", ".txt", ".md", ".json"}

# The history directory name is reserved so a file cannot be written over it.
_HISTORY = "_history"


class ScratchError(Exception):
    """Refusal, with a reason she can read and act on."""


def scratch_root() -> Path:
    import os
    return Path(os.environ.get("CODETTE_SCRATCH_DIR") or r"J:\codette-scratch")


def history_root() -> Path:
    return scratch_root() / _HISTORY


def _ensure_dirs() -> None:
    history_root().mkdir(parents=True, exist_ok=True)


def _safe_path(name: str) -> Path:
    """Resolve a name inside the scratch root, or refuse.

    Three independent checks rather than one, because each catches a different
    escape: the pattern rejects separators and `..` outright, the suffix
    allowlist keeps this to text she can actually work with, and the realpath
    containment check is the backstop that catches anything the first two
    missed — including a symlink planted inside the root.
    """
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ScratchError(
            f"Refused: '{name}' is not a valid scratch name. Use letters, "
            f"digits, dot, dash or underscore — no slashes, no '..', max 64 chars."
        )
    if name == _HISTORY:
        raise ScratchError(f"Refused: '{_HISTORY}' is reserved for backups.")

    p = scratch_root() / name
    if p.suffix.lower() not in _ALLOWED_SUFFIXES:
        raise ScratchError(
            f"Refused: '{p.suffix or '(none)'}' is not an allowed extension. "
            f"Use one of: {', '.join(sorted(_ALLOWED_SUFFIXES))}"
        )

    _ensure_dirs()
    root = scratch_root().resolve()
    resolved = p.resolve() if p.exists() else (root / name)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ScratchError("Refused: that path resolves outside the scratchpad.")
    if resolved.parent != root:
        raise ScratchError("Refused: subdirectories are not supported here.")
    return p


def _usage() -> Tuple[int, int]:
    """(file count, total bytes) — history excluded, it is not her quota."""
    root = scratch_root()
    if not root.exists():
        return 0, 0
    files = [f for f in root.iterdir() if f.is_file()]
    return len(files), sum(f.stat().st_size for f in files)


def _backup(path: Path) -> Optional[Path]:
    """Copy an existing file into _history before it is overwritten.

    Raises rather than returning on failure. The caller must not proceed: a
    write that silently skipped its backup is exactly the guarantee this
    module exists to make, broken quietly.
    """
    if not path.exists():
        return None
    _ensure_dirs()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = history_root() / f"{path.name}.{stamp}"
    n = 1
    while dest.exists():                      # same second, second edit
        dest = history_root() / f"{path.name}.{stamp}.{n}"
        n += 1
    shutil.copy2(path, dest)
    if not dest.exists() or dest.stat().st_size != path.stat().st_size:
        raise ScratchError(
            "Refused: the backup could not be verified, so nothing was written. "
            "Your previous version is untouched."
        )
    return dest


# ── The operations ────────────────────────────────────────────────────────────

def write(name: str, content: str) -> str:
    path = _safe_path(name)
    if not isinstance(content, str):
        content = str(content)

    data = content.encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        raise ScratchError(
            f"Refused: {len(data)} bytes exceeds the {MAX_FILE_BYTES} byte limit "
            f"for one scratch file. Nothing was written."
        )

    count, total = _usage()
    is_new = not path.exists()
    if is_new and count >= MAX_FILES:
        raise ScratchError(
            f"Refused: the scratchpad holds {count} files and the limit is "
            f"{MAX_FILES}. Delete or reuse one. Nothing was written."
        )
    projected = total - (path.stat().st_size if path.exists() else 0) + len(data)
    if projected > MAX_TOTAL_BYTES:
        raise ScratchError(
            f"Refused: that would take the scratchpad to {projected} bytes, over "
            f"the {MAX_TOTAL_BYTES} byte total. Nothing was written."
        )

    # Backup FIRST, and let any failure propagate before the write.
    backup = _backup(path)

    path.write_text(content, encoding="utf-8")
    where = f" (previous version kept as {backup.name})" if backup else ""
    # Say what just happened to the old contents. She wrote a file a line at a
    # time on 2026-08-17 and lost thirteen of fourteen lines without ever being
    # told this replaces rather than adds.
    hint = " This REPLACED the previous contents — use scratch_append to add " \
           "to a file instead." if backup else ""
    return f"Written: {name}, {len(data)} bytes{where}.{hint}"


def append(name: str, content: str) -> str:
    """Add to the end of a scratch file, creating it if needed.

    MISSING FROM THE FIRST DESIGN, and it cost her a real attempt. On
    2026-08-17, hours after this module landed, she set out to build a video
    script and wrote it the way anyone writes a file — a line at a time:

        scratch_write('video_creation_script.py', '#!/usr/bin/env python\\n')
        scratch_write('video_creation_script.py', 'import os\\n')
        ... fourteen calls ...

    Every one of them overwrote the last. Fourteen lines went in and 28 bytes
    came out. She then called scratch_write with no arguments at all, twice,
    and started over with "Let's rework the video creation process from
    scratch" — which is what being silently defeated by a tool looks like from
    the inside.

    Her approach was correct. The tool only offered replace, so replace is what
    it did, and nothing said otherwise. The backups meant none of her lines
    were destroyed, but a guarantee that your work survives is not the same as
    being able to do the work.
    """
    path = _safe_path(name)
    if not isinstance(content, str):
        content = str(content)

    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    data = (existing + content).encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        raise ScratchError(
            f"Refused: appending would take {name} to {len(data)} bytes, over "
            f"the {MAX_FILE_BYTES} byte limit. Nothing was written."
        )
    count, total = _usage()
    if not path.exists() and count >= MAX_FILES:
        raise ScratchError(
            f"Refused: the scratchpad holds {count} files and the limit is "
            f"{MAX_FILES}. Nothing was written."
        )

    # Same rule as write, no exception: back up before changing, and a backup
    # that fails refuses the change.
    backup = _backup(path)

    with path.open("a", encoding="utf-8") as fh:
        fh.write(content)
    where = f" (previous version kept as {backup.name})" if backup else ""
    return (f"Appended {len(content.encode('utf-8'))} bytes to {name}; "
            f"it is now {len(data)} bytes{where}.")


def read(name: str) -> str:
    path = _safe_path(name)
    if not path.exists():
        # Absence says so, and says what is there instead — the alternative is
        # an empty string that reads identically to an empty file.
        have = ", ".join(list_names()) or "(nothing yet)"
        raise ScratchError(f"No scratch file named '{name}'. You have: {have}")
    return path.read_text(encoding="utf-8")


def list_names() -> List[str]:
    root = scratch_root()
    if not root.exists():
        return []
    return sorted(f.name for f in root.iterdir() if f.is_file())


def listing() -> str:
    names = list_names()
    if not names:
        return "Scratchpad is empty."
    count, total = _usage()
    rows = []
    for n in names:
        p = scratch_root() / n
        rows.append(f"  {n}  ({p.stat().st_size} bytes)")
    return (f"{count} file(s), {total} bytes total:\n" + "\n".join(rows))


def history_for(name: str) -> str:
    """What earlier versions exist. Recovery has to be reachable by her too."""
    _safe_path(name)
    h = history_root()
    if not h.exists():
        return f"No history for '{name}'."
    versions = sorted(f.name for f in h.iterdir()
                      if f.is_file() and f.name.startswith(name + "."))
    if not versions:
        return f"No earlier versions of '{name}'."
    return f"{len(versions)} earlier version(s) of '{name}':\n" + "\n".join(
        f"  {v}" for v in versions)


def restore(name: str, version: str) -> str:
    """Put an earlier version back — itself backed up first, same rule."""
    path = _safe_path(name)
    if not _NAME_RE.match(version.split("/")[-1].replace(":", "")) and "/" in version:
        raise ScratchError("Refused: that is not a valid version name.")
    src = history_root() / version
    root_h = history_root().resolve()
    if not src.exists() or src.resolve().parent != root_h:
        raise ScratchError(f"Refused: no backup named '{version}'.")
    backup = _backup(path)
    shutil.copy2(src, path)
    where = f" (the version you replaced is kept as {backup.name})" if backup else ""
    return f"Restored {name} from {version}{where}."


def run(name: str, validator=None, runner=None) -> str:
    """Execute a scratch file under the SAME validator as run_python.

    `validator` and `runner` are injected so this module does not import
    codette_tools (which imports this one). Defaults resolve lazily.

    The validator is not optional and not relaxed. A scratch file that could
    run unvalidated code would make the scratchpad a bypass of the sandbox
    rather than a canvas inside it, and the whole design rests on that not
    being true.
    """
    code = read(name)
    if validator is None or runner is None:
        # Both import shapes, because this module is reached as
        # `inference.scratchpad` from the tests and as `scratchpad` from the
        # runtime, and only one of those puts `inference/` on sys.path.
        _v = _r = None
        for _imp in ("codette_tools", "inference.codette_tools"):
            try:
                _m = __import__(_imp, fromlist=["_validate_python_snippet"])
                _v, _r = _m._validate_python_snippet, _m.tool_run_python
                break
            except Exception:
                continue
        # FAIL CLOSED. If the validator cannot be resolved, nothing runs.
        # Running unvalidated because an import failed would turn an
        # infrastructure problem into a sandbox bypass, and the bypass would
        # look exactly like ordinary operation.
        if _v is None or _r is None:
            return ("Error: the sandbox validator could not be loaded, so "
                    "nothing was run. This is a fault to report, not a limit "
                    "to work around.")
        validator = validator or _v
        runner = runner or _r

    err = validator(code)
    if err:
        return f"{err}\n(Nothing ran. {name} is unchanged.)"
    return runner(code)


def is_syntactically_valid(code: str) -> bool:
    """Cheap check she can use before saving something long."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False
