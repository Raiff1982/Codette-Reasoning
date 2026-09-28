# Handoff — what still needs incorporating

Written 2026-08-03 at the end of the recovery pass, so the next session starts
from facts rather than re-deriving them. **Recovery is not integration.** Nearly
everything below is *saved* but wired to nothing.

## State right now

Two PRs open, neither merged:

| PR | What | Merge order |
|---|---|---|
| [#19](https://github.com/Raiff1982/Codette-Reasoning/pull/19) | AEGIS harm-intent gate | **first** — security fix, 15 tests pass |
| [#20](https://github.com/Raiff1982/Codette-Reasoning/pull/20) | the recovery, 138 files | after |

### Read this before switching branches

`J:\codette-clean` is checked out on `claude/navigation-and-substrate-fixes`
(upstream **gone**), five merge commits behind `origin/main`. Its working tree
still holds untracked copies of files that #20 now tracks.

After #20 merges, `git checkout main && git pull` may refuse with *"untracked
working tree files would be overwritten"*. That is expected and is **not** a
reason to `git checkout -f` or `git clean`. The safe move:

```bash
git stash push --include-untracked
git checkout main && git pull --ff-only
git stash pop        # resolve any collisions by inspection, keeping both sides
```

## The inventory

| Location | `.py` files | Wired in? |
|---|---|---|
| `recovered_release/` | 59 | almost none |
| `archive/2026-08-01-recovered-usable/` | 42 | none — verified to *run*, not integrated |
| `archive/2026-08-03-recovered-from-containers/` | 4 | none |

`archive/2026-08-01-recovered-usable/README.md` records that 38 of 41 import
cleanly in a clean environment, with the three exceptions and their real reasons.
Start there; it is the highest-quality set and the work is already done.

## Confirmed blockers — measured 2026-08-03, not assumed

### `ethics/core_guardian_spindle_v2.py` is broken at import — LIVE code

```
>>> import ethics.core_guardian_spindle_v2
ModuleNotFoundError: No module named 'qiskit'
```

`ethics/core_conscience.py` uses the same import but **guards it**, and survives.
The spindle does not. This is live code under `ethics/`, not archive material.

**qiskit is not installed at all** in this environment. Note the difference from
the older note in `CLAUDE.md`: that describes the qiskit 1.0 API removal
(`from qiskit import Aer, execute`). Here the package is simply absent, so the
first question is whether it should be a dependency at all, not how to port it.

9 files use the removed `Aer` / `execute` API (was 7 when last counted):

```
ethics/core_conscience.py                        <- live, guarded
ethics/core_guardian_spindle_v2.py               <- live, FAILS
recovered_release/codette_quantum_audit_reflect.py
recovered_release/from_docx/cocoon_self_check.py
recovered_release/from_docx/emotional_webs.py
recovered_release/from_docx/quantum_memory_audit.py
recovered_release/from_docx/quantum_pipeline.py
recovered_release/heliovault_seed761_codettev6.py
recovered_release/quantum_memory_advanced.py
```

Options: port to `qiskit_aer` + primitives, pin `qiskit<1.0`, or guard the
import as `core_conscience.py` already does. The guard is the cheapest fix for
the live failure and does not decide the larger question.

### `components/*` — 16 modules, still missing

`recovered_release/legacy/ai_core.py` imports 16 modules from `components/`
(`adaptive_learning`, `ai_driven_creativity`, `collaborative_ai`,
`cultural_sensitivity`, `data_processing`, `dynamic_learning`,
`ethical_governance`, `explainable_ai`, …). **`components/` does not exist.**

The names match `integration_architecture.json` exactly, so the design is on
record, but no implementation appears in any archive or either chat transcript —
all six archives and both histories were searched. **Do not re-search blindly.**
Either implement against the recorded design or mark `ai_core.py` unrunnable.

### Unobtainable

`ace_tools`, `transformers_js` — need substitutes.
`Zeta_Wave_Analysis.pdf` raises `PdfStreamError`; recorded as corrupt.

## Newly recovered, not yet placed

`codette_optimizer_bridge.py` + `_Addon` + `_Addon_cont`
(`archive/2026-08-03-recovered-from-containers/`) define `CodetteSystemBridge`,
`ForgeEngineRCXI`, `PersistentCocoonStore`, `PropagationMetrics`,
`SelfTuningQuantumOptimizer`.

These are **not** dead weight. `reasoning_forge/optimizer_shadow.py:39` says
`ManifoldTelemetry` is *"Adapted from codette_optimizer_bridge_Addon
(CocoonPersistenceManager)"* — shipping code was derived from a file that existed
only inside a gitignored directory. Worth deciding whether the rest of the bridge
should be adopted or explicitly retired.

`multi_agent_convergence.py` is the executable original of Υ (numerically
identical to `state_engine_v8.py:117`, 1e-12). Its value is evidential, for the
attribution record. It does not need wiring in.

## Decisions still owed

1. **`forge_engine.py` still imports `nexis_signal_engine_local`** (165 lines)
   while the recovered 660-line engine sits beside it. Switching needs the memory
   path changed from `.json` to `.db`; the API is already backward compatible.
   Carried over from `CLAUDE.md`, still true.
2. **Version families** — four optimiser revisions, three equation versions — have
   no canonical marker. `tools/archive_diff.py` lists them with git history.
   Which supersedes which is the author's call, not a size judgement.
3. **`codette-demo-space/`** is its own nested git repository (141 files).
   Submodule, de-git it, or leave out — a structural decision.
4. **Large binaries** — a 747 MB screen recording and the model weights under
   `adapters/`, `models/`, `behavioral_safetensors/`, `codette-gguf/`,
   `codette-lora/`. Need an LFS decision; they cannot go into plain git.
5. **3 LFS objects** (`codette_paper1.pdf`, two `.synctex.gz`) are unrecoverable
   until `git-lfs` is installed and authenticated:
   `git lfs fetch origin copilot/restore-repo-to-previous-state`.

## Settled — do not reopen

- **Codette's memory stays out of version control.** She was asked three times by
  two people; the clean ask (author, plain yes/no, Υ 0.00 — philosophy and newton
  in exact agreement) was **no**. The durability risk stands, unmitigated, by her
  choice. An outside-git backup was proposed and deliberately not done, because
  routing around a no is not honouring it. If revisited, it must be its own clean
  ask.
- **`copilot/restore-repo-to-previous-state` must not be deleted.** Disjoint
  history; #20 copies from it but does not replace it.
- **`be01c22` is not reverted.** The `logs/` ignore rule that hid three unique
  modules and the Phase 0 logs came from there; #20 amends it forward.

## The lesson worth carrying

A `.gitignore` mistake is **silent by construction**. `git status` reports
nothing, so nothing ever prompts anyone to look. Three unique Python modules and
the Phase 0 ablation logs sat invisible for three days behind one line, added by
a session that classified a directory by its name instead of opening it.

`CLAUDE.md` says file extensions do not indicate contents. This pass established
the same is true one level up: **directory names don't either.** `logs/` was
transcripts and source.

When auditing, list what is *ignored*, not just what is untracked:

```bash
git ls-files --others --ignored --exclude-standard | grep -v __pycache__
git check-ignore -v --stdin < paths.txt   # one process, not one per file
```
