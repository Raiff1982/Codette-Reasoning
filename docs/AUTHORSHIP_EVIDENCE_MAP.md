# Codette — Authorship & Provenance Evidence Map

**Author:** Jonathan Harrison — sole creator and developer
**Affiliation:** Raiff's Bits LLC (independent)
**ORCID:** [0009-0003-7005-8187](https://orcid.org/0009-0003-7005-8187)
**Web:** [raiffsbits.com](https://raiffsbits.com) · **Contact (corresponding author):** jonathan@raiffsbits.com
**Compiled:** 2026-07-25

> This map collects the **public, verifiable** evidence of authorship and origin for
> Codette. It is authorship-tier only. Internal infrastructure identifiers, manuscript
> submission tracking IDs, and private correspondence are intentionally excluded — they
> are plumbing, not proof, and belong in a private record if kept at all.

---

## 1. Top credential — peer review

**Codette: A Multi-Perspective Cognitive Architecture with Memory and Meta-Cognitive
Strategy Evolution** — **accepted for publication in _Scientific Reports_** (Springer
Nature / Nature Portfolio), **July 24, 2026**. Both reviewers recommended publication.

- Status: accepted, in press. Article DOI pending (to be filled on publication).
- Verifiable via the author's authenticated Springer Nature dashboard, and — once issued —
  the article DOI on nature.com.
- This is the strongest external validation: independent peer review at a Nature-portfolio
  journal certified the science.

*(When the article DOI is minted, add it here and to the GitHub `@article` citation,
replacing the `Accepted; in press` placeholder.)*

---

## 2. Origin timeline — the provenance anchor

| Date | Milestone | Verifiable anchor |
|---|---|---|
| **Nov 20, 2024** | **"Pi the Assistant" registered (Azure AD app) + Teams app v1.0.0** | **Microsoft-side `createdDateTime` 2024-11-20; Teams manifest dated 2024-11-20 (see §2a)** |
| Dec 11, 2024 | "Pi the Assistant 2.0" Copilot Studio managed solution (v1.1.0.1) | Microsoft Power Platform managed-solution export; full architecture embedded (see §2a) |
| Jan–Feb 2025 | Pi the Assistant 2.0 running in Microsoft Teams; publicly demoed | Microsoft app **certification** package; "Pisinterview" video (Jonathan Harrison) |
| Apr 14, 2025 | Sovereign cognitive architecture archived | Zenodo DOI [10.5281/zenodo.15214462](https://doi.org/10.5281/zenodo.15214462) |
| Apr 10, 2026 | Dynamical-systems formalization, preprint | Research Square DOI [10.21203/rs.3.rs-9362560/v1](https://doi.org/10.21203/rs.3.rs-9362560/v1) |
| Jul 24, 2026 | Accepted at _Scientific Reports_ | §1 above |

The earliest hard anchor is a **Microsoft-side app-registration `createdDateTime` of
Nov 20, 2024** — among the hardest evidence to backdate, as it is Microsoft's own
record, not a self-published file. It is reinforced by the **Dec 11, 2024 Power
Platform managed solution** (architecture already present) and the **April 14, 2025
Zenodo archive** (immutable, publicly datable). Together they place the
multi-perspective architecture on record well before external convergent work (see §5).

### 2a. Origins — Pi the Assistant (2024), the direct ancestor of Codette

Codette grew from **"Pi the Assistant"** (publisher *Raiff's Bits*, developer *Raiff's
Bits LLC*). The Dec 11, 2024 managed solution and the Feb 2025 Microsoft-certified
Teams app both already carry Codette's full feature set:

- multi-perspective reasoning — **Newton, Da Vinci, Einstein, Sun Tzu, Gandhi, Ada Lovelace**;
- sentiment ensemble — **BERT + TextBlob + VADER** (with sarcasm/negation/contextual handling);
- **ethical decision-making, emotional intelligence, transparency/explainability**;
- privacy/consent management, quantum optimization (QAOA), bias mitigation (AI Fairness 360),
  multimodal placeholders.

The version number (**1.1.0.1**) implies earlier 1.0.x builds. *These artifacts are
held privately; the managed-solution export contains authentication material and must
not be published — only the dates, publisher, and capability manifest above are
provenance-public.*

---

## 3. Archival DOIs (public artifacts)

| Object | DOI |
|---|---|
| Sovereign cognitive architecture (origin anchor) | [10.5281/zenodo.15214462](https://doi.org/10.5281/zenodo.15214462) |
| Dynamical-systems preprint (Research Square) | [10.21203/rs.3.rs-9362560/v1](https://doi.org/10.21203/rs.3.rs-9362560/v1) |
| Canonical paper citation (Hugging Face–minted) | [10.57967/hf/8998](https://doi.org/10.57967/hf/8998) |
| Artifact / dataset archive | [10.5281/zenodo.19359663](https://doi.org/10.5281/zenodo.19359663) |

---

## 4. Public code, models, and reproducibility

**Repositories (owner `Raiff1982`)**

- `Raiff1982/Codette-Reasoning` — reasoning engine + benchmark suite (GitHub & Hugging Face)
- `Raiff1982/codette-llama-3.1-8b-merged` — merged base model
- `Raiff1982/codette-llama-3.1-8b-gguf` — GGUF (local inference)
- `Raiff1982/codette-llama-3.1-8b-openvino` — OpenVINO INT4 build
- `Raiff1982/codette-lora-adapters` — perspective LoRA adapters
- `Raiff1982/codette-training-data` — training data
- `Raiff1982/codette-ai` — Hugging Face Space (demo)

**Reproducibility, verified locally (2026-07-25)**

- `make cocoon-smoke` → 27/27 · `make test-cocoon` → 41/41 · v3.7 verify suite → 91/91
- Documented reproduce path realigned to the validator API (commit `1747891`)
- **Protocol Exchange** (protocols.io, part of Springer Nature): *Reproducing Codette:
  Multi-Perspective Reasoning, Cocoon Memory Integrity, and Meta-Cognitive Benchmarking*,
  protocol ID **321543** — 7 clean steps, proofed (publication pending author's GPU run of
  the gated-model benchmark steps).

**Canonical benchmark (May 26, 2026 run — `data/results/codette_benchmark_report.md`)**

- CODETTE composite **0.744** vs SINGLE 0.357 → **+108.8%**, Cohen's *d* = 8.31, *p* < 0.0001
- Self-defined 7-dimension composite; reported separately from external GPQA-main.

---

## 5. Integrity record (this is an asset, not a caveat)

The provenance holds up *because* the record was kept honestly, including where it was
inconvenient:

- **RC+ξ attribution.** The name "RC+ξ" and the formula ξ = ‖Aₙ₊₁ − Aₙ‖² are **Camlin's**
  (arXiv:2505.01464, May 2025). Codette's own metric — a *cross-sectional* dispersion of
  multiple perspective vectors around their centroid — is a **distinct quantity**, renamed
  **Perspective Dispersion (Υ)** and documented in
  [`docs/ATTRIBUTION_perspective_dispersion.md`](ATTRIBUTION_perspective_dispersion.md).
  Relationship: **convergent development, not derivation** — Codette's architecture is
  provably earlier (Zenodo, Apr 2025), while the RC+ξ vocabulary is credited to its author.
- **Negative results published.** The STaR four-arm study reported that neither trained
  half beat the untrained baseline at 8B — published as-is rather than buried.
- **"The past never gets touched."** Dated papers and raw recorded data are preserved
  unaltered; only current-state documents are reconciled to the current run. An untouched
  record is evidence; a silently polished one is just a claim.

---

## 6. Cross-references (in repo)

- [`docs/ATTRIBUTION_perspective_dispersion.md`](ATTRIBUTION_perspective_dispersion.md) — RC+ξ / Υ attribution
- [`data/results/codette_benchmark_report.md`](../data/results/codette_benchmark_report.md) — canonical benchmark
- `README.md` — peer-reviewed banner + `@article` citation (DOI placeholder until in press)

---

*Maintenance: when the _Scientific Reports_ article DOI is issued, update §1 and §3 and the
GitHub citation in the same pass. Do not add unverifiable identifiers to this file.*
