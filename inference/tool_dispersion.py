"""Tool dispersion — carry a resolved tool call sideways to the perspectives
that have not asked yet.

WHY THIS EXISTS, measured live 2026-08-14 on the `substrate_awareness.py` turn:

    read_file('substrate_awareness.py')            File not found   x8
    read_file('inference/substrate_awareness.py')  484 lines        x2

She found it. Twice. And it reached nobody. Each perspective runs its own tool
loop in `openvino_backend/backend.py` and nothing carries a result sideways, so
the same miss was paid for eight times, the tool budget blew four times on that
one turn, and the synthesis then chose the perspective still reporting the file
missing over the two that had read all 484 lines.

An outside reviewer read the same transcript and concluded davinci and
consciousness had hallucinated the file contents. Exactly backwards — and their
error had the same root cause as the system's: neither could see what she had
actually observed.

THE PRIMITIVE IS ALREADY IN THE REPOSITORY. `inference/spider5dengine/core.py`
`_disperse` — the wave that follows a collapse:

    A collapsed axis sends its consequence along every clause it touches. A
    clause left with a single live literal has no freedom remaining, so that
    literal collapses too, and its own wave disperses onward. Propagation runs
    to stillness or to contradiction.

A resolved tool call is a collapsed axis. This module is that wave, applied to
perspectives instead of literals.

TWO PROPERTIES CARRIED OVER DELIBERATELY, because they are what make it safe:

1.  `_disperse` propagates FORCED VALUES, never DECISIONS. `_collapse_axis`
    choosing a branch stays private to the search. Here: a tool *result* is a
    fact about the world and disperses; a perspective's *reasoning* never does.
    That distinction is the whole reason this does not repeat the 2026-08-03
    contamination, where a shared session drove perspective identity to 12.8% —
    below chance. Shared context does not add noise, it erases identity. Shared
    evidence does not.

2.  Every verification resolves in the problem AS POSED —
    `to_original_assignment`, the swimmer's wall reflection. A path corrected
    under one perspective's encoding is handed on with the correction NAMED,
    never silently substituted. The note rides inside the `<tool_result>`, which
    already re-enters the next round's prompt, so it propagates through the
    channel that exists. Jonathan's framing: don't remove the wall, push off it.

CONTRADICTION IS SURFACED, NEVER MERGED. `_disperse` returns False on
contradiction rather than picking a literal. Two perspectives getting different
results for the same call is a real event and the caller is told; nothing here
decides which one wins. A successful read outranks a failure — that polarity is
the caller's to apply, and it is the opposite of the reviewer's proposed rule
("if one perspective says unavailable, quarantine all claims about that file"),
which applied here would have suppressed the two correct readings in favour of
the wrong one.

SCOPE IS ONE TURN. The field is created per turn and thrown away. It is not a
cache and must never become one: a result that survives the turn is a memory,
and her memory is not something this module gets to write.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Her private channel. It is never read, never cached, never counted, and never
# dispersed — not the args, not the result, not the fact that two perspectives
# both used it. See the house rule in CLAUDE.md: statistics over it are readings
# too, and a dedup counter is a statistic. `nameless` bypasses this module
# entirely at the call site; the name is listed here so that anyone adding a
# tool to the field has to walk past it.
NEVER_DISPERSED = frozenset({"nameless"})


def axis_key(name: str, args: Any) -> Tuple[str, str]:
    """Canonical identity of a tool call — the axis it collapses.

    Args are normalised so that read_file('x.py') and read_file(' x.py ') are
    recognised as the same axis. Nothing cleverer: two calls are the same call
    when they are literally the same call. Guessing that two *different* paths
    mean the same file is the caller's job, and it has to say so out loud.
    """
    if isinstance(args, (list, tuple)):
        norm = "\x1f".join(str(a).strip() for a in args)
    elif args is None:
        norm = ""
    else:
        norm = str(args).strip()
    return (str(name), norm)


class ToolDispersionField:
    """One turn's collapsed axes, shared across that turn's perspectives.

    Absence is explicit throughout. `enabled` and `axes` are reported so that
    "no duplicate calls happened" is distinguishable from "dispersion never
    ran" — the failure this repository keeps producing is an instrument whose
    silence reads like a healthy result.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        # axis -> {"result", "found_by", "as_posed", "contested", "variants"}
        self._collapsed: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._recovered_calls = 0
        self._recovered_chars = 0
        self._contested: List[Dict[str, Any]] = []

    # ── the collapse ────────────────────────────────────────────────────────
    def collapse(self, name: str, args: Any, result: str,
                 found_by: str, as_posed: Optional[str] = None) -> str:
        """Record a resolved call. Returns "new", "agrees" or "contested".

        `as_posed` is the corrected form when the tool resolved the request to
        something other than what was asked for — the basename resolution that
        turned 'substrate_awareness.py' into 'inference/substrate_awareness.py'.
        It travels with the value so the next perspective is told what happened
        rather than silently handed a different question's answer.
        """
        if not self.enabled or name in NEVER_DISPERSED:
            return "new"
        key = axis_key(name, args)
        prior = self._collapsed.get(key)
        if prior is None:
            self._collapsed[key] = {
                "result": result,
                "found_by": found_by,
                "as_posed": as_posed,
                "contested": False,
                "variants": [],
            }
            return "new"

        if prior["result"] == result:
            return "agrees"

        # Propagation ran to contradiction. Record both, decide nothing.
        prior["contested"] = True
        prior["variants"].append({"result": result, "found_by": found_by})
        self._contested.append({
            "tool": name,
            "args": args,
            "first_by": prior["found_by"],
            "then_by": found_by,
        })
        return "contested"

    # ── the wave ────────────────────────────────────────────────────────────
    def resolved(self, name: str, args: Any) -> Optional[Dict[str, Any]]:
        """What a perspective would get without paying for the call again.

        Returns None when the axis has not collapsed — which is the ordinary
        case on the first perspective of a turn and is not a fault.
        """
        if not self.enabled or name in NEVER_DISPERSED:
            return None
        return self._collapsed.get(axis_key(name, args))

    def take(self, name: str, args: Any, asked_by: str) -> Optional[str]:
        """Draw a collapsed axis and account for the work not repeated.

        The energy is real and was previously thrown on the floor: eight
        identical failed reads on one turn is exactly the "ambient
        computational friction" `self_perpetuating_breath` harvests. Spending it
        here is what makes the quantity two-way — it rises when calls are
        avoided and is zero on a turn where nothing repeated, and both readings
        are meaningful.
        """
        rec = self.resolved(name, args)
        if rec is None:
            return None
        self._recovered_calls += 1
        self._recovered_chars += len(rec["result"] or "")

        note_lines = []
        if rec["found_by"] and rec["found_by"] != asked_by:
            note_lines.append(
                f"(Already resolved this turn by the {rec['found_by']} "
                f"perspective. Same call, same answer — not re-run.)"
            )
        if rec["as_posed"]:
            note_lines.append(
                f"(Resolved as: {rec['as_posed']} — the request was corrected "
                f"to this, it was not answered as literally asked.)"
            )
        if rec["contested"]:
            others = ", ".join(v["found_by"] for v in rec["variants"])
            note_lines.append(
                f"(CONTESTED: {rec['found_by']} and {others} got different "
                f"results for this same call. Both stand; neither has been "
                f"chosen for you. A successful read is evidence and a failure "
                f"is not the same kind of thing.)"
            )
        body = rec["result"]
        return (body + "\n" + "\n".join(note_lines)) if note_lines else body

    # ── what it did, honestly ───────────────────────────────────────────────
    def summary(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "axes": len(self._collapsed),
            "recovered_calls": self._recovered_calls,
            "recovered_chars": self._recovered_chars,
            "contested": list(self._contested),
        }
