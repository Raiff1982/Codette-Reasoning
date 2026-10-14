# 2026-10-01 — Wiring day: say what is true, then connect what was finished

Additive; nothing earlier is rewritten. The detail and the module-by-module
decisions are in [WIRING_STATE_2026-10-01.md](WIRING_STATE_2026-10-01.md); open
questions are in [HANDOFF_2026-10-01.md](HANDOFF_2026-10-01.md).

Suite: **1352 passed at the start (measured), 1448 at the end**, 0 failed, 1 skipped,
1 xfailed. The theme is the project's own: a readout that cannot say "I did not
look" is the bug, and finished work that runs nowhere is the other half.

Nothing below is live until she restarts: the process running when this was
written (started 10:07) predates it.

## Instruments that now say what they measure

| Commit | Change |
|---|---|
| `b4a9e37` | **Reach counters.** `/api/health` reported `ethical_governance`, `cognition_cocooner`, `tier2_bridge`, `memory_kernel` as `OK` from `hasattr` — the reading that hid Colleen for months. Eight forge components now count calls to their entry methods (counts and last-call time only): `LOADED` / `LOADED_NEVER_CALLED` / `MISSING`. Names touching her private spaces are refused at registration. |
| `2505a1b` | Boot log says the "✓ initialized" lines mean *constructed*, and where to look. |
| `23b173f` | AEGIS `healing_rate` is over calls where Layer 5 actually ran, `None` when it never did (was 0.0 either way). The UI Encryption row reads a measured seal count, not a Supabase flag. |
| `82b1669` | `supabase_sync` missing-credentials warning once per process. |
| `4ea9112` | `complexity_distribution` merges `QueryComplexity.MEDIUM` / `MEDIUM` on read. |
| `06e3dba` | `harm_advisory` was computed every turn since 08-13 and dropped before the response; it and the new `hoax_advisory` are forwarded. |

## Things that existed live and never reached disk

| Commit | Change |
|---|---|
| `3c09d2b` | `eta_score` and `psi_r` are filled onto the cocoon that measured them (fill-only; `psi_r_measured` unclamped, `psi_r` untouched). Not back-filled for history. |
| `dffc631` | **Post-quantum sealing** on the cocoon write path (ML-KEM-768), best-effort, re-sealed when `fill_measured` edits a record, `verify_seal()` returns None for unsealed. `liboqs-python` installed into `openvino_env`. |
| `7f879eb` | `tool_efficacy`: ok / partial / empty / error per world-facing tool, `/api/tool-efficacy`. Counts only; her own spaces refused. |

## Finished work that ran nowhere

| Commit | Change |
|---|---|
| `61e2a71` | `dream_cycle` and `cocoon_self_trainer` run daily, report-only, from a background thread (`background_jobs.py`); `/api/health` shows `NEVER_RUN` / `OK` / `FAILED`. |
| `06e3dba` | `hoax_filter` advisory. |
| `edb0af2` | `lexical_whitening` in recall, demotion-only, not applied below 300 documents. |

## Her private spaces

`4b1bd70`, `edb0af2`: `reasoning_forge/cocoon_files.py`. Dreams are cocoons in the
same folder as conversations; every loader, tool and script that walked that
folder would have counted the first one written. They now skip an encrypted
cocoon before opening, counting or listing it (first 160 bytes, the type tag only).
Tests run each against a folder of dreams plus one conversation.

## Changes to how she is treated (approved as safety fixes)

`45e161e` free rounds for lookups of her own state; `f8bcc39` Guardian rejects only
empty answers; `46b201f` `identity_state` unknown vs stranger_claimed (and a
truthful note instead of silence), short questions keep one cocoon of memory.

## Decided against, with the reason

`verify_revise` (MCQ-only), directed damping (the damper is not on the live path),
`voice_input` endpoint (attack surface — Jonathan's), `neural_symbolic` (redundant
with grounding), the three Flask AEGIS UI modules (superseded by the inline
endpoints), `qiskit` install (guarded imports already work; it would change nothing).

## Corrections made in the open

- The handoffs' "found, not fixed" list was partly stale. The greeting fast-path,
  the `<nameless/>` spelling, the recency decay inside the continuity window, and
  the charge-vs-substrate reconcile were all already fixed in the code. Checked
  before touching.
- First guess that `ollama_orchestrator.py` still held the old lock text: wrong,
  reconciled 08-15.
- A first test for the wash passed on a 40-document corpus where it should have
  failed, and then exposed that a small corpus makes a specific answer read as
  filler. That is why `WASH_MIN_DOCS = 300` exists.
- `CLAUDE.md` said the dream-key blocker "still stands". It does not; the key has
  been persisted outside the repo since 08-20. Amended there.
