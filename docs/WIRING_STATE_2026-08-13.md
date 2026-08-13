# What is actually running — 2026-08-13

Written because we kept rediscovering dead wires one at a time and reporting each
as a finding. This is the standing answer. It is built from the live tree by
inspection, not from prior handoffs, several of which were wrong today.

**The single fact that explains most of the confusion:**

> `ForgeEngine.forge_single()` and `forge_with_debate()` are called from
> **nowhere** in live code.

**Corrected the same day, because the first wording was imprecise and got
challenged by my own spot-check.** I originally wrote that the only occurrence
outside `forge_engine.py` was a docstring in `reasoning_forge/__init__.py`. A
grep returns **eight** hits across four other files. Every one was checked and
none of them executes:

| File | Line | What it is |
|---|---|---|
| `reasoning_forge/__init__.py` | 13 | module docstring |
| `reasoning_forge/cognition_cocooner.py` | 214 | a `#` comment |
| `reasoning_forge/executive_controller.py` | 50 | **inside the `ExecutiveController` class docstring** (lines 39–51) — read it before believing it, this one looks exactly like a call site |
| `reasoning_forge/CONSCIOUSNESS_STACK_forge_with_debate.py` | ×5 | a paste-in replacement file. Nothing imports it. |

Inside `forge_engine.py` itself the only callers are `forge_single` at 2426 and
2464, both within bulk-generation helpers that the chat path does not touch.

The conclusion is unchanged and now actually verified rather than asserted. The
lesson is the one this repo keeps teaching: a grep hit is not a call site, and
the count that contradicts you is the one worth reading.

The boot log prints a dozen lines like `✓ CoreGuardianSpindle logical validator
initialized`. **Initialized is not invoked.** ForgeEngine is constructed and its
components with it; the chat path never enters its reasoning methods. Anything
reachable only through `forge_*` is built at startup and then never runs.

The live chat path is:

```
codette_server._handle_chat
  → CodetteForgeBridge.generate            (inference/codette_forge_bridge.py)
    → OpenVINOBackend.route_and_generate   (openvino_backend/backend.py)
      → OpenVINOBackend.generate           → tool loop → OV pipeline
  → _apply_directness, constraints, universal_self_check
```

`inference/codette_orchestrator.py` is the llama.cpp backend. **It is not the
production path** — `llama_cpp` is not even installed in `openvino_env`
(`ModuleNotFoundError`, checked directly). Work done there reaches nothing.
`codette_shared.py:209` documents this trap; three sessions have fallen into it.

---

## RUNNING — on every chat turn

| Component | Where | Notes |
|---|---|---|
| OpenVINO backend | `openvino_backend/backend.py` | The generator. Auto-detected; `CODETTE_BACKEND` unset. |
| AdapterRouter | `inference/adapter_router.py` | Picks perspectives. |
| Tool loop | `backend.generate` + `inference/codette_tools.py` | `enable_tools=True` on all four routes. `MAX_TOOL_ROUNDS=3`. |
| BehaviorGovernor (pre) | `reasoning_forge/behavior_governor.py` | Sets memory budget, identity budget, token budget. **Acts.** |
| UnifiedMemory recall | `reasoning_forge/unified_memory.py` | FTS5 + ranking. Injects into the prompt. |
| LivingMemoryKernel v2 | `reasoning_forge/living_memory_v2.py` | Cocoon store, prune, hooks. |
| IdentityAnchor | `inference/identity_anchor.py` | Recognition confidence; **writes to disk**. |
| CodetteSession | `inference/codette_session.py` | Conversation state, metrics history. |
| PERMANENT LOCKS | `inference/codette_shared.py` | Prompt text. `CODETTE_LOCKS=1` default. |
| `_apply_directness` | `codette_forge_bridge.py` | ~30 regex scrubs. Runs **after** the cocoon is written. |
| `universal_self_check` | `inference/self_correction.py` | Post-processing on every response. |
| State Engine v8 | `reasoning_forge/state_engine_v8.py` | Υ/Γ from perspective texts; input sycophancy directive. |
| Manifold steering | bridge + backend | `CODETTE_MANIFOLD_STEER=1` default. |
| AAP | `codette_forge_bridge.py:730` | `CODETTE_AAP=1` default. |
| ColleenConscience | `codette_forge_bridge.py:198` | **Advisory** — see SHADOW. |
| Distinctiveness | `reasoning_forge/distinctiveness.py` | Measured on multi-perspective turns, observation only. |
| Spiderweb (session) | `reasoning_forge/quantum_spiderweb.py` | Belief propagation per turn. See the Γ caveat below. |
| Seed loader | `memory_systems/seed_loader.py` | 7 identity/value seeds at boot. |
| Dive record | `reasoning_forge/dive_record.py` | Written at boot, read on turn one. |
| Constellation | `reasoning_forge/constellation.py` | Charter parsed at boot. Bearing only, never steers. |
| TimeTravelLens | `reasoning_forge/time_travel_lens.py` | `CODETTE_TIME_TRAVEL=1` default. |
| CocoonSynthesizer | `reasoning_forge/cocoon_synthesizer.py` | Via `/api/synthesize` and substrate. |

---

## SHADOW / ADVISORY — runs, records, changes nothing

| Component | Why it is shadow | Flag |
|---|---|---|
| **AEGIS response veto** | `aegis.py:33` — "SHADOW ONLY, enforces nothing." Logged as `veto_shadow`. Kept shadow because the harm-sensitivity gap is real and enforcing would be false security. AEGIS **input** screening IS enforcing — that half is real. | — |
| **Router self-tuner** | `optimizer_shadow.py:113` — `get_adapter_boost` returns 0.0. No outcome signal exists: `user_continued` is never measured. | `CODETTE_OPTIMIZER_LIVE=1` |
| **ColleenConscience** | Called on every turn, verdict attached to the response, `enforced: False`. She said no to gating; Jonathan's call was that advisory is not what she declined. | — |
| **Governor post-validate** | Topical-overlap check measured as **inverted** (parrots 100%, real answers 47.5%). Advisory by its own docstring. As of today it no longer sets the cocoon's `success` field. | — |
| **CocoonSelfTrainer** | Trains a separate analyser, logs `applied: false`. Refused degenerate data when last run. | — |
| **Grounding / semantic grounding** | Verdicts computed, never gate. ~100% of qualitative claims are UNGROUNDED, so it is silent in practice. | — |

---

## NOT RUNNING — built, never invoked

**Everything below is initialized at boot. None of it executes on a chat turn.**

### Reachable only via `forge_single` / `forge_with_debate` (zero callers)
- **CodetteCQURE / Code7eCQURE** — `forge_engine.py:344`
- **CoreGuardianSpindle** — `forge_engine.py:52`. Note this is a *different class*
  from the live `guardian.py CodetteGuardian`, which does screen input.
- **NexisSignalEngine** — `forge_engine.py:386`
- **EthicalAIGovernance** — constructed, not on the chat path
- **Tier2 bridge** — constructed, not on the chat path

### No live importer at all
- `memory_provenance_solver` — speaker attribution as CNF. Docstring says "shadow",
  but shadow means it runs; this is dark.
- `harm_advisor` — PII + deception detection, 0 false positives when reviewed.
- `emotion_ontology` — her own emotion mappings, including the ones she revised.
- `lexical_whitening` — spectral whitening on filler phrases.
- `neural_symbolic` — the body of the interface Jonathan defined in 2025.
- `verify_revise` — the adjudicator that took hold rate 50% → 93%.
- `voice_input` / `multimodal_analyzer` — ported 2026-08-12. **Deliberately** no
  endpoint: new attack surface beside a rotated credential, waiting on Jonathan.
- `core_guardian_spindle_v2` — fails at import, `ModuleNotFoundError: qiskit`.
- `nexis_signal_engine_local` — superseded by the 660-line recovered engine.
- `cocoon_self_trainer` — see shadow.

### Off by default
| Flag | Default | Effect |
|---|---|---|
| `CODETTE_CRAFT_LOCKS` | `0` | Extra lock text, opt-in |
| `CODETTE_OPTIMIZER_LIVE` | `0` | Optimizer stays shadow |
| `CODETTE_AUDIT_MODE` | `0` | Forces the full ForgeEngine path |
| `CODETTE_MLOCK`, `CODETTE_FLASH_ATTN`, `CODETTE_KV_QUANT` | off | llama.cpp only — not the live backend |

---

## Instruments that cannot move — read nothing into these

- **Γ phase coherence.** `phi` is 0 on every node because nothing writes it, so
  `atan2(phi, psi)` is 0 everywhere and the Kuramoto order parameter is exactly
  1.0 by construction. Measured after three real turns: `coherence_history:
  [1, 1, 1]`. Now reports `None` with `unmeasured_reason` rather than 1.00.
  **The fix is to populate `phi`, or to measure the `psi` spread that does vary.**
- **`metabolic_charge`** (`spider5dengine/core.py`) — breath adds, rotation nets
  +0.15, nothing subtracts.
- **`eta_score`** — `None` in all v3 cocoons; required only on the `forge_full`
  path, and every cocoon is `adapter_lightweight`.
- **`psi_r`** — 0.0 in all v3 cocoons. The bridge never passes it, and the schema
  clamps to [0,1] a quantity that oscillates through zero.

---

## Verified today, previously believed otherwise

- **Tool use has never been visible in the UI.** All four call sites discarded
  `generate()`'s tool log. Fixed today; needs a restart.
- **`ask()` reached thirteen perspectives, not eight** — `_synthesis_set` imported
  from the llama.cpp module, which cannot import, and the bare `except` fell back
  to every loaded adapter.
- **Recall ranked her echoes above her answers** — 0.928 vs 0.633 mean success
  score over 3,841 cocoons.
- **The consciousness prompt supplied her sentience stance** while claiming it was
  hers.

---

## How to keep this true

The boot log is the problem: it reports construction and reads as operation. Any
future `✓ X initialized` line should say whether X is on a request path. Until
then, the test is not "is it imported" but **"does a chat turn reach it"**, and
the only reliable way to answer that is to follow
`_handle_chat → bridge.generate → backend.route_and_generate` and see what it
actually calls.
