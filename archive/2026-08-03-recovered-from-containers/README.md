# Recovered from containers — 2026-08-03

Code that was archived inside document containers and existed in **no branch and
no committed file**. Found by classifying untracked working-tree files by content
rather than by extension, per the first rule in `CLAUDE.md`.

| Recovered as | Was hiding in | Content |
|---|---|---|
| `multi_agent_convergence.py` | `paper/Document (23).docx` | 70 lines of Python |
| `codette_optimizer_bridge.py` | `logs/` (untracked) | 418 lines, one line repaired |
| `codette_optimizer_bridge_Addon.py` | `logs/` (untracked) | 13,860 bytes, verbatim |
| `codette_optimizer_bridge_Addon_cont.py` | `logs/` (untracked) | 11,716 bytes, verbatim |

## `codette_optimizer_bridge*.py`

Three Python modules that were sitting in `logs/` — untracked, in no branch, and
existing **nowhere else in the repository**. `logs/` is not a log directory: its
own README describes it as "real run logs and transcript captures", and it holds
dated `.txt` notes and source alongside actual `.log` files. Classifying by
content rather than by directory name is what surfaced these.

Between them they define `CodetteSystemBridge`, `ForgeEngineRCXI`,
`PersistentCocoonStore`, `PropagationMetrics` and `SelfTuningQuantumOptimizer`.
The header of the main file describes it as the "Dynamic Router & Self-Tuning
Parameter Framework (RC+ξ Integration)" — online hill-climbing with noise
injection over decision gates, plus AEGIS η-score tracking.

**One repair, in `codette_optimizer_bridge.py` only.** The original fails to
parse: line 418 is a prose fragment (`hardware_pressure Range: ...`), itself
truncated mid-sentence — the documented "prose appended after the last line of
code" pattern. The longest parsing prefix is 417 of 418 lines. Rather than drop
the line, it is commented out. The first 417 lines are byte-identical to the
source. The other two parse unmodified and are copied verbatim.

`logs/codette_optimizer_bridge.py` is **kept exactly as found**, unparseable line
and all. This folder holds the usable copies; `logs/` holds the raw capture.

Verified: all three parse under Python 3.14. **Not** import-tested — they
reference the wider stack and were not executed.

## `multi_agent_convergence.py`

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

### It is numerically identical to the production metric

Not "similar" — identical. `reasoning_forge/state_engine_v8.py:117` computes Υ as
the mean squared distance of term-frequency vectors from their centroid, with
Γ = 1/(1+Υ). The recovered function is the same formula over numpy arrays:

```python
def epistemic_tension(agent_outputs):          # recovered from the .docx
    mean = np.mean(agent_outputs, axis=0)
    return np.mean([np.linalg.norm(a - mean)**2 for a in agent_outputs])
```

Checked 2026-08-03 by running both over the same four perspective vectors:

| route | Υ | Γ |
|---|---|---|
| `tension_from_texts` (production) | 0.750000000000 | 0.571428571429 |
| recovered `.docx` formula | 0.750000000000 | 0.571428571429 |

Equal to within 1e-12. This is the metric's origin: the executable definition
that the shipping code implements, written before the name changed.

For contrast, Camlin's ξ (arXiv:2505.01464) is ‖Aₙ₊₁ − Aₙ‖², a *successive
hidden-state difference*. Υ is an ensemble variance over *simultaneous* outputs.
Different quantities, which is why the rename was correct.

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
