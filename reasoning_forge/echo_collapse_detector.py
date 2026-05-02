"""
Echo / Perspective-Collapse Detector

Detects two failure modes in multi-perspective reasoning:

  1. Echo:     A perspective output is nearly identical to the raw input prompt
               — the "lens" is just relabeling the question rather than analyzing it.

  2. Collapse: All perspective outputs are near-identical to each other
               — the multi-perspective call collapsed into a single viewpoint.

Uses token-based cosine similarity (no ML dependencies).
Thresholds:
  echo_threshold:      similarity(output, prompt) > 0.70 → echo risk
  collapse_threshold:  mean pairwise sim across perspectives > 0.80 → collapse
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Text utilities ────────────────────────────────────────────────────────────

_STOP = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would could should may might shall this that these those with "
    "from for of in on at to by as it its i you he she we they and or "
    "but not what when where which how who".split()
)


def _tokenize(text: str) -> List[str]:
    return [
        w for w in re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        if w not in _STOP
    ]


def _term_vec(text: str) -> Counter:
    return Counter(_tokenize(text))


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a if k in b)
    mag_a = sum(v * v for v in a.values()) ** 0.5
    mag_b = sum(v * v for v in b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return round(dot / (mag_a * mag_b), 4)


def _novelty_ratio(output: str, prompt: str) -> float:
    """Fraction of output tokens NOT present in prompt (0=pure echo, 1=all novel)."""
    out_tokens = set(_tokenize(output))
    prompt_tokens = set(_tokenize(prompt))
    if not out_tokens:
        return 0.0
    novel = out_tokens - prompt_tokens
    return round(len(novel) / len(out_tokens), 4)


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class PerspectiveEchoResult:
    """Per-perspective echo analysis."""
    name: str
    similarity_to_prompt: float   # cosine similarity to raw prompt
    novelty_ratio: float          # fraction of unique tokens vs prompt
    token_count: int
    is_echo: bool                 # True if similarity_to_prompt > threshold
    is_too_short: bool            # True if suspiciously short output


@dataclass
class EchoCollapseResult:
    """Full echo + collapse report for a multi-perspective generation."""
    echo_risk: str                      # 'low' | 'medium' | 'high' | 'unknown'
    perspective_collapse_detected: bool
    per_perspective: List[PerspectiveEchoResult] = field(default_factory=list)
    mean_prompt_similarity: float = 0.0
    mean_pairwise_similarity: float = 0.0
    collapse_pairs: List[Tuple[str, str, float]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "echo_risk":                    self.echo_risk,
            "perspective_collapse_detected": self.perspective_collapse_detected,
            "mean_prompt_similarity":        self.mean_prompt_similarity,
            "mean_pairwise_similarity":      self.mean_pairwise_similarity,
            "collapse_pairs": [
                {"a": a, "b": b, "similarity": s}
                for a, b, s in self.collapse_pairs
            ],
            "per_perspective": [
                {
                    "name":                  p.name,
                    "similarity_to_prompt":  p.similarity_to_prompt,
                    "novelty_ratio":         p.novelty_ratio,
                    "token_count":           p.token_count,
                    "is_echo":               p.is_echo,
                    "is_too_short":          p.is_too_short,
                }
                for p in self.per_perspective
            ],
            "summary": self.summary,
        }


# ── Detector ──────────────────────────────────────────────────────────────────

class EchoCollapseDetector:
    """Detect echo and collapse in multi-perspective outputs.

    Args:
        echo_threshold:      similarity(output, prompt) above which output is flagged as echo.
        collapse_threshold:  mean pairwise similarity above which collapse is flagged.
        min_token_count:     outputs shorter than this are flagged as suspiciously short.
    """

    def __init__(
        self,
        echo_threshold: float = 0.70,
        collapse_threshold: float = 0.80,
        min_token_count: int = 15,
    ):
        self.echo_threshold = echo_threshold
        self.collapse_threshold = collapse_threshold
        self.min_token_count = min_token_count

    def check(
        self,
        prompt: str,
        perspective_outputs: Dict[str, str],
    ) -> EchoCollapseResult:
        """Analyze perspective_outputs for echo and collapse.

        Args:
            prompt:               The raw user query / input prompt.
            perspective_outputs:  {perspective_name: output_text}

        Returns:
            EchoCollapseResult with echo_risk, collapse flag, and per-perspective detail.
        """
        if not perspective_outputs:
            return EchoCollapseResult(
                echo_risk="unknown",
                perspective_collapse_detected=False,
                summary="No perspective outputs to analyze.",
            )

        prompt_vec = _term_vec(prompt)
        per_perspective = []
        output_vecs: Dict[str, Counter] = {}

        for name, output in perspective_outputs.items():
            tokens = _tokenize(output)
            out_vec = _term_vec(output)
            output_vecs[name] = out_vec

            sim = _cosine(out_vec, prompt_vec)
            novelty = _novelty_ratio(output, prompt)
            n_tokens = len(tokens)

            per_perspective.append(PerspectiveEchoResult(
                name=name,
                similarity_to_prompt=sim,
                novelty_ratio=novelty,
                token_count=n_tokens,
                is_echo=(sim > self.echo_threshold),
                is_too_short=(n_tokens < self.min_token_count),
            ))

        # ── Echo risk ─────────────────────────────────────────────────────────
        mean_prompt_sim = (
            sum(p.similarity_to_prompt for p in per_perspective) / len(per_perspective)
        )
        n_echo = sum(1 for p in per_perspective if p.is_echo)
        echo_fraction = n_echo / len(per_perspective)

        if echo_fraction >= 0.6 or mean_prompt_sim > 0.80:
            echo_risk = "high"
        elif echo_fraction >= 0.3 or mean_prompt_sim > 0.65:
            echo_risk = "medium"
        else:
            echo_risk = "low"

        # ── Collapse detection ────────────────────────────────────────────────
        names = list(output_vecs.keys())
        pairwise_sims = []
        collapse_pairs = []

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                sim = _cosine(output_vecs[a], output_vecs[b])
                pairwise_sims.append(sim)
                if sim > self.collapse_threshold:
                    collapse_pairs.append((a, b, sim))

        mean_pairwise = (
            sum(pairwise_sims) / len(pairwise_sims) if pairwise_sims else 0.0
        )
        collapse_detected = (
            mean_pairwise > self.collapse_threshold
            or len(collapse_pairs) / max(len(pairwise_sims), 1) > 0.5
        )

        # ── Summary ───────────────────────────────────────────────────────────
        parts = []
        if echo_risk == "high":
            parts.append(
                f"{n_echo}/{len(per_perspective)} perspectives are echoing the prompt "
                f"(mean similarity={mean_prompt_sim:.2f})"
            )
        if collapse_detected:
            parts.append(
                f"Perspective collapse detected: mean pairwise similarity={mean_pairwise:.2f}, "
                f"{len(collapse_pairs)} collapsing pairs"
            )
        if not parts:
            parts.append(
                f"No echo/collapse. Mean prompt-sim={mean_prompt_sim:.2f}, "
                f"mean pairwise-sim={mean_pairwise:.2f}"
            )
        summary = "; ".join(parts)

        return EchoCollapseResult(
            echo_risk=echo_risk,
            perspective_collapse_detected=collapse_detected,
            per_perspective=per_perspective,
            mean_prompt_similarity=round(mean_prompt_sim, 4),
            mean_pairwise_similarity=round(mean_pairwise, 4),
            collapse_pairs=collapse_pairs,
            summary=summary,
        )

    def check_single(self, prompt: str, output: str, name: str = "output") -> PerspectiveEchoResult:
        """Quick echo check for a single output (no collapse analysis)."""
        prompt_vec = _term_vec(prompt)
        out_vec = _term_vec(output)
        tokens = _tokenize(output)
        sim = _cosine(out_vec, prompt_vec)
        return PerspectiveEchoResult(
            name=name,
            similarity_to_prompt=sim,
            novelty_ratio=_novelty_ratio(output, prompt),
            token_count=len(tokens),
            is_echo=(sim > self.echo_threshold),
            is_too_short=(len(tokens) < self.min_token_count),
        )
