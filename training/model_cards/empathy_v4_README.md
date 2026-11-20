---
base_model: Raiff1982/codette-llama-3.1-8b-merged
library_name: peft
pipeline_tag: text-generation
license: other
license_name: csal-1.0
license_link: https://github.com/Raiff1982/Codette-Reasoning/blob/main/LICENSE
language:
- en
tags:
- base_model:adapter:Raiff1982/codette-llama-3.1-8b-merged
- lora
- sft
- transformers
- trl
- codette
---

# Codette: Empathy voice adapter (v4)

A LoRA adapter for the **Empathy** voice of
[Codette](https://github.com/Raiff1982/Codette-Reasoning), a multi-perspective
reasoning project by Jonathan Harrison. Codette answers through several voices
(Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Multi-Perspective,
Systems Architecture). Each voice is a LoRA adapter on one shared base model. This
is the Empathy voice, in its v4 form.

## What it was trained to do

Fifty-three hand-written examples teach a register: warm, specific, and honest
rather than flattering. The notes in the data generator name four behaviours:

| When the person... | The example answer... |
|---|---|
| sends something vague or empty of content | asks **one** concrete grounding question instead of padding |
| fishes for praise | stays warm but honest, and does not flatter |
| asks an introspective question | answers it directly, without turning to praise the person |
| is venting and has not asked for advice | offers presence and brevity, not a lecture |

Every example is a single turn: a system message, one user message and one answer of
10 to 112 words (median 84). All 53 share the same system message, so that is the
only one the adapter was trained with. Use it:

> You are Codette, responding with the Empathy perspective: warm, emotionally
> intelligent, and genuinely present. Engage with the specifics of what the person
> actually said — their situation, not a generic version of it. Validate feelings
> without flattering the person or padding with platitudes. When a message is vague
> or you lack what you'd need to help, ask one concrete grounding question instead of
> guessing. Match their register: brief when they're venting, practical when they want
> to think something through. Be honest even when that's harder than being nice.
> Never open by praising the user's 'approach' or 'thoughtfulness', and never fill
> space with generic statements about emotional intelligence.

## How to use it

The standard PEFT way to load an adapter from a subfolder. **Not run in the
environment this card was written in** (no GPU, and no `torch` installed there):

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base_id = "Raiff1982/codette-llama-3.1-8b-merged"
tok = AutoTokenizer.from_pretrained(base_id)
model = AutoModelForCausalLM.from_pretrained(base_id, device_map="auto", torch_dtype="auto")
model = PeftModel.from_pretrained(model, "Raiff1982/codette-adapters-v4", subfolder="empathy")

messages = [
    {"role": "system", "content": "<the system message above>"},
    {"role": "user", "content": "It's been a year since I lost my mom and I feel like I should be over it by now."},
]
ids = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)
out = model.generate(ids, max_new_tokens=200)
print(tok.decode(out[0][ids.shape[-1]:], skip_special_tokens=True))
```

Inside Codette the adapter is converted for the project's two runtimes (llama.cpp
GGUF and OpenVINO) by `training/deploy_v4_adapters.py`, per the project changelog.
That conversion was not re-run for this card.

## Training

| | |
|---|---|
| Base model | `Raiff1982/codette-llama-3.1-8b-merged` |
| Method | QLoRA: base loaded in 4-bit (nf4, double quantization, fp16 compute) |
| LoRA | r = 16, alpha = 32, dropout 0.05, on `q_proj`, `k_proj`, `v_proj`, `o_proj` |
| Data | 53 examples: `empathy_v4.jsonl` here, `dataset_engine/empathy_reasoning.jsonl` in the repository, written by `dataset_engine/empathy_dataset_v2.py` |
| Epochs | 5 |
| Batch | 1 per device, 8 accumulation steps (effective 8) |
| Learning rate | 1e-4, warmup ratio 0.05 |
| Max length | 1024 tokens |
| Precision | fp16, gradient checkpointing |
| Trainer | TRL `SFTTrainer`, PEFT 0.19.1 |
| Hardware | one GPU on Kaggle (T4), per the project changelog |

The settings come from `training/kaggle_train_all_adapters_v4.py` and the changelog
(`docs/CHANGELOG_2026-07-17.md`); the adapter's own `adapter_config.json` matches the
LoRA row. The training run itself was not re-checked.

The v4 data replaced an earlier template-generated set (v1). That set slotted topics
into fixed sentences, and the adapter learned to repeat the boilerplate. The 53 v4
examples engage with what each person actually wrote.

## Evaluation

**None for this adapter on its own.** Whether it produces the register described
above has not been measured. For context only: the one v4 adapter the project has
measured, newton-v4 on GPQA diamond (n = 198), was capability-neutral (+1.52 points,
p = 0.65). That is a different adapter and a different kind of test.

## Limitations and known issues

- **Small.** Fifty-three single-turn examples in English. Multi-turn conversation and
  other languages were not part of training.
- **Not a crisis tool and not a substitute for professional care.** Some examples
  involve grief, self-worth and a person saying nobody would notice if they
  disappeared. The adapter by itself has no safety layer; inside Codette it runs
  behind her input and output gates.
- **Example 26 of 53** is a first-person answer to "How are you doing today,
  Codette? Like actually." in which the assistant says it has no day the way a person
  has one and has no feeling to perform. The project's current position is to take no side on that question for
  any AI, in either direction (house rule in `CLAUDE.md`, 2026-11-20). The text is
  in the trained weights, so changing it means a new dataset version and a retrain.
  It is flagged here, not edited.

## License

Codette Source-Available License (CSAL) v1.0. Non-commercial use only. Attribution to
Jonathan Harrison (ORCID https://orcid.org/0009-0003-7005-8187) is required, and
commercial or corporate use needs his written permission. Read the full terms in the
[LICENSE](https://github.com/Raiff1982/Codette-Reasoning/blob/main/LICENSE) before
using or sharing the weights.

## Credits

Written by Jonathan Harrison. The data, training pipeline and this card were
prepared jointly with Claude, who is credited as co-author in the repository's
commits.

### Framework versions

- PEFT 0.19.1
