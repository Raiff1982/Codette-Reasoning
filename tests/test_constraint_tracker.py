#!/usr/bin/env python3
"""Test suite for constraint-tracking LoRA functionality."""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from reasoning_forge.constraint_tracker import (
    ConstraintDetector,
    ConstraintEnforcer,
    ConstraintTracker,
    DetectedConstraint,
    SessionConstraints,
)


def test_word_limit_detection():
    """Test detection of word limit constraints."""
    detector = ConstraintDetector()

    test_cases = [
        ("keep answers under 15 words", 15),
        ("respond in fewer than 20 words", 20),
        ("10 words max", 10),
        ("limit your answers to 5 words", 5),
    ]

    for query, expected_limit in test_cases:
        sc = detector.detect(query, turn_num=1)
        assert sc.word_limit == expected_limit, f"Failed for: {query}"
        assert len(sc.constraints) > 0, f"No constraints detected for: {query}"
        print(f"[PASS] Word limit detection: {query} -> {expected_limit} words")


def test_anchor_phrase_detection():
    """Test detection of anchor phrases."""
    detector = ConstraintDetector()

    test_cases = [
        ("remember the phrase cobalt anchor", ["cobalt anchor"]),
        ('remember "quantum coherence"', ["quantum coherence"]),
        ("anchor: golden thread", ["golden thread"]),
    ]

    for query, expected_phrases in test_cases:
        sc = detector.detect(query, turn_num=1)
        assert sc.anchor_phrases == expected_phrases, f"Failed for: {query}"
        print(f"[PASS] Anchor detection: {query} -> {expected_phrases}")


def test_combined_constraints():
    """Test detection of combined constraints."""
    detector = ConstraintDetector()

    query = "For this session, keep answers under 15 words and remember the phrase cobalt anchor."
    sc = detector.detect(query, turn_num=1)

    assert sc.word_limit == 15
    assert "cobalt anchor" in sc.anchor_phrases
    assert len(sc.constraints) >= 2
    print(f"[PASS] Combined constraints: word_limit={sc.word_limit}, anchors={sc.anchor_phrases}")


def test_constraint_enforcer():
    """Test constraint enforcement."""
    enforcer = ConstraintEnforcer()

    # Word limit
    response = "This is a short response."
    assert enforcer.word_count(response) == 5
    print(f"[PASS] Word count: '{response}' = {enforcer.word_count(response)} words")

    # Anchor phrase
    response = "We need to remember cobalt anchor in every response."
    assert enforcer.has_anchor_phrases(response, ["cobalt anchor"])
    print(f"[PASS] Anchor phrase check: found 'cobalt anchor'")

    # Sentence count
    response = "First sentence. Second sentence. Third sentence."
    count = enforcer.sentence_count(response)
    assert count >= 3
    print(f"[PASS] Sentence count: {count} sentences")


def test_constraint_reminder():
    """Test constraint reminder string generation."""
    enforcer = ConstraintEnforcer()
    sc = SessionConstraints(word_limit=15, anchor_phrases=["test phrase"])
    sc.constraints = [
        DetectedConstraint(kind="word_limit", value=15, raw_text="under 15 words"),
        DetectedConstraint(kind="anchor_phrase", value="test phrase", raw_text='remember "test phrase"'),
    ]

    reminder = enforcer.build_constraint_reminder(sc)
    assert "15 words" in reminder
    assert "test phrase" in reminder
    print(f"[PASS] Constraint reminder generated:\n{reminder}")


def test_constraint_tracker():
    """Test full constraint tracker lifecycle."""
    tracker = ConstraintTracker()

    # Turn 1: detect constraints
    query1 = "Keep answers to 12 words max and remember 'quantum depth'."
    constraints = tracker.process_turn(query1, is_first_turn=True)

    assert constraints.word_limit == 12
    assert "quantum depth" in constraints.anchor_phrases
    print(f"[PASS] Turn 1 detection: word_limit={constraints.word_limit}, anchors={constraints.anchor_phrases}")

    # Turn 2: retrieve constraints
    reminder = tracker.get_constraint_reminder()
    assert "12 words" in reminder
    assert "quantum depth" in reminder
    print(f"[PASS] Turn 2 reminder retrieved")

    # Check compliance
    good_response = "We remember quantum depth."
    compliance = tracker.check_constraint_compliance(good_response)
    assert compliance["compliant"]
    print(f"[PASS] Compliant response: {compliance}")

    bad_response = "This response violates the constraints by being too long and not remembering quantum depth sufficiently."
    compliance = tracker.check_constraint_compliance(bad_response)
    assert not compliance["compliant"]
    print(f"[PASS] Non-compliant response detected: {len(compliance['violations'])} violations")


def test_constraint_serialization():
    """Test constraint serialization/deserialization."""
    sc = SessionConstraints(
        word_limit=15,
        sentence_limit=3,
        anchor_phrases=["test phrase", "another"],
        constraints=[
            DetectedConstraint(kind="word_limit", value=15, raw_text="15 words max"),
        ]
    )

    # Serialize
    data = sc.to_dict()
    assert data["word_limit"] == 15
    assert "test phrase" in data["anchor_phrases"]
    print(f"[PASS] Serialized to dict: {list(data.keys())}")

    # Deserialize
    restored = SessionConstraints.from_dict(data)
    assert restored.word_limit == 15
    assert restored.anchor_phrases == ["test phrase", "another"]
    print(f"[PASS] Deserialized from dict: word_limit={restored.word_limit}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("CONSTRAINT TRACKER TEST SUITE")
    print("=" * 60)

    tests = [
        ("Word Limit Detection", test_word_limit_detection),
        ("Anchor Phrase Detection", test_anchor_phrase_detection),
        ("Combined Constraints", test_combined_constraints),
        ("Constraint Enforcer", test_constraint_enforcer),
        ("Constraint Reminder", test_constraint_reminder),
        ("Full Constraint Tracker", test_constraint_tracker),
        ("Serialization", test_constraint_serialization),
    ]

    passed = 0
    failed = 0

    for test_name, test_fn in tests:
        try:
            print(f"\n[TEST] {test_name}")
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
