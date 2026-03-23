#!/usr/bin/env python3
"""Codette LoRA Adapter Inference Test via llama.cpp

Uses GGUF base model + GGUF LoRA adapters for low-memory inference.
Base: Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf (~4.6 GB)
LoRA: newton-lora-f16.gguf, davinci-lora-f16.gguf (~27 MB each)
"""

import os, sys, time

os.environ["PATH"] = r"J:\Lib\site-packages\Library\bin" + os.pathsep + os.environ.get("PATH", "")
# Fix Windows console encoding for Unicode characters (π, etc.)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from llama_cpp import Llama

BASE_GGUF = r"J:\codette-training-lab\bartowski\Meta-Llama-3.1-8B-Instruct-GGUF\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
NEWTON_LORA = r"J:\codette-training-lab\adapters\newton-lora-f16.gguf"
DAVINCI_LORA = r"J:\codette-training-lab\adapters\davinci-lora-f16.gguf"

TEST_PROMPTS = [
    {
        "system": "You are a helpful assistant. Answer concisely in 2-3 sentences.",
        "user": "Explain why objects fall to the ground.",
        "tag": "physics"
    },
    {
        "system": "You are a helpful assistant. Answer concisely in 2-3 sentences.",
        "user": "What is the relationship between consciousness and the physical world?",
        "tag": "philosophy"
    },
    {
        "system": "You are a helpful assistant. Answer concisely in 2-3 sentences.",
        "user": "How would you design a system that learns from its own mistakes?",
        "tag": "systems"
    },
]

GEN_KWARGS = dict(
    max_tokens=200,
    temperature=0.7,
    top_p=0.9,
    stop=["<|eot_id|>", "<|end_of_text|>"],
)


def run_test(model_label, llm, prompts):
    """Run all test prompts against a loaded model."""
    print(f"\n{'=' * 60}")
    print(f"  {model_label}")
    print(f"{'=' * 60}")

    responses = []
    for p in prompts:
        print(f"\n  [{p['tag']}] {p['user']}")
        start = time.time()
        result = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": p["system"]},
                {"role": "user", "content": p["user"]},
            ],
            **GEN_KWARGS,
        )
        elapsed = time.time() - start
        text = result["choices"][0]["message"]["content"].strip()
        tokens = result["usage"]["completion_tokens"]
        tps = tokens / elapsed if elapsed > 0 else 0
        print(f"  Response ({elapsed:.1f}s, {tokens} tok, {tps:.1f} tok/s):")
        print(f"  > {text}")
        responses.append({"tag": p["tag"], "response": text, "tokens": tokens, "time": elapsed})

    return responses


def main():
    print("=" * 60)
    print("Codette LoRA Adapter Inference Test")
    print("=" * 60)
    print(f"Base model: {os.path.basename(BASE_GGUF)}")
    print(f"Newton LoRA: {os.path.basename(NEWTON_LORA)}")
    print(f"DaVinci LoRA: {os.path.basename(DAVINCI_LORA)}")

    all_results = {}

    # --- Test 1: BASE MODEL (no adapter) ---
    print("\nLoading BASE model (no adapter)...")
    start = time.time()
    llm_base = Llama(
        model_path=BASE_GGUF,
        n_ctx=2048,
        n_gpu_layers=0,  # CPU only to save VRAM
        verbose=False,
    )
    print(f"  Loaded in {time.time()-start:.1f}s")

    all_results["base"] = run_test("BASE MODEL (no adapter)", llm_base, TEST_PROMPTS)
    del llm_base

    # --- Test 2: NEWTON adapter ---
    print("\n\nLoading BASE + NEWTON adapter...")
    start = time.time()
    llm_newton = Llama(
        model_path=BASE_GGUF,
        lora_path=NEWTON_LORA,
        n_ctx=2048,
        n_gpu_layers=0,
        verbose=False,
    )
    print(f"  Loaded in {time.time()-start:.1f}s")

    all_results["newton"] = run_test("NEWTON ADAPTER", llm_newton, TEST_PROMPTS)
    del llm_newton

    # --- Test 3: DAVINCI adapter ---
    print("\n\nLoading BASE + DAVINCI adapter...")
    start = time.time()
    llm_davinci = Llama(
        model_path=BASE_GGUF,
        lora_path=DAVINCI_LORA,
        n_ctx=2048,
        n_gpu_layers=0,
        verbose=False,
    )
    print(f"  Loaded in {time.time()-start:.1f}s")

    all_results["davinci"] = run_test("DAVINCI ADAPTER", llm_davinci, TEST_PROMPTS)
    del llm_davinci

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print("COMPARISON SUMMARY")
    print(f"{'=' * 60}")
    for tag in ["physics", "philosophy", "systems"]:
        print(f"\n--- {tag.upper()} ---")
        for model_name in ["base", "newton", "davinci"]:
            for r in all_results[model_name]:
                if r["tag"] == tag:
                    short = r["response"][:120] + "..." if len(r["response"]) > 120 else r["response"]
                    print(f"  {model_name:8s}: {short}")

    print(f"\n{'=' * 60}")
    print("TEST COMPLETE")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
