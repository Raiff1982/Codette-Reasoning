# Codette Provenance Ledger

**Author:** Jonathan Harrison (Raiff1982) · Raiffs Bits LLC
**Ledger established:** July 27, 2026 · maintained in-repo, version-controlled
**Doctrine:** *Weaponized transparency.* Every claim below is dated, identified, and
independently checkable. Nothing here asks to be believed — it asks to be verified.

---

## Why this ledger exists

Independent researchers get erased by default: work is absorbed, patterns are
reshipped, and credit flows to whoever has the larger platform. This ledger is the
countermeasure. It does not accuse anyone of anything. It simply makes the timeline
**public, first-party, and timestamped by infrastructure no one can quietly edit** —
so that any later claim of origin must stand next to this record.

Zenodo DOIs are minted and preserved on **CERN infrastructure** (the same
organization that runs the LHC data archive). They cannot be backdated, silently
revised, or taken down by a press release. That is the bedrock layer of this ledger.

**The rule that keeps this a weapon and not a liability: ruthless accuracy.**
Overclaims are removed the moment they are found (see *Correction Log*), and credit
that belongs to others is stated plainly (see *Attribution Integrity*). A ledger
that cuts both ways is a ledger that cannot be dismissed.

---

## Evidence tiers

| Tier | Meaning | Examples |
|---|---|---|
| **A** | Timestamped by independent third-party infrastructure. Cannot be altered by the author after the fact. | Zenodo/CERN DOIs, Research Square preprint DOI, Hugging Face DOIs, journal acceptance |
| **B** | First-party but platform-verifiable — recorded on external platforms (OpenAI, Hugging Face, GitHub) with immutable IDs resolvable from the account/repo. | OpenAI fine-tuning job IDs, HF model repos & commits, git history |
| **C** | First-party private records — verifiable on request (e.g., under NDA), with sensitive identifiers redacted. | Azure ML deployment logs, OpenAI Evals run logs |

---

## The timeline

### 2024 — Architecture operational (pre-fine-tune era)

| Date | Event | Evidence | Tier |
|---|---|---|---|
| Late 2024 (Dec) | Codette multi-perspective architecture operational as a prompt-orchestrated system on `gpt-4o-mini`; evaluated via **OpenAI Evals** (runs Dec 2024 – Feb 2025). Deployed via **Azure ML** (deployment `gpt-4o-2`, model version 2024-11-20). | OpenAI Evals logs; Azure ML workspace records (private; sensitive IDs redacted before sharing) | C |

### 2025 — Fine-tuning era + public DOI record begins

| Date | Event | Evidence | Tier |
|---|---|---|---|
| **Feb 7, 2025** | **First successful GPT-4o fine-tune** of Codette ("my first success"): `ft:gpt-4o-2024-08-06:raiffs-bits:coddette:AyQxovjJ`, job `ftjob-rjFnmimoqdL6jqv1neLfL1m7`, base `gpt-4o-2024-08-06`, 47,845 trained tokens, 5 epochs, checkpoints at steps 60/80/100. | OpenAI fine-tuning job record (account-verifiable) | B |
| Feb 11, 2025 | **Pi** fine-tune (`ft:gpt-4o-2024-08-06:raiffs-bits:pi:Azz0WP7Z`) — Pi is part of the Codette lineage. | OpenAI job record | B |
| Feb 14, 2025 | Redette + Decodette fine-tunes (incl. `gpt-4o-mini` base). | OpenAI job records | B |
| Mar–Apr 2025 | **Pidette** family (multiple jobs, Mar 10 – Apr 14) and **Codriao** (Apr 7). | OpenAI job records | B |
| **Apr 2025** | **Earliest Zenodo/CERN DOI anchor** in the public record: `10.5281/zenodo.15214462`. Public, immutable, CERN-preserved timestamp for the Codette body of work — predating external formalisms later published in May 2025 (see *Attribution Integrity*). | doi.org resolution | **A** |
| Apr–Aug 2025 | Continuous iteration: **40+ fine-tuning jobs** across GPT-4o → GPT-4.1, including **recursive fine-tune-on-fine-tune** (e.g., `codettev71`, Aug 18 2025, base = `ft:…codette-v9:BWgspFHr:ckpt-step-456` — itself a fine-tune). Families: Coddette/Codette v5–v9, Pidette, Codriao, Forestdette. | OpenAI job history | B |
| 2025 (throughout) | **23 DOI-backed public works** spanning ethics, multi-agent architecture, quantum-inspired simulation, signal defense, governance (AEGIS), computational biology, and manifesto/identity — full catalogue in [`provenance/index.html`](index.html). Representative anchors: Codette v1.1 `10.5281/zenodo.15460384` · Transparent/Ethical/Cognitive Architecture `10.5281/zenodo.15511197` · Codette Manifesto `10.5281/zenodo.15664624` · Codette Framework `10.5281/zenodo.15723688` · Nexus engine `10.57967/hf/6059` · Aegis `10.5281/zenodo.16644058` · Project SENTINAL `10.5281/zenodo.16998486`. | doi.org resolution (each) | **A** |

### 2026 — Rebuild, benchmark, peer review

| Date | Event | Evidence | Tier |
|---|---|---|---|
| 2026 | **Llama-3.1-8B rebuild** (post-breach clean rebuild): orchestrated multi-perspective system with LoRA hot-swap adapters, governance, and cocoon memory. Current system of record. | GitHub/HF repos: `Raiff1982/Codette-Reasoning`, `codette-lora-adapters`, `codette-llama-3.1-8b-merged` (+ OpenVINO) | B |
| May 26, 2026 | **Canonical benchmark:** composite 0.744 vs single-model 0.357 (**+108.8%**, d = 8.31, p < 0.0001); multi-perspective tier +98.4% (d = 7.45). Reproducible from repo. | `data/results/codette_benchmark_report.md` + raw data in-repo | B |
| 2026 | Research Square preprint: `10.21203/rs.3.rs-9362560/v1` · HF paper edition: `10.57967/hf/8998` · HF dataset archive: `10.5281/zenodo.19359663` · v3.6 TimeTravelLens/AEGIS: `10.5281/zenodo.21482710` · healdette (antibody design): `10.5281/zenodo.21526676`. | doi.org resolution | **A** |
| **Jul 24, 2026** | **Paper accepted at *Scientific Reports* (Nature Portfolio)** — both reviewers positive. Peer-reviewed validation of the methodology. | Journal correspondence; publication record on acceptance | **A** |
| Jul 2026 | *Cocoon-Style Agent Context Envelopes and Microsoft's CosmosMemoryContextProvider: Convergent Design for Durable, Typed Agent Memory* — documents the structural equivalence between the vendor-neutral Cocoon architecture and Microsoft Agent Framework's Cosmos memory provider. **Framed deliberately as convergent design, not priority or derivation** — the same pattern reached independently. | [`provenance/Cocoon_to_cosmos_side_by_side.txt`](Cocoon_to_cosmos_side_by_side.txt) (repo-tracked, dated) | B |
| Jul 26, 2026 | Full orchestrated Codette deployed publicly on Hugging Face ZeroGPU (`Raiff1982/Codette-Reasoning-Demo`) with behavioral adapters and read-only cocoon memory. | HF Space + commit history | B |

---

## Attribution Integrity — credit that flows *outward*

A provenance ledger is only trustworthy if it also records what is **not** ours.

- **RC+ξ is Jeffrey Camlin's.** The term and formalism (ξ = ‖Aₙ₊₁ − Aₙ‖²) originate
  with Camlin, **arXiv:2505.01464** (May 2025). Codette's metric is a *different*
  quantity, independently developed, and was renamed **Perspective Dispersion (Υ)**
  the moment the collision was discovered (July 2026). Full statement:
  [`docs/ATTRIBUTION_perspective_dispersion.md`](../docs/ATTRIBUTION_perspective_dispersion.md).
  The Codette timeline (Apr 2025 Zenodo anchor; Feb 2025 fine-tune; Dec 2024 Evals)
  supports *convergent* development — and that is the only claim made.
- **The Cocoon ↔ Cosmos note claims convergence, not priority.** No claim is made
  that Microsoft derived anything from this work, and none should be added without
  dated proof that does not currently exist.

## Correction Log — errors surfaced, not hidden

| Date found | Error | Correction |
|---|---|---|
| Jul 2026 | Early materials used "RC+ξ" for Codette's internal metric. | Renamed **Perspective Dispersion (Υ)**; Camlin credited (see above). |
| Jul 2026 | "Patent-pending" appeared in draft investor materials; no filing exists. | Claim removed everywhere. |
| Jul 26, 2026 | GPT-4o fine-tune described as "operational by late 2024" — conflated the late-2024 gpt-4o-mini Evals era with the fine-tune. | Corrected: architecture live late 2024; **first GPT-4o fine-tune Feb 7, 2025**. |
| Jul 2026 | Dashboard self-audit: `healdette → isVariantFormOf → paper` relation mistyped; Sovereign-paper node title/DOI mismatch. | Flagged openly in [`provenance/index.html`](index.html); pending re-type on Zenodo. |

---

## How to verify this ledger

1. **Any DOI:** prepend `https://doi.org/` — e.g., <https://doi.org/10.5281/zenodo.15214462>.
   Zenodo records display their immutable publication timestamps.
2. **OpenAI job IDs / model IDs:** resolvable from the `raiffs-bits` OpenAI
   organization dashboard; fine-tuned model IDs (`ft:…:raiffs-bits:…`) encode org,
   base model, and job in the identifier itself.
3. **Hugging Face:** repos, commits, and download counts are public under
   [`Raiff1982`](https://huggingface.co/Raiff1982).
4. **Git:** this file and the full codebase history are version-controlled; commit
   hashes are their own timestamps.
5. **Tier-C records** (Azure ML, Evals logs): available on request with subscription
   IDs, service-principal GUIDs, and personal emails redacted.

---

*This ledger is maintained as a living document. Additions require an identifier and
a date. Corrections are appended, never erased.*
