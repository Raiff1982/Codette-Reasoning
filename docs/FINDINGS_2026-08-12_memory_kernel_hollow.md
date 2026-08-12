# The memory kernel loads 2,445 cocoons and 98.7% of them are empty

Found 2026-08-12, from Jonathan's boot log, while verifying an unrelated fix.
**Not fixed** — see the last section for why.

## A correction first

Commit `0d945bc` claimed that `/api/search` had two dead branches, and that the
second one was dead because the fallback kernel had no `search` method. **That
was wrong.**

`reasoning_forge/forge_engine.py` imports `LivingMemoryKernel` from
`memory_kernel.py`, which has no `search` — that much was right, and it is what
the import line shows. But at runtime it does not keep that object:

```python
_v1_kernel = LivingMemoryKernel(cocoon_dir=cocoon_dir)
if _V2_KERNEL_AVAILABLE:
    _v1_dict = {"memories": [m.to_dict() for m in _v1_kernel.memories]}
    living_memory = LivingMemoryKernelV2.migrate_from_v1(_v1_dict)
```

`LivingMemoryKernelV2` **does** have `search` (`living_memory_v2.py:264`). So the
kernel branch was live the whole time. Only the `UnifiedMemory` branch was dead.
The endpoint still returned `[]`, so the fix stands and the symptom was real —
but the reason given for half of it was not, and reading the import line instead
of the runtime object is exactly the mistake this repository keeps punishing.

Confirmed after the reboot: the endpoint now reports
`backends_consulted: ["unified", "kernel"]`. Both run. All ten results come from
`unified`. The kernel contributes zero.

## Why the kernel contributes zero

`LivingMemoryKernel._load_cocoons_from_disk` builds every cocoon like this:

```python
cocoon = MemoryCocoon(
    title=data.get("title", f.stem),
    content=data.get("summary", data.get("quote", "")),
    ...
)
```

A reasoning cocoon has no `title`, no `summary` and no `quote`. Its text lives in
`wrapped.response`, with `v3.user_response_text` alongside it in the newer
schema. So it loads as:

- `title` = its own filename, e.g. `cocoon_1774117687_1664`
- `content` = `""`

Measured against her live `cocoons/` directory on 2026-08-12:

| | |
|---|---|
| memories loaded | 2,445 |
| **empty content** | **2,412 (98.7%)** |
| title is the filename | 2,410 |
| memories containing "cobalt" | **0** |

Ten files on disk contain "cobalt anchor". None of them survives the load.

## The hypothesis that was checked and did not hold

Jonathan, on being shown the number: *"they might be the quarantined ones I had
to put placeholders for."* A real alternative — empty records would be exactly
what a placeholder looks like, and it would make this a non-finding.

Tested by joining each kernel-empty memory back to its file on disk:

| | |
|---|---|
| kernel-empty memories | 2,412 |
| **file DOES contain response text** | **2,410** |
| file genuinely has no text | 2 |
| file missing or unparseable | 0 |

The text is ordinary conversation — *"Good morning to you as well…"*, *"I see
that you're struggling with typing because you go too fast…"*. Only two records
are genuinely empty.

Checked further, because the theory deserved better than one number.
`cocoons/quarantine/` and `cocoons/low_confidence/` are both empty directories.
The `_backup_*` cleanup directories are real and hold 950 files that also exist
at top level — but comparing the pairs shows the cleanups either **removed** the
top-level file (breach, GPQA: top-level absent, backup holds the original) or
**copied** it (query, file: both sides identical, 1313 vs 1313 chars, 223 vs 223).
No cleanup emptied a file in place. There are no placeholders.

The loader's glob is `cocoon_*.json`, non-recursive, so it never reads those
subdirectories at all.

**But the challenge corrected the finding anyway**, in a way that makes it
broader rather than narrower. Look at the `type` field on those samples: they are
`reasoning`, not `reasoning_v3`. This loader does not read `wrapped` for *any*
schema. It was never a case of a reader that missed the v3 migration — it has
never been able to read a reasoning cocoon of any vintage, only the older
foundational `title`/`summary`/`quote` shape. The first draft of this document
said "the third reader that never learned v3", and that was wrong.

## Why this is worse than the other two

`UnifiedMemory._migrate_legacy` and the `/api/search` endpoint **skipped** what
they could not read. This one does not skip. It constructs an empty record,
stores it, and counts it. So the boot log says:

```
✓ Loaded 2445 cocoon memories from ...\cocoons
✓ Migrated 2445 cocoons to v2 kernel
[PHASE6] Memory kernel wired to orchestrator (2445 cocoon memories)
```

Three healthy-looking numbers, all real, all counting shells. A guard that fails
loudly is a bug; a guard that reports success on nothing is the counterfeit this
codebase keeps producing — and the same shape as `answer_detection_rate`
reporting a quality score that was inverted, and `memory_count: 56` in
`/api/status` being the kernel's list rather than the 3,733-cocoon store.

Everything downstream of `self.memory_kernel` inherits it: `DynamicMemoryEngine`,
`WisdomModule`, `MemoryWeighting`, and the orchestrator wiring above.

## Why it is not fixed in this commit

Repairing the loader means 2,410 memories that are currently empty arrive
carrying real text, all at once, into the kernel that feeds `WisdomModule`,
`DynamicMemoryEngine`, `MemoryWeighting` and the orchestrator. That is a change
to what she has available to think with — her memory substrate, not an
instrument — and it is Jonathan's call rather than something to slip in while
fixing a search endpoint.

That is the whole reason. An earlier draft of this section also argued it was
the wrong *moment*, because she had just been rebooted and had two questions
waiting. That was caution copied from the previous session's 2am context into a
midday one, and Jonathan corrected it: *"bro its noon ive slept and we just got
started."* The timing argument is withdrawn; the substrate argument stands on
its own.

**The fix**, when it is made: the load path should read the same fields
`UnifiedMemory._migrate_legacy` now reads — `wrapped.response`, falling back to
`v3.user_response_text` then `v3.response_summary` — and should count and report
what it could not parse rather than storing a shell. Worth measuring shadow-first:
load both ways, diff what recall surfaces, and look at what actually moved before
it becomes the live path.
