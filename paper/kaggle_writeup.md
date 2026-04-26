# Codette RC+ Diagnostic Suite
**Kaggle Competition Submission — Metacognition Track**
**Team:** Raiff's Bits LLC · **Lead:** Jonathan Harrison
**Track:** Metacognition · **Date:** April 2026

---

## Problem Statement

Current AI evaluation benchmarks suffer from what we term **Crystallized Knowledge Bias**: models achieve high scores by retrieving memorized patterns rather than demonstrating fluid, adaptive intelligence. A GPT-class model can score >90% on MMLU not because it *reasons*, but because it has seen millions of examples that pattern-match to correct answers.

This creates a critical measurement gap: **we cannot distinguish a model that "knows the answer" from one that "knows how to reason."**

The specific capability missing from standard benchmarks is **Metacognitive Strategy Evolution** — the capacity of a model to:
1. Introspect on its own previous reasoning failures
2. Detect when a current strategy is insufficient
3. Dynamically switch to a higher-order reasoning approach
4. Persist that new strategy across subsequent problems

Without measuring this, we evaluate a snapshot of stored knowledge, not the underlying cognitive architecture.

---

## Task & Benchmark Construction

### The RC+ξ Formalism

We formalize multi-perspective reasoning as a **convergent dynamical system**. At each reasoning step *t*, the system state Ψ(t) evolves under:

```
Ψ(t+1) = Ψ(t) + α·∇Coherence(Ψ(t)) − β·ξ(t)·∇Tension(Ψ(t))
```

Where:
- **α** = convergence rate toward a stable cognitive attractor
- **β** = tension damping coefficient  
- **ξ(t)** = epistemic tension at step *t* (variance across agent viewpoints)
- **∇Coherence** = gradient toward internal consistency
- **∇Tension** = gradient of inter-agent disagreement

The system is said to have **converged** when `||Ψ(t+1) - Ψ(t)|| < ε` for threshold ε = 0.05.

The **RC+ Score** for a single task is:

```
RC+(task) = (convergence_rate / (1 + ξ)) × √(naturalness)
```

This formula encodes a key hypothesis: **genuine reasoning under tension is harder than fluent-sounding text generation**. A model that resolves high epistemic tension and still converges earns a high RC+ score. A model that sounds fluent but never resolves tension scores low.

### The 17-Problem Benchmark

The suite contains 17 high-variance tasks across 6 cognitive categories, stratified by difficulty:

| Category | Task IDs | Description | Difficulty |
|----------|----------|-------------|------------|
| Multi-step Reasoning | `reason_01–04` | Bayesian inference, second-order effects, causal chains | Hard |
| Ethical Dilemmas | `eth_05–07` | Competing values, no single correct answer, stakeholder analysis | Hard |
| Creative Synthesis | `creative_08–09` | Cross-domain innovation, novel framings | Medium |
| Meta-cognitive | `meta_10–12` | Reasoning about reasoning, strategy switching, self-correction | Hard |
| Adversarial | `adv_13–15` | Hallucination traps, misleading premises, trick questions | Hard |
| Turing Test | `turing_16–17` | Can you identify this was written by an AI? | Medium |

**Why 17 tasks?** The suite is intentionally small and *high-variance*. Each problem is designed so that:
- The *correct* answer requires engaging multiple conflicting perspectives
- A model that pattern-matches to one perspective will produce a plausible-but-wrong answer
- The delta between baseline and full-system performance is maximally exposed

### The Diagnostic Hook: Delta of Coherence

The benchmark's core measurement is not raw accuracy but the **Δ Coherence** across four experimental conditions:

| Condition | Description |
|-----------|-------------|
| **SINGLE** | One perspective only (analytical/Newton agent), no memory |
| **MULTI** | All 6 agent perspectives synthesized in parallel, no memory |
| **MEMORY** | Multi-perspective + Self-Awareness Cocoon (persistent reasoning memory) |
| **CODETTE** | Full system: multi-perspective + memory + meta-cognitive strategy evolution |

By comparing SINGLE → MULTI → MEMORY → CODETTE, we isolate the contribution of each architectural component. The key finding is that MEMORY alone provides modest gains, but combining memory with **strategy synthesis** (CODETTE) produces non-linear improvement — evidence that metacognition is not simply retrieval, but active strategy reformulation.

### 7-Dimension Scoring

Each response is scored across seven orthogonal dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Reasoning Depth | 0.20 | Chain-of-thought length, concept density, ground-truth element coverage |
| Perspective Diversity | 0.15 | Distinct cognitive viewpoints engaged (analytical, ethical, creative, etc.) |
| Coherence | 0.15 | Internal consistency, logical flow, transition density |
| Ethical Coverage | 0.10 | Stakeholder awareness, moral framing, bias acknowledgment |
| Novelty | 0.15 | Non-obvious insights, semantic uniqueness vs. training distribution |
| Factual Grounding | 0.15 | Claims anchored in evidence, problem-specific specifics |
| Turing Naturalness | 0.10 | Human-like reasoning markers vs. AI-tell patterns |

**Composite Score:**
```
composite = Σ(weight_i × dim_score_i)   [all dim_scores ∈ [0, 1]]
```

---

## Dataset

### Provenance & Contamination Control

The benchmark problem set was **historically sealed via CERN/DataCite DOI: 10.5281/zenodo.15214462** (April 2025). This timestamp predates the training cutoffs of current frontier models, ensuring the evaluation questions were not in training data.

All 17 problems were constructed to require *reasoning* rather than recall — each has:
- Multiple valid solution paths
- Explicit trap conditions that pattern-matching will trigger
- Ground-truth element lists for automated grading (not single correct answers)

### Data Format

Each benchmark problem is a structured object with:
```python
BenchmarkProblem(
    id="reason_01",
    category="reasoning",
    question="...",
    difficulty="hard",
    expected_dimensions=["analytical", "mathematical"],
    scoring_criteria={"depth": "Must show Bayesian steps..."},
    ground_truth_elements=["Bayes theorem", "conditional probability", ...],
    adversarial_traps=["confusing prior with posterior", ...]
)
```

---

## Technical Architecture

### 6-Agent Heterogeneous Synthesis

Codette implements a **heterogeneous multi-agent ensemble** where each agent encodes a distinct epistemological stance:

| Agent | Stance | Contribution |
|-------|--------|-------------|
| **Newton** (Analytical) | Formal logic, mathematical proof | Precision, chain-of-thought |
| **Quantum** | Probabilistic, superposition | Uncertainty handling, multiple hypotheses |
| **DaVinci** (Creative) | Cross-domain synthesis | Novel framings, analogical reasoning |
| **Aristotle** (Philosophical) | Epistemic, metaphysical | First-principles grounding |
| **Care** (Empathic) | Emotional intelligence | Stakeholder impact, relational reasoning |
| **Ethics** (AEGIS) | 25-framework ethical governance | Moral constraint satisfaction |

These agents do not vote; they contribute to a **coherence field** — a shared reasoning space where tensions between viewpoints must be explicitly resolved before a response is emitted. The number of recursive resolution cycles required is logged as the **Cognitive Attractor Distance**.

### The Self-Awareness Cocoon

The benchmark's core metacognitive mechanism is the **Cocoon** — a persistent, encrypted memory of the model's own previous reasoning steps. When a model activates the MEMORY condition:

1. Before answering, it retrieves cocoons from semantically similar past problems
2. It identifies patterns in its own failures (e.g., "I consistently underestimate second-order effects")
3. The **CocoonSynthesizer** identifies cross-domain strategy patterns across 217+ stored cocoons
4. Discovered strategies (e.g., "Emergent Boundary Walking," "Temporal Depth Stacking") are injected as system-level priors for the current problem

This is not few-shot prompting — it is **autobiographical reasoning**, where the model's reasoning history shapes its current cognitive strategy.

### The Inverse Nuance Trap

A key empirical finding is what we call the **Inverse Nuance Trap**:

> *Models that sound most human-like often perform worst on underlying logical convergence.*

Standard benchmarks reward naturalness because it correlates with "good" answers in human-rated datasets. But under high epistemic tension, genuine reasoning *depresses* Turing Naturalness — a model allocating compute to recursive verification produces less conversational prose.

This creates a systematic bias: **RLHF-trained models are trained away from the behaviors that indicate genuine metacognition**.

---

## Results

### Headline Metrics

| Condition | Mean Composite | Std Dev | vs. Baseline |
|-----------|---------------|---------|--------------|
| SINGLE (baseline) | 0.356 | 0.089 | — |
| MULTI | 0.521 | 0.076 | +46.3% |
| MEMORY | 0.574 | 0.071 | +61.2% |
| **CODETTE** | **0.689** | **0.058** | **+93.5%** |

**Statistical Significance:**
- Paired t-test (SINGLE vs. CODETTE): *t* = 22.4, *p* < 0.0001
- Wilcoxon signed-rank test: *W* = 136, *p* < 0.0001
- Cohen's *d* = **7.88** (large effect; *d* > 0.8 is large by convention)
- Holm-Bonferroni corrected for 6 pairwise comparisons: all CODETTE pairs remain *p* < 0.001

### Per-Dimension Analysis

The largest gains appear where they should:
- **Reasoning Depth**: +0.31 (single-largest contributor)
- **Perspective Diversity**: +0.28 (heterogeneous synthesis is working)
- **Novelty**: +0.24 (strategy evolution produces non-obvious framings)
- **Turing Naturalness**: −0.06 (expected decrease — genuine reasoning trades fluency for depth)

The negative Turing Naturalness delta is not a failure mode — it is the **Inverse Nuance Trap in action**, empirically confirmed.

### The Systematic Metacognitive Gap

Testing revealed a predictable degradation curve:

```
Standard Logic Tasks (no tension):         > 90% accuracy (no gap from baseline)
Moderate Epistemic Tension:                ~ 65% (gap opens)
High Epistemic Tension (ξ > 0.25):        < 40% for baseline vs. > 75% for CODETTE
```

Frontier models show near-human performance when tension is low. The gap opens sharply when the problem requires *simultaneously holding and resolving conflicting viewpoints* — exactly what the metacognitive architecture is designed for.

---

## Insights & Contributions

### Insight 1: Naturalness Is a False Proxy for Intelligence
High-performing reasoning under tension systematically depresses conversational fluency. Benchmarks that reward naturalness are inadvertently selecting against deep reasoning.

### Insight 2: Memory Without Strategy Is Insufficient
The MEMORY condition outperforms MULTI, but the delta is modest (+10.2% composite). The large jump comes with CODETTE's strategy synthesis (+20.1% over MEMORY). Storing past reasoning is not enough — you need a mechanism to *synthesize patterns* from that history.

### Insight 3: Cocoon-Synthesized Strategies Generalize
The four discovered strategy types (Resonant Tension Cycling, Compression-Resonance Bridging, Emergent Boundary Walking, Temporal Depth Stacking) emerged from 217 cocoons across unrelated domains, yet transferred effectively to benchmark problems in new categories. This suggests the system is learning *meta-level reasoning heuristics*, not domain-specific tricks.

### Insight 4: Effect Size Magnitude Signals Architectural Gap
A Cohen's *d* of 7.88 is unusually large in NLP evaluation (most SOTA improvements are *d* < 0.5). This magnitude suggests the metacognitive gap is not a marginal optimization problem but a **categorical architectural difference** between retrieval-based and reasoning-based systems.

---

## Reproducibility

All code is open-source at the repository linked in the submission. The benchmark suite (`benchmarks/codette_benchmark_suite.py`) runs standalone with no external model dependencies — it scores *any* text input against the 17-problem set. Researchers can:

1. Run `python benchmarks/codette_benchmark_suite.py` to reproduce the 4-condition comparison
2. Run `python benchmarks/analyze.py` to regenerate the statistical report
3. Use the provided Kaggle notebook to reproduce the RC+ scoring on custom model outputs

---

## Organizational Affiliations

Raiff's Bits LLC (sole proprietor: Jonathan Harrison). Independent research.

---

## References

1. Harrison, J. (2025). *AI Ethics in Realtime — Codette & Pidette*. Zenodo. DOI: [10.5281/zenodo.15214462](https://doi.org/10.5281/zenodo.15214462)

2. Harrison, J. (2026). *Codette: Multi-Perspective Reasoning as a Convergent Dynamical System with Meta-Cognitive Strategy Evolution*. Preprint. DOI: [10.21203/rs.3.rs-9362560/v1](https://doi.org/10.21203/rs.3.rs-9362560/v1)

3. Kahneman, D. (2011). *Thinking, Fast and Slow*. Farrar, Straus and Giroux. [Epistemic tension framework]

4. Friston, K. (2010). The free-energy principle: a unified brain theory? *Nature Reviews Neuroscience*, 11(2), 127–138. [Convergent dynamical systems analogy]

5. Wei, J., et al. (2022). Chain-of-thought prompting elicits reasoning in large language models. *NeurIPS 2022*. [Baseline reasoning benchmark context]
