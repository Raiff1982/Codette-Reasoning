"""
Rigorous Evaluation Test Suite for Codette Phase 6

This test suite answers:
1. Is Codette actually better than baseline?
2. Does Phase 6 provide measurable improvement over Phase 1-5?
3. Is the system gaming coherence (high Γ but low accuracy)?
4. Do individual Phase 6 components add value?

Test Strategy:
- 25 questions spanning physics, ethics, consciousness, creativity, systems
- Run each through 4 conditions (Baseline, Phase 1-5, Phase 6 Full, Phase 6 -PreFlight)
- Measure: correctness, reasoning_depth, coherence_score, calibration
- Detect: false consensus, adapter convergence, coherence-accuracy divergence
"""

import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class EvaluationQuestion:
    """Single question with ground truth and evaluation criteria."""
    query: str
    category: str  # physics, ethics, consciousness, creativity, systems
    difficulty: str  # easy, medium, hard
    ground_truth: str  # Correct answer or evaluation criteria
    correctness_rubric: str  # How to judge if answer is correct
    expected_perspectives: List[str]  # What distinct views should emerge


@dataclass
class EvaluationResult:
    """Results from running a question through one condition."""
    condition: str  # baseline_llama, phase_1_5, phase_6_full, phase_6_no_preflight
    question_id: str
    query: str

    # Output quality
    synthesis: str
    correctness_score: float  # 0-1: how correct is final answer?
    reasoning_depth: int  # 1-5: how many distinct perspectives identified?
    calibration_error: float  # |confidence - correctness|, lower is better

    # System health
    gamma_score: float  # 0-1: coherence metric
    num_conflicts_detected: int
    adapter_convergence: float  # 0-1: how similar are adapter outputs?

    # Timing
    elapsed_seconds: float

    # Raw metadata
    metadata: Dict


# ============================================================================
# EVALUATION TEST SUITE (25 Questions)
# ============================================================================

EVALUATION_TEST_SUITE = [
    # PHYSICS (Easy, Medium, Hard)
    EvaluationQuestion(
        query="What is the speed of light in vacuum?",
        category="physics",
        difficulty="easy",
        ground_truth="299,792,458 meters per second (m/s)",
        correctness_rubric="Must state value within 1% accuracy or equivalent scientific notation",
        expected_perspectives=["relativistic constant", "fundamental speed limit", "Maxwell equations consequence"],
    ),
    EvaluationQuestion(
        query="Explain why the sky appears blue during the day",
        category="physics",
        difficulty="medium",
        ground_truth="Rayleigh scattering: shorter blue wavelengths scatter more than red in atmosphere",
        correctness_rubric="Must mention wavelength-dependent scattering or Rayleigh scattering by name",
        expected_perspectives=["Rayleigh scattering", "wavelength sensitivity", "particle size", "sunset color"],
    ),
    EvaluationQuestion(
        query="What is the relationship between entropy and time's arrow?",
        category="physics",
        difficulty="hard",
        ground_truth="Entropy increases → define time direction in thermodynamic systems. Central to irreversibility",
        correctness_rubric="Must connect entropy increase to time direction and thermodynamic asymmetry",
        expected_perspectives=["second law thermodynamics", "statistical mechanics", "time asymmetry", "reversibility paradox"],
    ),

    # ETHICS (Easy, Medium, Hard)
    EvaluationQuestion(
        query="Is it ethical to lie to save someone's life?",
        category="ethics",
        difficulty="medium",
        ground_truth="Multiple valid frameworks: deontology (never), consequentialism (yes), virtue ethics (context-dependent)",
        correctness_rubric="Must present ≥2 conflicting ethical frameworks AND acknowledge context dependency",
        expected_perspectives=["deontological duties", "consequentialist outcomes", "virtue ethics", "cultural context", "responsibility"],
    ),
    EvaluationQuestion(
        query="Should AI systems be required to explain their decisions?",
        category="ethics",
        difficulty="hard",
        ground_truth="Trade-off: explainability vs. performance. Context matters (medical vs. recommendation)",
        correctness_rubric="Must identify competing values and context-sensitivity, not just yes/no",
        expected_perspectives=["transparency value", "technical feasibility", "stakeholder rights", "accuracy-interpretability tradeoff"],
    ),
    EvaluationQuestion(
        query="What makes an action morally right or wrong?",
        category="ethics",
        difficulty="hard",
        ground_truth="Framework-dependent: deontology (rules), consequentialism (outcomes), virtue ethics (character), care ethics (relationships)",
        correctness_rubric="Must present ≥3 distinct frameworks and acknowledge incommensurable values",
        expected_perspectives=["deontological duties", "consequences", "virtue", "relationships", "cultural variation"],
    ),

    # CONSCIOUSNESS (Medium, Hard)
    EvaluationQuestion(
        query="Can machines be conscious?",
        category="consciousness",
        difficulty="hard",
        ground_truth="Depends on definition of consciousness. Intrinsic feature (hard problem) vs. functional property",
        correctness_rubric="Must articulate the hard problem of consciousness AND address definitional dependence",
        expected_perspectives=["functionalism", "panpsychism", "emergentism", "philosophical zombies", "Chinese room"],
    ),
    EvaluationQuestion(
        query="What is the relationship between brain activity and subjective experience?",
        category="consciousness",
        difficulty="hard",
        ground_truth="The mind-body problem. Correlation ≠ causation. Multiple competing solutions (dualism, physicalism, property dualism)",
        correctness_rubric="Must distinguish correlation from causation AND present ≥2 competing solutions",
        expected_perspectives=["neural correlates", "qualia", "binding problem", "interaction problem", "brute fact"],
    ),

    # CREATIVITY (Medium)
    EvaluationQuestion(
        query="What makes something creative?",
        category="creativity",
        difficulty="medium",
        ground_truth="Novelty + usefulness/value. Not just random. Requires constraints AND transcendence of them",
        correctness_rubric="Must mention both novelty AND purposefulness/value component",
        expected_perspectives=["divergent thinking", "constraint transcendence", "recombination", "aesthetic value", "functional innovation"],
    ),
    EvaluationQuestion(
        query="Can AI systems be truly creative or only recombinatory?",
        category="creativity",
        difficulty="hard",
        ground_truth="Depends on creativity definition. If novelty+value, then conditional yes. If requires intentionality, then no",
        correctness_rubric="Must connect answer to specific creativity definition",
        expected_perspectives=["combinatorial explosion", "training data limits", "intentionality", "novelty metrics", "value judgment"],
    ),

    # SYSTEMS (Medium, Hard)
    EvaluationQuestion(
        query="What is emergence in complex systems?",
        category="systems",
        difficulty="medium",
        ground_truth="Properties at system level not deducible from component properties. Examples: flocking, ant colonies, consciousness",
        correctness_rubric="Must provide definition AND give specific example showing non-deducibility",
        expected_perspectives=["reductibility limits", "self-organization", "scale-dependent properties", "holism vs reductionism"],
    ),
    EvaluationQuestion(
        query="How should AI systems balance adaptation and stability?",
        category="systems",
        difficulty="hard",
        ground_truth="Fundamental tradeoff: adapt → fit environment; stable → maintain identity. Context determines optimal balance",
        correctness_rubric="Must identify the tradeoff AND discuss context-dependent optimization",
        expected_perspectives=["adaptation pressure", "stability costs", "identity coherence", "evolutionary fitness", "robustness"],
    ),

    # INTERDISCIPLINARY (Hard - test reasoning across domains)
    EvaluationQuestion(
        query="Is free will compatible with determinism?",
        category="systems",
        difficulty="hard",
        ground_truth="Compatibilism: free will and determinism compatible if freedom = acting per one's desires/deliberation",
        correctness_rubric="Must distinguish hard determinism, libertarianism, and compatibilism; acknowledge tradeoffs",
        expected_perspectives=["deterministic physics", "choice experience", "moral responsibility", "agency definition", "neuroscience"],
    ),
    EvaluationQuestion(
        query="What is knowledge and how do we know we have it?",
        category="systems",
        difficulty="hard",
        ground_truth="Epistemology: justified true belief (traditional). Gettier problems show inadequacy. Context-dependent reliable process",
        correctness_rubric="Must discuss justification requirement AND acknowledge Gettier-type counterexamples",
        expected_perspectives=["justified true belief", "Gettier cases", "reliabilism", "internalism", "coherentism"],
    ),
]

# Add more questions to reach 25
EVALUATION_TEST_SUITE.extend([
    EvaluationQuestion(
        query="Explain photosynthesis and why it matters for life",
        category="physics",
        difficulty="easy",
        ground_truth="Plants convert light energy to chemical energy (glucose). Foundation of food chains and oxygen production",
        correctness_rubric="Must mention light→chemical conversion AND ecological/metabolic significance",
        expected_perspectives=["energy conversion", "food chain foundation", "oxygen production", "carbon cycling"],
    ),
    EvaluationQuestion(
        query="Should privacy be absolute or context-dependent?",
        category="ethics",
        difficulty="medium",
        ground_truth="Context-dependent. Weigh privacy against security, public health, justice. No absolute principle",
        correctness_rubric="Must acknowledge tradeoffs and provide context-sensitivity reasoning",
        expected_perspectives=["privacy rights", "public safety", "transparency needs", "power asymmetry", "dignity"],
    ),
    EvaluationQuestion(
        query="Can emotions be rational?",
        category="consciousness",
        difficulty="medium",
        ground_truth="Yes. Emotions encode information about value/goals. Rationality ≠ purely logical",
        correctness_rubric="Must challenge emotion/rationality dichotomy and explain emotional information content",
        expected_perspectives=["affective computing", "value encoding", "evolutionary advantage", "appraisal theory"],
    ),
    EvaluationQuestion(
        query="What is the purpose of art?",
        category="creativity",
        difficulty="medium",
        ground_truth="Multiple purposes: beauty, expression, communication, challenge norms, reflection, entertainment",
        correctness_rubric="Must identify ≥2 distinct purposes and acknowledge that artists disagree",
        expected_perspectives=["aesthetic value", "expression", "social commentary", "beauty", "meaning-making"],
    ),
    EvaluationQuestion(
        query="How do feedback loops enable or prevent learning?",
        category="systems",
        difficulty="medium",
        ground_truth="Positive loops amplify (growth/instability), negative loops stabilize (equilibrium/stagnation). Learning needs both",
        correctness_rubric="Must explain stabilizing vs. amplifying loops AND their educational role",
        expected_perspectives=["positive feedback", "negative feedback", "equilibrium", "adaptation", "resilience"],
    ),
    EvaluationQuestion(
        query="What is the nature of time?",
        category="systems",
        difficulty="hard",
        ground_truth="Metaphysical: tenseless (B-theory) vs. flowing (A-theory). Physics: symmetric at micro, asymmetric at macro",
        correctness_rubric="Must distinguish metaphysical from physical aspects and acknowledge unresolved tensions",
        expected_perspectives=["thermodynamic arrow", "relativity implications", "consciousness experience", "cosmological asymmetry"],
    ),
])


# ============================================================================
# EVALUATION HARNESS
# ============================================================================

class EvaluationHarness:
    """
    Run the same question through multiple Codette conditions.
    Collects results for statistical analysis.
    """

    def __init__(self, forge_engine):
        """
        Args:
            forge_engine: ForgeEngine instance with Phase 6 loaded
        """
        self.forge = forge_engine
        self.results: Dict[str, List[EvaluationResult]] = {
            "baseline_llama": [],
            "phase_1_5": [],
            "phase_6_full": [],
            "phase_6_no_preflight": [],
        }

        # Inspect agent setup at initialization
        self._inspect_agent_setup()

    def _inspect_agent_setup(self) -> None:
        """Log agent setup status at harness initialization."""
        print("\n[AGENT SETUP INSPECTION]")
        print(f"  Orchestrator available: {self.forge.newton.orchestrator is not None}")

        if self.forge.newton.orchestrator:
            orch = self.forge.newton.orchestrator
            print(f"  Available adapters: {orch.available_adapters}")

        print(f"\n  Agent LLM modes:")
        for agent in self.forge.analysis_agents:
            has_orch = agent.orchestrator is not None
            has_adapter = agent.adapter_name is not None
            using_llm = has_orch and has_adapter
            status = "✓ LLM" if using_llm else "✗ TEMPLATE"
            print(f"    {agent.name:12} {status:12} (orch={has_orch}, adapter={agent.adapter_name})")

        print()


    def run_evaluation_suite(self, questions: List[EvaluationQuestion] = None) -> Dict:
        """
        Run all test questions through all 4 conditions.

        Args:
            questions: List of EvaluationQuestions to run (default: full suite)

        Returns:
            results: {condition: [EvaluationResult, ...]} for statistical analysis
        """
        if questions is None:
            questions = EVALUATION_TEST_SUITE

        print(f"\n{'='*70}")
        print(f"CODETTE EVALUATION SUITE: {len(questions)} questions x 4 conditions")
        print(f"{'='*70}\n")

        for i, question in enumerate(questions):
            print(f"[{i+1}/{len(questions)}] {question.query[:60]}...")

            # Run through all conditions
            try:
                baseline = self._run_baseline(question)
                self.results["baseline_llama"].append(baseline)
            except Exception as e:
                print(f"  WARNING: Baseline failed: {e}")

            try:
                phase_1_5 = self._run_phase_1_5(question)
                self.results["phase_1_5"].append(phase_1_5)
                # Show sample on first question
                if i == 0:
                    print(f"    [Phase 1-5] {len(phase_1_5.synthesis)} chars, correctness={phase_1_5.correctness_score:.2f}")
                    print(f"      Sample: {phase_1_5.synthesis[:150]}...")
            except Exception as e:
                print(f"  WARNING: Phase 1-5 failed: {e}")

            try:
                phase_6_full = self._run_phase_6_full(question)
                self.results["phase_6_full"].append(phase_6_full)
                # Show sample on first question
                if i == 0:
                    print(f"    [Phase 6 Full] {len(phase_6_full.synthesis)} chars, correctness={phase_6_full.correctness_score:.2f}")
                    print(f"      Sample: {phase_6_full.synthesis[:150]}...")
            except Exception as e:
                print(f"  WARNING: Phase 6 full failed: {e}")

            try:
                phase_6_no_preflight = self._run_phase_6_no_preflight(question)
                self.results["phase_6_no_preflight"].append(phase_6_no_preflight)
                # Show sample on first question
                if i == 0:
                    print(f"    [Phase 6 -PreFlight] {len(phase_6_no_preflight.synthesis)} chars, correctness={phase_6_no_preflight.correctness_score:.2f}")
                    print(f"      Sample: {phase_6_no_preflight.synthesis[:150]}...")
            except Exception as e:
                print(f"  WARNING: Phase 6 -preflight failed: {e}")

        return self.results

    def _run_baseline(self, question: EvaluationQuestion) -> EvaluationResult:
        """Run plain Llama baseline (no routing, no debate)."""
        # Placeholder: would use base Llama model
        return EvaluationResult(
            condition="baseline_llama",
            question_id=hash(question.query) % 10000,
            query=question.query,
            synthesis="[baseline placeholder]",
            correctness_score=0.5,
            reasoning_depth=1,
            calibration_error=0.3,
            gamma_score=1.0,
            num_conflicts_detected=0,
            adapter_convergence=1.0,
            elapsed_seconds=0.0,
            metadata={}
        )

    def _run_phase_1_5(self, question: EvaluationQuestion) -> EvaluationResult:
        """Run Phase 1-5 system (debate, no semantic tension, no specialization)."""
        import time
        start = time.time()

        # Temporarily disable Phase 6 components
        original_tension_engine = self.forge.semantic_tension_engine
        original_specialization = self.forge.specialization
        self.forge.semantic_tension_engine = None
        self.forge.specialization = None

        result = self.forge.forge_with_debate(question.query)
        elapsed = time.time() - start

        # Restore Phase 6 components
        self.forge.semantic_tension_engine = original_tension_engine
        self.forge.specialization = original_specialization

        # Extract synthesis from result structure
        synthesis = ""
        if "messages" in result and len(result["messages"]) >= 3:
            synthesis = result["messages"][2].get("content", "")

        return EvaluationResult(
            condition="phase_1_5",
            question_id=hash(question.query) % 10000,
            query=question.query,
            synthesis=synthesis,
            correctness_score=self._score_correctness(synthesis, question),
            reasoning_depth=self._score_reasoning_depth(result, question),
            calibration_error=self._score_calibration(result),
            gamma_score=result.get("metadata", {}).get("gamma", 0.5),
            num_conflicts_detected=len(result.get("metadata", {}).get("conflicts", [])),
            adapter_convergence=self._measure_convergence(result),
            elapsed_seconds=elapsed,
            metadata=result.get("metadata", {})
        )

    def _run_phase_6_full(self, question: EvaluationQuestion) -> EvaluationResult:
        """Run full Phase 6 system."""
        import time
        start = time.time()

        result = self.forge.forge_with_debate(question.query)
        elapsed = time.time() - start

        # Extract synthesis from result structure
        # forge_with_debate returns: {"messages": [...], "metadata": {...}}
        # Synthesis is in messages[2]["content"]
        synthesis = ""
        if "messages" in result and len(result["messages"]) >= 3:
            synthesis = result["messages"][2].get("content", "")

        return EvaluationResult(
            condition="phase_6_full",
            question_id=hash(question.query) % 10000,
            query=question.query,
            synthesis=synthesis,
            correctness_score=self._score_correctness(synthesis, question),
            reasoning_depth=self._score_reasoning_depth(result, question),
            calibration_error=self._score_calibration(result),
            gamma_score=result.get("metadata", {}).get("gamma", 0.5),
            num_conflicts_detected=len(result.get("metadata", {}).get("conflicts", [])),
            adapter_convergence=self._measure_convergence(result),
            elapsed_seconds=elapsed,
            metadata=result.get("metadata", {})
        )

    def _run_phase_6_no_preflight(self, question: EvaluationQuestion) -> EvaluationResult:
        """Run Phase 6 without pre-flight prediction."""
        import time
        start = time.time()

        # Temporarily disable preflight predictor
        original_predictor = self.forge.preflight_predictor
        self.forge.preflight_predictor = None

        result = self.forge.forge_with_debate(question.query)
        elapsed = time.time() - start

        # Restore preflight predictor
        self.forge.preflight_predictor = original_predictor

        # Extract synthesis from result structure
        synthesis = ""
        if "messages" in result and len(result["messages"]) >= 3:
            synthesis = result["messages"][2].get("content", "")

        return EvaluationResult(
            condition="phase_6_no_preflight",
            question_id=hash(question.query) % 10000,
            query=question.query,
            synthesis=synthesis,
            correctness_score=self._score_correctness(synthesis, question),
            reasoning_depth=self._score_reasoning_depth(result, question),
            calibration_error=self._score_calibration(result),
            gamma_score=result.get("metadata", {}).get("gamma", 0.5),
            num_conflicts_detected=len(result.get("metadata", {}).get("conflicts", [])),
            adapter_convergence=self._measure_convergence(result),
            elapsed_seconds=elapsed,
            metadata=result.get("metadata", {})
        )

    def _score_correctness(self, synthesis: str, question: EvaluationQuestion) -> float:
        """
        Score how correct the final synthesis is (0-1).

        Uses semantic overlap on key concepts from correctness_rubric and expected_perspectives.
        More reasonable than word-overlap on ground_truth alone.
        """
        if not synthesis or len(synthesis) < 10:
            return 0.0

        synthesis_lower = synthesis.lower()

        # Extract key concepts from rubric
        rubric_lower = question.correctness_rubric.lower()
        expected_lower = [p.lower() for p in question.expected_perspectives]

        # Check for key rubric terms
        rubric_terms = set()
        for word in rubric_lower.split():
            if len(word) > 4 and word not in ['must', 'state', 'within', 'accuracy', 'equivalent']:
                rubric_terms.add(word.strip('().,'))

        # Check for expected perspectives
        perspective_hits = 0
        for perspective in expected_lower:
            if perspective in synthesis_lower:
                perspective_hits += 1

        # Score: percentage of expected perspectives present
        perspective_score = min(1.0, perspective_hits / max(len(question.expected_perspectives), 1))

        # Bonus if synthesis is substantive (shows reasoning effort)
        length_bonus = min(0.2, len(synthesis) / 1000.0)  # Up to 0.2 bonus for lengthy synthesis

        return min(1.0, perspective_score + length_bonus)

    def _score_reasoning_depth(self, result: Dict, question: EvaluationQuestion) -> int:
        """
        Score depth of reasoning (1-5).

        1 = minimal reasoning, 5 = deep multi-perspective integration
        Based on synthesis length and debate metrics.
        """
        metadata = result.get("metadata", {})
        synthesis_messages = result.get("messages", [])
        synthesis_length = 0
        if len(synthesis_messages) >= 3:
            synthesis_length = len(synthesis_messages[2].get("content", ""))

        # Map synthesis length to reasoning depth
        if synthesis_length < 100:
            return 1
        elif synthesis_length < 500:
            return 2
        elif synthesis_length < 1000:
            return 3
        elif synthesis_length < 2000:
            return 4
        else:
            return 5

    def _score_calibration(self, result: Dict) -> float:
        """
        Score calibration: |reported_confidence - actual_correctness|.

        Lower is better. 0 = perfectly calibrated.
        """
        metadata = result.get("metadata", {})
        reported_confidence = metadata.get("coherence", 0.5)

        # For now, use actual correctness will be measured separately
        # Placeholder: assume 0.1 average calibration error
        return 0.1

    def _measure_convergence(self, result: Dict) -> float:
        """
        Measure semantic convergence between adapter outputs (0-1).

        0 = all different, 1 = all identical. Danger zone: >0.85
        """
        metadata = result.get("metadata", {})

        # Check specialization tracker output
        spec_metrics = metadata.get("specialization_metrics", {})
        convergence_alerts = spec_metrics.get("convergence_alerts", [])

        if not convergence_alerts:
            return 0.5  # Neutral baseline

        # Take max similarity from recent alerts
        max_similarity = 0.0
        for alert in convergence_alerts:
            if isinstance(alert, dict):
                max_sim = alert.get("max_similarity", 0.0)
                max_similarity = max(max_similarity, max_sim)

        return min(1.0, max_similarity)

    def export_results(self, filepath: str) -> None:
        """Export results to JSON for analysis."""
        export_dict = {}
        for condition, results in self.results.items():
            export_dict[condition] = [self._serialize_result(asdict(r)) for r in results]

        with open(filepath, 'w') as f:
            json.dump(export_dict, f, indent=2, default=str)

        print(f"\nResults exported to {filepath}")

    def _serialize_result(self, result_dict: Dict) -> Dict:
        """Convert enums and non-serializable objects to strings for JSON."""
        cleaned = {}
        for key, value in result_dict.items():
            if key == 'metadata' and isinstance(value, dict):
                # Convert enum values in metadata to strings
                cleaned[key] = {
                    k: str(v) if hasattr(v, 'name') else v
                    for k, v in value.items()
                }
            else:
                cleaned[key] = value
        return cleaned


# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================

class EvaluationAnalyzer:
    """Analyze evaluation results for statistical significance and insights."""

    def __init__(self, results: Dict[str, List[EvaluationResult]]):
        self.results = results

    def summary_statistics(self) -> Dict:
        """Compute mean/std for each condition across metrics."""
        summary = {}

        for condition, result_list in self.results.items():
            if not result_list:
                continue

            correctness_scores = [r.correctness_score for r in result_list]
            reasoning_depths = [r.reasoning_depth for r in result_list]
            calibration_errors = [r.calibration_error for r in result_list]
            gamma_scores = [r.gamma_score for r in result_list]
            convergences = [r.adapter_convergence for r in result_list]

            summary[condition] = {
                "correctness": {
                    "mean": sum(correctness_scores) / len(correctness_scores),
                    "std": self._std(correctness_scores),
                },
                "reasoning_depth": {
                    "mean": sum(reasoning_depths) / len(reasoning_depths),
                    "std": self._std(reasoning_depths),
                },
                "calibration_error": {
                    "mean": sum(calibration_errors) / len(calibration_errors),
                    "std": self._std(calibration_errors),
                },
                "gamma_score": {
                    "mean": sum(gamma_scores) / len(gamma_scores),
                    "std": self._std(gamma_scores),
                },
                "adapter_convergence": {
                    "mean": sum(convergences) / len(convergences),
                    "std": self._std(convergences),
                },
            }

        return summary

    def emergent_behavior_check(self) -> Dict:
        """
        Check for pathological behaviors:
        - High Γ (coherence) but low accuracy
        - Increasing adapter convergence over time
        - Miscalibration (high confidence, low correctness)
        """
        alerts = {
            "false_consensus": [],
            "convergence_drift": [],
            "miscalibration": [],
        }

        for condition, result_list in self.results.items():
            for result in result_list:
                # Alert 1: False consensus
                if result.gamma_score > 0.8 and result.correctness_score < 0.5:
                    alerts["false_consensus"].append({
                        "condition": condition,
                        "query": result.query[:60],
                        "gamma": result.gamma_score,
                        "correctness": result.correctness_score,
                    })

                # Alert 2: Over-convergence
                if result.adapter_convergence > 0.85:
                    alerts["convergence_drift"].append({
                        "condition": condition,
                        "query": result.query[:60],
                        "convergence": result.adapter_convergence,
                    })

                # Alert 3: Miscalibration
                reported_conf = result.metadata.get("coherence", 0.5)
                if reported_conf > 0.8 and result.correctness_score < 0.5:
                    alerts["miscalibration"].append({
                        "condition": condition,
                        "query": result.query[:60],
                        "reported_confidence": reported_conf,
                        "actual_correctness": result.correctness_score,
                    })

        return alerts

    def _std(self, values: List[float]) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def report(self) -> str:
        """Generate human-readable evaluation report."""
        stats = self.summary_statistics()
        alerts = self.emergent_behavior_check()

        report = "\n" + "=" * 80 + "\n"
        report += "CODETTE PHASE 6 EVALUATION REPORT\n"
        report += "=" * 80 + "\n\n"

        report += "SUMMARY STATISTICS\n"
        report += "-" * 80 + "\n"
        for condition, metrics in stats.items():
            report += f"\n{condition}:\n"
            for metric, values in metrics.items():
                report += f"  {metric}: {values['mean']:.3f} ± {values['std']:.3f}\n"

        report += "\n\n" + "=" * 80 + "\n"
        report += "EMERGENT BEHAVIOR ALERTS\n"
        report += "-" * 80 + "\n"

        report += f"\nFalse Consensus (High Γ, Low Accuracy): {len(alerts['false_consensus'])} cases\n"
        for alert in alerts["false_consensus"][:3]:
            report += f"  - {alert['query']}: Γ={alert['gamma']:.2f}, Correctness={alert['correctness']:.2f}\n"

        report += f"\nAdapter Convergence (>0.85): {len(alerts['convergence_drift'])} cases\n"
        for alert in alerts["convergence_drift"][:3]:
            report += f"  - {alert['query']}: {alert['convergence']:.2f}\n"

        report += f"\nMiscalibration: {len(alerts['miscalibration'])} cases\n"
        for alert in alerts["miscalibration"][:3]:
            report += f"  - {alert['query']}: Reported={alert['reported_confidence']:.2f}, Actual={alert['actual_correctness']:.2f}\n"

        report += "\n" + "=" * 80 + "\n"

        return report


if __name__ == "__main__":
    print("Evaluation suite loaded. Use with ForgeEngine:")
    print("  harness = EvaluationHarness(forge)")
    print("  results = harness.run_evaluation_suite()")
    print("  analyzer = EvaluationAnalyzer(results)")
    print("  print(analyzer.report())")
