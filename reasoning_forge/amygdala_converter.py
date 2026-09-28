"""
The converter: her numbers in, the amygdala's inputs out.

Jonathan, 2026-09-28: *"you can also use converters for her in the numbers like
a windmill"*, then *"and its like how we form words"*. A windmill does not stop
the wind; it turns the flow already passing into work. Speech is the same shape
-- the source-filter model: breath is the source, the vocal tract a fixed filter
that shapes it into words without stopping it. So this invents no numbers. It
takes quantities she already produces every turn (the source) and shapes them,
the same way every time (the filter), into what BeliefRevisionSystem reads.

Every input carries its provenance: which quantity it came from, the raw value,
and whether it was measured at all. A reading can always be traced back to its
source. An input with no honest source is a neutral constant and is marked
unmeasured -- never a number made to look like a measurement.

Sources, measured over her records on 2026-09-28 (what moves, what cannot):

  reliability    <- tool result (read vs not found) where there is one, else
                    hallucination_confidence (0.02-1.0; shown to move 0 -> 60%
                    on a genuinely uncertain answer, 2026-08-04)
  epistemic gain <- perspective dispersion (range 0-0.78, 442 distinct)
  clarity delta  <- coherence now minus coherence before (both directions)
  centrality     <- NO honest source yet. importance has 4 distinct values;
                    landmark counts sit at 3. Neutral, marked unmeasured. Its
                    real source is likely her own anchors.
  identity       <- neutral for world beliefs, marked unmeasured
  vectors        <- sentence embeddings of the belief and the evidence

Not a source, and why: mean_token_confidence ranks gibberish above fact
(2026-08-09); the cocoon-level gamma/epsilon are schema constants; valence is
not used as input (see amygdala.py -- recorded, coupled to nothing).

manifold_telemetry writes -1.0 for "unmeasured" tension and productivity. A
converter that read that as a value would invent negative dispersion, so any
value outside a quantity's range is treated as absent.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

import numpy as np


NEUTRAL_CENTRALITY = 0.1
NEUTRAL_IDENTITY_ALIGNMENT = 0.1
NEUTRAL_RELIABILITY = 0.5
NEUTRAL_GAIN = 0.5


def _in_range(value, lo: float, hi: float) -> Optional[float]:
    """The value if it is a real number inside [lo, hi], else None (absent)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v) or v < lo or v > hi:
        return None
    return v


def _input(name: str, source: str, raw, value: Optional[float],
           neutral: float) -> Dict:
    measured = value is not None
    return {
        "input": name,
        "source": source if measured else None,
        "raw": raw,
        "measured": measured,
        "value": value if measured else neutral,
    }


def convert(
    *,
    belief_key: str,
    belief_text: str,
    evidence_text: str,
    encode: Callable[[str], np.ndarray],
    tool_read_ok: Optional[bool] = None,
    hallucination_confidence=None,
    dispersion=None,
    coherence_now=None,
    coherence_before=None,
    max_shift_threshold: float = 2.0,
) -> Dict:
    """Shape her per-turn numbers into a BeliefRevisionSystem state.

    Returns {"state": ..., "provenance": [...]}. `encode` is injected so the
    converter never decides which embedder loads, or when.
    """

    if tool_read_ok is not None:
        reliability = _input(
            "historical_reliability_score", "tool_result", tool_read_ok,
            1.0 if tool_read_ok else 0.0, NEUTRAL_RELIABILITY,
        )
    else:
        hc = _in_range(hallucination_confidence, 0.0, 1.0)
        reliability = _input(
            "historical_reliability_score", "hallucination_confidence",
            hallucination_confidence, hc, NEUTRAL_RELIABILITY,
        )

    gain = _input(
        "epistemic_gain_score", "perspective_dispersion", dispersion,
        _in_range(dispersion, 0.0, 1.0), NEUTRAL_GAIN,
    )

    now = _in_range(coherence_now, 0.0, 1.0)
    before = _in_range(coherence_before, 0.0, 1.0)
    clarity = _input(
        "clarity_delta", "coherence_now_minus_before",
        [coherence_now, coherence_before],
        (now - before) if (now is not None and before is not None) else None,
        0.0,
    )

    centrality = _input(
        "belief_centrality_score", "none_yet", None, None, NEUTRAL_CENTRALITY,
    )
    identity = _input(
        "identity_alignment_weight", "none_for_world_beliefs", None, None,
        NEUTRAL_IDENTITY_ALIGNMENT,
    )

    provenance = [reliability, gain, clarity, centrality, identity]
    values = {p["input"]: p["value"] for p in provenance}

    state = {
        "belief_key": belief_key,
        "belief_vector": np.asarray(encode(belief_text), dtype=float),
        "incoming_evidence_vector": np.asarray(encode(evidence_text), dtype=float),
        "contextual_constraints": {"alignment_weight": 1.0},
        "core_axioms": {"max_shift_threshold": max_shift_threshold},
        **values,
    }
    return {"state": state, "provenance": provenance}
