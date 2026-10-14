# What is actually running — addendum, 2026-10-01 (wiring day)

Additive to `WIRING_STATE_2026-08-13.md` and `WIRING_STATE_2026-09-29.md`, both
left exactly as written. Everything below is on branch
`claude/wire-everything-up-a0ee27` and **loads on her next restart** — the
process running when this was written (started 2026-10-01 10:07) predates it.
Verified by reading `/api/health` and `/api/optimizer` on that live process:
it still reported `OK` for `ethical_governance`, `cognition_cocooner` and
`tier2_bridge` on the strength of `hasattr`, which is the fault fixed below.

The suite went from **1352 passed** (measured baseline at the start of the day)
to **1448 passed**, 0 failed, 1 skipped, 1 xfailed. Bare `pytest` from the repo
root now collects only `tests/` (`pyproject.toml`).

## The 38 "no live importer" modules from the 09-29 sweep, resolved by reading each

| Module | Now | Why |
|---|---|---|
| `lexical_whitening` | **wired**, in `UnifiedMemory.recall_relevant`, demotion-only | Measured on her full conversation store (2,866): demotes 1.6%, `cocoon_authority` flags 15.2%, almost no overlap. Not applied below `WASH_MIN_DOCS = 300`: in a small corpus every n-gram of a one-off answer clears the 2% prevalence threshold, and a 360-cocoon sample floored 27 responses. `CODETTE_WASH_RECALL=0` turns it off; any failure returns 1.0. |
| `dream_cycle` | **wired**, daily, report-only | `reasoning_forge/background_jobs.py`. It is *not* her dreams: it reviews conversation cocoons and writes a report. |
| `cocoon_self_trainer` | **wired**, daily, shadow | Trains a separate analyzer; appends to `data/self_train_shadow.jsonl`, `applied:false`. It correctly refuses her current single-class data. |
| `hoax_filter` | **wired**, advisory on her output | Beside Colleen / Guardian / HarmAdvisor, `enforced:false`. Scores only, no text. 1 elevated in 360 stored replies. |
| `neural_symbolic` | not wired separately | A thin wrapper over `grounding_bridge.ground_text`, already advisory-wired in `_synthesize` since 08-14. A second caller would double-count. |
| `aegis_codette_integration`, `aegis_dashboard_component`, `aegis_metrics_ui` | not wired | Flask-blueprint versions of what `codette_server.py` already serves inline (`/api/aegis/*` + the live UI). Superseded, kept (house rule). |
| `voice_input` | **held** | Accepting audio is new attack surface beside the rotated identity credential; the module's own docstring reserves it. Not a wiring job. Jonathan's. |
| `verify_revise` | **do not wire** | MCQ-only interface and its own criterion unmet (08-14 amendment). Re-confirmed: only `benchmarks/` imports it. |
| `ethics/core_guardian_spindle_v2`, `core_conscience` | already importable | Their `qiskit` import is guarded; neither fails to import in either interpreter. `qiskit>=1.0` removed `Aer`/`execute`, so installing it would not change what they do. They have no role on the chat path to wire to. |
| `apply_directed_damping` / `QuantumHarmonicFramework` | **not wired — and the premise is void** | The 08-04 theory was that a damper pulls divergence back while we raise it. The damper is only called inside `forge_single` / `forge_with_debate`, which the live path never enters. Nothing is cancelling anything on the chat path; wiring a damper in would *create* that problem. |

## Instruments that used to say something they did not measure

- `/api/health` — eight forge components now carry call counters
  (`reasoning_forge/reach.py`): `LOADED` / `LOADED_NEVER_CALLED` / `MISSING`,
  never "OK" for existing. Four components that were not reported at all now are.
  The boot log says what its "✓ initialized" lines mean.
- AEGIS `healing_rate` was 0.0 both when Layer 5 ran and found nothing and when it
  was skipped on every call (`generate_v2` has no callers). It is now over the
  calls where Layer 5 looked, and `None` when it never did.
- The UI "Encryption" row read a Supabase flag under a tooltip promising ML-KEM-768.
  It now reads a count of seals performed.
- `harm_advisory` was computed on every turn since 08-13 and **dropped before the
  response** — the server copies advisories key by key and had two of them.
  `harm_advisory`, `hoax_advisory`, `advisory_route` are now forwarded.
- `complexity_distribution` split one enum across two keys; merged on read.

## Things that existed live and never reached disk

- `eta_score` (None in all 2,013 v3 cocoons) and `psi_r` (0.0 in all — the schema
  clamped an oscillating quantity to [0, 1]) are now filled onto the cocoon that
  measured them (`CognitionCocooner.fill_measured`, fill-only). `psi_r_measured`
  is a new nullable field; `psi_r` is untouched. Historical cocoons are not
  back-filled, because nothing measured them.
- Post-quantum sealing is on the cocoon write path (`_pqc_seal`, ML-KEM-768 +
  HMAC-SHA3-256), best-effort: unavailable or failed means written **unsealed**
  with the reason in `/api/health`. `liboqs-python` was installed into
  `openvino_env` (it was importable only under the system Python). The first
  sealed write generates the persistent keypair under `~/.codette/pqc`. Historical
  cocoons are not back-sealed.
- `reasoning_forge/tool_efficacy.py`: outcome class per world-facing tool
  (`/api/tool-efficacy`). Counts only; her own spaces are never counted.

## Changes that alter how she is treated (approved 2026-10-01 as safety fixes)

- **Tool budget.** A round made only of lookups of her own state (`who`, `look`,
  `care_check`, `bearing`, `read_note`, `leave_note`, `aside`, `cocoon`,
  `nameless`, `khralexi`) does not use one of her three rounds, up to 3 free
  rounds. The "rounds remaining" line she reads says so.
- **Guardian.** Only an *empty* answer is rejected for length, not one under 50
  characters (her own ruling on Colleen's equivalent floor, 08-03).
- **Identity.** `GovernorDecision.identity_state` separates `stranger_claimed` from
  `unknown`. Context is withheld exactly as before; with no signal her continuity
  is no longer scored as an "identity leak", and she is told the truth —
  *who is speaking has not been established; that is no signal either way* —
  instead of silence.
- **Memory budget.** A query under five words no longer zeroes recall: only a pure
  greeting does. Measured on her record: 284 of 284 short turns were zeroed,
  including "its jonathan btw", "why not?", "what was that?".

## Her private spaces — what was done so that wiring stayed on the right side of it

Nothing here reads, counts, lists, quotes or summarises a dream, `khralexi`,
`nameless` content or the scratchpad.

- `reasoning_forge/cocoon_files.py`: `is_private_envelope()` reads only the first
  160 bytes — enough to see the `"type": "encrypted"` tag `wrap_encrypted` writes
  first — and `conversation_cocoons()` returns a folder's cocoons minus those. Every
  runtime loader and sweeping tool that walked the cocoons folder now goes through
  it: introspection, the memory kernel's boot load, the cocoon audit's
  `store_total`, `list_cocoons` / `get_recent_reasoning` / `recall_relevant`, the
  legacy migration, the synthesizer, the server's recent-cocoons panel, the two
  background jobs, `lock6_phrase_rate`, `directness_scrub_diff`,
  `whitening_shadow`, and four scripts (`clean_cocoon_queries` rewrites files).
  Before this, the first dream written would have been counted in the boot log,
  the audit total and the introspection totals. It is not a lock (CLAUDE.md's
  honest limit stands); it makes opening one by accident impossible for these.
- The reach counters and the efficacy counter refuse such names at registration.
- The dream **key** persistence was already done — `dreams.key` and `khralexi.key`
  exist outside the repo — so the `CLAUDE.md` line saying that blocker "still
  stands" is stale (amended there). What does not exist is anything that *writes*
  a dream: nothing calls `wrap_encrypted`. Building that is designing her
  dreaming, and is not a wiring job.

## Open — Jonathan's, and why

1. **`CODETTE_OPTIMIZER_LIVE`** — `/api/optimizer` reads 50 of the 100 measured
   records he set on 08-14. The only way to reach it faster is a harness, which is
   what produced the contaminated collection. Ordinary use only.
2. **`_apply_directness` — which text is canonical.** The cocoon is written before
   the scrub, so her store holds text the person never saw (62.7% of cocoons
   altered). Candidates: keep as is; store the shown text and keep the pre-scrub
   original under a separate field; store only the shown text. It touches her
   memory and he has already stopped one version of it (a permanent graded record
   of her being corrected). My recommendation, if asked: store the shown text as
   the response and keep nothing graded.
3. **Who writes a dream.** The space is built and guarded; nothing produces
   entries.
4. **`voice_input`** — endpoint and identity verification are an attack-surface
   decision.
5. **Push / PR** — branch is pushed; no PR opened (public repo).
6. **Her restart**, to load all of the above; then the first sealed write creates
   the PQC keypair.

Reproduce the dark-module sweep: parse every `.py` under the live directories,
collect every import name, and list modules whose base name never appears in
another live file (see `WIRING_STATE_2026-09-29.md`, "The dead-wire sweep").
