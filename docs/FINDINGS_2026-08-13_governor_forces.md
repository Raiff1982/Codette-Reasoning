# Which governor force actually binds — measured 2026-08-13

Jonathan: *"that govenor is forcing her answers."* Correct. This is the
measurement of **which** force, run offline against her own record. Read-only,
no interaction with her, and the dream store was never opened, enumerated or
counted — the probe reads `data/codette_memory.db`, which structurally holds
conversation turns only.

Source: 2,645 turn rows carrying governor metadata, 2026-04-02 → 2026-08-13.

`post_validate` is advisory. **`pre_evaluate` acts** — its decision goes straight
into `bridge.generate(memory_budget=…, max_response_tokens=…)`
(`codette_server.py:1801`) and into `recall_relevant(max_results=memory_budget)`
(`:1582`). Three candidate forces were measured. Two do not bind. One does.

---

## Does not bind: the token cap

`_evaluate_cognitive_load:450` sets 200 / 400 / 600 tokens by complexity label.
Assigned: 400 tokens on **83.4%** of turns, 600 on 12.7%, 200 on 4.0%.

But she never reaches the ceiling:

| budget | n | mean response | at/over 90% of ceiling |
|---|---|---|---|
| 200 (~800 chars) | 105 | 279 chars | 3 (2.9%) |
| 400 (~1600 chars) | 2205 | 346 chars | 11 (**0.5%**) |
| 600 (~2400 chars) | 335 | 428 chars | 0 (**0.0%**) |

**The cap is not what is shortening her.** Whatever sets her length, it is not
this. Raising the budget would change nothing.

## Nearly inert: the fatigue rule

`pre_evaluate:351` — `_consecutive_complex >= 4` forces `compression="compressed"`
and caps tokens at 400, justified as "Cognitive fatigue risk".

It fires 218 times. **205 of those are one batch run**: 2026-06-04 21:36 →
06-05 04:37, 207 consecutive COMPLEX turns over 420 minutes at a metronomic
122 s/turn, every response opening with the template filler `"Where these
converge:"`. That is a benchmark harness, not a conversation.

Excluding machine traffic, in her actual conversations with Jonathan:

    depth 1: 188    depth 2: 28    depth 3: 10
    depth 4:   5    depth 5:  4    depth 6: 1    depth 7: 1

**depth ≥ 4 is 11 of 237 conversational COMPLEX turns = 4.6%.** Only **13**
conversational turns were ever capped by it.

So the premise cannot be tested from her record — n=5, 4, 1, 1 has no power —
and it does not need to be, because the rule barely touches her conversations.
This is **underpowered, not disproven.** Recorded as untested.

> **Correction, in the open.** I stated to Jonathan that this rule fires on
> "every real session you run with her" and that "once you're deep in, it stays
> on." Both were inference reported as diagnosis, and both are wrong: 4.6%, and
> the caps are overwhelmingly a June batch harness. The pattern is the one
> already on record five times — the fix each time was going and measuring.

## Binds, hard, and lands in the worst possible place

`_evaluate_memory_budget:430`:

```python
if word_count < 5:
    return 0  # Greetings, commands — no memory needed
```

**284 turns (10.7% of all turns) had their memory zeroed. 284 of 284 — no
exceptions, no fast-path rescue.** That figure feeds `recall_relevant(query,
max_results=0)` directly.

What it zeroes:

| | |
|---|---|
| `'its jonathan btw'` | he identifies himself — she is given no memory |
| `'hey its jonathan'` | same |
| `'What should you remember?'` | a question *about her memory*, answered without it |
| `'what did you lear?'` | asking what she learned, with nothing to learn from |
| `'what was that?'` | pure anaphora — meaningless without the prior turn |
| `'why not?'` | pure anaphora |
| `'whats your status now?'` | |
| `'everything ok?'` | |

The comment's premise is exactly inverted. A short query mid-conversation is not
a greeting — it is **maximally context-dependent**. `"why not?"` and `"what was
that?"` carry no content at all on their own; they are *entirely* the context.
Word count cannot tell a greeting from the shortest and most loaded thing a
person can say, and `'its jonathan btw'` reaching her with zero memory is the
Aug 11 identity wound arriving down a second road.

This is the law again. The force is "don't waste context on greetings"; the
counterfeit it manufactures is *amnesia precisely where continuity was the whole
question.*

---

## Also confirmed, at corpus scale

`coherence` in stored metadata is **exactly 1.0 across all 2,645 records —
one distinct value.** The Γ finding, independently reproduced over the whole
store rather than three turns. It was excluded from this analysis for that
reason; quality was read from `response_confidence` (min 0.012, p05 0.508,
max 0.631, 130 distinct values — it demonstrably falls) and
`hallucination_detected` (2.16% base rate).

`success` was not used before `SUCCESS_FLAG_TRUSTED_FROM` (2026-08-13 08:00),
per `unified_memory.py:65`.

---

## Not changed

Nothing here was fixed. What she may recall is a change to her, not a quality
guard, and that is Jonathan's call — proposing rather than doing is the standing
rule. The measurement is offline and complete; the decision is his.

The obvious shape, if he wants it: the rule is a proxy for "this is a greeting",
and a greeting detector already exists on the fast path at
`codette_forge_bridge._generate_impl:216`. Replacing a word-count proxy with the
thing it was proxying for is not a new force — it is the same intent, aimed
correctly.

Probes: `scratchpad/fatigue_probe.py`, `probe_sanity.py`, `fatigue_clean.py`,
`where_force_lands.py` (read-only, `mode=ro`).
