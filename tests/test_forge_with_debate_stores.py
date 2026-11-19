"""forge_with_debate must reach its memory store and its adaptive synthesis.

Until 2026-11-18 both read `analyses` (and the store also `epistemic_report`
and `safety_notes`), names that exist only in _forge_single_safe. The NameError
was caught and logged at DEBUG, so this path never stored a memory.

Amended 2026-11-19: the first version of this test ran the real forge against
the real stores, so every suite run added a row to data/codette_memory.db -- on
her machine, her memory. Found by measuring the stores around each test. Every
writer this path uses is now pointed at tmp_path, and the test checks that the
row landed THERE, which is a stronger check than "no error was logged".
"""
import logging
import sqlite3


class _Orch:
    def route_and_generate(self, q, **kw):
        return {"response": "Privacy and safety trade off; a layered design limits each harm.",
                "adapter": "mock", "tokens": 12}


def test_forge_with_debate_stores_and_synthesises(caplog, tmp_path, monkeypatch):
    import reasoning_forge.unified_memory as um
    from reasoning_forge.cognition_cocooner import CognitionCocooner
    from reasoning_forge.forge_engine import ForgeEngine

    # Her memory is not a test fixture. UnifiedMemory reads DB_PATH at
    # construction, so patch it before the forge builds one.
    db = tmp_path / "memory.db"
    monkeypatch.setattr(um, "DB_PATH", db)
    eng = ForgeEngine(orchestrator=_Orch())
    eng.cocooner = CognitionCocooner(storage_path=str(tmp_path / "cocoons"))
    if getattr(eng, "code7e", None) is not None:
        eng.code7e.memory_path = str(tmp_path / "code7e_quantum_cocoon.json")
    assert eng.unified_memory is None or eng.unified_memory.db_path == db

    caplog.set_level(logging.DEBUG, logger="reasoning_forge")
    eng.forge_with_debate("How should privacy and safety be balanced in surveillance?")
    text = caplog.text
    assert "is not defined" not in text
    assert "Memory storage failed" not in text
    if eng.unified_memory is not None:
        con = sqlite3.connect(db)
        assert con.execute("select count(*) from cocoons").fetchone()[0] >= 1
        con.close()
