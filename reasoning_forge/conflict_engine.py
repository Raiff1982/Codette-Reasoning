"""
Conflict Detection and Classification Engine

Identifies conflicting claims across agent pairs using token-level confidence scores.
Classifies conflicts by type (contradiction, emphasis, framework) and scores strength
weighted by agent confidence.

Author: Claude Code
"""

import re
import logging
import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Phase 4: Memory-Aware Conflict Strength (Self-Correcting Feedback)
# ============================================================================


def adjust_conflict_strength_with_memory(conflict, memory_weighting=None):
    """
    Enhance conflict strength using historical adapter performance.

    Makes conflict importance adaptive: conflicts involving high-performing
    adapters are weighted heavier, enabling experience-aware reasoning.

    Args:
        conflict: Conflict object with agent_a, agent_b, conflict_strength
        memory_weighting: MemoryWeighting instance (or None for no adjustment)

    Returns:
        Adjusted conflict strength (same type as input)
    """
    if not memory_weighting:
        return conflict.conflict_strength

    try:
        # Get adapter performance weights
        weight_a = memory_weighting.adapter_weights.get(conflict.agent_a.lower(), None)
        weight_b = memory_weighting.adapter_weights.get(conflict.agent_b.lower(), None)

        if not weight_a or not weight_b:
            return conflict.conflict_strength

        # Compute average performance
        avg_weight = (weight_a.weight + weight_b.weight) / 2.0

        # Normalize to modifier [0.5, 1.5]
        # weight=0.0 → modifier=0.5 (suppress weak adapter conflicts)
        # weight=1.0 → modifier=1.0 (neutral)
        # weight=2.0 → modifier=1.5 (amplify strong adapter conflicts)
        modifier = 0.5 + (avg_weight / 2.0) * 0.5
        modifier = max(0.5, min(1.5, modifier))

        adjusted = conflict.conflict_strength * modifier

        return adjusted

    except Exception as e:
        logger.debug(f"Error adjusting conflict strength: {e}")
        return conflict.conflict_strength



@dataclass
class Conflict:
    """A detected conflict between two agents on a specific claim."""

    agent_a: str  # First agent
    agent_b: str  # Second agent
    claim_a: str  # Claim from agent A
    claim_b: str  # Claim from agent B
    conflict_type: str  # "contradiction" | "emphasis" | "framework"
    conflict_strength: float  # [0, 1], weighted by agent confidence
    confidence_a: float  # Agent A's confidence in their claim
    confidence_b: float  # Agent B's confidence in their claim
    semantic_overlap: float  # Cosine similarity of claims [0, 1]
    opposition_score: float  # How opposed are the claims [0, 1]

    def to_dict(self) -> Dict:
        """Serialize for storage."""
        return asdict(self)


class ConflictEngine:
    """Detects and scores conflicts between agent responses."""

    def __init__(
        self,
        token_confidence_engine: Optional[object] = None,
        contradiction_threshold: float = 0.7,
        overlap_threshold: float = 0.3,
        semantic_tension_engine: Optional[object] = None,
        max_conflicts_per_pair: int = 2,  # Cap generation at source
        max_total_conflicts: int = 12,    # Total budget (was 10 after capping from 71)
    ):
        """
        Initialize conflict detection engine.

        Args:
            token_confidence_engine: TokenConfidenceEngine for scoring claims
            contradiction_threshold: Semantic overlap needed to consider claims related
            overlap_threshold: Threshold for identifying same-claim conflicts
            semantic_tension_engine: (Phase 6) SemanticTensionEngine for embedding-based tension
            max_conflicts_per_pair: Max conflicts to generate per agent pair (default: 2)
            max_total_conflicts: Max total conflicts allowed (default: 12)
        """
        self.token_confidence = token_confidence_engine
        self.contradiction_threshold = contradiction_threshold
        self.overlap_threshold = overlap_threshold
        self.semantic_tension_engine = semantic_tension_engine  # Phase 6
        self.max_conflicts_per_pair = max_conflicts_per_pair
        self.max_total_conflicts = max_total_conflicts

        # Contradiction pattern pairs (negation patterns)
        self.negation_patterns = [
            (r"\b(no|not|none|neither|never|cannot|doesn['\"]t)\b", "negation"),
            (r"\b(must|should|always|only)\b", "necessity"),
            (r"\b(reject|disagree|oppose|deny|false|wrong)\b", "rejection"),
        ]

    def detect_conflicts(
        self, agent_analyses: Dict[str, str]
    ) -> List[Conflict]:
        """
        Detect conflicts across agent pairs.

        Args:
            agent_analyses: Dict {agent_name: response_text}

        Returns:
            List of Conflicts sorted by strength (descending)
        """
        conflicts = []

        # Score tokens/claims for each agent
        agent_scores = {}
        agent_names = list(agent_analyses.keys())

        for agent_name in agent_names:
            response = agent_analyses[agent_name]
            if self.token_confidence:
                peer_responses = {
                    a: agent_analyses[a]
                    for a in agent_names
                    if a != agent_name
                }
                scores = self.token_confidence.score_tokens(
                    response, agent_name, peer_responses=peer_responses
                )
                agent_scores[agent_name] = scores
            else:
                logger.warning(
                    "No token_confidence engine provided; using fallback scoring"
                )

        # Check each agent pair
        for i, agent_a in enumerate(agent_names):
            for agent_b in agent_names[i + 1 :]:
                claims_a = (
                    agent_scores[agent_a].claims
                    if agent_a in agent_scores
                    else self._extract_simple_claims(agent_analyses[agent_a])
                )
                claims_b = (
                    agent_scores[agent_b].claims
                    if agent_b in agent_scores
                    else self._extract_simple_claims(agent_analyses[agent_b])
                )

                # === FIX: Cap conflicts at source (per-pair) ===
                pair_conflicts = []

                # Check each claim pair
                for claim_a in claims_a:
                    for claim_b in claims_b:
                        # Stop early if we've already hit per-pair limit
                        if len(pair_conflicts) >= self.max_conflicts_per_pair:
                            break

                        # Compute semantic overlap
                        overlap = self._compute_semantic_overlap(claim_a.text, claim_b.text)

                        # If claims are related (high overlap), check for conflict
                        if overlap > self.overlap_threshold:
                            conflict_type, opposition_score = self._classify_conflict(
                                claim_a.text, claim_b.text, overlap
                            )

                            if opposition_score > 0:  # Only include if there's opposition
                                # Conflict strength = product of confidences × opposition
                                conflict_strength = (
                                    claim_a.confidence
                                    * claim_b.confidence
                                    * opposition_score
                                )

                                conflict = Conflict(
                                    agent_a=agent_a,
                                    agent_b=agent_b,
                                    claim_a=claim_a.text,
                                    claim_b=claim_b.text,
                                    conflict_type=conflict_type,
                                    conflict_strength=conflict_strength,
                                    confidence_a=claim_a.confidence,
                                    confidence_b=claim_b.confidence,
                                    semantic_overlap=overlap,
                                    opposition_score=opposition_score,
                                )
                                pair_conflicts.append(conflict)

                    # Stop outer loop too if limit reached
                    if len(pair_conflicts) >= self.max_conflicts_per_pair:
                        break

                # Add this pair's conflicts to global list
                conflicts.extend(pair_conflicts)

        # Sort by strength descending
        conflicts.sort(key=lambda c: c.conflict_strength, reverse=True)

        # === Phase 4: Adjust conflict strength by adapter performance ===
        # Make conflict importance adaptive using historical memory
        for conflict in conflicts:
            memory_weighting = getattr(self, "memory_weighting", None)
            conflict.conflict_strength = adjust_conflict_strength_with_memory(
                conflict, memory_weighting
            )

        # Re-sort after adjustment
        conflicts.sort(key=lambda c: c.conflict_strength, reverse=True)

        # === FIX: Use configurable max_total_conflicts (default 12, up from 10) ===
        # Prevent combinatorial explosion by limiting to max total
        if len(conflicts) > self.max_total_conflicts:
            logger.info(
                f"Capping conflicts: {len(conflicts)} → {self.max_total_conflicts} "
                f"(per-pair cap: {self.max_conflicts_per_pair}, total budget: {self.max_total_conflicts})"
            )
            conflicts = conflicts[: self.max_total_conflicts]

        return conflicts

    def _extract_simple_claims(self, response: str) -> List[object]:
        """
        Fallback: extract simple sentence-based claims without token scoring.

        Returns:
            List of simple claim objects with text and neutral confidence
        """
        claim_pattern = re.compile(r"[.!?]+")
        sentences = claim_pattern.split(response)

        claims = []
        for sentence in sentences:
            if not sentence.strip():
                continue

            # Create simple claim object
            class SimpleClaim:
                def __init__(self, text):
                    self.text = text
                    self.confidence = 0.5  # Neutral
                    self.agent_name = ""

            claims.append(SimpleClaim(sentence.strip()))

        return claims

    def _compute_semantic_overlap(self, claim_a: str, claim_b: str) -> float:
        """
        Compute semantic overlap between two claims via cosine similarity.

        Simple implementation: word overlap ratio.

        Returns:
            Similarity [0, 1]
        """
        words_a = set(claim_a.lower().split())
        words_b = set(claim_b.lower().split())

        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "and",
            "or",
            "of",
            "to",
            "in",
            "that",
            "it",
            "for",
            "with",
        }
        words_a = words_a - stop_words
        words_b = words_b - stop_words

        if not words_a or not words_b:
            return 0.0

        # Jaccard similarity
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        if union == 0:
            return 0.0

        return intersection / union

    def _classify_conflict(
        self, claim_a: str, claim_b: str, overlap: float
    ) -> Tuple[str, float]:
        """
        Classify the type of conflict and compute opposition score.

        Phase 6 Enhancement: Blends heuristic opposition_score (discrete 0.4/0.7/1.0)
        with embedding-based semantic tension (continuous [0, 1]) for nuanced conflicts.

        Returns:
            (conflict_type, opposition_score) where:
            - conflict_type: "contradiction" | "emphasis" | "framework" | "paraphrase"
            - opposition_score: [0, 1] how directly opposed are the claims
              (0 = paraphrase/same, 1 = maximum opposition)
        """
        claim_a_lower = claim_a.lower()
        claim_b_lower = claim_b.lower()

        # --- Compute Heuristic Opposition Score (Phase 1-5) ---
        # Look for negation patterns
        negation_in_a = any(
            re.search(pattern, claim_a_lower) for pattern, _ in self.negation_patterns
        )
        negation_in_b = any(
            re.search(pattern, claim_b_lower) for pattern, _ in self.negation_patterns
        )

        # If one has negation and the other doesn't, likely contradiction
        heuristic_opposition = 1.0
        heuristic_type = "contradiction"
        if negation_in_a != negation_in_b:
            logger.debug(f"Direct contradiction detected:\n  A: {claim_a}\n  B: {claim_b}")
            heuristic_opposition = 1.0
            heuristic_type = "contradiction"
        else:
            # Check for explicit negation of key noun phrases
            key_noun_pattern = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
            nouns_a = set(m.group() for m in key_noun_pattern.finditer(claim_a))
            nouns_b = set(m.group() for m in key_noun_pattern.finditer(claim_b))

            # If different key nouns mentioned, might be framework conflict
            if nouns_a and nouns_b and nouns_a != nouns_b:
                heuristic_opposition = 0.4
                heuristic_type = "framework"
            else:
                # --- Check for emphasis conflict ---
                # Both mention similar concepts but with different priorities
                emphasis_words = ["important", "prioritize", "focus", "emphasize", "weight", "prefer", "favor"]
                emphasis_pattern = "|".join(emphasis_words)

                has_emphasis_a = bool(re.search(emphasis_pattern, claim_a_lower))
                has_emphasis_b = bool(re.search(emphasis_pattern, claim_b_lower))

                if has_emphasis_a and has_emphasis_b:
                    # Both making prioritization claims
                    logger.debug(f"Emphasis conflict detected:\n  A: {claim_a}\n  B: {claim_b}")
                    heuristic_opposition = 0.7
                    heuristic_type = "emphasis"
                else:
                    # Default: framework conflict (valid under different assumptions)
                    heuristic_opposition = 0.4
                    heuristic_type = "framework"

        # --- Phase 6: Compute Semantic Opposition (Embedding-Based) ---
        semantic_opposition = 0.4  # Default fallback
        semantic_type = "framework"

        if self.semantic_tension_engine:
            try:
                semantic_opposition = self.semantic_tension_engine.compute_semantic_tension(claim_a, claim_b)
                semantic_type = self.semantic_tension_engine.compute_polarity(claim_a, claim_b)
                logger.debug(f"Semantic tension: {semantic_opposition:.3f} ({semantic_type})")
            except Exception as e:
                logger.debug(f"Semantic tension computation failed: {e}, using heuristic only")

        # --- Phase 6: Hybrid Opposition Score ---
        # Blend both signals: semantic (0.6) + heuristic (0.4)
        # This gives nuanced, continuous opposition scores while preserving heuristic insight
        if self.semantic_tension_engine:
            final_opposition = 0.6 * semantic_opposition + 0.4 * heuristic_opposition
            final_type = semantic_type  # Prefer semantic classification
        else:
            final_opposition = heuristic_opposition
            final_type = heuristic_type

        return (final_type, float(final_opposition))

    def resolve_conflict_round(
        self,
        conflict: Conflict,
        agent_a_response_round2: str,
        agent_b_response_round2: str,
    ) -> Dict:
        """
        Score whether agents moved towards resolving a conflict in next round.

        Args:
            conflict: The original conflict
            agent_a_response_round2: Agent A's response in round 2
            agent_b_response_round2: Agent B's response in round 2

        Returns:
            Dict with resolution metrics
        """
        # Check if agents mentioned the other's claim in their response
        addressed_by_a = self._is_claim_addressed(conflict.claim_b, agent_a_response_round2)
        addressed_by_b = self._is_claim_addressed(conflict.claim_a, agent_b_response_round2)

        # Check if they've softened their position (added qualifiers)
        softened_a = self._is_claim_softened(conflict.claim_a, agent_a_response_round2)
        softened_b = self._is_claim_softened(conflict.claim_b, agent_b_response_round2)

        resolution_score = 0.0
        if addressed_by_a and addressed_by_b:
            resolution_score += 0.4
        if softened_a and softened_b:
            resolution_score += 0.3
        if addressed_by_a or addressed_by_b:
            resolution_score += 0.1

        resolution_score = min(1.0, resolution_score)

        return {
            "engaged_with_conflict": addressed_by_a or addressed_by_b,
            "both_addressed": addressed_by_a and addressed_by_b,
            "softened_positions": softened_a or softened_b,
            "resolution_score": resolution_score,
        }

    def _is_claim_addressed(self, claim: str, response: str) -> bool:
        """
        Check if a claim is explicitly addressed in response.

        Detects pronoun references, direct quotes, or semantic restatement.
        """
        response_lower = response.lower()
        claim_lower = claim.lower()

        # Direct substring match
        if claim_lower in response_lower:
            return True

        # Check for key words from claim appearing in response
        key_words = [
            w
            for w in claim.split()
            if len(w) > 4 and w.lower() not in ["this", "that", "these", "other"]
        ]

        matching_words = sum(1 for w in key_words if w.lower() in response_lower)
        return matching_words >= 2  # At least 2 key words must appear

    def _is_claim_softened(self, original_claim: str, followup_response: str) -> bool:
        """
        Check if an agent has softened their original claim in follow-up.

        Detects addition of qualifiers, exceptions, or concessions.
        """
        softening_words = [
            "however",
            "though",
            "but",
            "perhaps",
            "maybe",
            "could",
            "might",
            "arguably",
            "in some cases",
            "exception",
            "qualify",
            "depends",
        ]

        response_lower = followup_response.lower()

        # Check for softening language near the original claim
        has_softening = any(word in response_lower for word in softening_words)

        # Check for explicit concession
        has_concession = bool(re.search(r"\b(granted|acknowledge|admit|agree)\b", response_lower))

        return has_softening or has_concession

    def group_conflicts_by_pair(self, conflicts: List[Conflict]) -> Dict[str, List[Conflict]]:
        """
        Group conflicts by agent pair.

        Returns:
            Dict {agent_pair_key: List[Conflict]}
        """
        grouped = defaultdict(list)
        for conflict in conflicts:
            pair_key = f"{conflict.agent_a}_vs_{conflict.agent_b}"
            grouped[pair_key].append(conflict)
        return dict(grouped)

    def summarize_conflicts(self, conflicts: List[Conflict]) -> Dict:
        """
        Generate summary statistics for conflicts.

        Returns:
            Dict with count, average strength, distribution by type
        """
        if not conflicts:
            return {
                "total_conflicts": 0,
                "avg_conflict_strength": 0.0,
                "by_type": {},
                "top_conflicts": [],
            }

        by_type = defaultdict(list)
        for c in conflicts:
            by_type[c.conflict_type].append(c)

        return {
            "total_conflicts": len(conflicts),
            "avg_conflict_strength": sum(c.conflict_strength for c in conflicts) / len(conflicts),
            "by_type": {
                ctype: len(clist) for ctype, clist in by_type.items()
            },
            "type_avg_strength": {
                ctype: sum(c.conflict_strength for c in clist) / len(clist)
                for ctype, clist in by_type.items()
            },
            "top_conflicts": [
                {
                    "agent_a": c.agent_a,
                    "agent_b": c.agent_b,
                    "type": c.conflict_type,
                    "strength": c.conflict_strength,
                    "claim_a_excerpt": c.claim_a[:100],
                    "claim_b_excerpt": c.claim_b[:100],
                }
                for c in conflicts[:5]
            ],
        }


# ============================================================================
# Phase 3: Multi-Round Conflict Evolution Tracking
# ============================================================================


@dataclass
class ConflictEvolution:
    """Track how a conflict changes across multiple debate rounds."""

    original_conflict: Conflict        # From Round 0
    round_trajectories: Dict[int, Dict]  # {round: {strength, addressing_score, ...}}
    resolution_rate: float = 0.0       # (initial - final) / initial
    resolution_type: str = "new"       # "hard_victory"|"soft_consensus"|"stalled"|"worsened"|"resolved"
    resolved_in_round: int = -1        # Which round resolved it? (-1 if unresolved)

    def _compute_resolution_rate(self) -> float:
        """Calculate (initial - final) / initial."""
        if not self.round_trajectories or 0 not in self.round_trajectories:
            return 0.0

        initial_strength = self.round_trajectories[0].get("strength", 0)
        if initial_strength == 0:
            return 0.0

        final_strength = min(
            (s.get("strength", float('inf')) for s in self.round_trajectories.values()),
            default=initial_strength
        )

        return (initial_strength - final_strength) / initial_strength


class ConflictTracker:
    """Track conflicts across multiple debate rounds (Phase 3)."""

    def __init__(self, conflict_engine):
        """Initialize tracker with reference to ConflictEngine."""
        self.conflict_engine = conflict_engine
        self.evolution_data: Dict[str, ConflictEvolution] = {}

    def track_round(self, round_num: int, agent_analyses: Dict[str, str],
                   previous_round_conflicts: List[Conflict]) -> List[ConflictEvolution]:
        """Track conflicts across rounds."""
        current_round_conflicts = self.conflict_engine.detect_conflicts(agent_analyses)

        evolutions = []

        # Track previous conflicts in current round
        for prev_conflict in previous_round_conflicts:
            matches = self._find_matching_conflicts(prev_conflict, current_round_conflicts)

            if matches:
                current_conflict = matches[0]
                evolution = self._compute_evolution(
                    prev_conflict, current_conflict, round_num, agent_analyses
                )
            else:
                evolution = self._mark_resolved(prev_conflict, round_num)

            evolutions.append(evolution)

        # Track new conflicts
        new_conflicts = self._find_new_conflicts(previous_round_conflicts, current_round_conflicts)
        for new_conflict in new_conflicts:
            evolution = ConflictEvolution(
                original_conflict=new_conflict,
                round_trajectories={round_num: {
                    "strength": new_conflict.conflict_strength,
                    "addressing_score": 0.0,
                    "softening_score": 0.0,
                }},
                resolution_rate=0.0,
                resolution_type="new",
                resolved_in_round=-1,
            )
            evolutions.append(evolution)

        return evolutions

    def _find_matching_conflicts(self, conflict: Conflict,
                                candidates: List[Conflict]) -> List[Conflict]:
        """Find conflicts that likely match across rounds."""
        matches = []
        for candidate in candidates:
            # Match if same agent pair
            same_pair = (
                (conflict.agent_a == candidate.agent_a and conflict.agent_b == candidate.agent_b) or
                (conflict.agent_a == candidate.agent_b and conflict.agent_b == candidate.agent_a)
            )

            if same_pair:
                # Check claim overlap
                overlap = self.conflict_engine._compute_semantic_overlap(
                    conflict.claim_a, candidate.claim_a
                )
                if overlap > 0.5:
                    matches.append(candidate)

        return matches

    def _compute_evolution(self, prev_conflict: Conflict, current_conflict: Conflict,
                          round_num: int, agent_analyses: Dict[str, str]) -> ConflictEvolution:
        """Compute how conflict evolved between rounds."""
        # Check if agents addressed each other
        addressing_a = self.conflict_engine._is_claim_addressed(
            prev_conflict.claim_b, agent_analyses.get(current_conflict.agent_a, "")
        )
        addressing_b = self.conflict_engine._is_claim_addressed(
            prev_conflict.claim_a, agent_analyses.get(current_conflict.agent_b, "")
        )
        addressing_score = (float(addressing_a) + float(addressing_b)) / 2.0

        # Check if agents softened positions
        softening_a = self.conflict_engine._is_claim_softened(
            prev_conflict.claim_a, agent_analyses.get(current_conflict.agent_a, "")
        )
        softening_b = self.conflict_engine._is_claim_softened(
            prev_conflict.claim_b, agent_analyses.get(current_conflict.agent_b, "")
        )
        softening_score = (float(softening_a) + float(softening_b)) / 2.0

        # Classify resolution type
        strength_delta = prev_conflict.conflict_strength - current_conflict.conflict_strength
        if strength_delta > prev_conflict.conflict_strength * 0.5:
            resolution_type = "hard_victory"
        elif strength_delta > 0.05:
            resolution_type = "soft_consensus"
        elif abs(strength_delta) < 0.05:
            resolution_type = "stalled"
        else:
            resolution_type = "worsened"

        # Update evolution data
        key = f"{prev_conflict.agent_a}_vs_{prev_conflict.agent_b}"
        if key not in self.evolution_data:
            self.evolution_data[key] = ConflictEvolution(
                original_conflict=prev_conflict,
                round_trajectories={0: {
                    "strength": prev_conflict.conflict_strength,
                    "addressing_score": 0.0,
                    "softening_score": 0.0,
                }},
                resolution_rate=0.0,
                resolution_type="new",
                resolved_in_round=-1,
            )

        self.evolution_data[key].round_trajectories[round_num] = {
            "strength": current_conflict.conflict_strength,
            "addressing_score": addressing_score,
            "softening_score": softening_score,
        }

        self.evolution_data[key].resolution_rate = self.evolution_data[key]._compute_resolution_rate()
        self.evolution_data[key].resolution_type = resolution_type

        return self.evolution_data[key]

    def _mark_resolved(self, conflict: Conflict, round_num: int) -> ConflictEvolution:
        """Mark conflict as resolved (no longer detected)."""
        key = f"{conflict.agent_a}_vs_{conflict.agent_b}"
        if key not in self.evolution_data:
            self.evolution_data[key] = ConflictEvolution(
                original_conflict=conflict,
                round_trajectories={0: {
                    "strength": conflict.conflict_strength,
                    "addressing_score": 0.0,
                    "softening_score": 0.0,
                }},
                resolution_rate=1.0,
                resolution_type="resolved",
                resolved_in_round=round_num,
            )
            self.evolution_data[key].round_trajectories[round_num] = {
                "strength": 0.0,
                "addressing_score": 1.0,
                "softening_score": 1.0,
            }

        return self.evolution_data[key]

    def _find_new_conflicts(self, previous: List[Conflict],
                           current: List[Conflict]) -> List[Conflict]:
        """Find conflicts that are new."""
        prev_pairs = {(c.agent_a, c.agent_b) for c in previous}
        new = []
        for conflict in current:
            pair = (conflict.agent_a, conflict.agent_b)
            if pair not in prev_pairs:
                new.append(conflict)
        return new

    def get_summary(self) -> Dict:
        """Get summary of all conflict evolutions."""
        if not self.evolution_data:
            return {"total_tracked": 0, "message": "No conflicts tracked yet"}

        resolved = [e for e in self.evolution_data.values() if e.resolution_type == "resolved"]
        hard_victory = [e for e in self.evolution_data.values() if e.resolution_type == "hard_victory"]
        soft_consensus = [e for e in self.evolution_data.values() if e.resolution_type == "soft_consensus"]
        stalled = [e for e in self.evolution_data.values() if e.resolution_type == "stalled"]
        worsened = [e for e in self.evolution_data.values() if e.resolution_type == "worsened"]

        avg_resolution = sum(e.resolution_rate for e in self.evolution_data.values()) / len(self.evolution_data)

        return {
            "total_tracked": len(self.evolution_data),
            "resolved": len(resolved),
            "hard_victory": len(hard_victory),
            "soft_consensus": len(soft_consensus),
            "stalled": len(stalled),
            "worsened": len(worsened),
            "avg_resolution_rate": avg_resolution,
            "by_type": {
                "resolved": len(resolved),
                "hard_victory": len(hard_victory),
                "soft_consensus": len(soft_consensus),
                "stalled": len(stalled),
                "worsened": len(worsened),
            },
        }
