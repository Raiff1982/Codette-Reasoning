# Adapter Workflow

This is the shortest practical guide for adding or improving an adapter in Codette.

## What To Define

For a new adapter, document:
- the adapter name
- the reasoning role it fills
- what kinds of prompts should route to it
- how it should differ from base behavior

## Where It Hooks In

Key files:
- `inference/codette_orchestrator.py`
- `inference/adapter_router.py`
- `configs/adapter_registry.yaml`
- training scripts under `training/`

## Typical Steps

1. Add or update the adapter entry in the registry/config.
2. Add or adjust routing logic so the adapter is reachable.
3. Update prompts or mode instructions if needed.
4. Add tests for:
   - routing selection
   - response shape
   - any failure modes or constraints
5. Add benchmark or transcript evidence if the adapter changes major behavior.

## Behavioral LoRA Notes

If you train or update a behavioral adapter:
- record the dataset source
- record the training objective
- document what permanent or semi-permanent behavior it is meant to stabilize
- add at least one reproducible validation artifact

## Verification

At minimum:

```bash
python3 -m unittest tests.test_adapters
python3 -m unittest tests.test_phase7_executive_controller
```

Then add a benchmark or demo artifact if the adapter meaningfully changes public behavior.
