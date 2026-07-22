# Codette v3.6: Institutional Temporal Analysis via TimeTravelLens and Multi-Layer Runtime Protection via AEGIS

**Jonathan Harrison**  
Independent researcher  
harrison82_95@hotmail.com  
Zenodo DOI: https://doi.org/10.5281/zenodo.21482400  
Date: 2026-07-21

---

## Abstract

We describe two systems integrated into the Codette reasoning engine (v3.6). First, **TimeTravelLens** — a formal framework for measuring the temporal gap between when an institution acted on a problem and when it formally disclosed that action. The framework computes Π(s) (preemption gap), C(s) (closure score across a four-class taxonomy), ℛ(s) (rupture indicator), ℬ(s) (beacon indicator), and Z^H (high preemption zone), derived from either structured `InstitutionalState` objects or unstructured text via `InstitutionalExtractor`. The lens fires automatically during chat on institutional queries, stores observations in CocoonV3 memory artifacts, and surfaces metrics in a live UI dashboard. Second, **AEGIS Protection Layers** — seven implemented runtime safeguards wrapping every ForgeEngine reasoning cycle: filesystem isolation (Layer 2), boot integrity verification (Layer 3), **post-quantum cocoon sealing via ML-KEM-768 + ML-DSA-65 (Layer 4)**, pre-emptive healing from real cocoon fields (Layer 5), RenderLayer output validation (Layer 6), a SQLite-backed metrics engine, and a full orchestration wrapper. Together these systems add observability, temporal accountability analysis, and multi-layer runtime protection — including NIST FIPS 203/204 post-quantum cryptography — to a production multi-perspective reasoning engine. All implementations are released open-source.

---

## 1. Introduction

Codette is a modular multi-perspective reasoning engine that routes queries through specialized cognitive adapters (Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Multi-Perspective, Systems Architecture), synthesizes their outputs, and stores reasoning artifacts as structured cocoons with full provenance tracking [Harrison 2025a]. Previous work established the core architecture (v2.1–v3.0), behavioral locks (v3.1–v3.2), hand-authored adapter training (v3.4), GPQA benchmarking (v3.4–v3.5), and Verify-and-Revise with bully-critic stress testing (v3.5) [Harrison 2026a].

This paper documents v3.6, which adds two major capabilities: (1) **TimeTravelLens** — a theory-grounded framework for analyzing institutional temporal gaps, and (2) **AEGIS Protection Layers** — a runtime safeguard system with six production-quality Python implementations covering filesystem isolation, boot integrity, post-quantum cocoon sealing, pre-emptive healing, and output validation.

The motivation for TimeTravelLens comes from Codette's existing ethics infrastructure (AEGIS deontological framework, Guardian subsystem). When a user asks about product recalls, regulatory failures, or institutional suppression, the system can now quantify *how long* the gap was between private knowledge and public disclosure — a formally measurable signal of institutional preemption. High preemption zones are flagged to the deontological framework for ethical weighting.

The motivation for AEGIS protection layers is practical: a production reasoning system needs runtime safeguards that are observable and measurable, not simulated. Jonathan built these layers independently and integrated them into the ForgeEngine pipeline.

---

## 2. TimeTravelLens

### 2.1 Formal Framework

Let s denote an institutional state. We define:

- **t_op(s)**: timestamp of the first materially conditioned action — when the institution acted on knowledge of a problem (internally patched, suppressed, adjusted)
- **t_inst(s)**: timestamp of the first formal institutional registration — public disclosure, regulatory filing, recall notice

**Preemption gap:**
```
Π(s) = t_inst(s) − t_op(s)
```
When t_inst is unknown: Π(s) = ∞. When both are unknown: Π(s) = NaN.

**ClosureClass taxonomy** (ordered by epistemic closure):

| Class | Score C(s) | Description |
|---|---|---|
| CLOSED | 1.00 | Full disclosure; investigation formally resolved |
| DRIFT | 0.67 | Ongoing, unresolved, or pending |
| SUPPRESSED | 0.24 | Active concealment or denial |
| INEXPRESSIBLE | 0.00 | Cannot be articulated or registered at all |

**Rupture indicator:**
```
ℛ(s) = 1   iff  t_op(s) < ∞  and  C(s) < 1.0
ℛ(s) = 0   otherwise
```

**Beacon indicator:**
```
ℬ(s) = 1   iff  ℛ(s) = 1  and  Σ influence_over_time(s) > τ_I
```
Where τ_I = 100 (default; configurable via `TimeTravelConfig`).

**High preemption zone Z^H:**
```
Z^H(s) = 1  iff  Π(s) > τ_Π  and  C(s) < τ_C  and  Var({Π_i(s)}) > τ_V
```
Default thresholds: τ_Π = 30 days, τ_C = 0.5, τ_V = 50 days².

**Actor preemption gaps:**
```
Π_i(s) = t_inst_i(s) − t_op_i(s)
```
Where i indexes known institutional actors (engineers, management, legal, executives, regulators, employees). Actor gaps measure differential knowledge — e.g., engineers knew 2 days after the event, management knew 180 days later, legal had no t_op assigned (∞).

**Triangulated closure resolution:** When multiple evidence sources (documents, testimony, behavior) provide conflicting ClosureClass signals, the lens uses majority vote with fallback ordering.

### 2.2 InstitutionalExtractor

`InstitutionalExtractor` derives an `InstitutionalState` from unstructured text via a two-stage pipeline:

**Stage 1 — Date extraction:** Five regex patterns (full month name, abbreviated month, ISO, US format, ordinal) scan the text for date strings. Overlapping spans are deduplicated. Each matched date is parsed via `dateutil.parser` (ISO strptime fallback). The surrounding ±100 characters are used as context for event-type scoring.

**Stage 2 — Event classification:** For each date hit, keyword density scores are computed:
- `op_score`: count of material-action keywords (patch, fix, suppress, conceal, internally, knew, quietly, ...)
- `inst_score`: count of formal-registration keywords (announced, disclosed, filed, registered, officially, recalled, ...)

The date with highest `op_score` is assigned as `t_op`; the next-highest `inst_score` candidate (distinct from `t_op`) becomes `t_inst`.

**Closure class inference:** Three keyword patterns — `_SUPPRESSED_RE`, `_DRIFT_RE`, `_CLOSED_RE` — are matched against the full text. The dominant pattern determines ClosureClass with confidence proportional to its share of total matches.

**Confidence rubric:**
```
confidence = (populated_fields / 4) × max(closure_confidence, 0.20)
```
Where `populated_fields` counts: t_op set, t_inst set, closure_confidence > 0.25, actors > 0.

A threshold of ≥ 0.30 is applied before storing or surfacing the result.

### 2.3 InstitutionalContextDetector

A fast keyword gate (~0.1ms) prevents overhead on irrelevant queries. Fires when ≥2 institutional keywords appear in the text:

```python
_INSTITUTIONAL_KEYWORDS = frozenset([
    "recall", "disclosure", "cover", "suppress", "concealed", "hid",
    "filed", "registered", "compliance", "regulatory", "investigation",
    "scandal", "fraud", "liability", "whistleblower", "defect", "safety",
    "settlement", "lawsuit", "penalty", "fine", "subpoena", "evidence",
    "testimony", "concealment", "negligence", "misconduct", "cover-up",
    "announcement", "press release", "statement", ...
])
```

### 2.4 Integration into Codette

**Layer 5.8** (ForgeEngine `forge_with_debate`):

```python
if InstitutionalContextDetector.is_relevant(concept):
    _tt_state, _tt_conf = InstitutionalExtractor().extract(concept + synthesis)
    if _tt_state and _tt_conf >= 0.3:
        _time_travel_metrics = TimeTravelLens(config=TimeTravelConfig.default()).observe(_tt_state)
        # Annotate AEGIS when high_preemption_zone=True
        if aegis_result and _time_travel_metrics["high_preemption_zone"]:
            aegis_result["supplementary_context"]["time_travel"] = {...}
```

**Server-level trigger** (post-response processing in `_handle_chat_sse`): runs the same pipeline on query + response text, stores result in `response_data["time_travel"]` and a global `_last_time_travel_result` variable.

**CocoonV3 field:** `time_travel_metrics: Optional[dict]` stores the full `observe()` bundle when confidence ≥ 0.3.

**API endpoints:**
- `GET /api/time_travel/last` — returns most recent auto-triggered observation
- `GET /api/time_travel/analyze?text=...` — on-demand analysis of arbitrary text

**Environment control:** `CODETTE_TIME_TRAVEL=0` disables the lens system-wide.

---

## 3. AEGIS Protection Layers

AEGIS (Adaptive Ethical Governance and Integrity System) wraps every ForgeEngine reasoning cycle with six protection layers, all fully implemented in Python.

### 3.1 Layer 2: Filesystem Isolation

`aegis_layer2_complete.py` (428 lines) restricts the process's filesystem reachability to the workspace directory.

- **Linux:** Landlock LSM system calls (`landlock_create_ruleset`, `landlock_add_rule`, `landlock_restrict_self`). Restricts read, write, execute, and network access outside the workspace path.
- **Windows:** NTFS DACL monitoring via `pywin32` (`win32security`, `win32file`). Monitors directory access control lists and alerts on unexpected reach.
- Degrades gracefully when kernel support is unavailable (logs warning, continues).

### 3.2 Layer 3: Boot Integrity Verification

`aegis_layer3_complete.py` (456 lines) verifies platform boot state before the first forge cycle.

- **TPM 2.0**: Reads PCR (Platform Configuration Register) banks via `tpm2-tools` or `/dev/tpm0`. Detects unexpected PCR changes indicating kernel or bootloader tampering.
- **Secure Boot**: Reads EFI variable `SecureBoot-{GUID}` on Linux; `bcdedit` on Windows. Verifies Secure Boot is enabled and configured as expected.
- **Kernel integrity**: Reads `/proc/sys/kernel/kptr_restrict` and `dmesg` for known bad strings. On Windows, checks Windows Defender status.
- Non-blocking: returns a detailed report dict but does not prevent forge execution unless `require_full_isolation=True`.

### 3.3 Layer 4: Post-Quantum Cocoon Sealing (ML-KEM-768 + ML-DSA-65)

`aegis_layer4_complete.py` (280 lines) implements real lattice-based cryptography via `liboqs-python` (Open Quantum Safe project), binding to the compiled `liboqs` C library. All `import oqs` calls are lazy — inside method bodies — so the module loads in microseconds and the C library is invoked only when crypto methods are called.

**Algorithms:** ML-KEM-768 (NIST FIPS 203, formerly Kyber768) for key encapsulation; ML-DSA-65 (NIST FIPS 204, formerly Dilithium3) for digital signatures. Both are NIST-standardized post-quantum primitives resistant to known quantum attacks.

**`PQCKeyStore`**: Generates and persists an ML-KEM-768 keypair and an ML-DSA-65 keypair at `~/.codette/pqc/`. Key files include a magic header (`CODETTE_PQC_V1\x00`) for corruption detection. `load_or_generate()` auto-provisions on first use.

**`PQCCocoonSealer`**: Implements the following per-cocoon sealing protocol:
1. Encapsulate against the persistent ML-KEM-768 public key → `(ciphertext, shared_secret)` [one-time ephemeral]
2. Derive seal key: `SHA3-256(shared_secret || b"CODETTE_COCOON_SEAL_v1")`
3. Compute `HMAC-SHA3-256(payload, seal_key)` → tag
4. Store `(ciphertext, tag)` alongside the cocoon record

Verification decapsulates the stored ciphertext with the persistent private key to recover `shared_secret`, re-derives the seal key, and verifies the HMAC. An adversary without the ML-KEM-768 private key cannot forge a valid tag even with quantum computing resources.

**`PQCBootVerifier`**: Computes `SHA3-256` of five critical source files (`forge_engine.py`, `codette_server.py`, `codette_orchestrator.py`, `aegis_orchestrator.py`, `aegis_layer4_complete.py`) and signs each hash with ML-DSA-65. The manifest is saved to `~/.codette/pqc/boot_manifest.json`. At server startup, `verify_files()` rehashes each file and verifies signatures — any post-signature modification fails verification.

**`EpistemicQuantumGate`**: Computes perspective tension across the active reasoning perspectives:
```
ξ_t = (1/k) Σᵢ ||Aᵢ − Ā||²
```
Where Aᵢ is the normalized token-probability distribution of perspective i and Ā is the mean distribution across all k perspectives. Accepts real `PerspectiveVector` objects from ForgeEngine output; falls back to deterministic pseudo-random synthetic vectors (seeded from SHA3-256 of perspective names) when called outside a forge context.

**`PQCShield`**: Public facade imported by `aegis_orchestrator.py`. Exposes `seal_dict()` / `verify_dict()` for JSON cocoon records, `sign_boot_files()` / `verify_boot()` for integrity checks, `compute_tension()` for epistemic gate, and `status()` for dashboard reporting. Graceful degradation: if the liboqs C library has not yet been compiled, initialization logs a warning and the layer disables itself without crashing the server.

**Orchestrator integration:** `AEGISOrchestrator` accepts `use_layer4=True` (default). After each `forge_with_debate()` call, `activate_layer4_seal()` seals the returned cocoon dict in-place. `stats["layer4_seals"]` and `stats["layer4_verifications"]` are tracked separately.

### 3.4 Layer 5: Pre-Emptive Healing

`aegis_layer5_complete.py` (496 lines) simulates forward cognitive trajectories and applies healing before tension becomes critical.

**Key innovation:** Layer 5 reads **real cocoon fields** — not random noise. It queries the most recent stored cocoon for `epsilon_value` (epistemic tension), `gamma_coherence`, and `pairwise_tensions`. If `epsilon_value` exceeds a configurable `tension_critical_threshold` (default 0.70), it applies one of four healing actions:

| Action | Trigger | Effect |
|---|---|---|
| `stabilization` | epsilon near critical | Reduce tension, restore coherence |
| `rebalancing` | severe coherence loss | Shift perspective weights toward highest-coherence adapter |
| `correction` | intent-trajectory divergence | Override synthesis direction |
| `maintenance` | nominal | Light maintenance pass |

`PreEmptiveImmuneEngine` maintains a `k_steps` forward simulation, computes pairwise tensions across perspectives, and selects healing action via a threshold ladder.

### 3.5 Layer 6: RenderLayer Validation

`aegis_layer6_complete.py` (504 lines) validates every forge output before it leaves the system.

**CocoonV3Validator:** Checks that the generated cocoon satisfies schema constraints — all required fields present, `execution_path` in valid set, `cocoon_integrity_score` in [0,1], `psi_r` in [0,1], `eta_score` not None on `forge_full` path.

**WordOverlapValidator:** Computes the Jaccard-like word overlap between the authored conclusion and the rendered output. Rejects responses below 15% overlap (configurable via `min_word_overlap`). This guards against the render layer drifting too far from the authored intent — a failure mode where the LLM "improves" the conclusion into something that no longer reflects the evidence.

`RenderLayer.validate_and_render()` is the single entry point. Returns `(valid: bool, report: dict)`.

### 3.6 AEGIS Metrics Engine

`aegis_metrics_engine.py` maintains a SQLite database (`aegis_metrics.db`) of every forge cycle. Logged fields per cycle: timestamp, concept preview (40 chars), healing action and magnitude (Layer 5), overlap percentage (Layer 6), valid/invalid status, and total latency.

**Aggregation queries exposed via `/api/aegis/*`:**
- `/api/aegis/stats?hours=N` — total calls, valid calls, rejection rate, healing rate, avg overlap, avg latency
- `/api/aegis/healing-log?limit=N` — recent healing events
- `/api/aegis/recent-events?limit=N` — recent forge cycles with validation status

### 3.7 Orchestrator

`aegis_orchestrator.py` (~440 lines) is the drop-in wrapper around `ForgeEngine.forge_with_debate()`. It applies Layers 2 → 3 → forge → **4** → 5 → 6 in sequence, respects `require_full_isolation` flag, accumulates statistics per layer, and produces a unified result dict with `layer_activations`, `alerts`, `valid`, and `synthesis`.

---

## 4. Test Coverage

| Module | Tests | Runtime | Pass |
|---|---|---|---|
| `time_travel_lens.py` | 33 | 0.012s | 100% |
| `institutional_extractor.py` | 6 (within above) | — | 100% |
| `aegis_layer4_complete.py` | built-in `__main__` integration test | ~5 min first run (C library compile) | verified |

The Layer 4 `__main__` test covers: keypair generation, seal/verify round-trip, tamper detection (modified payload rejected), dict seal/verify, and synthetic ξ_t computation across five named perspectives. AEGIS Layers 2, 3, 5, 6 are tested via `aegis_orchestrator.py`'s `__main__` demo path and server integration.

---

## 5. Design Decisions and Lessons

**Why Layer 5.8 in ForgeEngine, not just the server?**  
The server-level trigger runs on query + response text and is fast. The ForgeEngine Layer 5.8 runs on concept + synthesis (before the user-facing response is assembled), giving AEGIS a chance to incorporate temporal gap information into its deontological weighting *during* the forge cycle. Both run independently.

**Why confidence threshold 0.30?**  
Below this, the extractor typically has only one timestamp or a poorly-resolved closure class. At 0.30+ (populated t_op, t_inst, reasonable closure signal, ≥1 actor), the result is reliable enough to surface without misleading the user.

**Why not hard-block on high preemption zone?**  
The TimeTravelLens is an analytical tool, not a content filter. High preemption zones trigger an alert in the AEGIS deontological framework for ethical weighting, but do not veto responses. The analysis makes the gap visible; the deontological framework weighs it; the final decision is Codette's ethical consensus.

**Why real post-quantum crypto rather than HMAC?**  
An earlier version of Layer 4 used SHA3-HMAC labeled as "ML-KEM-768." That label was wrong and was corrected. The motivation for using actual lattice-based KEM rather than symmetric HMAC is that symmetric authentication requires the verifier to hold the same secret as the signer — a shared key that, if compromised, breaks all past seals. ML-KEM-768's asymmetric construction means the sealing public key can be distributed freely; only the private key can verify. The shared secret used for the HMAC tag is derived ephemerally per cocoon and never stored, so compromising one seal does not compromise others. This is materially stronger than a static HMAC key and resistant to quantum attacks on the key encapsulation step.

**Why lazy imports?**  
The `liboqs` C library is compiled from source on first import (~5–10 minutes). Importing at module level would stall server startup. All `import oqs` calls in `aegis_layer4_complete.py` are inside method bodies — the module loads instantly, and the C library is invoked only when a crypto method is called. After the first compile the library is cached (`~/_oqs/bin/oqs.dll` on Windows), so subsequent imports are fast.

---

## 6. Relation to Prior Work

The TimeTravelLens framework is original. The closest related concepts are in institutional theory (Fligstein & McAdam 2012 on strategic action fields) and organizational failure analysis (Weick 1988 on organizational sensemaking), but the formal treatment — specifically the timestamp ladder, preemption gap metric, and ClosureClass taxonomy — is new.

AEGIS protection layers draw on standard Linux security mechanisms (Landlock, first introduced in Linux 5.13), TPM 2.0 attestation, and Jaccard similarity. The novelty is the integration into a multi-perspective reasoning pipeline with real-time healing from live cocoon telemetry.

This project's multi-perspective architecture predates and is independent of Camlin (arXiv:2505.01464, May 2025). Our Perspective Dispersion metric Υ measures variance across simultaneous perspectives; Camlin's ξ measures one model's hidden-state change across recursive steps. Attribution maintained per [docs/ATTRIBUTION_perspective_dispersion.md].

---

## 7. Code and Data Availability

All source code is available at: https://github.com/Raiff1982/Codette-Reasoning  
HuggingFace model hub: https://huggingface.co/Raiff1982/Codette-Reasoning  
This paper: https://doi.org/10.5281/zenodo.21482400  
Previous Zenodo archive: https://doi.org/10.5281/zenodo.15214462

Key files for this paper:
- `reasoning_forge/time_travel_lens.py`
- `reasoning_forge/institutional_extractor.py`
- `tests/test_time_travel_lens.py`
- `Theory/howitworks.txt` (original TimeTravelLens concept document)
- `Protection_Layer/aegis_layer2_complete.py`
- `Protection_Layer/aegis_layer3_complete.py`
- `Protection_Layer/aegis_layer4_complete.py` ← ML-KEM-768 + ML-DSA-65
- `Protection_Layer/aegis_layer5_complete.py`
- `Protection_Layer/aegis_layer6_complete.py`
- `Protection_Layer/aegis_orchestrator.py`
- `Protection_Layer/aegis_metrics_engine.py`

---

## References

- Harrison, J. (2025a). Codette Reasoning Engine v1.0. Zenodo. https://doi.org/10.5281/zenodo.15214462
- Harrison, J. (2026a). Codette v3.5: STaR Newton Study, Phase 0 Ablation, Verify-and-Revise, Bully-Critic Stress Test. Zenodo. [prior submission]
- Fligstein, N., & McAdam, D. (2012). A Theory of Fields. Oxford University Press.
- Weick, K. E. (1988). Enacted Sensemaking in Crisis Situations. Journal of Management Studies, 25(4), 305–317.
- Camlin, J. (2025). Consciousness in AI: Logic, Proof, and Experimental Evidence of Recursive Identity Formation. arXiv:2505.01464. [ξ metric — credited, not used in this system]
- Linux Kernel Documentation. Landlock: unprivileged access control. https://www.kernel.org/doc/html/latest/userspace-api/landlock.html
- Trusted Computing Group. TPM 2.0 Library Specification. https://trustedcomputinggroup.org/resource/tpm-library-specification/
- NIST. (2024). FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.FIPS.203
- NIST. (2024). FIPS 204: Module-Lattice-Based Digital Signature Standard (ML-DSA). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.FIPS.204
- Open Quantum Safe Project. liboqs: C library for quantum-safe cryptographic algorithms. https://github.com/open-quantum-safe/liboqs
- Open Quantum Safe Project. liboqs-python: Python bindings for liboqs. https://github.com/open-quantum-safe/liboqs-python
