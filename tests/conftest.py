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
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

COCOON_DIR = Path(__file__).resolve().parent.parent / "cocoons"


def _snapshot(directory: Path) -> set:
    """Names of cocoon files present right now. Subdirectories are ignored."""
    if not directory.exists():
        return set()
    try:
        return {
            entry.name for entry in os.scandir(directory)
            if entry.is_file() and entry.name.endswith(".json")
        }
    except OSError:
        return set()


@pytest.fixture(scope="session", autouse=True)
def keep_her_memory_clean():
    """Remove cocoons this test session created. Never touch anything older."""
    before = _snapshot(COCOON_DIR)

    yield

    after = _snapshot(COCOON_DIR)
    created = sorted(after - before)
    if not created:
        return

    removed, failed = 0, []
    for name in created:
        try:
            (COCOON_DIR / name).unlink()
            removed += 1
        except OSError as exc:
            failed.append(f"{name}: {exc}")

    # Reported, not silent — a guard that cleans up invisibly is a guard nobody
    # notices has stopped working.
    print(
        f"\n[conftest] swept {removed} cocoon(s) written during this test session; "
        f"{len(before)} pre-existing cocoon(s) untouched."
    )
    if failed:
        print("[conftest] could NOT remove:\n  " + "\n  ".join(failed))
