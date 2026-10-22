"""RoutingMetrics and SpecializationTracker are fed by the live turn, and only with what is known."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

from reasoning_forge import reach
from reasoning_forge.routing_metrics import RoutingMetrics
from reasoning_forge.specialization_tracker import SpecializationTracker
from inference.codette_forge_bridge import CodetteForgeBridge


def _bridge():
    b = CodetteForgeBridge.__new__(CodetteForgeBridge)
    b.forge = types.SimpleNamespace(routing_metrics=RoutingMetrics(),
                                    specialization=SpecializationTracker())
    reach.instrument_forge(b.forge)
    return b


def _result(**kw):
    route = types.SimpleNamespace(primary="newton", secondary=["empathy"], confidence=0.8,
                                  strategy="keyword")
    d = {"response": "an answer", "route": route, "adapter": "newton"}
    d.update(kw)
    return d


def test_a_live_turn_reaches_both_and_health_counts_it():
    b = _bridge()
    b._observe_routing(_result(measured_coherence=0.7), "why does the sky look blue?")
    rm, sp = b.forge.routing_metrics, b.forge.specialization
    assert rm.total_queries == 1 and rm.adapter_primary_count == {"newton": 1}
    assert sum(len(v) for d in sp.domain_accuracy.values() for v in d.values()) >= 1
    assert rm.invocation_stats()["calls"] == 1
    assert sp.invocation_stats()["calls"] == 1


def test_unknown_things_stay_unknown():
    b = _bridge()
    b._observe_routing(_result(), "hello there")                 # no measured_coherence
    rm, sp = b.forge.routing_metrics, b.forge.specialization
    assert rm.total_queries == 1
    assert sp.domain_accuracy == {}                              # no coherence invented
    assert rm.get_summary()["memory_boost_rate"] is None         # the flag was never exposed


def test_benchmark_queries_and_empty_results_are_not_recorded():
    b = _bridge()
    exam = "What is the correct answer to this question?\n(A) a\n(B) b\n(C) c\n(D) d"
    b._observe_routing(_result(measured_coherence=0.9), exam)
    b._observe_routing(_result(response=""), "a normal question")
    b._observe_routing({"response": "x"}, "no route and no adapter")
    assert b.forge.routing_metrics.total_queries == 0


def test_generate_cannot_be_broken_by_the_observation():
    import re
    src = (ROOT / "inference" / "codette_forge_bridge.py").read_text(encoding="utf-8")
    # The call sits inside its own try/except in generate(), after the advisory.
    assert re.search(r"try:\s+self\._observe_routing\(result, query\)\s+except Exception", src)
