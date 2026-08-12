"""Regression tests for cocoon search.

`/api/search`, and therefore the `cocoon_search` MCP tool, returned an empty
list for every query it was ever given. On 2026-08-11 a search for "cobalt
anchor" came back with nothing while ten cocoon files on disk contained it, and
that was written up as "two stores; the search covers one".

It was not a store problem. The live database holds 3,732 cocoons and its FTS5
index matches "cobalt anchor" 27 times. Two separate faults, both silent:

1. `UnifiedMemory` had no `search` method at all, and the fallback kernel wired
   into `forge_engine` (`memory_kernel.LivingMemoryKernel`) has none either. The
   call site guarded both with `hasattr`, so neither branch ever executed and
   the endpoint fell through to `results = []`.
2. Both branches read dict rows with `getattr(row, "title", "")`, which returns
   the default for a dict — so even a working backend would have produced rows
   of empty strings.

A third fault sat behind them, in the cold-start migration: it matched
`type == "reasoning"` exactly, while the schema had moved to `reasoning_v3`.
1,992 of 2,452 files on disk — 81% — were dropped without a log line.

Every test uses a temp database and a temp legacy directory. Codette's real
store under data/codette_memory.db and her cocoons/ directory are never opened.
"""

import json

import pytest

from reasoning_forge.unified_memory import UnifiedMemory


@pytest.fixture
def mem(tmp_path):
    """A UnifiedMemory on a throwaway database with an empty legacy dir."""
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    return UnifiedMemory(db_path=tmp_path / "test_memory.db", legacy_dir=legacy)


# ── 1. the method exists and finds what is there ────────────────────────────

def test_search_method_exists(mem):
    """The server guards this call with hasattr. If it is ever removed again,
    the endpoint goes silent rather than failing."""
    assert hasattr(mem, "search"), "UnifiedMemory.search is what /api/search calls"
    assert callable(mem.search)


def test_search_finds_a_stored_phrase(mem):
    mem.store(query="what should I remember?",
              response="Remember the cobalt anchor when you wake up.",
              adapter="empathy")
    mem.store(query="unrelated", response="Nothing to do with it.", adapter="base")

    hits = mem.search("cobalt anchor")

    assert len(hits) >= 1
    assert any("cobalt anchor" in h["response"].lower() for h in hits)


def test_search_returns_dicts_with_populated_fields(mem):
    """The endpoint bug was `getattr(row, 'title', '')` on a dict. Rows are
    dicts and must be read with subscripts."""
    mem.store(query="the question", response="the answer", adapter="newton",
              domain="physics")

    (hit,) = mem.search("question")

    assert isinstance(hit, dict)
    assert hit["query"] == "the question"
    assert hit["response"] == "the answer"
    assert hit["adapter"] == "newton"
    assert hit["domain"] == "physics"
    assert hit["timestamp"] > 0
    # the failure mode being locked out: attribute access yields the default
    assert getattr(hit, "title", "<default>") == "<default>"


# ── 2. an empty result means empty ──────────────────────────────────────────

def test_search_does_not_fall_back_to_recent(mem):
    """`recall_relevant` substitutes the most recent cocoons when FTS matches
    nothing. That is correct for recall and wrong for search: it turns "no
    match" into a page of unrelated results, which is exactly how a broken
    search hides. `search` must return an empty list."""
    for i in range(5):
        mem.store(query=f"q{i}", response=f"ordinary content {i}", adapter="base")

    assert mem.search("zzzz-nonexistent-term-zzzz") == []
    # and the contrast that motivates the rule
    assert len(mem.recall_relevant("zzzz-nonexistent-term-zzzz")) > 0


def test_empty_query_returns_empty(mem):
    mem.store(query="something", response="something else")
    assert mem.search("") == []
    assert mem.search("   ") == []


# ── 3. user text is not FTS5 syntax ─────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "don't forget",          # apostrophe
    'she said "hello"',      # double quote — FTS phrase delimiter
    "anchor-point",          # hyphen — FTS NOT operator
    "a AND b OR c",          # bare boolean keywords
    "(parenthesis",          # unbalanced group
    "*",                     # bare wildcard
])
def test_search_survives_punctuation(mem, query):
    """FTS5 treats quotes, hyphens and bare booleans as syntax. Raw user text
    went straight into MATCH; anything with an apostrophe raised OperationalError
    inside a try/except that reported it as an empty result."""
    mem.store(query="context", response="don't forget the anchor-point she said")
    mem.search(query)  # must not raise


def test_search_respects_limit(mem):
    for i in range(12):
        mem.store(query=f"q{i}", response="the same recurring keyword here")
    assert len(mem.search("recurring", limit=5)) == 5


# ── 4. the cold-start migration covers the v3 schema ────────────────────────

def _write_cocoon(directory, name, payload):
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


def test_migration_imports_reasoning_v3(tmp_path):
    """The check was `type == "reasoning"`. Live cocoons are `reasoning_v3`."""
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    _write_cocoon(legacy, "cocoon_1_old.json", {
        "type": "reasoning",
        "wrapped": {"query": "old q", "response": "answer mentioning aardvarks",
                    "adapter": "base", "metadata": {"domain": "general"}},
    })
    _write_cocoon(legacy, "cocoon_2_v3.json", {
        "type": "reasoning_v3",
        "wrapped": {"query": "v3 q", "response": "answer mentioning zeppelins",
                    "adapter": "empathy", "metadata": {"domain": "general"}},
        "v3": {"query": "v3 q", "user_response_text": "answer mentioning zeppelins"},
    })

    mem = UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=legacy)

    assert len(mem.search("aardvarks")) == 1
    assert len(mem.search("zeppelins")) == 1, \
        "reasoning_v3 cocoons were silently dropped by the cold-start migration"


def test_migration_reads_v3_block_when_wrapped_is_absent(tmp_path):
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    _write_cocoon(legacy, "cocoon_3_v3only.json", {
        "type": "reasoning_v3",
        "v3": {"query": "only in the v3 block",
               "user_response_text": "distinctive marmalade response",
               "dominant_perspective": "philosophy"},
    })

    mem = UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=legacy)

    (hit,) = mem.search("marmalade")
    assert hit["adapter"] == "philosophy"


def test_migration_reports_what_it_declined(tmp_path, caplog):
    """The v3 gap stayed invisible because unrecognised files were dropped in
    silence. Anything not imported must be counted out loud."""
    legacy = tmp_path / "cocoons"
    legacy.mkdir()
    _write_cocoon(legacy, "cocoon_4_weird.json", {"type": "something_unknown"})

    with caplog.at_level("WARNING"):
        UnifiedMemory(db_path=tmp_path / "m.db", legacy_dir=legacy)

    assert any("unimported" in r.message.lower() or "unimported" in r.getMessage().lower()
               for r in caplog.records), "silent skips are the bug"
