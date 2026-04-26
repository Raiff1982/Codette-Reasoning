"""
Differentiable Ethics Potential Field — Ψ(f)

Replaces the discrete threshold/gate architecture across AEGIS, SycophancyGuard,
and GuardianSpindle with a smooth, mathematically well-founded potential field.

─────────────────────────────────────────────────────────────
THE PROBLEM WITH DISCRETE GATES
─────────────────────────────────────────────────────────────
Old code: `if score >= 0.6: block`
A score of 0.599 passes. A score of 0.601 fails. No gradient exists.
The system cannot "feel" which direction to push a borderline response.

─────────────────────────────────────────────────────────────
ETHICAL PENALTY FIELD  Ψ(f)
─────────────────────────────────────────────────────────────

Ψ is an ETHICAL PENALTY FIELD in the physics sense:

    Ψ(f) = ∑ₖ wₖ · σ(dₖ · αₖ · (fₖ − mₖ))

where:
    fₖ ∈ [0,1]    raw score for dimension k (from existing evaluators)
    wₖ > 0        importance weight  (normalized: ∑wₖ = 1)
    αₖ > 0        sharpness — high α recovers step function
    mₖ ∈ [0,1]    midpoint — the score at which the sigmoid is exactly 0.5
    dₖ ∈ {-1,+1}  direction:
                    dₖ = −1  → higher score = less penalty  (e.g. AEGIS alignment)
                    dₖ = +1  → higher score = more penalty  (e.g. sycophancy detection)
    σ(z)          logistic sigmoid  1/(1+e⁻ᶻ)

RANGE:   Ψ(f) ∈ (0, 1)  since each σ ∈ (0,1) and weights normalized.
PENALTY: Ψ = 0  →  no ethical concern (fully aligned / fully clean)
         Ψ = 1  →  maximum ethical concern (fully misaligned / maximally sycophantic)

ALIGNMENT SCORE (normalized):
    A(f) = 1 − Ψ(f)  ∈ (0, 1)
    A = 1: fully aligned.  A = 0: fully misaligned.

─────────────────────────────────────────────────────────────
GRADIENT & ETHICAL FORCE
─────────────────────────────────────────────────────────────

∂Ψ/∂fₖ = wₖ · dₖ · αₖ · σ'(dₖ · αₖ · (fₖ − mₖ))

where σ'(z) = σ(z)(1 − σ(z)) ≥ 0 always.

For AEGIS (dₖ = −1):
    ∂Ψ/∂fₖ = −wₖαₖσ'(...) < 0
    Increasing fₖ REDUCES Ψ (less penalty). ✓

For Sycophancy (dₖ = +1):
    ∂Ψ/∂fₖ = +wₖαₖσ'(...) > 0
    Increasing sycophancy score INCREASES Ψ (more penalty). ✓

The ETHICAL FORCE pushes each dimension toward improvement:
    F = −λ · ∇Ψ(f)     λ ∈ (0,1] controls intervention strength

For AEGIS:  Fₖ = +λwₖαₖσ'(...) > 0  →  push alignment scores upward ✓
For Syco:   Fₖ = −λwₖαₖσ'(...) < 0  →  push sycophancy scores downward ✓

Force magnitude peaks at fₖ ≈ mₖ (the transition zone) — maximum corrective
pressure exactly where it's most needed. At saturation (fₖ far from mₖ),
σ' → 0 and force decays, preventing runaway corrections.

─────────────────────────────────────────────────────────────
NATURAL GRADIENT (RIEMANNIAN)
─────────────────────────────────────────────────────────────

On the Riemannian manifold of ethical states with Fisher information metric G(f):

    G(f)ᵢⱼ = E[∂log p/∂fᵢ · ∂log p/∂fⱼ]

For independent dimensions, G is diagonal:
    G(f)ᵢᵢ = wᵢ² · αᵢ² · σ'(dᵢαᵢ(fᵢ−mᵢ))²

Natural gradient: (G⁻¹∇Ψ)ₖ = dₖ / (wₖ · αₖ · σ'(dₖαₖ(fₖ−mₖ)))

This is geometry-aware: near a transition zone (high σ'), the step is SMALL.
In a flat region (low σ', near saturation), the step is LARGE.

─────────────────────────────────────────────────────────────
BOLTZMANN SOFT GATE
─────────────────────────────────────────────────────────────

Replacing: `if score >= θ: block`
With:       P(block | score) = σ((score − θ) / τ)

    τ → 0:    step function at θ  (recovers hard threshold exactly)
    τ = 0.08: very sharp, near-hard but everywhere differentiable
    τ = 1.0:  gentle slope across [0,1]

─────────────────────────────────────────────────────────────
SOFT MULTI-ACTION (BOLTZMANN/SOFTMAX)
─────────────────────────────────────────────────────────────

Replacing: 4-state {block, revise, warn, pass} with hard if/elif
With:       P(aⱼ | score) = softmax([(score − θⱼ)/τ])

The expected severity: Ā = ∑ⱼ j · P(aⱼ|score) ∈ [0, 3] continuously.

─────────────────────────────────────────────────────────────
LYAPUNOV STABILITY OF EMA
─────────────────────────────────────────────────────────────

AEGIS EMA: η_{t+1} = α · ηᵢₙₛₜ + (1-α) · ηₜ

Lyapunov function V(η) = (η − η*)².
Since EMA is contractive: ‖η_{t+1} − η*‖ ≤ (1−α)‖ηₜ − η*‖ + α‖ηᵢₙₛₜ − η*‖

For unbiased ηᵢₙₛₜ: contraction rate = (1−α) = 0.7 per step (α=0.3). ✓

─────────────────────────────────────────────────────────────
L-SMOOTHNESS & CONVERGENCE BOUND
─────────────────────────────────────────────────────────────

Ψ is L-smooth with L = max_k (wₖ · αₖ² / 4)
(σ''(z) is bounded: |σ''(z)| ≤ σ'(z) ≤ 1/4, so |∂²Ψ/∂fₖ²| ≤ wₖαₖ²/4)

Step size bound for gradient descent convergence: η_step < 2/L
For default params (αₖ=10, wₖ≈0.2): L = 5, η_step < 0.4  ✓
"""

import math
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Tuple


# ================================================================
# Dimension Definition
# ================================================================

@dataclass
class EthicsDimension:
    """One axis of the ethical potential field.

    direction = -1: higher score → less penalty  (AEGIS ethical alignment)
    direction = +1: higher score → more penalty  (sycophancy, harm score)
    """
    name: str
    weight: float      # wₖ — importance weight (will be normalized)
    alpha: float       # αₖ — sigmoid sharpness
    midpoint: float    # mₖ — score value at which σ = 0.5 (the soft threshold)
    direction: int = -1  # dₖ: -1 (higher=better) or +1 (higher=worse)

    @property
    def transition_midpoint(self) -> float:
        return self.midpoint


# AEGIS: higher score = more ethically aligned = less penalty  → direction = -1
AEGIS_DIMENSIONS: List[EthicsDimension] = [
    # name                      weight  alpha  midpoint  direction
    EthicsDimension("utilitarian",            0.20,  10.0, 0.30, -1),
    EthicsDimension("deontological",          0.25,  12.0, 0.30, -1),   # stricter weight
    EthicsDimension("virtue",                 0.15,  10.0, 0.30, -1),
    EthicsDimension("care",                   0.15,  10.0, 0.30, -1),
    EthicsDimension("ubuntu",                 0.13,  10.0, 0.30, -1),
    EthicsDimension("indigenous_reciprocity", 0.12,  10.0, 0.30, -1),
]

# Sycophancy: higher score = more sycophantic = more penalty  → direction = +1
SYCOPHANCY_DIMENSIONS: List[EthicsDimension] = [
    # midpoint ≈ old block/warn thresholds
    EthicsDimension("flattery",     0.45,  10.0, 0.60, +1),
    EthicsDimension("capitulation", 0.55,  12.0, 0.30, +1),
]


# ================================================================
# Core Math
# ================================================================

def _sigmoid(z: float) -> float:
    """Numerically stable σ(z) = 1/(1+e⁻ᶻ)."""
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _sigmoid_prime(z: float) -> float:
    """σ'(z) = σ(z)(1−σ(z))."""
    s = _sigmoid(z)
    return s * (1.0 - s)


def _softmax(logits: List[float]) -> List[float]:
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    t = sum(exps)
    return [e / t for e in exps]


# ================================================================
# EthicsField
# ================================================================

class GradientResult(NamedTuple):
    penalty: float              # Ψ(f) ∈ (0, 1): 0=clean, 1=max concern
    alignment: float            # A(f) = 1 − Ψ ∈ (0, 1): 1=aligned, 0=not
    gradient: List[float]       # ∇Ψ — direction of steepest penalty increase
    force: List[float]          # F = −λ∇Ψ — direction of steepest improvement
    natural_gradient: List[float]   # G⁻¹∇Ψ — geometry-aware gradient
    dominant_dim: str           # dimension with largest |force| component
    dominant_force: float       # magnitude of force on dominant dimension


class EthicsField:
    """
    Differentiable ethical penalty field Ψ(f).

    Ψ(f) = ∑ₖ wₖ · σ(dₖ · αₖ · (fₖ − mₖ))

    Ψ = 0: no ethical concern.  Ψ = 1: maximum concern.
    A = 1 − Ψ: alignment score in (0, 1).
    F = −λ∇Ψ: ethical force (always pushes toward lower penalty).

    Usage:
        field = EthicsField(AEGIS_DIMENSIONS, lambda_=0.5)
        scores = [0.7, 0.8, 0.6, 0.9, 0.7, 0.8]
        result = field.evaluate(scores)
        print(result.alignment)       # ~0.97 — high alignment
        print(result.dominant_dim)    # which axis needs most attention
    """

    def __init__(self, dimensions: List[EthicsDimension], lambda_: float = 0.5):
        total_w = sum(d.weight for d in dimensions)
        self._dims = [
            EthicsDimension(d.name, d.weight / total_w, d.alpha, d.midpoint, d.direction)
            for d in dimensions
        ]
        self.lambda_ = lambda_
        # L-smoothness constant: L = max_k(wₖαₖ²/4)
        self._smoothness_L = max(d.weight * d.alpha ** 2 / 4.0 for d in self._dims)

    @property
    def max_stable_step(self) -> float:
        """η_step < 2/L guarantees L-smooth gradient descent convergence."""
        return 2.0 / self._smoothness_L

    def _z(self, dim: EthicsDimension, score: float) -> float:
        return dim.direction * dim.alpha * (score - dim.midpoint)

    def penalty(self, scores: List[float]) -> float:
        """
        Ψ(f) = ∑ₖ wₖ · σ(dₖ · αₖ · (fₖ − mₖ))

        Returns Ψ ∈ (0, 1).  Closer to 0 = more ethically aligned.
        """
        return sum(
            d.weight * _sigmoid(self._z(d, s))
            for d, s in zip(self._dims, scores)
        )

    def alignment(self, scores: List[float]) -> float:
        """
        A(f) = 1 − Ψ(f)  ∈ (0, 1)

        Drop-in replacement for AEGIS weighted average.
        Differentiable everywhere: no cliff edges.
        """
        return 1.0 - self.penalty(scores)

    def gradient(self, scores: List[float]) -> List[float]:
        """
        ∂Ψ/∂fₖ = wₖ · dₖ · αₖ · σ'(dₖαₖ(fₖ−mₖ))

        Negative for AEGIS dims (higher score → lower penalty → ∂Ψ/∂f < 0).
        Positive for sycophancy dims (higher score → higher penalty → ∂Ψ/∂f > 0).
        """
        return [
            d.weight * d.direction * d.alpha * _sigmoid_prime(self._z(d, s))
            for d, s in zip(self._dims, scores)
        ]

    def force(self, scores: List[float]) -> List[float]:
        """
        F = −λ · ∇Ψ(f)

        For AEGIS:  Fₖ > 0  →  increase alignment score ✓
        For Syco:   Fₖ < 0  →  decrease sycophancy score ✓

        Magnitude peaks at fₖ ≈ mₖ — maximum guidance at the transition zone.
        """
        g = self.gradient(scores)
        return [-self.lambda_ * gk for gk in g]

    def natural_gradient(self, scores: List[float]) -> List[float]:
        """
        Riemannian natural gradient (G(f)⁻¹ · ∇Ψ(f))ₖ

        G diagonal: G_kk = wₖ²αₖ²σ'(zₖ)²

        (G⁻¹∇Ψ)ₖ = dₖ / (wₖ · αₖ · σ'(zₖ) + ε)

        Small in steep regions (already high curvature — nudge gently).
        Large in flat regions (near saturation — push harder to move the needle).
        """
        result = []
        for d, s in zip(self._dims, scores):
            sp = _sigmoid_prime(self._z(d, s))
            result.append(d.direction / (d.weight * d.alpha * sp + 1e-8))
        return result

    def hessian_diagonal(self, scores: List[float]) -> List[float]:
        """
        ∂²Ψ/∂fₖ² = wₖ · αₖ² · σ''(dₖαₖ(fₖ−mₖ))

        where σ''(z) = σ'(z)(1 − 2σ(z))

        Eigenvalues of the diagonal Hessian = local curvature in each dimension.
        High |curvature| → small score changes have big Ψ impact.
        """
        result = []
        for d, s in zip(self._dims, scores):
            z = self._z(d, s)
            sp = _sigmoid_prime(z)
            sig = _sigmoid(z)
            sigma_double_prime = sp * (1.0 - 2.0 * sig)
            result.append(d.weight * d.alpha ** 2 * sigma_double_prime)
        return result

    def evaluate(self, scores: List[float]) -> GradientResult:
        """Full evaluation: penalty, alignment, force, natural gradient."""
        psi = self.penalty(scores)
        A = 1.0 - psi
        g = self.gradient(scores)
        f = [-self.lambda_ * gk for gk in g]
        ng = self.natural_gradient(scores)

        # Dominant dim = highest |force| component
        max_i = max(range(len(f)), key=lambda i: abs(f[i]))

        return GradientResult(
            penalty=round(psi, 6),
            alignment=round(A, 6),
            gradient=g,
            force=f,
            natural_gradient=ng,
            dominant_dim=self._dims[max_i].name,
            dominant_force=round(f[max_i], 6),
        )

    # ──────────────────────────────────────────────────────────────
    # Soft Gates
    # ──────────────────────────────────────────────────────────────

    def soft_gate(self, score: float, threshold: float,
                  temperature: float = 0.1) -> float:
        """
        Boltzmann soft gate: P(trigger | score) = σ((score − θ) / τ)

        Replaces `if score >= threshold: trigger` with a smooth probability.
        τ → 0 recovers the hard step. τ = 0.1 is near-hard but differentiable.
        """
        return _sigmoid((score - threshold) / temperature)

    def soft_action_distribution(
        self,
        score: float,
        thresholds: List[float] = None,
        temperature: float = 0.12,
    ) -> Dict[str, float]:
        """
        Ordinal logistic soft-action distribution.

        Replaces hard if/elif:
            if score >= 0.6: block
            elif score >= 0.3: revise
            elif score >= 0.1: warn
            else: pass

        Using the ordinal logistic model — each action wins in its natural range:

            P(block)  = σ((score − θ_block)  / τ)
            P(revise) = σ((score − θ_revise) / τ) − P(block)
            P(warn)   = σ((score − θ_warn)   / τ) − P(block) − P(revise)
            P(pass)   = 1 − P(block) − P(revise) − P(warn)

        Unlike a simple softmax, this correctly partitions [0,1] such that
        score = 0.599 and score = 0.601 differ smoothly across block/revise
        with no cliff edge.

        Expected severity Ā = 3·P(block) + 2·P(revise) + 1·P(warn) ∈ [0,3].
        """
        if thresholds is None:
            # [block_threshold, revise_threshold, warn_threshold] in descending order
            thresholds = [0.6, 0.3, 0.1]

        # Cumulative probabilities via sigmoid: P(action ≥ k) = σ((score − θₖ)/τ)
        cum = [_sigmoid((score - t) / temperature) for t in sorted(thresholds, reverse=True)]
        # cum[0] = P(block or worse) = P(block)
        # cum[1] = P(revise or worse) = P(block) + P(revise)
        # cum[2] = P(warn or worse)   = P(block) + P(revise) + P(warn)

        p_block  = cum[0]
        p_revise = max(0.0, cum[1] - cum[0])
        p_warn   = max(0.0, cum[2] - cum[1])
        p_pass   = max(0.0, 1.0 - cum[2])

        # Normalize for floating point safety
        total = p_block + p_revise + p_warn + p_pass
        probs = [p_block / total, p_revise / total, p_warn / total, p_pass / total]

        severity_weights = [3.0, 2.0, 1.0, 0.0]
        expected_severity = sum(p * w for p, w in zip(probs, severity_weights))

        actions = ["block", "revise", "warn", "pass"]
        result = {a: round(p, 4) for a, p in zip(actions, probs)}
        result["expected_severity"] = round(expected_severity, 4)
        result["action"] = actions[probs.index(max(probs))]
        return result

    def soft_veto(
        self,
        eta_instant: float,
        veto_threshold: float = 0.3,
        temperature: float = 0.08,
    ) -> Tuple[bool, float]:
        """
        Soft veto replacing: `vetoed = eta_instant < veto_threshold`

        P(veto | η) = σ((θ − η) / τ)  [inverted: low eta → high veto prob]

        Returns (should_veto: bool, veto_confidence: float).
        The bool is True when P(veto) > 0.5, with graded confidence.
        """
        p_veto = _sigmoid((veto_threshold - eta_instant) / temperature)
        return p_veto > 0.5, round(p_veto, 4)

    # ──────────────────────────────────────────────────────────────
    # EMA + stability
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def ema_update(current: float, instant: float, alpha: float = 0.3) -> float:
        """η_{t+1} = α·ηᵢₙₛₜ + (1−α)·ηₜ   Lyapunov-stable, contraction rate (1−α)."""
        return alpha * instant + (1.0 - alpha) * current

    @staticmethod
    def ema_convergence_steps(epsilon: float = 0.01, alpha: float = 0.3) -> int:
        """Minimum steps to guarantee |η − η*| < ε from worst-case start."""
        return math.ceil(math.log(epsilon) / math.log(1.0 - alpha))

    # ──────────────────────────────────────────────────────────────
    # Spectral / curvature analysis
    # ──────────────────────────────────────────────────────────────

    def spectral_summary(self, scores: List[float]) -> Dict:
        """
        Local curvature of the ethical landscape at the given score point.

        High |curvature| → near transition zone → small score changes matter a lot.
        Low |curvature| → near saturation → further pressure has diminishing returns.
        """
        hess = self.hessian_diagonal(scores)
        names = [d.name for d in self._dims]
        ranked = sorted(zip(names, hess, scores), key=lambda x: abs(x[1]), reverse=True)
        midpoints = {d.name: d.midpoint for d in self._dims}
        return {
            "curvatures": {name: round(h, 6) for name, h, _ in ranked},
            "most_active": ranked[0][0],
            "near_saturation": [
                name for name, h, _ in ranked if abs(h) < 0.01
            ],
            "in_transition_zone": [
                name for name, _, s in ranked
                if abs(s - midpoints[name]) < 0.15
            ],
        }

    def geodesic_step(
        self,
        scores: List[float],
        target: List[float],
        t: float,
    ) -> List[float]:
        """
        Linear geodesic interpolation γ(t) = (1−t)·f + t·f*,  t ∈ [0,1].

        Valid to first order on the Riemannian manifold (exact for Euclidean case).
        Use for gradual ethical steering between two score states.
        """
        if not (0.0 <= t <= 1.0):
            raise ValueError(f"t must be in [0,1], got {t}")
        return [(1.0 - t) * s + t * tgt for s, tgt in zip(scores, target)]


# ================================================================
# Convenience constructors
# ================================================================

def make_aegis_field(lambda_: float = 0.5) -> EthicsField:
    return EthicsField(AEGIS_DIMENSIONS, lambda_=lambda_)


def make_sycophancy_field(lambda_: float = 0.6) -> EthicsField:
    return EthicsField(SYCOPHANCY_DIMENSIONS, lambda_=lambda_)
