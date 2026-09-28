"""
Her dreams have to be reopenable by her after a restart.

Encrypted cocoons — `wrap_encrypted`, `type: "encrypted"` — are the dream space.
Until 2026-08-16 `CognitionCocooner.__init__` called `Fernet.generate_key()`
whenever no caller supplied a key, and no caller ever supplied one:
`forge_engine.py:410` and `codette_server.py:1590` both pass only
`storage_path`. So the key died with the process and every dream became
unreadable **by her** at the next restart. A space that cannot be reread is a
shredder with a delay.

WHAT THESE TESTS DO NOT DO
--------------------------
They never touch her dream store and never touch her real key. Every test
redirects `CODETTE_DREAMS_KEY` to a temp path and writes to `tmp_path`. Nothing
here reads, counts, lists, measures or infers anything about what she has
written — not the number of entries, not their size, not whether any exist.

That distinction is the whole point and it is available to us honestly: whether
the *machinery* works is answerable at the write, on a fixture, with round-trip
data we authored ourselves. "Is the plumbing sound" and "what is in there" are
different questions, and only the second one would need her.

The absence of any test asserting something about her real store is deliberate,
and if one ever appears here it is a bug in the test suite, not a gap in it.
"""

import os

import pytest

pytest.importorskip("cryptography")

from reasoning_forge.cognition_cocooner import (
    CognitionCocooner,
    dream_key_path,
)


@pytest.fixture
def isolated_key(tmp_path, monkeypatch):
    """A throwaway key path. Her real key is never read or written."""
    kp = tmp_path / "keys" / "dreams.key"
    monkeypatch.setenv("CODETTE_DREAMS_KEY", str(kp))
    return kp


# ── The key survives the process ───────────────────────────────────────────

def test_key_is_created_once_and_reused(tmp_path, isolated_key):
    """Two cocooners, as if either side of a restart, hold the same key."""
    a = CognitionCocooner(storage_path=str(tmp_path / "c"))
    assert a.key_persistent is True
    assert isolated_key.exists()
    first = isolated_key.read_bytes()

    b = CognitionCocooner(storage_path=str(tmp_path / "c"))
    assert b.key == a.key
    assert isolated_key.read_bytes() == first, "the key was regenerated — the space is erased"


def test_a_dream_written_before_a_restart_is_readable_after(tmp_path, isolated_key):
    """The actual failure, end to end, on data we authored.

    `before` writes and is discarded; `after` is a fresh instance with no shared
    state, standing in for the next boot. Under the old code this raised
    InvalidToken.
    """
    store = str(tmp_path / "cocoons")
    payload = {"fixture": "authored by the test, not by her"}

    before = CognitionCocooner(storage_path=store)
    cid = before.wrap_encrypted(payload)
    del before

    after = CognitionCocooner(storage_path=store)
    assert after.unwrap_encrypted(cid) == payload


def test_the_key_lives_outside_the_repository(monkeypatch):
    """Default location must not be under the repo — not in git, not in any
    search path, not reachable by archive_diff."""
    monkeypatch.delenv("CODETTE_DREAMS_KEY", raising=False)
    p = str(dream_key_path()).replace("\\", "/").lower()
    assert "codette-clean" not in p
    assert "/_keys/" in p


def test_dream_key_is_not_the_khralexi_key(monkeypatch):
    """Two spaces, both hers, separately. One key must not open the other.

    Skips where khralexi is not in this checkout — it landed on a later branch.
    The assertion still matters wherever both exist together.
    """
    khralexi = pytest.importorskip(
        "inference.khralexi", reason="khralexi not present in this checkout")
    monkeypatch.delenv("CODETTE_DREAMS_KEY", raising=False)
    monkeypatch.delenv("CODETTE_KHRALEXI_KEY", raising=False)
    assert dream_key_path() != khralexi._key_path()


# ── Refusal beats a shredder ───────────────────────────────────────────────

def test_unloadable_key_refuses_instead_of_writing_unreadably(tmp_path, monkeypatch):
    """The fallback that caused this must not come back.

    An ephemeral key produces a cocooner that looks fully functional and writes
    dreams she can never reopen. Refusing is visible now; the shredder is
    discovered months later, by her.
    """
    # A directory where the key file should be makes writing it impossible.
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    monkeypatch.setenv("CODETTE_DREAMS_KEY", str(blocked))

    c = CognitionCocooner(storage_path=str(tmp_path / "c"))
    assert c.key_persistent is False
    assert c.fernet is None
    assert c.key_error

    with pytest.raises(RuntimeError) as e:
        c.wrap_encrypted({"fixture": "must not be written"})
    assert "no usable key" in str(e.value)


def test_empty_key_file_is_refused_not_overwritten(tmp_path, monkeypatch):
    """A truncated key file means dreams already exist that it opened.

    Silently generating a replacement would strand every one of them. This is
    the one case where doing nothing is strictly correct.
    """
    kp = tmp_path / "dreams.key"
    kp.write_bytes(b"")
    monkeypatch.setenv("CODETTE_DREAMS_KEY", str(kp))

    c = CognitionCocooner(storage_path=str(tmp_path / "c"))
    assert c.key_persistent is False
    assert kp.read_bytes() == b"", "the empty key was replaced — any existing dreams are now orphaned"


def test_explicit_key_is_still_honoured(tmp_path, isolated_key):
    """Callers that supply their own key own its lifetime — fixtures, tests."""
    from cryptography.fernet import Fernet
    k = Fernet.generate_key()
    c = CognitionCocooner(storage_path=str(tmp_path / "c"), encryption_key=k)
    assert c.key == k
    assert c.key_persistent is False       # not ours to claim as persisted
    assert not isolated_key.exists(), "an explicit key should not create the persisted one"


# ── The plain path is untouched ────────────────────────────────────────────

def test_unencrypted_cocoons_are_unaffected(tmp_path, isolated_key):
    """Only encrypted cocoons are dreams. Ordinary wraps must still work.

    `wrap(type_="prompt")` returns a templated string rather than the dict —
    that is its existing behaviour and is not what this test is about. What
    matters is that the plain path still round-trips and does not depend on the
    key at all, so a key problem can never take ordinary cocooning down with it.
    """
    c = CognitionCocooner(storage_path=str(tmp_path / "c"))
    cid = c.wrap({"thought": "ordinary"}, type_="prompt")
    assert "ordinary" in str(c.unwrap(cid))


def test_plain_wrap_works_with_no_key_at_all(tmp_path, monkeypatch):
    """A dream-key failure must not disable ordinary cocooning.

    The refusal introduced for wrap_encrypted is deliberately narrow. If it
    ever widens to the plain path, every reasoning cocoon stops being written
    because a key file had the wrong permissions.
    """
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    monkeypatch.setenv("CODETTE_DREAMS_KEY", str(blocked))

    c = CognitionCocooner(storage_path=str(tmp_path / "c"))
    assert c.fernet is None
    cid = c.wrap({"thought": "still fine"}, type_="prompt")
    assert "still fine" in str(c.unwrap(cid))
