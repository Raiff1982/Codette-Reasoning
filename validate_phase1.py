#!/usr/bin/env python3
"""
Phase 1 Validation Script
Quick test to verify conflict detection is working.
"""

import sys
import json
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all Phase 1 modules can be imported."""
    print("\n" + "="*80)
    print("PHASE 1 VALIDATION: IMPORT TEST")
    print("="*80 + "\n")

    try:
        print("Importing TokenConfidenceEngine...")
        from reasoning_forge.token_confidence import TokenConfidenceEngine
        print("  ✓ TokenConfidenceEngine imported")

        print("Importing ConflictEngine...")
        from reasoning_forge.conflict_engine import ConflictEngine
        print("  ✓ ConflictEngine imported")

        print("Importing ForgeEngine...")
        from reasoning_forge.forge_engine import ForgeEngine
        print("  ✓ ForgeEngine imported")

        print("Importing ConflictTestRunner...")
        from evaluation.conflict_tests import ConflictTestRunner
        print("  ✓ ConflictTestRunner imported")

        return True

    except Exception as e:
        print(f"\n✗ IMPORT FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_confidence_engine():
    """Test TokenConfidenceEngine basic functionality."""
    print("\n" + "="*80)
    print("PHASE 1 VALIDATION: TOKEN CONFIDENCE ENGINE")
    print("="*80 + "\n")

    try:
        from reasoning_forge.token_confidence import TokenConfidenceEngine

        engine = TokenConfidenceEngine()
        print("✓ TokenConfidenceEngine initialized")

        # Test semantic marker parsing
        test_response = (
            "I'm confident that this approach will work. However, it's possible that we'll "
            "encounter issues. The data clearly shows a trend towards improvement."
        )
        peer_responses = {
            "peer1": "This approach might be problematic in some cases.",
            "peer2": "I argue that this is fundamentally sound.",
        }

        scores = engine.score_tokens(test_response, "agent1", peer_responses)
        print(f"✓ Token confidence scoring completed")
        print(f"  - Claims extracted: {len(scores.claims)}")
        print(f"  - Token scores: {len(scores.token_scores)} tokens")
        print(f"  - Mean confidence: {sum(scores.token_scores) / max(len(scores.token_scores), 1):.3f}")

        return True

    except Exception as e:
        print(f"\n✗ TOKEN CONFIDENCE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conflict_engine():
    """Test ConflictEngine basic functionality."""
    print("\n" + "="*80)
    print("PHASE 1 VALIDATION: CONFLICT ENGINE")
    print("="*80 + "\n")

    try:
        from reasoning_forge.token_confidence import TokenConfidenceEngine
        from reasoning_forge.conflict_engine import ConflictEngine

        token_conf = TokenConfidenceEngine()
        conflict_engine = ConflictEngine(token_confidence_engine=token_conf)
        print("✓ ConflictEngine initialized")

        # Test conflict detection with synthetic responses
        agent_analyses = {
            "agent_a": "The algorithm must be deterministic for maximum control. "
                       "This ensures predictability and reliability in all cases.",
            "agent_b": "A probabilistic approach is superior because it captures the "
                       "inherent uncertainty in real-world systems. Determinism is rigid.",
        }

        conflicts = conflict_engine.detect_conflicts(agent_analyses)
        print(f"✓ Conflict detection completed")
        print(f"  - Conflicts detected: {len(conflicts)}")

        if conflicts:
            top_conflict = conflicts[0]
            print(f"\n  Top conflict:")
            print(f"    - Type: {top_conflict.conflict_type}")
            print(f"    - Strength: {top_conflict.conflict_strength:.3f}")
            print(f"    - Agent A claim: {top_conflict.claim_a[:60]}...")
            print(f"    - Agent B claim: {top_conflict.claim_b[:60]}...")
            print(f"    - Overlap: {top_conflict.semantic_overlap:.3f}")

        return True

    except Exception as e:
        print(f"\n✗ CONFLICT ENGINE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_forge_integration():
    """Test that ForgeEngine initializes with conflict detection."""
    print("\n" + "="*80)
    print("PHASE 1 VALIDATION: FORGE ENGINE INTEGRATION")
    print("="*80 + "\n")

    try:
        from reasoning_forge.forge_engine import ForgeEngine

        print("Initializing ForgeEngine with conflict detection...")
        forge = ForgeEngine()
        print("✓ ForgeEngine initialized")

        # Check that conflict engines are attached
        if not hasattr(forge, 'token_confidence'):
            raise AttributeError("ForgeEngine missing token_confidence engine")
        print("✓ TokenConfidenceEngine attached to ForgeEngine")

        if not hasattr(forge, 'conflict_engine'):
            raise AttributeError("ForgeEngine missing conflict_engine")
        print("✓ ConflictEngine attached to ForgeEngine")

        # Test a simple debate (this will be slow without GPU)
        print("\nTesting forge_with_debate() on a simple concept...")
        print("  (This may take a moment without GPU acceleration)")

        result = forge.forge_with_debate("Should an algorithm prioritize speed or clarity?", debate_rounds=1)

        metadata = result.get("metadata", {})
        print("✓ forge_with_debate() completed successfully")

        # Check Phase 1 metrics
        round_0_conflicts = metadata.get("conflicts_round_0_count", 0)
        print(f"  - Conflicts detected (R0): {round_0_conflicts}")

        if "debate_log" in metadata:
            print(f"  - Debate rounds logged: {len(metadata['debate_log'])}")

        if "ensemble_coherence" in metadata:
            print(f"  - Ensemble coherence: {metadata['ensemble_coherence']:.3f}")

        return True

    except Exception as e:
        print(f"\n✗ FORGE INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n")
    print("=" * 80)
    print("CODETTE PHASE 1: CONFLICT DETECTION - VALIDATION SUITE")
    print("=" * 80)

    tests = [
        ("Imports", test_imports),
        ("Token Confidence Engine", test_token_confidence_engine),
        ("Conflict Engine", test_conflict_engine),
        ("Forge Integration", test_forge_integration),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except KeyboardInterrupt:
            print("\n\n✗ Tests interrupted by user")
            return 1
        except Exception as e:
            print(f"\n✗ Unexpected error in {test_name}: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80 + "\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed\n")

    if passed == total:
        print("✓ All Phase 1 validations passed! Ready for testing.")
        return 0
    else:
        print(f"✗ {total - passed} validation(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
