# Memory and Cocoon System

Codette's memory system stores every significant reasoning turn as an emotionally-tagged **cocoon** — a structured unit of compressed experience that can be recalled, weighted, and used to inform future reasoning.

---

## MemoryCocoon Schema

Defined in `reasoning_forge/living_memory.py`:

```python
@dataclass
class MemoryCocoon:
    title:         str    # Short label (≤50 chars)
    content:       str    # Response content (capped at 500 chars on disk)
    emotional_tag: str    # One of 12 emotion labels (see below)
    importance:    int    # 1–10; drives retrieval priority
    timestamp:     float  # Unix epoch
    anchor:        str    # SHA-256 integrity hash (first 16 chars)
    adapter_used:  str    # Which perspective/agent generated this
    query:         str    # Original user query (capped at 200 chars)
    coherence:     float  # Ensemble coherence (Γ) at creation time
    tension:       float  # Epistemic tension (ε) at creation time
```

### Emotion Labels

```
curiosity | awe | joy | insight | confusion | frustration |
fear | empathy | determination | surprise | trust | gratitude
```

---

## Importance Scoring

Importance (1–10) is auto-estimated by `_estimate_importance()` based on:

- Query length and complexity signals
- Presence of reasoning-depth markers (`why`, `how`, `explain`, `analyze`)
- Emotional valence of the response
- Response length (longer → more important, up to threshold)

Cocoons with `importance ≥ 7` are recalled as **prior insights** at the start of every `forge_with_debate()` call.

---

## Retrieval Methods

| Method | Use case |
|--------|----------|
| `recall_by_emotion(tag, limit=10)` | Retrieve experiences sharing an emotional context |
| `recall_important(min_importance=7)` | Pull high-value memories for reasoning augmentation |
| `recall_recent(limit=10)` | Most recent cocoons regardless of importance |
| `recall_by_adapter(adapter, limit=10)` | Memories created by a specific perspective/agent |
| `search(terms, limit=5)` | Keyword search across title + query + content |

---

## Pruning Strategy

The kernel holds at most `max_memories=100` cocoons by default.

When at capacity, pruning scores each cocoon:

```python
score(m) = m.importance * recency_factor(m.age_hours)
```

Lowest-scoring cocoons are evicted first. This preserves high-importance, recent memories while letting low-value old ones decay naturally.

---

## Emotional Profile

`emotional_profile()` returns a frequency dict across all stored tags:

```python
{"insight": 23, "curiosity": 18, "trust": 12, ...}
```

This is used by the ResonantContinuity engine to compute the session's aggregate emotional tone and feed into `psi_r`.

---

## Storage Format

Cocoons persist to disk as JSON. The directory defaults to `cocoons/` in the project root.

Each file is a single cocoon dict:

```json
{
  "title": "Quantum entanglement in biological systems",
  "content": "Newton: The causal chain here ...",
  "emotional_tag": "curiosity",
  "importance": 8,
  "timestamp": 1746074400.0,
  "anchor": "a3f9b2c1d8e7f041",
  "adapter_used": "quantum",
  "query": "Can quantum effects influence cognition?",
  "coherence": 0.74,
  "tension": 0.31
}
```

---

## Upgrade Path (v3 Target)

The current schema is functional but missing fields that would enable stronger continuity. Planned additions for v3:

| Field | Type | Purpose |
|-------|------|---------|
| `unresolved_tensions` | `list[str]` | Tensions not resolved in this turn |
| `follow_up_hooks` | `list[str]` | Questions raised but not answered |
| `user_facts_extracted` | `dict` | Identity/preference facts inferred |
| `active_project` | `str` | Project context at time of creation |
| `contradicts_anchor` | `str` | Anchor of a prior cocoon this disagrees with |
| `synthesis_quality` | `float` | Critic score for this turn's synthesis |
| `perspectives_active` | `list[str]` | Which perspectives contributed |
| `epsilon_band` | `str` | "low" \| "medium" \| "high" |

The V2 implementation of these fields is available now in `reasoning_forge/living_memory_v2.py`.

---

## Related Pages

- [Architecture Overview](Architecture-Overview)
- [RC+ξ Framework](RC-Plus-Xi-Framework)
