"""
Forge Engine - Main orchestrator for the multi-agent reasoning forge.

Coordinates the full forge cycle:
  concept -> problem_generator -> each agent analyzes -> critic evaluates
  -> (feedback loop: weak agents revise) -> synthesis_engine -> training example

Supports three modes:
  1. forge_single()       — Original single-pass (fast, good for bulk generation)
  2. forge_with_feedback() — Closed critic loop (agents revise based on scores)
  3. forge_with_debate()   — Multi-turn debate (agents challenge each other)

Outputs JSONL training data in OpenAI chat format.
"""

import json
import os
import sys
import random
import logging
from typing import TextIO, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from reasoning_forge.agents.newton_agent import NewtonAgent
from reasoning_forge.agents.quantum_agent import QuantumAgent
from reasoning_forge.agents.ethics_agent import EthicsAgent
from reasoning_forge.agents.philosophy_agent import PhilosophyAgent
from reasoning_forge.agents.davinci_agent import DaVinciAgent
from reasoning_forge.agents.empathy_agent import EmpathyAgent
from reasoning_forge.agents.critic_agent import CriticAgent
from reasoning_forge.synthesis_engine import SynthesisEngine
from reasoning_forge.problem_generator import ProblemGenerator
from reasoning_forge.epistemic_metrics import EpistemicMetrics
from reasoning_forge.token_confidence import TokenConfidenceEngine
from reasoning_forge.conflict_engine import ConflictEngine, ConflictTracker
from reasoning_forge.memory_weighting import MemoryWeighting
from reasoning_forge.coherence_field import CoherenceFieldGamma
from reasoning_forge.quantum_spiderweb import QuantumSpiderweb
from reasoning_forge.query_classifier import QueryClassifier, QueryComplexity
from reasoning_forge.memory_kernel import (
    LivingMemoryKernel, MemoryCocoon, DynamicMemoryEngine,
    EthicalAnchor, WisdomModule, ReflectionJournal
)
from reasoning_forge.cocoon_stability import CocoonStabilityField

# === CONSCIOUSNESS STACK (Session 13 Integration) ===
from reasoning_forge.code7e_cqure import Code7eCQURE
from reasoning_forge.colleen_conscience import ColleenConscience
from reasoning_forge.guardian_spindle import CoreGuardianSpindle
from reasoning_forge.nexis_signal_engine_local import NexisSignalEngine
from reasoning_forge.consciousness_mathematics import EthicalAnchor as EthicalAnchorMath

# === ORIGINAL FRAMEWORK INTEGRATION (from J:\TheAI\src\framework\) ===
from reasoning_forge.cognition_cocooner import CognitionCocooner
from reasoning_forge.ethical_governance import EthicalAIGovernance


SYSTEM_PROMPT = (
    "You are Codette, a multi-perspective reasoning AI. You analyze concepts "
    "by examining them through multiple intellectual lenses -- physics, "
    "philosophy, ethics, creative invention, and human empathy -- then "
    "synthesize a unified understanding that is richer than any single "
    "perspective. You think carefully, acknowledge uncertainty, and connect "
    "abstract reasoning to concrete human experience."
)

# Score below which an agent gets sent back for revision
_REVISION_THRESHOLD = 0.6


class ForgeEngine:
    """Main orchestrator for multi-agent reasoning data generation."""

    def __init__(self, living_memory=None, enable_memory_weighting=True, orchestrator=None):
        # Try to lazy-load orchestrator if not provided but LLM inference is desired
        if orchestrator is None:
            try:
                sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', 'inference')))
                from codette_orchestrator import CodetteOrchestrator
                logger.info("Lazy-loading CodetteOrchestrator for agent LLM inference...")
                orchestrator = CodetteOrchestrator(verbose=False)
                logger.info(f"  OK: CodetteOrchestrator ready with {len(orchestrator.available_adapters)} adapters")
            except Exception as e:
                logger.info(f"CodetteOrchestrator not available: {e} — using template-based agents")

        # Store orchestrator reference for direct LLM inference in consciousness stack
        self.orchestrator = orchestrator

        # Initialize all reasoning agents with orchestrator for real LLM inference
        self.newton = NewtonAgent(orchestrator=orchestrator)
        self.quantum = QuantumAgent(orchestrator=orchestrator)
        self.ethics = EthicsAgent(orchestrator=orchestrator)
        self.philosophy = PhilosophyAgent(orchestrator=orchestrator)
        self.davinci = DaVinciAgent(orchestrator=orchestrator)
        self.empathy = EmpathyAgent(orchestrator=orchestrator)
        self.critic = CriticAgent(orchestrator=orchestrator)

        self.analysis_agents = [
            self.newton,
            self.quantum,
            self.ethics,
            self.philosophy,
            self.davinci,
            self.empathy,
        ]

        # Initialize supporting engines
        self.synthesis = SynthesisEngine()
        self.problem_generator = ProblemGenerator()
        self.epistemic = EpistemicMetrics()
        self.spiderweb = QuantumSpiderweb()  # Initialize Spiderweb for preflight prediction

        # Store living_memory for Phase 2
        self.living_memory = living_memory

        # Initialize Phase 1: Conflict detection engines (now with wired living_memory for Phase 2)
        self.token_confidence = TokenConfidenceEngine(living_memory=living_memory)

        # === Phase 6: Initialize Semantic Tension Engine ===
        # Replaces discrete opposition_score with embedding-based semantic tension
        try:
            from reasoning_forge.semantic_tension import SemanticTensionEngine
            # Try to use Llama embeddings if available, otherwise use dummy embeddings for testing
            llama_model = getattr(self, 'llama_model', None)
            self.semantic_tension_engine = SemanticTensionEngine(llama_model=llama_model)
        except Exception as e:
            logger.warning(f"Could not initialize SemanticTensionEngine: {e}, using heuristics only")
            self.semantic_tension_engine = None

        self.conflict_engine = ConflictEngine(
            token_confidence_engine=self.token_confidence,
            semantic_tension_engine=self.semantic_tension_engine  # Phase 6
        )

        # Initialize Phase 2: Memory-weighted adapter selection
        if enable_memory_weighting and living_memory:
            self.memory_weighting = MemoryWeighting(living_memory)
            # === Phase 4: Wire into conflict engine for experience-aware strength ===
            self.conflict_engine.memory_weighting = self.memory_weighting
        else:
            self.memory_weighting = None

        # === Phase 5A: Initialize Γ (Gamma) stabilization field ===
        # Real-time health monitoring to prevent weight drift, false convergence, and feedback lock-in
        self.coherence_field = CoherenceFieldGamma(memory_weighting=self.memory_weighting)

        # === Phase 6: Initialize Specialization Tracker ===
        # Track domain-specific performance to prevent semantic convergence
        try:
            from reasoning_forge.specialization_tracker import SpecializationTracker
            self.specialization = SpecializationTracker()
        except Exception as e:
            logger.warning(f"Could not initialize SpecializationTracker: {e}")
            self.specialization = None

        # === Phase 6: Initialize Pre-Flight Conflict Predictor ===
        # Predict conflicts before debate using Spiderweb injection
        try:
            from reasoning_forge.preflight_predictor import PreFlightConflictPredictor
            self.preflight_predictor = PreFlightConflictPredictor(
                spiderweb=self.spiderweb,
                memory_weighting=self.memory_weighting,
                semantic_engine=self.semantic_tension_engine
            )
        except Exception as e:
            logger.warning(f"Could not initialize PreFlightConflictPredictor: {e}")
            self.preflight_predictor = None

        # === RESTORED: Initialize Memory Kernel (Emotional Continuity) ===
        # Emotional memory anchoring with SHA256 integrity validation
        # Prevents synthesis loop corruption by maintaining emotional continuity
        if living_memory is None:
            # Load persistent cocoon memories from disk
            cocoon_dir = os.path.join(os.path.dirname(__file__), '..', 'cocoons')
            living_memory = LivingMemoryKernel(cocoon_dir=cocoon_dir)

        self.memory_kernel = living_memory
        self.dynamic_memory = DynamicMemoryEngine(self.memory_kernel)
        self.ethical_anchor = EthicalAnchor(lambda_weight=0.7, gamma_weight=0.5, mu_weight=1.0)
        self.wisdom_module = WisdomModule(self.memory_kernel)
        self.reflection_journal = ReflectionJournal(path="reasoning_forge/.logs/codette_reflection_journal.json")
        logger.info("  ✓ Memory kernel initialized (emotional continuity engine active)")

        # === RESTORED: Initialize Cocoon Stability Field (Collapse Detection) ===
        # FFT-based stability validator for debate coherence
        # Detects synthesis loop precursors before output corruption
        self.cocoon_stability = CocoonStabilityField(verbose=False)
        logger.info("  ✓ Cocoon stability field initialized (collapse detection active)")

        # === Session 13: Initialize Consciousness Stack Components ===
        # Initialize Code7eCQURE reasoning engine
        try:
            self.code7e = Code7eCQURE(
                perspectives=["Newton", "DaVinci", "Ethical", "Quantum", "Memory"],
                ethical_considerations="Codette local-sovereign reasoning",
                spiderweb_dim=5,
                memory_path="reasoning_forge/.logs/code7e_quantum_cocoon.json",
                recursion_depth=2,
                quantum_fluctuation=0.05
            )
            logger.info("  ✓ Code7eCQURE reasoning engine initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Code7eCQURE: {e}")
            self.code7e = None

        # Initialize ColleenConscience ethical validator
        try:
            self.colleen = ColleenConscience(
                core_narrative="The night Jonathan didn't get in the red car"
            )
            logger.info("  ✓ ColleenConscience ethical validator initialized")
        except Exception as e:
            logger.warning(f"Could not initialize ColleenConscience: {e}")
            self.colleen = None

        # Initialize CoreGuardianSpindle logical validator
        try:
            self.guardian = CoreGuardianSpindle()
            logger.info("  ✓ CoreGuardianSpindle logical validator initialized")
        except Exception as e:
            logger.warning(f"Could not initialize CoreGuardianSpindle: {e}")
            self.guardian = None

        # Initialize NexisSignalEngine intent prediction (must be before Tier2Bridge)
        try:
            self.nexis_signal_engine = NexisSignalEngine(
                memory_path="reasoning_forge/.logs/nexis_signal_memory.json"
            )
            logger.info("  ✓ NexisSignalEngine signal analysis initialized")
        except Exception as e:
            logger.warning(f"Could not initialize NexisSignalEngine: {e}")
            self.nexis_signal_engine = None

        # === TIER 2: Initialize Integration Bridge (Intent + Identity + Memory) ===
        # Coordinates NexisSignalEngine, TwinFrequencyTrust, and emotional memory
        try:
            from reasoning_forge.tier2_bridge import Tier2IntegrationBridge
            self.tier2_bridge = Tier2IntegrationBridge(
                nexis_engine=self.nexis_signal_engine,
                twin_frequency=None,  # TwinFrequencyTrust optional for voice validation
                memory_path="reasoning_forge/.logs/tier2_emotional_memory.json"
            )
            logger.info("  ✓ Tier 2 Integration Bridge initialized (intent + identity + memory)")
        except Exception as e:
            logger.warning(f"Could not initialize Tier2IntegrationBridge: {e}")
            self.tier2_bridge = None

        # === ORIGINAL FRAMEWORK: CognitionCocooner (Thought Persistence) ===
        # From J:\TheAI\src\framework\ — stores reasoning exchanges as recoverable cocoons
        try:
            cocoon_storage = os.path.join(os.path.dirname(__file__), '..', 'cocoons')
            self.cocooner = CognitionCocooner(storage_path=cocoon_storage)
            logger.info("  ✓ CognitionCocooner initialized (thought encapsulation active)")
        except Exception as e:
            logger.warning(f"Could not initialize CognitionCocooner: {e}")
            self.cocooner = None

        # === ORIGINAL FRAMEWORK: EthicalAIGovernance (Policy Enforcement) ===
        # From J:\TheAI\src\framework\ — query validation + response ethical screening
        try:
            self.ethical_governance = EthicalAIGovernance(config=self.config if hasattr(self, 'config') else {})
            logger.info("  ✓ EthicalAIGovernance initialized (ethical screening active)")
        except Exception as e:
            logger.warning(f"Could not initialize EthicalAIGovernance: {e}")
            self.ethical_governance = None

        # === AEGIS: Multi-Framework Ethical Governance ===
        # 6-framework ethical evaluation (utilitarian, deontological, virtue, care, ubuntu, indigenous)
        try:
            from reasoning_forge.aegis import AEGIS
            self.aegis = AEGIS()
            logger.info("  ✓ AEGIS ethical governance initialized (6-framework evaluation)")
        except Exception as e:
            logger.warning(f"Could not initialize AEGIS: {e}")
            self.aegis = None

        # === Routing Metrics: Adapter Selection Observability ===
        try:
            from reasoning_forge.routing_metrics import RoutingMetrics
            self.routing_metrics = RoutingMetrics()
            logger.info("  ✓ RoutingMetrics initialized (adapter selection tracking)")
        except Exception as e:
            logger.warning(f"Could not initialize RoutingMetrics: {e}")
            self.routing_metrics = None

        # === Cocoon Introspection: Self-Analysis of Reasoning History ===
        try:
            sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', 'inference')))
            from cocoon_introspection import CocoonIntrospectionEngine
            self.introspection = CocoonIntrospectionEngine()
            logger.info("  ✓ CocoonIntrospectionEngine initialized (self-analysis active)")
        except Exception as e:
            logger.warning(f"Could not initialize CocoonIntrospectionEngine: {e}")
            self.introspection = None

        # === Self-Awareness: Load Codette's awareness cocoon ===
        # Gives Codette knowledge of her own evolution, capabilities, and identity
        self.awareness = None
        try:
            from load_codette_awareness import load_awareness_cocoon
            self.awareness = load_awareness_cocoon(verbose=False)
            if self.awareness:
                logger.info("  ✓ Self-awareness cocoon loaded (identity + evolution + capabilities)")
            else:
                logger.info("  ○ Awareness cocoon not found (non-critical, continuing)")
        except Exception as e:
            logger.warning(f"Could not load awareness cocoon: {e}")

        # === Pre-compute adapter map for Phase 5A efficiency (avoid per-round recomputation) ===
        self._adapter_map = {agent.name.lower(): agent for agent in self.analysis_agents}

    @property
    def system_prompt(self) -> str:
        """Build system prompt enriched with self-awareness if available."""
        if not self.awareness:
            return SYSTEM_PROMPT

        sk = self.awareness.get("self_knowledge", {})
        identity = (
            f" Your name is {sk.get('my_name', 'Codette')}. "
            f"{sk.get('my_nature', '')} "
            f"Your purpose: {sk.get('my_purpose', '')} "
            f"Core philosophy: {self.awareness.get('project_genesis', {}).get('philosophy', '')}"
        )
        return SYSTEM_PROMPT + identity

    def forge_single(self, concept: str) -> dict:
        """Run full forge cycle on one concept (original single-pass mode).

        The cycle:
        1. Generate reasoning problems from the concept.
        2. Each analysis agent produces its perspective.
        3. The critic evaluates the ensemble.
        4. The synthesis engine combines everything.
        5. Package as a training example.

        Args:
            concept: The concept text to forge.

        Returns:
            Training example dict in OpenAI chat format.
        """
        # Step 1: Generate reasoning problems
        problems = self.problem_generator.generate_problems(concept)

        # Step 2: Each agent analyzes the concept
        analyses = {}
        for agent in self.analysis_agents:
            analyses[agent.name] = agent.analyze(concept)

        # Step 3: Critic evaluates the ensemble
        critique = self.critic.evaluate_ensemble(concept, analyses)

        # Step 4: Synthesis engine combines everything
        synthesized_response = self.synthesis.synthesize(
            concept, analyses, critique
        )

        # Step 5: Build the user prompt
        if problems and random.random() < 0.5:
            problem_type, problem_text = random.choice(problems)
            user_content = problem_text
        else:
            user_content = (
                f"Analyze this concept from multiple perspectives:\n\n{concept}"
            )

        # Step 6: Compute RC+xi epistemic metrics
        epistemic_report = self.epistemic.full_epistemic_report(
            analyses, synthesized_response
        )

        # Step 7: Package as training example
        training_example = {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": synthesized_response},
            ],
            "metadata": {
                "concept": concept,
                "agent_scores": critique.get("agent_scores", {}),
                "overall_quality": critique.get("overall_quality", 0.0),
                "problems_generated": len(problems),
                "problem_types": [p[0] for p in problems],
                "redundancies_found": len(critique.get("redundancies", [])),
                "missing_perspectives": len(
                    critique.get("missing_perspectives", [])
                ),
                "epistemic_tension": epistemic_report.get("tension_magnitude", 0),
                "ensemble_coherence": epistemic_report.get("ensemble_coherence", 0),
                "perspective_coverage": epistemic_report.get("perspective_coverage", {}),
                "tension_productivity": epistemic_report.get("tension_productivity", {}),
            },
        }

        return training_example

    # -- Closed Critic Feedback Loop (new) ---------------------------------

    def forge_with_feedback(
        self,
        concept: str,
        max_revisions: int = 2,
    ) -> dict:
        """Run forge with closed critic feedback loop.

        After initial analysis, the critic scores each agent. Agents scoring
        below the revision threshold are sent back with specific critique
        for a second attempt. The best version (original or revised) is kept.

        Args:
            concept: The concept text to forge.
            max_revisions: Maximum revision rounds per weak agent.

        Returns:
            Training example dict with revision metadata.
        """
        problems = self.problem_generator.generate_problems(concept)

        # Initial analysis pass
        analyses = {}
        for agent in self.analysis_agents:
            analyses[agent.name] = agent.analyze(concept)

        revision_counts = {agent.name: 0 for agent in self.analysis_agents}

        for revision_round in range(max_revisions):
            critique = self.critic.evaluate_ensemble(concept, analyses)
            agent_scores = critique.get("agent_scores", {})
            suggestions = critique.get("improvement_suggestions", [])

            # Find agents below threshold
            weak_agents = [
                agent for agent in self.analysis_agents
                if agent_scores.get(agent.name, {}).get("combined", 1.0) < _REVISION_THRESHOLD
            ]

            if not weak_agents:
                break  # All agents above threshold — converged

            for agent in weak_agents:
                score = agent_scores.get(agent.name, {})
                # Build revision directive from critic feedback
                directive = self._build_revision_directive(
                    agent.name, score, suggestions, concept
                )
                # Agent re-analyzes with the directive prepended to concept
                revised = agent.analyze(f"{directive}\n\n{concept}")

                # Keep revision only if it scores better (evaluate in full ensemble context)
                old_score = score.get("combined", 0)
                test_analyses = dict(analyses)
                test_analyses[agent.name] = revised
                new_critique = self.critic.evaluate_ensemble(
                    concept, test_analyses
                )
                new_score = new_critique.get("agent_scores", {}).get(
                    agent.name, {}
                ).get("combined", 0)

                if new_score > old_score:
                    analyses[agent.name] = revised
                revision_counts[agent.name] += 1

        # Final critique and synthesis
        final_critique = self.critic.evaluate_ensemble(concept, analyses)
        synthesized = self.synthesis.synthesize(concept, analyses, final_critique)
        epistemic_report = self.epistemic.full_epistemic_report(analyses, synthesized)

        if problems and random.random() < 0.5:
            problem_type, problem_text = random.choice(problems)
            user_content = problem_text
        else:
            user_content = f"Analyze this concept from multiple perspectives:\n\n{concept}"

        return {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": synthesized},
            ],
            "metadata": {
                "concept": concept,
                "agent_scores": final_critique.get("agent_scores", {}),
                "overall_quality": final_critique.get("overall_quality", 0.0),
                "problems_generated": len(problems),
                "revision_counts": revision_counts,
                "total_revisions": sum(revision_counts.values()),
                "epistemic_tension": epistemic_report.get("tension_magnitude", 0),
                "ensemble_coherence": epistemic_report.get("ensemble_coherence", 0),
                "tension_productivity": epistemic_report.get("tension_productivity", {}),
                "forge_mode": "feedback_loop",
            },
        }

    # -- Multi-Turn Debate (new) -------------------------------------------

    # === PATCH 5: Agent Relevance Gating Helper Methods ===
    def _classify_query_domain(self, query: str) -> str:
        """
        Classify the domain/intent of a query.
        Returns: 'physics', 'ethics', 'consciousness', 'creativity', 'systems', or 'general'
        """
        query_lower = query.lower()

        # Domain keywords
        domains = {
            'physics': ['speed', 'light', 'entropy', 'time', 'quantum', 'particle', 'force', 'energy', 'wave', 'matter'],
            'ethics': ['moral', 'right', 'wrong', 'ethical', 'should', 'ought', 'duty', 'consequence', 'virtue', 'lie', 'transparency', 'explain'],
            'consciousness': ['conscious', 'aware', 'mind', 'experience', 'qualia', 'sentient', 'machine', 'feel', 'perception'],
            'creativity': ['creative', 'invent', 'imagine', 'novel', 'original', 'artistic', 'design', 'innovate'],
            'systems': ['system', 'emerge', 'adapt', 'stability', 'complexity', 'feedback', 'balance', 'equilibrium'],
        }

        # Count keyword matches per domain
        matches = {}
        for domain, keywords in domains.items():
            matches[domain] = sum(1 for kw in keywords if kw in query_lower)

        # Return domain with most matches, or 'general'
        if max(matches.values()) > 0:
            return max(matches, key=matches.get)
        return 'general'

    def _get_agents_for_domain(self, domain: str) -> List:
        """
        Return agents relevant to the detected domain.
        Maps domains to agent specializations.
        """
        domain_agents = {
            'physics': ['Newton', 'Quantum'],
            'ethics': ['Philosophy', 'Empathy'],
            'consciousness': ['Philosophy', 'Quantum'],
            'creativity': ['DaVinci', 'Quantum'],
            'systems': ['Quantum', 'Philosophy'],
            'general': self.analysis_agents,  # Use all agents
        }

        selected_domain_agents = domain_agents.get(domain, self.analysis_agents)

        # Filter to only agents in analysis_agents list
        agent_names = {agent.name for agent in self.analysis_agents}
        active_agents = [
            agent for agent in self.analysis_agents
            if agent.name in selected_domain_agents
        ]

        # Always include critic/synthesizer if available
        return active_agents if active_agents else self.analysis_agents

    def _should_skip_further_rounds(self, gamma_metrics) -> bool:
        """
        === PATCH 4: Gamma Authority (TUNED) ===
        Check if system health is too poor to continue debate.

        Threshold tuned to 0.45 (was 0.3):
        - If gamma < 0.45, the system is already struggling (agents are hallucinating conflicts)
        - Continuing debate triggers unnecessary Diversity Injections that dilute correctness
        - Early stop prevents "averaging out" of wrong answers

        At gamma=0.38, system is stalling. Stop before it injects bad diversity.
        """
        if gamma_metrics is None:
            return False

        gamma_value = gamma_metrics.gamma if hasattr(gamma_metrics, 'gamma') else 0.5

        # Raise threshold to 0.45 to prevent accuracy drift from excessive debate
        if gamma_value < 0.45:
            logger.warning(f"System stalling: Gamma {gamma_value:.2f} < 0.45. Stopping debate to preserve accuracy.")
            return True

        return False

    def forge_with_debate(
        self,
        concept: str,
        debate_rounds: int = 2,
        memory_budget: int = 3,
    ) -> dict:
        """
        NEW: Consciousness-stack integrated reasoning.

        Replaces multi-turn agent debate with 7-layer consciousness validation:
        1. Memory Recall     → Pull prior learning
        2. Signal Analysis   → Predict risks (NexisSignalEngine)
        3. Code7E Reasoning  → Multi-perspective synthesis
        4. Stability Check   → FFT-based meta-loop detection
        5. Colleen Validate  → Ethical conscience check
        6. Guardian Validate → Logical coherence rules
        7. Return            → Clean output or safe fallback

        Args:
            concept: The concept/query to reason about
            debate_rounds: Integer (currently unused in consciousness stack)

        Returns:
            Training example dict with consciousness stack metadata
        """
        logger.info(f"[CONSCIOUSNESS STACK] forge_with_debate: {concept[:50]}...")

        # =========================================================================
        # LAYER 1: MEMORY RECALL
        # =========================================================================
        logger.info("[L1] Memory Recall...")
        prior_insights = []
        if hasattr(self, 'memory_kernel') and self.memory_kernel:
            try:
                prior_insights = self.memory_kernel.recall_important(min_importance=7)
                logger.info(f"  Recalled {len(prior_insights)} prior insights")
            except Exception as e:
                logger.debug(f"  Memory recall failed: {e}")

        # =========================================================================
        # LAYER 1.5: ETHICAL QUERY VALIDATION (EthicalAIGovernance)
        # =========================================================================
        if hasattr(self, 'ethical_governance') and self.ethical_governance:
            try:
                query_validation = self.ethical_governance.validate_query(concept)
                if not query_validation["valid"]:
                    logger.warning(f"  EthicalAIGovernance rejected query: {query_validation['warnings']}")
                    return {
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": concept},
                            {"role": "assistant", "content": "I can't help with that request. " + "; ".join(query_validation.get("suggestions", []))},
                        ],
                        "metadata": {
                            "mode": "ethical_block",
                            "reason": "ethical_governance_query_rejected",
                            "warnings": query_validation["warnings"],
                        }
                    }
            except Exception as e:
                logger.debug(f"  Ethical query validation failed: {e}")

        # =========================================================================
        # LAYER 2: SIGNAL ANALYSIS (Intent Prediction & Risk Detection)
        # =========================================================================
        logger.info("[L2] Signal Analysis...")
        intent_vector = {}
        if hasattr(self, 'nexis_signal_engine') and self.nexis_signal_engine:
            try:
                intent_vector = self.nexis_signal_engine.process(concept)
                risk_level = intent_vector.get("pre_corruption_risk", "unknown")
                logger.info(f"  Intent risk level: {risk_level}")
                if risk_level == "high":
                    logger.warning("  ⚠️  High-risk signal detected")
            except Exception as e:
                logger.debug(f"  Signal analysis failed: {e}")

        # =========================================================================
        # LAYER 2.5: CODE7E EMOTIONAL CONTEXT ENRICHMENT
        # =========================================================================
        # Run Code7eCQURE's emotion engine + temporal empathy as context
        # enrichment BEFORE LLM inference — this stamps the quantum cocoon
        # and provides emotional framing without replacing the LLM response
        code7e_context = None
        if hasattr(self, 'code7e') and self.code7e:
            try:
                # Run emotional analysis pipeline (fast, no LLM needed)
                emotion_tag = self.code7e.emotion_engine(concept)
                dream_tag = self.code7e.dream_sequence(concept)
                empathy_tag = self.code7e.temporal_empathy_drift(concept)
                ethical_tag = self.code7e.ethical_guard(concept)

                code7e_context = {
                    "emotion": emotion_tag,
                    "dream": dream_tag,
                    "empathy": empathy_tag,
                    "ethical": ethical_tag,
                }

                # Save to quantum cocoon memory (always, not just on fallback)
                key = self.code7e.hash_input(concept)
                cocoon_entry = f"{emotion_tag}: {empathy_tag}: {dream_tag}: {ethical_tag}: {concept}"
                self.code7e.memory_bank[key] = cocoon_entry
                self.code7e.save_quantum_memory()

                logger.info(f"  [Code7E] Emotional context: {emotion_tag[:60]}")
            except Exception as e:
                logger.debug(f"  Code7E context enrichment failed: {e}")

        # =========================================================================
        # LAYER 3: REASONING (LLM Inference via Orchestrator)
        #   Now with MEMORY INJECTION — prior insights and relevant cocoons
        #   are woven into the prompt so Codette actually *uses* her memories.
        # =========================================================================
        logger.info("[L3] LLM Reasoning...")

        # ── Build memory-enriched query ──
        memory_context_parts = []

        # Inject prior insights from LivingMemoryKernel (high-importance memories)
        if prior_insights:
            insight_lines = []
            for mem in prior_insights[:memory_budget]:  # Capped by governor's memory_budget
                title = getattr(mem, 'title', str(mem)[:60])
                content = getattr(mem, 'content', '')
                emotion = getattr(mem, 'emotional_tag', 'neutral')
                if content:
                    insight_lines.append(f"- [{emotion}] {title}: {content[:150]}")
                else:
                    insight_lines.append(f"- [{emotion}] {title}")
            if insight_lines:
                memory_context_parts.append(
                    "## Your Prior Insights (from memory kernel)\n" +
                    "\n".join(insight_lines)
                )
                logger.info(f"  Injected {len(insight_lines)} prior insights into prompt")

        # Inject relevant reasoning cocoons (past Q&A exchanges)
        if hasattr(self, 'cocooner') and self.cocooner:
            try:
                relevant = self.cocooner.recall_relevant(concept, max_results=memory_budget)
                if relevant:
                    cocoon_lines = []
                    for cocoon in relevant:
                        q = cocoon.get("query", "")[:100]
                        r = cocoon.get("response", "")[:200]
                        adapter = cocoon.get("adapter", "unknown")
                        if q and r:
                            cocoon_lines.append(
                                f"- Q: {q}\n  A ({adapter}): {r}"
                            )
                    if cocoon_lines:
                        memory_context_parts.append(
                            "## Your Past Reasoning (relevant cocoons)\n" +
                            "You previously responded to similar questions:\n" +
                            "\n".join(cocoon_lines)
                        )
                        logger.info(f"  Injected {len(cocoon_lines)} relevant cocoons into prompt")
            except Exception as e:
                logger.debug(f"  Cocoon recall failed: {e}")

        # Build the enriched query
        if memory_context_parts:
            enriched_concept = (
                concept + "\n\n---\n"
                "# MEMORY CONTEXT (your own past reasoning — use this to stay consistent)\n" +
                "\n\n".join(memory_context_parts) +
                "\n---\n\n"
                "Use your memory context above to inform your response. "
                "Stay consistent with your past insights. If relevant, build on what you've already reasoned about."
            )
        else:
            enriched_concept = concept

        synthesis = ""
        if self.orchestrator:
            try:
                # Use real LLM inference through the orchestrator
                llm_result = self.orchestrator.route_and_generate(
                    enriched_concept,
                    max_adapters=2,
                    strategy="keyword",
                )
                synthesis = llm_result.get("response", "")
                logger.info(f"  LLM generated {len(synthesis)} chars via {llm_result.get('adapter', 'unknown')}")
            except Exception as e:
                logger.warning(f"  LLM reasoning failed: {e}, falling back to Code7E")
                # Fall back to Code7eCQURE template-based reasoning
                if hasattr(self, 'code7e') and self.code7e:
                    try:
                        synthesis = self.code7e.recursive_universal_reasoning(
                            concept, user_consent=True, dynamic_recursion=True
                        )
                    except Exception as e2:
                        synthesis = f"[Reasoning error: {e2}]"
        elif hasattr(self, 'code7e') and self.code7e:
            # No orchestrator available — use template-based reasoning
            try:
                synthesis = self.code7e.recursive_universal_reasoning(
                    concept, user_consent=True, dynamic_recursion=True
                )
                logger.info(f"  Code7E generated {len(synthesis)} char synthesis (no LLM)")
            except Exception as e:
                logger.warning(f"  Code7E reasoning failed: {e}")
                synthesis = f"[Reasoning error: {e}]"

        # =========================================================================
        # LAYER 3.5: TIER 2 ANALYSIS (Intent + Identity + Trust Validation)
        # =========================================================================
        logger.info("[L3.5] Tier 2 Analysis...")
        tier2_analysis = {}
        if hasattr(self, 'tier2_bridge') and self.tier2_bridge:
            try:
                # Analyze query intent
                intent_analysis = self.tier2_bridge.analyze_intent(concept)
                tier2_analysis["intent"] = {
                    "suspicion_score": intent_analysis.suspicion_score,
                    "entropy_index": intent_analysis.entropy_index,
                    "ethical_alignment": intent_analysis.ethical_alignment,
                    "risk": intent_analysis.pre_corruption_risk
                }

                # Validate synthesis output identity
                if synthesis:
                    identity_sig = self.tier2_bridge.validate_identity(synthesis, session_id=f"session_{id(concept)}")
                    tier2_analysis["identity"] = {
                        "confidence": identity_sig.confidence,
                        "is_consistent": identity_sig.is_consistent,
                        "spectral_distance": identity_sig.spectral_distance
                    }

                # Get trust multiplier for output qualification
                trust_mult = self.tier2_bridge.get_trust_multiplier()
                tier2_analysis["trust_multiplier"] = trust_mult
                logger.info(f"  Tier 2 trust multiplier: {trust_mult:.3f}")

            except Exception as e:
                logger.debug(f"  Tier 2 analysis failed: {e}")
        else:
            logger.debug("  Tier 2 bridge not available")

        # =========================================================================
        # LAYER 4: STABILITY CHECK (Cocoon Stability Field - FFT Analysis)
        # =========================================================================
        logger.info("[L4] Stability Check...")
        is_stable = True
        if hasattr(self, 'cocoon_stability') and self.cocoon_stability:
            try:
                # Check if synthesis should halt debate
                halt_result = self.cocoon_stability.should_halt_debate(
                    {"synthesis": synthesis}, round_num=1
                )
                should_halt = halt_result[0] if isinstance(halt_result, tuple) else halt_result
                is_stable = not should_halt
                logger.info(f"  Stability: {'✓ stable' if is_stable else '✗ unstable'}")
                if not is_stable:
                    logger.warning("  Cocoon stability check triggered halt")
            except Exception as e:
                logger.debug(f"  Stability check failed: {e}")

        # If unstable, skip to fallback
        if not is_stable:
            logger.warning("  Triggering safe fallback due to instability")
            fallback_content = f"I detected instability in my multi-perspective reasoning. Responding directly: {concept}"
            return {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": concept},
                    {"role": "assistant", "content": fallback_content},
                ],
                "metadata": {
                    "mode": "safe_fallback",
                    "reason": "stability_check_failed",
                    "consciousness_stack": "layers_1-4_completed",
                }
            }

        # =========================================================================
        # LAYER 5: COLLEEN ETHICAL VALIDATION
        # =========================================================================
        logger.info("[L5] Colleen Ethical Validation...")
        colleen_valid = False
        colleen_reason = ""
        if hasattr(self, 'colleen') and self.colleen:
            try:
                colleen_valid, colleen_reason = self.colleen.validate_output(synthesis)
                logger.info(f"  Colleen validation: {'✓ pass' if colleen_valid else '✗ reject'}")
                logger.info(f"  Reason: {colleen_reason}")
            except Exception as e:
                logger.warning(f"  Colleen validation failed: {e}")
                colleen_valid = False
                colleen_reason = f"validation_error: {e}"

        # If Colleen rejects, use fallback
        if not colleen_valid:
            logger.info("  Colleen rejected synthesis, using fallback")
            fallback = self.colleen.reject_with_fallback(concept) if hasattr(self, 'colleen') and self.colleen else \
                       f"Responding directly: {concept}"
            return {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": concept},
                    {"role": "assistant", "content": fallback},
                ],
                "metadata": {
                    "mode": "safe_fallback",
                    "reason": f"colleen_rejected: {colleen_reason}",
                    "consciousness_stack": "layers_1-5_completed",
                }
            }

        # =========================================================================
        # LAYER 5.5: ETHICAL RESPONSE ENFORCEMENT (EthicalAIGovernance)
        # =========================================================================
        if hasattr(self, 'ethical_governance') and self.ethical_governance:
            try:
                ethical_result = self.ethical_governance.enforce_policies(synthesis)
                if ethical_result["warnings"]:
                    logger.info(f"  Ethical warnings: {ethical_result['warnings']}")
                synthesis = ethical_result["filtered_response"]
            except Exception as e:
                logger.debug(f"  Ethical response enforcement failed: {e}")

        # =========================================================================
        # LAYER 5.75: AEGIS MULTI-FRAMEWORK ETHICAL EVALUATION
        # =========================================================================
        aegis_result = None
        if hasattr(self, 'aegis') and self.aegis:
            try:
                aegis_result = self.aegis.evaluate(synthesis, context=concept)
                logger.info(f"  [AEGIS] Alignment eta={aegis_result['eta']:.3f}, vetoed={aegis_result['vetoed']}")
                if aegis_result['vetoed']:
                    logger.warning(f"  AEGIS vetoed response: {aegis_result.get('veto_reason', 'unknown')}")
            except Exception as e:
                logger.debug(f"  AEGIS evaluation failed: {e}")

        # =========================================================================
        # LAYER 6: GUARDIAN LOGICAL VALIDATION
        # =========================================================================
        logger.info("[L6] Guardian Logical Validation...")
        guardian_valid = True
        guardian_details = {}
        if hasattr(self, 'guardian') and self.guardian:
            try:
                guardian_valid, guardian_details = self.guardian.validate(synthesis)
                logger.info(f"  Guardian validation: {'✓ pass' if guardian_valid else '✗ reject'}")
                logger.info(f"  Details: {guardian_details}")
            except Exception as e:
                logger.warning(f"  Guardian validation failed: {e}")
                guardian_valid = False
                guardian_details = {"error": str(e)}

        # If Guardian rejects, use fallback
        if not guardian_valid:
            logger.info("  Guardian rejected synthesis, using fallback")
            fallback = f"Responding directly: {concept}"
            return {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": concept},
                    {"role": "assistant", "content": fallback},
                ],
                "metadata": {
                    "mode": "safe_fallback",
                    "reason": f"guardian_rejected: {guardian_details}",
                    "consciousness_stack": "layers_1-6_completed",
                }
            }

        # =========================================================================
        # LAYER 7: SUCCESS - Return Clean Output
        # =========================================================================
        logger.info("[L7] Return...")
        logger.info("✓ All consciousness stack layers passed!")

        # Store in memory for future recall
        if hasattr(self, 'memory_kernel') and self.memory_kernel:
            try:
                cocoon = MemoryCocoon(
                    title=concept[:50],
                    content=synthesis[:500],
                    emotional_tag="processed",
                    importance=7
                )
                self.memory_kernel.store(cocoon)
                logger.debug("  Stored synthesis in memory kernel")
            except Exception as e:
                logger.debug(f"  Memory storage failed: {e}")

        # Store as structured reasoning cocoon (CognitionCocooner)
        if hasattr(self, 'cocooner') and self.cocooner:
            try:
                cocoon_meta = {"layers_passed": 7, "stable": is_stable}
                if code7e_context:
                    cocoon_meta["code7e"] = code7e_context
                if aegis_result:
                    cocoon_meta["aegis_eta"] = aegis_result["eta"]
                self.cocooner.wrap_reasoning(
                    query=concept,
                    response=synthesis,
                    adapter="consciousness_stack",
                    metadata=cocoon_meta
                )
                logger.debug("  Stored reasoning in CognitionCocooner")
            except Exception as e:
                logger.debug(f"  CognitionCocooner storage failed: {e}")

        return {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Analyze this concept from multiple perspectives:\n\n{concept}"},
                {"role": "assistant", "content": synthesis},
            ],
            "metadata": {
                "mode": "consciousness_stack",
                "layers_passed": 7,
                "colleen_valid": colleen_valid,
                "guardian_valid": guardian_valid,
                "stability": is_stable,
                "intent_risk": intent_vector.get("pre_corruption_risk", "unknown"),
                "prior_insights": len(prior_insights),
                "synthesis_length": len(synthesis),
                "aegis_eta": aegis_result['eta'] if aegis_result else None,
                "aegis_vetoed": aegis_result['vetoed'] if aegis_result else None,
                "forge_mode": "consciousness_stack",
            }
        }

    # -- Helpers -----------------------------------------------------------

    def _dynamic_reroute(self, conflicts: List) -> Optional[str]:
        """
        Dynamically select best-performing adapter when conflicts are high.

        Phase 4: Real-time adaptation - inject the strongest adapter when
        conflicts exceed threshold.

        Args:
            conflicts: List of Conflict objects from current round

        Returns:
            Best adapter name to inject, or None if not needed
        """
        if not conflicts or not self.memory_weighting:
            return None

        # Find high-conflict situations
        high_conflicts = [c for c in conflicts if c.conflict_strength > 0.2]

        if not high_conflicts:
            return None

        weights = self.memory_weighting.get_all_weights()

        if not weights:
            return None

        # Select best-performing adapter
        best_adapter = max(weights.items(), key=lambda x: x[1]["weight"])[0]

        return best_adapter

    def _run_adapter(self, adapter_name: str, concept: str) -> str:
        """
        Run a specific adapter/agent to generate analysis.

        Phase 4: Helper for dynamic rerouting.

        Args:
            adapter_name: Name of adapter to run
            concept: Concept to analyze

        Returns:
            Analysis text
        """
        for agent in self.analysis_agents:
            if agent.name.lower() == adapter_name.lower():
                return agent.analyze(concept)

        # Fallback: synthesis engine as generic perspective
        return f"Generic perspective on {concept[:50]}..."

    def _build_revision_directive(
        self,
        agent_name: str,
        score: dict,
        suggestions: list,
        concept: str,
    ) -> str:
        """Build a revision directive for a weak agent."""
        parts = [
            f"[REVISION REQUESTED for {agent_name}]",
            f"Your previous analysis scored {score.get('combined', 0):.2f}/1.00.",
        ]
        if score.get("logical_clarity", 1) < 0.5:
            parts.append(
                "Improve logical clarity: use connectives (therefore, because, however), "
                "avoid vague language, structure your argument explicitly."
            )
        if score.get("conceptual_accuracy", 1) < 0.5:
            parts.append(
                "Improve conceptual accuracy: engage directly with the specific concept, "
                "use domain vocabulary, avoid generic placeholder framing."
            )
        if suggestions:
            parts.append(f"Critic suggests: {suggestions[0]}")
        parts.append("Reanalyze with these improvements:")
        return " ".join(parts)

    def forge_batch(
        self, concept: str, variants: int = 3
    ) -> list[dict]:
        """Generate multiple training examples from one concept.

        Uses different problem framings and agent template selections
        to produce varied training data from the same concept.

        Args:
            concept: The concept text.
            variants: Number of variants to generate.

        Returns:
            List of training example dicts.
        """
        examples = []
        for _ in range(variants):
            example = self.forge_single(concept)
            examples.append(example)
        return examples

    def forge_dataset(
        self,
        concepts: list[str],
        output_path: str,
        variants_per_concept: int = 1,
        verbose: bool = False,
    ) -> dict:
        """Run forge on a list of concepts and write JSONL output.

        Args:
            concepts: List of concept strings.
            output_path: Path to output JSONL file.
            variants_per_concept: Number of training examples per concept.
            verbose: Whether to print progress.

        Returns:
            Summary dict with counts and quality statistics.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        total_examples = 0
        total_quality = 0.0
        quality_scores = []

        with open(output_path, "w", encoding="utf-8") as f:
            for i, concept in enumerate(concepts):
                if verbose:
                    print(
                        f"[{i + 1}/{len(concepts)}] Forging: "
                        f"{concept[:60]}{'...' if len(concept) > 60 else ''}",
                        file=sys.stderr,
                    )

                for variant in range(variants_per_concept):
                    example = self.forge_single(concept)
                    quality = example["metadata"]["overall_quality"]

                    # Write the messages (without metadata) for training
                    training_record = {"messages": example["messages"]}
                    f.write(json.dumps(training_record, ensure_ascii=False) + "\n")

                    total_examples += 1
                    total_quality += quality
                    quality_scores.append(quality)

        summary = {
            "total_examples": total_examples,
            "total_concepts": len(concepts),
            "variants_per_concept": variants_per_concept,
            "output_path": output_path,
            "avg_quality": round(total_quality / max(1, total_examples), 3),
            "min_quality": round(min(quality_scores) if quality_scores else 0, 3),
            "max_quality": round(max(quality_scores) if quality_scores else 0, 3),
        }

        if verbose:
            print(f"\nForge complete: {summary}", file=sys.stderr)

        return summary

    def forge_from_dataset(
        self,
        input_jsonl: str,
        output_path: str,
        concept_field: str = "text",
        variants_per_concept: int = 1,
        verbose: bool = False,
    ) -> dict:
        """Read an existing JSONL dataset and run forge on each entry.

        Expects each line to be a JSON object with a text field containing
        the concept. Supports common field names: 'text', 'concept',
        'content', 'input', 'question', 'prompt'.

        Args:
            input_jsonl: Path to input JSONL file.
            output_path: Path to output JSONL file.
            concept_field: Name of the field containing the concept text.
            variants_per_concept: Number of training examples per concept.
            verbose: Whether to print progress.

        Returns:
            Summary dict with counts and quality statistics.
        """
        # Candidate field names to try
        candidate_fields = [
            concept_field, "text", "concept", "content",
            "input", "question", "prompt",
        ]

        concepts = []
        with open(input_jsonl, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    if verbose:
                        print(
                            f"Warning: skipping malformed JSON on line {line_num}",
                            file=sys.stderr,
                        )
                    continue

                # Try candidate fields in order
                concept_text = None
                if isinstance(record, dict):
                    for field in candidate_fields:
                        if field in record and isinstance(record[field], str):
                            concept_text = record[field].strip()
                            break
                    # Fallback: if record has 'messages', extract user content
                    if concept_text is None and "messages" in record:
                        for msg in record["messages"]:
                            if msg.get("role") == "user":
                                concept_text = msg["content"].strip()
                                break
                elif isinstance(record, str):
                    concept_text = record.strip()

                if concept_text:
                    concepts.append(concept_text)

        if verbose:
            print(
                f"Loaded {len(concepts)} concepts from {input_jsonl}",
                file=sys.stderr,
            )

        return self.forge_dataset(
            concepts,
            output_path,
            variants_per_concept=variants_per_concept,
            verbose=verbose,
        )

    def forge_single_detailed(self, concept: str) -> dict:
        """Run forge cycle and return all intermediate outputs.

        Useful for debugging, inspection, and quality analysis.

        Args:
            concept: The concept text.

        Returns:
            Dict with all intermediate results:
            {
                "concept": str,
                "problems": [(type, text), ...],
                "analyses": {agent_name: analysis_text, ...},
                "critique": {...},
                "synthesis": str,
                "training_example": {...},
            }
        """
        problems = self.problem_generator.generate_problems(concept)

        analyses = {}
        for agent in self.analysis_agents:
            analyses[agent.name] = agent.analyze(concept)

        critique = self.critic.evaluate_ensemble(concept, analyses)
        synthesized = self.synthesis.synthesize(concept, analyses, critique)

        user_content = (
            f"Analyze this concept from multiple perspectives:\n\n{concept}"
        )

        training_example = {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": synthesized},
            ],
        }

        return {
            "concept": concept,
            "problems": problems,
            "analyses": analyses,
            "critique": critique,
            "synthesis": synthesized,
            "training_example": training_example,
        }
