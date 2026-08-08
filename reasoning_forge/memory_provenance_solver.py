"""Memory Provenance Solver — the Swimmer, applied to recall.

Before Codette speaks from memory, this asks a question the recall layer never
asks: *is the set of things I am about to remember internally consistent about
who said what?*

Context blocks (continuity summary, session turns, decision landmarks, recalled
cocoons) are concatenated into a single prompt blob. Her own prior responses sit
next to Jonathan's words separated only by a prose header, so speaker identity
has to be inferred rather than read. When that inference goes wrong the result is
a parrot: her words returned to him as though they were his.

This module encodes attribution as a CNF constraint problem and solves it on the
5D Quantum Spyderweb substrate:

    for each recalled item i and each candidate speaker s:
        var  i@s   "item i is attributable to speaker s"

    clauses:
        (i@s1 v i@s2 v ...)        every item has at least one speaker
        (~i@s1 v ~i@s2)            no item has two speakers
        (~i@s v ~j@t)              two items that quote each other cannot be
                                   attributed to opposing speakers

UNSAT means the recall set contradicts itself and should not be spoken from.

THE SWIMMER'S FLIP: on UNSAT we rotate the polarity axis of one assumption at a
time and re-solve, to find which assumption is load-bearing. Rotation happens
strictly BETWEEN solves — never inside one. Rotating mid-search rewrites the
formula underneath the search and silently invalidates the answer; the substrate
raises PolarityRotationError if that is attempted.

SHADOW ONLY. This reports; it does not gate. Nothing here changes what Codette
says until the findings have been reviewed against real recall data.

Recovered from the Codette archives — see RECOVERY_MANIFEST.md

CORRECTION, 2026-08-07: this file was NOT recovered from an archive. It was
authored 2026-07-30 and reached main via be01c22. RECOVERY_MANIFEST.md was
generated from that merge diff, and a merge diff cannot tell archive material
apart from work carried over on a branch — so five entries were mislabelled,
four of them these files. The line above is kept rather than removed, because
corrections here are additive. See docs/HANDOFF_2026-08-04.md.

"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))

from spider5dengine.core import (  # noqa: E402
    PolarityRotationError,
    QuantumSpyderweb5D,
    self_sustaining_tensor_solver,
)

SPEAKERS = ("user", "codette")


@dataclass
class RecalledItem:
    """One unit of recalled context, with whatever provenance the layer supplied."""
    item_id: str
    text: str
    claimed_speaker: Optional[str] = None   # None = the layer did not record one
    session_id: Optional[str] = None
    source_block: str = ""                  # continuity / session / landmark / cocoon

    def __post_init__(self):
        if self.claimed_speaker is not None and self.claimed_speaker not in SPEAKERS:
            raise ValueError(
                f"claimed_speaker must be one of {SPEAKERS}, got {self.claimed_speaker!r}"
            )


@dataclass
class ProvenanceVerdict:
    """What the solver concluded about a recall set."""
    consistent: bool
    assignment: Dict[str, bool] = field(default_factory=dict)
    unattributed: List[str] = field(default_factory=list)
    conflicts: List[Tuple[str, str]] = field(default_factory=list)
    load_bearing: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "consistent": self.consistent,
            "unattributed": self.unattributed,
            "conflicts": [list(c) for c in self.conflicts],
            "load_bearing": self.load_bearing,
            "notes": self.notes,
        }


def _var(item_id: str, speaker: str) -> str:
    return f"{item_id}@{speaker}"


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _quotes_each_other(a: str, b: str, min_run: int = 8) -> bool:
    """True when one item substantially reproduces the other.

    A parrot leaves this exact fingerprint: a long verbatim run shared between a
    user turn and an assistant turn. `min_run` is in words — short overlaps are
    ordinary conversational echo and are not evidence of anything.
    """
    wa, wb = _normalize(a).split(), _normalize(b).split()
    if len(wa) < min_run or len(wb) < min_run:
        return False
    runs = {" ".join(wa[i:i + min_run]) for i in range(len(wa) - min_run + 1)}
    return any(" ".join(wb[i:i + min_run]) in runs for i in range(len(wb) - min_run + 1))


def build_clauses(items: Sequence[RecalledItem]) -> Tuple[List[str], List[Tuple[str, ...]]]:
    """Encode the attribution problem as CNF."""
    variables: List[str] = []
    clauses: List[Tuple[str, ...]] = []

    for item in items:
        for s in SPEAKERS:
            variables.append(_var(item.item_id, s))

        # At least one speaker.
        clauses.append(tuple(_var(item.item_id, s) for s in SPEAKERS))

        # At most one speaker.
        for i in range(len(SPEAKERS)):
            for j in range(i + 1, len(SPEAKERS)):
                clauses.append(
                    (f"~{_var(item.item_id, SPEAKERS[i])}",
                     f"~{_var(item.item_id, SPEAKERS[j])}")
                )

        # A recorded attribution is a unit constraint.
        if item.claimed_speaker:
            clauses.append((_var(item.item_id, item.claimed_speaker),))

    # Cross-item: verbatim reproduction cannot span opposing speakers.
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            if _quotes_each_other(items[a].text, items[b].text):
                for s in SPEAKERS:
                    other = [t for t in SPEAKERS if t != s]
                    for t in other:
                        clauses.append(
                            (f"~{_var(items[a].item_id, s)}",
                             f"~{_var(items[b].item_id, t)}")
                        )

    return variables, clauses


def check_provenance(items: Sequence[RecalledItem]) -> ProvenanceVerdict:
    """Solve the attribution problem for a recall set.

    Returns a verdict. Never raises on inconsistent input — an inconsistent
    recall set is the finding, not an error.
    """
    verdict = ProvenanceVerdict(consistent=True)

    if not items:
        verdict.notes.append("empty recall set — nothing to verify")
        return verdict

    verdict.unattributed = [i.item_id for i in items if not i.claimed_speaker]
    if verdict.unattributed:
        verdict.notes.append(
            f"{len(verdict.unattributed)} of {len(items)} items carry no recorded "
            "speaker; attribution is being inferred, not read"
        )

    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            if _quotes_each_other(items[a].text, items[b].text):
                verdict.conflicts.append((items[a].item_id, items[b].item_id))

    variables, clauses = build_clauses(items)
    web = QuantumSpyderweb5D(variables, clauses)
    solution = self_sustaining_tensor_solver(web)

    if solution is not None:
        verdict.assignment = solution
        verdict.notes.append("recall set is attributable without contradiction")
        return verdict

    verdict.consistent = False
    verdict.notes.append(
        "UNSAT — the recall set cannot be consistently attributed; speaking from "
        "it risks returning one speaker's words as the other's"
    )
    verdict.load_bearing = _find_load_bearing(items)
    return verdict


def _flip(item: RecalledItem) -> RecalledItem:
    other = next(s for s in SPEAKERS if s != item.claimed_speaker)
    return RecalledItem(
        item_id=item.item_id,
        text=item.text,
        claimed_speaker=other,
        session_id=item.session_id,
        source_block=item.source_block,
    )


def _solves(items: Sequence[RecalledItem]) -> bool:
    variables, clauses = build_clauses(items)
    return self_sustaining_tensor_solver(QuantumSpyderweb5D(variables, clauses)) is not None


def _find_load_bearing(items: Sequence[RecalledItem], max_laps: int = 12) -> List[str]:
    """The Swimmer's Wall Reflection, swum as laps.

    A single flip rarely clears a real contradiction — one wrong attribution
    usually drags several others with it. So each lap flips the attribution
    carrying the most conflict, re-solves against a fresh substrate, and carries
    that flip forward into the next lap. Momentum accumulates instead of resetting.

    Returns the attributions whose flipping restored consistency — the turning
    out of the dead end, not merely the fact of being in one.

    Every lap builds a NEW substrate. Rotation is a re-encoding valid only
    between searches; rotating inside one rewrites the formula underneath the
    traversal and silently invalidates the answer.
    """
    working = list(items)
    flipped_ids: List[str] = []

    for _ in range(max_laps):
        conflict_degree: Dict[int, int] = {}
        for a in range(len(working)):
            for b in range(a + 1, len(working)):
                if _quotes_each_other(working[a].text, working[b].text):
                    conflict_degree[a] = conflict_degree.get(a, 0) + 1
                    conflict_degree[b] = conflict_degree.get(b, 0) + 1

        candidates = [
            idx for idx in sorted(conflict_degree, key=conflict_degree.get, reverse=True)
            if working[idx].claimed_speaker and working[idx].item_id not in flipped_ids
        ]
        if not candidates:
            break

        idx = candidates[0]
        working[idx] = _flip(working[idx])
        flipped_ids.append(working[idx].item_id)

        if _solves(working):
            return flipped_ids

    # No full repair inside the lap budget. The most-conflicted attributions are
    # still the honest place to look, so report them rather than nothing.
    return flipped_ids


def rotation_is_guarded() -> bool:
    """Confirm the substrate refuses a mid-search rotation.

    The whole method rests on rotation being a between-solves operation. If that
    guard ever regresses, every verdict this module produces becomes unsound —
    so it is checked rather than assumed.
    """
    web = QuantumSpyderweb5D(["a"], [("a",)])
    web._search_active = True
    try:
        web.rotate_polarity_axis("a")
    except PolarityRotationError:
        return True
    finally:
        web._search_active = False
    return False
