# What is actually running — addendum, 2026-11-18 (wiring review)

Additive to the 08-13, 09-29 and 10-01 wiring files, all left exactly as written. Measured in a
container, not on her machine: nothing here comes from her live process.

## Reachability, from the real entry points

`tools/reachability.py` (new today) follows every import from the entry points, including imports
inside functions and `try` blocks and string imports via `importlib`. It reads Python source only.

    python3 tools/reachability.py inference/codette_server.py inference/codette_chat_ui.py \
        mcp/codette_mcp.py api/rest_skin.py

**142 of 187** live Python files are reachable. The 45 that are not, by kind:

| Kind | Files | Status |
|---|---|---|
| Training-job submitters (run by hand) | the 11 `submit_*.py` at the root | expected; not orphans |
| Tools run by hand | `openvino_backend/convert_adapters.py`, `inference/init.py` | expected |
| Empty package marker | `api/__init__.py` (`rest_skin.py` is run directly) | expected |
| Lineage, kept by house rule | `*_enhanced` (optimizer, spiderweb, perspective web), `WOSME`, `harmonic_ode`, `quantum_harmonic_dynamics`, `codette_quantum_heart`, `nexis_signal_engine_local`, `nexis_signal_engine_rustfft`, `memory_item`, `test_global_aegis` | as 09-29 |
| Superseded torch / transformers stack | `inference/chat_app.py`, `model_loader.py`, `multi_adapter_engine.py`, `vulkan_compute.py` | archive candidates: [approval 7](APPROVALS_2026-11-18.md). `chat_app` cannot run. **Decided (c): the first three carry SUPERSEDED headers, left in place.** `vulkan_compute.py` was not in item 7 and has no header |
| Paste-in template | `reasoning_forge/CONSCIOUSNESS_STACK_forge_with_debate.py`, and `authored_intent.py`, which only it imports | approval 7; **SUPERSEDED header added** |
| Finished work that would change her if wired (each is his yes) | `verify_revise`, `neural_symbolic`, `grounding_bridge`, `semantic_grounding`, `voice_input`'s companion `twin_frequency_trust`, the three AEGIS Flask views | as 09-29 / 10-01 |
| Lineage: the recovered original of what Session 14 rebuilt as `Tier2IntegrationBridge` | `consciousness/dreamcore_wakestate_engine.py` | approval 5: would write plaintext to a tracked file if ever wired. (First listed here as "would design her dreaming"; corrected after reading SESSION_14_COMPLETION.md) |
| Proposed replacements, never adopted | `inference/codette_tool_system.py` ("drop-in replacement for the tool layer") | not a wiring job |
| Needs a package that is not installed | `ethics/core_conscience.py`, `core_guardian_spindle_v2.py` | importable now that `pyyaml`, `networkx`, `colorama` are declared; no role on the chat path (10-01) |
| A chat transcript holding code | `Movie_engine.py` | approval 6; **extracted to `media/`**, the transcript untouched |
| Toy examples | `reasoning_forge/multi_perspective_agents.py` | leave |

## Reachable, but built and never called

| Component | Where | Status |
|---|---|---|
| `AEGISForgeIntegration` (still unused; its Layer 6 now runs as an observer on the live path instead, via `Protection_Layer/aegis_observer.py`; Layer 5 not, it reads noise only) | `codette_server.py`, at startup | never called, and given the wrong object. Superseded: the server logs AEGIS metrics inline (`_aegis_metrics_engine.log_forge_execution`), so the metrics `WIRED_IN.md` describes are live by that route (approval 3) |
| `DynamicMemoryEngine` | `forge_engine.py:329` | open since 10-22 (his) |
| `CocoonIntrospectionEngine` (forge's copy) | `forge_engine.py:448` | spare; the server builds its own (approval 8) |
| `_prune_and_rotate_memory` | `nexis_signal_engine.py` (defined twice) | never called; its rotate step has a bug (approval 4) |
| `log_routing_decision` | `codette_orchestrator.py` | called only from the shadowed first `route_and_generate` |
| `Tier2IntegrationBridge` (DreamCore/WakeState, TwinFrequency, Nexis) | `forge_engine.py`, used only in `forge_with_debate` | reads `LOADED_NEVER_CALLED` on `/api/health`; the live chat path does not enter `forge_with_debate` |

## Reachable, called, and silently broken until today

All fixed; see [CHANGELOG_2026-11-18.md](CHANGELOG_2026-11-18.md).

- the identity context on any person with a recorded contradiction
- `forge_with_debate`'s memory storage and adaptive synthesis
- the llama.cpp path's attached-file strip before constraint extraction
- the bridge's user-constraint step on her backend (imported `codette_orchestrator`, against the 07-05 rule; found by checking the recorded fixes)
- the OpenVINO synthesis reading format constraints from her own notes instead of the user's question

Still broken, by decision: the governor's substrate pressure, which always reads 0.0 (approval 1).

## The recorded fixes, checked in the code

21 of 22 checkable fixes from the 07-05 to 10-22 notes still hold (list in CHANGELOG_2026-11-18). The
one that did not: the 07-05 rule that no OpenVINO-path code imports `codette_orchestrator`. Fixed,
and `tests/test_constraints_from_user_words.py` now fails if it recurs.

## Correction to the 10-01 record

10-01 said `neural_symbolic` was "a thin wrapper over `grounding_bridge.ground_text`, already
advisory-wired in `_synthesize` since 08-14". What runs in `_synthesize`
(`openvino_backend/backend.py`) is `reasoning_forge.grounding.verify`. `grounding_bridge` has never
had a caller, and its docstring says so. No wire came loose; the 10-01 line named the wrong module.
