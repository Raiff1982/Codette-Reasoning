#!/usr/bin/env python3
"""
Phase 1 End-to-End Test
Quick validate that forge_with_debate produces conflict detection metrics
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.forge_engine import ForgeEngine
from evaluation.conflict_tests import ConflictTestRunner, CONFLICT_PROMPTS

def main():
    print("\n" + "="*80)
    print("PHASE 1 END-TO-END TEST: CONFLICT DETECTION IN DEBATE")
    print("="*80 + "\n")

    # Initialize forge
    print("Initializing ForgeEngine with conflict detection...\n")
    forge = ForgeEngine()

    # Test a single conflict-triggering prompt
    test_prompt = CONFLICT_PROMPTS[0]  # Ethics vs Efficiency

    print(f"Testing: {test_prompt['description']}")
    print(f"Query: {test_prompt['query']}\n")

    print("Running forge_with_debate()...\n")
    try:
        result = forge.forge_with_debate(test_prompt['query'], debate_rounds=1)

        metadata = result.get("metadata", {})

        print("[OK] forge_with_debate() completed\n")

        # Extract metrics
        print("Results:")
        print(f"  - Overall quality: {metadata.get('overall_quality', 0):.3f}")
        print(f"  - Ensemble coherence: {metadata.get('ensemble_coherence', 0):.3f}")
        print(f"  - Epistemic tension: {metadata.get('epistemic_tension', 0):.3f}")

        # Phase 1 metrics
        r0_conflicts = metadata.get("conflicts_round_0_count", 0)
        print(f"\n  PHASE 1 METRICS:")
        print(f"  - Conflicts detected (R0): {r0_conflicts}")

        if r0_conflicts > 0:
            detected = metadata.get("conflicts_detected", [])
            print(f"  - Top conflicts:")
            for i, conflict in enumerate(detected[:3], 1):
                print(f"      {i}. {conflict['conflict_type']}: {conflict['agent_a']} vs {conflict['agent_b']}")
                print(f"         Strength: {conflict['conflict_strength']:.3f}")

        # Debate log
        debate_log = metadata.get("debate_log", [])
        print(f"\n  - Debate log entries: {len(debate_log)}")
        for entry in debate_log:
            round_num = entry.get("round", "?")
            entry_type = entry.get("type", "unknown")
            print(f"      Round {round_num} ({entry_type}): "
                  f"{entry.get('conflicts_detected', 0)} conflicts")

        print("\n[OK] Phase 1 integration working successfully!\n")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
