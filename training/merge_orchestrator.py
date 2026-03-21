#!/usr/bin/env python3
"""Codette Merge-Only Script — Merge orchestrator LoRA into base Llama 3.1 8B.

Lightweight script that:
  1. Downloads the orchestrator adapter from HF
  2. Loads the base model on CPU (float16) to avoid GPU OOM
  3. Merges LoRA weights into base
  4. Uploads merged model to Raiff1982/codette-llama-3.1-8b-merged

Designed to run on HF Jobs with cpu-basic or a10g-small.
"""

import subprocess, sys

print("=" * 60)
print("Codette Orchestrator Merge — Installing Dependencies")
print("=" * 60)
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers>=4.40.0", "peft>=0.10.0",
    "accelerate>=0.28.0", "huggingface_hub>=0.22.0",
    "sentencepiece", "protobuf", "safetensors",
])
print("Dependencies installed.\n")

import os, gc, torch, traceback
from datetime import datetime
from huggingface_hub import HfApi, snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ── Config ──
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
ADAPTER_REPO = "Raiff1982/codette-lora-adapters"
MERGED_REPO = "Raiff1982/codette-llama-3.1-8b-merged"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

def main():
    api = HfApi(token=HF_TOKEN)

    # Step 1: Download orchestrator adapter
    print("=" * 60)
    print("Step 1: Downloading orchestrator adapter")
    print("=" * 60)
    adapter_dir = "/tmp/orchestrator_adapter"
    snapshot_download(
        repo_id=ADAPTER_REPO,
        allow_patterns=["orchestrator/*"],
        local_dir="/tmp/adapter_download",
        token=HF_TOKEN,
    )
    adapter_dir = "/tmp/adapter_download/orchestrator"

    if not os.path.exists(adapter_dir):
        print(f"ERROR: Adapter not found at {adapter_dir}")
        # Try flat structure
        adapter_dir = "/tmp/adapter_download"
        if not os.path.exists(os.path.join(adapter_dir, "adapter_config.json")):
            print("ERROR: No adapter_config.json found. Listing downloaded files:")
            for root, dirs, files in os.walk("/tmp/adapter_download"):
                for f in files:
                    print(f"  {os.path.join(root, f)}")
            return

    print(f"  Adapter ready at: {adapter_dir}")
    print(f"  Files: {os.listdir(adapter_dir)}")

    # Step 2: Load base model on CPU in float16
    print("\n" + "=" * 60)
    print("Step 2: Loading base model on CPU (float16)")
    print("=" * 60)
    print("  This avoids GPU OOM — merge is a one-time weight operation.")

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True,
        token=HF_TOKEN,
        low_cpu_mem_usage=True,
    )
    print("  Base model loaded on CPU.")

    # Step 3: Load adapter and merge
    print("\n" + "=" * 60)
    print("Step 3: Merging LoRA adapter into base model")
    print("=" * 60)

    print("  Loading orchestrator LoRA adapter...")
    merged_model = PeftModel.from_pretrained(base_model, adapter_dir)

    print("  Merging weights (this may take a few minutes on CPU)...")
    merged_model = merged_model.merge_and_unload()
    print("  Merge complete!")

    # Step 4: Save merged model
    merged_dir = "/tmp/merged_model"
    print(f"\n  Saving merged model to {merged_dir}...")
    os.makedirs(merged_dir, exist_ok=True)
    merged_model.save_pretrained(merged_dir, safe_serialization=True)

    print("  Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
    tokenizer.save_pretrained(merged_dir)

    # Model card
    model_card = f"""---
license: llama3.1
base_model: {MODEL_NAME}
tags:
  - codette
  - multi-perspective-reasoning
  - orchestrator
  - phase6+
  - lora-merged
---

# Codette Orchestrator Model (Merged)

**Base Model**: {MODEL_NAME}
**Merged Adapter**: Orchestrator (Phase 6+ framework)
**Created**: {datetime.now().isoformat()}

## Overview

This is the Codette orchestrator model — Llama 3.1 8B Instruct with the
orchestrator LoRA adapter merged into the base weights. It serves as the
central reasoning coordinator for the Codette multi-perspective AI system.

## Capabilities

- **Query Classification**: Routes queries as SIMPLE/MEDIUM/COMPLEX
- **Adapter Routing**: Selects optimal perspective combinations
- **Coherence Monitoring**: Tracks Γ field health (target: 0.4-0.8)
- **Semantic Tension**: Detects and manages ξ between perspectives
- **Multi-Agent Debate**: Coordinates rounds with conflict resolution
- **AEGIS Governance**: 6-framework ethical validation
- **Synthesis**: Integrates diverse perspectives into unified responses

## Framework Metrics

- **ψ (Psi)**: 5D state vector (psi, tau, chi, phi, lambda)
- **ξ (Xi)**: Epistemic tension = 0.6*semantic + 0.4*heuristic
- **Γ (Gamma)**: System coherence/health score

## Usage

Use as standalone model or pair with 8 perspective LoRA adapters:
- Newton (analytical physics)
- DaVinci (creative synthesis)
- Empathy (emotional intelligence)
- Philosophy (conceptual analysis)
- Quantum (probabilistic reasoning)
- Consciousness (meta-cognition / RC+ξ)
- Multi-Perspective (integration)
- Systems Architecture (design)

Adapters: https://huggingface.co/{ADAPTER_REPO}
"""
    with open(f"{merged_dir}/README.md", "w") as f:
        f.write(model_card)

    # Free memory before upload
    del base_model, merged_model
    gc.collect()

    # Step 5: Upload
    print("\n" + "=" * 60)
    print(f"Step 5: Uploading merged model to {MERGED_REPO}")
    print("=" * 60)

    try:
        api.create_repo(MERGED_REPO, private=False, token=HF_TOKEN)
        print("  Created new repo.")
    except Exception:
        print("  Repo already exists.")

    api.upload_folder(
        folder_path=merged_dir,
        repo_id=MERGED_REPO,
        token=HF_TOKEN,
    )
    print(f"  Uploaded: https://huggingface.co/{MERGED_REPO}")

    print("\n" + "=" * 60)
    print("MERGE COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
