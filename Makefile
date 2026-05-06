.PHONY: cocoon-smoke cocoon-smoke-strict test test-cocoon lint \
        inspect-latest list-cocoons health dev

# ── Integrity gate ────────────────────────────────────────────────────────────

# Smoke test: build a complete CocoonV3, assert integrity_score=1.0, no missing fields
# Run this before pushing any change that touches reasoning_forge/ or inference/
cocoon-smoke:
	python scripts/cocoon_smoke.py

# Strict mode: CODETTE_AUDIT_MODE=1 validates every cocoon write in-process
cocoon-smoke-strict:
	CODETTE_AUDIT_MODE=1 python scripts/cocoon_smoke.py

# ── Tests ─────────────────────────────────────────────────────────────────────

# Full test suite
test:
	python -m pytest tests/ -v

# Cocoon audit tests only
test-cocoon:
	python -m pytest tests/test_cocoon_audit.py -v

# ── Cocoon inspection ─────────────────────────────────────────────────────────

# Human-friendly summary of the most recently written cocoon
inspect-latest:
	python scripts/inspect_cocoon.py --latest

# Inspect a specific cocoon by ID or path: make inspect COCOON=cocoon_1234_5678
inspect:
	python scripts/inspect_cocoon.py $(COCOON)

# List last N cocoons with execution_path, integrity, echo risk at a glance
# Override N: make list-cocoons N=50
list-cocoons:
	python scripts/list_recent_cocoons.py --n $(or $(N),20)

# Filter views
list-high-echo:
	python scripts/list_recent_cocoons.py --filter high-echo

list-low-integrity:
	python scripts/list_recent_cocoons.py --filter low-integrity

list-legacy:
	python scripts/list_recent_cocoons.py --filter legacy

# ── Health check ──────────────────────────────────────────────────────────────

# Avg integrity score, echo distribution, fallback alarm count
health:
	python scripts/health_check.py

# Strict health: exits 1 if any metric is degraded
health-strict:
	python scripts/health_check.py --strict

# ── Local dev ─────────────────────────────────────────────────────────────────

# Start Codette locally with a separate dev cocoon store so dev writes
# don't pollute the production cocoons/ directory.
# Server prints the cocoon store path on startup.
dev:
	COCOON_STORE=./dev_cocoons CODETTE_AUDIT_MODE=1 python inference/codette_server.py

# ── Lint ──────────────────────────────────────────────────────────────────────

# ── Benchmarks ───────────────────────────────────────────────────────────────

# Phase 7.1 AAP benchmark: directness, attractor distribution, trust, latency
# Requires server running (make dev in another terminal)
bench-aap:
	python benchmarks/phase71_aap_benchmark.py --timeout $(or $(TIMEOUT),120)

bench-aap-quick:
	python benchmarks/phase71_aap_benchmark.py --quick --timeout $(or $(TIMEOUT),120)

# Full Phase 7 benchmark (existing)
bench-phase7:
	python benchmarks/phase7_benchmark.py

lint:
	python -m py_compile \
	    reasoning_forge/cocoon_schema_v3.py \
	    reasoning_forge/cocoon_validator.py \
	    reasoning_forge/echo_collapse_detector.py \
	    reasoning_forge/subsystem_contracts.py \
	    reasoning_forge/cognition_cocooner.py \
	    inference/codette_forge_bridge.py \
	    scripts/cocoon_smoke.py \
	    scripts/inspect_cocoon.py \
	    scripts/list_recent_cocoons.py \
	    scripts/health_check.py
	@echo "Lint OK"
