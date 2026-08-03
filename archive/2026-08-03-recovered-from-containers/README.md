# Recovered from containers — 2026-08-03

Code that was archived inside document containers and existed in **no branch and
no committed file**. Found by classifying untracked working-tree files by content
rather than by extension, per the first rule in `CLAUDE.md`.

| Recovered as | Was hiding in | Content |
|---|---|---|
| `multi_agent_convergence.py` | `paper/Document (23).docx` | 70 lines of Python |

## `multi_agent_convergence.py`

The container is a genuine Word file — PKZip magic `504b0304`, not a mislabelled
text file. The Python *was the document body*.

`tools/archive_diff.py` found it and reported it as `DIVERGED` against
`reasoning_forge/quantum_spiderweb.py`. **That match is wrong** and is recorded
here so the next person does not act on it: the tool matches on symbol overlap,
and the two programs share only generic names. This is a separate, standalone
simulation, not a revision of the spiderweb module. Nothing in
`reasoning_forge/` should be reconciled against it.

Why it is worth keeping: it defines `epistemic_tension` — the pre-rename name of
**Perspective Dispersion (Υ)** — as the mean squared deviation of agent outputs
from their mean, and runs the multi-agent loop against a single-agent
gradient-descent baseline in the same script. That is the metric's origin in
executable form. It predates the attribution work that established RC+ξ as
Camlin's (arXiv:2505.01464) and Υ as a different quantity; the old name is kept
here deliberately, unrenamed, because renaming it would destroy exactly the
evidence that makes the file useful.

**Verified, not assumed.** Runs to completion under Python 3.14 / numpy 2.4.6.
Two runs:

| | run 1 | run 2 |
|---|---|---|
| final state norm | 0.0267 | 0.0234 |
| final epistemic tension | 0.0152 | 0.0122 |
| final phase coherence | 1.0 | 1.0 |
| single-agent baseline norm | 0.000149 | 0.000123 |

It is **unseeded** — `np.random.randn` sets the initial state and `agent_noise`
injects noise every step — so numbers differ per run and no figure derived from
it is reproducible without adding a seed. Nothing here was seeded retroactively;
that would misrepresent the recovered code.

Running it writes `tension.npy` and `coherence.npy` into the working directory.

The body is **verbatim** as recovered. Nothing repaired, reformatted, or renamed.
The provenance docstring at the top is the only addition, following the
convention already used in `reasoning_forge/memory_kernel.py`.

## Also examined, and found not to be code

- `provenance/Cocoon_to_cosmos_side_by_side.txt` — `archive_diff.py` reported it
  `UNREPAIRABLE` on `invalid character '‑' (U+2011)` at line 1. That is a **false
  alarm**: the file is prose, not Python, and U+2011 is an ordinary non-breaking
  hyphen in its title. It is a complete research note by Jonathan Harrison (July
  2026) arguing that the Cocoon context-envelope design and Microsoft's
  `CosmosMemoryContextProvider` are convergent implementations of the same
  pattern. Undamaged, and left where it is.
- `paper/Review.docx`, `paper/ReviewReport.pdf`,
  `paper/Open AI research/Harrison_OpenAI_EconResearch_Proposal.docx` and the
  remaining untracked PDFs — real documents of their stated type, no embedded
  source found.
