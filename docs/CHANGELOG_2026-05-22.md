# Changelog — 2026-05-22

RC+ξ v2.3 — Full Roster Online, Full-Synthesis Mode, Self-Overclaiming Guard,
and a Voice-Reinforced Perspective Retrain

This session brought the complete adapter roster online (orchestrator and
constraint_tracker now load as live behavioral adapters), added a one-click
full multi-perspective synthesis, closed a class of self-aggrandizing
hallucinations the guard previously scored at 0% risk, and fixed a
constraint-parser bug that could lock the model into a repetition loop. It
finishes with a voice-reinforced behavioral retrain of all eight perspectives
to harden them against convergence.

---

## Adapters

### Orchestrator + constraint_tracker now load (10 adapters, up from 8)
**`inference/codette_orchestrator.py`**

`ADAPTER_GGUF_MAP` was only iterating 8 perspectives — `orchestrator` (which
had GGUF weights on disk) was never added to the load loop, and
`constraint_tracker` had no GGUF at all. Both are now in the roster:

```python
for _name in ["newton", "davinci", "empathy", "philosophy", "quantum",
              "consciousness", "multi_perspective", "systems_architecture",
              "constraint_tracker", "orchestrator"]:
```

Startup now reports `Ready : 10 adapters`.

### constraint_tracker converted + retrained behaviorally (HF Jobs, uv)
The PEFT/safetensors constraint_tracker adapter was converted to GGUF on
Hugging Face Jobs (UV script, llama.cpp `convert_lora_to_gguf.py` against the
training base), then **retrained behaviorally** — the four permanent locks baked
into the training system prompt, like the other behavioral adapters — and
re-uploaded as `constraint_tracker-behavioral-lora-f16.gguf`. The orchestrator
prefers the behavioral version automatically.

---

## Features

### Full Adapter Synthesis — ◈ SYNTHESIZE ALL
**`inference/codette_orchestrator.py`, `inference/codette_server.py`,
`inference/static/{index.html,app.js,style.css}`**

A new control runs **every reasoning perspective at once** and synthesizes them
into a single answer, instead of the router picking 2–3. Implemented via a
`__all__` sentinel in `route_and_generate` that builds a route across all loaded
perspectives, a `full_synthesis` flag plumbed through the JSON / multipart / SSE
request paths, and a styled button in the controls row. The adapter dropdown also
gained `constraint_tracker` and `orchestrator`.

---

## Hallucination Guard

### Signal 7 — Self-Overclaiming detection
**`reasoning_forge/hallucination_guard.py`**

A grandiose self-description ("perfect stability near absolute perfection
(eps=0.998) … never achieved by any other system in my vast knowledge domain")
previously scored **0% hallucination risk** — none of the six existing signals
covered self-aggrandizement. Added a seventh signal catching three patterns:

- **Superiority claims** — "never been achieved", "no other system", "unmatched",
  "vast knowledge domain", …
- **Absolute self-descriptions** — "absolute perfection", "perfect stability",
  "flawless", "near perfection", …
- **Fabricated self-metrics** — a precise metric like `eps=0.998`, **only** when
  wrapped in perfection/superiority framing (so genuine technical mentions of
  eps/psi are not penalized).

The same grandiose output now scores **88% risk → INTERRUPT**, while grounded
self-reflection and legitimate `eps` mentions stay clean.

### Reliability scan now covers every displayed perspective
**`inference/codette_server.py`**

`_analyze_response_reliability` was only scanning the synthesized text. In
multi-perspective mode the grandiosity lived in an individual perspective
(`result["perspectives"]`), so it was never scanned. The scan now covers the
synthesis **plus** each perspective shown via "Show N perspectives", so a problem
confined to one lens still lowers the reliability score.

### Fixed a latent crash in `_check_contradictions`
The `always X … except not X` contradiction pattern used a `\1` backreference
inside a *standalone* pattern, raising `re.PatternError` on any response
containing "always <word>". The error was swallowed by the caller's try/except,
silently disabling contradiction detection. It now substitutes the captured word
correctly.

---

## Prompts

### Consciousness adapter — anti-grandiosity guardrail
**`inference/codette_orchestrator.py`**

The consciousness system prompt now explicitly forbids perfection/absolute/
superiority language and inventing precise self-metrics, instructing it to
reflect plainly with acknowledged uncertainty.

### Synthesis — perspectives framed as Codette's own lenses
**`inference/codette_orchestrator.py`**

The synthesis prompt described perspectives as external parties that "weighed in"
and asked the model to "note where perspectives complement or tension each
other" — producing third-person attribution ("as the Philosophy Perspective
suggests"). It's reframed: the perspectives are *her own internal reasoning
notes*, and she must write **one first-person answer** with no attribution to
named lenses or "users". The internal-note labels changed from
`**NEWTON PERSPECTIVE:**` to `[your newton lens — internal note]`.

---

## Bug Fixes

### Constraint parser captured ordinary negations → repetition loop
**`reasoning_forge/constraint_tracker.py`**

The format-rule pattern `((?:no|avoid)\s+\w+)` matched **any** "no <word>", so
"be detailed **no word** constraint" became a stored constraint
`Format: no word`, pinned as a session landmark and injected every turn — forcing
terse, near-identical answers that memory recall then reinforced into a loop.
Even "no constraints needed" was re-captured as another constraint.

Fix: restricted the negated-format pattern to real formatting targets (bullets,
lists, markdown, json, headers, emoji, tables, …) and added a
`CONSTRAINT_NEGATION_PATTERNS` guard so explicit declines ("no constraints",
"no word limit", "without constraints", "ignore constraints") derive **zero**
constraints from that turn.

### Session list survives a transient drive disconnect
**`inference/codette_session.py`**

The project lives on the `J:` drive, which can briefly disconnect. When it did,
`list_sessions()` threw `sqlite3.OperationalError: unable to open database file`
on every `/api/sessions` page-load. It now degrades gracefully (logs a warning,
returns `[]`) instead of 500-ing the UI.

### UI — Recent Sessions list clipped at the bottom
**`inference/static/{index.html,style.css}`**

The Recent Sessions section was a `flex:1` child with `overflow-y:auto` but no
`min-height:0`, so its scroll never engaged and the last session was clipped at
the panel edge. Added `min-height:0` and a `#session-list` bottom padding.

---

## Tooling

### Full benchmark suite can target the live llama.cpp server
**`benchmarks/full_benchmark.py`**

Added `--backend server` (calls the running `codette_server.py` at
`/api/chat`, with `--max-adapters`, `--timeout`, and `--verbose`) alongside the
existing Ollama backend, so the all-in-one 9-category suite can score the actual
llama.cpp + LoRA-hot-swap system being shipped. Health check, summary labels, and
the `.json`/`.md` reports are now backend-aware.

---

## Retrain

### Voice-reinforced behavioral retrain — all 8 perspectives (HF Jobs, uv)
**`training/train_perspectives_behavioral.py`**

On a substantive prompt the perspectives differentiate well, but identity-style
prompts plus heavy shared scaffolding could collapse them onto near-identical
text. To harden against this, each perspective is retrained on its **own**
`NAME_reasoning.jsonl` dataset (≈820 distinct examples) with its **distinct
persona + the four locks** in the system prompt — instead of the prior recipe
(generic lock-compliance + a one-line prompt) that homogenized them. Each
adapter is trained, converted to GGUF, and uploaded as
`NAME-behavioral-lora-f16.gguf`. Run on an A10G via a UV job.
