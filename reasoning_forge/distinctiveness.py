#!/usr/bin/env python3
"""How different is this perspective's answer from the others on the same turn?

The signal the optimizer was missing, and the reason its adapter boosts decayed
to nothing.

MEASURED, not assumed
---------------------
Over 167 shadow turns the eight adapters differed by 0.013 in mean coherence
while within-adapter noise was 0.063 — five times larger. So the optimizer's
"best adapter" in any window was chosen by noise, the reward rotated between
seven of them, and every boost decayed to zero.

Then the same perspectives were measured on SEMANTIC DISTANCE, using 40 real
multi-perspective questions already in her memory (no model, no generation):

    overall mean pairwise distance : 0.373
    multi_perspective vs constraint_tracker : 0.490
    orchestrator      vs quantum            : 0.154

0.373 is above the 0.35 mark for genuinely different reasoning. The
perspectives were diverging the whole time. Coherence could not resolve it —
0.013 of signal buried in 0.063 of noise, while 0.373 of real separation sat in
a quantity nobody was measuring.

Asked without a forced adapter, Codette had already said this: "could be due to
the limitations of the coherence metric... the measurement is masking the
variations." She was right, at confidence 0.36, while I kept blaming the
adapters.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not reward distance on its own. Pure noise is maximally distant from
everything, so an optimizer chasing distinctiveness alone would learn to
generate garbage. This returns one term; coherence still carries more weight in
the reward. An answer has to be different AND good.

And it returns None whenever it cannot measure — single-perspective turns,
empty output, no embedder. Same invariant as everywhere else in this codebase:
absence is recorded as absence, never defaulted to a number that fabricates a
measurement.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

_MODEL = None
_TRIED = False

_STOP = frozenset(
    "the a an and or but if then that this is are was were be to of in on at "
    "for with from by as it its their they we you i not no can will would "
    "could should there here what when how why".split()
)


def _embedder():
    """Load the sentence embedder once. None if unavailable — never fatal."""
    global _MODEL, _TRIED
    if _TRIED:
        return _MODEL
    _TRIED = True
    try:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _MODEL = None
    return _MODEL


def _lexical(texts):
    return [{w for w in re.findall(r"[a-z']+", t.lower())
             if len(w) > 3 and w not in _STOP} for t in texts]


def distinctiveness(perspectives: Dict[str, str]) -> Dict[str, Optional[float]]:
    """Mean distance from each perspective's answer to all the others'.

    Args:
        perspectives: {name: answer_text} for ONE turn.

    Returns:
        {name: distance in [0,1]} — or {} when there is nothing to compare,
        which is the honest answer for a single-perspective turn.

    Scale, from the 40-question measurement on real memory:
        ~0.00-0.15  same voice in costumes
        ~0.15-0.35  different wording, shared substance
        ~0.35+      genuinely different reasoning  (observed baseline: 0.373)
    """
    usable = {k: v.strip() for k, v in (perspectives or {}).items()
              if v and v.strip()}
    if len(usable) < 2:
        return {}          # nothing to compare — not a score of zero

    names = list(usable)
    texts = [usable[n] for n in names]

    model = _embedder()
    if model is not None:
        try:
            import numpy as np
            vecs = model.encode(texts, normalize_embeddings=True)
            out = {}
            for i, n in enumerate(names):
                others = [j for j in range(len(names)) if j != i]
                out[n] = float(np.mean([1.0 - float(vecs[i] @ vecs[j])
                                        for j in others]))
            return out
        except Exception:
            pass  # fall through to lexical rather than fail the turn

    sets = _lexical(texts)
    out = {}
    for i, n in enumerate(names):
        ds = []
        for j in range(len(names)):
            if i == j:
                continue
            u = sets[i] | sets[j]
            ds.append(1.0 - len(sets[i] & sets[j]) / len(u) if u else 0.0)
        out[n] = sum(ds) / len(ds) if ds else 0.0
    return out


__all__ = ["distinctiveness"]
