"""
Longitudinal Drift Detector
============================

Reads the accumulated LivingMemoryKernelV2 store and surfaces four categories
of drift that matter for RC+ξ continuity:

    1. Epsilon trend       — is epistemic tension rising, falling, or stable?
    2. Perspective lock    — is one perspective dominating at >LOCK_THRESHOLD?
    3. Recurring tensions  — which unresolved_tensions appear in 3+ cocoons?
    4. Hook accumulation   — how many follow-up hooks are piling up unresolved?

Designed for periodic reads (e.g., session start, /api/drift endpoint), not
for every inference call.  All computation is O(n) over the memory store.

Usage:
    detector = DriftDetector()
    report   = detector.detect(engine.memory_kernel)
    print(report.summary())
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

LOCK_THRESHOLD     = 0.60   # one perspective > 60% usage → perspective_lock
RECURRING_MIN      = 3      # tension must appear in ≥3 cocoons to be "recurring"
EPSILON_WINDOW     = 10     # number of recent cocoons for windowed epsilon
STABLE_BAND        = 0.05   # |slope| < this → "stable" trend


# ── Band encoding ────────────────────────────────────────────────────────────

_BAND_TO_FLOAT: Dict[str, float] = {
    "low": 0.2,
    "medium": 0.5,
    "high": 0.75,
    "max": 0.95,
}


def _band_value(band: str) -> float:
    return _BAND_TO_FLOAT.get(band.lower().strip(), 0.5)


# ── Linear regression (no numpy dependency) ──────────────────────────────────

def _slope(values: List[float]) -> float:
    """Return the least-squares slope of a list of scalars indexed 0..n-1."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


# ── Report ────────────────────────────────────────────────────────────────────

@dataclass
class DriftReport:
    """
    Snapshot of longitudinal drift in the memory store.

    All fields are read-only aggregates — nothing is written back to the kernel.
    """
    generated_at: float = field(default_factory=time.time)

    # Epsilon
    epsilon_trend: str = "unknown"          # "rising" | "falling" | "stable" | "unknown"
    epsilon_slope: float = 0.0              # raw slope over last EPSILON_WINDOW cocoons
    epsilon_mean: float = 0.0              # mean epsilon across all cocoons
    epsilon_distribution: Dict[str, int] = field(default_factory=dict)

    # Perspective
    dominant_perspective: str = ""
    perspective_usage: Dict[str, int] = field(default_factory=dict)
    perspective_lock: bool = False          # True if one perspective > LOCK_THRESHOLD
    perspective_lock_ratio: float = 0.0

    # Tensions
    recurring_tensions: List[Tuple[str, int]] = field(default_factory=list)
    # [(tension_label, cocoon_count), ...] sorted by count desc

    # Hooks
    open_hook_count: int = 0
    hooks_sample: List[str] = field(default_factory=list)  # up to 5 example hooks

    # Meta
    total_cocoons: int = 0
    observation_window: int = EPSILON_WINDOW

    def summary(self) -> str:
        """Human-readable one-paragraph summary."""
        lines = [
            f"Drift report over {self.total_cocoons} cocoons "
            f"(window={self.observation_window}):",
        ]

        lines.append(
            f"  ε trend: {self.epsilon_trend} "
            f"(slope={self.epsilon_slope:+.3f}, mean={self.epsilon_mean:.2f})"
        )

        if self.perspective_lock:
            lines.append(
                f"  ⚠ Perspective lock: '{self.dominant_perspective}' "
                f"at {self.perspective_lock_ratio:.0%} usage"
            )
        else:
            lines.append(
                f"  Perspective balance: dominant='{self.dominant_perspective}' "
                f"({self.perspective_lock_ratio:.0%})"
            )

        if self.recurring_tensions:
            top = self.recurring_tensions[:3]
            tension_str = ", ".join(f"'{t}' ×{n}" for t, n in top)
            lines.append(f"  Recurring tensions: {tension_str}")
        else:
            lines.append("  No recurring tensions detected.")

        lines.append(f"  Open hooks: {self.open_hook_count}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "epsilon_trend": self.epsilon_trend,
            "epsilon_slope": round(self.epsilon_slope, 4),
            "epsilon_mean": round(self.epsilon_mean, 4),
            "epsilon_distribution": self.epsilon_distribution,
            "dominant_perspective": self.dominant_perspective,
            "perspective_usage": self.perspective_usage,
            "perspective_lock": self.perspective_lock,
            "perspective_lock_ratio": round(self.perspective_lock_ratio, 4),
            "recurring_tensions": [
                {"tension": t, "count": n} for t, n in self.recurring_tensions
            ],
            "open_hook_count": self.open_hook_count,
            "hooks_sample": self.hooks_sample,
            "total_cocoons": self.total_cocoons,
            "observation_window": self.observation_window,
        }


# ── Detector ─────────────────────────────────────────────────────────────────

class DriftDetector:
    """
    Stateless analyser — call detect() as often as needed.

    Accepts any object that implements:
        .memories        → list of MemoryCocoonV2
        .continuity_profile() → dict (used for perspective_usage, epsilon_distribution,
                                       follow-up hooks, unresolved_tensions)
        .recall_with_hooks()  → list of MemoryCocoonV2 with open hooks
    Falls back gracefully if any of those attributes are absent.
    """

    def detect(self, kernel: Any) -> DriftReport:
        report = DriftReport()

        if kernel is None:
            return report

        # ── Pull raw data ─────────────────────────────────────────────────────
        memories = getattr(kernel, 'memories', [])
        report.total_cocoons = len(memories)

        # continuity_profile gives us the pre-aggregated view
        try:
            profile = kernel.continuity_profile()
        except Exception:
            profile = {}

        # ── Epsilon trend ─────────────────────────────────────────────────────
        epsilon_dist = profile.get("epsilon_distribution", {})
        report.epsilon_distribution = epsilon_dist

        # Windowed slope from recent cocoons (ordered by storage position)
        recent = memories[-EPSILON_WINDOW:] if len(memories) >= 2 else memories
        eps_values: List[float] = []
        for m in recent:
            band = getattr(m, 'epsilon_band', None)
            if band:
                eps_values.append(_band_value(band))

        if len(eps_values) >= 2:
            s = _slope(eps_values)
            report.epsilon_slope = s
            report.epsilon_mean = sum(eps_values) / len(eps_values)
            if s > STABLE_BAND:
                report.epsilon_trend = "rising"
            elif s < -STABLE_BAND:
                report.epsilon_trend = "falling"
            else:
                report.epsilon_trend = "stable"
        elif eps_values:
            report.epsilon_mean = eps_values[0]
            report.epsilon_trend = "stable"

        # ── Perspective dominance ─────────────────────────────────────────────
        perspective_usage: Dict[str, int] = profile.get("perspective_usage", {})
        report.perspective_usage = perspective_usage
        report.dominant_perspective = profile.get("dominant_perspective", "")

        total_perspective_uses = sum(perspective_usage.values())
        if total_perspective_uses > 0 and report.dominant_perspective:
            ratio = perspective_usage.get(report.dominant_perspective, 0) / total_perspective_uses
            report.perspective_lock_ratio = ratio
            report.perspective_lock = ratio > LOCK_THRESHOLD

        # ── Recurring tensions ────────────────────────────────────────────────
        tension_counter: Counter = Counter()
        for m in memories:
            tensions = getattr(m, 'unresolved_tensions', [])
            for t in tensions:
                t_clean = t.strip().lower()
                if t_clean:
                    tension_counter[t_clean] += 1

        report.recurring_tensions = [
            (t, n) for t, n in tension_counter.most_common()
            if n >= RECURRING_MIN
        ]

        # ── Open hooks ────────────────────────────────────────────────────────
        try:
            hooked = kernel.recall_with_hooks(limit=50)
        except Exception:
            hooked = [m for m in memories if getattr(m, 'follow_up_hooks', [])]

        all_hooks: List[str] = []
        for m in hooked:
            all_hooks.extend(getattr(m, 'follow_up_hooks', []))

        report.open_hook_count = len(all_hooks)
        seen: set = set()
        for h in all_hooks:
            if h not in seen:
                seen.add(h)
                report.hooks_sample.append(h)
                if len(report.hooks_sample) >= 5:
                    break

        return report
