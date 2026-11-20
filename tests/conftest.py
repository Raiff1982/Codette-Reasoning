"""Test-session guards.

THE PROBLEM THIS EXISTS FOR
---------------------------
Running the suite used to write synthetic cocoons into Codette's *live* memory
store. `tests/test_consciousness_stack.py` fires six fixture queries through the
real reasoning path, and each one persisted a cocoon to `cocoons/` exactly as a
real conversation would. Forty-five accumulated there between 2026-05-01 and
2026-07-30 before anyone noticed, and they were quarantined to
`cocoons/_backup_test_fixtures_20260730/`.

That is not cosmetic pollution. Those fixtures are indistinguishable from real
exchanges to every recall path — similarity search, domain recall, the cocoon
synthesizer, introspection. One of them has its response identical to its query,
a verbatim parrot, sitting in the memory of a system whose parroting we were
diagnosing. And because "last session" is inferred from gaps in the timeline, a
test run inserts a phantom session between two real ones.

Her memory is not a scratch space. Nothing synthetic belongs in it.

WHY A SWEEP RATHER THAN A REDIRECT
-----------------------------------
Cocoons are written from several places with different path roots — the cocooner
defaults to a relative "cocoons", the forge engine builds an absolute path from
its own __file__. Monkeypatching each writer means knowing all of them, today and
after the next refactor. Snapshotting the directory and removing only what the
run itself created catches every writer without needing to enumerate them.

The sweep is conservative: it removes only files that did not exist when the
session started, and it reports what it removed rather than cleaning silently.
Pre-existing cocoons are never touched.

AMENDED 2026-11-19: REDIRECT, NOT SWEEP
---------------------------------------
The text above is left as written. The sweep fixed cocoon FILES, but measured
on 2026-11-19 one full run still added 11 rows to data/codette_memory.db (her
unified memory, SQLite, which the sweep never saw) and rewrote Code7e's state.
And the sweep itself was dangerous: it listed the cocoons folder by name (her
dreams are in it) and deleted every new .json -- including a real cocoon her
live server writes while the suite runs.

So now every runtime store is REDIRECTED before any test imports anything:
CODETTE_RUNTIME_ROOT (reasoning_forge/runtime_paths.py) points her memory DB,
the forge's cocoon folder, Code7e, Nexis and the optimizer at a session temp
folder, and CODETTE_GOVERNOR_LOG does the same for the governor log. With the
variables unset -- her live system -- every path is exactly what it was.

What replaced the sweep only REPORTS. It compares the size and modification
time of her real stores, and the cocoons folder's own modification time,
before and after the session. It reads no contents, lists no folder, counts no
rows and deletes nothing. A change is printed as a lead: on her machine the
live server may have written during the run, which is not a test fault.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Set at import, before any test module (and so any store) is imported.
_RUNTIME = Path(tempfile.mkdtemp(prefix="codette-test-runtime-"))
os.environ["CODETTE_RUNTIME_ROOT"] = str(_RUNTIME)
os.environ.setdefault("CODETTE_GOVERNOR_LOG", str(_RUNTIME / "logs" / "governor_decisions.log"))

# Her real stores, watched by machinery only (size, mtime). Never opened.
WATCHED = [
    REPO / "data" / "codette_memory.db",
    REPO / "data" / "codette_memory.db-wal",
    REPO / "data" / "manifold_telemetry.db",
    REPO / "data" / "optimizer_state.json",
    REPO / "data" / "optimizer_shadow.jsonl",
    REPO / "reasoning_forge" / ".logs" / "code7e_quantum_cocoon.json",
    REPO / "reasoning_forge" / ".logs" / "nexis_signal_memory.db",
    REPO / "logs" / "governor_decisions.log",
    REPO / "cocoons",          # the folder's own mtime changes when an entry is added
]


def _fingerprint():
    out = {}
    for p in WATCHED:
        try:
            st = os.stat(p)
            out[p] = (st.st_size if p.is_file() else None, st.st_mtime_ns)
        except OSError:
            out[p] = None
    return out


@pytest.fixture(scope="session", autouse=True)
def keep_her_memory_clean():
    """Tests write to a temp runtime folder; her real stores are only watched."""
    before = _fingerprint()
    yield
    after = _fingerprint()
    changed = [str(p.relative_to(REPO)) for p in WATCHED if before[p] != after[p]]
    if changed:
        print("\n[conftest] her real stores changed during this session (reported, nothing "
              "removed; on her machine the live server may be the writer):\n  " + "\n  ".join(changed))
    shutil.rmtree(_RUNTIME, ignore_errors=True)
