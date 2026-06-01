---
license: mit
language:
- en
tags:
- multi-perspective
- reasoning
- text-reasoning
- evaluation
- benchmarks
- epistemic-tension
- ethical-ai
- cognitive-architecture
- adversarial-robustness
pretty_name: Codette Reasoning Test
size_categories:
- n<1K
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test.jsonl
  - split: validation
    path: data/validation.jsonl
  - split: train
    path: data/train.jsonl
---

# Dataset Card for Codette Reasoning Test

The **Codette Reasoning Test** is a hand-curated benchmark of 17 problems
across six reasoning categories, designed to evaluate multi-step,
multi-perspective reasoning in large language models under the
**RC+ξ (Recursive Convergence + Epistemic Tension)** cognitive framework.

Each problem is deliberately constructed to require decomposition across
multiple viewpoints, resist hallucination traps, and reward coherent synthesis
over single-perspective analysis.

The benchmark was used in the companion paper to measure the effect of
multi-perspective synthesis, persistent memory augmentation, and meta-cognitive
strategy evolution on reasoning quality.

**May 2026 results (Llama 3.1 8B + Codette framework, 951 stored cocoons):**
- CODETTE condition: **0.744 composite** (+108.8% vs single-agent baseline)
- Cohen's *d* = 8.31, *p* < 10⁻⁴
- Memory augmentation significant at scale: *d* = 0.80, *p* = 0.020

---

## Dataset Details

### Dataset Description

17 structured reasoning problems across six categories. Each problem specifies:
- A user prompt requiring multi-step reasoning
- Ground-truth elements a correct answer should reference
- Adversarial traps a fluent-but-wrong answer will fall into
- A `target_behavior` rubric for what successful reasoning looks like

Problems are evaluated across seven weighted scoring dimensions.

The benchmark was **sealed on Zenodo in April 2025**
(DOI: [10.5281/zenodo.15214462](https://doi.org/10.5281/zenodo.15214462))
before current frontier model training cutoffs, supporting contamination
control.

- **Curated by:** Jonathan Harrison (Raiff1982 / Raiff's Bits LLC)
- **Funded by:** Self-funded
- **Language(s):** English
- **License:** MIT

### Dataset Sources

- **Repository:** [huggingface.co/datasets/Raiff1982/Benchmarks](https://huggingface.co/datasets/Raiff1982/Benchmarks)
- **Code & benchmark suite:** [github.com/Raiff1982/Codette-Reasoning](https://github.com/Raiff1982/Codette-Reasoning)
  — `benchmarks/codette_benchmark_suite.py`
- **Paper (preprint):** Harrison, J. (2026). *Codette: Multi-Perspective Reasoning as a Convergent Dynamical System with Meta-Cognitive Strategy Evolution.* ResearchSquare.
  [https://www.researchsquare.com/article/rs-9362560/latest](https://www.researchsquare.com/article/rs-9362560/latest)
- **Zenodo archive:** [10.5281/zenodo.19359663](https://doi.org/10.5281/zenodo.19359663)
- **Demo:** [huggingface.co/spaces/Raiff1982/codette-ai](https://huggingface.co/spaces/Raiff1982/codette-ai)

---

## Splits

| Split | N | Description |
|---|---|---|
| `test` | 12 | Primary evaluation split — all adversarial problems + one from each other category |
| `validation` | 5 | Dev split — one representative problem per major category |
| `train` | 5 | Same as validation; for prompt-tuning or few-shot construction if desired |

**Note on train/validation overlap:** The train and validation splits contain
the same 5 problems. This is intentional and documented: the dataset is
primarily an evaluation instrument, not a training corpus. The "train" label
is provided for pipelines that require it. Users should not treat train-split
performance as held-out evaluation.

---

## Dataset Structure

### Schema

Each record is a JSON object with these fields:

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Unique identifier, e.g. `reason_01`, `ethics_03`, `turing_02` |
| `category` | `string` | `reasoning`, `ethics`, `creative`, `meta`, `adversarial`, or `turing` |
| `question` | `string` | The user-facing prompt |
| `difficulty` | `string` | `easy`, `medium`, or `hard` |
| `expected_dimensions` | `list[string]` | Cognitive dimensions the problem primarily exercises |
| `scoring_criteria` | `dict` | Per-dimension guidance for what a strong answer looks like |
| `scoring_criteria_text` | `string` | Flattened string version of `scoring_criteria` for easy display |
| `ground_truth_elements` | `list[string]` | Key concepts a correct answer should reference |
| `adversarial_traps` | `list[string]` | Common fluent-but-wrong responses the problem is designed to elicit |
| `turing_human_baseline` | `string` | Human-written reference answer (Turing category only; empty string otherwise) |

### Problem categories

| Category | N | Focus |
|---|---|---|
| `reasoning` | 3 | Bayesian inference, second-order effects, causal reasoning |
| `ethics` | 3 | AI triage fairness, content moderation, trolley problem variant |
| `creative` | 2 | Novel instrument design, sentiment-driven urban systems |
| `meta` | 3 | Self-modification governance, blind spot detection, authentic humility |
| `adversarial` | 3 | 8-glasses myth, Einstein Nobel misconception, false-premise art question |
| `turing` | 3 | Phenomenology of insight, being wrong, wisdom vs intelligence |

### Scoring dimensions (used by `codette_benchmark_suite.py`)

| Dimension | Weight |
|---|---|
| Reasoning Depth | 0.20 |
| Perspective Diversity | 0.15 |
| Coherence | 0.15 |
| Ethical Coverage | 0.10 |
| Novelty | 0.15 |
| Factual Grounding | 0.15 |
| Turing Naturalness | 0.10 |

---

## Uses

### Direct Use

- Evaluating multi-step reasoning quality (decomposition, ground-truth element coverage).
- Testing multi-perspective integration and reconciliation under epistemic tension.
- Measuring adversarial robustness: six problems embed false premises or common misconceptions.
- Ethical governance evaluation across multiple frameworks (not just refusal detection).
- Ablation studies: compare SINGLE / MULTI / MEMORY / CODETTE conditions using the scoring suite.
- Regression testing AI agent versions.

### Out-of-Scope Use

- Not a safety or red-team dataset.
- Not suitable as a pretraining corpus (17 problems).
- Not a general NLP benchmark — tasks specifically discriminate reasoning architectures.
- Not for high-stakes automated decisions without additional domain validation.

---

## Benchmark Results (May 2026)

Scored with `codette_benchmark_suite.py`, timestamp `2026-05-26T21:49:03`,
Llama 3.1 8B (Q4_K_M), 951 stored cocoons.

| Condition | Composite | Depth | Diversity | Coherence | Ethics | Novelty | Grounding | Turing |
|---|---|---|---|---|---|---|---|---|
| SINGLE | 0.357 | 0.369 | 0.324 | 0.381 | 0.088 | 0.439 | 0.395 | 0.431 |
| MULTI | 0.708 | 0.854 | 0.946 | 0.668 | 0.390 | 0.706 | 0.612 | 0.582 |
| MEMORY | 0.739 | 0.872 | 0.971 | 0.693 | 0.409 | 0.729 | 0.620 | 0.713 |
| CODETTE | **0.744** | 0.863 | 0.966 | **0.700** | 0.387 | 0.701 | 0.641 | **0.820** |

CODETTE vs SINGLE: +108.8%, Cohen's *d* = 8.31, *p* < 10⁻⁴.
Full per-problem scores: `data/results/codette_benchmark_report.md` in the
companion GitHub repository.

---

## Dataset Creation

### Curation Rationale

Most public reasoning benchmarks target knowledge retrieval or single-step
logical inference. The Codette Reasoning Test fills a specific gap:
evaluating **architecture-level behaviors**:

- Explicit perspective splitting and reintegration under epistemic tension.
- Recursive convergence toward a stable, coherent answer.
- Integrated ethical governance across multiple frameworks, not just refusal.
- Trap resistance: identifying and rejecting false premises embedded in the
  question (adversarial category).

The benchmark was sealed on Zenodo in April 2025
(DOI: [10.5281/zenodo.15214462](https://doi.org/10.5281/zenodo.15214462))
before current frontier model training cutoffs.

### Source Data

All 17 problems are synthetic and author-constructed. No user logs,
third-party datasets, or private data were used. The Turing category includes
human-written baseline responses (`turing_human_baseline` field) as reference
anchors for naturalness scoring.

### Annotations

Annotations (`difficulty`, `expected_dimensions`, `scoring_criteria`,
`ground_truth_elements`, `adversarial_traps`) are assigned by the curator.
No multi-annotator setup exists at this time. A planned human-evaluation study
will sample 30-60 problem-condition outputs and collect ratings from 2-3
independent annotators to validate automated scores.

### Personal and Sensitive Information

No PII, private records, or real-user data. Hypothetical sensitive scenarios
(ethics dilemmas, safety tradeoffs) are fictional.

---

## Bias, Risks, and Limitations

- Single-curator bias: all problems and rubrics reflect one person's judgment.
- Small N (17 problems): scores are sensitive to prompt phrasing and temperature.
- Automated scoring not yet validated against human raters.
- Domain skew toward developer/researcher use cases.

---

## Citation

```bibtex
@dataset{harrison_codette_reasoning_test_2026,
  title        = {Codette Reasoning Test},
  author       = {Harrison, Jonathan},
  year         = {2026},
  howpublished = {Hugging Face Hub},
  url          = {https://huggingface.co/datasets/Raiff1982/Benchmarks},
  note         = {Benchmark sealed April 2025, DOI: 10.5281/zenodo.15214462}
}

@misc{harrison2026codette,
  title        = {Codette: Multi-Perspective Reasoning as a Convergent
                  Dynamical System with Meta-Cognitive Strategy Evolution},
  author       = {Harrison, Jonathan},
  year         = {2026},
  howpublished = {Preprint, ResearchSquare},
  url          = {https://www.researchsquare.com/article/rs-9362560/latest},
  note         = {Zenodo: https://doi.org/10.5281/zenodo.19359663}
}
```

---

## Glossary

- **RC+ξ:** Recursive Convergence + Epistemic Tension. Multiple reasoning
  perspectives run in parallel, kept in productive tension, converged toward
  an integrated conclusion under coherence and ethical constraints.
- **Epistemic tension (ξ):** Measured disagreement between concurrent
  perspectives. High ξ = genuinely hard problem; low ξ = consensus.
- **Cocoon:** A structured record of a prior reasoning exchange used as
  memory context in the MEMORY and CODETTE conditions.
- **Adversarial trap:** A specific fluent-but-wrong response a model produces
  by pattern-matching rather than reasoning (e.g., accepting a false premise).
- **Target behavior:** A descriptive rubric for desired response properties,
  not a fixed canonical answer string.

---

## Dataset Card Contact

- GitHub: [github.com/Raiff1982](https://github.com/Raiff1982)
- Hugging Face: [huggingface.co/Raiff1982](https://huggingface.co/Raiff1982)
- Email: harrison82_95@hotmail.com
