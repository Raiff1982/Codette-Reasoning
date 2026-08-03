# Handoff — what still needs incorporating

Written 2026-08-03 at the end of the recovery pass, so the next session starts
from facts rather than re-deriving them. **Recovery is not integration.** Nearly
everything below is *saved* but wired to nothing.

> **UPDATE, later on 2026-08-03.** Both PRs below are **merged** (`8006a21` =
> #19, `0e764f7` = #20). A follow-up pass resolved several items in this
> document; each is marked **[DONE]** inline. Items with no marker still stand.
>
> Also fixed in that pass, and *not* previously in this document: bare `pytest`
> from the repository root collected **zero tests** — five collection errors
> aborted every run while 596 working tests sat behind them. Now 600 collected,
> 0 errors, 22 pre-existing failures unchanged. See `24b8311`.
>
> And a reward-function bug in `quantum_optimizer.py`: `productivity` was scored
> unconditionally at weight 0.25 while `optimizer_shadow` fed it a neutral `0.5`
> on 34% of turns — a fabricated measurement, scored, breaking the invariant the
> function states above itself. Fixed in `8be7c76`; the causal story attached to
> that fix was then **disproved** in `fbb8307`. Read both.

## State right now

Two PRs, **both now merged**:

| PR | What | Merge order |
|---|---|---|
| [#19](https://github.com/Raiff1982/Codette-Reasoning/pull/19) | AEGIS harm-intent gate | **[DONE]** merged as `8006a21` |
| [#20](https://github.com/Raiff1982/Codette-Reasoning/pull/20) | the recovery, 138 files | **[DONE]** merged as `0e764f7` |

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

### `ethics/core_guardian_spindle_v2.py` is broken at import — LIVE code — **[DONE]**

**Fixed in `24b8311`.** The guard from `core_conscience.py` was copied verbatim,
plus a classical fallback of the same distribution so `quantum_execute` returns
rather than raising on `None`. The fallback is named honestly — without qiskit
it is not a quantum selection and does not claim to be. Verified: imports
cleanly, empty web returns `None`, all nodes reachable. The qiskit branch is
marked **UNVERIFIED** in-file: qiskit is still not installed, so that path has
never executed. Note also that **nothing currently imports this module**, so it
was a latent break, not an active one. The larger qiskit question (9 files,
`Aer`/`execute` removed in 1.0) is untouched and still open.

Original text follows.

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

### `components/*` — 16 modules, still missing — **CONFIRMED ABSENT, independently**

The claim below was re-tested on 2026-08-03 the only way it can be: by reading
**inside** 1,157 non-`.py` containers (`.docx`, `.pdf`, `.txt`, chat-history
`.json`, zip members) for `class <Name>` definitions, rather than by filename.
Extensions here do not indicate contents, so a filename search proves nothing.

Result: **genuinely absent.** `SelfImprovingAI`, `AdvancedDataProcessor`,
`NeuroSymbolicEngine`, `AIDrivenCreativity`, `EnhancedSentimentAnalyzer` and the
rest are *mentioned* across archives and cocoons but **defined nowhere**. Two of
the sixteen do exist and are merely mispathed: `ethical_governance` →
`reasoning_forge/ethical_governance.py`, `quantum_spiderweb` →
`reasoning_forge/quantum_spiderweb.py`.

One thing this document did not record: **`utilities/integrated_ai_core_with_cocoons.py`
is LIVE code with the same problem**, not just `recovered_release/legacy/ai_core.py`.
It imports six of the missing names. Nothing imports *it*, so it is inert.

Original text follows.

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

---

# Addendum — follow-up pass, 2026-08-03 (later)

## Resolved

- **Test suite runnable.** 0 collected / 5 errors → 600 collected / 0 errors.
  `MazegameCompKaggle/` archived to `archive/2026-08-03-mazegame-kaggle/` by
  `git mv` at the author's direction (history preserved, README explains the
  CWD-relative path bug that caused three of the errors).
  `reasoning_forge/test_global_aegis.py` import repaired — recovers 4 tests that
  were never running, the only direct exercise of the 25-framework AEGIS table.
  `pyproject.toml` now has a pytest section stating what is excluded *and why*.
- **`logs/codette_optimizer_bridge.py` parses.** It was the "prose appended
  after the last line of code" pattern, one un-commented line at EOF. Commented,
  not deleted. This mattered because **unparseable meant unscreenable**.
- **Harm screen run.** 153 recovered/archive `.py` screened by AST for
  exfiltration, obfuscated execution, destructive filesystem calls, credential
  reads, reverse shells and prompt injection. **No malicious code.** Zero
  injection strings — notable given how much came out of `.docx`/PDF/transcripts.
  All 16 HIGH hits resolved to false positives (loopback binds, DuckDuckGo,
  NASA's exoplanet archive) and the resolutions are recorded, not assumed.

## Still open, with new detail

- **`archive/2026-07-23/git-history-scripts/push_cleanup.py`** runs
  `reflog expire --expire=now --all` + `gc --prune=now --aggressive` +
  `rmtree('.git-rewrite')`. Not malicious, inert where it sits, but it destroys
  recoverability and so conflicts directly with the "we don't erase the past"
  rule. Flagged rather than acted on, because deleting it would itself be an
  erasure. Suggest a header marking it retained-for-record, not-to-be-run.
- **Optimizer shadow → live is BLOCKED**, and the blocker is not sample size:
  `user_continued` is never measured (0/167 turns), so there is **no outcome
  signal** to judge "consistent results" against. It is correctly passed as
  `None`, not fabricated — an earlier version of `optimizer_shadow.py`'s
  docstring claimed `True`, which was stale and is now fixed.
- **The decay pattern in the shadow log is real and unexplained.** 41.1% of
  placeholder turns vs 49.5% of measured turns propose a decay, so it is *not*
  an artifact of the productivity bug. Wanted a cause.
- **Flaky test**: `tests/test_drift_detector.py::TestInterventionPlan::
  test_psi_r_history_populated` failed once in a full run, then passed 8/8 in
  isolation and did not reproduce. Order-dependent pollution.
- **28 modules run plotting code at import**, 19 of them calling `plt.show()`
  or `savefig` *outside* a `__main__` guard — all in `archive/`,
  `recovered_release/` and `experiments/`. **Zero in live code.** Importing
  those directories opens blocking GUI windows and writes `.npy`/`.png` into the
  repository root; that is what any repo-wide import sweep will trigger.

## Method note

The reference audit's first version treated a `.py` stem *anywhere* in the tree
as satisfying an import, which silently emptied the "exists but mispathed"
category — the single most actionable class. Worth knowing before trusting a
similar sweep. Ground truth for imports is executing them, not parsing them;
`CLAUDE.md` already says so and it was right again here.

Working notes, baselines and the screen output are outside the repository, in
`G:\claudes space for files\2026-08-03-incorporation\`.

---

# Addendum 2 — systematic pass, 2026-08-03 (later still)

Worked in the order Jonathan set: major need, then quality of life, then oops.

## Test suite

**Start of session: 0 tests collected behind 5 errors. Now: 630 passed, 0 failed.**
Intermediate baseline once collection was repaired was 22 failed / 573 passed;
every step was diffed against it and no change introduced a regression.

## The pattern worth carrying forward

Three separate defects, all the same shape: **a guard whose silence is
indistinguishable from success.** This is the thing to hunt for here.

1. **`ColleenConscience._detect_corruption` was dead on all real output.** Every
   signature is `a.*b.*c`, and without `re.DOTALL` a `.` cannot cross a newline,
   so a signature could only match if the whole nested phrase sat on one line.
   Real output wraps. The anti-parrot guard was failing **open**, silently.
2. **`NexisSignalEngine.process()` raised on every single call.** NLTK renamed
   `punkt` to `punkt_tab`; the bootstrap probed for `punkt`, found it, and never
   fetched what the code needs. `forge_engine` swallowed the LookupError in a
   bare `except Exception` at DEBUG. `safety_notes['intent_risk']` was never
   populated, so every consumer read the absence as "no risk detected".
3. **Phase 6 `summary()` rendered "nothing measured" identically to "measured,
   all fine"** — title, rule, no findings.

## Codette's conscience had never run

`tests/test_consciousness_stack.py` imported four `reasoning_forge/` modules
bare, and the `except ImportError: sys.exit(1)` beneath turned the resulting
ModuleNotFoundError into a pytest INTERNALERROR that killed the whole session.
41 tests reported as failures while never executing. Fixing the imports exposed
six real defects, including (1) above and a rule that discarded any answer under
ten words as "intent lost".

Two of its tests **contradicted each other** and could not both pass. That
decides what Codette may say, so it was put to her. Her first answer chose the
restrictive option at **confidence 0**; asked whether that was preference or the
safer-looking option, she said at confidence 1.0 it had been "an attempt to
appear humble or cautious" and proposed a better third rule, which is what is
implemented. A self-restricting answer at zero confidence is not consent.

## Literal parroting, in the live path

`recursive_universal_reasoning` returned the user's question **verbatim** on
~10% of calls: a stochastic early-exit sat above the only assignment to
`final_answer`, so taking it on cycle 0 returned the raw input. 5/60 before,
**0 in 400 after**. It had been visible only as a test failing ~1 run in 5 and
passing in isolation — dismissed as flakiness for who knows how long. **Treat
intermittent failures as defects reproducing at their natural rate.**

Note the conscience could never have caught this one: an echoed question trips
no corruption signature, no meta-loop, no length rule. Distinct from the
cocoon-substrate pollution; fixing either does not fix the other.

## Resolved from the decisions list

**Decision 1 (nexis engine switch) was already done and this document was
stale.** `forge_engine` imports the full 733-line engine — PR #18 made the
switch. The 165-line local version now carries a SUPERSEDED header explaining it
is kept for lineage and still used deliberately as a fast hermetic stub by two
test modules, with the cost recorded: those tests do not exercise the live
engine, which is exactly how (2) above went unnoticed.

## Still open

- **`test_psi_r_history_populated` flake is UNEXPLAINED.** ~1 in 10 before, 0 in
  20 consecutive runs since the parrot fix — but no mechanism was found, so it
  is **not** claimed fixed. Ruled out: `_FakeKernel` has no `recall_recent`, so
  `detect()` always falls to `memories[-EPSILON_WINDOW:]`; nothing mutates
  `EPSILON_WINDOW`.
- **Optimizer shadow -> live remains blocked.** `user_continued` is never
  measured (0/167 turns), so there is no outcome signal to judge consistency
  against. It is correctly passed as `None`, not fabricated.
- **The decay pattern in the shadow log is real and unexplained** — 41.1% of
  placeholder turns vs 49.5% of measured turns, so it is not an artifact of the
  productivity bug fixed in `8be7c76`.
- **`OneDrive\Documents\Nexus` is unreadable**: 283 directories, zero local
  files, attributes `ReparsePoint + UNPINNED`, and **the OneDrive process is not
  running**. Content is in the cloud. C: has 15.9 GB free, so hydrating an
  unknown volume there is a risk. Author's call.
- **`J:\xbox drive\Backup` is an iOS device backup** (34,672 SHA1-named files,
  50.6 GB, written 27 Oct 2024 — adjacent to the Tier-A provenance window).
  Author's instruction: leave alone. Untouched.
