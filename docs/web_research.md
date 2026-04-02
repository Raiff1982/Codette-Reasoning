# Web Research

This document explains how Codette's live web research works and what safety filters are applied before results can influence answers or memory.

## Design Goal

Codette's local tools are not general browsing. Live web research is a separate, explicit feature for current facts.

## Trigger Paths

Web research can be enabled in two ways:

1. The `Web Research` toggle in the web UI
2. An explicit phrase in the query such as:
   - `search the web`
   - `look this up online`
   - `check online`

The toggle is permission, not a blanket instruction. A query still has to look like it benefits from current facts unless the user explicitly requests web lookup in the message.

## Current-Fact Gating

Automatic web use is biased toward queries that mention things like:
- `latest`
- `current`
- `recent`
- `today`
- `release notes`
- `docs`
- `price`
- `status`

Reflective or conversational prompts such as `tell me your approach` are intentionally filtered out even if the toggle is on.

## Safety Filters

Implementation lives in [inference/web_search.py](../inference/web_search.py).

Key protections:
- only `http` and `https` URLs are allowed
- localhost and loopback are blocked
- private, reserved, multicast, and link-local IPs are blocked
- fetched page size is capped
- text extraction strips scripts/styles and keeps visible text only
- results are summarized with citations instead of passed through as raw HTML

## Source Flow

1. Search runs through a text-only search endpoint
2. top safe results are selected
3. visible page text is extracted
4. results are summarized into a prompt-safe block with citations
5. sources are shown back to the user in the UI

## Memory Integration

When live research succeeds, Codette can persist it into unified memory as `web_research` cocoons.

This enables:
- cited follow-up answers
- less repeated lookup for the same current-fact question
- visible `web-cited` trust tags in the UI

## Auditing

Evidence and tests:
- [tests/test_event_embedded_value.py](../tests/test_event_embedded_value.py)
- [data/results/codette_runtime_benchmark_20260402_140237.md](../data/results/codette_runtime_benchmark_20260402_140237.md)
- [docs/proof.md](proof.md)
