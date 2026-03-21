"""
Phase 6: Semantic Tension Engine

Computes ξ_semantic using Llama-3.1-8B embeddings instead of token heuristics.
Replaces discrete opposition_score (0.4/0.7/1.0) with continuous [0, 1] semantic distance.

Key innovation: Embedding-based tension captures *real disagreement*, not just
syntactic differences or confidence levels.
"""

from typing import Dict, Tuple
import numpy as np


class SemanticTensionEngine:
    """
    Computes semantic tension (ξ_semantic) between claims using Llama embeddings.

    Strategy:
    1. Embed claims using Llama's final hidden layer
    2. Normalize embeddings (L2)
    3. Compute cosine similarity
    4. Convert to tension: ξ = 1.0 - similarity

    Benefits over heuristic opposition_score:
    - Captures semantic meaning, not just tokens or contradiction keywords
    - Continuous [0, 1] range reveals nuance (not discrete 0.4/0.7/1.0)
    - Robust to paraphrasing (similar meaning = low tension)
    - Detects orthogonal concepts (framework divergence)
    """

    def __init__(self, llama_model=None):
        """
        Initialize with Llama model for embeddings.

        Args:
            llama_model: Llama-3.1-8B instance with .encode() method,
                        or None for testing (will use dummy embeddings)
        """
        self.model = llama_model
        self.embedding_cache = {}  # {claim_text: embedding_vector}
        self.embedding_dim = 4096  # Llama-3.1-8B hidden state dimension

    def embed_claim(self, claim: str, use_cache: bool = True) -> np.ndarray:
        """
        Get normalized embedding from Llama for a claim.

        Args:
            claim: Text claim to embed
            use_cache: If True, reuse cached embeddings

        Returns:
            Normalized embedding, shape (4096,), L2 norm = 1.0
        """
        if use_cache and claim in self.embedding_cache:
            return self.embedding_cache[claim]

        if self.model is None:
            # Fallback for testing: deterministic dummy embedding
            embedding = self._dummy_embedding(claim)
        else:
            try:
                # Get final hidden states from Llama
                hidden_state = self.model.encode(claim)  # Shape: (dim,)

                if hidden_state is None or len(hidden_state) == 0:
                    embedding = self._dummy_embedding(claim)
                else:
                    embedding = np.array(hidden_state, dtype=np.float32)
            except Exception as e:
                print(f"Warning: Embedding failed for '{claim[:50]}...': {e}")
                embedding = self._dummy_embedding(claim)

        # Normalize L2
        norm = np.linalg.norm(embedding)
        if norm > 1e-8:
            embedding = embedding / norm
        else:
            embedding = np.zeros_like(embedding)

        if use_cache:
            self.embedding_cache[claim] = embedding

        return embedding

    def _dummy_embedding(self, text: str) -> np.ndarray:
        """
        Create deterministic dummy embedding from text for testing.
        Not used in production, but allows testing without Llama.
        """
        # Use text hash to seed RNG for reproducibility
        seed = hash(text) % (2**31)
        rng = np.random.RandomState(seed)
        return rng.randn(self.embedding_dim).astype(np.float32)

    def compute_semantic_tension(
        self, claim_a: str, claim_b: str, return_components: bool = False
    ) -> float or Tuple[float, float]:
        """
        Compute ξ_semantic = 1.0 - cosine_similarity(embed_a, embed_b).

        Args:
            claim_a: First claim text
            claim_b: Second claim text
            return_components: If True, also return similarity

        Returns:
            tension (float) in [0, 1], or (tension, similarity) if return_components
            - 0.0 = identical claims (no tension)
            - 0.5 = orthogonal claims (framework divergence)
            - 1.0 = opposite claims (maximum tension)
        """
        embed_a = self.embed_claim(claim_a)
        embed_b = self.embed_claim(claim_b)

        # Cosine similarity for normalized vectors = dot product
        similarity = float(np.dot(embed_a, embed_b))

        # Clamp to [-1, 1] in case of floating point errors
        similarity = np.clip(similarity, -1.0, 1.0)

        # Convert to tension: higher divergence = higher tension
        # Formula: ξ = (1 - similarity) / 2 maps [-1, 1] similarity to [0, 1] tension
        semantic_tension = (1.0 - similarity) / 2.0

        if return_components:
            return semantic_tension, similarity
        return semantic_tension

    def compute_polarity(self, claim_a: str, claim_b: str) -> str:
        """
        Classify the relationship type between two claims using embeddings.

        Logic:
        - similarity > 0.7   : "paraphrase" (same meaning, different wording)
        - similarity < -0.3  : "contradiction" (opposite meanings)
        - -0.3 <= sim <= 0.7 : "framework" (orthogonal/different domains)

        Returns:
            polarity_type: "paraphrase" | "contradiction" | "framework"
        """
        _, similarity = self.compute_semantic_tension(claim_a, claim_b, return_components=True)

        if similarity > 0.7:
            return "paraphrase"
        elif similarity < -0.3:
            return "contradiction"
        else:
            return "framework"

    def explain_tension(self, claim_a: str, claim_b: str) -> Dict:
        """
        Detailed breakdown of semantic tension for debugging/analysis.

        Returns:
            Dict with claims, tension, polarity, similarity, and raw embeddings
        """
        embed_a = self.embed_claim(claim_a)
        embed_b = self.embed_claim(claim_b)

        tension, similarity = self.compute_semantic_tension(claim_a, claim_b, return_components=True)
        polarity = self.compute_polarity(claim_a, claim_b)

        return {
            "claim_a": claim_a[:100],
            "claim_b": claim_b[:100],
            "semantic_tension": round(tension, 4),
            "similarity": round(similarity, 4),
            "polarity_type": polarity,
            "embedding_a_norm": round(float(np.linalg.norm(embed_a)), 4),
            "embedding_b_norm": round(float(np.linalg.norm(embed_b)), 4),
            "embedding_dim": self.embedding_dim,
        }

    def compare_multiple(self, claims: list) -> Dict:
        """
        Compare one claim against multiple others.

        Useful for routing or measuring how divergent a set of claims is.

        Args:
            claims: List of claim strings

        Returns:
            {
                "primary_claim": claims[0],
                "pairwise_tensions": [
                    {"claim": "...", "tension": 0.35, "polarity": "framework"}
                ],
                "mean_tension": 0.42,
                "max_tension": 0.78,
            }
        """
        if len(claims) < 2:
            return {"error": "need at least 2 claims"}

        primary = claims[0]
        comparisons = []

        for claim in claims[1:]:
            tension = self.compute_semantic_tension(primary, claim)
            polarity = self.compute_polarity(primary, claim)
            comparisons.append({
                "claim": claim[:100],
                "tension": round(tension, 4),
                "polarity": polarity,
            })

        mean_tension = float(np.mean([c["tension"] for c in comparisons]))
        max_tension = float(np.max([c["tension"] for c in comparisons]))

        return {
            "primary_claim": primary[:100],
            "pairwise_tensions": comparisons,
            "mean_tension": round(mean_tension, 4),
            "max_tension": round(max_tension, 4),
            "num_compared": len(comparisons),
        }

    def clear_cache(self):
        """Clear embedding cache to free memory."""
        self.embedding_cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get embedding cache statistics."""
        return {
            "cached_embeddings": len(self.embedding_cache),
            "embedding_dim": self.embedding_dim,
            "approximate_cache_size_mb": (len(self.embedding_cache) * self.embedding_dim * 4) / (1024 ** 2),
        }


# Export for use in conflict_engine.py and other modules
__all__ = ["SemanticTensionEngine"]
