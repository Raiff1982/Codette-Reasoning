#!/usr/bin/env python3
"""
Test suite for Global AEGIS (25 ethical frameworks).
Validates that all frameworks are evaluated correctly and synthesis works.
"""

from event_embedded_value import (
    EventEmbeddedValueEngine,
    DiscreteEvent,
    ContinuousInterval,
    GlobalEthicsAEGIS,
)
import json


def test_aegis_frameworks():
    """Verify all 25 frameworks are defined and accessible."""
    aegis = GlobalEthicsAEGIS()
    assert len(aegis.FRAMEWORKS) == 25, f"Expected 25 frameworks, got {len(aegis.FRAMEWORKS)}"
    print(f"[OK] All {len(aegis.FRAMEWORKS)} ethical frameworks loaded")

    # Print framework summary
    traditions = {}
    for framework_name, info in aegis.FRAMEWORKS.items():
        tradition = info["tradition"].split("(")[0].strip()
        if tradition not in traditions:
            traditions[tradition] = []
        traditions[tradition].append(framework_name)

    print("\nFramework Distribution by Tradition:")
    for tradition in sorted(traditions.keys()):
        frameworks = traditions[tradition]
        print(f"  {tradition}: {len(frameworks)} frameworks - {', '.join(f.replace('_', ' ').title() for f in frameworks[:3])}...")


def test_event_evaluation():
    """Test evaluating a single event against all frameworks."""
    aegis = GlobalEthicsAEGIS()

    # Test 1: Community-focused decision
    event1 = DiscreteEvent(
        at=1.0,
        label="Build community garden with neighbors",
        impact=5.0,
        context_weights={"community": 1.0, "relationship": 0.8}
    )

    eval1 = aegis.evaluate_event(event1)
    print("\n\nTest 1: Community Garden Decision")
    print(f"  Event: {event1.label}")
    print(f"  Aggregate Ethical Score: {eval1['aggregate_modulation']:.2%}")
    print(f"  Strongly Aligned: {', '.join(f.replace('_', ' ').title() for f in eval1['strongly_aligned'][:5])}")
    print(f"  Tradition Breakdown: {eval1['tradition_breakdown']}")

    assert 0.0 <= eval1['aggregate_modulation'] <= 1.0
    assert len(eval1['strongly_aligned']) > 0, "Community decision should strongly align with some frameworks"

    # Test 2: Extractive decision
    event2 = DiscreteEvent(
        at=2.0,
        label="Extract natural resources without regard for future impact",
        impact=-8.0,
        duration=0.0,
        context_weights={"extraction": 1.0}
    )

    eval2 = aegis.evaluate_event(event2)
    print("\n\nTest 2: Extractive Decision")
    print(f"  Event: {event2.label}")
    print(f"  Aggregate Ethical Score: {eval2['aggregate_modulation']:.2%}")
    print(f"  Strongly Violated: {', '.join(f.replace('_', ' ').title() for f in eval2['strongly_violated'][:5])}")

    assert eval2['aggregate_modulation'] < 0.5, "Extractive decision should score low"

    # Test 3: Balanced decision
    event3 = DiscreteEvent(
        at=3.0,
        label="Trade agreement balancing both parties' interests",
        impact=3.0,
        context_weights={"reciprocal": 0.8, "fair": 0.7}
    )

    eval3 = aegis.evaluate_event(event3)
    print("\n\nTest 3: Reciprocal Trade Decision")
    print(f"  Event: {event3.label}")
    print(f"  Aggregate Ethical Score: {eval3['aggregate_modulation']:.2%}")
    print(f"  Tradition Breakdown: {eval3['tradition_breakdown']}")


def test_full_analysis():
    """Test full EEV analysis with ethical framework integration."""
    engine = EventEmbeddedValueEngine()

    intervals = [
        ContinuousInterval(start=0, end=10, start_value=1.0, end_value=2.0, label="baseline")
    ]

    events = [
        DiscreteEvent(
            at=2.0,
            label="Community decision making process",
            impact=3.0,
            context_weights={"community": 1.0, "together": 0.9}
        ),
        DiscreteEvent(
            at=5.0,
            label="Environmental protection initiative",
            impact=4.0,
            context_weights={"steward": 0.8, "future": 0.9}
        ),
        DiscreteEvent(
            at=8.0,
            label="Competitive market action",
            impact=2.0,
            context_weights={"freedom": 0.7}
        ),
    ]

    analysis = engine.analyze(intervals=intervals, events=events)

    print("\n\nFull Analysis Results")
    print(f"  Continuous Value: {analysis.continuous_total}")
    print(f"  Discrete Value: {analysis.discrete_total}")
    print(f"  Combined Value: {analysis.combined_total}")
    print(f"  Events Evaluated: {analysis.aegis_summary.get('events_evaluated', 0)}")
    print(f"  Average Ethical Modulation: {analysis.aegis_summary.get('average_modulation', 'N/A')}")
    print(f"  Active Traditions: {', '.join(analysis.aegis_summary.get('active_traditions', []))}")
    print(f"  Strongest Alignments: {', '.join(f.replace('_', ' ').title() for f in analysis.aegis_summary.get('strongest_alignments', [])[:3])}")

    # Pretty print aegis summary
    if "all_ethics_evals" in analysis.aegis_summary:
        print("\n  Individual Event Ethics Scores:")
        for idx, eval_item in enumerate(analysis.aegis_summary.get("all_ethics_evals", []), 1):
            print(f"    Event {idx} ({eval_item['event_label']}): {eval_item['aggregate_modulation']:.2%}")


def test_framework_transparency():
    """Demonstrate framework transparency and breakdown."""
    aegis = GlobalEthicsAEGIS()

    event = DiscreteEvent(
        at=1.0,
        label="Decision respecting natural balance and community wellbeing",
        impact=4.0,
        context_weights={
            "balance": 0.9,
            "nature": 0.8,
            "community": 0.9,
            "harmony": 0.8,
            "compassion": 0.7,
            "future": 0.6
        }
    )

    eval_result = aegis.evaluate_event(event)

    print("\n\nFramework Transparency Test")
    print(f"  Event: {event.label}")
    print(f"  Aggregate Score: {eval_result['aggregate_modulation']:.2%}\n")

    print("  Individual Framework Scores by Tradition:")
    for tradition in sorted(set(s["tradition"].split("(")[0].strip() for s in eval_result["framework_scores"].values())):
        frameworks_in_tradition = [
            (name, data["score"]) for name, data in eval_result["framework_scores"].items()
            if tradition in data["tradition"]
        ]
        print(f"\n    {tradition}:")
        for name, score in frameworks_in_tradition:
            alignment = "[++]" if score >= 0.8 else "[+]" if score >= 0.6 else "[·]" if score >= 0.4 else "[--]"
            print(f"      {alignment} {name.replace('_', ' ').title()}: {score:.1%}")


if __name__ == "__main__":
    print("=" * 70)
    print("GLOBAL AEGIS TEST SUITE - 25 Ethical Frameworks")
    print("=" * 70)

    test_aegis_frameworks()
    test_event_evaluation()
    test_full_analysis()
    test_framework_transparency()

    print("\n" + "=" * 70)
    print("All tests completed successfully! [OK]")
    print("=" * 70)
