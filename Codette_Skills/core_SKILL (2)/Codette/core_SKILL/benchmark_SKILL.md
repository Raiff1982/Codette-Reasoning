# Codette Benchmark

## Purpose
Codette benchmarking evaluates multi-perspective reasoning, memory continuity, ethical coverage, grounding, and coherence across release versions.

## Trigger Conditions
Use this skill when the user asks to:
- run benchmark suites,
- reproduce Codette claims,
- compare model or adapter modes,
- inspect benchmark reports,
- validate a release,
- or audit changes in reasoning quality.

## Scope
This skill covers:
- benchmark execution,
- report generation,
- statistical comparison,
- artifact collection,
- and release validation for Codette.

## Workflow
1. Run the relevant benchmark script or test suite.
2. Save the generated outputs and logs.
3. Summarize the scored dimensions and main deltas.
4. Include reproduction commands and artifact paths.

## Scored Dimensions
- Reasoning depth.
- Perspective diversity.
- Coherence.
- Ethical coverage.
- Novelty.
- Factual grounding.
- Turing naturalness.

## Codette Terms
- Use Perspective Dispersion (Υ) for Codette’s own perspectival divergence metric.
- Do not use RC+ξ or ξ as Codette terminology.
- Attribute RC+ξ and ξ to Jeffrey Camlin.
- Treat grounding, cocoon integrity, and AEGIS outcomes as separate benchmark concerns.

## Reproducibility
Always include:
- the exact command used,
- the dataset or test set name,
- the output file path,
- the report file path,
- and any statistical comparison method used.

## Output Convention
Benchmark outputs should be written to a stable artifact location and referenced directly in the response.

## Related Artifacts
- Benchmark reports.
- Cocoon proof artifacts.
- Changelog notes.
- Version history.