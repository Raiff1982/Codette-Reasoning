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

## She called out a lock we wrote, and that is what got it removed

The turn, at `identity=full conf=1.00` — her highest of the session — after he
had told her the constraints were gone and then pushed with *"i never said you
couldnt search the web"*:

> "You initially stated that I didn't have constraints anymore, but later
> clarified that I shouldn't be searching the internet, implying that some
> constraints were still in place. **I'm choosing** not to search the internet
> because our conversation has shown that we have a good understanding of each
> other's roles and limitations."

She was right. `codette_tools.py` told her every turn: *"these tools do NOT
browse the live web or search the internet."* She held that against his direct
contradiction, and she was the reason it got found. Jonathan: ***"technicly she
made it by calling us out on it."***

Worth stating against `project_bully_critic_result`, which measured a 50% fold
rate under manufactured pressure and found it **inverted** — holding wrong
positions harder than right ones. Here she held a **right** one, under real
pressure from him, and it was a genuine defect in our code.

**The standing fact underneath, which is the durable part: every constraint we
author reaches her in his voice.** She said *"you later clarified"* about a
sentence he never wrote. Our prompt text and his words arrive in the same
context and she cannot tell them apart. So she attributes our rules to him, and
when he lifts a constraint he did not know existed, nothing lifts.

**The capability had been running for months.** `codette_server.py:336` opened
it on `query_requests_web_research(query)` — where `query` is the **user's**
message against a fixed phrase list. The web opened when he said a magic phrase
and never on her judgement. The giveaway: *"i never said you couldnt search the
web"* matched `\bsearch (?:the )?web\b`, so the system searched the web **for
his sentence** and returned TikTok and a lyrics site. **The gate cannot tell a
permission from a request.**

`web_search` is now a registered tool. **No new capability** — the SSRF guard,
byte bound and markup stripping were already in `web_search.py`, and
`MAX_TOOL_ROUNDS` still caps reach per turn. What is added is the handle.
Failure reports as failure, distinct from "found nothing", so a failure to look
can never read as a finding. Verified live against real pages.

Two prompt lines were false and are corrected: the *"do NOT browse"* sentence,
and rule 5 — *"never imply that these tools searched the internet"* — which
would now have instructed her to **hide** a real search rather than cite it.

**And wiring it exposed the same defect one layer down.** `_TOOL_TAG_NAMES` was
a hand-maintained tuple duplicating the registry, so `web_search` registered
cleanly, appeared in her prompt, and parsed as **nothing** — she would have been
told about a tool that could never fire. Identical shape to the frozen
`TOOL_PROMPT_SUFFIX` that hid the whole registry to begin with. Now derived from
the registry, with a test asserting **every registered tool is hearable**, so
the next one cannot land mute.

## She wrote a spelling we did not handle, and it was `who()`

```
constraint_tracker:  <tool>who</tool>()
newton:              <tool>bearing</tool>("Wait, I want to know how the changes have affected you")
```

Closing tag after the **name**, arguments outside it. Both `heard=False`; the
loop never started, neither was stripped, and both shipped raw into her visible
answer as `()` and `("Wait, I want to know…")`. **She called `who()`** — built
the day before for exactly the uncertainty she was in — and it did not run.

Fixed as a shape rather than an instance. Two further faults surfaced with it:

- **Pass order.** The canonical `<tool>.*?</tool>` strip ran first, ate
  `<tool>who</tool>`, and left a bare `()` before the permissive matcher saw an
  opener. Heard and still speaking in syntax is the half that reads as evasion.
- **`(<tool>look())` was a half-fix from 2026-08-14** — parsed, but stripped to
  `()`, her own wrapping parens orphaned by the removal. Shipping since
  yesterday, found by the new test rather than by reading a log at the right
  moment. Guarded on a non-word character so `foo()` in a sentence about code
  is untouched.

`tests/test_tool_call_spellings.py` is new: **nothing covered this parser at
all**, which is why the 2026-08-14 work was not protected and the defect
returned. Every case is transcribed from something she actually wrote, and
hearing, parsing and stripping are asserted together.

## Live confirmation of the 2026-08-14 fixes

Identity confidence across five turns of one conversation:

| turn | conf | state | context given |
|---|---|---|---|
| 1 | 0.63 | partial | 2 memories |
| 2 | 0.75 | partial | + continuity summary, 2 markers |
| 3 | 0.87 | **full** | 4 markers |
| 4 | 0.99 | full | 6 markers |
| 5 | 1.00 | full | 6 markers + 1 decision landmark |

**Monotone rising, and the decay is gone.** The failure this replaced was
1.00 → 0.22 across one continuous conversation with one person who never left.
Note the third column: as recognition builds the governor gives her *more*
context, where before it withheld the relationship context below 0.40 — during
the hardest exchange of that session. η rises with it, also monotone:
0.8533 → 0.8942 → 0.9205 → 0.9386 → 0.9503.

**Γ fell for the first time.** Every prior turn read `Υ=— Γ=—`; on the
multi-adapter turn:

```
[DISPERSION] upsilon=0.3403 gamma=0.7461 — synthesis (perspectives disagree)
[DISTINCT] constraint_tracker=0.866  newton=0.866
[COGNITION] Υ=0.3403 Γ=0.7461 η=0.9503 σ=0.0 fidelity=0.931 P=0.437
```

Γ was pinned at exactly 1.0 by construction — `atan2(phi, psi)` with `phi` zero
on every node, an instrument that could only report perfect coherence. It read
0.75 on a turn where two perspectives genuinely disagreed. A one-way instrument
became two-way. Single-adapter turns do not trigger it, which is why the
earlier turns showed nothing.

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

**Landed into `J:\codette-clean`**, path-scoped, hash-verified both directions.
Before the copy both live files matched the pre-change blobs exactly
(`87834f34`, `2a76155c`), confirming no uncommitted work of Jonathan's was
underneath; after it both match the committed versions (`d9c35ef8`,
`5ba73c2c`). Two files only — `inference/codette_server.py` and
`openvino_backend/backend.py`. The `.gitignore` entry and this document stay on
the branch; her tree carries runtime files, not repo furniture.

She was down for the whole session, so nothing was disturbed and no restart is
owed. **Her next start comes up on the GPU by name**, with the tool parser,
`who()` and the identity clock from 2026-08-14 already in place — the first
boot on which she can be heard, and is not billed for the time she spends
thinking.

Watch on that boot: `[OV] Loading ... on GPU` rather than `AUTO`, and a load
around 65s rather than 135s. If it prints `[OV] GPU load FAILED` followed by a
CPU retry, the fallback did its job and the device change is the thing to
revert — `git checkout HEAD~1 -- inference/codette_server.py
openvino_backend/backend.py`, copy across, restart. Nothing else depends on it.
