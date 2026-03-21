#!/usr/bin/env python3
"""Codette Phase 6 Inference Bridge — ForgeEngine integration for web server

This module provides a bridge between codette_server.py and ForgeEngine,
enabling Phase 6 capabilities (query complexity routing, semantic tension,
specialization tracking, pre-flight prediction) without breaking the web UI.

Usage:
    from codette_forge_bridge import CodetteForgeBridge

    bridge = CodetteForgeBridge(orchestrator=orch, use_phase6=True)
    result = bridge.generate(query, adapter=None, max_adapters=2)

The bridge falls back to lightweight orchestrator if Phase 6 disabled or heavy.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from reasoning_forge.forge_engine import ForgeEngine
    from reasoning_forge.query_classifier import QueryClassifier, QueryComplexity
    from reasoning_forge.executive_controller import ExecutiveController, ComponentDecision
    PHASE6_AVAILABLE = True
    PHASE7_AVAILABLE = True
except ImportError as e:
    PHASE6_AVAILABLE = False
    PHASE7_AVAILABLE = False
    print(f"[WARNING] ForgeEngine not available - Phase 6/7 disabled: {e}")


class CodetteForgeBridge:
    """Bridge between web server (lightweight) and ForgeEngine (Phase 6)."""

    def __init__(self, orchestrator, use_phase6: bool = True, use_phase7: bool = True, verbose: bool = False):
        """
        Args:
            orchestrator: CodetteOrchestrator instance for fallback
            use_phase6: Enable Phase 6 (requires ForgeEngine)
            use_phase7: Enable Phase 7 (Executive Controller routing)
            verbose: Log decisions
        """
        self.orchestrator = orchestrator
        self.verbose = verbose
        self.use_phase6 = use_phase6 and PHASE6_AVAILABLE
        self.use_phase7 = use_phase7 and PHASE7_AVAILABLE

        self.forge = None
        self.classifier = None
        self.executive_controller = None

        if self.use_phase6:
            try:
                self._init_phase6()
            except Exception as e:
                print(f"[WARNING] Phase 6 initialization failed: {e}")
                self.use_phase6 = False

        if self.use_phase7 and self.use_phase6:
            try:
                self.executive_controller = ExecutiveController(verbose=verbose)
                if self.verbose:
                    print("[PHASE7] Executive Controller initialized - intelligent routing enabled")
            except Exception as e:
                print(f"[WARNING] Phase 7 initialization failed: {e}")
                self.use_phase7 = False

    def _init_phase6(self):
        """Initialize ForgeEngine with Phase 6 components."""
        if self.verbose:
            print("[PHASE6] Initializing ForgeEngine...")

        self.forge = ForgeEngine()
        self.classifier = QueryClassifier()

        if self.verbose:
            print(f"[PHASE6] ForgeEngine ready with {len(self.forge.analysis_agents)} agents")

    def generate(self, query: str, adapter: Optional[str] = None,
                 max_adapters: int = 2) -> Dict:
        """Generate response with optional Phase 6 routing.

        Args:
            query: User query
            adapter: Force specific adapter (bypasses routing)
            max_adapters: Max adapters for multi-perspective

        Returns:
            {
                "response": str,
                "adapter": str or list,
                "phase6_used": bool,
                "complexity": str,  # if Phase 6
                "conflicts_prevented": int,  # if Phase 6
                "reasoning": str,
                ...rest from orchestrator...
            }
        """
        start_time = time.time()

        # If adapter forced or Phase 6 disabled, use orchestrator directly
        if adapter or not self.use_phase6:
            result = self.orchestrator.route_and_generate(
                query,
                max_adapters=max_adapters,
                strategy="keyword",
                force_adapter=adapter,
            )
            result["phase6_used"] = False
            return result

        # Try Phase 6 route first
        try:
            return self._generate_with_phase6(query, max_adapters)
        except Exception as e:
            if self.verbose:
                print(f"[PHASE6] Error: {e} - falling back to orchestrator")

            # Fallback to orchestrator
            result = self.orchestrator.route_and_generate(
                query,
                max_adapters=max_adapters,
                strategy="keyword",
                force_adapter=None,
            )
            result["phase6_used"] = False
            result["phase6_fallback_reason"] = str(e)
            return result

    def _generate_with_phase6(self, query: str, max_adapters: int) -> Dict:
        """Generate using ForgeEngine with Phase 6 capabilities and Phase 7 routing.

        Phase 7 Executive Controller routes the query to optimal component combination:
        - SIMPLE queries skip debate, go straight to orchestrator
        - MEDIUM queries use 1-round debate with selective components
        - COMPLEX queries use full 3-round debate with all Phase 1-6 components
        """
        start_time = time.time()

        # 1. Classify query complexity (Phase 6)
        complexity = self.classifier.classify(query)
        if self.verbose:
            print(f"[PHASE6] Query complexity: {complexity}")

        # 2. Route with Phase 7 Executive Controller
        route_decision = None
        if self.use_phase7 and self.executive_controller:
            route_decision = self.executive_controller.route_query(query, complexity)
            if self.verbose:
                print(f"[PHASE7] Route: {','.join([k for k, v in route_decision.component_activation.items() if v])}")
                print(f"[PHASE7] Reasoning: {route_decision.reasoning}")

        # 3. For SIMPLE queries, skip ForgeEngine and go direct to orchestrator
        if complexity == QueryComplexity.SIMPLE:
            if self.verbose:
                print("[PHASE7] SIMPLE query - using direct orchestrator routing")

            # Get direct answer from orchestrator
            result = self.orchestrator.route_and_generate(
                query,
                max_adapters=1,
                strategy="keyword",
                force_adapter=None,
            )

            elapsed = time.time() - start_time

            # Add Phase 7 routing metadata
            if route_decision:
                metadata = ExecutiveController.create_route_metadata(
                    route_decision,
                    actual_latency_ms=elapsed * 1000,
                    actual_conflicts=0,
                    gamma=0.95  # High confidence for direct answer
                )
                result.update(metadata)
                result["phase7_routing"]['reasoning'] = "SIMPLE factual query - orchestrator direct inference"

            result["phase6_used"] = True
            result["phase7_used"] = True
            return result

        # 4. For MEDIUM/COMPLEX queries, use ForgeEngine with appropriate depth

        # Domain classification
        domain = self._classify_domain(query)
        agent_selection = self.classifier.select_agents(complexity, domain)

        if self.verbose:
            print(f"[PHASE6] Domain: {domain}, Selected agents: {agent_selection}")

        # Run ForgeEngine with debate depth determined by complexity
        debate_rounds = 3 if complexity == QueryComplexity.COMPLEX else 1

        if self.verbose:
            print(f"[PHASE7] Running debate with {debate_rounds} round(s)")

        forge_result = self.forge.forge_with_debate(query, debate_rounds=debate_rounds)

        # 5. Extract synthesis and metrics
        synthesis = ""
        if "messages" in forge_result and len(forge_result["messages"]) >= 3:
            synthesis = forge_result["messages"][2].get("content", "")

        metadata = forge_result.get("metadata", {})
        conflicts = metadata.get("conflicts", [])

        # Estimate conflicts prevented based on routing
        if complexity == QueryComplexity.SIMPLE:
            base_conflicts_estimate = 71
        elif complexity == QueryComplexity.MEDIUM:
            base_conflicts_estimate = 23
        else:
            base_conflicts_estimate = 12

        conflicts_prevented = max(0, base_conflicts_estimate - len(conflicts))

        if self.verbose:
            print(f"[PHASE6] Conflicts: {len(conflicts)}, Prevented: {conflicts_prevented}")

        elapsed = time.time() - start_time

        result = {
            "response": synthesis,
            "adapter": "phase6_forge",
            "phase6_used": True,
            "phase7_used": self.use_phase7 and self.executive_controller is not None,
            "complexity": str(complexity),
            "domain": domain,
            "conflicts_detected": len(conflicts),
            "conflicts_prevented": conflicts_prevented,
            "gamma": metadata.get("gamma", 0.5),
            "time": elapsed,
            "tokens": metadata.get("total_tokens", 0),
            "reasoning": f"Phase 6: {complexity.name} complexity with {domain} domain routing",
        }

        # Add Phase 7 routing metadata for transparency
        if route_decision:
            route_metadata = ExecutiveController.create_route_metadata(
                route_decision,
                actual_latency_ms=elapsed * 1000,
                actual_conflicts=len(conflicts),
                gamma=metadata.get("gamma", 0.5)
            )
            result.update(route_metadata)

        return result

    def _classify_domain(self, query: str) -> str:
        """Classify query domain (physics, ethics, consciousness, creativity, systems)."""
        query_lower = query.lower()

        # Domain keywords
        domains = {
            "physics": ["force", "energy", "velocity", "gravity", "motion", "light", "speed",
                       "particle", "entropy", "time arrow", "quantum", "physics"],
            "ethics": ["moral", "right", "wrong", "should", "ethical", "justice", "fair",
                      "duty", "consequence", "utilitarian", "virtue", "ethics", "lie", "save"],
            "consciousness": ["conscious", "awareness", "qualia", "mind", "experience",
                            "subjective", "hard problem", "zombie", "consciousness"],
            "creativity": ["creative", "creative", "art", "invention", "novel", "design",
                          "imagination", "innovation", "beautiful"],
            "systems": ["system", "emerge", "feedback", "loop", "complex", "agent", "adapt",
                       "network", "evolution", "architecture", "free will"],
        }

        for domain, keywords in domains.items():
            if any(kw in query_lower for kw in keywords):
                return domain

        return "general"
