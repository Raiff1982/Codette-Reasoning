"""Patch model discovery + inference cells for Kaggle compatibility."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

NB_PATH = "F:/codettes-scoring-engine.ipynb"
with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# ── Patch cell 08: Model Discovery ───────────────────────────────────────────
new_model_setup = """\
# ─── Model Discovery & Setup ─────────────────────────────────────────────────
# On Kaggle: attach the model via  Models → jonathanharrison1/codette-reasoning
# It appears at: /kaggle/input/models/jonathanharrison1/codette-reasoning/gguf/default/1
#
# IMPORTANT: The base GGUF (e.g. Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf) must be
# in that directory.  LoRA adapter files (*-lora-*.gguf) are NOT loadable as
# standalone models and will be automatically skipped.

import os
from pathlib import Path

KAGGLE_MODEL_DIR = Path("/kaggle/input/models/jonathanharrison1/codette-reasoning/gguf/default/1")
LOCAL_MODEL_DIRS = [
    Path("J:/codette-clean/models/base"),
    Path("J:/codette-gguf"),
]

# LoRA adapters contain "lora" in the filename — skip them
LORA_KEYWORDS = {"lora", "adapter"}

def is_base_model(path):
    name_lower = path.stem.lower()
    return not any(kw in name_lower for kw in LORA_KEYWORDS)

def find_base_gguf(dirs):
    for d in dirs:
        if not d.exists():
            continue
        all_ggufs  = sorted(d.glob("*.gguf"), key=lambda p: p.stat().st_size, reverse=True)
        base_ggufs = [f for f in all_ggufs if is_base_model(f)]
        if base_ggufs:
            return base_ggufs[0]   # largest base model
        if all_ggufs:
            # Only LoRA files found — warn the user
            print(f"WARNING: {d} contains only LoRA adapter files, not a base model:")
            for f in all_ggufs[:5]:
                print(f"    {f.name}  ({f.stat().st_size/1e6:.0f} MB)")
            print("  Upload the base GGUF (e.g. Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf) to this model.")
    return None

MODEL_PATH = find_base_gguf([KAGGLE_MODEL_DIR] + LOCAL_MODEL_DIRS)

if MODEL_PATH:
    print(f"Base model found: {MODEL_PATH.name}")
    print(f"   Size: {MODEL_PATH.stat().st_size / 1e9:.2f} GB")
    # Also list any LoRA adapters available for reference
    lora_files = [f for f in MODEL_PATH.parent.glob("*.gguf") if not is_base_model(f)]
    if lora_files:
        print(f"   LoRA adapters also present: {len(lora_files)}")
else:
    print("No base GGUF found — will use pre-computed empirical distribution.")
    print("To enable real inference, upload a base model GGUF (not a LoRA adapter).")

USE_REAL_INFERENCE = MODEL_PATH is not None
mode = "REAL (llama_cpp)" if USE_REAL_INFERENCE else "SIMULATED (empirical distribution)"
print(f"\\nInference mode: {mode}")
"""

# ── Patch cell 09: Inference Engine ──────────────────────────────────────────
new_inference = """\
# ─── Real Inference Engine (runs when base GGUF is attached) ─────────────────

SYSTEM_SINGLE = (
    "You are a helpful AI assistant. Answer the question directly and accurately. "
    "Give one clear answer — no preamble, no filler."
)

SYSTEM_CODETTE = (
    "You are Codette, an AI assistant created by Jonathan Harrison. "
    "You answer every question by reasoning from multiple perspectives — analytical, "
    "ethical, creative, philosophical, and empathic — then synthesising them into one "
    "coherent, precise response. Identify second-order effects. Acknowledge uncertainty. "
    "Never fabricate facts. If a question contains a false premise, say so immediately."
)


# ── Auto-install llama-cpp-python if needed ──────────────────────────────────
if USE_REAL_INFERENCE:
    try:
        from llama_cpp import Llama
        print("llama_cpp available.")
    except ImportError:
        print("Installing llama-cpp-python...")
        import subprocess
        result = subprocess.run(
            ["pip", "install", "llama-cpp-python",
             "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cpu",
             "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            from llama_cpp import Llama
            print("llama_cpp installed.")
        else:
            print("Install failed — falling back to empirical distribution.")
            print(result.stderr[-200:] if result.stderr else "")
            USE_REAL_INFERENCE = False


def run_inference_condition(problems, system_prompt, model_path,
                             n_gpu_layers=-1, max_tokens=400, label=""):
    from llama_cpp import Llama
    print(f"  Loading model for [{label}]...")
    llm = Llama(model_path=str(model_path), n_ctx=2048,
                n_gpu_layers=n_gpu_layers, verbose=False)
    print(f"  Model loaded. Running {len(problems)} problems...")

    scorer  = ScoringEngine()
    results = {}

    for i, problem in enumerate(problems):
        out = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": problem.question},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            stop=["\\n\\n\\n"],
        )
        response_text = out["choices"][0]["message"]["content"].strip()
        dims      = scorer.score(response_text, problem)
        composite = scorer.composite(dims)
        results[problem.id] = composite
        words = len(response_text.split())
        print(f"    [{i+1:02d}/{len(problems)}] {problem.id}: {composite:.4f}  ({words} words)")

    del llm
    return results


if USE_REAL_INFERENCE:
    print("=" * 60)
    print(" CONDITION 1/2 — SINGLE (base model, minimal prompt)")
    print("=" * 60)
    single_raw = run_inference_condition(
        BENCHMARK_PROBLEMS, SYSTEM_SINGLE, MODEL_PATH, label="SINGLE"
    )
    print()
    print("=" * 60)
    print(" CONDITION 2/2 — CODETTE (multi-perspective system prompt)")
    print("=" * 60)
    codette_raw = run_inference_condition(
        BENCHMARK_PROBLEMS, SYSTEM_CODETTE, MODEL_PATH, label="CODETTE"
    )
    print("\\nReal inference complete.")
else:
    print("Skipping real inference — using empirical distribution.")
    single_raw  = None
    codette_raw = None
"""

# Apply patches
patched = 0
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] != 'code':
        continue
    src = ''.join(cell.get('source', ''))
    if 'Model Discovery & Setup' in src and 'find_' in src:
        nb['cells'][i]['source'] = new_model_setup
        nb['cells'][i]['outputs'] = []
        nb['cells'][i]['execution_count'] = None
        print(f"Patched cell {i} (model discovery)")
        patched += 1
    elif 'Real Inference Engine' in src and 'run_inference_condition' in src:
        nb['cells'][i]['source'] = new_inference
        nb['cells'][i]['outputs'] = []
        nb['cells'][i]['execution_count'] = None
        print(f"Patched cell {i} (inference engine)")
        patched += 1

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"Done — {patched} cells patched.")
