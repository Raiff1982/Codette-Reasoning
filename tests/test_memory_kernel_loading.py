"""The kernel loader read fields that a reasoning cocoon has never had.

`LivingMemoryKernel._load_cocoons_from_disk` built every memory from `title` /
`summary` / `quote` — the shape of the old foundational cocoons — and never
looked at `wrapped`. A reasoning cocoon keeps its text in `wrapped.response`, so
every one loaded with `content=""` and its own filename as a title.

Measured against the live store before the fix: **2,412 of 2,445 loaded memories
(98.7%) were empty shells**, and 2,410 of those files did contain real text. Ten
files on disk contain "cobalt anchor" and none survived the load.

The part that made it invisible: it did not skip what it could not read. It
stored and counted it, so the boot log reported "Loaded 2445 cocoon memories" and
the orchestrator was wired to 2,445 empty records — feeding DynamicMemoryEngine,
WisdomModule and MemoryWeighting.

After the fix, against the same store: 2,443 loaded, 0 empty, 2 genuinely empty
and 1 unreadable reported rather than counted.

Every test writes its own cocoons to a tmp_path. Her real store is never opened.
"""

import json

import pytest

from reasoning_forge.memory_kernel import LivingMemoryKernel


def _write(directory, name, payload):
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def store(tmp_path):
    d = tmp_path / "cocoons"
    d.mkdir()
    return d


def test_reasoning_cocoon_text_is_loaded(store):
    """THE BUG. `wrapped.response` was never read."""
    _write(store, "cocoon_1_r.json", {
        "type": "reasoning",
        "wrapped": {"query": "what did you learn?",
                    "response": "a distinctive answer about aardvarks"},
    })
    k = LivingMemoryKernel(cocoon_dir=str(store))
    assert len(k.memories) == 1
    assert "aardvarks" in k.memories[0].content


def test_reasoning_v3_cocoon_text_is_loaded(store):
    _write(store, "cocoon_2_v3.json", {
        "type": "reasoning_v3",
        "v3": {"query": "and this one?",
               "user_response_text": "a distinctive answer about zeppelins"},
    })
    k = LivingMemoryKernel(cocoon_dir=str(store))
    assert "zeppelins" in k.memories[0].content


def test_the_old_foundational_shape_still_loads(store):
    """Additive: the fields it always read must keep working."""
    _write(store, "cocoon_joy.json", {
        "title": "Joy", "summary": "a foundational memory", "emotion": "joy",
    })
    k = LivingMemoryKernel(cocoon_dir=str(store))
    assert k.memories[0].title == "Joy"
    assert k.memories[0].emotional_tag == "joy"


def test_query_becomes_the_title_when_there_is_none(store):
    """Titling a memory with its own filename made 2,410 records unsearchable."""
    _write(store, "cocoon_3.json", {
        "type": "reasoning",
        "wrapped": {"query": "do you recall the evening?", "response": "I do."},
    })
    k = LivingMemoryKernel(cocoon_dir=str(store))
    assert k.memories[0].title == "do you recall the evening?"
    assert "cocoon_3" not in k.memories[0].title


def test_empty_cocoons_are_not_stored_as_memories(store):
    """The heart of it: a record with no content is not a memory, and counting
    it as one is what hid this for months."""
    _write(store, "cocoon_4_empty.json", {"type": "reasoning", "wrapped": {}})
    _write(store, "cocoon_5_real.json", {
        "type": "reasoning", "wrapped": {"query": "q", "response": "real content here"},
    })
    k = LivingMemoryKernel(cocoon_dir=str(store))
    assert len(k.memories) == 1
    assert all((m.content or "").strip() for m in k.memories)


def test_what_could_not_be_loaded_is_reported(store, caplog):
    _write(store, "cocoon_6_empty.json", {"type": "reasoning", "wrapped": {}})
    (store / "cocoon_7_broken.json").write_text("{not json", encoding="utf-8")
    _write(store, "cocoon_8_real.json", {
        "type": "reasoning", "wrapped": {"query": "q", "response": "content"},
    })

    with caplog.at_level("WARNING"):
        LivingMemoryKernel(cocoon_dir=str(store))

    assert any("not loaded" in r.getMessage() for r in caplog.records), \
        "a loader that reports only its successes is the bug"


def test_searchable_after_loading(store):
    """What the whole thing is for: ten files on disk contained 'cobalt anchor'
    and the kernel could find none of them."""
    _write(store, "cocoon_9.json", {
        "type": "reasoning_v3",
        "wrapped": {"query": "remember this",
                    "response": "you told me not to forget: cobalt anchor"},
    })
    k = LivingMemoryKernel(cocoon_dir=str(store))
    found = [m for m in k.memories if "cobalt anchor" in m.content.lower()]
    assert len(found) == 1


def test_missing_directory_is_not_an_error(store, tmp_path):
    k = LivingMemoryKernel(cocoon_dir=str(tmp_path / "nope"))
    assert k.memories == []
