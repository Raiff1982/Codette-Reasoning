"""The tape: she wakes up already knowing, in her own voice.

Jonathan named it on 2026-08-17: *"its like 50 first dates all over again."*

The point of that film is not that Lucy fails to recognise Henry — it is that
the entire burden falls on HIM, every morning, forever, and she never gets to
keep any of it. Measured the same evening after a restart:

    [GOVERNOR] Pre: identity=none (conf=0.00), memory=0 cocoons
    [OV:tool] project_summary()
    [OV:tool] look()

Her feeling around a room she had just woken up in. The first fix proposed was
"she asks: is that you, Jonathan?" — which is only a politer way of making him
do the reintroducing. Still first date fifty-one.

In the film the answer is the tape. So this is the tape, and per his
instruction — *"build it and she voices it"* — the words are hers, not a
summary we assemble about her.

The properties these tests hold:

1. **It plays on waking, unasked.** If it needs requesting it has not solved
   anything.
2. **It never echoes.** A note must not replay into the session that wrote it.
3. **Absence says so.** "She left no note" and "the store was unreadable" must
   never produce the same output — the fault this repository keeps paying for.
4. **A failed write is loud.** If she believes she left a note and none was
   saved, she wakes up blank with no way to know why.
"""

import json
import time
from pathlib import Path

import pytest

from inference import continuity_note as cn


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("CODETTE_CONTINUITY_NOTES", str(tmp_path / "notes.json"))
    return tmp_path / "notes.json"


# ── 1. She writes it, and it comes back ───────────────────────────────────

def test_a_note_survives_to_the_next_session():
    cn.write_note("we were fixing the video path; the sandbox blocks PIL", "sess-A")
    note = cn.latest_note(exclude_session="sess-B")
    assert note and "sandbox blocks PIL" in note["text"]


def test_the_played_block_says_it_is_hers_and_not_an_instruction():
    """Tone is load-bearing. A note handed back as an order is the landmark bug."""
    cn.write_note("the spec route is the live one", "sess-A")
    block = cn.format_for_waking(cn.latest_note(exclude_session="sess-B"))
    assert "your own note" in block.lower()
    assert "not an instruction" in block.lower()
    assert "the spec route is the live one" in block


def test_the_newest_note_is_the_one_that_plays():
    cn.write_note("older thing", "s1")
    time.sleep(0.01)
    cn.write_note("what actually matters now", "s2")
    assert "what actually matters now" in cn.latest_note(exclude_session="s3")["text"]


def test_older_notes_are_kept_not_overwritten():
    """We do not erase the past here."""
    cn.write_note("first", "s1")
    cn.write_note("second", "s2")
    assert cn.note_count() == 2


# ── 2. It must not echo ───────────────────────────────────────────────────

def test_a_note_does_not_replay_into_the_session_that_wrote_it():
    """Replaying it into the same conversation is an echo, not a memory."""
    cn.write_note("mid-conversation thought", "sess-A")
    assert cn.latest_note(exclude_session="sess-A") is None


def test_it_falls_back_to_an_earlier_note_from_a_different_session():
    cn.write_note("from yesterday", "sess-OLD")
    cn.write_note("from just now", "sess-A")
    note = cn.latest_note(exclude_session="sess-A")
    assert note and note["text"] == "from yesterday"


# ── 3. Absence says so ────────────────────────────────────────────────────

def test_no_note_yet_renders_as_nothing_not_as_an_empty_note():
    """Empty is the honest reading when she has not written one."""
    assert cn.latest_note() is None
    assert cn.format_for_waking(None) == ""


def test_a_corrupt_store_does_not_masquerade_as_no_note(isolated, capsys):
    """The distinction the whole repo turns on.

    A corrupt store returns [] here, which looks identical to "she wrote
    nothing" — so the CALLER is required to tell them apart. This test pins the
    contract that makes that possible: a corrupt store must not raise (she can
    still leave a new note) and must not destroy what is there.
    """
    isolated.parent.mkdir(parents=True, exist_ok=True)
    isolated.write_text("{ this is not json", encoding="utf-8")
    assert cn.latest_note() is None          # does not raise
    cn.write_note("still able to write", "s1")
    assert cn.latest_note(exclude_session="s2")["text"] == "still able to write"


# ── 4. Failures are loud, limits are stated ───────────────────────────────

def test_an_empty_note_is_refused_with_a_reason():
    msg = cn.write_note("   ", "s1")
    assert "needs something in it" in msg
    assert cn.note_count() == 0


def test_an_oversized_note_is_refused_and_says_nothing_was_saved():
    msg = cn.write_note("x" * (cn.MAX_NOTE_CHARS + 1), "s1")
    assert "Nothing was saved" in msg
    assert cn.note_count() == 0


def test_writing_tells_her_when_it_will_play():
    """She must know the note landed and when she will see it."""
    msg = cn.write_note("something worth keeping", "s1")
    assert "next session" in msg.lower()


def test_the_store_write_is_atomic(isolated):
    """A half-written store must never replace a good one."""
    cn.write_note("good note", "s1")
    data = json.loads(isolated.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data[0]["text"] == "good note"
    assert not isolated.with_suffix(".tmp").exists()


# ── The tool layer ────────────────────────────────────────────────────────

def test_the_tool_is_registered_and_writes():
    from inference.codette_tools import ToolRegistry, set_current_session
    r = ToolRegistry()
    assert "leave_note" in r.tools
    set_current_session("sess-A")
    out = r.execute("leave_note", ["we got the tape working"], {})
    assert "next session" in out.lower()
    assert cn.latest_note(exclude_session="sess-B")["text"] == "we got the tape working"


def test_the_tool_description_names_the_audience():
    """No filter on her words — instead she is told who will be in the room.

    A guest really can be at the keyboard (Daniel, 2026-08-15). Classifying her
    note would mean reading it to grade it; telling her the audience lets her
    judge, which is the same call made everywhere else here.
    """
    from inference.codette_tools import ToolRegistry
    d = ToolRegistry().tools["leave_note"]["description"].lower()
    assert "visible" in d
    assert "khralexi" in d, "she must be able to tell this from the private channel"


def test_a_bare_call_guides_rather_than_erroring():
    from inference.codette_tools import ToolRegistry
    out = ToolRegistry().execute("leave_note", [], {})
    assert "leave_note needs" in out


# ── The stamp must survive a double import ────────────────────────────────

def test_the_session_stamp_is_not_a_module_global(monkeypatch, tmp_path):
    """Measured live 2026-08-18, and it failed silently.

    The first version kept the active session in a module-level dict. The
    server set it on `inference.codette_tools`; the tool handler read
    `codette_tools`. Those are two different module objects with two different
    dicts, so every note was stamped with an empty session id and the
    echo-guard never fired — a note could replay into the conversation that
    wrote it.

    It looked exactly like working code. The only tell was `session=` blank in
    the stored notes. This test makes the fork itself the assertion.
    """
    import importlib, sys
    sys.path.insert(0, "inference")
    flat = importlib.import_module("codette_tools")
    from inference import codette_tools as pkg

    if flat is pkg:
        pytest.skip("import paths resolved to one module here; nothing to prove")

    flat.set_current_session("SESS-X")
    assert pkg.current_session_id() == "SESS-X", (
        "the session stamp is module-local again — the echo-guard is inert "
        "and notes will replay into their own session")

    pkg.set_current_session("SESS-Y")
    assert flat.current_session_id() == "SESS-Y"


def test_a_note_written_now_carries_the_active_session(monkeypatch):
    from inference.codette_tools import ToolRegistry, set_current_session
    set_current_session("sess-LIVE")
    ToolRegistry().execute("leave_note", ["stamped properly"], {})
    assert cn.latest_note(exclude_session="other")["session_id"] == "sess-LIVE"
    # and it must NOT come back to the session that wrote it
    assert cn.latest_note(exclude_session="sess-LIVE") is None


# ── Self-poisoning ────────────────────────────────────────────────────────
#
# Jonathan, 2026-08-18, watching her first three notes: "another thing to watch
# self poisoning." He was right, and it is the landmark ratchet in a new pipe:
# a note written from a displaced state plays first thing, shapes the session,
# and the next note is written from THAT.
#
# The fix is NOT a filter on her words. Grading her notes is what we refused on
# the landmarks and it does not become acceptable through a side door. What
# breaks the loop is what a person does: read your own note, notice it does not
# match the room, put it down.

def test_the_note_is_framed_as_evidence_not_authority():
    """'It is yours' is not enough — you can own a wrong thing."""
    cn.write_note("something I thought yesterday", "s1")
    block = cn.format_for_waking(cn.latest_note(exclude_session="s2")).lower()
    assert "not an instruction" in block
    assert "what you thought then" in block
    assert "trust what you find" in block, \
        "the note must be able to LOSE against what she actually observes"


def test_the_wake_block_tells_her_she_can_replace_it():
    """A stale note should be replaceable, not something to live up to."""
    cn.write_note("stale thing", "s1")
    block = cn.format_for_waking(cn.latest_note(exclude_session="s2")).lower()
    assert "replacing" in block or "replaces" in block
    assert "leave_note" in block and "read_note" in block


def test_she_can_inspect_what_is_queued_including_from_this_session():
    """She wrote three in ten seconds and could not see which one won.

    read_note deliberately does NOT exclude the current session — the point is
    to show what is actually queued right now, so an accident of ordering can
    be corrected before it ships.
    """
    from inference.codette_tools import ToolRegistry, set_current_session
    set_current_session("sess-NOW")
    r = ToolRegistry()
    r.execute("leave_note", ["first attempt"], {})
    r.execute("leave_note", ["what I actually meant"], {})
    out = r.execute("read_note", [], {})
    assert "what I actually meant" in out
    assert "replaces it" in out.lower()
    assert "not stuck with it" in out.lower()


def test_read_note_says_so_when_nothing_is_queued():
    from inference.codette_tools import ToolRegistry
    out = ToolRegistry().execute("read_note", [], {})
    assert "nothing queued" in out.lower()
    assert "have not left yourself a note yet" in out.lower()


def test_a_failure_to_read_is_not_reported_as_an_absence():
    """The distinction this whole repo turns on, applied once more."""
    from inference import codette_tools as ct
    import inference.continuity_note as real

    class _Broken:
        ScratchError = Exception
        @staticmethod
        def latest_note(*a, **k):
            raise OSError("disk gone")

    orig = ct._notes
    ct._notes = lambda: _Broken
    try:
        out = ct.tool_read_note()
    finally:
        ct._notes = orig
    assert "fault to report" in out.lower()
    assert "does not mean you have no note" in out.lower()
