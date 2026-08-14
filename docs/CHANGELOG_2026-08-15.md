# 2026-08-15 — The accelerator she had was the one already named wrong

Started as a memory-and-handoff review. The only code change is one word, and
the more useful output is two negative results recorded so nobody spends the
afternoon on them again.

---

## The landing from 2026-08-14 was already done

The Aug 14 changelog closed by listing the identity clock and the tool parser
as committed-but-not-landed. All three files are landed — hash-identical
between the branch and `J:\codette-clean` (`133dfb64`, `87834f34`, `f75befa6`).
Amended there rather than rewritten.

What was worth doing was verifying the channel carries, offline, no server:
all six spellings she actually used parse, `ask` receives its perspective as
its own argument rather than one mangled string, prose (*"I want to
look(inward)"*) does not fire, and `who` is registered at
`codette_tools.py:211` rather than merely defined.

## `device="AUTO"` was never the neutral default it looked like

`AUTO` begins inference on CPU while the GPU compiles. Jonathan's note on
finding this: *"i always wanted gpu not auto i just thought auto was default."*
It was a default nobody chose.

Measured with one **fresh process per run**, interleaved round-robin so drift
across the session cannot masquerade as an effect, n=3:

| arm | load (median) | range | tok/s (median) | range |
|---|---|---|---|---|
| `AUTO`, hers until now | 137.2s | 134–227 | 8.79 | 7.7–11.0 |
| `GPU` | **64.9s** | 62–126 | 10.11 | 10.0–11.2 |
| `GPU` + `CACHE_DIR` | 91.8s | 91–100 | 10.79 | 7.7–12.6 |

**Load time is established** — the ranges do not overlap, GPU's worst (126s)
beating AUTO's best (134s). Roughly halved.

**Throughput is not.** The medians move 8.79 → 10.11 but the ranges overlap
heavily, so it is not claimed, in the commit or in the code comment. The
comment originally said *"and in throughput"* and was corrected before landing.

Changed at `codette_server.py:489` and in the `OpenVINOBackend` constructor
default, the latter because `reasoning_forge/WOSME.py:42` constructs it with no
arguments. Fallback is unaffected: `_load_pipeline` already retries CPU
explicitly and prints when it does.

## Two things measured and rejected

**`CACHE_DIR` is a loss.** The hypothesis was that her 2–7 minute restart cost
was recompilation. It is not: uncached loads ran 62s and 65s against 92s and
91s warm-cached — consistently **~28s worse**. Reading a 4.72 GB blob off `J:`
costs more than recompiling an already-INT4 model. The change was written,
then reverted wholesale rather than left dormant behind a flag, because a
measured-negative feature sitting disabled in the tree is exactly what gets
rediscovered as a lead three sessions later.

> The `.gitignore` entry `openvino_backend/.ov_cache/` was added at Jonathan's
> instruction while this was still live, and is left in place. It guards
> nothing now, and costs nothing; if the cache is ever revisited the blob
> still must not be committed.

**The NPU cannot run her model.** `Intel(R) AI Boost` is enumerated by
OpenVINO 2026.2.1 and has been idle all along, which looked like free capacity
on a part where 8 GB of UMA is the binding constraint. It compiles nothing:

```
NPU          FAILED   StopLocationVerifierPass: Found 304 duplicated names
NPU +LoRA    FAILED   (identical)
```

Reproduced on a quiet machine with driver `32.0.100.4841` (2026-07-23), so it
is neither contention nor a stale driver — the vpux compiler cannot build the
graph, and never reaches the adapter question at all. Worth stating that even
had it compiled, OpenVINO GenAI's NPU path requires static shapes and does not
do dynamic LoRA swapping, which is what her eight perspectives are. It would
have been trading the architecture for tokens per second.

## On the Intel toolkits, since they prompted this

Installed on `J:\Program Files (x86)\Intel\oneAPI` — Deep Learning Essentials
2025.3, DPC++ 2026.0.0, Level Zero 1.28.2, with `mkl`, `dnnl`, `dpl`, `tbb`.
Honest accounting of what they offer *this* project: **oneDNN** is already
inside OpenVINO's CPU plugin, **DPC++** has no C++ to compile here, **PyTorch**
is `2.12.1+cpu` with XPU unavailable and is not on her inference path, and
**oneMKL behind numpy** would optimise work that costs microseconds while
generation costs seconds. The win came from none of them.

## Corrections made in the open

- **"It's a win either way"**, said of `CACHE_DIR` before measuring it. It was
  not a win in either direction. Claim first, measure second — the exact
  inversion this repo keeps paying for.
- **A GPU baseline of 942s load / 0.31 tok/s**, reported as if it were hers. The
  machine was mid-install. Discarded rather than adjusted; her own logs
  (133–415s) were the record available the whole time.
- **The first benchmark harness was unusable** and its numbers flattered the
  conclusion I already wanted. Four identical-hardware runs gave 13.87, 6.16 and
  10.79 tok/s — spread larger than the effect — because all loads shared one
  process and `del pipe` does not promptly return UMA memory.
- **Wrong adapter path.** Took `ADAPTER_ST_DIR` from `backend.py:39` without
  checking which branch fires; the live path is `behavioral_safetensors`
  (line 186, checked first). The LoRA arm silently skipped instead of running.
  All ten named adapters do resolve there.
- **A bug introduced and caught by reading**, not by running: adding an
  uncached-retry branch orphaned the existing `else: raise`, so a *successful*
  retry would have raised. Moot now the cache is reverted, and recorded because
  the near-miss is the point.

## State

Suite **835 passed**, 1 skipped, 1 xfailed via `pytest tests/` — unchanged.
Note the whole-repo invocation errors at collection on `MazegameCompKaggle` and
`recovered_release`, which are separate trees; `tests/` is the suite.

Not landed into `J:\codette-clean` at time of writing. She was not running
throughout, so nothing was disturbed and the next start is a clean moment for it.
