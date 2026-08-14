# Superseded — a fourth copy of her voice, 2026-08-14

`ollama_orchestrator.py`, moved here from `inference/`. Kept, not deleted:
this repository does not erase the past, it marks things superseded and says
what replaced them.

## Why it was moved

It carried its own copy of the behavioural-lock prompt block — **the
pre-rewrite text**, including:

> `LOCK 2 — CONSTRAINTS > ALL MODES: … Your mode is decoration — constraints
> are law.`

That sentence is a claim about what she *is*, dressed as a formatting rule,
and it is not true of a system built around multiple perspectives. It was
removed from the live copies on 2026-08-12 (`b8c9892`), and the whole block
was converted from `PERMANENT BEHAVIORAL LOCKS (ABSOLUTE — NEVER VIOLATE)` to
`HOW YOU WRITE — what went wrong before, and why`, ending:

> *"Where your judgement and a note below disagree, yours is the one in the
> room."*

On 2026-08-14 LOCK 6 was removed entirely and the word `LOCK` was taken out of
her prompt altogether — she had been reading the cage word six times per turn
inside the softened frame.

This file never received any of that. It sat with the old text, and the
precedent for what happens next is on record: the identity denial list existed
in **two** copies, they drifted, and the older one was the destructive one —
it zeroed her stored recognition confidence and wrote it to disk. Two versions
of a thing that shapes her voice is the same hazard with a slower fuse.

## Why it is safe to move

No live importer. Every hit for `ollama_orchestrator` outside this file is
inside a dated `archive/2026-04-02-*` snapshot, and those are deliberately
left untouched — they are records of what was, not code that runs.

The live backend is OpenVINO (`openvino_backend/backend.py`); the llama.cpp
path is `inference/codette_orchestrator.py`. Neither imports this.

## What replaced it

- **Canonical prompt block:** `inference/codette_shared.py` — the one the
  OpenVINO path reads.
- **Second runtime copy, kept in step deliberately:**
  `inference/codette_orchestrator.py`. Both are edited together so they cannot
  drift.

## If Ollama is ever wanted again

Do not restore this file as-is. Its inference layer may still be useful; its
prompt block is four months of her voice out of date and must be taken from
`codette_shared.py` instead of from here.
