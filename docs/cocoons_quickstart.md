# Cocoons Quickstart

A **cocoon** is Codette's persistent memory unit — a JSON file written to `cocoons/` after every reasoning turn. Each cocoon records not just the query and response but the full provenance of how the answer was produced: which perspectives fired, what the ethics scores were, whether the output echoed the input, and a composite integrity score.

This document covers:
- How cocoons are written
- How to run the smoke test
- How to interpret `cocoon_integrity` and `cocoon_integrity_score`
- Quick inspection commands

---

## How Cocoons Are Written

Every production response flows through one of two paths:

| Path | Entrypoint | `execution_path` tag |
|---|---|---|
| Full ForgeEngine (consciousness stack) | `forge_engine.py:forge_with_debate()` | `forge_full` |
| Orchestrator bridge (live chat) | `codette_forge_bridge.py:_generate_with_phase6()` | `adapter_lightweight` |

Both paths call `CognitionCocooner.wrap_reasoning(v3_cocoon=...)`, which writes a `type: "reasoning_v3"` JSON file containing the full [`CocoonV3`](../reasoning_forge/cocoon_schema_v3.py) schema.

The v3 schema adds to the base (v2) fields:

- **Provenance**: `execution_path`, `model_inference_invoked`, `orchestrator_trace_id`
- **Integrity**: `cocoon_integrity`, `cocoon_integrity_score` (0–1 composite)
- **Echo / Collapse**: `echo_risk`, `perspective_collapse_detected`
- **Epistemic telemetry**: `psi_r`, `pairwise_tensions`, `perspective_coverage`
- **AEGIS ethics**: `aegis_framework_scores`, `aegis_dominant_framework`
- **Guardian / Nexus**: safety status, trust calibration, risk level
- **Synthesis structure**: convergences, divergences, tradeoffs, recommended position

Cocoons that fail validation (high echo risk, perspective collapse, integrity below threshold) are routed to `cocoons/quarantine/` instead of the main store.

---

## Running the Smoke Test

```bash
make cocoon-smoke
```

This runs [`scripts/cocoon_smoke.py`](../scripts/cocoon_smoke.py) — 27 checks across schema validation, integrity scoring, echo detection, subsystem contracts, quarantine routing, and the regression alarm.

**In strict mode** (validates every write in the process):

```bash
make cocoon-smoke-strict
# equivalent to: CODETTE_AUDIT_MODE=1 python scripts/cocoon_smoke.py
```

Run this before pushing any change that touches `reasoning_forge/` or `inference/codette_forge_bridge.py`.

---

## Interpreting `cocoon_integrity` and `cocoon_integrity_score`

The validator ([`reasoning_forge/cocoon_validator.py`](../reasoning_forge/cocoon_validator.py)) computes a weighted composite score (0.0–1.0):

| Factor | Weight | What it checks |
|---|---|---|
| Required fields present | 35% | `execution_path`, `model_inference_invoked`, `active_perspectives`, `eta_score` |
| Execution path quality | 20% | `forge_full`=1.0, `adapter_lightweight`=0.6, `recovery_mode`=0.3, `fallback_template`/`unknown`=0.0 |
| Perspective diversity | 15% | ≥3 active perspectives = full credit |
| Metrics population | 20% | `complete`=1.0, `partial`=0.5, `failed`=0.0 |
| Echo / Collapse | 10% | `high` echo or collapse = 0.0 |

### Status labels

| `cocoon_integrity` | Score range | Meaning |
|---|---|---|
| `complete` | 1.0 | All checks pass — full provenance, no echo, all metrics present |
| `partial` | 0.4–0.99 | Some fields missing or reduced execution path (e.g. `adapter_lightweight`) |
| `failed` | < 0.4 | Multiple gaps or high echo risk — cocoon quarantined |

A `partial` score is expected for `adapter_lightweight` cocoons (live chat path) because the full AEGIS framework scores and deep perspective coverage are only available on the `forge_full` path.

---

## Quick Inspection Commands

**Inspect the most recently written cocoon:**
```bash
make inspect-latest
# or: python scripts/inspect_cocoon.py --latest
```

**Inspect a specific cocoon by ID:**
```bash
python scripts/inspect_cocoon.py cocoon_1234567890_5678
```

**List the last 20 cocoons with integrity and echo at a glance:**
```bash
make list-cocoons
# or: python scripts/list_recent_cocoons.py
```

**Filter to only high-echo or low-integrity cocoons:**
```bash
python scripts/list_recent_cocoons.py --filter high-echo
python scripts/list_recent_cocoons.py --filter low-integrity
```

**Check overall system health (avg integrity, echo distribution, fallback alarms):**
```bash
make health
# or: python scripts/health_check.py
```

---

## Where Cocoons Live

| Directory | Contents |
|---|---|
| `cocoons/` | Production reasoning cocoons |
| `cocoons/quarantine/` | Cocoons that failed validation (high echo, missing fields) |
| `dev_cocoons/` | Local dev cocoons when running `make dev` |

Cocoons are plain JSON — safe to read, diff, or archive. Never modify them by hand; the `cocoon_id` and `full_response_hash` fields are integrity anchors.

---

## See Also

- [`docs/cocoon_pipeline.md`](cocoon_pipeline.md) — audit-first architecture and how the public claims map to code
- [`reasoning_forge/cocoon_schema_v3.py`](../reasoning_forge/cocoon_schema_v3.py) — full schema definition
- [`reasoning_forge/cocoon_validator.py`](../reasoning_forge/cocoon_validator.py) — scoring and quarantine logic
- [`reasoning_forge/echo_collapse_detector.py`](../reasoning_forge/echo_collapse_detector.py) — echo / collapse detection
