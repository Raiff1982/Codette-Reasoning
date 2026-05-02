# Proof Index

This document maps Codette's public claims to concrete artifacts in the repository.

## What This Repository Proves

The strongest current evidence in this repo is that Codette:

- runs as a local multi-perspective reasoning system
- exposes measurable routing, memory, valuation, and safety behaviors
- can be benchmarked with saved results
- can be tested locally through both automated tests and live API demos
- has documented fixes for real failure modes, not just ideal-case descriptions

## Quick Audit Path

If you want the fastest audit, review these in order:

1. [README.md](../README.md)
2. [demo/README.md](../demo/README.md)
3. [codette_benchmark_report.md](../data/results/codette_benchmark_report.md)
4. [codette_runtime_benchmark_20260402_135517.md](../data/results/codette_runtime_benchmark_20260402_135517.md)
5. [codette_runtime_benchmark_20260402_140237.md](../data/results/codette_runtime_benchmark_20260402_140237.md)
6. [tests](../tests)

## Claims To Artifacts

### Multi-Perspective Reasoning

Proof artifacts:
- [benchmarks/codette_benchmark_suite.py](../benchmarks/codette_benchmark_suite.py)
- [data/results/codette_benchmark_report.md](../data/results/codette_benchmark_report.md)
- [inference/codette_orchestrator.py](../inference/codette_orchestrator.py)

What these show:
- single vs multi vs memory vs full-Codette comparisons
- per-category scoring
- saved statistical output, not just descriptive claims

### Session Continuity And Memory Recall

Proof artifacts:
- [inference/codette_session.py](../inference/codette_session.py)
- [reasoning_forge/unified_memory.py](../reasoning_forge/unified_memory.py)
- [tests/test_event_embedded_value.py](../tests/test_event_embedded_value.py)
- [data/results/codette_runtime_benchmark_20260402_135517.md](../data/results/codette_runtime_benchmark_20260402_135517.md)

What these show:
- continuity summaries
- decision landmarks
- persistent cocoon-backed recall
- runtime validation of continuity retention

### Valuation And Risk Frontier Reasoning

Proof artifacts:
- [reasoning_forge/event_embedded_value.py](../reasoning_forge/event_embedded_value.py)
- [reasoning_forge/cocoon_synthesizer.py](../reasoning_forge/cocoon_synthesizer.py)
- [tests/test_event_embedded_value.py](../tests/test_event_embedded_value.py)
- [data/results/codette_runtime_benchmark_20260402_140237.md](../data/results/codette_runtime_benchmark_20260402_140237.md)

What these show:
- event-embedded value analysis
- singularity handling
- valuation-aware synthesis
- runtime proof that frontier ranking works

### Safe Web Research

Proof artifacts:
- [inference/web_search.py](../inference/web_search.py)
- [inference/codette_server.py](../inference/codette_server.py)
- [data/results/codette_runtime_benchmark_20260402_140237.md](../data/results/codette_runtime_benchmark_20260402_140237.md)
- [tests/test_event_embedded_value.py](../tests/test_event_embedded_value.py)

What these show:
- explicit live web lookup path
- current-fact gating and phrase-trigger handling
- source surfacing
- cocoon-backed research reuse

### Failure Handling And Loop Resistance

Proof artifacts:
- [docs/CHANGELOG_2026-04-02.md](CHANGELOG_2026-04-02.md)
- [data/results/codette_runtime_benchmark_20260402_135517.md](../data/results/codette_runtime_benchmark_20260402_135517.md)
- [tests/test_event_embedded_value.py](../tests/test_event_embedded_value.py)

What these show:
- explicit diagnostic gating
- loop-resistance benchmarking
- regression tests for trigger and continuity edge cases

### Audit-First Runtime Integrity

Proof artifacts:
- [reasoning_forge/cocoon_schema_v3.py](../reasoning_forge/cocoon_schema_v3.py) — CocoonV3 schema with execution path provenance, integrity scoring, echo detection
- [reasoning_forge/cocoon_validator.py](../reasoning_forge/cocoon_validator.py) — composite integrity scorer (0–1), quarantine routing
- [reasoning_forge/echo_collapse_detector.py](../reasoning_forge/echo_collapse_detector.py) — token cosine similarity detecting theatrical labeling and perspective collapse
- [reasoning_forge/subsystem_contracts.py](../reasoning_forge/subsystem_contracts.py) — TypedDicts enforcing required outputs at every subsystem boundary
- [reasoning_forge/cognition_cocooner.py](../reasoning_forge/cognition_cocooner.py) — regression alarm (`_v3_missing_fallback_count`) if any write bypasses v3
- [scripts/cocoon_smoke.py](../scripts/cocoon_smoke.py) — 27-check smoke test; run `make cocoon-smoke`
- [docs/cocoon_pipeline.md](cocoon_pipeline.md) — full claims-to-code map for audit-first architecture

What these show:
- every production response writes a `CocoonV3` with `execution_path`, AEGIS framework scores, echo risk, integrity score
- high-echo or collapsed cocoons are routed to quarantine, not the main store
- a module-level counter + WARNING log fires if the v3 path is ever bypassed
- `make cocoon-smoke` is the one-command CI gate: exits 1 on any regression

Quick verification:
```bash
make cocoon-smoke          # must pass before any push touching forge/memory
make health                # avg integrity, echo distribution, fallback count
make inspect-latest        # human-readable view of the most recent cocoon
```

## Runnable Evidence

### Demo

Use the local demo package:

- [demo/README.md](../demo/README.md)
- [demo/run_local_api_demo.py](../demo/run_local_api_demo.py)
- [demo/api_examples.md](../demo/api_examples.md)

### UI Proof Artifacts

Saved UI evidence:
- [Codette_system_proof.pdf](proof_assets/Codette_system_proof.pdf)
- [Codette_response_proof.pdf](proof_assets/Codette_response_proof.pdf)
- [Codettechat_UI_conversation_proof.pdf](proof_assets/Codettechat_UI_conversation_proof.pdf)

What this adds:
- system-level visual proof artifacts from real Codette runs
- response-level proof artifacts showing actual outputs
- proof that the web UI is active during a real conversation
- visible evidence of mid-session interaction rather than static setup screenshots
- an audit artifact that complements the benchmark and demo outputs

### Benchmarks

Run:

```bash
python benchmarks/codette_benchmark_suite.py
python benchmarks/codette_runtime_benchmark.py
python benchmarks/codette_runtime_benchmark.py --include-web
```

### Tests

Run:

```bash
python3 -m unittest tests.test_event_embedded_value
python3 -m unittest tests.test_codette_runtime_benchmark
```

## Current Limits

This proof layer is stronger than it was, but still not complete.

Current gaps:
- not every benchmark has a notebook or visualization
- live transcript logs are not yet heavily populated
- latency evidence exists, but long-run performance profiling is still limited
- fairness and adversarial robustness are still lighter than the core reasoning evidence

## Suggested Reading Order For Reviewers

1. README
2. proof index
3. runtime benchmark reports
4. benchmark runner code
5. focused tests
6. live demo scripts
