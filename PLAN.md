# Codette Multi-Adapter Inference + Chat System — Implementation Plan

## Overview

Build three things inside `codette-training-lab`:

1. **HF Upload Scripts + Model Cards** — publish each trained adapter to HuggingFace
2. **Multi-Adapter Inference Engine** — loads Llama 3.1 8B + dynamically switches between 8 LoRA adapters
3. **Gradio Real-Time Chat App** — interactive UI to test any adapter with streaming responses, deployable to HF Spaces

---

## Architecture

```
codette-training-lab/
├── inference/                    ← NEW
│   ├── __init__.py
│   ├── model_loader.py          ← Core: loads base model + all adapters via PEFT
│   ├── multi_adapter_engine.py  ← Orchestrates multi-perspective generation
│   └── chat_app.py              ← Gradio UI with streaming chat
├── scripts/
│   ├── upload_adapters.py       ← NEW: push adapters to HF Hub
│   └── model_card_template.md   ← NEW: model card for each adapter
└── app.py                       ← NEW: HF Spaces entry point (launches chat_app)
```

---

## Part 1: HF Upload Scripts + Model Cards (2 files)

### `scripts/upload_adapters.py`
- Scans `adapters/` directory for trained adapter folders
- For each adapter: creates an HF repo `Raiff1982/codette-{adapter_name}`, uploads safetensors + adapter_config.json + tokenizer
- Generates a model card from template with correct metadata (base_model, datasets, pipeline_tag, etc.)
- Supports `--adapter newton` to upload one or `--all` to upload all 8

### `scripts/model_card_template.md`
- Standard HF model card with YAML frontmatter
- Fields: base_model, datasets, tags, pipeline_tag, license
- Sections: description, intended use, training details, how to use

---

## Part 2: Multi-Adapter Inference Engine (2 files)

### `inference/model_loader.py` — `CodetteModelLoader`
- Loads `meta-llama/Llama-3.1-8B-Instruct` in 4-bit QLoRA (same config as training)
- Uses PEFT's `PeftModel.from_pretrained()` to load the first adapter
- Uses `model.load_adapter("path", adapter_name="name")` for each additional adapter
- Exposes `set_active_adapter(name)` to switch between loaded adapters at runtime
- Manages tokenizer (Llama 3.1 chat template with `apply_chat_template`)
- GPU memory footprint: ~5GB base + ~20MB per adapter = ~5.2GB total (fits A10G/T4/consumer GPUs)

### `inference/multi_adapter_engine.py` — `CodetteEngine`
- Takes a `CodetteModelLoader` instance
- **Single-perspective mode**: user picks one adapter, generates with it
- **Multi-perspective mode**: runs the query through N selected adapters, collects responses, synthesizes
- **Synthesis**: combines multiple adapter responses into one unified answer (using the multi_perspective adapter or a template)
- Streaming support via `TextIteratorStreamer` for real-time token output
- Generation params: temperature, top_p, max_tokens, repetition_penalty — all configurable per adapter from `adapter_registry.yaml`

---

## Part 3: Gradio Chat Interface (2 files)

### `inference/chat_app.py` — `create_chat_app()`
- **Chat Tab**: streaming chatbot with adapter selector dropdown
  - Dropdown: "Newton", "DaVinci", "Empathy", "Philosophy", "Quantum", "RC-XI", "Multi-Perspective", "Systems", "All (synthesized)"
  - Slider controls: temperature, max tokens, top_p
  - Streaming output token-by-token
  - Chat history with system/user/assistant roles
- **Compare Tab**: side-by-side adapter comparison
  - Select 2-4 adapters, send same prompt, see responses side by side
  - Quality scores from ReasoningMetrics displayed per response
- **Status Tab**: model info, loaded adapters, GPU memory, adapter configs
- Theme: `gr.themes.Soft()` matching existing Codette aesthetic

### `app.py` (project root) — HF Spaces entry point
- Minimal: imports and launches `create_chat_app()`
- Loads adapters from HF Hub (for Spaces) or local `adapters/` directory
- Configurable via env vars: `CODETTE_ADAPTER_SOURCE=hub|local`, `HF_TOKEN`, `ADAPTER_NAMES`

---

## Key Design Decisions

1. **PEFT multi-adapter** — PEFT natively supports loading multiple LoRA adapters on one base model and switching with `set_adapter()`. No need to load 8 separate models.

2. **Streaming** — `TextIteratorStreamer` from transformers, threaded generation, yielded to Gradio chatbot for real-time display.

3. **Chat template** — Llama 3.1 uses `<|begin_of_text|><|start_header_id|>system<|end_header_id|>...` format. We use `tokenizer.apply_chat_template()` which handles this automatically.

4. **System prompts from registry** — Each adapter's system prompt comes from `adapter_registry.yaml`, injected as the system message in chat.

5. **HF Spaces compatible** — The app.py + requirements.txt are structured so deploying to a HF Space with GPU runtime works out of the box.

---

## File Count: 7 new files

| File | Purpose | ~Lines |
|------|---------|--------|
| `inference/__init__.py` | Package exports | 10 |
| `inference/model_loader.py` | Load base + adapters | 200 |
| `inference/multi_adapter_engine.py` | Generation orchestration | 250 |
| `inference/chat_app.py` | Gradio UI | 350 |
| `app.py` | HF Spaces entry point | 50 |
| `scripts/upload_adapters.py` | Push to HF Hub | 180 |
| `scripts/model_card_template.md` | Model card template | 80 |

**Total: ~1,120 lines of new code**

---

## Execution Order

1. Upload scripts + model cards (so adapters are on HF when chat loads)
2. Model loader (core inference)
3. Multi-adapter engine (orchestration)
4. Chat app + entry point (UI)
5. Test locally, then deploy to HF Space
