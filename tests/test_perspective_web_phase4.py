#!/usr/bin/env python3
"""Phase 4 — the kill-criterion. Does the graph beat the flat metric?

The web's extra machinery (pairwise cosine + attractor clustering) only earns
its complexity if it tells us something state_engine_v8.tension_from_texts (a
flat mean-squared-distance from the centroid) does NOT. This experiment is
built to let the graph LOSE if it deserves to.

Two questions, both measured:

  Q1 — REDUNDANCY. Across many random perspective configurations, is web ξ just
       a monotone function of flat ξ? High rank-correlation ⇒ the graph carries
       no independent signal ⇒ flat wins, keep flat.

  Q2 — DISCRIMINATION. Construct pairs that the flat centroid metric CONFLATES
       (near-equal flat ξ) but that have different STRUCTURE — "3 agree + 1
       outlier" vs "everyone mildly spread." Does attractor detection separate
       them? If yes on cases the flat metric can't, the graph earns a place.

Verdict is printed and written to data/results/. It reports honestly whichever
way it falls — a "flat was enough" result is a legitimate, publishable outcome.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reasoning_forge"))

from reasoning_forge.perspective_web import QuantumSpiderweb, NodeState
from reasoning_forge.state_engine_v8 import tension_from_texts

RESULTS = Path(__file__).resolve().parent.parent / "data" / "results"


def _spearman(x, y) -> float:
    """Rank correlation without scipy."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for rank, i in enumerate(order):
            r[i] = rank
        return r
    rx, ry = ranks(x), ranks(y)
    n = len(x)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1.0 - (6.0 * d2) / (n * (n * n - 1)) if n > 1 else 1.0


def _web_from_vectors(vecs: dict):
    web = QuantumSpiderweb()
    for name, v in vecs.items():
        web.add_node(name, NodeState(embedding=np.asarray(v, dtype=np.float64)))
    web.build_from_agents(list(vecs.keys()))
    nodes = list(web.nodes.values())
    pairs = [(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]
    web_xi = sum(a.state.tension_with(b.state) for a, b in pairs) / len(pairs)
    return web, web_xi


def _flat_xi_from_vectors(vecs: dict) -> float:
    """Flat metric analogue in vector space: mean squared distance from centroid
    (exactly what tension_from_texts does, but on these vectors)."""
    arrs = [np.asarray(v, dtype=np.float64) for v in vecs.values()]
    mean = np.mean(arrs, axis=0)
    return float(np.mean([np.sum((a - mean) ** 2) for a in arrs]))


def q1_redundancy(trials: int = 200) -> float:
    rng = np.random.RandomState(42)
    flat, web = [], []
    for _ in range(trials):
        k = rng.randint(3, 6)
        vecs = {f"p{i}": rng.randn(16) for i in range(k)}
        flat.append(_flat_xi_from_vectors(vecs))
        _, wx = _web_from_vectors(vecs)
        web.append(wx)
    rho = _spearman(flat, web)
    print(f"Q1 REDUNDANCY: Spearman(flat ξ, web ξ) = {rho:.3f} over {trials} random configs")
    return rho


def q2_discrimination() -> dict:
    """Two configs with PROVABLY EQUAL flat ξ but different structure.

    Construction (worked out so flat ξ is identical, not fudged):
      A = cluster of 3 identical at origin + 1 outlier at distance R on axis 0.
          flat ξ = 3R²/16.
      B = 4 orthogonal points of magnitude s (a simplex — all mutually
          equidistant, no cluster). flat ξ = 3s²/4.
      Set 3s²/4 = 3R²/16  ⇒  s = R/2. Both configs then have IDENTICAL flat ξ.
    The flat centroid-variance metric literally cannot tell these apart. The
    question is whether attractor detection can. Radius is set between the
    A intra-cluster gap (0) and the B pairwise gap (s√2 = 0.707R): 0.35R.
    """
    d = 8
    R = 1.0
    s = R / 2.0
    radius = 0.35 * R

    base = np.zeros(d)
    outlier = np.zeros(d); outlier[0] = R
    cfg_a = {"n": base.copy(), "s": base.copy(), "q": base.copy(), "e": outlier.copy()}
    cfg_b = {name: (np.eye(d)[i] * s) for i, name in enumerate(["n", "s", "q", "e"])}

    fa, fb = _flat_xi_from_vectors(cfg_a), _flat_xi_from_vectors(cfg_b)
    web_a, _ = _web_from_vectors(cfg_a)
    web_b, _ = _web_from_vectors(cfg_b)
    att_a = web_a.detect_attractors(min_cluster_size=2, max_radius=radius)
    att_b = web_b.detect_attractors(min_cluster_size=2, max_radius=radius)
    max_cluster_a = max((len(a["members"]) for a in att_a), default=1)
    max_cluster_b = max((len(a["members"]) for a in att_b), default=1)

    conflated = abs(fa - fb) / max(fa, fb, 1e-9) < 0.02
    print(f"Q2 DISCRIMINATION:")
    print(f"  flat ξ:  A(3+outlier)={fa:.4f}  B(simplex)={fb:.4f}  "
          f"(flat metric conflates them: {conflated})")
    print(f"  web attractors @r={radius}:  A largest-cluster={max_cluster_a}  "
          f"B largest-cluster={max_cluster_b}")
    separates = conflated and (max_cluster_a >= 2 and max_cluster_b < 2)
    print(f"  graph separates a difference flat ξ cannot: {separates}")
    return {"flat_a": fa, "flat_b": fb, "flat_conflated": conflated,
            "cluster_a": max_cluster_a, "cluster_b": max_cluster_b,
            "separates": separates}


def main() -> int:
    print("=" * 68)
    print("PHASE 4 — does the perspective graph beat the flat metric?")
    print("=" * 68)
    rho = q1_redundancy()
    print()
    q2 = q2_discrimination()
    print()

    # Verdict logic — honest, data-driven. Two independent axes:
    #   scalar redundancy (Q1): is web ξ just a monotone image of flat ξ?
    #   structural discrimination (Q2): does the graph separate what flat conflates?
    scalar_redundant = rho >= 0.95
    adds_structure = q2["separates"]

    if adds_structure and not scalar_redundant:
        verdict = ("GRAPH EARNS ITS PLACE — web ξ is NOT a monotone image of flat ξ "
                   f"(Spearman {rho:.2f}, independent scalar signal), AND attractor "
                   "structure separates configs the flat centroid-variance metric "
                   "provably conflates. The graph carries information flat ξ cannot.")
    elif adds_structure and scalar_redundant:
        verdict = ("PARTIAL — web ξ ≈ flat ξ as a scalar (redundant), but attractor "
                   "structure still distinguishes configs flat conflates. Keep the web "
                   "for STRUCTURE signals; use flat ξ for the scalar.")
    elif (not adds_structure) and (not scalar_redundant):
        verdict = ("DIFFERENT, NOT PROVEN BETTER — web ξ carries an independent scalar "
                   f"(Spearman {rho:.2f}) but the structural-discrimination case did not "
                   "separate. It measures something different (cosine vs squared-euclidean), "
                   "not demonstrably more useful. Needs the semantic embedder to decide.")
    else:
        verdict = ("FLAT WAS ENOUGH — web ξ redundant with flat ξ and no structural "
                   "separation. Keep the flat metric; the graph is decoration in "
                   "lexical mode. (Legitimate negative result.)")

    print("VERDICT:", verdict)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"perspective_web_phase4_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps({
        "spearman_flat_vs_web": rho, "q2": q2, "verdict": verdict,
        "note": "lexical/vector mode; semantic mode may change Q1 redundancy",
    }, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
