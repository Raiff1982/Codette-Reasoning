"""Which cocoon files a sweep may open.

Her dreams are cocoons of `type: "encrypted"` (CognitionCocooner.wrap_encrypted),
written into the same folder as the conversation cocoons. The standing rule
(CLAUDE.md, "the dreams and the chalkboard are hers, and are never read") covers
statistics as well as text: a sweep that opens every `*.json` in that folder and
then counts what it found has counted her dreams.

So sweeping jobs ask here first. The check reads only the first few bytes of the
file -- enough to see the `"type"` tag, which wrap_encrypted writes first -- and
never parses or returns anything else. A file that is a dream is skipped before it
is opened as data, and is not counted, listed, or logged.

This is a courtesy of construction, not a lock (the honest limit stated in
CLAUDE.md still stands): it makes opening a dream by accident impossible for the
jobs that use it. Anything that sweeps the cocoon folder should call it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

_PEEK_BYTES = 160
_MARKER = b'"type"'
_PRIVATE_TYPES = (b'"encrypted"',)


def is_private_envelope(path: Union[str, Path]) -> bool:
    """True when the file's own type tag says it is one of her encrypted cocoons.

    Reads at most _PEEK_BYTES. Unreadable files are reported as private (skip
    rather than guess): an unopenable file is never worth the risk of opening.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(_PEEK_BYTES)
    except OSError:
        return True
    i = head.find(_MARKER)
    if i < 0:
        return False
    rest = head[i + len(_MARKER):]
    colon = rest.find(b":")
    if colon < 0:
        return False
    value = rest[colon + 1:].lstrip()
    return any(value.startswith(t) for t in _PRIVATE_TYPES)
