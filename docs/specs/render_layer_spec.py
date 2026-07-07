"""
Codette Architecture - Phase 8 Post-Render Control
Filename: render_layer.py (SPEC — reference copy, not executed)
Author: Jonathan Harrison & Codette
Enforces strict 15% token overlap constraints between AuthoredState and
natural language renderings.

IMPLEMENTATION NOTES (July 7 2026 review):
- ALREADY LIVE: reasoning_forge/state_engine_v8.py verify_render_fidelity(),
  ENFORCING in codette_forge_bridge since commit 5625ab9 — a failed audit
  reverts the response to the substrate's own words.
- Design difference resolved by experiment: this spec counts unique tokens
  INCLUDING stopwords; the live version EXCLUDES stopwords. Tested against
  the genuine 2026-07-05 failure (substrate physics conclusion vs the
  'Tensions remain' template that actually shipped):
      spec (stopwords in):  21.05% -> PASS  (would have shipped the bug)
      live (stopwords out): 11.76% -> FAIL  (correctly rejects it)
  Glue words ('the', 'is', 'so', 'and') inflate stopword-inclusive overlap
  enough to pass drifted renders. Live version retained.
- Worth adopting from this spec: the typed AuthoredState parameter (the
  live version takes strings; a typed contract is Phase 2 work alongside
  the frozen dataclass from core_substrate_spec).
"""

import re
from typing import Set


class RenderLayerVerifier:
    @staticmethod
    def _tokenize_and_clean(text: str) -> Set[str]:
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        tokens = set(clean_text.split())
        tokens.discard('')
        return tokens

    @classmethod
    def verify_render_fidelity(cls, conclusion: str, rendered_response: str,
                               threshold: float = 0.15) -> bool:
        """Jaccard-adjacent word overlap ratio between authored conclusion
        and rendered response."""
        conclusion_tokens = cls._tokenize_and_clean(conclusion)
        rendered_tokens = cls._tokenize_and_clean(rendered_response)
        if not conclusion_tokens:
            return True
        intersection = conclusion_tokens.intersection(rendered_tokens)
        overlap_ratio = len(intersection) / len(conclusion_tokens)
        return overlap_ratio >= threshold
