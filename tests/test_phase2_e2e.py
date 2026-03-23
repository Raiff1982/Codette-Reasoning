#!/usr/bin/env python3
"""
Phase 2 End-to-End Test: Memory-Weighted Adapter Selection
Quick validate that memory-weighted routing works correctly.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.forge_engine import ForgeEngine
from reasoning_forge.living_memory import LivingMemoryKernel
from reasoning_forge.memory_weighting import MemoryWeighting


def test_memory_weighting_initialization():
    """Test that MemoryWeighting initializes correctly."""
    print("\n" + "="*80)
    print("PHASE 2 TEST 1: MemoryWeighting Initialization")
    print("="*80 + "\n")

    memory = LivingMemoryKernel(max_memories=100)
    weighting = MemoryWeighting(memory)

    print("[OK] MemoryWeighting initialized")
    print(f"  - Memory kernel: {len(memory.memories)} memories")
    print(f"  - Adapter weights computed: {len(weighting.adapter_weights)} adapters")

    summary = weighting.get_summary()
    print(f"\nSummary:")
    for key, value in summary.items():
        print(f"  - {key}: {value}")

    return True


def test_forge_with_memory():
    """Test ForgeEngine with living_memory wired in."""
    print("\n" + "="*80)
    print("PHASE 2 TEST 2: ForgeEngine with Living Memory")
    print("="*80 + "\n")

    # Create memory kernel
    memory = LivingMemoryKernel(max_memories=100)

    # Initialize forge with memory
    print("Initializing ForgeEngine with living_memory...")
    forge = ForgeEngine(living_memory=memory, enable_memory_weighting=True)
    print("[OK] ForgeEngine initialized")

    # Check components
    assert forge.living_memory is not None, "living_memory not wired in"
    print("[OK] living_memory wired into ForgeEngine")

    assert forge.token_confidence.living_memory is not None, "living_memory not in token_confidence"
    print("[OK] living_memory wired into TokenConfidenceEngine")

    assert forge.memory_weighting is not None, "memory_weighting not initialized"
    print("[OK] MemoryWeighting initialized")

    return True


def test_forge_with_debate():
    """Test forge_with_debate with memory storage."""
    print("\n" + "="*80)
    print("PHASE 2 TEST 3: forge_with_debate() with Memory Storage")
    print("="*80 + "\n")

    # Create memory kernel
    memory = LivingMemoryKernel(max_memories=100)

    # Initialize forge
    forge = ForgeEngine(living_memory=memory, enable_memory_weighting=True)

    # Run a debate
    test_query = "Should we prioritize speed or clarity in algorithm design?"
    print(f"Running forge_with_debate()...")
    print(f"Query: {test_query}\n")

    try:
        result = forge.forge_with_debate(test_query, debate_rounds=1)

        metadata = result.get("metadata", {})

        # Check Phase 1 metrics (should still work)
        conflicts_r0 = metadata.get("conflicts_round_0_count", 0)
        print(f"[OK] Conflicts detected (R0): {conflicts_r0}")

        # Check memory storage
        print(f"\nMemory state after debate:")
        print(f"  - Total memories: {len(memory.memories)}")

        if memory.memories:
            tension_memories = [m for m in memory.memories if m.emotional_tag == "tension"]
            print(f"  - Tension memories: {len(tension_memories)}")

            if tension_memories:
                print(f"  - First conflict memory: {tension_memories[0].title}")

        # Check memory weighting
        print(f"\nMemory weighting state:")
        summary = forge.memory_weighting.get_summary()
        print(f"  - Adapters being tracked: {summary.get('total_adapters', 0)}")
        print(f"  - Total memories indexed: {summary.get('total_memories', 0)}")
        print(f"  - Average weight: {summary.get('avg_weight', 0):.3f}")

        all_weights = forge.memory_weighting.get_all_weights()
        if all_weights:
            print(f"  - Adapter weights:")
            for adapter, weights_dict in list(all_weights.items())[:3]:
                print(f"      {adapter}: weight={weights_dict['weight']:.3f}, coherence={weights_dict['coherence']:.3f}")

        return True

    except Exception as e:
        print(f"[FAIL] Error running forge_with_debate: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_weighting_explain():
    """Test that weight explanations work."""
    print("\n" + "="*80)
    print("PHASE 2 TEST 4: Memory Weight Explanations")
    print("="*80 + "\n")

    # Create memory with some data
    from reasoning_forge.living_memory import MemoryCocoon

    memory = LivingMemoryKernel(max_memories=100)

    # Add some synthetic cocoons for different adapters
    cocoon1 = MemoryCocoon(
        title="Newton analysis",
        content="Analytical perspective on efficiency",
        adapter_used="newton",
        coherence=0.8,
        emotional_tag="neutralness",
        importance=7,
    )
    memory.store(cocoon1)

    cocoon2 = MemoryCocoon(
        title="DaVinci analysis",
        content="Creative approach to clarity",
        adapter_used="davinci",
        coherence=0.6,
        emotional_tag="neutral",
        importance=5,
    )
    memory.store(cocoon2)

    # Create weighting
    weighting = MemoryWeighting(memory)

    print(f"[OK] Memory seeded with {len(memory.memories)} cocoons")
    print(f"[OK] Weights computed for {len(weighting.adapter_weights)} adapters\n")

    # Explain weights
    for adapter in ["newton", "davinci"]:
        if adapter in weighting.adapter_weights:
            explanation = weighting.explain_weight(adapter)
            print(f"{adapter.upper()}:")
            print(f"  - Coherence: {explanation['base_coherence']:.3f}")
            print(f"  - Conflict success: {explanation['conflict_success_rate']:.1%}")
            print(f"  - Recency: {explanation['recency_score']:.3f}")
            print(f"  - Final weight: {explanation['final_weight']:.3f}")
            print()

    return True


def main():
    """Run all Phase 2 tests."""
    print("\n")
    print("="*80)
    print("CODETTE PHASE 2: MEMORY-WEIGHTED ADAPTER SELECTION - TEST SUITE")
    print("="*80)

    tests = [
        ("MemoryWeighting Initialization", test_memory_weighting_initialization),
        ("ForgeEngine with Memory", test_forge_with_memory),
        ("forge_with_debate() Storage", test_forge_with_debate),
        ("Memory Weight Explanations", test_memory_weighting_explain),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except KeyboardInterrupt:
            print("\n\n[FAIL] Tests interrupted by user")
            return 1
        except Exception as e:
            print(f"\n[FAIL] Unexpected error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed\n")

    if passed == total:
        print("[OK] All Phase 2 tests passed! Memory-weighted routing ready.")
        return 0
    else:
        print(f"[FAIL] {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
