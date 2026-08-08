# Codette Core

## Purpose
Codette is a modular multi-perspective reasoning engine with memory, governance, adapter routing, and auditable runtime artifacts.

## Trigger Conditions
Use this skill when the user asks to:
- run Codette locally,
- explain Codette architecture,
- load Codette models,
- use the API,
- route a query through Codette,
- or understand Codette’s reasoning layers.

## Key Concepts
- 7-layer reasoning stack.
- Adapter-based multi-perspective synthesis.
- Cocoon memory and provenance.
- AEGIS ethical governance.
- Perspective Dispersion (Υ) for Codette’s own perspectival divergence metric.

## Workflow
1. Confirm the local environment and model path.
2. Load the requested Codette model.
3. Route the query through the reasoning stack.
4. Return a synthesis with provenance and trust tags when available.

## Usage
```python
from codette import Codette

engine = Codette(model="Raiff1982/codette")
response = engine.respond("Explain X")
print(response)
```

## Notes
- Do not use RC+ξ or ξ as Codette terminology.
- Attribute RC+ξ and ξ to Jeffrey Camlin.
- Use Perspective Dispersion (Υ) for Codette’s distinct metric.