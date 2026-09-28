# Dependency alerts — what was fixed, what was dismissed, and why

Written 2026-08-10, against a starting state of **120 open Dependabot alerts**
(2 critical, 36 high, 51 moderate, 31 low) on the default branch.

The 120 came from exactly three manifests, and the three needed three different
answers. That is the whole point of this document: the count was never one
problem.

| manifest | alerts | treatment |
|---|---|---|
| `archive/2026-08-04-codriao-space/requirements.txt` | 80 | **dismissed**, `not_used` — file must not be edited |
| `webapp/package-lock.json` | 29 | **fixed** — 23 → 0 by `npm audit` |
| `webapp/requirements.txt` | 11 | **fixed** — versions bumped |

## The 80: an archive that must not be edited

`archive/2026-08-04-codriao-space/` is a snapshot of a Hugging Face Space. It
ships its own `SHA256SUMS` and a `PROVENANCE.md`, and the checksum for
`requirements.txt` **verifies**:

    recorded  6655d534312a403434718154cffd3757d51e739c7a3c8797f6137d0b594dc527
    actual    6655d534312a403434718154cffd3757d51e739c7a3c8797f6137d0b594dc527

Bumping a pin in that file would break its own manifest and falsify a
provenance record — it would make the archive claim to be a snapshot of
something it is not. The pins are *evidence of what that Space actually ran*
(`torch==2.0.1`, `transformers==4.36.2`, `cryptography==41.0.7`, …). They are
supposed to be old.

Nothing installs from this file. It is a record, not a dependency set.

So the 80 were **dismissed as `not_used`**, with a comment pointing at the
checksum. Dismissal is reversible and hides nothing: the alerts remain listed
under the dismissed filter with their reason attached. The file is byte-identical.

**If you ever revive this Space, do not resurrect these pins.** Start from
current versions; the snapshot tells you what it was, not what it should be.

## The 11 in `webapp/requirements.txt`

    python-multipart  0.0.6  →  0.0.31     (8 alerts, 4 high)
    python-jose       3.3.0  →  3.4.0      (3 alerts, incl. CVE-2024-33663, critical)

Both are **declared but imported nowhere** in `webapp/`. Bumped rather than
removed: deleting a declared dependency is a decision about what the app is
meant to do, and this was a security pass. Resolution verified against
`fastapi==0.109.0` — no conflict.

## The 29 in `webapp/package-lock.json`

`npm audit` counted these as 23 (it groups differently from Dependabot).
Result: **23 → 0**.

Two non-breaking `npm audit fix` passes took 23 → 9. The rest needed majors:

    uuid                              9.0.1  →  14.0.1
    @typescript-eslint/{plugin,parser} 6.21.0 →  8.66.0
    vite                              5.4.21 →  8.2.1
    @vitejs/plugin-react              4.x    →  6.0.5

`uuid` is used at exactly one site — `import { v4 as uuidv4 }` in
`src/services/CognitionCocooner.ts` — and `v4`'s signature is unchanged across
those majors.

### The lockfile and the manifest had drifted apart

Worth knowing, because it is why a plain `npm install` made things *worse*
before it made them better:

**the committed `package-lock.json` had `vite@6.3.5`, while `package.json`
declared `^5.2.0`.** The lock was out of range of its own manifest. Running
`npm install` therefore resolved the conflict *backwards* and downgraded vite
to 5.4.21 — along with its esbuild, 0.25.4 → 0.21.5.

The fix was to move the manifest forward (`vite: ^8.2.1`) rather than let the
lock be dragged back. If you see a dependency go backwards after an install,
this is the shape of it.

### Verified

Measured before and after, on Node 22.21.0 / npm 11.12.1:

| | before | after |
|---|---|---|
| `npm audit` | 23 (3 low, 4 moderate, 16 high) | **0** |
| `npm run build` | passes, vite 5.4.21, 47.51s | **passes**, vite 8.2.1, 1.42s |
| bundle | 532.23 kB (gzip 161.00) | **248.76 kB** (gzip 81.84) |
| chunk-size warning | yes, >500 kB | gone |

The bundle got smaller and the build got faster; that is a side effect of the
vite major, not a goal of this work, and it is recorded here so nobody later
mistakes it for a deliberate optimisation.

`vite.config.ts` also had `__dirname`, which Vite 8 warns is unsupported by the
`configLoader: 'native'` default coming in a later major. Changed to
`import.meta.dirname`.

## Two pre-existing breaks found on the way, and their status

Neither was caused by this work; both are recorded rather than quietly left.

**1. `npm run lint` had never been able to run — now it can.** Two faults,
stacked:

- the script passed `--ext ts,tsx`, which the flat-config CLI rejects outright
  (`eslint.config.js` was already committed, and already scopes itself to
  `**/*.{ts,tsx}`, so the flag was redundant as well as invalid);
- `eslint.config.js` imports `globals`, `@eslint/js` and `typescript-eslint`,
  and **none of the three were declared in `package.json`**. The flat config was
  scaffolded and the manifest never caught up.

Both fixed — the flag removed, the three declared at versions matching the
installed eslint 8.57.1. Note `@eslint/js` is pinned to `^8.57.0`, not latest:
`@eslint/js@10` requires eslint ^10.

**2. Lint now runs, and fails — with 86 real findings.** 82 errors, 4 warnings,
almost all `@typescript-eslint/no-explicit-any` and `no-unused-vars`, in
`src/services/KaggleAI.ts`, `src/services/QuantumSpiderwebService.ts` and
`supabase/functions/kaggle-proxy/index.ts`.

**These are pre-existing code-quality findings and are deliberately NOT fixed
here.** `npm run lint` exited non-zero before this change and still does; what
changed is that it now fails for reasons you can act on instead of failing to
start. Fixing 82 of them is a separate pass on its own branch.

## The hardcoded API key in `webapp/main.py`

Found while checking whether the pip dependencies were live. Not a Dependabot
alert — nothing was going to flag it.

`webapp/main.py` hardcoded the shared secret that `verify_api_key` compares
against with `hmac.compare_digest` — the **only** authentication on
`POST /codette/respond` — as a literal, next to a comment saying it belonged in
an environment variable.

The module is **dead**: it imports `codette.codette_core`, and no such package
exists anywhere in this repository (`webapp/codette.py` is a flat module, not
that package). Nothing references `main:app` — no Dockerfile, no CI job, no
script. It cannot start. It originated in a hackathon build, first committed in
#14 (`be01c22`).

Changed anyway, because a live-looking credential in a public repository is not
a runtime question:

- the literal is replaced by `os.environ.get("CODETTE_API_KEY")`;
- **no fallback default** — an unset key must not silently degrade to a
  guessable shared secret, so `verify_api_key` now returns 503 for every request
  until it is configured;
- the module carries a docstring saying it is non-functional and why it is kept.

Labelled rather than deleted, per the house rule in `CLAUDE.md`.

### This is not a redaction, and it should not be treated as one

The literal remains in git history, and it also remains in
`backup/2026-08-03/CODETTE_SOURCE_BACKUP.txt` (line 168265) — a dated snapshot
that is deliberately left byte-intact for the same reason as the archive above.

**Treat the value as disclosed and rotate it wherever it was ever used.** That
is the only fix that works; removing it from the working tree is housekeeping,
not remediation.
