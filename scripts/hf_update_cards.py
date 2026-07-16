#!/usr/bin/env python3
"""Upload updated model cards to HuggingFace repos."""

import os
from huggingface_hub import HfApi, get_token

TOKEN = os.environ.get("HF_TOKEN") or get_token()
api = HfApi(token=TOKEN)

# ── codette-llama-3.1-8b-merged ───────────────────────────────────────────────
MERGED_README = '''---
license: llama3.1
base_model: meta-llama/Llama-3.1-8B-Instruct
tags:
  - codette
  - llama-3.1
  - merged
  - multi-perspective
  - reasoning
  - orchestrator
language:
  - en
pipeline_tag: text-generation
---

# Codette Llama 3.1 8B — Merged Orchestrator Base

Llama 3.1 8B Instruct with the **Codette Orchestrator LoRA** permanently merged into the base weights. This is the inference base for the Codette multi-perspective reasoning system — pair it with the [perspective LoRA adapters](https://huggingface.co/Raiff1982/codette-lora-adapters) for full multi-agent synthesis.

**Paper:** [Codette: Multi-Perspective Reasoning as a Convergent Dynamical System](https://doi.org/10.21203/rs.3.rs-9362560/v1)
**GitHub:** [Raiff1982/Codette-Reasoning](https://github.com/Raiff1982/Codette-Reasoning)
**ORCID:** [0009-0003-7005-8187](https://orcid.org/0009-0003-7005-8187)

---

## Benchmark Results (May 2026)

17-problem benchmark across 6 cognitive categories, 4-condition ablation:

| Condition | Composite Score | vs. Baseline |
|-----------|----------------|--------------|
| SINGLE (baseline) | 0.357 | — |
| MULTI (6 perspectives) | 0.521 | +46.1% |
| MEMORY (+ cocoon store) | 0.574 | +60.8% |
| **CODETTE (full system)** | **0.744** | **+108.8%** |

- Cohen\'s *d* = 8.31 (large effect; *d* > 0.8 is large by convention)
- Paired *t*-test: *p* < 0.0001
- Turing naturalness: 0.245 → 0.820 (+235%) — depth–naturalness tradeoff resolved
- Coherence: 0.477 → 0.700

**GPQA (graduate-level science, 0-shot, 198-question diamond set):**

| Run | Accuracy | Environment |
|-----|----------|-------------|
| Base model + adapters (Kaggle cloud, June 17 2026) | **27.8%** (55/198) | Direct transformers+PEFT, no orchestration |
| Full Codette system (local server, June 6 2026) | **30.8%** (61/198) | Multi-agent debate + coherence tracking + cocoon memory |

Baselines: random 25%, GPT-4 0-shot 39%, human expert 65%.
The ~3pp gap between runs quantifies the system layer\'s contribution on GPQA specifically.

---

## Model Details

| Property | Value |
|---|---|
| Base Model | meta-llama/Llama-3.1-8B-Instruct |
| Merged Adapter | Orchestrator LoRA |
| Format | SafeTensors (full precision, ~16 GB) |
| Context Length | 8192 tokens |
| Quantized version | [codette-llama-3.1-8b-gguf](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-gguf) |

---

## System Architecture

```
Query
  │
  ▼
Executive Controller (complexity routing)
  │
  ▼
Merged Orchestrator Base  ◄── this repo
  │
  ▼
LoRA Hot-Swap (newton / davinci / empathy / philosophy /
               quantum / consciousness / multi_perspective /
               systems_architecture)
  │
  ▼
Multi-Agent Debate + Semantic Tension (RC+ξ)
  │
  ▼
AEGIS Ethical Governance (6 frameworks)
  │
  ▼
Synthesized Response + Cocoon Memory
```

The RC+ξ (Recursive Convergence + Epistemic Tension) formalism models cognitive state evolution as a convergent dynamical system:

```
Ψ(t+1) = Ψ(t) + α·∇Coherence(Ψ(t)) − β·ξ(t)·∇Tension(Ψ(t))
```

---

## Quick Start

### With Transformers (full precision)
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("Raiff1982/codette-llama-3.1-8b-merged")
tokenizer = AutoTokenizer.from_pretrained("Raiff1982/codette-llama-3.1-8b-merged")

inputs = tokenizer("Explain the nature of consciousness", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=512)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### With 4-bit quantization (recommended for 8–16 GB VRAM)
```python
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.bfloat16)
model = AutoModelForCausalLM.from_pretrained(
    "Raiff1982/codette-llama-3.1-8b-merged",
    quantization_config=bnb, device_map="auto"
)
```

### With perspective adapters (multi-agent mode)
```python
from peft import PeftModel

# Apply a perspective adapter on top of the base
model = PeftModel.from_pretrained(model, "Raiff1982/codette-lora-adapters",
                                  subfolder="newton_v2")
```

### Full local server
```bash
git clone https://github.com/Raiff1982/Codette-Reasoning
cd Codette-Reasoning
python inference/codette_server.py  # serves on :7860
```

---

## Related Resources

| Resource | Link |
|----------|------|
| Perspective LoRA adapters | [codette-lora-adapters](https://huggingface.co/Raiff1982/codette-lora-adapters) |
| Quantized GGUF | [codette-llama-3.1-8b-gguf](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-gguf) |
| Training datasets | [codette-training-data](https://huggingface.co/datasets/Raiff1982/codette-training-data) |
| GitHub | [Raiff1982/Codette-Reasoning](https://github.com/Raiff1982/Codette-Reasoning) |
| Paper (preprint) | [Research Square DOI](https://doi.org/10.21203/rs.3.rs-9362560/v1) |
| Zenodo archive | [10.5281/zenodo.19480004](https://doi.org/10.5281/zenodo.19480004) |
| Kaggle AGI benchmark | [RC+ Diagnostic Suite](https://kaggle.com/competitions/kaggle-measuring-agi/writeups/codette-rc-diagnostic-suite) |

---

## License

Subject to the [Llama 3.1 Community License](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE).
Created by Jonathan Harrison (Raiff\'s Bits LLC) — independent research.
'''

# ── codette-lora-adapters ─────────────────────────────────────────────────────
ADAPTERS_README = '''---
license: llama3.1
base_model: meta-llama/Llama-3.1-8B-Instruct
tags:
  - codette
  - llama-3.1
  - lora
  - peft
  - multi-perspective
  - reasoning
  - gguf
language:
  - en
pipeline_tag: text-generation
---

# Codette LoRA Adapters — 10 Perspective Lenses

10 specialized LoRA adapters for the **Codette Multi-Perspective Reasoning System**.
Each adapter encodes a distinct cognitive stance; the system routes queries and synthesizes across them at inference time.

**Paper:** [Codette: Multi-Perspective Reasoning as a Convergent Dynamical System](https://doi.org/10.21203/rs.3.rs-9362560/v1)
**Base model:** [Raiff1982/codette-llama-3.1-8b-merged](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-merged)

---

## Behavioral Verification (June 17, 2026)

All 7 perspective adapters passed behavioral verification after v2 retrain — **zero template-contamination markers** detected across 14 targeted probes. Adapters generate substantive, specific responses rather than training-data boilerplate.

---

## Adapters

| Adapter | Cognitive Stance | Version | GGUF |
|---------|-----------------|---------|------|
| **newton** | Analytical physics, mathematical precision, conservation laws | v2 | `newton-behavioral-lora-f16.gguf` |
| **davinci** | Creative invention, cross-domain synthesis, analogical reasoning | v2 | `davinci-behavioral-lora-f16.gguf` |
| **empathy** | Emotional intelligence, active listening, anti-flattery | v2 | `empathy-behavioral-lora-f16.gguf` |
| **philosophy** | Epistemological analysis, Socratic method, ethical frameworks | v2 | `philosophy-behavioral-lora-f16.gguf` |
| **quantum** | Probabilistic reasoning, Bayesian updating, superposition thinking | v2 | `quantum-behavioral-lora-f16.gguf` |
| **consciousness** | Recursive meta-cognition, RC+ξ self-monitoring | v2 | `consciousness-behavioral-lora-f16.gguf` |
| **multi_perspective** | Cross-lens synthesis, integrative reasoning | v2 | `multi_perspective-behavioral-lora-f16.gguf` |
| **systems_architecture** | Modularity, scalability, engineering tradeoffs | v2 | `systems_architecture-behavioral-lora-f16.gguf` |
| **orchestrator** | Query routing, debate coordination, coherence monitoring | v1 | `orchestrator-behavioral-lora-f16.gguf` |
| **constraint_tracker** | Instruction compliance, constraint enforcement | v1 | `constraint_tracker-behavioral-lora-f16.gguf` |

### v2 Adapter Training (June 15, 2026)
- Hand-authored datasets replacing the original template-generated training data
- Jargon-free system prompts (removed RC+ξ metric references that encouraged filler)
- 6 epochs, lr 1e-4, rank 16, A10G GPU
- Science claims web-verified before inclusion in training data
- Available as PEFT safetensors under `{name}_v2/` subfolders

---

## Usage

### Hot-swap with llama-cpp-python (local inference)
```python
from llama_cpp import Llama

llm = Llama(model_path="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            n_ctx=8192, n_gpu_layers=35)
llm.load_lora("newton-behavioral-lora-f16.gguf")

response = llm.create_chat_completion(
    messages=[{"role": "user", "content": "Derive the escape velocity formula."}],
    max_tokens=512,
)
```

### With PEFT + transformers (fine-tuning / Kaggle)
```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
import torch

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.bfloat16)
base = AutoModelForCausalLM.from_pretrained(
    "Raiff1982/codette-llama-3.1-8b-merged",
    quantization_config=bnb, device_map="auto"
)
model = PeftModel.from_pretrained(base, "Raiff1982/codette-lora-adapters",
                                  subfolder="newton_v2")
```

### Full Codette server (all adapters, live routing)
```bash
git clone https://github.com/Raiff1982/Codette-Reasoning
cd Codette-Reasoning
python inference/codette_server.py  # :7860
```

---

## File Structure

```
codette-lora-adapters/
  ├── behavioral-gguf/              # v2 GGUF adapters (27 MB each)
  │   ├── newton-behavioral-lora-f16.gguf
  │   ├── davinci-behavioral-lora-f16.gguf
  │   ├── empathy-behavioral-lora-f16.gguf
  │   └── ...
  ├── newton_v2/                    # v2 PEFT safetensors
  │   ├── adapter_config.json
  │   └── adapter_model.safetensors
  ├── davinci_v2/
  ├── empathy_v2/
  ├── ...
  ├── newton/                       # v1 PEFT safetensors (legacy)
  └── ...
```

---

## Related Resources

| Resource | Link |
|----------|------|
| Merged base model | [codette-llama-3.1-8b-merged](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-merged) |
| Quantized GGUF base | [codette-llama-3.1-8b-gguf](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-gguf) |
| Training datasets | [codette-training-data](https://huggingface.co/datasets/Raiff1982/codette-training-data) |
| GitHub | [Raiff1982/Codette-Reasoning](https://github.com/Raiff1982/Codette-Reasoning) |
| Paper | [Research Square DOI](https://doi.org/10.21203/rs.3.rs-9362560/v1) |

---

## License

Subject to the [Llama 3.1 Community License](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE).
Created by Jonathan Harrison (Raiff\'s Bits LLC) — independent research.
'''

# ── Upload ────────────────────────────────────────────────────────────────────
import tempfile, os

def push_readme(repo_id, content, repo_type="model"):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    try:
        api.upload_file(
            path_or_fileobj=tmp,
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Update model card: benchmark results, v2 adapters, public access",
        )
        print(f"✓ Updated {repo_id}")
    finally:
        os.unlink(tmp)

push_readme("Raiff1982/codette-llama-3.1-8b-merged", MERGED_README)
push_readme("Raiff1982/codette-lora-adapters", ADAPTERS_README)
print("Done.")
