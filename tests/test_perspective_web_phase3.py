#!/usr/bin/env python3
"""Phase 3 proof: spectral identity glyphs over a conversation's tension history.

Simulates a multi-turn conversation and shows SessionGlyphTracker forms stable
FFT glyphs from each perspective's divergence-from-consensus time-series. A
perspective with a STRUCTURED dissent rhythm should form a stable glyph; the
tracker should accumulate history turn over turn and only emit a glyph once
there's enough signal (never fabricated early).

Lexical mode (no Llama needed) — deterministic per text, CI-safe.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reasoning_forge"))

from reasoning_forge.perspective_web import SessionGlyphTracker


def main() -> int:
    tracker = SessionGlyphTracker(embedder=None, glyph_components=8)

    # 12-turn conversation. newton & systems stay near consensus; empathy
    # dissents on a structured cadence (alternating strong/mild disagreement).
    base_a = "the steel structure fails from repeated cyclic stress over time"
    base_b = "metal fatigue under cyclic loading is the failure mechanism here"
    dissent_strong = "no this is all wrong people just worry about nothing at all"
    dissent_mild = "the steel is probably fine but maybe some minor concern exists"

    glyph_turns = []
    for i in range(12):
        emp = dissent_strong if i % 2 == 0 else dissent_mild
        turn = tracker.observe_turn({
            "newton": base_a + f" (turn {i})",
            "systems": base_b + f" (turn {i})",
            "empathy": emp + f" (turn {i})",
        })
        if turn["glyphs"]:
            glyph_turns.append((turn["turn"], list(turn["glyphs"].keys())))

    print(f"  turns observed: {tracker.turns}")
    print(f"  history length per node: "
          f"{ {n: len(tracker.web.nodes[n].tension_history) for n in tracker.web.nodes} }")
    print(f"  first glyph appeared at turn: {glyph_turns[0][0] if glyph_turns else 'never'}")
    print(f"  total glyphs stored: {len(tracker.web.glyphs)}")
    if tracker.web.glyphs:
        g = tracker.web.glyphs[-1]
        print(f"  sample glyph: {g.glyph_id} source={g.source_node} "
              f"stability={g.stability_score:.3f} components={len(g.encoded_tension)}")

    checks = {
        "accumulated history over all turns": all(
            len(tracker.web.nodes[n].tension_history) == 12 for n in tracker.web.nodes),
        "no glyph before enough history (>=8)": (glyph_turns[0][0] >= 8) if glyph_turns else True,
        "at least one stable glyph formed": len(tracker.web.glyphs) >= 1,
        "glyph has spectral components": (len(tracker.web.glyphs[-1].encoded_tension) == 8)
                                         if tracker.web.glyphs else False,
    }
    print()
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    print()
    print("PHASE 3 REAL — spectral glyphs from real conversation tension history"
          if ok else "PHASE 3 NEEDS WORK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
