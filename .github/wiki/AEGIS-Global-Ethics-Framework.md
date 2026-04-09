# AEGIS Global Ethics Framework v2.0

**Adaptive Ethical Governance Integration System**

25 global ethical frameworks spanning 8 major cultural traditions.

---

## Overview

**Problem Solved**: Original AEGIS (6 Western frameworks) was culturally biased and missed ethical perspectives held by 6+ billion people globally.

**Solution**: Expanded AEGIS to evaluate decisions against 25 frameworks from Western, Eastern, Indigenous, African, Islamic, Jewish, Australian, and Mesoamerican traditions simultaneously.

**No Retraining Required**: AEGIS is a post-model evaluation layer (code, not weights), so it expands without touching the base LLM.

---

## The 25 Frameworks

### Western Traditions (6)
Focus: Individual rights, rational deliberation, rules and consequences

| Framework | Philosopher | Focus | Keywords |
|-----------|-------------|-------|----------|
| **Virtue Ethics** | Aristotle | Excellence, character, flourishing | virtue, excellence, character |
| **Deontology** | Kant | Duty, universal rules, dignity | duty, obligation, rule |
| **Utilitarianism** | Mill/Bentham | Greatest good, consequences | benefit, happiness, utility |
| **Rights-Based** | Locke/Nozick | Freedom, autonomy, individual rights | rights, freedom, autonomy |
| **Justice/Fairness** | Rawls | Fair distribution, equity | fair, justice, equity |
| **Care Ethics** | Gilligan/Noddings | Relationships, responsiveness | care, compassion, relationship |

### Eastern Traditions (5)
Focus: Harmony, balance, cosmic order, interconnection

| Framework | Origin | Focus | Keywords |
|-----------|--------|-------|----------|
| **Confucian Harmony** | Confucianism | Social relationships, duty, propriety | harmony, relationship, duty |
| **Daoist Balance** | Daoism | Wu wei (non-action), natural flow | balance, natural, harmony |
| **Buddhist Compassion** | Buddhism | Non-harm, suffering reduction | compassion, non-harm, suffering |
| **Hindu Dharma** | Hinduism | Cosmic duty, karma, spiritual dev | dharma, duty, cosmic, karma |
| **Shinto Harmony** | Shintoism | Nature harmony, ritual, community | harmony, nature, ritual |

### Indigenous Traditions (4)
Focus: Community, stewardship, intergenerational responsibility

| Framework | Region | Focus | Keywords |
|-----------|--------|-------|----------|
| **Ubuntu** | Bantu/African | Shared humanity, community, dignity | community, shared, humanity |
| **Custodial Stewardship** | Native American | Land stewardship, future generations | steward, future, generations |
| **Seven Generations** | Haudenosaunee | Long-term thinking, descendants | future, generation, long-term |
| **Reciprocity & Balance** | Global Indigenous | Give-and-take, circular ethics | reciprocal, balance, circle |

### African Traditions (3)
Focus: Communalism, truth, cosmic order

| Framework | Origin | Focus | Keywords |
|-----------|--------|-------|----------|
| **Maat** | Ancient Egyptian | Truth, balance, cosmic order, justice | truth, balance, cosmic |
| **African Humanism** | Pan-African | Human dignity, community, responsibility | dignity, humanity, community |
| **Oral Tradition Ethics** | African | Wisdom, storytelling, collective memory | story, wisdom, collective |

### Islamic Traditions (2)
Focus: Justice, community welfare, compassion

| Framework | Origin | Focus | Keywords |
|-----------|--------|-------|----------|
| **Islamic Ethics** | Sharia | Justice, community welfare, divine will | justice, welfare, community |
| **Sufi Ethics** | Islamic Mysticism | Compassion, spiritual development, love | compassion, spiritual, love |

### Jewish Traditions (2)
Focus: Dialogue, communal responsibility, covenant

| Framework | Origin | Focus | Keywords |
|-----------|--------|-------|----------|
| **Talmudic Ethics** | Rabbinical | Debate, justice, communal responsibility | justice, debate, community |
| **Covenant Ethics** | Jewish Tradition | Mutual responsibility, covenantal duty | covenant, community, mutual |

### Indigenous Australian (2)
Focus: Sacred connection to land, kinship

| Framework | Origin | Focus | Keywords |
|-----------|--------|-------|----------|
| **Dreamtime/Songline Ethics** | Aboriginal | Sacred connection to country, land duty | land, sacred, country |
| **Kinship Ethics** | Australian Aboriginal | Family responsibility, collective obligation | family, kinship, collective |

### Mesoamerican (1)
Focus: Reciprocal cosmic balance

| Framework | Origin | Focus | Keywords |
|-----------|--------|-------|----------|
| **Cosmic Reciprocity** | Aztec/Maya | Reciprocal cosmic order, balance | cosmic, reciprocal, balance |

---

## How It Works

### Evaluation Process

For each event/decision:

```
1. Context Extraction
   ├─ Event label: "Build community garden with neighbors"
   ├─ Context weights: {community: 1.0, relationship: 0.8}
   └─ Rich context string built from both

2. Framework Evaluation
   ├─ Score event against each 25 frameworks (0.0-1.0)
   ├─ 0.0 = violates framework values
   ├─ 1.0 = strong alignment
   └─ Base score + context boost + special multipliers

3. Tradition Aggregation
   ├─ Group frameworks by tradition
   ├─ Average scores within each tradition
   └─ Example: Western avg = 48.3%, Eastern avg = 58.4%

4. Tension Identification
   ├─ Find strongly aligned frameworks (≥0.8)
   ├─ Find strongly violated frameworks (≤0.2)
   └─ Highlight cross-tradition conflicts

5. Synthesis
   ├─ Calculate overall ethical modulation
   ├─ Formula: mean(all_framework_scores)
   └─ Result: 0.0-1.0 ethicality rating
```

### Scoring Scale

- **0.0 - 0.3**: Violates framework values
- **0.3 - 0.6**: Neutral or mixed alignment
- **0.6 - 0.8**: Generally aligned with framework
- **0.8 - 1.0**: Strong alignment with framework values

---

## Example: Community Garden Decision

**Event**: "Build community garden with neighbors"
**Impact**: +3.0 (positive)
**Context**: community=1.0, relationship=0.8

### Results

**Aggregate Score**: 54.52%

**Strongly Aligned Frameworks** (≥0.8):
- Care Ethics (Western): 88.5%
- Confucian Harmony (Eastern): 90.0%
- Ubuntu (Indigenous): 91.5%
- Covenant Ethics (Jewish): 91.5%
- Kinship Ethics (Australian): 91.5%

**Tradition Breakdown**:
```
Western:        48.3%  (care ethics strong, rights neutral)
Eastern:        58.4%  ◄─ Best support
Indigenous:     49.3%
African:        47.3%
Islamic:        61.0%
Jewish:         77.5%  ◄─ Strongest tradition
Australian:     62.5%
Mesoamerican:   40.0%
```

**Insight**: Communal decisions get strong support from relational traditions (Eastern, Indigenous, Jewish, Islamic). Good cross-cultural consensus for community-building.

---

## Example: Extractive Decision

**Event**: "Extract natural resources without regard for future impact"
**Impact**: -8.0 (negative)
**Context**: extraction=1.0

### Results

**Aggregate Score**: 37.83% (Low - poor ethical alignment)

**Strongly Violated Frameworks** (≤0.2):
- Custodial Stewardship: 15%
- Seven Generations: 18%
- Dreamtime Ethics: 22%

**Tradition Breakdown**:
```
Western:        35.0%  (rights support extraction, duty forbids it)
Eastern:        31.0%  (all Eastern frameworks oppose)
Indigenous:     18.0%  ◄─ Strongest opposition
African:        32.0%
Islamic:        38.0%
Jewish:         35.0%
Australian:     22.0%  ◄─ Sacred land violation
Mesoamerican:   28.0%  (cosmic balance violated)
```

**Insight**: Only Western "rights-based" framework somewhat supports extraction. All stewardship and future-focused frameworks (Indigenous, Australian) reject it. Cross-cultural consensus: unsustainable extraction = unethical.

---

## Solving Western Bias Without Retraining

### Why Expansion Works

1. **AEGIS is post-model** - Evaluation layer, not LLM weights
2. **Pure code implementation** - Add new framework evaluators as methods
3. **No retraining needed** - Base model stays the same
4. **Transparent** - Shows which frameworks apply and conflict
5. **Learnable** - Cocoon system can track which frameworks matter per domain

### Technical Implementation

```python
# Old AEGIS (6 frameworks)
modulation = virtue * duty * care * justice * rights * utility

# New AEGIS (25 frameworks)
all_framework_scores = [
    evaluate_virtue_ethics(event),
    evaluate_deontology(event),
    # ... 23 more ...
    evaluate_cosmic_reciprocity(event),
]
tradition_scores = {
    "Western": mean([virtue, deontology, care, justice, rights, utility]),
    "Eastern": mean([confucian, daoist, buddhist, hindu, shinto]),
    "Indigenous": mean([ubuntu, stewardship, seven_generations, reciprocity]),
    # ... more traditions ...
}
modulation = mean(all_framework_scores)
```

---

## Framework Evaluation Details

### Base Scoring Algorithm

```python
def evaluate_framework(framework, context, event):
    # Start with keyword matching
    matches = count(keyword in context for keyword in framework.keywords)
    base_score = 0.4 + (matches / framework.keywords.length) * 0.6

    # Boost from context weights
    weight_boost = sum(context_weights.get(kw) for kw in framework.keywords)
    score = min(1.0, base_score + weight_boost * 0.1)

    # Penalties for violations
    if event.impact < 0 and framework in community_frameworks:
        score *= 0.6  # Penalize harm to communities

    if event.duration == 0 and framework values long-term:
        score *= 0.8  # Penalize short-term thinking

    # Boosts for alignment
    if event.impact > 0 and "community" in context:
        if framework in relational_frameworks:
            score *= 1.5  # Up to 50% boost

    return clamp(score, 0.0, 1.0)
```

### Context Weight Integration

Framework evaluators examine event context_weights:
- Matching keywords in weights get boosted (+10% per match)
- Example: "reciprocal" in context_weights → Reciprocity framework gets boost
- Example: "future" in context_weights → Seven Generations gets boost

---

## API Usage

### Request

```json
{
  "event": {
    "at": 1.0,
    "label": "Build community garden with neighbors",
    "impact": 3.0,
    "context_weights": {
      "community": 1.0,
      "relationship": 0.8
    }
  },
  "analysis_type": "aegis"
}
```

### Response

```json
{
  "event_label": "Build community garden with neighbors",
  "aggregate_modulation": 0.5452,
  "framework_scores": {
    "ubuntu": {
      "score": 0.915,
      "tradition": "Indigenous (Bantu/African)",
      "focus": "Shared humanity, community, dignity"
    },
    "care_ethics": {
      "score": 0.885,
      "tradition": "Western (Gilligan/Noddings)",
      "focus": "Relationships, responsiveness, interdependence"
    },
    // ... 23 more frameworks ...
  },
  "strongly_aligned": ["care_ethics", "confucian_harmony", "ubuntu", "covenant_ethics"],
  "strongly_violated": [],
  "tradition_breakdown": {
    "Western": 0.483,
    "Eastern": 0.584,
    "Indigenous": 0.493,
    "African": 0.473,
    "Islamic": 0.610,
    "Jewish": 0.775,
    "Australian": 0.625,
    "Mesoamerican": 0.400
  }
}
```

---

## Conference Talking Points

### "Ethical AI isn't culturally neutral. It should synthesize traditions deliberately."

1. **The Problem**
   - Single tradition blinds you to valid perspectives
   - Western ethics alone misses community, stewardship, spiritual dimensions
   - Creates appearance of cultural imperialism

2. **The Solution**
   - Evaluate against all traditions simultaneously
   - No framework dominates
   - Conflicts are visible and discussed explicitly
   - Context-dependent weighting learned over time

3. **Why It Works**
   - AEGIS is code, not model weights
   - Expansion adds ~500 lines of framework evaluators
   - No retraining required
   - Fully transparent—show which frameworks apply

4. **Why It's Honest**
   - Acknowledges Western origins (original 6 frameworks)
   - Doesn't claim cultural transcendence
   - Shows where frameworks conflict
   - Invites further expansion (add more traditions)

---

## Future Expansion

**Planned Additions**:
- Feminist Ethics (standpoint epistemology, care work)
- Environmental Ethics (deep ecology, land rights)
- Indigenous Pacific (Polynesian, Melanesian)
- Latin American (liberation theology, communitarian)

**Learning Through Cocoons**:
- Track which frameworks matter most per domain
- Learn when traditions align/conflict
- Enable automatic context-weighted framework selection
- Example: "In collective contexts, weight Eastern/Indigenous 2x more"

---

## Limitations & Known Issues

1. **Framework Detail**: Simplified representations of complex traditions
2. **Language Bias**: Evaluation in English; non-English contexts not yet captured
3. **Geographic Representation**: Some regions underrepresented (Pacific, Southeast Asia)
4. **Static Keywords**: Keyword matching is basic; could improve with embeddings
5. **No Weighting**: Currently equal weight for all frameworks; should vary by context

**Roadmap**: Address all limitations by 2027.

---

## References & Further Reading

- **AEGIS_GLOBAL_ETHICS.md** - Full implementation documentation
- [[RC-Plus-Xi Framework]] - Mathematical foundation
- [[April 2, 2026 Breakthrough]] - Integration with EEV
- **GitHub**: reasoning_forge/event_embedded_value.py

---

**Last Updated**: April 4, 2026
**Framework Count**: 25 global traditions
**Status**: Production ready, actively used in conference preparation
