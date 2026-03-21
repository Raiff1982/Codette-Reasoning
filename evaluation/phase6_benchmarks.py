"""
Phase 6: Benchmarking Suite

Measures Phase 6 improvements:
1. Multi-round debate: Does accuracy improve across rounds?
2. Memory weighting: Does memory-boosted routing reduce error?
3. Semantic tension: Are embeddings better than heuristics?
4. Specialization: Are adapters maintaining domain expertise?

Run with: pytest test_phase6_e2e.py -v
"""

import json
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime


class Phase6Benchmarks:
    """
    Comprehensive Phase 6 evaluation suite.
    """

    def __init__(self, forge_engine=None):
        """
        Initialize benchmarks.

        Args:
            forge_engine: ForgeEngine instance to test against
        """
        self.forge = forge_engine
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "multi_round_convergence": {},      # Coherence per round
            "memory_weighting_impact": {},      # With vs. without memory
            "semantic_tension_quality": {},     # Embeddings vs heuristics
            "specialization_metrics": {},       # Domain expertise scores
        }

    def benchmark_multi_round_debate(self, queries: List[str], num_rounds: int = 3) -> Dict:
        """
        BENCHMARK 1: Multi-Round Debate Convergence

        Question: Does multi-round debate improve answer quality?

        Hypothesis: As agents debate across rounds:
        - Tensions decrease (convergence)
        - Coherence increases
        - Synthesis accuracy improves

        Measurement:
        - Run each query through N rounds
        - Track coherence_score per round
        - Track resolution_rate per round
        - Compute convergence rate (tension decay)

        Returns:
            {
                "queries_tested": int,
                "rounds_per_query": int,
                "coherence_by_round": {round: [scores...]},
                "convergence_rate": float,
                "improved_queries": int,
            }
        """
        if not self.forge:
            return {"error": "ForgeEngine not available"}

        coherence_by_round = {i: [] for i in range(num_rounds)}
        resolution_by_round = {i: [] for i in range(num_rounds)}
        improved_count = 0

        for query in queries:
            try:
                result = self.forge.forge_with_debate(query, num_rounds=num_rounds)
                metadata = result.get("metadata", {})

                # Extract per-round metrics
                for round_num in range(num_rounds):
                    round_key = f"round_{round_num}"
                    if round_key in metadata:
                        coherence = metadata[round_key].get("coherence", 0.5)
                        resolution = metadata[round_key].get("resolution_rate", 0.5)
                        coherence_by_round[round_num].append(coherence)
                        resolution_by_round[round_num].append(resolution)

                # Check if coherence improved from round 0 to final
                initial_coh = coherence_by_round[0][-1] if coherence_by_round[0] else 0.5
                final_coh = coherence_by_round[num_rounds - 1][-1] if coherence_by_round[num_rounds - 1] else 0.5

                if final_coh > initial_coh:
                    improved_count += 1

            except Exception as e:
                print(f"Error benchmarking query '{query[:50]}...': {e}")

        # Compute statistics
        coherence_means = {
            i: float(np.mean(scores)) if scores else 0.5 for i, scores in coherence_by_round.items()
        }

        convergence_rate = 0.0
        if num_rounds > 1:
            initial = coherence_means.get(0, 0.5)
            final = coherence_means.get(num_rounds - 1, 0.5)
            if initial > 0:
                convergence_rate = (final - initial) / initial  # Positive = improvement

        self.results["multi_round_convergence"] = {
            "queries_tested": len(queries),
            "rounds_per_query": num_rounds,
            "coherence_by_round": {str(k): round(v, 3) for k, v in coherence_means.items()},
            "convergence_rate": round(convergence_rate, 3),
            "improved_queries": improved_count,
            "improvement_percentage": round(100 * improved_count / max(len(queries), 1), 1),
        }

        return self.results["multi_round_convergence"]

    def benchmark_memory_weighting(self, queries: List[str]) -> Dict:
        """
        BENCHMARK 2: Memory Weighting Impact

        Question: Does memory-weighted routing reduce error vs. pure keyword routing?

        Hypothesis: Adapter weights from past experience guide routing better
        than keywords alone.

        Measurement:
        - Run each query WITHOUT memory weighting (baseline)
        - Run each query WITH memory weighting
        - Compare: coherence_score, conflict_resolution_rate, adapter_diversity
        - Compute improvement delta

        Returns:
            {
                "baseline_coherence": float,
                "memory_coherence": float,
                "coherence_improvement": float,
                "memory_helps_percentage": float,
                "avg_resolution_baseline": float,
                "avg_resolution_memory": float,
            }
        """
        if not self.forge:
            return {"error": "ForgeEngine not available"}

        baseline_coherences = []
        memory_coherences = []
        baseline_resolutions = []
        memory_resolutions = []

        for query in queries:
            try:
                # Baseline: without memory weights
                result_baseline = self.forge.forge_with_debate(query, use_memory_weights=False)
                baseline_meta = result_baseline.get("metadata", {})
                baseline_coherences.append(baseline_meta.get("coherence", 0.5))
                baseline_resolutions.append(baseline_meta.get("resolution_rate", 0.5))

                # With memory: weights from past performance
                result_memory = self.forge.forge_with_debate(query, use_memory_weights=True)
                memory_meta = result_memory.get("metadata", {})
                memory_coherences.append(memory_meta.get("coherence", 0.5))
                memory_resolutions.append(memory_meta.get("resolution_rate", 0.5))

            except Exception as e:
                print(f"Error in memory weighting benchmark: {e}")

        # Compute statistics
        baseline_coh = float(np.mean(baseline_coherences)) if baseline_coherences else 0.5
        memory_coh = float(np.mean(memory_coherences)) if memory_coherences else 0.5
        coh_improve = memory_coh - baseline_coh

        baseline_res = float(np.mean(baseline_resolutions)) if baseline_resolutions else 0.5
        memory_res = float(np.mean(memory_resolutions)) if memory_resolutions else 0.5

        # Percentage of queries where memory helped
        improved = sum(1 for b, m in zip(memory_coherences, baseline_coherences) if m > b)
        help_percentage = 100 * improved / max(len(queries), 1)

        self.results["memory_weighting_impact"] = {
            "queries_tested": len(queries),
            "baseline_avg_coherence": round(baseline_coh, 3),
            "memory_avg_coherence": round(memory_coh, 3),
            "coherence_delta": round(coh_improve, 3),
            "memory_helps_percentage": round(help_percentage, 1),
            "baseline_avg_resolution": round(baseline_res, 3),
            "memory_avg_resolution": round(memory_res, 3),
            "resolution_delta": round(memory_res - baseline_res, 3),
        }

        return self.results["memory_weighting_impact"]

    def benchmark_semantic_tension(self, conflict_samples: List[Tuple[str, str, float]] = None) -> Dict:
        """
        BENCHMARK 3: Semantic Tension Quality

        Question: Are embedding-based tensions (ξ_semantic) better than heuristics?

        Hypothesis: Semantic embeddings capture *real* disagreement better than
        discrete opposition scores (0.4/0.7/1.0).

        Measurement:
        - For known conflict pairs (with ground truth tension)
        - Compute heuristic opposition_score
        - Compute semantic_tension (embeddings)
        - Measure correlation with ground truth

        Args:
            conflict_samples: List of (claim_a, claim_b, ground_truth_tension)

        Returns:
            {
                "samples_tested": int,
                "heuristic_correlation": float,
                "semantic_correlation": float,
                "semantic_advantage": float,
            }
        """
        if not self.forge or not self.forge.semantic_tension_engine:
            return {"error": "SemanticTensionEngine not available"}

        if not conflict_samples:
            return {"error": "No conflict samples provided"}

        heuristic_scores = []
        semantic_scores = []
        ground_truths = []

        for claim_a, claim_b, ground_truth in conflict_samples:
            try:
                # Get semantic tension
                semantic_tension = self.forge.semantic_tension_engine.compute_semantic_tension(claim_a, claim_b)
                semantic_scores.append(semantic_tension)

                # Get heuristic opposition (from conflict engine)
                _, heuristic_opposition = self.forge.conflict_engine._classify_conflict(claim_a, claim_b, 0.5)
                heuristic_scores.append(heuristic_opposition)

                ground_truths.append(ground_truth)

            except Exception as e:
                print(f"Error computing tensions: {e}")

        # Compute correlations with ground truth
        if len(heuristic_scores) > 1 and len(ground_truths) > 1:
            heuristic_corr = float(np.corrcoef(heuristic_scores, ground_truths)[0, 1])
            semantic_corr = float(np.corrcoef(semantic_scores, ground_truths)[0, 1])
            advantage = semantic_corr - heuristic_corr
        else:
            heuristic_corr = 0.0
            semantic_corr = 0.0
            advantage = 0.0

        self.results["semantic_tension_quality"] = {
            "samples_tested": len(conflict_samples),
            "heuristic_correlation": round(heuristic_corr, 3),
            "semantic_correlation": round(semantic_corr, 3),
            "semantic_advantage": round(advantage, 3),
            "semantic_better": semantic_corr > heuristic_corr,
        }

        return self.results["semantic_tension_quality"]

    def benchmark_specialization(self) -> Dict:
        """
        BENCHMARK 4: Specialization Tracking

        Question: Are adapters maintaining domain specialization?

        Hypothesis: Spec scores trend positive for expert adapters,
        negative for generalists. Convergence alerts trigger when
        adapter outputs become too similar.

        Returns:
            {
                "adapters_tracked": int,
                "specialist_adapters": list,
                "generalist_adapters": list,
                "convergence_risks": list,
                "health_status": str,
            }
        """
        if not self.forge or not self.forge.specialization:
            return {"error": "SpecializationTracker not available"}

        system_health = self.forge.specialization.get_system_health()
        health_by_adapter = system_health.get("health_by_adapter", {})

        specialists = [a for a, h in health_by_adapter.items() if h.get("recommendation") == "excellent_specialist"]
        generalists = [a for a, h in health_by_adapter.items() if h.get("recommendation") == "good_generalist"]
        convergence_alerts = system_health.get("convergence_alerts", [])

        self.results["specialization_metrics"] = {
            "adapters_tracked": len(health_by_adapter),
            "specialist_adapters": specialists,
            "generalist_adapters": generalists,
            "convergence_risk_count": len(convergence_alerts),
            "health_by_adapter": {a: h.get("recommendation") for a, h in health_by_adapter.items()},
        }

        return self.results["specialization_metrics"]

    def export_results(self, filepath: str = None) -> Dict:
        """
        Export all benchmark results to JSON.

        Args:
            filepath: Where to save results (optional)

        Returns:
            Complete results dict
        """
        if filepath:
            with open(filepath, "w") as f:
                json.dump(self.results, f, indent=2)
            print(f"Benchmark results saved to {filepath}")

        return self.results

    def summary(self) -> str:
        """
        Generate human-readable summary of all benchmarks.

        Returns:
            Formatted summary string
        """
        summary = "PHASE 6 BENCHMARK SUMMARY\n"
        summary += "=" * 60 + "\n"

        # Multi-round convergence
        mr = self.results.get("multi_round_convergence", {})
        if mr:
            summary += f"\n[1] MULTI-ROUND DEBATE CONVERGENCE\n"
            summary += f"    Queries tested: {mr.get('queries_tested', 0)}\n"
            summary += f"    Convergence rate: {mr.get('convergence_rate', 0):.3f}\n"
            summary += f"    Queries improved: {mr.get('improvement_percentage', 0)}%\n"

        # Memory weighting
        mw = self.results.get("memory_weighting_impact", {})
        if mw:
            summary += f"\n[2] MEMORY WEIGHTING IMPACT\n"
            summary += f"    Baseline coherence: {mw.get('baseline_avg_coherence', 0):.3f}\n"
            summary += f"    With memory: {mw.get('memory_avg_coherence', 0):.3f}\n"
            summary += f"    Delta: {mw.get('coherence_delta', 0):.3f}\n"
            summary += f"    Memory helps: {mw.get('memory_helps_percentage', 0)}% of queries\n"

        # Semantic tension
        st = self.results.get("semantic_tension_quality", {})
        if st:
            summary += f"\n[3] SEMANTIC TENSION QUALITY\n"
            summary += f"    Semantic correlation: {st.get('semantic_correlation', 0):.3f}\n"
            summary += f"    Heuristic correlation: {st.get('heuristic_correlation', 0):.3f}\n"
            summary += f"    Semantic advantage: {st.get('semantic_advantage', 0):.3f}\n"

        # Specialization
        sp = self.results.get("specialization_metrics", {})
        if sp:
            summary += f"\n[4] ADAPTER SPECIALIZATION\n"
            summary += f"    Adapters tracked: {sp.get('adapters_tracked', 0)}\n"
            summary += f"    Specialists: {len(sp.get('specialist_adapters', []))}\n"
            summary += f"    Convergence risks: {sp.get('convergence_risk_count', 0)}\n"

        summary += "\n" + "=" * 60 + "\n"
        return summary


__all__ = ["Phase6Benchmarks"]
