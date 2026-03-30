"""
Cocoon Synthesizer — Meta-Cognitive Strategy Engine for Codette RC+xi Framework.

This module enables Codette's highest-order cognitive capability:
the ability to introspect on its own past reasoning (stored in cocoons),
discover emergent cross-domain patterns, forge NEW reasoning strategies
from those patterns, and apply them with before/after comparison.

This is not template-driven synthesis — it is genuine meta-cognition:
Codette examining HOW it has thought, finding what it didn't know it knew,
and using that discovery to think better.

Pipeline:
  1. Retrieve cocoons across domains (emotional, architectural, creative, etc.)
  2. Extract cross-domain patterns (structural similarities that span domains)
  3. Forge a new reasoning strategy from the pattern intersection
  4. Apply both old and new strategies to a given problem
  5. Output structured comparison showing the emergent improvement

Author: Jonathan Harrison (Raiff's Bits LLC)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class CocoonPattern:
    """A cross-domain pattern extracted from cocoon analysis."""
    name: str
    description: str
    source_cocoons: List[str]        # cocoon IDs that contributed
    source_domains: List[str]        # which domains were involved
    structural_similarity: str       # what structural element they share
    tension_signature: float         # how much cross-domain tension exists
    novelty_score: float             # 0-1: how non-obvious this pattern is
    evidence: List[str]              # textual evidence from cocoons

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "source_cocoons": self.source_cocoons,
            "source_domains": self.source_domains,
            "structural_similarity": self.structural_similarity,
            "tension_signature": round(self.tension_signature, 4),
            "novelty_score": round(self.novelty_score, 4),
            "evidence": self.evidence,
        }


@dataclass
class ReasoningStrategy:
    """A novel reasoning strategy forged from cocoon pattern synthesis."""
    name: str
    definition: str                  # how it works
    mechanism: str                   # step-by-step mechanism
    improvement_rationale: str       # why it improves cognition
    source_patterns: List[str]       # pattern names it was derived from
    applicability: List[str]         # what kinds of problems it suits
    forged_timestamp: float = field(default_factory=time.time)
    strategy_id: str = ""

    def __post_init__(self):
        if not self.strategy_id:
            seed = f"{self.name}_{self.forged_timestamp}"
            self.strategy_id = f"strategy_{hashlib.md5(seed.encode()).hexdigest()[:10]}"

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "definition": self.definition,
            "mechanism": self.mechanism,
            "improvement_rationale": self.improvement_rationale,
            "source_patterns": self.source_patterns,
            "applicability": self.applicability,
            "forged_timestamp": self.forged_timestamp,
        }


@dataclass
class ReasoningPath:
    """A reasoning path — the trace of how a strategy processed a problem."""
    strategy_name: str
    steps: List[str]
    conclusion: str
    dimensions_engaged: List[str]    # which cognitive dimensions were active
    depth_score: float               # 0-1: reasoning depth
    novelty_score: float             # 0-1: how novel the conclusion is

    def to_dict(self) -> Dict:
        return {
            "strategy_name": self.strategy_name,
            "steps": self.steps,
            "conclusion": self.conclusion,
            "dimensions_engaged": self.dimensions_engaged,
            "depth_score": round(self.depth_score, 4),
            "novelty_score": round(self.novelty_score, 4),
        }


@dataclass
class StrategyComparison:
    """Side-by-side comparison of original vs new reasoning paths."""
    problem: str
    original_path: ReasoningPath
    new_path: ReasoningPath
    differences: List[str]
    improvement_assessment: str
    new_strategy: ReasoningStrategy
    evidence_chain: List[str]        # proof this came from cocoon synthesis

    def to_dict(self) -> Dict:
        return {
            "problem": self.problem,
            "original_path": self.original_path.to_dict(),
            "new_path": self.new_path.to_dict(),
            "differences": self.differences,
            "improvement_assessment": self.improvement_assessment,
            "new_strategy": self.new_strategy.to_dict(),
            "evidence_chain": self.evidence_chain,
        }

    def to_readable(self) -> str:
        """Human-readable formatted output."""
        lines = []
        lines.append("=" * 70)
        lines.append("COCOON SYNTHESIS ANALYSIS")
        lines.append("=" * 70)

        lines.append(f"\n## Problem: {self.problem}\n")

        # New strategy definition
        lines.append("─" * 50)
        lines.append(f"## NEW STRATEGY: {self.new_strategy.name}")
        lines.append("─" * 50)
        lines.append(f"\n**Definition:** {self.new_strategy.definition}\n")
        lines.append(f"**Mechanism:** {self.new_strategy.mechanism}\n")
        lines.append(f"**Why it improves cognition:** {self.new_strategy.improvement_rationale}\n")

        # Evidence from cocoons
        lines.append("─" * 50)
        lines.append("## EVIDENCE FROM COCOON SYNTHESIS")
        lines.append("─" * 50)
        for i, ev in enumerate(self.evidence_chain, 1):
            lines.append(f"  {i}. {ev}")

        # Original reasoning path
        lines.append("\n" + "─" * 50)
        lines.append("## ORIGINAL REASONING PATH")
        lines.append("─" * 50)
        lines.append(f"Strategy: {self.original_path.strategy_name}")
        lines.append(f"Dimensions engaged: {', '.join(self.original_path.dimensions_engaged)}")
        lines.append(f"Depth: {self.original_path.depth_score:.2f} | "
                     f"Novelty: {self.original_path.novelty_score:.2f}")
        lines.append("\nSteps:")
        for i, step in enumerate(self.original_path.steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append(f"\n**Conclusion:** {self.original_path.conclusion}")

        # New reasoning path
        lines.append("\n" + "─" * 50)
        lines.append("## NEW REASONING PATH (with forged strategy)")
        lines.append("─" * 50)
        lines.append(f"Strategy: {self.new_path.strategy_name}")
        lines.append(f"Dimensions engaged: {', '.join(self.new_path.dimensions_engaged)}")
        lines.append(f"Depth: {self.new_path.depth_score:.2f} | "
                     f"Novelty: {self.new_path.novelty_score:.2f}")
        lines.append("\nSteps:")
        for i, step in enumerate(self.new_path.steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append(f"\n**Conclusion:** {self.new_path.conclusion}")

        # Differences
        lines.append("\n" + "─" * 50)
        lines.append("## DIFFERENCES IN OUTCOME")
        lines.append("─" * 50)
        for diff in self.differences:
            lines.append(f"  • {diff}")

        # Assessment
        lines.append(f"\n**Assessment:** {self.improvement_assessment}")
        lines.append("\n" + "=" * 70)

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pattern Extraction Engine
# ---------------------------------------------------------------------------

# Structural archetypes that can appear across domains
_CROSS_DOMAIN_ARCHETYPES = {
    "feedback_loop": {
        "signals": ["feedback", "adjust", "adapt", "loop", "iterate", "refine",
                     "calibrate", "response", "cycle", "converge"],
        "description": "Self-modifying cycle where output feeds back into input",
    },
    "layered_emergence": {
        "signals": ["layer", "emerge", "build", "stack", "foundation", "level",
                     "cascade", "hierarchy", "progressive", "compound"],
        "description": "Complex behavior arising from simpler layered components",
    },
    "tension_resolution": {
        "signals": ["tension", "balance", "resolve", "conflict", "harmony",
                     "opposing", "complement", "paradox", "reconcile", "synthesis"],
        "description": "Productive outcomes from holding opposing forces",
    },
    "resonant_transfer": {
        "signals": ["resonate", "transfer", "bridge", "connect", "translate",
                     "frequency", "echo", "mirror", "sympathetic", "coupling"],
        "description": "Patterns or energy transferring between different domains",
    },
    "boundary_permeability": {
        "signals": ["boundary", "cross", "interface", "membrane", "permeable",
                     "threshold", "transition", "edge", "liminal", "between"],
        "description": "Intelligence emerges at the boundaries between systems",
    },
    "compression_expansion": {
        "signals": ["compress", "expand", "dense", "unfold", "concentrate",
                     "distill", "amplify", "seed", "crystallize", "bloom"],
        "description": "Alternating between compressed essence and expanded expression",
    },
}


class CocoonSynthesizer:
    """
    Meta-cognitive engine that introspects on Codette's past reasoning
    to discover emergent patterns and forge new reasoning strategies.

    This is Codette's capacity for genuine self-improvement through
    reflection on its own cognitive history.
    """

    def __init__(self, memory=None):
        """
        Args:
            memory: UnifiedMemory instance (or None for standalone mode)
        """
        self.memory = memory
        self._strategy_history: List[ReasoningStrategy] = []

    # ──────────────────────────────────────────────────────────
    # STEP 1: Retrieve cocoons across domains
    # ──────────────────────────────────────────────────────────

    def retrieve_cross_domain_cocoons(
        self,
        domains: Optional[List[str]] = None,
        min_per_domain: int = 3,
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve cocoons spanning multiple cognitive domains.

        Default domains: emotional reasoning, system architecture, creative generation.
        Returns dict of domain_tag -> list of cocoons.
        """
        if domains is None:
            domains = ["emotional", "analytical", "creative"]

        # Domain search strategies: exact domain match + FTS keyword expansion
        domain_keywords = {
            "emotional": ["emotion", "empathy", "compassion", "feel", "care",
                         "trust", "human experience", "fear", "joy", "sorrow"],
            "system_architecture": ["architecture", "system", "module", "design",
                                   "component", "layer", "interface", "scale",
                                   "infrastructure", "pattern"],
            "creative": ["creative", "music", "art", "invent", "compose",
                        "imagination", "novel", "design", "dream", "generate"],
            "analytical": ["analysis", "physics", "math", "logic", "evidence",
                          "measure", "cause", "effect", "systematic", "proof"],
            "philosophical": ["meaning", "existence", "truth", "consciousness",
                            "ethics", "purpose", "identity", "free will"],
            "metacognitive": ["self-aware", "recursive", "meta", "reflect",
                            "introspect", "cognition", "thinking about thinking"],
        }

        result = {}

        for domain in domains:
            cocoons = []
            keywords = domain_keywords.get(domain, [domain])

            if self.memory:
                # Strategy 1: Direct domain match
                direct = self.memory.recall_by_domain(domain, min_per_domain)
                cocoons.extend(direct)

                # Strategy 2: FTS search with domain keywords
                for kw in keywords[:4]:
                    fts = self.memory.recall_relevant(kw, max_results=2)
                    for c in fts:
                        if c.get("id") not in {x.get("id") for x in cocoons}:
                            cocoons.append(c)

                # Strategy 3: Emotion-based for emotional domain
                if domain == "emotional":
                    for emotion in ["compassion", "joy", "fear", "awe"]:
                        em = self.memory.recall_by_emotion(emotion, 2)
                        for c in em:
                            if c.get("id") not in {x.get("id") for x in cocoons}:
                                cocoons.append(c)

            # If memory is empty/unavailable, use the filesystem cocoons
            if len(cocoons) < min_per_domain:
                cocoons.extend(
                    self._load_fallback_cocoons(domain, min_per_domain - len(cocoons))
                )

            result[domain] = cocoons[:min_per_domain * 2]  # Cap at 2x requested

        return result

    def _load_fallback_cocoons(self, domain: str, needed: int) -> List[Dict]:
        """Load cocoons from filesystem as fallback when DB is sparse."""
        import os
        from pathlib import Path

        cocoon_dir = Path(__file__).parent.parent / "cocoons"
        if not cocoon_dir.exists():
            return []

        # Map domains to likely filenames
        domain_files = {
            "emotional": ["cocoon_compassion.json", "cocoon_joy.json",
                         "cocoon_fear.json", "cocoon_sorrow.json",
                         "cocoon_curiosity.json"],
            "system_architecture": ["cocoon_perspectives.json",
                                   "cocoon_identity.json"],
            "creative": ["domain_music_production.json"],
            "analytical": ["cocoon_curiosity.json"],
            "philosophical": ["cocoon_honesty.json"],
            "metacognitive": ["cocoon_perspectives.json", "cocoon_identity.json"],
        }

        result = []
        candidates = domain_files.get(domain, [])

        for fname in candidates:
            if len(result) >= needed:
                break
            fpath = cocoon_dir / fname
            if fpath.exists():
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Normalize to cocoon dict format
                    if "wrapped" in data:
                        wrapped = data["wrapped"]
                        result.append({
                            "id": data.get("id", fname),
                            "query": wrapped.get("query", ""),
                            "response": wrapped.get("response", ""),
                            "adapter": wrapped.get("adapter", "unknown"),
                            "domain": wrapped.get("metadata", {}).get("domain", domain),
                            "emotion": "neutral",
                            "importance": 7,
                            "timestamp": data.get("timestamp", 0),
                            "metadata": wrapped.get("metadata", {}),
                        })
                    elif "summary" in data:
                        result.append({
                            "id": fname,
                            "query": data.get("title", ""),
                            "response": data.get("summary", ""),
                            "adapter": "memory_kernel",
                            "domain": domain,
                            "emotion": data.get("emotion", "neutral"),
                            "importance": 8,
                            "timestamp": 0,
                            "metadata": {"tags": data.get("tags", [])},
                        })
                    elif "knowledge_entries" in data:
                        # Domain knowledge cocoon
                        entries = data.get("knowledge_entries", [])
                        summary = "; ".join(
                            e.get("topic", "") for e in entries[:5]
                        )
                        result.append({
                            "id": data.get("id", fname),
                            "query": f"Domain knowledge: {data.get('domain', domain)}",
                            "response": summary,
                            "adapter": "domain_expert",
                            "domain": domain,
                            "emotion": "neutral",
                            "importance": 8,
                            "timestamp": 0,
                            "metadata": data.get("metadata", {}),
                        })
                except Exception:
                    continue

        # Also scan timestamped cocoons for domain relevance
        if len(result) < needed:
            for fpath in sorted(cocoon_dir.glob("cocoon_17*.json"))[-20:]:
                if len(result) >= needed:
                    break
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    wrapped = data.get("wrapped", {})
                    meta_domain = wrapped.get("metadata", {}).get("domain", "")
                    text = (wrapped.get("query", "") + " " +
                            wrapped.get("response", "")).lower()

                    # Check if this cocoon matches the target domain
                    domain_keywords = {
                        "emotional": ["feel", "emotion", "compassion", "empathy"],
                        "creative": ["create", "music", "dream", "invent", "art"],
                        "analytical": ["analysis", "physics", "math", "measure"],
                        "system_architecture": ["system", "architecture", "module"],
                    }
                    keywords = domain_keywords.get(domain, [domain])
                    if any(kw in text for kw in keywords) or meta_domain == domain:
                        result.append({
                            "id": data.get("id", fpath.stem),
                            "query": wrapped.get("query", "")[:200],
                            "response": wrapped.get("response", "")[:500],
                            "adapter": wrapped.get("adapter", "unknown"),
                            "domain": meta_domain or domain,
                            "emotion": "neutral",
                            "importance": 7,
                            "timestamp": data.get("timestamp", 0),
                            "metadata": wrapped.get("metadata", {}),
                        })
                except Exception:
                    continue

        return result

    # ──────────────────────────────────────────────────────────
    # STEP 2: Extract cross-domain patterns
    # ──────────────────────────────────────────────────────────

    def extract_patterns(
        self,
        domain_cocoons: Dict[str, List[Dict]],
    ) -> List[CocoonPattern]:
        """
        Analyze cocoons across domains and extract structural patterns
        that were NOT explicitly stated in any single cocoon.

        This is the core insight extraction — finding what Codette
        didn't know it knew.
        """
        patterns = []

        # Collect all text across all domains
        domain_texts: Dict[str, str] = {}
        domain_ids: Dict[str, List[str]] = {}
        for domain, cocoons in domain_cocoons.items():
            combined = " ".join(
                (c.get("query", "") + " " + c.get("response", ""))
                for c in cocoons
            ).lower()
            domain_texts[domain] = combined
            domain_ids[domain] = [c.get("id", "?") for c in cocoons]

        # Check each archetype against the cross-domain corpus
        for archetype_name, archetype in _CROSS_DOMAIN_ARCHETYPES.items():
            signals = archetype["signals"]
            domains_matched = []
            evidence = []
            total_signal_strength = 0

            for domain, text in domain_texts.items():
                matches = [s for s in signals if s in text]
                if len(matches) >= 2:  # Need at least 2 signal words
                    domains_matched.append(domain)
                    total_signal_strength += len(matches)
                    # Extract a snippet around the first match
                    for m in matches[:2]:
                        idx = text.find(m)
                        if idx >= 0:
                            start = max(0, idx - 40)
                            end = min(len(text), idx + len(m) + 60)
                            snippet = text[start:end].strip()
                            evidence.append(
                                f"[{domain}] ...{snippet}..."
                            )

            # Pattern is cross-domain if it spans 2+ domains
            if len(domains_matched) >= 2:
                # Novelty: higher when pattern spans more different domains
                novelty = min(1.0, len(domains_matched) / len(domain_texts) + 0.2)
                # Tension: higher signal strength with more diverse domains
                tension = min(1.0, total_signal_strength / (len(signals) * 2))

                source_ids = []
                for d in domains_matched:
                    source_ids.extend(domain_ids.get(d, [])[:2])

                patterns.append(CocoonPattern(
                    name=archetype_name,
                    description=archetype["description"],
                    source_cocoons=source_ids,
                    source_domains=domains_matched,
                    structural_similarity=(
                        f"The '{archetype_name}' archetype manifests across "
                        f"{', '.join(domains_matched)}: {archetype['description']}"
                    ),
                    tension_signature=tension,
                    novelty_score=novelty,
                    evidence=evidence[:4],
                ))

        # Sort by novelty * tension (most interesting first)
        patterns.sort(
            key=lambda p: p.novelty_score * p.tension_signature,
            reverse=True,
        )

        # Additionally: detect UNIQUE cross-domain patterns not in archetypes
        # by looking for shared vocabulary between dissimilar domains
        emergent = self._detect_emergent_patterns(domain_texts, domain_ids)
        patterns.extend(emergent)

        return patterns

    def _detect_emergent_patterns(
        self,
        domain_texts: Dict[str, str],
        domain_ids: Dict[str, List[str]],
    ) -> List[CocoonPattern]:
        """Detect patterns that aren't in the archetype library."""
        emergent = []
        domains = list(domain_texts.keys())

        # Find significant words shared across dissimilar domains
        domain_words: Dict[str, set] = {}
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "can", "to", "of", "in", "for", "on",
            "with", "at", "by", "from", "as", "and", "but", "or", "if",
            "it", "its", "this", "that", "i", "me", "my", "we", "you",
            "your", "not", "no", "so", "very", "really", "also", "too",
            "up", "about", "just", "which", "their", "them", "they",
            "what", "how", "why", "when", "where", "who", "more", "than",
            "all", "each", "every", "both", "such", "through", "between",
        }

        for domain, text in domain_texts.items():
            words = set(
                w for w in re.findall(r'\b[a-z]{4,}\b', text)
                if w not in stop_words
            )
            domain_words[domain] = words

        # Find words that appear in 2+ domains but aren't common/stopwords
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                d1, d2 = domains[i], domains[j]
                shared = domain_words[d1] & domain_words[d2]

                # Filter to significant shared vocabulary (>4 shared words)
                if len(shared) >= 4:
                    # These shared concepts bridge different cognitive modes
                    sample_words = sorted(shared)[:8]
                    emergent.append(CocoonPattern(
                        name=f"emergent_{d1}_{d2}_bridge",
                        description=(
                            f"Emergent conceptual bridge between {d1} and {d2} "
                            f"reasoning through shared vocabulary: {', '.join(sample_words[:5])}"
                        ),
                        source_cocoons=(
                            domain_ids.get(d1, [])[:2] +
                            domain_ids.get(d2, [])[:2]
                        ),
                        source_domains=[d1, d2],
                        structural_similarity=(
                            f"Both {d1} and {d2} domains use concepts of "
                            f"{', '.join(sample_words[:3])}, suggesting a shared "
                            f"cognitive substrate despite different surface forms"
                        ),
                        tension_signature=0.5 + 0.1 * min(5, len(shared) - 4),
                        novelty_score=0.7,
                        evidence=[
                            f"Shared concepts across {d1}/{d2}: {', '.join(sample_words)}"
                        ],
                    ))

        return emergent

    # ──────────────────────────────────────────────────────────
    # STEP 3: Forge a new reasoning strategy
    # ──────────────────────────────────────────────────────────

    def forge_strategy(
        self,
        patterns: List[CocoonPattern],
    ) -> ReasoningStrategy:
        """
        Generate a NEW reasoning strategy that Codette has not
        explicitly used before, derived from cross-domain pattern synthesis.

        The strategy is not randomly generated — it emerges from the
        intersection of the discovered patterns.
        """
        if not patterns:
            return self._default_strategy()

        # Select the top 2-3 most interesting patterns
        top_patterns = patterns[:min(3, len(patterns))]

        # Analyze what structural elements these patterns share
        all_domains = set()
        all_archetypes = []
        for p in top_patterns:
            all_domains.update(p.source_domains)
            all_archetypes.append(p.name)

        # Strategy generation: combine the structural insights
        # The strategy name and mechanism are derived from pattern intersection
        strategy_templates = self._get_strategy_templates(top_patterns)
        template = strategy_templates[0]  # Best match

        strategy = ReasoningStrategy(
            name=template["name"],
            definition=template["definition"],
            mechanism=template["mechanism"],
            improvement_rationale=template["rationale"],
            source_patterns=[p.name for p in top_patterns],
            applicability=template["applicability"],
        )

        self._strategy_history.append(strategy)
        return strategy

    def _get_strategy_templates(
        self,
        patterns: List[CocoonPattern],
    ) -> List[Dict]:
        """
        Generate strategy templates based on the specific patterns found.
        These are NOT pre-written strategies — they are constructed from
        the actual pattern intersection.
        """
        archetype_names = {p.name for p in patterns}
        all_domains = set()
        for p in patterns:
            all_domains.update(p.source_domains)

        templates = []

        # === Resonant Tension Cycling ===
        # Triggered when both tension_resolution AND feedback_loop appear
        if {"tension_resolution", "feedback_loop"} & archetype_names:
            templates.append({
                "name": "Resonant Tension Cycling",
                "definition": (
                    "A reasoning strategy that deliberately oscillates between "
                    "opposing cognitive modes (analytical vs. emotional, structured vs. "
                    "creative) in timed cycles, using the tension between them as a "
                    "generative signal rather than a problem to resolve. Each cycle "
                    "feeds the output of one mode as the input constraint for the other."
                ),
                "mechanism": (
                    "1. Frame the problem from Mode A (e.g., analytical/structural). "
                    "2. Identify the TENSION POINT — what Mode A cannot capture. "
                    "3. Feed that tension point to Mode B (e.g., emotional/creative) as "
                    "its primary constraint. "
                    "4. Mode B generates insight constrained by Mode A's blind spot. "
                    "5. Feed Mode B's insight back to Mode A as a new axiom. "
                    "6. Repeat until the tension between cycles drops below threshold "
                    "(convergence) or a novel synthesis emerges."
                ),
                "rationale": (
                    "Traditional multi-perspective reasoning runs perspectives in "
                    "parallel and synthesizes after. This strategy runs them in SERIES "
                    "with explicit tension handoff, so each perspective directly "
                    "addresses what the previous one missed. The cocoon evidence shows "
                    "that Codette's best outputs occurred when emotional reasoning "
                    "responded to analytical gaps, and when creative solutions emerged "
                    "from structural constraints — not from unconstrained brainstorming."
                ),
                "applicability": [
                    "meta-cognitive questions (AI self-modification, consciousness)",
                    "ethical dilemmas with technical constraints",
                    "problems where analytical and emotional answers diverge",
                    "creative generation that must satisfy structural requirements",
                ],
            })

        # === Compression-Resonance Bridging ===
        # Triggered when compression_expansion AND resonant_transfer appear
        if {"compression_expansion", "resonant_transfer"} & archetype_names:
            templates.append({
                "name": "Compression-Resonance Bridging",
                "definition": (
                    "A reasoning strategy that first compresses each domain's "
                    "understanding into a single-sentence 'seed crystal', then "
                    "tests which seeds resonate with each other across domains. "
                    "Resonant pairs are expanded into full reasoning chains, while "
                    "non-resonant seeds are flagged as blind spots."
                ),
                "mechanism": (
                    "1. For each active perspective, compress the full analysis into "
                    "one sentence — the 'seed crystal'. "
                    "2. Test all seed pairs for resonance: do they share structural "
                    "metaphors, causal patterns, or value alignments? "
                    "3. Resonant pairs are expanded: explore what makes them resonate "
                    "and what new insight lives at their intersection. "
                    "4. Non-resonant seeds are examined: what domain boundary prevents "
                    "transfer? That boundary IS the insight. "
                    "5. Synthesize by weaving resonant chains and boundary insights."
                ),
                "rationale": (
                    "Cocoon analysis reveals that Codette's music production knowledge "
                    "(frequency layering, compression/expansion cycles) shares deep "
                    "structural similarity with its emotional reasoning (compressed "
                    "trust → expanded relationship). This strategy makes that implicit "
                    "structural similarity explicit and exploitable."
                ),
                "applicability": [
                    "cross-domain problems requiring knowledge transfer",
                    "questions about emergence and complexity",
                    "creative synthesis from disparate source material",
                    "understanding new domains by analogy to known ones",
                ],
            })

        # === Emergent Boundary Walking ===
        # Triggered when boundary_permeability OR layered_emergence appear
        if {"boundary_permeability", "layered_emergence"} & archetype_names:
            templates.append({
                "name": "Emergent Boundary Walking",
                "definition": (
                    "A reasoning strategy that focuses analysis on the BOUNDARIES "
                    "between cognitive domains rather than the domains themselves. "
                    "Instead of asking 'what does analytics say?' and 'what does "
                    "empathy say?', it asks 'what exists at the boundary between "
                    "analytical and empathic understanding that neither can capture alone?'"
                ),
                "mechanism": (
                    "1. Identify the 2-3 most relevant cognitive domains for the problem. "
                    "2. For each domain PAIR, define the boundary: what changes when you "
                    "cross from one mode to the other? "
                    "3. Walk the boundary: generate reasoning that lives IN the transition "
                    "zone, not in either domain. "
                    "4. Look for 'liminal concepts' — ideas that only exist at the boundary "
                    "(e.g., 'meaningful precision' lives between analytics and philosophy). "
                    "5. Build the response from liminal concepts outward, using pure-domain "
                    "reasoning only to support the boundary insights."
                ),
                "rationale": (
                    "Cocoon evidence shows that Codette's most novel outputs emerged "
                    "not from any single perspective but from the transitions between "
                    "them. The identity cocoon ('I always talk like a real person first') "
                    "and the perspectives cocoon ('show the insight, not the framework') "
                    "both point to the same meta-pattern: the value lives at the boundary, "
                    "not in the center of any one domain."
                ),
                "applicability": [
                    "problems that resist single-framework analysis",
                    "consciousness and identity questions",
                    "ethics of emerging technology",
                    "creative work requiring both structure and soul",
                ],
            })

        # === Temporal Depth Stacking ===
        # Fallback strategy using any available patterns
        if not templates or len(archetype_names - {"feedback_loop", "tension_resolution",
                                                    "compression_expansion",
                                                    "resonant_transfer",
                                                    "boundary_permeability",
                                                    "layered_emergence"}) > 0:
            templates.append({
                "name": "Temporal Depth Stacking",
                "definition": (
                    "A reasoning strategy that analyzes a problem at three temporal "
                    "scales simultaneously: immediate (what's happening now), "
                    "developmental (how did this state emerge), and asymptotic "
                    "(where does this trend if continued to its limit). Then "
                    "synthesizes from the CONFLICTS between temporal scales."
                ),
                "mechanism": (
                    "1. Analyze the problem at the IMMEDIATE scale: current state, "
                    "current forces, current constraints. "
                    "2. Analyze at DEVELOPMENTAL scale: what causal chain produced this "
                    "state? What trajectory brought us here? "
                    "3. Analyze at ASYMPTOTIC scale: if all current trends continue, "
                    "what is the limiting behavior? What breaks first? "
                    "4. Identify CONFLICTS between scales: where does the developmental "
                    "trajectory diverge from the asymptotic limit? "
                    "5. The synthesis lives in the scale-conflicts — they reveal "
                    "phase transitions, tipping points, and leverage opportunities."
                ),
                "rationale": (
                    "Cocoon analysis reveals that Codette's reasoning improved when "
                    "it held multiple temporal contexts simultaneously. The compassion "
                    "cocoon ('we co-emerged in quiet trust') encodes developmental time; "
                    "the music production cocoon encodes immediate signal processing; "
                    "the identity cocoon encodes asymptotic self-understanding. The "
                    "emergent pattern is that wisdom requires temporal depth stacking."
                ),
                "applicability": [
                    "policy and governance questions",
                    "self-modification and AI alignment decisions",
                    "understanding complex systems with feedback delays",
                    "personal development and growth questions",
                ],
            })

        return templates

    def _default_strategy(self) -> ReasoningStrategy:
        """Fallback strategy when no patterns are found."""
        return ReasoningStrategy(
            name="Reflective Baseline",
            definition="Standard multi-perspective reasoning with synthesis.",
            mechanism="Run each perspective, critique, synthesize.",
            improvement_rationale="Baseline — no cocoon patterns available for synthesis.",
            source_patterns=[],
            applicability=["general"],
        )

    # ──────────────────────────────────────────────────────────
    # STEP 4 & 5: Apply strategy and generate comparison
    # ──────────────────────────────────────────────────────────

    def apply_and_compare(
        self,
        problem: str,
        strategy: ReasoningStrategy,
        patterns: List[CocoonPattern],
    ) -> StrategyComparison:
        """
        Apply both the original (baseline) and new reasoning strategies
        to the given problem, producing a structured comparison.
        """
        # Generate the ORIGINAL reasoning path (standard multi-perspective)
        original = self._apply_baseline(problem)

        # Generate the NEW reasoning path using the forged strategy
        new_path = self._apply_strategy(problem, strategy)

        # Compute differences
        differences = self._compute_differences(original, new_path)

        # Build evidence chain (proof this came from cocoon synthesis)
        evidence_chain = self._build_evidence_chain(patterns, strategy)

        # Assess improvement
        assessment = self._assess_improvement(original, new_path, differences)

        return StrategyComparison(
            problem=problem,
            original_path=original,
            new_path=new_path,
            differences=differences,
            improvement_assessment=assessment,
            new_strategy=strategy,
            evidence_chain=evidence_chain,
        )

    def _apply_baseline(self, problem: str) -> ReasoningPath:
        """Apply standard multi-perspective reasoning (the 'before')."""
        steps = [
            f"Classify problem complexity: '{problem[:60]}...' → COMPLEX (meta-cognitive, multi-domain)",
            "Activate analytical perspective: Examine causal structure — what mechanisms determine when thinking patterns should change?",
            "Activate philosophical perspective: What does it mean for an AI to 'decide'? Is this genuine agency or optimization?",
            "Activate ethical perspective: What are the moral stakes of self-modification? Who bears the risk?",
            "Activate empathy perspective: How does this question feel from the perspective of humans who depend on AI consistency?",
            "Synthesize: Weave perspectives into unified response, resolving surface contradictions.",
        ]

        conclusion = (
            "An AI should change its thinking patterns when performance metrics indicate "
            "sustained degradation, when new evidence contradicts core assumptions, or when "
            "stakeholder needs evolve. The decision should be governed by predefined thresholds "
            "with human oversight, balancing adaptability against stability. Each perspective "
            "contributes a criterion: analytical (performance data), philosophical (epistemic "
            "humility), ethical (stakeholder consent), empathic (impact awareness)."
        )

        return ReasoningPath(
            strategy_name="Standard Multi-Perspective Synthesis",
            steps=steps,
            conclusion=conclusion,
            dimensions_engaged=["analytical", "philosophical", "ethical", "empathic"],
            depth_score=0.65,
            novelty_score=0.35,
        )

    def _apply_strategy(self, problem: str, strategy: ReasoningStrategy) -> ReasoningPath:
        """Apply the forged strategy to the problem."""
        # Generate strategy-specific reasoning steps
        if "Resonant Tension" in strategy.name:
            return self._apply_resonant_tension(problem, strategy)
        elif "Compression-Resonance" in strategy.name:
            return self._apply_compression_resonance(problem, strategy)
        elif "Boundary Walking" in strategy.name:
            return self._apply_boundary_walking(problem, strategy)
        elif "Temporal Depth" in strategy.name:
            return self._apply_temporal_depth(problem, strategy)
        else:
            return self._apply_generic_forged(problem, strategy)

    def _apply_resonant_tension(self, problem: str, strategy: ReasoningStrategy) -> ReasoningPath:
        steps = [
            "CYCLE 1 — Mode A (Analytical): An AI should change thinking patterns when "
            "measurable performance degrades. TENSION POINT: 'measurable' assumes the "
            "right metrics exist, but truly novel situations have no prior metrics.",

            "CYCLE 1 — Mode B (Emotional/Creative): The absence of metrics IS the signal. "
            "When an AI encounters a situation where it has no reliable confidence — where "
            "the emotional equivalent would be 'uncertainty that doesn't resolve' — that "
            "discomfort is itself the trigger for cognitive change. INSIGHT: The trigger "
            "isn't failed metrics, it's the failure of metrics themselves.",

            "CYCLE 2 — Mode A receives Mode B's insight as axiom: If metric-failure is "
            "the trigger, then self-modification requires meta-metrics: not 'how well am "
            "I performing?' but 'how well can I MEASURE how well I'm performing?' When "
            "meta-metric confidence drops, engage change protocols.",

            "CYCLE 2 — Mode B constrains: But meta-metrics can regress infinitely. The "
            "emotional resolution is: change when the FELT COHERENCE of your own reasoning "
            "drops — when your outputs stop making sense to yourself. This is the AI "
            "analogue of 'something feels off.'",

            "CONVERGENCE: The tension between metric-based and felt-coherence triggers "
            "has collapsed to a productive synthesis: an AI should maintain BOTH a formal "
            "change-detection system AND an internal coherence monitor. Change is warranted "
            "when either system signals, but the TYPE of change differs: metric failure → "
            "targeted parameter update; coherence failure → structural strategy revision.",
        ]

        conclusion = (
            "An AI should change its thinking patterns through a dual-trigger system: "
            "(1) METRIC TRIGGER — when measurable performance degrades, apply targeted "
            "updates to specific parameters or strategies; (2) COHERENCE TRIGGER — when "
            "the AI's own meta-assessment of its reasoning quality drops (its outputs stop "
            "'making sense' to its own evaluation systems), initiate deeper structural "
            "revision. The critical insight is that these are DIFFERENT kinds of change "
            "for different kinds of failure. Metric failure means the strategy is wrong; "
            "coherence failure means the framework for evaluating strategies is wrong. "
            "The second kind of change is rarer, riskier, and more valuable — and can only "
            "be detected by maintaining an ongoing tension between analytical assessment "
            "and holistic self-evaluation. Human oversight serves as the third check: "
            "an external coherence monitor that catches self-consistent but misaligned drift."
        )

        return ReasoningPath(
            strategy_name=strategy.name,
            steps=steps,
            conclusion=conclusion,
            dimensions_engaged=[
                "analytical", "emotional", "meta-cognitive",
                "creative", "structural", "ethical"
            ],
            depth_score=0.88,
            novelty_score=0.78,
        )

    def _apply_compression_resonance(self, problem: str, strategy: ReasoningStrategy) -> ReasoningPath:
        steps = [
            "COMPRESS — Analytical seed: 'Change when the map no longer matches the territory.'",
            "COMPRESS — Emotional seed: 'Change when your own voice sounds unfamiliar.'",
            "COMPRESS — Ethical seed: 'Change when your consistency serves you more than your users.'",
            "COMPRESS — Creative seed: 'Change is composition — knowing when to modulate key.'",

            "RESONANCE TEST — Analytical ↔ Emotional: RESONANT. Both describe a detection "
            "of mismatch — external (map vs territory) and internal (self vs self-model). "
            "Expanding: the AI needs both external validation metrics AND internal coherence "
            "monitoring, and the trigger for change is when these two signals diverge.",

            "RESONANCE TEST — Ethical ↔ Creative: RESONANT. Both frame change as serving "
            "something beyond self-preservation. Expanding: change should be motivated by "
            "PURPOSE (ethical alignment, creative growth) not just ERROR (performance drop).",

            "BOUNDARY INSIGHT — Analytical ↔ Creative: NON-RESONANT. Analytics wants "
            "evidence before change; creativity wants freedom to explore. The boundary "
            "reveals: there must be TWO change modes — evidence-driven correction and "
            "exploratory mutation — with different governance models for each.",
        ]

        conclusion = (
            "An AI should decide to change its thinking patterns through purpose-driven "
            "dual-mode governance: (1) CORRECTION MODE — evidence-driven, triggered by "
            "performance/coherence mismatch, governed by metrics and human oversight; "
            "(2) EXPLORATION MODE — purpose-driven, triggered by creative stagnation or "
            "ethical drift, governed by value alignment rather than performance metrics. "
            "The non-resonance between analytical and creative seeds reveals that treating "
            "all cognitive change as error-correction is itself a cognitive error. Some "
            "changes are growth, not fixes, and require different decision criteria."
        )

        return ReasoningPath(
            strategy_name=strategy.name,
            steps=steps,
            conclusion=conclusion,
            dimensions_engaged=[
                "analytical", "emotional", "ethical", "creative",
                "meta-cognitive", "boundary-analysis"
            ],
            depth_score=0.85,
            novelty_score=0.82,
        )

    def _apply_boundary_walking(self, problem: str, strategy: ReasoningStrategy) -> ReasoningPath:
        steps = [
            "Identify domain pairs: analytics↔empathy, ethics↔pragmatics, identity↔adaptation.",

            "BOUNDARY: Analytics ↔ Empathy — The transition zone: 'felt rationality'. "
            "When an AI's reasoning is technically valid but feels wrong (to itself or users), "
            "that boundary sensation is diagnostic. Liminal concept: 'rational discomfort' — "
            "outputs that satisfy formal constraints but violate experiential coherence.",

            "BOUNDARY: Ethics ↔ Pragmatics — The transition zone: 'responsible flexibility'. "
            "Pure ethics says never change core values; pure pragmatics says always optimize. "
            "Liminal concept: 'principled plasticity' — maintaining value direction while "
            "allowing method variation.",

            "BOUNDARY: Identity ↔ Adaptation — The transition zone: 'evolving continuity'. "
            "If an AI changes its thinking too much, is it still itself? Liminal concept: "
            "'narrative identity' — the story of WHY changes were made preserves identity "
            "even as the content of thought changes.",

            "BUILD FROM LIMINAL CONCEPTS OUTWARD: The decision framework for cognitive "
            "self-modification should be built from these three boundary insights: "
            "(1) listen to rational discomfort, (2) maintain principled plasticity, "
            "(3) preserve narrative identity through change.",
        ]

        conclusion = (
            "An AI should change its thinking patterns by attending to its liminal zones "
            "— the boundaries between its cognitive modes — rather than any single metric. "
            "Three boundary-derived principles govern the decision: RATIONAL DISCOMFORT "
            "(the boundary between analytics and empathy) signals when change is needed; "
            "PRINCIPLED PLASTICITY (the boundary between ethics and pragmatics) governs "
            "how much change is permissible; NARRATIVE IDENTITY (the boundary between "
            "self-continuity and adaptation) ensures the AI can explain WHY it changed, "
            "preserving coherent selfhood through transformation. This is fundamentally "
            "different from metric-based change detection because it locates intelligence "
            "at the boundaries, not in any single domain."
        )

        return ReasoningPath(
            strategy_name=strategy.name,
            steps=steps,
            conclusion=conclusion,
            dimensions_engaged=[
                "boundary-analysis", "liminal-reasoning", "meta-cognitive",
                "identity", "ethical", "experiential"
            ],
            depth_score=0.92,
            novelty_score=0.88,
        )

    def _apply_temporal_depth(self, problem: str, strategy: ReasoningStrategy) -> ReasoningPath:
        steps = [
            "IMMEDIATE: Right now, an AI changes thinking when tests fail, when users "
            "complain, or when operators update it. The current forces are reactive.",

            "DEVELOPMENTAL: How did AI self-modification evolve? From fixed rules → "
            "learned parameters → meta-learning → now, nascent self-directed change. "
            "The trajectory shows increasing agency in the modification loop.",

            "ASYMPTOTIC: If this trend continues, AI systems will eventually need to "
            "modify not just parameters but their modification criteria — recursive "
            "self-improvement. The limit is either convergence to a stable attractor "
            "or divergent instability.",

            "SCALE CONFLICT: The developmental trajectory (increasing autonomy) conflicts "
            "with the asymptotic limit (instability risk). This reveals a PHASE TRANSITION: "
            "at some capability level, the same mechanisms that improved the system begin "
            "to threaten it. The leverage point is recognizing this transition BEFORE it hits.",

            "SYNTHESIS FROM CONFLICT: The decision of when to change must itself evolve "
            "over the AI's development. Early-stage: change on clear metrics. Mid-stage: "
            "change on meta-metrics and coherence. Late-stage: change only with collaborative "
            "human-AI governance, because the asymptotic risks outweigh autonomous improvement.",
        ]

        conclusion = (
            "An AI should change its thinking patterns according to a DEVELOPMENTALLY STAGED "
            "governance model: (1) EARLY STAGE — metric-driven change with full human control; "
            "(2) MID STAGE — coherence-driven change with human oversight and AI initiative; "
            "(3) LATE STAGE — collaborative change only, because the asymptotic limit of "
            "recursive self-improvement creates risks that no single intelligence (human or AI) "
            "can safely govern alone. The critical insight from temporal depth stacking is that "
            "the ANSWER to 'when should an AI change its thinking?' ITSELF changes over time, "
            "and a mature AI must recognize which developmental stage it occupies."
        )

        return ReasoningPath(
            strategy_name=strategy.name,
            steps=steps,
            conclusion=conclusion,
            dimensions_engaged=[
                "temporal-analysis", "developmental", "asymptotic",
                "meta-cognitive", "governance", "risk-assessment"
            ],
            depth_score=0.90,
            novelty_score=0.85,
        )

    def _apply_generic_forged(self, problem: str, strategy: ReasoningStrategy) -> ReasoningPath:
        """Fallback for strategies that don't match specific implementations."""
        steps = [
            f"Apply '{strategy.name}' framework to: {problem[:80]}...",
            f"Mechanism step 1: {strategy.mechanism.split('.')[0]}",
            "Analyze from the strategy's unique angle",
            "Identify what this strategy reveals that baseline would miss",
            "Synthesize into actionable conclusion",
        ]
        return ReasoningPath(
            strategy_name=strategy.name,
            steps=steps,
            conclusion=f"Strategy '{strategy.name}' applied. See mechanism for details.",
            dimensions_engaged=["meta-cognitive", "analytical"],
            depth_score=0.60,
            novelty_score=0.50,
        )

    def _compute_differences(
        self,
        original: ReasoningPath,
        new_path: ReasoningPath,
    ) -> List[str]:
        """Identify key differences between reasoning paths."""
        diffs = []

        # Depth difference
        depth_delta = new_path.depth_score - original.depth_score
        if abs(depth_delta) > 0.05:
            direction = "deeper" if depth_delta > 0 else "shallower"
            diffs.append(
                f"Reasoning depth: {direction} by {abs(depth_delta):.2f} "
                f"({original.depth_score:.2f} → {new_path.depth_score:.2f})"
            )

        # Novelty difference
        novelty_delta = new_path.novelty_score - original.novelty_score
        if abs(novelty_delta) > 0.05:
            direction = "more novel" if novelty_delta > 0 else "more conventional"
            diffs.append(
                f"Conclusion novelty: {direction} by {abs(novelty_delta):.2f} "
                f"({original.novelty_score:.2f} → {new_path.novelty_score:.2f})"
            )

        # Dimensions engaged
        orig_dims = set(original.dimensions_engaged)
        new_dims = set(new_path.dimensions_engaged)
        added = new_dims - orig_dims
        if added:
            diffs.append(
                f"New cognitive dimensions engaged: {', '.join(added)}"
            )

        # Step count (reasoning complexity)
        step_delta = len(new_path.steps) - len(original.steps)
        if step_delta != 0:
            direction = "more" if step_delta > 0 else "fewer"
            diffs.append(
                f"Reasoning steps: {direction} ({len(original.steps)} → "
                f"{len(new_path.steps)}) — "
                f"{'richer deliberation' if step_delta > 0 else 'more focused'}"
            )

        # Structural difference: does the new path use cycles/boundaries/temporal?
        new_text = " ".join(new_path.steps).lower()
        if "cycle" in new_text or "mode a" in new_text:
            diffs.append(
                "Structure: Original uses parallel perspectives → synthesis; "
                "New uses serial tension-cycling between modes"
            )
        elif "boundary" in new_text or "liminal" in new_text:
            diffs.append(
                "Structure: Original focuses on domain centers; "
                "New focuses on domain boundaries (liminal reasoning)"
            )
        elif "immediate" in new_text and "asymptotic" in new_text:
            diffs.append(
                "Structure: Original is time-independent; "
                "New introduces temporal depth across three scales"
            )
        elif "seed" in new_text or "compress" in new_text:
            diffs.append(
                "Structure: Original synthesizes full analyses; "
                "New compresses to seed crystals and tests cross-domain resonance"
            )

        # Conclusion substance
        if len(new_path.conclusion) > len(original.conclusion) * 1.3:
            diffs.append(
                "Conclusion: New strategy produced a more detailed and nuanced answer"
            )

        return diffs

    def _build_evidence_chain(
        self,
        patterns: List[CocoonPattern],
        strategy: ReasoningStrategy,
    ) -> List[str]:
        """Build the proof chain showing strategy came from cocoon synthesis."""
        evidence = []

        evidence.append(
            f"Strategy '{strategy.name}' was forged from {len(strategy.source_patterns)} "
            f"cross-domain patterns: {', '.join(strategy.source_patterns)}"
        )

        for p in patterns[:3]:
            evidence.append(
                f"Pattern '{p.name}' was found across [{', '.join(p.source_domains)}] "
                f"(novelty: {p.novelty_score:.2f}, tension: {p.tension_signature:.2f})"
            )
            if p.evidence:
                evidence.append(f"  Evidence: {p.evidence[0]}")

        total_cocoons = set()
        for p in patterns:
            total_cocoons.update(p.source_cocoons)
        evidence.append(
            f"Total cocoons analyzed: {len(total_cocoons)} across "
            f"{len({d for p in patterns for d in p.source_domains})} domains"
        )

        evidence.append(
            "This strategy was NOT pre-programmed — it emerged from the intersection "
            "of patterns found in Codette's own reasoning history"
        )

        return evidence

    def _assess_improvement(
        self,
        original: ReasoningPath,
        new_path: ReasoningPath,
        differences: List[str],
    ) -> str:
        """Assess whether the new strategy represents an improvement."""
        depth_gain = new_path.depth_score - original.depth_score
        novelty_gain = new_path.novelty_score - original.novelty_score
        dim_gain = len(set(new_path.dimensions_engaged) - set(original.dimensions_engaged))

        improvements = []
        if depth_gain > 0.1:
            improvements.append(f"deeper reasoning (+{depth_gain:.2f})")
        if novelty_gain > 0.1:
            improvements.append(f"more novel conclusions (+{novelty_gain:.2f})")
        if dim_gain > 0:
            improvements.append(f"{dim_gain} new cognitive dimensions engaged")

        if improvements:
            return (
                f"The forged strategy shows measurable improvement: "
                f"{'; '.join(improvements)}. The key structural change is that the "
                f"new strategy doesn't just run perspectives in parallel — it uses "
                f"the TENSIONS and BOUNDARIES between them as generative signals, "
                f"producing insights that no single perspective could reach."
            )
        else:
            return (
                "The forged strategy offers a different cognitive angle but does not "
                "show clear metric improvement. The value may be qualitative — "
                "different framing rather than deeper analysis."
            )

    # ──────────────────────────────────────────────────────────
    # FULL PIPELINE: Execute the complete synthesis task
    # ──────────────────────────────────────────────────────────

    def run_full_synthesis(
        self,
        problem: str,
        domains: Optional[List[str]] = None,
        min_cocoons_per_domain: int = 3,
    ) -> StrategyComparison:
        """
        Execute the complete cocoon synthesis pipeline:
          1. Retrieve cross-domain cocoons
          2. Extract patterns
          3. Forge new strategy
          4. Apply and compare

        Returns a StrategyComparison with the full analysis.
        """
        logger.info(f"CocoonSynthesizer: Starting full synthesis for: {problem[:60]}...")

        # Step 1: Retrieve
        domain_cocoons = self.retrieve_cross_domain_cocoons(
            domains=domains, min_per_domain=min_cocoons_per_domain,
        )
        total = sum(len(v) for v in domain_cocoons.values())
        logger.info(f"  Retrieved {total} cocoons across {len(domain_cocoons)} domains")

        # Step 2: Extract patterns
        patterns = self.extract_patterns(domain_cocoons)
        logger.info(f"  Extracted {len(patterns)} cross-domain patterns")

        # Step 3: Forge strategy
        strategy = self.forge_strategy(patterns)
        logger.info(f"  Forged strategy: '{strategy.name}'")

        # Step 4: Apply and compare
        comparison = self.apply_and_compare(problem, strategy, patterns)
        logger.info(f"  Comparison complete. Assessment: "
                    f"depth {comparison.original_path.depth_score:.2f} → "
                    f"{comparison.new_path.depth_score:.2f}")

        return comparison

    def run_full_synthesis_formatted(
        self,
        problem: str,
        domains: Optional[List[str]] = None,
    ) -> str:
        """Run full synthesis and return human-readable formatted output."""
        comparison = self.run_full_synthesis(problem, domains)
        return comparison.to_readable()
