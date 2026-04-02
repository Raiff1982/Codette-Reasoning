# Demo Index

This folder contains short, reproducible local demos for Codette.

## What You Can Run

### 1. Local API Demo Runner

Run:

```bash
python demo/run_local_api_demo.py
```

This calls a running local Codette server and saves outputs under `demo/outputs/`.

It demonstrates:
- chat reasoning
- risk-frontier value analysis
- valuation-aware synthesis

Optional web-enabled run:

```bash
python demo/run_local_api_demo.py --include-web
```

### 2. Copy/Paste API Examples

See [api_examples.md](/mnt/j/codette-clean/demo/api_examples.md) for direct `curl` examples.

## What This Folder Proves

- the public APIs can be exercised locally
- the demos are reproducible
- outputs can be saved as concrete artifacts rather than screenshots alone

## Recommended Flow

1. Start Codette with `scripts\codette_web.bat` or `scripts\codette_web_ollama.bat`
2. Run `python demo/run_local_api_demo.py`
3. Inspect the saved outputs in `demo/outputs/`
4. Compare against the benchmark and proof docs
