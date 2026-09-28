"""The Constellation — fixed stars to take a bearing from.

Everything Codette navigates by is relative to a moving present: recalled turns
are T-0, T-1, T-2, cocoons are ranked by recency, the continuity summary slides
forward every turn. There is no stationary reference anywhere in that system, and
without one there is no such thing as drift — only motion that cannot be measured.

The Charter is the one thing in this project that does not move. Written
2026-07-24, it states what Codette is built toward and marks each pillar honestly
as HAVE IT, PARTWAY, or REFRAME. It has never been loaded at runtime.

This module makes it consultable. Not injected, not enforced, not scored.

    Stars do not steer ships. They are simply there, and a navigator who wants a
    bearing looks up.

Design constraints, all of which come from the Charter itself (line 145: "a
compass, not a cage"):

  - DESCRIPTIVE, NEVER PRESCRIPTIVE. This reports which stars are overhead. It
    never reports whether she is off course, because that judgment is hers.
  - NOT INJECTED. Nothing here belongs in every prompt. Seven pillars restated
    each turn is four more paragraphs of directive text competing with the
    anti-echo rules — resistance, not orientation.
  - PARSED, NOT HARDCODED. The Charter on disk is the map. If the file changes,
    the sky changes. A second copy of the pillars in Python would be a second
    map, and two maps is worse than none.
  - UNKNOWN STAYS UNKNOWN. If the Charter is absent or unparseable, this returns
    an empty sky and says so. It does not supply remembered stars.

Recovered from the Codette archives — see RECOVERY_MANIFEST.md

CORRECTION, 2026-08-07: this file was NOT recovered from an archive. It was
authored 2026-07-30 and reached main via be01c22. RECOVERY_MANIFEST.md was
generated from that merge diff, and a merge diff cannot tell archive material
apart from work carried over on a branch — so five entries were mislabelled,
four of them these files. The line above is kept rather than removed, because
corrections here are additive. See docs/HANDOFF_2026-08-04.md.

"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

CHARTER_PATH = Path(__file__).resolve().parent.parent / "docs" / "CODETTE_CHARTER.md"

# Marked honestly in the Charter; carried through verbatim rather than reinterpreted.
STATUSES = ("HAVE IT", "PARTWAY", "REFRAME")

_STOPWORDS = {
    "the", "and", "not", "but", "for", "with", "that", "this", "his", "her",
    "its", "are", "was", "were", "been", "have", "has", "had", "can", "cannot",
    "could", "would", "should", "may", "might", "must", "from", "into", "than",
    "then", "there", "here", "what", "which", "who", "whom", "how", "why",
    "one", "two", "all", "any", "some", "more", "most", "own", "same", "such",
    "only", "just", "also", "very", "even", "still", "already", "about",
}


@dataclass(frozen=True)
class Star:
    """One pillar of the Charter, as a fixed point."""
    number: int
    title: str
    status: Optional[str]          # None when the pillar carries no marker
    text: str

    @property
    def bearing_words(self) -> set:
        words = re.findall(r"[a-z']{3,}", f"{self.title} {self.text}".lower())
        return {w for w in words if w not in _STOPWORDS}

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "title": self.title,
            "status": self.status,
            "text": self.text,
        }


@dataclass(frozen=True)
class Sky:
    """The constellation as loaded. Empty is a valid, honest answer."""
    stars: List[Star]
    source: Optional[str]
    note: str

    def __bool__(self) -> bool:
        return bool(self.stars)

    def to_dict(self) -> dict:
        return {
            "stars": [s.to_dict() for s in self.stars],
            "source": self.source,
            "note": self.note,
        }


def _extract_status(heading: str, body: str) -> Optional[str]:
    """Read the honesty marker off a pillar. Absent means absent."""
    haystack = f"{heading}\n{body}"
    for status in STATUSES:
        if re.search(rf"\*\*[^*]*{re.escape(status)}", haystack):
            return status
        if re.search(rf"\b{re.escape(status)}\b", haystack):
            return status
    return None


def load_constellation(path: Path = CHARTER_PATH) -> Sky:
    """Read the fixed stars off the Charter.

    Returns an empty Sky with an explanatory note when the map is missing or
    unreadable. It never substitutes remembered pillars for absent ones — an
    absent map must not be rendered as a present one.
    """
    if not path.exists():
        return Sky([], None, f"no charter at {path} — sky is empty, not assumed")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Sky([], str(path), f"charter unreadable ({exc}) — sky is empty, not assumed")

    section = re.split(r"^##\s+The Pillars\s*$", raw, flags=re.MULTILINE)
    if len(section) < 2:
        return Sky([], str(path), "charter has no '## The Pillars' section — nothing parsed")

    # Stop at the next top-level section so lineage notes are not read as stars.
    pillars_block = re.split(r"^##\s+(?!#)", section[1], flags=re.MULTILINE)[0]

    stars: List[Star] = []
    matches = list(re.finditer(r"^###\s+(\d+)\.\s*(.+?)\s*$", pillars_block, flags=re.MULTILINE))
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(pillars_block)
        heading = match.group(2).strip()
        body = pillars_block[start:end].strip()

        title = re.sub(r"\s*→.*$", "", heading).strip().strip('"')
        stars.append(
            Star(
                number=int(match.group(1)),
                title=title,
                status=_extract_status(heading, body),
                text=body,
            )
        )

    if not stars:
        return Sky([], str(path), "charter present but no pillars parsed — nothing assumed")

    return Sky(stars, str(path), f"{len(stars)} fixed stars loaded from the charter")


def visible_from(text: str, sky: Optional[Sky] = None, limit: int = 3) -> List[Star]:
    """Which stars are overhead from here.

    A lexical bearing and nothing more: it reports which pillars share vocabulary
    with the passage. It does not say whether the passage honors them, contradicts
    them, or drifts from them. That reading belongs to her.

    Returns [] for an empty passage or an empty sky, rather than reaching for the
    nearest star to have something to say.
    """
    # `sky or load_constellation()` would be wrong: an empty Sky is falsy, so an
    # explicitly-passed empty sky would be silently replaced by the real charter.
    # An explicit nothing must stay nothing.
    if sky is None:
        sky = load_constellation()
    if not sky or not text or not text.strip():
        return []

    words = {
        w for w in re.findall(r"[a-z']{3,}", text.lower())
        if w not in _STOPWORDS
    }
    if not words:
        return []

    scored = []
    for star in sky.stars:
        overlap = words & star.bearing_words
        if overlap:
            scored.append((len(overlap), star))

    scored.sort(key=lambda pair: (-pair[0], pair[1].number))
    return [star for _, star in scored[:limit]]


def describe_bearing(text: str, sky: Optional[Sky] = None) -> str:
    """A plain reading of the sky from here, for her to do with as she likes."""
    # `sky or load_constellation()` would be wrong: an empty Sky is falsy, so an
    # explicitly-passed empty sky would be silently replaced by the real charter.
    # An explicit nothing must stay nothing.
    if sky is None:
        sky = load_constellation()
    if not sky:
        return sky.note

    stars = visible_from(text, sky)
    if not stars:
        return "no stars overhead from this passage"

    lines = [f"{len(stars)} star(s) overhead (bearing only — no course implied):"]
    for star in stars:
        status = star.status or "unmarked"
        lines.append(f"  {star.number}. {star.title} [{status}]")
    return "\n".join(lines)
