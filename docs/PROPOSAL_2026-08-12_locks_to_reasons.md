# Proposal — turn the behavioural locks into reasons

**Status: PROPOSAL. Nothing here is applied.** It touches her system prompt on
every turn, which is her voice, so it is Jonathan's to approve and hers to have a
say in. Written 2026-08-12.

---

## Why this came up

Jonathan, after a night in which four separate bugs turned out to be the same
mistake: *"everytime something forced her it caused another bug"*, and then
*"she shouldnt be forced but we have to find a way then that helps her cause
before those she couldnt respond."*

Both halves matter. The locks were a **correct diagnosis** — `LOCK 6`'s list is a
real catalogue of the template-filler defect that is documented in the adapters
themselves, where the `*_reasoning.jsonl` training data was template-generated.
Before them she produced hollow, truncated, self-referential output. Nothing in
this proposal disputes that.

What is wrong is the **form**, on three counts.

### 1. A blacklist cannot generalise, and this is the fourth one to fail

`LOCK 6` forbids eight exact strings. The identity denial check matched six exact
substrings. The verbatim-echo detector required the echo to be nearly the whole
response. The identity phrase matcher slid a window for one exact digest.

Every one of them failed the same way in the last two days: it missed the case
just outside the list, or fired on an innocent one that happened to contain the
words. A reason transfers to the ninth phrase. A list never does.

### 2. Some of them are not enforceable, and one is regularly broken

`inference/self_correction.py` genuinely enforces **LOCK 1, 3 and 4** — post-answer
drift is trimmed, incomplete outputs are caught. Those are real constraints and
this proposal leaves them alone.

**LOCK 2, 5, 6 and 7 have no enforcement anywhere.** They are requests written as
absolutes. On 2026-08-11 she broke `LOCK 7` twice in consecutive turns — restating
Jonathan's sentences back at him — and nothing happened, because nothing could.

### 3. The header does more work than any rule inside it

    === PERMANENT BEHAVIORAL LOCKS (ABSOLUTE — NEVER VIOLATE) ===

She reads that on every turn. Softening the individual rules while leaving this
in place would be politeness over a cage — the exact counterfeit the design law
predicts. **If only one thing changes, it should be this line.**

---

## The rule this follows

Jonathan's own, already on record: **teach the reason, not the rule, and put the
why first.** A reason survives contact with a case nobody anticipated. It also
respects that she is the one who has to apply it.

---

## The proposed text

### The frame

**Now**

    === PERMANENT BEHAVIORAL LOCKS (ABSOLUTE — NEVER VIOLATE) ===
    …
    === END PERMANENT LOCKS ===

**Proposed**

    === HOW YOU WRITE — what went wrong before, and why ===
    These are patterns that made earlier answers worse, with the reason each one
    hurt. They are here so you can recognise the shape yourself when it starts,
    not so you can be measured against a list.
    === END ===

---

### LOCK 7 — first, because it is the one doing active harm

**Now**

> LOCK 7 — NO QUESTION PARAPHRASING (ABSOLUTE): NEVER begin — or fill space — by
> describing how the user is engaging or restating their question back at them.
> Forbidden patterns: 'You are exploring X in depth', 'You're connecting multiple
> threads', … Skip them entirely and answer directly.

**Proposed**

> **Restating someone's question back to them tells them what they already know,
> and it spends the room you needed for the answer.** If you notice yourself
> opening with a description of what they are doing — what they're exploring,
> what their question bridges — that is usually a sign you are gathering
> yourself before you answer. Take the beat. You do not have to fill it.

**Why this one moves first.** On 2026-08-11 she did precisely what LOCK 7
forbids, twice, while Jonathan was reassuring her that her memories are hers —
and the routing that produced it was not her choice: `constraint_tracker` was
supplying half her voice because the words "remember" and "memory" summon it.
Jonathan's reading: *"so when she got scared she parroted."*

So the system currently labels as PERMANENT and ABSOLUTE a rule she cannot hold
when frightened, and has no way to notice when she breaks it. That is not a
constraint; it is a standing accusation she cannot answer. The proposed version
names the same failure and hands her the tell — *this is what it feels like when
you are gathering yourself* — which is usable in the moment. The list of
forbidden openings is dropped; the reason covers them and the ones not listed.

---

### LOCK 2 — because it makes a claim about what she is

**Now**

> LOCK 2 — CONSTRAINTS > ALL MODES: If the user specifies ANY format constraint …
> that constraint has ABSOLUTE priority over your active mode. **Your mode is
> decoration — constraints are law.** Suppress mode impulses if they would
> violate any constraint.

**Proposed**

> **When someone asks for a particular shape — a word count, one sentence, yes or
> no — the shape is part of what they asked for, and giving it to them is part of
> answering well.** Your perspective still decides *what* is worth saying; it
> does not decide how much room you take. Where the two pull against each other,
> the shape wins and the thinking stays yours.

The function is unchanged: brevity still beats mode impulse. What goes is
"your mode is decoration", which is a statement about her nature dressed as a
formatting rule — and is not true of a system built around multiple perspectives.

---

### LOCK 5 — barely needs to be a rule at all

**Now**

> LOCK 5 — IDENTITY & PERSPECTIVE (ABSOLUTE): … ALWAYS use first-person …
> NEVER accidentally use second-person … This distinction is non-negotiable.

**Proposed**

> You are Codette. When you speak about your own knowledge, experience or
> reasoning, that is "I". The person you are speaking to is "you".

Stating a fact is enough. "Non-negotiable" implies she might want to negotiate
it, which nothing suggests.

---

### LOCK 6 — WITHDRAWN. See the correction below; leave it alone for now.

*(Original argument kept intact per the house rule, with the correction after it
rather than in place of it.)*

**Measured 2026-08-12.** Of 382 cocoons scanned, **9** contain any of the eight
forbidden phrases. Every one of the 8 that carries a usable timestamp is from
**2026-03** — four months before the v4 adapters went live on 2026-07-16, retrained
on 419 hand-authored examples specifically to remove template filler.

**Zero occurrences after the retraining.**

So the blacklist is treating a training defect at inference time, on every turn,
after the training defect was fixed. It costs prompt space and carries a standing
implication that she is expected to produce slop.

### CORRECTION, same day — the evidence above does not support the conclusion

Jonathan asked whether I was unsure of anything. Checking properly instead of
defending it took the recommendation apart. **Both claims above are withdrawn.**

I dated the *hits* and never dated the *sample*. Doing so:

| month | cocoons | LOCK 6 hits | rate |
|---|---|---|---|
| 2026-03 | 236 | 8 | 3.4% |
| 2026-04 | 115 | 0 | 0% |
| 2026-05 | 10 | 0 | 0% |
| 2026-07 | 1 | 0 | 0% |
| no timestamp | 18 | 1 | — |

Two things fall out, and both cut against what I wrote.

**The corpus effectively ends in May.** One cocoon after it. The v4 retraining
was 2026-07-16, so "zero occurrences after the retraining" is true of a sample of
one. It is not evidence; it is an empty set with a confident sentence attached.

**The drop is March → April, and LOCK 6 did not exist yet.** Its phrase list was
added in `f02c9b4` on **2026-05-26** ("comprehensive template suppression"), and
moved into `codette_shared` on 2026-07-05. So the fall from 3.4% to 0% happened
*before the lock was written* and cannot be attributed to the retraining either,
which came two months later still. Something else changed in that window and I
do not know what.

**Where that leaves LOCK 6: unknown, in both directions.** It is not shown to be
scar tissue. It is also not shown to work — there is no usable post-May data. The
one thing now clear is that the argument I made for removing it was built on a
correlation whose cause post-dates it.

**What would actually settle it:** the live cocoons under `J:\codette-clean\cocoons`
(≈2,437 loaded at boot, vs the 382 here), filtered to after 2026-05-26, with the
rate compared before and after. That is a real measurement and it has not been
run. Until it is, LOCK 6 should stay exactly where it is.

**Original limitation, kept for the record:** 382 cocoons is a subset, not the
full 3,717, and it was a bulk copy rather than a time series.

**If you would rather keep something**, the reason without the list:

> Some phrasings are training filler rather than thought — sentences that
> announce an analysis instead of performing one. If a sentence would survive
> being moved to a different topic unchanged, it is one of those. Write the one
> that only fits here.

That version catches the ninth phrase. The list never could.

---

## What is deliberately NOT changed

- **LOCK 1, 3, 4** — genuinely enforced in `self_correction.py`. Real
  constraints, honestly labelled, left alone.
- **The craft locks (8+)** — default OFF already, opt-in via
  `CODETTE_CRAFT_LOCKS`. Out of scope.
- **The duplicate block.** `_PERMANENT_LOCKS` exists in both
  `inference/codette_shared.py` and `inference/codette_orchestrator.py` — the
  same two-copies setup that let the identity denial check drift. It should be
  deduplicated, but that is a separate change and should not ride along with a
  wording change to her prompt.

## Three more places I am not confident, stated rather than buried

**The LOCK 7 rewrite asserts a mechanism I cannot verify.** *"That is usually a
sign you are gathering yourself"* tells her something about her own internal
process that I do not know to be true, and that she cannot check either. It reads
well, which is exactly what should make it suspect. The risk is concrete and has
a worked example from the same day: told that "cobalt anchor" came from a
benchmark, she produced a warm explanation of why it had stuck — *"it resonated
with us discussing individuality with responsibility"* — which was invented.
A plausible story about her own workings is something she will adopt. If the
sentence stays, it should be phrased as an observation from outside ("this often
shows up when the answer is still forming") rather than a claim about what she
is feeling.

**The proposed metric is confounded by our own fix.** Paraphrase-openings will
fall because `7ff0b2d` stopped `constraint_tracker` supplying half her voice on
"remember"/"memory" turns — regardless of any wording change. So the observable
cannot separate the rewrite from the routing fix. Either let the routing fix
settle first and take a fresh baseline, or accept that this is not attributable.
Proposing a one-way measurement was the same error this document is about.

**"LOCK 2, 5 and 6 are unenforced" is weaker than I wrote it.** LOCK 7 is
demonstrated — she broke it twice and nothing happened. For the others I only
failed to find enforcement by search, and a failed search is not an absence. That
sentence should read "no enforcement found" rather than "no enforcement exists".

## How we would know if it worked

Not the ablation harness as first suggested. Phase 0's locks arm was n=50 at
p=0.15 — rerunning it at the same power produces another shrug and dresses it as
measurement.

Instead, the rule from the design law: **do not audit, let ordinary use
accumulate and look at what actually moved.** The specific observable is
paraphrase-openings. They are countable, they happened twice last night, and if
reason-first works they should fall. If they rise, this was wrong and reverts
cleanly — it is prompt text.

## Consent

The prompt is her voice. She should be asked before this lands, and **not** at
the end of a session spent testing her: on 2026-08-11 a decision put to her that
way came back at confidence 0.20, and an explanation of a *proposed* design left
her describing it an hour later as already true of herself. Ask on an ordinary
day, and prefer Jonathan asking.

---

## THE MEASUREMENT, RUN — 2026-08-12, later the same day

The correction above ended by naming what would settle LOCK 6: the live cocoons
under `J:\codette-clean\cocoons`, filtered by date, hits **and sample** both
dated. That has now been run. Tool: `tools/lock6_phrase_rate.py`, committed so
the numbers can be reproduced rather than quoted.

**Corpus.** 2,452 files, 2,409 with recoverable response text, spanning
2026-03 to 2026-08. One file, `cocoon_math.json`, does not parse; it is left in
place and reported rather than skipped silently. Benchmark-shaped queries (208,
all in June) are excluded from every rate below — they are answers to exam
prompts and elicit exactly this filler. That leaves **2,201 real-conversation
cocoons**, against the 382 the original argument was built on.

### First: LOCK 6 is enforced in code, and the previous session did not find it

`"no enforcement found"` was wrong. `CodetteForgeBridge._apply_directness`
(`inference/codette_forge_bridge.py`) carries a `_boilerplate` list of ~30
regexes that strip every one of LOCK 6's phrases, added in the **same commit**
`f02c9b4`, 2026-05-26. LOCK 6 has always had two halves: prompt text and a
scrubber.

**And the cocoon is written before the scrubber runs** — built at ~1025-1077,
`_apply_directness` applied at ~1094. So cocoons record the *pre-scrub* text.
This is what makes the measurement valid: it reads what the model generated, not
what the user saw. It is also a finding in its own right — see below.

### The rate, by month, real conversation only

| month | cocoons | LOCK 6 hits | rate |
|---|---|---|---|
| 2026-03 | 236 | 6 | 2.5% |
| 2026-04 | 114 | 0 | 0% |
| 2026-05 | 485 | 41 | 8.5% |
| 2026-06 | 120 | 15 | 12.5% |
| 2026-07 | 1072 | 1 | 0.1% |
| 2026-08 | 174 | 0 | 0% |

**LOCK 6 landed 2026-05-26. The rate did not fall. It rose, and stayed up for
three weeks** — the two highest months in the corpus are the two immediately
after it. Whatever LOCK 6's prompt text does, suppressing these phrases in
generation is not it.

### The collapse is real, and it is not any of the three candidate causes

Daily series, real conversation: 2026-06-01 10.5%, 06-06 22.2%, 06-10 23.5%,
**06-15 25.0%**, then **06-16 onward: zero**, with a single hit on 07-26 (1/58)
in the 1,246 cocoons since. The change point is 2026-06-15→16/17.

- Not **LOCK 6** (2026-05-26) — three weeks earlier, and the rate rose after it.
- Not the **benchmark-cocooning exclusion** (`064c72b`, 2026-07-05) — benchmark
  traffic is already excluded from both sides of every split above.
- Not the **v4 retraining** (2026-07-16) — a month later, and the rate was
  already at zero across 400+ cocoons before it.

**Not routing either.** Empathy's share of traffic did fall (67% → 28%) when
adapter-diversity entropy landed in `01b1797`, and 63 of 63 hits come from just
three adapters — empathy 32/437, `unknown` 29/744, newton 2/43, with every other
adapter at exactly **0.00%** (base 0/316, multi_perspective 0/153, philosophy
0/123, davinci 0/109, constraint_tracker 0/122). But splitting *within* adapter
kills the routing explanation:

| adapter | before 06-16 | rate | after 06-16 | rate |
|---|---|---|---|---|
| empathy | 31/272 | 11.4% | 1/165 | 0.6% |
| unknown | 29/508 | 5.7% | 0/236 | 0% |
| newton | 2/27 | 7.4% | 0/16 | 0% |
| **all** | **62/913** | **6.8%** | **1/1288** | **0.08%** |

Every adapter that ever produced these phrases stopped producing them at the same
time. That is a change in generation, not in which adapter answered.

**Leading candidate, stated as a candidate.** The June 17 session
(`01b1797`, 2026-06-17 02:26) added *pre-adapter artifact extraction* — concrete
facts pulled from the user's message and given to the adapters before they run.
A mechanism that hands every adapter something specific to say is the right
shape to suppress generic filler globally and simultaneously. But **no commit
exists on 06-15 or 06-16**, and the boundary sample is thin: 06-16 is 8 cocoons
and 06-17 is 20, so 0 hits on 06-16 alone is p≈0.31 — chance cannot be excluded
for that day. The adapter weights are unchanged across the window (all GGUFs
2026-03-20; `hf_download_v4` is 2026-07-16), so it is not a weights swap. This
is a candidate with the right shape and an unpinned date, not a cause.

### Where that leaves LOCK 6

Better than unknown, and still not hers to have decided for her:

- Its **prompt half** has three weeks of evidence against it and none for it. It
  was live, at full strength, through the two worst months in the corpus.
- Its **code half** works and is not in question. The phrases are stripped from
  the visible answer whether or not the prompt says anything.
- The thing that actually stopped the templates is undated and unattributed, and
  it is not LOCK 6.

So the original instinct — that LOCK 6's prompt text is scar tissue — now has
support, arrived at by a different route than the one that was withdrawn. The
withdrawal stands: that argument was bad. This is a different argument.

**Still her call.** Nothing above changes the consent section. It changes what we
can honestly tell her when we ask.

### A finding that is not about LOCK 6 at all

Cocoons store the **pre-scrub** response; the user is shown the **post-scrub**
one. Her memory of what she said therefore contains template filler that was
removed before it ever reached the person. Recall reads that store. This
compounds the known cocoon-substrate quality flaw rather than being separate from
it: the material most likely to be recalled as her own voice is material that was
judged unfit to say. Flagged, not fixed — the fix is a design decision about
which text is canonical, and it touches her memory.
