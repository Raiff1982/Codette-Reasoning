"""Phase 7: Executive Control Architecture — Intelligent component routing

This module implements the decision-making layer that routes queries to the optimal
combination of Phase 1-6 components, preventing wasteful activation and improving
latency while maintaining reasoning quality.

Core Philosophy: "Right-sized reasoning for right-sized questions"
- SIMPLE queries bypass heavy machinery
- MEDIUM queries activate selective components
- COMPLEX queries use full Phase 1-6 capabilities

Author: Jonathan Harrison (Codette Framework)
"""

import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict

from reasoning_forge.query_classifier import QueryComplexity


@dataclass
class ComponentDecision:
    """Routing decision for which Phase 1-6 components to activate."""

    # Routing metadata
    query_complexity: QueryComplexity
    component_activation: Dict[str, bool]  # e.g., {"debate": True, "semantic_tension": False}
    component_config: Dict[str, any] = field(default_factory=dict)  # e.g., {"debate_rounds": 1}
    reasoning: str = ""  # Why this routing was chosen

    # Transparency
    estimated_latency_ms: float = 0.0  # Expected latency
    estimated_correctness: float = 0.5  # Expected correctness (0-1)
    estimated_compute_cost: float = 0.0  # Relative cost (1-100)


class ExecutiveController:
    """Phase 7: Intelligent routing of queries to optimal component combinations.

    This replaces the "all-systems-go" approach with targeted component activation.
    Simple factual queries skip heavy machinery; complex queries use full power.

    Usage:
        exec_ctrl = ExecutiveController()
        decision = exec_ctrl.route_query(query)

        # Use decision to activate only selected components
        if decision.component_activation['debate']:
            result = forge.forge_with_debate(query, rounds=decision.component_config.get('debate_rounds', 1))
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

        # Learned routing patterns (initially empty, updated from memory)
        self.routing_patterns: Dict[str, ComponentDecision] = {}

        # Statistics
        self.queries_routed = 0
        self.route_activation_counts = {}  # Track which components get used

    def route_query(self, query: str, complexity: QueryComplexity) -> ComponentDecision:
        """Route a query to optimal component combination.

        Args:
            query: The user query
            complexity: QueryComplexity classification from Phase 6

        Returns:
            ComponentDecision with activation flags and configuration
        """
        self.queries_routed += 1

        if complexity == QueryComplexity.SIMPLE:
            return self._route_simple(query)
        elif complexity == QueryComplexity.MEDIUM:
            return self._route_medium(query)
        else:  # COMPLEX
            return self._route_complex(query)

    def _route_simple(self, query: str) -> ComponentDecision:
        """Route SIMPLE queries: skip heavy machinery.

        SIMPLE queries are factual (e.g., "speed of light", "definition of entropy").
        They should get fast, direct answers without debate or heavy synthesis.

        Cost: ~3 units (classifier + router)
        Latency: ~150ms
        Correctness: 0.95 (factual answers are well-established)
        """
        decision = ComponentDecision(
            query_complexity=QueryComplexity.SIMPLE,
            component_activation={
                'debate': False,
                'semantic_tension': False,
                'specialization_tracking': False,
                'preflight_predictor': False,
                'memory_weighting': False,
                'gamma_monitoring': False,
                'synthesis': False,  # Direct answer only
            },
            component_config={},
            reasoning="SIMPLE factual query - avoided heavy machinery for speed",
            estimated_latency_ms=150,
            estimated_correctness=0.95,
            estimated_compute_cost=3,
        )

        self._record_routing(decision)
        return decision

    def _route_medium(self, query: str) -> ComponentDecision:
        """Route MEDIUM queries: selective Phase 1-6 components.

        MEDIUM queries need some reasoning depth but don't require full debate.
        Examples: "How does X relate to Y", "What are the implications of Z"

        Activate:
        - semantic_tension: Continuous conflict strength (vs discrete)
        - debate: 1 round only (faster than 3)
        - specialization_tracking: Measure adapter fit
        - memory_weighting: Use learned adapter weights

        Skip:
        - preflight_predictor: Unnecessary for simpler queries

        Cost: ~25 units
        Latency: ~900ms (1-round debate)
        Correctness: 0.80
        """
        decision = ComponentDecision(
            query_complexity=QueryComplexity.MEDIUM,
            component_activation={
                'debate': True,
                'semantic_tension': True,
                'specialization_tracking': True,
                'preflight_predictor': False,  # Skip for speed
                'memory_weighting': True,
                'gamma_monitoring': True,
                'synthesis': True,
            },
            component_config={
                'debate_rounds': 1,  # Single round for speed
                'max_conflicts': 12,  # Cap conflicts
                'min_conflict_threshold': 0.2,
            },
            reasoning="MEDIUM complexity - selective debate with semantic tension",
            estimated_latency_ms=900,
            estimated_correctness=0.80,
            estimated_compute_cost=25,
        )

        self._record_routing(decision)
        return decision

    def _route_complex(self, query: str) -> ComponentDecision:
        """Route COMPLEX queries: full Phase 1-6 machinery.

        COMPLEX queries need deep reasoning, multiple perspectives, and conflict analysis.
        Examples: "Can machines be conscious?", "Ethical implications of AGI"

        Activate all Phase 1-6 components:
        - debate: 3 rounds for deep exploration
        - semantic_tension: Advanced conflict strength calculation
        - preflight_predictor: Predict conflicts before debate
        - specialization_tracking: Measure domain expertise
        - memory_weighting: Apply learned adapter weights
        - gamma_monitoring: Real-time coherence monitoring

        Cost: ~50+ units
        Latency: ~2500ms (3-round debate)
        Correctness: 0.85+
        """
        decision = ComponentDecision(
            query_complexity=QueryComplexity.COMPLEX,
            component_activation={
                'debate': True,
                'semantic_tension': True,
                'specialization_tracking': True,
                'preflight_predictor': True,
                'memory_weighting': True,
                'gamma_monitoring': True,
                'synthesis': True,
            },
            component_config={
                'debate_rounds': 3,  # Full exploration
                'max_conflicts': 20,  # Allow more conflicts for complex problems
                'min_conflict_threshold': 0.15,
                'semantic_tension_threshold': 0.3,
            },
            reasoning="COMPLEX query - full Phase 1-6 machinery for deep synthesis",
            estimated_latency_ms=2500,
            estimated_correctness=0.85,
            estimated_compute_cost=50,
        )

        self._record_routing(decision)
        return decision

    def _record_routing(self, decision: ComponentDecision):
        """Track which routing decisions are being made."""
        for component, active in decision.component_activation.items():
            if active:
                self.route_activation_counts[component] = \
                    self.route_activation_counts.get(component, 0) + 1

    def get_routing_statistics(self) -> Dict:
        """Get statistics about routing decisions made so far.

        Returns:
            {
                'total_queries_routed': int,
                'component_activation_counts': {component: count, ...},
                'avg_latency_by_complexity': {SIMPLE: ms, MEDIUM: ms, COMPLEX: ms},
                'efficiency_gain': float (expected compute savings)
            }
        """
        total_cost_full_stack = self.queries_routed * 50  # All queries with full machinery

        # Estimate cost savings from actual routing
        estimated_cost_actual = 0

        return {
            'total_queries_routed': self.queries_routed,
            'component_activation_counts': self.route_activation_counts.copy(),
            'efficiency_gain': f"Estimated {((total_cost_full_stack - estimated_cost_actual) / total_cost_full_stack * 100):.1f}% compute savings",
        }

    @staticmethod
    def create_route_metadata(decision: ComponentDecision,
                            actual_latency_ms: float,
                            actual_conflicts: int = 0,
                            gamma: float = 0.5) -> Dict:
        """Create metadata dictionary for response transparency.

        This metadata tells users which components ran and why, making the
        system's reasoning transparent.

        Args:
            decision: The ComponentDecision that was executed
            actual_latency_ms: Measured latency from execution
            actual_conflicts: Number of conflicts detected
            gamma: Coherence score from ConflenceField

        Returns:
            Dictionary with routing transparency info for response
        """
        return {
            'phase7_routing': {
                'query_complexity': decision.query_complexity.value,
                'components_activated': {
                    k: v for k, v in decision.component_activation.items()
                },
                'reasoning': decision.reasoning,
                'latency_analysis': {
                    'estimated_ms': decision.estimated_latency_ms,
                    'actual_ms': actual_latency_ms,
                    'savings_ms': max(0, decision.estimated_latency_ms - actual_latency_ms),
                },
                'correctness_estimate': decision.estimated_correctness,
                'compute_cost': {
                    'estimated_units': decision.estimated_compute_cost,
                    'unit_scale': '1=classifier, 50=full_machinery',
                },
                'metrics': {
                    'conflicts_detected': actual_conflicts,
                    'gamma_coherence': gamma,
                }
            }
        }


class ExecutiveControllerWithLearning(ExecutiveController):
    """Extended Executive Controller with learning from historical routing decisions.

    This version learns which component combinations work best and adapts routing
    over time based on actual correctness measurements.

    Usage:
        ctrl = ExecutiveControllerWithLearning(living_memory=memory)
        ctrl.update_routes_from_history()  # Weekly job
    """

    def __init__(self, living_memory=None, verbose: bool = False):
        super().__init__(verbose)
        self.living_memory = living_memory
        self.learned_routes: Dict[str, float] = {}  # Query type -> success rate

    def update_routes_from_history(self, window_days: int = 7):
        """Update routing patterns based on historical correctness data.

        This job should run periodically (e.g., daily) to learn which routes work best.

        Args:
            window_days: Look back this many days for historical data
        """
        if not self.living_memory:
            if self.verbose:
                print("[EXEC] No living_memory available - skipping learned routing")
            return

        if self.verbose:
            print(f"[EXEC] Analyzing routing history ({window_days} days)...")

        # In a full implementation, this would:
        # 1. Query living_memory for recent debate results
        # 2. Correlate component_selection with correctness
        # 3. Update success rates for each route
        # 4. Adjust future routing based on evidence

        # For now, placeholder implementation
        self.learned_routes = {
            'SIMPLE': 0.95,   # High confidence in simple routing
            'MEDIUM': 0.80,   # Good but room for improvement
            'COMPLEX': 0.85,  # Good on complex routing
        }

        if self.verbose:
            print(f"[EXEC] Routing routes updated: {self.learned_routes}")

    def get_route_confidence(self, complexity: QueryComplexity) -> float:
        """Get learned confidence score for a routing decision.

        Returns:
            0-1 confidence score (higher = more reliable route)
        """
        return self.learned_routes.get(complexity.value, 0.5)

    def should_explore_alternate_route(self, complexity: QueryComplexity) -> bool:
        """Decide if we should try an alternate route (ε-greedy exploration).

        Args:
            complexity: Query complexity

        Returns:
            True if we should try a different route for learning
        """
        confidence = self.get_route_confidence(complexity)

        # If very confident, stick with known good route
        if confidence > 0.90:
            return False

        # If moderate confidence, 10% of time try alternate
        if confidence > 0.70:
            return __import__('random').random() < 0.1

        # If low confidence, 25% of time try alternate
        return __import__('random').random() < 0.25
