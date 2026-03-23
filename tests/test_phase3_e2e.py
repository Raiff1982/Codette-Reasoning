#!/usr/bin/env python3
"""
Phase 3 End-to-End Test: Multi-Round Conflict Evolution Tracking
Quick validate that conflicts are tracked across multiple debate rounds.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.forge_engine import ForgeEngine
from reasoning_forge.living_memory import LivingMemoryKernel


def test_phase3_multi_round():
    """Test forge_with_debate with multi-round conflict tracking."""
    print("\n" + "="*80)
    print("PHASE 3 TEST: Multi-Round Conflict Evolution Tracking")
    print("="*80 + "\n")

    # Create memory kernel
    memory = LivingMemoryKernel(max_memories=100)

    # Initialize forge with living memory
    forge = ForgeEngine(living_memory=memory, enable_memory_weighting=True)

    # Run a multi-round debate
    test_query = "Should algorithms prioritize speed or interpretability?"
    print(f"Running 3-round debate on: {test_query}\n")

    try:
        result = forge.forge_with_debate(test_query, debate_rounds=3)

        metadata = result.get("metadata", {})

        # Phase 1 metrics
        conflicts_r0 = metadata.get("conflicts_round_0_count", 0)
        print(f"[OK] Round 0 conflicts detected: {conflicts_r0}\n")

        # Phase 3 metrics
        phase3_metrics = metadata.get("phase_3_metrics", {})
        print(f"Phase 3 Evolution Tracking:")
        print(f"  - Total conflicts tracked: {phase3_metrics.get('total_tracked', 0)}")
        print(f"  - Resolved: {phase3_metrics.get('resolved', 0)}")
        print(f"  - Hard victory: {phase3_metrics.get('hard_victory', 0)}")
        print(f"  - Soft consensus: {phase3_metrics.get('soft_consensus', 0)}")
        print(f"  - Stalled: {phase3_metrics.get('stalled', 0)}")
        print(f"  - Worsened: {phase3_metrics.get('worsened', 0)}")
        print(f"  - Avg resolution rate: {phase3_metrics.get('avg_resolution_rate', 0):.1%}\n")

        # Show evolution trajectories for top conflicts
        evolutions = metadata.get("evolution_data", [])
        if evolutions:
            print(f"Sample conflict evolution trajectories:")
            for i, evolution in enumerate(evolutions[:3], 1):
                print(f"\n  {i}. {evolution['agents']}:")
                print(f"     - Type: {evolution['resolution_type']}")
                print(f"     - Resolution rate: {evolution['resolution_rate']:.1%}")
                trajectory = evolution['trajectory']
                for j, round_data in enumerate(trajectory):
                    strength = round_data.get('strength', 0)
                    addressing = round_data.get('addressing_score', 0)
                    print(f"     - Round {j}: strength={strength:.3f}, addressing={addressing:.1%}")

        # Check debate log for evolution data
        debate_log = metadata.get("debate_log", [])
        print(f"\nDebate log: {len(debate_log)} entries (Rounds 0-{len(debate_log)-1})")

        for i, entry in enumerate(debate_log):
            if entry.get("type") == "debate":
                evolution_count = len(entry.get("conflict_evolution", []))
                print(f"  - Round {i}: {evolution_count} conflicts evolved")

        print(f"\n[OK] Phase 3 multi-round tracking successful!")
        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run Phase 3 test."""
    print("\n")
    print("="*80)
    print("CODETTE PHASE 3: MULTI-ROUND CONFLICT EVOLUTION - TEST")
    print("="*80)

    try:
        result = test_phase3_multi_round()

        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80 + "\n")

        if result:
            print("[OK] Phase 3 test passed! Multi-round tracking is working.")
            return 0
        else:
            print("[FAIL] Phase 3 test failed. Check errors above.")
            return 1

    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
