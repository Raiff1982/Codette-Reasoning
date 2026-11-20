"""The test suite never writes into her stores (2026-11-19).

Before this, one full run added 11 rows to data/codette_memory.db (on her
machine, her memory) and rewrote Code7e's state. conftest.py now sets
CODETTE_RUNTIME_ROOT to a temp folder before anything is imported; these tests
fail if any store path still points into the repository.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _inside(p, root):
    try:
        Path(p).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def test_the_suite_runs_with_a_temp_runtime_root():
    from reasoning_forge.runtime_paths import runtime_root
    root = runtime_root()
    assert os.environ.get("CODETTE_RUNTIME_ROOT") and not _inside(root, REPO)


def test_every_store_path_points_outside_the_repository():
    import reasoning_forge.unified_memory as um
    import reasoning_forge.optimizer_shadow as osh
    from reasoning_forge.runtime_paths import runtime_root
    for p in (um.DB_PATH, osh._TELEMETRY_DB, osh._STATE_PATH, osh._LOG_PATH,
              os.environ["CODETTE_GOVERNOR_LOG"]):
        assert _inside(p, runtime_root()) and not _inside(p, REPO), p


def test_the_forge_writes_under_the_runtime_root():
    from reasoning_forge.forge_engine import ForgeEngine
    from reasoning_forge.runtime_paths import runtime_root
    eng = ForgeEngine(orchestrator=None)
    if getattr(eng, "cocooner", None) is not None:
        assert _inside(eng.cocooner.storage_path, runtime_root())
    if getattr(eng, "code7e", None) is not None:
        assert _inside(eng.code7e.memory_path, runtime_root())
    if getattr(eng, "unified_memory", None) is not None:
        assert _inside(eng.unified_memory.db_path, runtime_root())


def test_unset_means_the_repository_exactly(monkeypatch):
    from reasoning_forge import runtime_paths
    monkeypatch.delenv("CODETTE_RUNTIME_ROOT", raising=False)
    assert runtime_paths.runtime_root() == REPO
