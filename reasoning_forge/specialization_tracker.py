"""
Phase 6: Specialization Tracker

Monitors adapter specialization and prevents semantic convergence.

Key metrics:
- specialization_score = domain_accuracy / usage_frequency
  (higher = expert in domain, not overtaxed)
- semantic_convergence = similarity between adapter outputs
  (alert if > 0.85, indicates monoculture within adapters)

Prevents:
- Weight drift (Phase 5 catches at system level)
- Semantic convergence (adapters giving similar answers, Phase 6 catches)
"""

from typing import List, Dict, Optional
import numpy as np
from datetime import datetime


class SpecializationTracker:
    """
    Tracks per-adapter per-domain performance to maintain specialization
    and detect when adapters are overlapping semantically.
    """

    # Domain keywords for query classification
    DOMAIN_KEYWORDS = {
        "physics": ["force", "momentum", "gravity", "quantum", "relativity", "acceleration", "Newton", "energy"],
        "ethics": ["should", "right", "wrong", "moral", "ethics", "justice", "fair", "values", "good"],
        "consciousness": ["aware", "conscious", "mind", "self", "experience", "perception", "qualia", "sentient"],
        "creativity": ["design", "create", "novel", "innovative", "imagine", "artistic", "original", "aesthetic"],
        "systems": ["system", "architecture", "scalable", "complex", "interdependent", "emergence", "network"],
        "philosophy": ["meaning", "existence", "truth", "knowledge", "being", "essence", "reasoning"],
    }

    def __init__(self):
        """Initialize tracking dictionaries."""
        self.domain_accuracy = {}      # {adapter: {domain: [coherence_scores]}}
        self.domain_usage = {}         # {adapter: {domain: count}}
        self.domain_last_used = {}     # {adapter: {domain: timestamp}}
        self.query_domains = {}        # {query_id: [domain_tags]}
        self.semantic_convergence_history = []  # Track convergence over time

    def classify_query_domain(self, query: str) -> List[str]:
        """
        Classify query by topic domain using keyword heuristics.

        Returns:
            List of domain tags, e.g., ["physics", "ethics"] for multi-domain queries.
            Returns ["general"] if no keywords match.
        """
        domains = []
        query_lower = query.lower()

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(k.lower() in query_lower for k in keywords):
                domains.append(domain)

        return domains if domains else ["general"]

    def record_adapter_performance(self, adapter: str, query: str, coherence: float):
        """
        Log adapter performance in domain(s) for a query.

        Args:
            adapter: Adapter name (e.g., "newton", "empathy")
            query: Query text
            coherence: Output coherence score [0, 1]
        """
        domains = self.classify_query_domain(query)

        for domain in domains:
            # Initialize if needed
            if adapter not in self.domain_accuracy:
                self.domain_accuracy[adapter] = {}
                self.domain_usage[adapter] = {}
                self.domain_last_used[adapter] = {}

            if domain not in self.domain_accuracy[adapter]:
                self.domain_accuracy[adapter][domain] = []
                self.domain_usage[adapter][domain] = 0
                self.domain_last_used[adapter][domain] = None

            # Record coherence and increment usage
            self.domain_accuracy[adapter][domain].append(coherence)
            self.domain_usage[adapter][domain] += 1
            self.domain_last_used[adapter][domain] = datetime.now()

    def compute_specialization(self, adapter: str) -> Dict[str, float]:
        """
        Compute specialization_score for each domain an adapter is used in.

        specialization_score[domain] = mean_accuracy[domain] / usage_frequency[domain]

        Returns:
            {domain: specialization_score} for all domains used
            Higher = more specialized (good performance, not overused)
        """
        if adapter not in self.domain_accuracy:
            return {}

        specialization = {}

        for domain in self.domain_accuracy[adapter]:
            accuracies = self.domain_accuracy[adapter][domain]
            usage = self.domain_usage[adapter][domain]

            mean_accuracy = float(np.mean(accuracies)) if accuracies else 0.5
            # Avoid division by zero, natural penalty for high usage
            specialization[domain] = mean_accuracy / max(usage, 1)

        return specialization

    def get_global_specialization(self) -> Dict[str, Dict[str, float]]:
        """
        Compute specialization scores for all adapters.

        Returns:
            {adapter: {domain: specialization_score}}
        """
        return {adapter: self.compute_specialization(adapter) for adapter in self.domain_accuracy.keys()}

    def detect_domain_expert(self, domain: str) -> Optional[str]:
        """
        Find best-performing adapter for a specific domain.

        Returns:
            Adapter name with highest specialization in domain, or None
        """
        specs = self.get_global_specialization()
        experts = {a: s.get(domain, 0) for a, s in specs.items() if domain in s}

        if not experts:
            return None

        return max(experts.keys(), key=lambda a: experts[a])

    def detect_semantic_convergence(
        self, adapter_outputs: Dict[str, str], semantic_engine=None, threshold: float = 0.85
    ) -> Dict:
        """
        Measure overlap between adapter outputs on same query.

        Alerts if any pair similarity > threshold (converging).

        Args:
            adapter_outputs: {adapter_name: output_text}
            semantic_engine: SemanticTensionEngine instance (optional, for real embeddings)
            threshold: Similarity threshold for convergence alert

        Returns:
            {
                "convergent_pairs": [{pair, similarity, risk}],
                "max_similarity": float,
                "has_convergence": bool,
            }
        """
        if len(adapter_outputs) < 2:
            return {"convergent_pairs": [], "max_similarity": 0.0, "has_convergence": False}

        convergent_pairs = []
        max_similarity = 0.0

        adapters = list(adapter_outputs.keys())

        for i, a1 in enumerate(adapters):
            for a2 in adapters[i + 1 :]:
                output_a = adapter_outputs[a1]
                output_b = adapter_outputs[a2]

                # Compute similarity (use semantic engine if available)
                if semantic_engine:
                    try:
                        tension = semantic_engine.compute_semantic_tension(output_a, output_b)
                        similarity = 1.0 - tension
                    except Exception:
                        # Fallback to text overlap
                        similarity = self._text_similarity(output_a, output_b)
                else:
                    # Simple fallback: token overlap
                    similarity = self._text_similarity(output_a, output_b)

                max_similarity = max(max_similarity, similarity)

                if similarity > threshold:
                    convergent_pairs.append({
                        "adapter_a": a1,
                        "adapter_b": a2,
                        "similarity": round(similarity, 3),
                        "convergence_risk": "HIGH" if similarity > 0.92 else "MEDIUM",
                    })

        has_convergence = len(convergent_pairs) > 0

        record = {
            "timestamp": datetime.now().isoformat(),
            "convergent_pairs": convergent_pairs,
            "max_similarity": round(max_similarity, 3),
            "has_convergence": has_convergence,
            "num_adapters": len(adapter_outputs),
        }

        self.semantic_convergence_history.append(record)

        return record

    def _text_similarity(self, text_a: str, text_b: str) -> float:
        """
        Simple text similarity fallback: Jaccard similarity on tokens.

        Args:
            text_a, text_b: Text strings

        Returns:
            Similarity in [0, 1]
        """
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)

        return intersection / max(union, 1)

    def get_adapter_health(self, adapter: str) -> Dict:
        """
        Get overall health score for an adapter.

        Returns:
            {
                "adapter": adapter,
                "num_domains": int,
                "avg_accuracy": float,
                "total_usage": int,
                "specialization_avg": float,
                "recommendation": str
            }
        """
        if adapter not in self.domain_accuracy:
            return {"error": f"No data for adapter {adapter}"}

        accuracies_all = []
        usage_total = 0

        for domain in self.domain_accuracy[adapter]:
            accuracies_all.extend(self.domain_accuracy[adapter][domain])
            usage_total += self.domain_usage[adapter][domain]

        avg_accuracy = float(np.mean(accuracies_all)) if accuracies_all else 0.5
        specs = self.compute_specialization(adapter)
        spec_avg = float(np.mean(list(specs.values()))) if specs else 0.5

        # Generate recommendation
        if spec_avg > 0.1 and avg_accuracy > 0.75:
            recommendation = "excellent_specialist"
        elif spec_avg > 0.05 and avg_accuracy > 0.6:
            recommendation = "good_generalist"
        elif usage_total > 20 and avg_accuracy < 0.5:
            recommendation = "overused_poorly"
        else:
            recommendation = "maintain_current"

        return {
            "adapter": adapter,
            "num_domains": len(self.domain_accuracy[adapter]),
            "avg_accuracy": round(avg_accuracy, 3),
            "total_usage": usage_total,
            "specialization_avg": round(spec_avg, 3),
            "recommendation": recommendation,
            "domain_specializations": {d: round(s, 3) for d, s in specs.items()},
        }

    def get_system_health(self) -> Dict:
        """
        Get overall system specialization health.

        Returns:
            Flags convergence risks, identifies experts, recommends actions.
        """
        health_by_adapter = {adapter: self.get_adapter_health(adapter) for adapter in self.domain_accuracy.keys()}

        overused = [a for a, h in health_by_adapter.items() if h.get("recommendation") == "overused_poorly"]
        excellent = [a for a, h in health_by_adapter.items() if h.get("recommendation") == "excellent_specialist"]
        experts = {domain: self.detect_domain_expert(domain) for domain in self.DOMAIN_KEYWORDS.keys()}

        return {
            "timestamp": datetime.now().isoformat(),
            "total_adapters": len(health_by_adapter),
            "health_by_adapter": health_by_adapter,
            "overused_adapters": overused,
            "specialist_adapters": excellent,
            "domain_experts": experts,
            "convergence_alerts": self.semantic_convergence_history[-5:] if self.semantic_convergence_history else [],
        }

    def export_summary(self) -> Dict:
        """Export complete specialization data for analysis."""
        return {
            "timestamp": datetime.now().isoformat(),
            "global_specialization": self.get_global_specialization(),
            "system_health": self.get_system_health(),
            "convergence_history": self.semantic_convergence_history,
        }


__all__ = ["SpecializationTracker"]
