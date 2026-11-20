"""Verdicts for the harness ledger. SHADOW-ONLY. Pure functions: no I/O, no clock.

Every function here says what a gate WOULD do. Nothing on a live path calls them,
and nothing acts on what they return. Storage, and the rules that keep this from
becoming force, are in reasoning_forge/harness_ledger.py.

Where the design came from (2026-11-20). Jonathan shared two AI-made designs, both
Gemini conversations: "GUARD" (a promotion gate using directional regret, plus a
circuit breaker) and "SIM" (a lab notebook of diagnosis -> harness patch -> trial).
They cite arXiv:2611.23476 and arXiv:2611.18856; neither paper could be checked
from this container (arXiv is blocked here), so both are UNVERIFIED citations.
This is a rebuild, not that code. The review that found 23 bugs in it, each with
the probe output, is docs/HARNESS_LEDGER_2026-11-20.md. Built jointly.

What is stock here, said plainly (CLAUDE.md, "say when a pattern is stock"):
classifying before/after pass states is ordinary regression-testing practice, and
the breaker is the ordinary circuit-breaker idea. What is written for her: unknown
stays None instead of becoming 0, Perspective Dispersion comes only from her own
tension_from_texts, and every threshold is a parameter printed beside the verdict.
The default thresholds are placeholders, not measurements; choosing them is
Jonathan's decision (docs/START_HERE.md).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from reasoning_forge.state_engine_v8 import tension_from_texts
except ImportError:                       # imported as a bare module
    from state_engine_v8 import tension_from_texts

# A check's three states, compared. "still_regressed" is the case the pasted gate
# filed under persistent_fail: broken by an EARLIER edit and still broken. GUARD's
# own point is that those two must not be mixed, so they are separate here.
TRANSITIONS: Tuple[str, ...] = (
    "newly_broken",       # passed under the active harness, fails with the candidate
    "fixed_regression",   # passed at baseline, broken by an earlier edit, fixed now
    "fixed_baseline",     # never passed, passes now
    "stable_pass",        # passed, still passes
    "still_regressed",    # passed at baseline, broken by an earlier edit, still broken
    "persistent_fail",    # never passed, still fails
    "not_measured",       # one of the three states is unknown
)

# Placeholders, not measurements (see the module docstring).
DEFAULT_MAX_FAILURES = 3
DEFAULT_MAX_PATCHES = 3


def classify_transition(baseline: Optional[bool], last_active: Optional[bool],
                        candidate: Optional[bool]) -> str:
    """Where one check went. Any unknown state gives 'not_measured', never a guess."""
    if baseline is None or last_active is None or candidate is None:
        return "not_measured"
    if last_active:
        return "stable_pass" if candidate else "newly_broken"
    if candidate:
        return "fixed_regression" if baseline else "fixed_baseline"
    return "still_regressed" if baseline else "persistent_fail"


def mean_measured(values: Iterable[Optional[float]]) -> Tuple[Optional[float], int]:
    """Mean over the values that were measured, and how many there were.
    (None, 0) when nothing was measured: absent is not zero."""
    measured = [float(v) for v in values if v is not None]
    return (sum(measured) / len(measured) if measured else None), len(measured)


def dispersion(perspective_texts: Dict[str, str]) -> Optional[float]:
    """Perspective Dispersion (Υ), from her own tension_from_texts and nothing else.

    tension_from_texts returns 0.0 for fewer than two non-empty texts, which is
    also what identical texts give. Here that case is None: not measured. The
    pasted bridge defined a second Υ (the spread of lens SCORES); for two identical
    texts it read 0.35 where hers reads 0.0. There is one definition, and it is hers.
    """
    non_empty = [t for t in (perspective_texts or {}).values() if t and t.strip()]
    if len(non_empty) < 2:
        return None
    upsilon, _coherence = tension_from_texts(perspective_texts)
    return upsilon


def band_position(upsilon: Optional[float],
                  band: Optional[Tuple[float, float]] = None) -> str:
    """'not_measured', 'not_judged' (no band chosen), 'below', 'within' or 'above'.
    Both sides are checked; the pasted gate only ever looked for an exact 0.0."""
    if upsilon is None:
        return "not_measured"
    if band is None:
        return "not_judged"
    low, high = band
    if upsilon < low:
        return "below"
    if upsilon > high:
        return "above"
    return "within"


def guard_verdict(rows: Iterable[Tuple[str, bool]], lam: Optional[float] = None) -> dict:
    """What a promotion gate would say about one candidate, from (transition, pinned) rows.

    Strict by default: any newly broken check -> would_reject; otherwise any fix ->
    would_promote; otherwise neutral. A rule that still passes everything is
    neutral, not rejected. With `lam`, GUARD's soft form applies instead:
    net = fixes - lam * newly_broken. Either way a newly broken PINNED check
    rejects, and a pinned check that was already failing is reported, not blocking.
    """
    counts = {t: 0 for t in TRANSITIONS}
    pinned_newly_broken = 0
    pinned_already_failing = 0
    for transition, pinned in rows:
        counts[transition] += 1
        if pinned and transition == "newly_broken":
            pinned_newly_broken += 1
        if pinned and transition in ("still_regressed", "persistent_fail"):
            pinned_already_failing += 1

    measured = sum(counts.values()) - counts["not_measured"]
    fixes = counts["fixed_regression"] + counts["fixed_baseline"]
    broken = counts["newly_broken"]
    net = None if lam is None else fixes - lam * broken

    if measured == 0:
        verdict, reason = "not_judged", "nothing_measured"
    elif pinned_newly_broken:
        verdict, reason = "would_reject", "pinned_newly_broken"
    elif lam is None:
        if broken:
            verdict, reason = "would_reject", "newly_broken"
        elif fixes:
            verdict, reason = "would_promote", "fixed"
        else:
            verdict, reason = "neutral", "no_change"
    elif net > 0:
        verdict, reason = "would_promote", "net_positive"
    elif net < 0:
        verdict, reason = "would_reject", "net_negative"
    else:
        verdict, reason = "neutral", "net_zero"

    return {
        "verdict": verdict, "reason": reason, "counts": counts, "measured": measured,
        "pinned_newly_broken": pinned_newly_broken,
        "pinned_already_failing": pinned_already_failing,
        "net": net, "parameters": {"rule": "strict" if lam is None else "soft", "lam": lam},
    }


def trial_verdict(score: Optional[float], baseline: Optional[float],
                  invariants: Optional[bool], error: Optional[str],
                  margin: float = 0.0) -> str:
    """One trial: 'error', 'invariant_failed', 'not_measured', 'no_baseline',
    'improved', 'regressed' or 'neutral'. A missing baseline is never read as 0."""
    if error:
        return "error"
    if invariants is False:
        return "invariant_failed"
    if score is None:
        return "not_measured"
    if baseline is None:
        return "no_baseline"
    delta = score - baseline
    if delta > margin:
        return "improved"
    if delta < -margin:
        return "regressed"
    return "neutral"


def trial_summary(trials: Sequence[dict], baseline: Optional[float],
                  margin: float = 0.0) -> dict:
    """Every trial judged on its own; 'mixed' when they disagree. No trial overwrites
    another (the pasted notebook kept only the last one's verdict)."""
    judged: List[dict] = []
    for t in trials:
        v = trial_verdict(t.get("score"), baseline, t.get("invariants"), t.get("error"), margin)
        delta = (None if t.get("score") is None or baseline is None
                 else round(t["score"] - baseline, 6))
        judged.append({
            "target_model": t.get("target_model"), "target_adapters": t.get("target_adapters"),
            "verdict": v, "delta": delta,
            "invariants": {True: "passed", False: "failed", None: "not_checked"}[t.get("invariants")],
        })
    verdicts = {j["verdict"] for j in judged}
    if not judged:
        overall = "no_trials"
    elif len(verdicts) == 1:
        overall = next(iter(verdicts))
    else:
        overall = "mixed"
    return {"overall": overall, "trials": judged, "parameters": {"margin": margin}}


def breaker_verdict(events: Sequence[dict], max_failures: int = DEFAULT_MAX_FAILURES,
                    max_patches: int = DEFAULT_MAX_PATCHES) -> dict:
    """What a circuit breaker would say about one target, from its events in order.

    Only the CURRENT failure streak counts. A success ends the streak, so patches
    that worked are not held against a later failure (the pasted breaker kept a
    lifetime count and retired a target on its first failure after two good patches).
    """
    streak: List[dict] = []
    for e in reversed(events):
        if e.get("succeeded"):
            break
        streak.append(e)
    streak.reverse()
    failures = len(streak)
    signatures = [e.get("patch_signature") for e in streak if e.get("patch_signature")]
    repeated = len(signatures) >= 2 and signatures[-1] == signatures[-2]

    if not events:
        verdict, reason = "not_judged", "no_events"
    elif failures == 0:
        verdict, reason = "ok", "last_event_succeeded"
    elif len(signatures) >= max_patches:
        verdict, reason = "would_retire", "patch_budget"
    elif failures >= max_failures:
        verdict, reason = "would_quarantine", "consecutive_failures"
    elif repeated:
        verdict, reason = "would_quarantine", "same_patch_repeated"
    else:
        verdict, reason = "failing", "under_budget"

    return {
        "verdict": verdict, "reason": reason, "consecutive_failures": failures,
        "patches_in_streak": len(signatures), "same_patch_repeated": repeated,
        "parameters": {"max_failures": max_failures, "max_patches": max_patches},
    }
