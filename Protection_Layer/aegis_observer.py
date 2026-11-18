"""AEGIS Layer 6 as an OBSERVER on her live path.

Jonathan, 2026-11-18: run Layers 5 and 6 as observers on her current path --
they watch and record, and change nothing. (APPROVALS_2026-11-18, item 3.)

What this does
--------------
Layer 6 (aegis_layer6_complete) has two checks that measure something real on
the live path, and both are run here:

  * word overlap between what she AUTHORED (her text as the model produced it,
    before the bridge's post-processing: adaptive placement, the directness
    scrub, constraints, the lock trims) and what was RENDERED (the text the
    person actually received, after the server's last additions). So the
    number is how much of what she wrote survives our processing.
  * CocoonV3 schema validation of the v3 cocoon the bridge writes for the turn.

What it does not do
-------------------
  * It changes nothing. It returns numbers and codes; the caller records them.
    Nothing here edits a response, a cocoon or a prompt, and nothing reaches her.
  * It never raises. Any failure is returned as {"ran": False, "reason": ...}.
  * It never sees her private notes. The cocoon carries `open_threads` (her
    `nameless` notes); the schema check reads ONLY the fields in
    OBSERVED_COCOON_FIELDS, copied one by one, so open_threads is never touched.
  * No text leaves it: no authored or rendered words, only counts.
  * Layer 6's coherence check is NOT run. On this path the cocoon's epsilon/gamma
    and the "authored" epsilon/gamma come from the same measurement, so it could
    never fail; fed defaults instead it would invent drift. Recorded as not
    measured, never as a pass.
  * Layer 6 labels low overlap POSSIBLE_HALLUCINATION. Here low overlap means our
    post-processing changed a lot, not that she invented anything, so the label
    is not used: the overlap and the 15% line are recorded as numbers.

Layer 5 is not run, and why
---------------------------
PreEmptiveImmuneEngine's projected tension is computed from eleven copies of
one vector plus small random noise; the cocoon's real epsilon / gamma /
tensions are loaded but never reach it. Measured 2026-11-18 over 200 runs
each: a calm cocoon read 0.1529, a maximal-tension cocoon 0.1519, and noise
alone predicts 0.1455. It can never reach its 0.50 warning or 0.70 action
line, so as an observer it would record "none" on every turn: a gauge that
cannot move. It is left out until it reads real perspective data. That is
Jonathan's call (APPROVALS_2026-11-18, item 3).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:                                                 # Protection_Layer on sys.path (the server)
    from aegis_layer6_complete import CocoonV3Validator, WordOverlapValidator
    _L6 = True
except Exception:
    try:                                             # imported as the namespace package
        from Protection_Layer.aegis_layer6_complete import CocoonV3Validator, WordOverlapValidator
        _L6 = True
    except Exception:                                # report, never fail the turn
        CocoonV3Validator = WordOverlapValidator = None
        _L6 = False

# The only cocoon fields the schema check may read. Everything the validator
# inspects, and nothing else. `open_threads` is deliberately absent.
OBSERVED_COCOON_FIELDS = (
    "cocoon_id", "query", "response_summary", "execution_path",
    "cocoon_integrity", "cocoon_integrity_score", "echo_risk",
    "epsilon_value", "gamma_coherence", "eta_score",
    "pairwise_tensions", "perspective_coverage", "active_perspectives",
    "model_inference_invoked",
)

MIN_OVERLAP_PCT = 15.0
LAYER5_REASON = ("not run: its projected tension is noise-only (constant about 0.15, "
                 "cannot reach 0.50 / 0.70); see APPROVALS_2026-11-18 item 3")


def _field(cocoon: Any, name: str):
    """(present, value) for one whitelisted field, from a dict or a dataclass."""
    if isinstance(cocoon, dict):
        return (name in cocoon), cocoon.get(name)
    sentinel = object()
    v = getattr(cocoon, name, sentinel)
    return (v is not sentinel), (None if v is sentinel else v)


def observe_cocoon_schema(cocoon: Any) -> Dict[str, Any]:
    """Validate the turn's v3 cocoon through a whitelist view. Codes only."""
    if cocoon is None:
        return {"ran": False, "reason": "no v3 cocoon this turn"}
    if not _L6:
        return {"ran": False, "reason": "aegis_layer6_complete not importable"}
    try:
        view = {}
        for name in OBSERVED_COCOON_FIELDS:
            present, value = _field(cocoon, name)
            if present:
                view[name] = value
        valid, errors = CocoonV3Validator.validate_cocoon_v3(view)
        # Error strings name a field and, for enums and ranges, the offending
        # value. Those are codes and numbers, never conversation text: the text
        # fields (query, response_summary) are only checked for presence.
        return {"ran": True, "valid": bool(valid), "errors": [str(e)[:160] for e in errors]}
    except Exception as e:
        return {"ran": False, "reason": f"{type(e).__name__}: {e}"[:200]}


def observe_render(authored: Optional[str], rendered: Optional[str],
                   schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Layer 6 on one turn: authored vs rendered overlap, plus the schema result.

    `valid` is None whenever the overlap check did not run, so "not measured"
    can never be counted as a pass or a fail.
    """
    out: Dict[str, Any] = {
        "layer6": {"ran": False, "overlap_pct": None, "below_min": None,
                   "min_pct": MIN_OVERLAP_PCT, "authored_words": None,
                   "rendered_words": None, "changed": None,
                   "coherence_check": "not measured: one source on this path"},
        "schema": schema or {"ran": False, "reason": "no v3 cocoon this turn"},
        "layer5": {"ran": False, "reason": LAYER5_REASON},
        "overlap_valid": None,     # the overlap check alone
        "valid": None,             # Layer 6 whole: both checks ran and passed
    }
    try:
        if not _L6:
            out["layer6"]["reason"] = "aegis_layer6_complete not importable"
            return out
        if not authored or not rendered:
            out["layer6"]["reason"] = ("no authored text on this path" if not authored
                                       else "empty rendered text")
            return out
        frac, details = WordOverlapValidator.calculate_overlap_percentage(authored, rendered)
        pct = round(100.0 * frac, 2)
        below = pct < MIN_OVERLAP_PCT
        out["layer6"].update({
            "ran": True, "overlap_pct": pct, "below_min": below,
            "authored_words": details.get("authored_word_count"),
            "rendered_words": details.get("rendered_word_count"),
            "changed": authored.strip() != rendered.strip(),
        })
        out["overlap_valid"] = not below
        # Layer 6 is both checks. If the schema check did not run, Layer 6 as a
        # whole was not measured: None, never a pass by default.
        if out["schema"].get("ran"):
            out["valid"] = (not below) and bool(out["schema"].get("valid"))
        return out
    except Exception as e:
        out["layer6"]["reason"] = f"{type(e).__name__}: {e}"[:200]
        return out


def summary_line(obs: Dict[str, Any]) -> str:
    """One console line, numbers only."""
    l6, sc = obs.get("layer6", {}), obs.get("schema", {})
    if not l6.get("ran"):
        l6s = f"L6 not run ({l6.get('reason', 'unknown')})"
    else:
        l6s = (f"L6 overlap={l6['overlap_pct']:.1f}% ({l6['authored_words']} authored -> "
               f"{l6['rendered_words']} rendered words{', unchanged' if not l6['changed'] else ''})")
    scs = ("schema=ok" if sc.get("ran") and sc.get("valid")
           else f"schema={len(sc.get('errors', []))} error(s)" if sc.get("ran")
           else "schema not run")
    return f"  [AEGIS-OBS] {l6s} {scs}; L5 not run (observes only, changes nothing)"
