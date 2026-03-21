#!/usr/bin/env python3
"""Codette LoRA Adapter Test Suite

Tests the newton and davinci adapters:
1. Weight inspection (no base model needed)
2. Full inference comparison (loads base model)

Hardware: Intel Arc 140V (8GB XPU) + 16GB RAM
Strategy: CPU float16 inference with LoRA merge
"""

import os, sys, json, time

# SYCL DLLs
os.environ["PATH"] = r"J:\Lib\site-packages\Library\bin" + os.pathsep + os.environ.get("PATH", "")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
import safetensors.torch as st
from pathlib import Path

ADAPTER_DIR = Path("J:/codette-training-lab/adapters/hf_download")
NEWTON_DIR = ADAPTER_DIR / "newton"
DAVINCI_DIR = ADAPTER_DIR / "davinci"
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

# ================================================================
# PHASE 1: Quick Adapter Weight Validation (no base model needed)
# ================================================================
def phase1_weight_inspection():
    print("=" * 60)
    print("PHASE 1: Adapter Weight Inspection")
    print("=" * 60)

    for name, adapter_dir in [("newton", NEWTON_DIR), ("davinci", DAVINCI_DIR)]:
        print(f"\n--- {name.upper()} Adapter ---")

        # Load adapter config
        with open(adapter_dir / "adapter_config.json") as f:
            config = json.load(f)
        print(f"  Base model: {config['base_model_name_or_path']}")
        print(f"  LoRA rank: {config['r']}, alpha: {config['lora_alpha']}")
        print(f"  Targets: {config['target_modules']}")
        print(f"  PEFT version: {config['peft_version']}")

        # Load adapter weights
        weights = st.load_file(str(adapter_dir / "adapter_model.safetensors"))
        print(f"  Weight tensors: {len(weights)}")

        total_params = 0
        layer_stats = {}
        for key, tensor in sorted(weights.items()):
            params = tensor.numel()
            total_params += params
            mean = tensor.float().mean().item()
            std = tensor.float().std().item()
            abs_mean = tensor.float().abs().mean().item()
            nonzero = (tensor != 0).float().mean().item() * 100

            # Group by layer type
            if "lora_A" in key:
                ltype = "lora_A"
            elif "lora_B" in key:
                ltype = "lora_B"
            else:
                ltype = "other"

            if ltype not in layer_stats:
                layer_stats[ltype] = {"count": 0, "means": [], "stds": [], "abs_means": []}
            layer_stats[ltype]["count"] += 1
            layer_stats[ltype]["means"].append(mean)
            layer_stats[ltype]["stds"].append(std)
            layer_stats[ltype]["abs_means"].append(abs_mean)

        print(f"  Total LoRA params: {total_params:,}")
        print(f"  File size: {(adapter_dir / 'adapter_model.safetensors').stat().st_size / 1024**2:.1f} MB")

        for ltype, stats in layer_stats.items():
            avg_mean = sum(stats["means"]) / len(stats["means"])
            avg_std = sum(stats["stds"]) / len(stats["stds"])
            avg_abs = sum(stats["abs_means"]) / len(stats["abs_means"])
            print(f"  {ltype} ({stats['count']} tensors):")
            print(f"    avg mean={avg_mean:.6f}, avg std={avg_std:.6f}, avg |w|={avg_abs:.6f}")

    # Compare newton vs davinci
    print(f"\n--- Weight Divergence (newton vs davinci) ---")
    newton_w = st.load_file(str(NEWTON_DIR / "adapter_model.safetensors"))
    davinci_w = st.load_file(str(DAVINCI_DIR / "adapter_model.safetensors"))

    divergences = []
    for key in sorted(newton_w.keys()):
        if key in davinci_w:
            diff = (newton_w[key].float() - davinci_w[key].float()).abs().mean().item()
            divergences.append((key.split(".")[-2] + "." + key.split(".")[-1], diff))

    divergences.sort(key=lambda x: x[1], reverse=True)
    print(f"  Total shared keys: {len(divergences)}")
    print(f"  Top 5 most divergent layers:")
    for name, div in divergences[:5]:
        print(f"    {name}: {div:.6f}")
    avg_div = sum(d for _, d in divergences) / len(divergences)
    print(f"  Average divergence: {avg_div:.6f}")

    if avg_div > 0.001:
        print(f"  PASS: Adapters learned distinct representations (div={avg_div:.6f} >> 0)")
    else:
        print(f"  WARN: Adapters may be too similar (div={avg_div:.6f})")

    return True


# ================================================================
# PHASE 2: Full Inference Test
# ================================================================
def phase2_inference_test():
    print(f"\n{'=' * 60}")
    print("PHASE 2: Full Inference Test")
    print("=" * 60)

    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import gc

    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load base model on CPU with disk offload to avoid OOM
    print("Loading base model (CPU + disk offload, float16)...")
    os.makedirs("J:/tmp/offload", exist_ok=True)
    start = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        dtype=torch.float16,
        device_map={
            "": "cpu",
        },
        low_cpu_mem_usage=True,
    )
    print(f"  Base model loaded in {time.time()-start:.0f}s")

    # Test prompt - same question, different perspectives expected
    test_prompt = "Explain why objects fall to the ground."
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer concisely in 2-3 sentences."},
        {"role": "user", "content": test_prompt},
    ]
    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(input_text, return_tensors="pt")

    gen_kwargs = dict(
        max_new_tokens=150,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

    # --- Base model response ---
    print(f"\n--- BASE MODEL (no adapter) ---")
    print(f"Prompt: {test_prompt}")
    start = time.time()
    with torch.no_grad():
        output = model.generate(**inputs, **gen_kwargs)
    base_response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Response ({time.time()-start:.1f}s): {base_response}")

    # --- Newton adapter ---
    print(f"\n--- NEWTON ADAPTER ---")
    print("Loading newton adapter...")
    start = time.time()
    newton_model = PeftModel.from_pretrained(model, str(NEWTON_DIR))
    newton_model.eval()
    print(f"  Adapter loaded in {time.time()-start:.1f}s")

    start = time.time()
    with torch.no_grad():
        output = newton_model.generate(**inputs, **gen_kwargs)
    newton_response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Response ({time.time()-start:.1f}s): {newton_response}")

    # Unload newton
    del newton_model
    import gc; gc.collect()

    # --- DaVinci adapter ---
    print(f"\n--- DAVINCI ADAPTER ---")
    print("Loading davinci adapter...")
    start = time.time()
    davinci_model = PeftModel.from_pretrained(model, str(DAVINCI_DIR))
    davinci_model.eval()
    print(f"  Adapter loaded in {time.time()-start:.1f}s")

    start = time.time()
    with torch.no_grad():
        output = davinci_model.generate(**inputs, **gen_kwargs)
    davinci_response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Response ({time.time()-start:.1f}s): {davinci_response}")

    del davinci_model
    gc.collect()

    # --- Second test: creative/philosophical prompt ---
    test_prompt2 = "What is the relationship between consciousness and the physical world?"
    messages2 = [
        {"role": "system", "content": "You are a helpful assistant. Answer concisely in 2-3 sentences."},
        {"role": "user", "content": test_prompt2},
    ]
    input_text2 = tokenizer.apply_chat_template(messages2, tokenize=False, add_generation_prompt=True)
    inputs2 = tokenizer(input_text2, return_tensors="pt")

    print(f"\n{'=' * 60}")
    print(f"TEST 2: {test_prompt2}")
    print(f"{'=' * 60}")

    # Newton on philosophical question
    print(f"\n--- NEWTON on consciousness ---")
    newton_model = PeftModel.from_pretrained(model, str(NEWTON_DIR))
    newton_model.eval()
    start = time.time()
    with torch.no_grad():
        output = newton_model.generate(**inputs2, **gen_kwargs)
    response = tokenizer.decode(output[0][inputs2["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Response ({time.time()-start:.1f}s): {response}")
    del newton_model; gc.collect()

    # DaVinci on philosophical question
    print(f"\n--- DAVINCI on consciousness ---")
    davinci_model = PeftModel.from_pretrained(model, str(DAVINCI_DIR))
    davinci_model.eval()
    start = time.time()
    with torch.no_grad():
        output = davinci_model.generate(**inputs2, **gen_kwargs)
    response = tokenizer.decode(output[0][inputs2["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Response ({time.time()-start:.1f}s): {response}")
    del davinci_model; gc.collect()

    # Cleanup
    del model
    gc.collect()

    print(f"\n{'=' * 60}")
    print("INFERENCE TESTS COMPLETE")
    print(f"{'=' * 60}")
    return True


# ================================================================
# MAIN
# ================================================================
if __name__ == "__main__":
    print("Codette LoRA Adapter Test Suite")
    print(f"PyTorch: {torch.__version__}")
    print(f"XPU: {torch.xpu.is_available()}")
    print(f"Adapters: {ADAPTER_DIR}")
    print()

    # Phase 1 is fast - always run
    phase1_weight_inspection()

    # Phase 2 needs base model download (~16GB) and lots of RAM
    print("\n" + "=" * 60)
    if "--inference" in sys.argv or "--full" in sys.argv:
        phase2_inference_test()
    else:
        print("Skipping inference test (run with --inference to enable)")
        print("  Note: Will download ~16GB base model and needs ~16GB RAM")
