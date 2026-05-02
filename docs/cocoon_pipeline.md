# Cocoon Pipeline — Audit-First Architecture

This document links Codette's public "audit-first" and "transparent reasoning" claims to the concrete mechanics that back them up. Every claim here resolves to a specific file, class, or `make` command you can run.

---

## The Public Claim

Codette's model cards and README describe it as an **audit-first reasoning system**: every response is attributable to a specific reasoning path, every ethical check leaves a trace, and no response can silently bypass the integrity layer.

This document is the one-click path from that claim to the code proving it.

---

## The Pipeline

A single user turn flows through these stages:

```
User query
    │
    ▼
[1] Complexity routing          codette_forge_bridge.py / forge_engine.py
    │   QueryComplexity: SIMPLE / MEDIUM / COMPLEX
    │   Substrate-aware adjustment (memory pressure, CPU load)
    ▼
[2] Multi-perspective inference  forge_engine.py:_forge_single_safe() / forge_with_debate()
    │   Up to N adapters fire in parallel
    │   Each named perspective (Newton, Empathy, Philosophy, ...) produces output
    ▼
[3] Epistemic metrics            reasoning_forge/epistemic_metrics.py
    │   epsilon (tension magnitude), gamma (ensemble coherence), psi_r (resonance)
    ▼
[4] AEGIS ethics evaluation      reasoning_forge/aegis.py
    │   6 frameworks: utilitarian, deontological, virtue, care, ubuntu, indigenous_reciprocity
    │   eta score, per-framework scores, dominant framework, conflict notes
    ▼
[5] Guardian + Nexus             safety_notes, intent_vector
    │   guardian_safety_status: pass / flag / block
    │   nexus_risk_level: low / medium / high
    ▼
[6] Echo / Collapse detection    reasoning_forge/echo_collapse_detector.py
    │   Token cosine similarity: output vs. prompt (echo), output vs. output (collapse)
    │   echo_risk: low / medium / high
    │   perspective_collapse_detected: True / False
    ▼
[7] CocoonV3 build               reasoning_forge/cocoon_schema_v3.py:build_cocoon_v3()
    │   All metrics, scores, path tags assembled into a single validated object
    │   Raises ValueError on validation failure — no silent writes
    ▼
[8] Integrity scoring            reasoning_forge/cocoon_validator.py:CocoonValidator
    │   Composite score 0–1 from 5 weighted factors
    │   High echo or collapse → quarantine routing
    ▼
[9] Disk write                   reasoning_forge/cognition_cocooner.py:wrap_reasoning()
    │   type: "reasoning_v3" JSON with full v3 block embedded
    │   Regression alarm: if v3_cocoon=None, WARN log + counter increment
    ▼
cocoons/<cocoon_id>.json         or   cocoons/quarantine/<cocoon_id>.json
```

---

## Claims → Code

### "Every response is attributable to a specific reasoning path"

| Claim | Implementation |
|---|---|
| execution_path recorded on every cocoon | `CocoonV3.execution_path` — one of `forge_full`, `adapter_lightweight`, `recovery_mode`, `fallback_template`, `unknown` |
| path quality affects integrity score | `CocoonValidator._PATH_QUALITY`: `forge_full`=1.0, `adapter_lightweight`=0.6, `unknown`=0.0 |
| orchestrator trace ID on every write | `CocoonV3.orchestrator_trace_id` — UUID per turn |

→ [`reasoning_forge/cocoon_schema_v3.py`](../reasoning_forge/cocoon_schema_v3.py)
→ [`reasoning_forge/cocoon_validator.py`](../reasoning_forge/cocoon_validator.py)

### "Every ethical check leaves a trace"

| Claim | Implementation |
|---|---|
| Per-framework AEGIS scores on disk | `aegis_framework_scores` — all 6 frameworks scored 0–1 |
| Dominant ethical framework recorded | `aegis_dominant_framework` |
| Ethical conflicts noted | `aegis_ethical_conflict_notes` |
| Safety status + trust calibration | `guardian_safety_status`, `guardian_trust_calibration` |

→ [`reasoning_forge/cocoon_schema_v3.py`](../reasoning_forge/cocoon_schema_v3.py) lines 81–91

### "No response can silently bypass the integrity layer"

| Claim | Implementation |
|---|---|
| Both production write paths pass v3_cocoon | `forge_engine.py:1971`, `codette_forge_bridge.py:407` |
| Legacy fallback emits WARNING + increments counter | `cognition_cocooner.py:wrap_reasoning()` legacy branch |
| Smoke test asserts fallback_count == 0 | `scripts/cocoon_smoke.py` section [6] |
| CI gate via `make cocoon-smoke` | `Makefile:cocoon-smoke` |

→ [`reasoning_forge/cognition_cocooner.py`](../reasoning_forge/cognition_cocooner.py)
→ [`scripts/cocoon_smoke.py`](../scripts/cocoon_smoke.py)

### "Echo and perspective collapse are detected, not just described"

| Claim | Implementation |
|---|---|
| Token cosine similarity vs. prompt | `EchoCollapseDetector.check()` — no ML, pure token overlap |
| Theatrical labeling flagged as high echo | Tested in smoke test section [3] |
| Collapsed perspectives quarantined | `CocoonValidator`: `should_quarantine=True` on high echo or collapse |

→ [`reasoning_forge/echo_collapse_detector.py`](../reasoning_forge/echo_collapse_detector.py)

---

## Contributor Workflow

**Before pushing any change that touches ForgeEngine, memory, or cocoon paths:**

```bash
make cocoon-smoke
```

This is your one-command sanity check. It asserts:
- Schema builds and validates correctly
- Integrity score reaches 1.0 on a complete cocoon
- Echo detector correctly flags theatrical labels
- Subsystem contracts enforce required fields
- Quarantine routes high-risk cocoons correctly
- No v3 fallback fires (regression alarm is silent)

**To install the pre-push git hook** (optional but recommended):

```bash
cp .githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

The hook runs `make cocoon-smoke` automatically when you push changes to `reasoning_forge/` or `inference/`.

---

## Verifying a Live System

After a real Codette server run, spot-check the output:

```bash
# What just got written?
make list-cocoons

# Inspect the most recent cocoon in full
make inspect-latest

# System health (avg integrity, echo distribution, fallback count)
make health
```

Healthy output looks like:
- `cocoon_integrity: complete`, score ≥ 0.8 on `forge_full` turns
- `cocoon_integrity: partial`, score ≈ 0.6 on `adapter_lightweight` turns (expected — AEGIS depth not available)
- `echo_risk: low` on substantive queries
- `v3_missing_fallback_count: 0`

---

## See Also

- [`docs/cocoons_quickstart.md`](cocoons_quickstart.md) — how to run the smoke test and read cocoon fields
- [`docs/proof.md`](proof.md) — full claims-to-artifacts index
- [`reasoning_forge/subsystem_contracts.py`](../reasoning_forge/subsystem_contracts.py) — TypedDicts enforcing required fields at every subsystem handoff
