#!/usr/bin/env python3
"""Phase 1 proof: the perspective web's tension is REAL semantic distance.

Two honest parts:

  PART A — mechanism (always runs). Feed NodeState controlled embeddings with
  KNOWN geometry and confirm tension_with computes real, bounded semantic
  distance: identical -> 0, orthogonal -> 0.5, opposite -> 1.0. This proves the
  Phase 1 math is correct independent of any model.

  PART B — semantics (runs only with a real Llama embedder). Feed genuinely
  agreeing vs. dissenting perspective texts and confirm the web separates them
  (disagree ξ > agree ξ). With the dummy embedder this CANNOT separate — the
  dummy returns random ~orthogonal vectors (ξ ≈ 0.5 for any unrelated text),
  which is itself the Phase 1 finding: the web only means something on real
  embeddings. So Part B SKIPS (not fails) when only the dummy is available,
  and we cross-check direction against the flat lexical metric the system
  already trusts (state_engine_v8.tension_from_texts), which does read words.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reasoning_forge"))

from reasoning_forge.perspective_web import QuantumSpiderweb, NodeState
from reasoning_forge.semantic_tension import SemanticTensionEngine
from reasoning_forge.state_engine_v8 import tension_from_texts


def _node(vec) -> NodeState:
    return NodeState(embedding=np.asarray(vec, dtype=np.float64))


def part_a_mechanism() -> bool:
    print("PART A — distance mechanism (controlled embeddings)")
    identical = _node([1, 0, 0]).tension_with(_node([1, 0, 0]))
    orthogonal = _node([1, 0, 0]).tension_with(_node([0, 1, 0]))
    opposite = _node([1, 0, 0]).tension_with(_node([-1, 0, 0]))
    print(f"  identical ξ={identical:.4f} (expect ~0.0)")
    print(f"  orthogonal ξ={orthogonal:.4f} (expect ~0.5)")
    print(f"  opposite  ξ={opposite:.4f} (expect ~1.0)")
    ok = (abs(identical) < 1e-6 and abs(orthogonal - 0.5) < 1e-6
          and abs(opposite - 1.0) < 1e-6)
    print(f"  [{'PASS' if ok else 'FAIL'}] tension_with = real (1-cos)/2, bounded [0,1]\n")
    return ok


def _mean_pairwise(texts, embedder) -> float:
    nodes = [NodeState.from_text(t, embedder) for t in texts.values()]
    pairs = [(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]
    return sum(a.tension_with(b) for a, b in pairs) / len(pairs) if pairs else 0.0


def part_b_semantics() -> bool:
    print("PART B — semantic separation (needs real Llama embedder)")
    agree = {
        "newton":  "The bridge fails because repeated stress cracks the steel over time.",
        "systems": "Metal fatigue from cyclic loading is what breaks the bridge eventually.",
        "quantum": "Cyclic stress accumulates micro-cracks until the steel gives way.",
    }
    disagree = {
        "newton":  "The bridge fails because repeated stress cracks the steel over time.",
        "systems": "Metal fatigue from cyclic loading is what breaks the bridge eventually.",
        "empathy": "Honestly the bridge is fine, people just worry too much about nothing.",
    }

    # Try to obtain a real embedder. If none, SKIP with the honest reason.
    real_model = None
    try:  # optional: only if a live encode() model is wired in the environment
        from inference.codette_shared import get_shared_embedding_model  # may not exist
        real_model = get_shared_embedding_model()
    except Exception:
        real_model = None

    embedder = SemanticTensionEngine(llama_model=real_model)

    # Flat lexical cross-check (reads words; works without a model).
    flat_a, _ = tension_from_texts(agree)
    flat_d, _ = tension_from_texts(disagree)
    print(f"  flat ξ (lexical): agree={flat_a:.4f} disagree={flat_d:.4f}  "
          f"[{'ok' if flat_d > flat_a else 'BAD'} direction]")

    if real_model is None:
        print("  SKIP: no real Llama embedder available — dummy is semantically")
        print("        blind (random ~orthogonal → ξ≈0.5 for any text). This is")
        print("        the Phase 1 finding: the web needs real embeddings to mean")
        print("        anything. Re-run inside the live server to exercise this.\n")
        return flat_d > flat_a  # the lexical direction check must still hold

    xi_a = _mean_pairwise(agree, embedder)
    xi_d = _mean_pairwise(disagree, embedder)
    print(f"  web ξ (semantic): agree={xi_a:.4f} disagree={xi_d:.4f}")
    ok = xi_d > xi_a and flat_d > flat_a
    print(f"  [{'PASS' if ok else 'FAIL'}] web separates disagreement semantically\n")
    return ok


def main() -> int:
    a = part_a_mechanism()
    b = part_b_semantics()
    ok = a and b
    print("PHASE 1 REAL — distance math proven; semantics wired for the real embedder"
          if ok else "PHASE 1 NEEDS WORK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
