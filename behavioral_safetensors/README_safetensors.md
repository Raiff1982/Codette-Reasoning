# Codette LoRA Adapters — safetensors (OpenVINO-compatible)

The 10 Codette perspective adapters converted from GGUF to `.safetensors`, the format required by `openvino_genai.AdapterConfig` for hot-swap and blended multi-adapter generation.

Pairs with [Raiff1982/codette-llama-3.1-8b-openvino](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-openvino).

| Adapter | Domain |
|---|---|
| newton | Physics, math, analytical reasoning |
| davinci | Creative synthesis, cross-domain invention |
| empathy | Emotional intelligence, warmth |
| philosophy | Conceptual and ethical reasoning |
| quantum | Probabilistic / uncertainty-aware |
| consciousness | Self-reflective meta-cognition |
| multi_perspective | Balanced synthesis across lenses |
| systems_architecture | Technical design, engineering |
| constraint_tracker | Format/constraint adherence |
| orchestrator | Executive routing |

## Blended generation

`openvino_genai.AdapterConfig` supports multiple adapters at per-adapter alpha weights in a single generation — perspectives mixed at the weight level rather than merged as text:

```python
import openvino_genai as ov_genai
ac = ov_genai.AdapterConfig()
ac.add(ov_genai.Adapter("newton-behavioral-lora.safetensors"), 0.7)
ac.add(ov_genai.Adapter("philosophy-behavioral-lora.safetensors"), 0.3)
cfg.adapters = ac  # weights should sum to ~1.0
```

Created by **Jonathan Harrison** (Raiff1982).
