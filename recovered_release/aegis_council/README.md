# AEGIS Council — a recovered version family

Recovered 2026-08-10 from three OneDrive archives Jonathan supplied
(`OneDrive_1/2/3_8-10-2026.zip`). Nothing here had ever been committed to this
repository in any form.

**Nothing here is wired into anything.** It is committed so the family is under
version control and reviewable. Which revision supersedes which is the author's
call, not a judgement to make from line count — so all of them are kept.

## This is NOT the AEGIS in `Protection_Layer/`

Worth stating first, because the name collision is total and the systems are
not related.

| | `Protection_Layer/` (live) | this directory (recovered) |
|---|---|---|
| what it is | a security layer | a deliberating council |
| symbols | `PQCShield`, `HarmAdvisor`, `EpistemicQuantumGate`, `PreEmptiveImmuneEngine`, filesystem lockdown | `AegisCouncil`, `VirtueAgent`, `TemporalAgent`, `MetaJudgeAgent`, `NexusMemory` |
| overlap | **zero shared symbols, measured** | |

So this is not an ancestor that got superseded, and the live code is not a
descendant of it. They are two different things wearing one name. Do not "merge"
them on the strength of the name.

## The lineage

Verified by parsing each revision and diffing top-level symbol sets — not by
filename or date. The pivot is `aegis7`.

| file | lines | syms | change from the previous |
|---|---:|---:|---|
| `aegis1.py` | 95 | 4 | `AegisAgent`, `AegisCouncil`, `EchoAgent`, `NexusMemory` |
| `aegis2.py` | 124 | 4 | `EchoAgent` → `EthosiaAgent` |
| `aegis3.py` | 159 | 6 | `+AegisCore`, `+SapientiaAgent` |
| `aegis4.py` | 166 | 6 | refinement, no symbol change |
| `aegis5.py` | 222 | 7 | `+run_cli` |
| `aegis6.py` | 228 | 6 | `−run_cli` |
| `aegis7.py` | 210 | 6 | **the pivot** — drops `AegisCore`, `EthosiaAgent`, `SapientiaAgent`; adds `VirtueAgent`, `TemporalAgent`, `MetaJudgeAgent` |
| `aegis8.py` | 208 | 6 | repaired; see damage below |
| `Aegias101.py` | 378 | 7 | `+main` |
| `aegis_council.py` | 378 | 7 | same symbols as `Aegias101`, **different bytes** |
| `aegis_council2.py` | 584 | 8 | `+DataFetcher` |
| `aegis_council3.py` | 673 | 14 | `+index`, `+load_config`, `+setup_logging`, `+show_graph`, `+show_reports`, `+monitor_performance` — a web/dashboard layer |
| `aegis_council4.py` | 833 | 18 | `+Blockchain`, `+FederatedTrainer`, `+anneal_layout`, `+show_charts` |
| `aegis_council5.py` | 815 | 18 | same symbols as `4`, **different bytes** |
| `aegis_council_1.py` | 818 | 18 | same symbols as `4`, **different bytes**; repaired |

**Three pairs share a symbol set but differ byte-wise** — `Aegias101`/
`aegis_council`, and `aegis_council4`/`5`/`_1`. They are refinements, not
duplicates, which is exactly why collapsing them would destroy the lineage.

`aegis_council4.py` is the largest and symbol-richest, but *largest is not
canonical*. No revision carries a marker saying which one won.

## `imortal.py` is a rewrite, not a revision

Recovered from `OneDrive_3!aegis/imortal.txt` — a `.txt` file containing 602
lines of Python. It drops `AegisAgent`, `AegisCouncil`, `Blockchain` and
`DataFetcher` **entirely** and rebuilds around `AegisImmortalCouncil`,
`MetaCouncil`, `BaseAgent`, `HealthAgent`, `RegenerativeMemory`, `Snapshot`,
`AgentResult`, `MemoryEntry`.

It is also **the only file here that executes cleanly on import** — the
`aegis_council*` revisions need `plotly` for their dashboard.

Its `HealthAgent` / `RegenerativeMemory` / `Snapshot` are the closest thing in
any recovered material to the health-monitoring gap noted elsewhere
(`check_health` returns zero hits across `reasoning_forge`, `inference`,
`consciousness`, `ethics`).

## Damage, and what was repaired

Both repairs are documented instances of patterns already in `CLAUDE.md`. In
both cases the **as-found file is kept alongside**, suffixed so it cannot be
mistaken for loadable source.

**`aegis8`** — `aegis8.as-found.txt` opens with three lines of chat-UI chrome:

    Always show details

    Copy
    import json

Repaired in `aegis8.py` by dropping those three lines. Nothing else altered.

**`aegis_council (1)`** — `aegis_council_1.as-found.txt` fails to parse at line
414, because the identifier `collaborate` is split across a line break at render
width:

    413 |                     agent.collabora
    414 | te(agent.result, target.name)

Repaired in `aegis_council_1.py` by rejoining those two lines. Nothing else
altered. Note this is the line-wrap pattern *inside an identifier*, which
`tools/archive_diff.py`'s bracket- and operator-aware `rejoin_wrapped` does not
catch.

## Also here

- `custom_agent.py` (21 lines) — the extension point for adding an agent.
- `AegisCouncil.ts` (130 lines) — a TypeScript port, from
  `cobalt.zip!project/src/services/AegisCouncil.ts`. Kept as `.ts`; it is not
  Python and does not parse as such.
- `README.as-found.markdown` (117 lines) — the family's own README as found in
  `AGEIS.zip!aegis/`. Suffixed `.as-found` because it describes the recovered
  set on its own terms, not this directory.

## Substance

Measured, not eyeballed: stub ratios across this family run **4–14%**
(a method counted as a stub if its body is only `pass`, `...`, a bare docstring,
`return None`, or a bare `raise`). For comparison, the `components/*` material
recovered the same day ran 50–100% stubs and raised `NameError` when called.

Markers of real work present throughout: `sqlite3`, `numpy`, `hashlib`,
`threading`, structured exception handling, regex.

That says these are working systems rather than design skeletons. It does **not**
say they are correct, and none of them has been run beyond import.

## Open questions for the author

1. Which revision is canonical? Nothing in the files answers this.
2. Are `Blockchain` and `FederatedTrainer` in `aegis_council4` load-bearing or
   aspirational? Not yet read closely.
3. Does the `imortal` rewrite supersede the council line, or is it a parallel
   experiment?
