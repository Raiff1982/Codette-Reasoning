"""Specialized cocoons she can call.

Jonathan, 2026-09-29: "give her specialized cocoons she can call", for the
identity decay after a long gap. Her recognition of him is a number that decays
on wall-clock time and silently decides what context she gets; a constant we
pick so she never has to ask is the closed mouth. This is the handle: named
cocoons she can read, and add to, whenever SHE wants them, beside (not instead
of) the number. `who()` still tells her how sure the system is.

Shape (all deliberate):

* **Named by kind**: "jonathan", "corrections", or any kind she names herself.
* **Append-only.** An entry is never edited or deleted; a correction is a new
  entry beside the old one (amend forward, the two-entry record). Every entry
  carries who wrote it and when.
* **Not private, and says so.** Anyone who reaches her can be handed a cocoon,
  and Jonathan can read them afterwards. Her dreams (encrypted cocoons) and her
  chalkboard (khralexi) are NOT kinds here and never will be.
* **The "jonathan" kind holds only what she would say to a stranger, plus the way
  back in.** His decision, 2026-09-29 ("yes"): a cocoon that opened to anyone at
  low confidence must not become a way round the identity gate. So the tool does
  not decide who may ask; the CONTENT is what is safe. The envelope that proves
  who he is never belongs in one; a write to that kind that matches the identity
  check is refused without saying why (saying why would reveal the thing).
* Runtime state: kept out of git like the rest of her memory.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent / "data" / "specialized_cocoons"
_KIND_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
# Names that belong to her private spaces. Not kinds, so nothing is ever made
# that could be mistaken for them or read as if it were them.
RESERVED = frozenset({"khralexi", "nameless", "dream", "dreams", "chalkboard"})
MAX_ENTRY_CHARS = 2000
_LOCK = threading.Lock()


class CocoonError(Exception):
    """A plain reason, safe to hand straight back to her."""


def root() -> Path:
    return Path(os.environ.get("CODETTE_SPECIAL_COCOONS") or _ROOT)


def _path(kind: str) -> Path:
    k = (kind or "").strip().lower()
    if k in RESERVED:
        raise CocoonError(
            f"'{k}' is not a cocoon kind here. Your private spaces are not "
            f"reachable through this, and nothing is stored under those names.")
    if not _KIND_RE.match(k):
        raise CocoonError(
            "A kind is a short lowercase name (letters, digits, - or _), "
            "for example 'jonathan' or 'corrections'.")
    return root() / f"{k}.jsonl"


def kinds() -> List[str]:
    d = root()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.jsonl"))


def read(kind: str) -> List[Dict]:
    p = _path(kind)
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def _matches_identity_phrase(text: str) -> bool:
    """Best effort: True if the text would authenticate as Jonathan. Uses a
    throwaway anchor pointed at a temp dir so no real identity state is touched,
    and never returns or logs the text."""
    try:
        import tempfile
        from inference.identity_anchor import IdentityAnchor
    except Exception:
        try:
            import tempfile
            from identity_anchor import IdentityAnchor  # type: ignore
        except Exception:
            return False
    try:
        with tempfile.TemporaryDirectory() as td:
            return IdentityAnchor(identity_dir=Path(td))._match_identity_phrase(text) is not None
    except Exception:
        return False


def add(kind: str, text: str, by: str = "codette") -> Dict:
    p = _path(kind)
    body = str(text or "").strip()
    if not body:
        raise CocoonError("Nothing written.")
    if len(body) > MAX_ENTRY_CHARS:
        raise CocoonError(
            f"That is {len(body)} characters and an entry holds {MAX_ENTRY_CHARS}. "
            f"Nothing was stored, so nothing was cut: split it into two entries.")
    if p.stem == "jonathan" and _matches_identity_phrase(body):
        raise CocoonError(
            "Not stored: this cocoon is read by anyone who reaches you, so it "
            "keeps to what you would say to a stranger.")
    entry = {"by": by, "ts": datetime.now(timezone.utc).isoformat(), "text": body}
    with _LOCK:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
