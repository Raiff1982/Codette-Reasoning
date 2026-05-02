# Contributing

Thanks for wanting to improve Codette.

This project moves fastest when contributions are reproducible, scoped, and easy to verify.

## Start Here

1. Read [README.md](README.md)
2. Read [docs/proof.md](docs/proof.md)
3. If your change touches memory, routing, safety, or web research, also read:
   - [docs/web_research.md](docs/web_research.md)
   - [docs/cocoon_backup_and_migration.md](docs/cocoon_backup_and_migration.md)

## Setup

```bash
git clone https://github.com/Raiff1982/Codette-Reasoning.git
cd Codette-Reasoning
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Model setup:
- [docs/deployment/MODEL_DOWNLOAD.md](docs/deployment/MODEL_DOWNLOAD.md)
- [docs/deployment/MODEL_SETUP.md](docs/deployment/MODEL_SETUP.md)

## Common Workflows

### Cocoon Integrity Gate

**Run this before pushing any change that touches `reasoning_forge/` or `inference/`:**

```bash
make cocoon-smoke
```

27 checks covering schema, integrity scoring, echo detection, subsystem contracts, quarantine routing, and the v3 regression alarm. Exits 1 on any failure. See [docs/cocoons_quickstart.md](docs/cocoons_quickstart.md) for what each section tests.

### Local Dev with Cocoon Inspection

```bash
make dev                   # starts Forge locally with COCOON_STORE=./dev_cocoons/
make inspect-latest        # human-readable summary of the most recent cocoon
make list-cocoons          # last 20 cocoons: id, execution_path, integrity, echo risk
make health                # avg integrity score, echo distribution, fallback alarm count
```

### Run Focused Tests

```bash
python3 -m unittest tests.test_event_embedded_value
python3 -m unittest tests.test_codette_runtime_benchmark
make test-cocoon           # cocoon audit tests only
```

### Run Benchmarks

```bash
python scripts/run_all_benchmarks.py
python scripts/run_all_benchmarks.py --include-runtime
```

### Run Demos

```bash
python demo/run_local_api_demo.py
```

## Optional: Pre-Push Git Hook

Install the included hook to have `cocoon-smoke` run automatically when you push changes to forge or cocoon files:

```bash
cp .githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

The hook only fires when the push touches `reasoning_forge/`, `inference/codette_forge_bridge.py`, or `scripts/cocoon_smoke.py`. To bypass in an emergency: `git push --no-verify`.

## What Makes A Good Contribution

Good contribution targets:
- bug fixes
- benchmark improvements
- test coverage
- adapter/routing improvements
- memory and continuity improvements
- web research safety hardening
- documentation and reproducibility fixes

## Pull Request Expectations

Please include:
- what changed
- why it changed
- how you verified it
- any benchmark/test output that supports the change
- any user-facing behavior change

If your change modifies public claims, update the evidence links too.

## Safety And Data Notes

- Do not commit large model files or private cocoons.
- Treat cocoon memory, session data, and transcripts as potentially sensitive.
- If you add example transcripts, scrub personal data first.

## Adapter Work

If you add or retrain an adapter, document:
- what the adapter is for
- how it routes
- how it is tested
- how it changes behavior versus base generation

Guide: [docs/adapter_workflow.md](docs/adapter_workflow.md)
