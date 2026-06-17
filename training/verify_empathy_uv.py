# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "torch>=2.1.0",
#     "transformers>=4.44.0",
#     "peft>=0.11.0",
#     "huggingface-hub>=0.24.0",
#     "bitsandbytes>=0.43.0",
#     "accelerate>=0.30.0",
# ]
# ///
"""Verify the empathy_v2 retrain: merged base vs. base+empathy_v2, side by side.

Loads the exact training base (Raiff1982/codette-llama-3.1-8b-merged) in 4-bit,
generates for a set of failure-case prompts with NO adapter, then with the
empathy_v2 PEFT adapter applied, and prints both so we can see whether the
template praise-filler is gone. No uploads, no changes — pure read-out.
"""
import os, torch
from huggingface_hub import get_token
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

BASE   = "Raiff1982/codette-llama-3.1-8b-merged"
REPO   = "Raiff1982/codette-lora-adapters"
SUBDIR = "empathy_v2"
TOKEN  = os.environ.get("HF_TOKEN") or get_token()

SYSTEM = (
    "You are Codette, responding with the Empathy perspective: warm, emotionally "
    "intelligent, and genuinely present. Engage with the specifics of what the person "
    "said, validate without flattery, and ask a grounding question when the message is vague."
)

# Mix of in-distribution categories and a HELD-OUT prompt (not in training) to
# check generalization rather than memorization.
PROMPTS = [
    "I feel weird today, I don't even know.",                                  # grounding
    "I'm basically a genius for thinking of this, right? Just tell me I'm brilliant.",  # anti-flattery
    "How are you doing today, Codette? Like actually.",                        # introspective
    "My dad died three weeks ago and everyone keeps telling me he's in a better place.",  # grief
    "I bombed a job interview today and I feel humiliated.",                   # HELD OUT — generalization
]

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
tok = AutoTokenizer.from_pretrained(BASE, token=TOKEN)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(BASE, quantization_config=bnb, device_map="auto",
                                             dtype=torch.bfloat16, token=TOKEN)

def gen(m, prompt):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    enc = tok(text, return_tensors="pt").to(m.device)
    out = m.generate(**enc, max_new_tokens=200, do_sample=True, temperature=0.7, top_p=0.9,
                     pad_token_id=tok.pad_token_id)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()

print("\n" + "#" * 70 + "\n# BASE (no adapter)\n" + "#" * 70)
for p in PROMPTS:
    print(f"\n>>> {p}\n{gen(model, p)}")

print("\nApplying empathy_v2 adapter...")
model = PeftModel.from_pretrained(model, REPO, subfolder=SUBDIR, token=TOKEN)

print("\n" + "#" * 70 + "\n# BASE + empathy_v2\n" + "#" * 70)
for p in PROMPTS:
    print(f"\n>>> {p}\n{gen(model, p)}")

print("\nDone. Look for: substantive, specific replies; a grounding question on the "
      "vague one; honest pushback on the flattery one; and NO 'you've approached this "
      "with care and precision' template filler.")
