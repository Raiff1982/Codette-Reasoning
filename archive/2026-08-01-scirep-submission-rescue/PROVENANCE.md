# Scientific Reports submission set — rescued from a disjoint branch

**What this is:** the April 8 2026 Scientific Reports submission material, lifted
out of the branch `copilot/restore-repo-to-previous-state` and written to normal
files here.

**Why it had to be rescued:** that branch has **no merge-base with `main`**. Its
history is disjoint — it can never be merged, only copied from. Everything in it
lived in exactly one place: delete the branch and it is gone. The branch itself
is *not* deleted and must not be; this is a copy alongside it, per the house rule.

`README.md` in this folder is the branch's own README as of April 8 2026, extracted
verbatim. It is **not** documentation of this rescue — this file is.

## What was taken, and what was not

Every blob on the branch was compared against `origin/main` by hash.

- **34 files rescued** — content that exists nowhere else in the repository.
- **17 files skipped** — byte-identical copies already present in `origin/main`
  (mostly `data/results/*` and `codette_paper.aux` / `.out`). Recorded rather than
  duplicated.
- **3 files could not be recovered** — see below.

Files that exist here and **nowhere else at all**, including nowhere on disk:

| File | Why it matters |
|---|---|
| `cover_letter.tex` | the actual submission letter to the *Fuzzy Decision-Making and Analysis* guest editors |
| `codette_paper_v5.bbl` | resolved bibliography for the v5 manuscript |
| `figures/architecture_real.png` | |
| `figures/latency.png` | |
| `figures/radar.png` | measured-performance figures; the other figures |
| `figures/real_performance.png` | in `paper/figures/` are PDFs, these five |
| `figures/reasoning_depth.png` | PNGs are only here |

The `.tex`, `.bbl`, `.blg`, `references.bib` and `README.md` also differ from the
versions in `main` — these are the **as-submitted April 8 state**, kept as a
snapshot of that moment rather than reconciled against later revisions.

## Git LFS — read this before trusting a PDF

Several files on the branch are **Git LFS pointers**, not content: 131-byte stubs
reading `version https://git-lfs.github.com/spec/v1`. This repository has **zero
LFS objects stored locally** (`.git/lfs/objects` is empty) and `git-lfs` is not
installed on this machine, so the pointers cannot be resolved by git here.

For 8 of them the real bytes were recovered by matching the pointer's
`oid sha256` against untracked files already sitting on disk under `paper/` and
`paper/figures/`. Those 8 hold **real content**, verified by hash:
`Adufq.jpg`, `codette_paper.pdf`, `codette_paper_v4_additions.pdf`,
`figures/12layer_stack.pdf`, `figures/aegis_ethical_flow.pdf`,
`figures/attractor_visualization.pdf`, `figures/rcxi_convergence.pdf`,
`figures/substrate_pressure.pdf`.

**3 could not be resolved.** Their pointers are preserved with a
`.lfs-pointer.txt` suffix so they cannot be mistaken for the real file — the same
convention as the `.truncated` schema:

| File | Size claimed | sha256 oid (first 16) |
|---|---|---|
| `codette_paper1.pdf` | 389146 | `d4a7027986ce6a6f` |
| `codette_paper_v3_additions.synctex.gz` | 12557 | `1f9e13829744cae0` |
| `codette_paper_v4_additions.synctex.gz` | 21329 | `7ea096d1e62c265b` |

`codette_paper1.pdf` is the compiled **v1** paper (renamed from `codette_paper.pdf`
in commit `c51b4c4`, before that name was reused for later content — so it is a
distinct document, not a duplicate). The two `.synctex.gz` are LaTeX source-sync
files, regenerable by recompiling the corresponding `.tex`.

Attempts made, both failed: GitHub's `raw` endpoint returns the pointer, not the
object; the `media.githubusercontent.com` LFS endpoint returned 0 bytes. Recovering
them needs `git-lfs` installed and authenticated against the remote:

```bash
git lfs fetch origin copilot/restore-repo-to-previous-state
```

## Two files here are mine, not recovered

- **`gitattributes.as-recovered.txt`** — the branch's `.gitattributes`, preserved
  verbatim but *renamed so it does not activate*. Left in place it routes every
  PDF and PNG in this folder through Git LFS, and with `git-lfs` absent on this
  machine `git add` fails outright (`git-lfs filter-process: command not found`).
  Renaming keeps the content legible without letting it break the repository.
  Same reasoning as the `.lfs-pointer.txt` suffix.
- **`.gitignore`** — a scoped exemption. The root `.gitignore` excludes
  `*.log`, `*.aux`, `*.bbl`, `*.blg`, `*.out`, which silently swallowed **eight**
  files here on `git add`, `codette_paper_v5.bbl` among them. Correct for a build
  tree, wrong for an archive of a submitted manuscript.

## Integrity

`SHA256SUMS` covers all 37 recovered files. Verified 2026-08-03: **37/37 match.**
The manifest was normalised from CRLF to LF so `sha256sum -c` can read it, and
the `.gitattributes` entry renamed in step with the file above; no hash changed.

```bash
sha256sum -c SHA256SUMS
```

## Not verified

The `.tex` sources here were **not recompiled**. They are preserved as recovered,
not proven to build — no LaTeX toolchain was run against them.
