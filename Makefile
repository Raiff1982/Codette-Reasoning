.PHONY: cocoon-smoke test lint

# Smoke test: build a complete CocoonV3, assert integrity_score=1.0, no missing fields
cocoon-smoke:
	python scripts/cocoon_smoke.py

# Full test suite
test:
	python -m pytest tests/ -v

# Run only cocoon audit tests
test-cocoon:
	python -m pytest tests/test_cocoon_audit.py -v

# Strict mode: validate every cocoon write
cocoon-smoke-strict:
	CODETTE_AUDIT_MODE=1 python scripts/cocoon_smoke.py

lint:
	python -m py_compile reasoning_forge/cocoon_schema_v3.py \
	    reasoning_forge/cocoon_validator.py \
	    reasoning_forge/echo_collapse_detector.py \
	    reasoning_forge/subsystem_contracts.py \
	    inference/codette_forge_bridge.py
	@echo "Lint OK"
