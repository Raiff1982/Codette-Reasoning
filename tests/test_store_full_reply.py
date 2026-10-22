"""Replies are stored whole (up to a safety limit), cut only on the way into context, and the cut is stated.

2026-10-22, Jonathan: the store cut every reply at 2,000 characters (60 of 3,380 exchanges hit it),
destroying the tail. The real limit is her 8k context window, which applies when a memory is READ
into her context, not when it is kept.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reasoning_forge.unified_memory import UnifiedMemory


@pytest.fixture
def mem(tmp_path):
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    return UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=legacy)


def _stored(mem_obj, cid):
    c = sqlite3.connect(mem_obj.db_path)
    try:
        resp, meta = c.execute("select response, metadata_json from cocoons where id=?", (cid,)).fetchone()
    finally:
        c.close()
    return resp, json.loads(meta or "{}")


def test_a_long_reply_is_stored_whole_and_not_called_cut(mem):
    reply = "word " * 1000                                   # 5,000 chars
    cid = mem.store("a question", reply, adapter="base")
    resp, meta = _stored(mem, cid)
    assert resp == reply and "truncated" not in meta          # nothing lost, nothing flagged
    assert mem.cut_status({"response": resp, "metadata": meta}) == "complete"


def test_recall_hands_consumers_what_it_always_did_and_says_it_was_cut(mem):
    reply = "word " * 1000
    mem.store("a question about words", reply, adapter="base")
    for got in (mem.recall_recent(1)[0], mem.recall_relevant("a question about words", max_results=1)[0]):
        assert len(got["response"]) == mem.READ_CAP            # an 8k window is never flooded
        assert got["response_cut_for_context"] is True and got["response_chars"] == len(reply)


def test_a_reply_past_the_safety_limit_is_cut_and_marked_as_cut(mem):
    reply = "x" * (mem.MAX_STORED_RESPONSE + 5000)
    cid = mem.store("q", reply, adapter="base")
    resp, meta = _stored(mem, cid)
    assert len(resp) == mem.MAX_STORED_RESPONSE
    assert meta["truncated"] is True and meta["original_chars"] == len(reply)
    assert mem.cut_status({"response": resp, "metadata": meta}) == "cut"


def test_cut_and_complete_are_different_facts_including_for_the_old_rows(mem):
    assert mem.cut_status({"response": "y" * 1999}) == "complete"
    assert mem.cut_status({"response": "y" * mem.LEGACY_CAP}) == "legacy_cap"     # probably cut by the old limit
    assert mem.cut_status({"response": "short", "metadata": '{"truncated": true}'}) == "cut"


def test_the_json_cocoon_keeps_the_reply_and_recall_cuts_it(tmp_path, monkeypatch):
    pytest.importorskip("cryptography")
    monkeypatch.setenv("CODETTE_DREAMS_KEY", str(tmp_path / "k" / "dreams.key"))
    from reasoning_forge.cognition_cocooner import CognitionCocooner
    from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3
    co = CognitionCocooner(storage_path=str(tmp_path / "c"))
    reply = "token " * 1000
    v3 = build_cocoon_v3(query="tell me about tokens", response_text=reply[:200],
                         response_summary="tokens", execution_path="adapter_lightweight",
                         model_inference_invoked=True, active_perspectives=["newton"])
    cid = co.wrap_reasoning("tell me about tokens", reply, adapter="base", v3_cocoon=v3)
    on_disk = json.loads((tmp_path / "c" / f"{cid}.json").read_text(encoding="utf-8"))["wrapped"]
    assert on_disk["response"] == reply and on_disk["truncated"] is False
    got = co.recall_relevant("tokens tell", max_results=1, min_overlap=1)[0]
    assert len(got["response"]) == 2000 and got["response_cut_for_context"] is True
