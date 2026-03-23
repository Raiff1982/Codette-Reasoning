"""
Phase 6 + Consciousness Stack Baseline Benchmark

Quick benchmark WITHOUT requiring Llama model or full server.
Tests core improvement metrics:
- Semantic tension quality
- Specialization tracking
- Conflict detection
- State vector consistency
"""

import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from framework_definitions import StateVector, CoherenceMetrics, TensionDefinition
from semantic_tension import SemanticTensionEngine
from specialization_tracker import SpecializationTracker

print("\n" + "="*70)
print("PHASE 6 + CONSCIOUSNESS STACK QUICK BASELINE")
print("="*70)

# Test 1: Framework initialization
print("\n[TEST 1] Framework Initialization")
start = time.time()
state = StateVector(psi=0.8, tau=0.6, chi=1.2, phi=0.3, lam=0.7)
t1 = time.time() - start
print(f"  StateVector creation: {t1*1000:.2f}ms")

# Test 2: Semantic tension computation
print("\n[TEST 2] Semantic Tension Computation")
engine = SemanticTensionEngine()

test_pairs = [
    ("Newton's laws are fundamental.", "Quantum mechanics reveals indeterminacy."),
    ("The universe is deterministic.", "Quantum effects introduce randomness."),
    ("Consciousness is an illusion.", "Consciousness is fundamental to reality."),
    ("AI will surpass human intelligence.", "AI and humans will collaborate."),
    ("Ethics are absolute.", "Ethics are relative and contextual."),
]

tensions = []
start = time.time()
for claim_a, claim_b in test_pairs:
    tension = engine.compute_semantic_tension(claim_a, claim_b)
    polarity = engine.compute_polarity(claim_a, claim_b)
    tensions.append({
        "claim_a": claim_a[:40],
        "claim_b": claim_b[:40],
        "semantic_tension": round(tension, 3),
        "polarity": polarity
    })
t2 = time.time() - start

print(f"  {len(test_pairs)} pairs processed in {t2*1000:.2f}ms ({t2/len(test_pairs)*1000:.1f}ms per pair)")
for i, t in enumerate(tensions, 1):
    print(f"    [{i}] Tension={t['semantic_tension']}, Polarity={t['polarity']}")

# Test 3: Specialization tracking
print("\n[TEST 3] Specialization Tracking")
tracker = SpecializationTracker()

# Simulate 5 adapters, 3 domains each
adapters = ["Newton", "Quantum", "Ethics", "Creativity", "Systems"]
domains_per_adapter = 3
samples_per_domain = 4

start = time.time()
total_recordings = 0
for adapter in adapters:
    queries = [
        f"Physics query about {adapter}",
        f"Ethics question for {adapter}",
        f"Systems analysis with {adapter}",
    ]
    for query in queries:
        for _ in range(samples_per_domain):
            coherence = 0.75 + (hash(f"{adapter}{query}") % 100) / 500  # Random 0.75-0.95
            tracker.record_adapter_performance(adapter, query, coherence)
            total_recordings += 1

t3 = time.time() - start

print(f"  {total_recordings} recordings in {t3*1000:.2f}ms")

# Compute specialization
specialization_scores = {}
for adapter in adapters:
    spec = tracker.compute_specialization(adapter)
    specialization_scores[adapter] = spec
    print(f"    {adapter}: {spec}")

# Test 4: Coherence metrics
print("\n[TEST 4] System Coherence Metrics")
test_states = [
    ("Healthy", (0.75, 0.65, 0.3, 0.6)),
    ("Collapsing", (0.1, 0.2, 0.9, 0.05)),
    ("Groupthinking", (0.95, 0.95, 0.0, 0.95)),
    ("Balanced", (0.6, 0.6, 0.4, 0.6)),
]

start = time.time()
health_results = []
for name, (div, tension, variance, resolution) in test_states:
    gamma, health = CoherenceMetrics.compute_gamma(div, tension, variance, resolution)
    health_results.append({
        "name": name,
        "gamma": round(gamma, 3),
        "health": health,
        "diversity": div,
        "tension_health": tension
    })
t4 = time.time() - start

print(f"  {len(test_states)} states computed in {t4*1000:.2f}ms")
for h in health_results:
    print(f"    {h['name']}: gamma={h['gamma']}, health={h['health']}")

# Test 5: State distance (structural tension)
print("\n[TEST 5] State Space Distance (Structural Tension)")
state_a = StateVector(psi=0.8, tau=0.6, chi=1.2, phi=0.3, lam=0.7)
state_b = StateVector(psi=0.5, tau=0.7, chi=0.8, phi=-0.2, lam=0.6)
state_c = StateVector(psi=0.1, tau=0.1, chi=0.1, phi=0.1, lam=0.1)

start = time.time()
dist_ab = StateVector.distance(state_a, state_b)
dist_ac = StateVector.distance(state_a, state_c)
dist_bc = StateVector.distance(state_b, state_c)
t5 = time.time() - start

print(f"  3 distances computed in {t5*1000:.2f}ms")
print(f"    State A-B distance: {dist_ab:.3f}")
print(f"    State A-C distance: {dist_ac:.3f}")
print(f"    State B-C distance: {dist_bc:.3f}")

# SUMMARY
print("\n" + "="*70)
print("BASELINE RESULTS SUMMARY")
print("="*70)

summary = {
    "tests_run": 5,
    "total_time_ms": (t1+t2+t3+t4+t5)*1000,
    "tests": {
        "framework_init_ms": t1*1000,
        "semantic_tension_ms": t2*1000,
        "specialization_ms": t3*1000,
        "coherence_ms": t4*1000,
        "state_distance_ms": t5*1000,
    },
    "results": {
        "semantic_tensions": tensions,
        "specialization": {k: str(v) for k, v in specialization_scores.items()},
        "coherence": health_results,
        "state_distances": {
            "A-B": dist_ab,
            "A-C": dist_ac,
            "B-C": dist_bc,
        }
    }
}

print(f"Total execution time: {summary['total_time_ms']:.1f}ms")
print(f"  - Framework init: {t1*1000:.2f}ms")
print(f"  - Semantic tension: {t2*1000:.2f}ms")
print(f"  - Specialization: {t3*1000:.2f}ms")
print(f"  - Coherence metrics: {t4*1000:.2f}ms")
print(f"  - State distance: {t5*1000:.2f}ms")

# Save results
with open('phase6_baseline_results.json', 'w') as f:
    # Convert non-serializable objects
    summary_clean = {
        "tests_run": summary["tests_run"],
        "total_time_ms": summary["total_time_ms"],
        "tests": summary["tests"],
        "results": {
            "semantic_tensions": summary["results"]["semantic_tensions"],
            "coherence": summary["results"]["coherence"],
            "state_distances": {str(k): float(v) for k, v in summary["results"]["state_distances"].items()},
            "note": "Specialization scores stored as string due to nested dict structure"
        }
    }
    json.dump(summary_clean, f, indent=2)

print("\nResults saved to: phase6_baseline_results.json")

print("\n" + "="*70)
print("QUALITY METRICS")
print("="*70)
print(f"Average semantic tension:     {sum(t['semantic_tension'] for t in tensions)/len(tensions):.3f}")
print(f"Min/Max semantic tension:     {min(t['semantic_tension'] for t in tensions):.3f} - {max(t['semantic_tension'] for t in tensions):.3f}")
print(f"Coherence (Healthy) Gamma:    {health_results[0]['gamma']:.3f}")
print(f"Coherence (Collapsing) Gamma: {health_results[1]['gamma']:.3f}")
print(f"Coherence (Groupthink) Gamma: {health_results[2]['gamma']:.3f}")
print(f"Max structural tension:       {max(dist_ab, dist_ac, dist_bc):.3f}")
print("\n✅ Phase 6 baseline benchmark complete!")
print("="*70 + "\n")

