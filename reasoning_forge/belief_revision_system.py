import copy
import unittest

import numpy as np


# ============================================================
# Architectural Infrastructure
# ============================================================

def module(name, version, layer, governance):
    """Decorator to register Codette cognitive modules and attach metadata."""

    def decorator(cls):
        cls._metadata = {
            "name": name,
            "version": version,
            "layer": layer,
            "governance": governance,
        }
        return cls

    return decorator


class AEGISGovernance:
    """Governance boundary for belief-state changes."""

    @staticmethod
    def check_core_axioms(proposed_belief_shift, core_axioms):
        """
        Determine whether a projected belief-state displacement remains
        within the configured governance boundary.

        Because evidence direction is unit-normalized during consolidation,
        abs(projected_belief_shift) equals the L2 norm of the proposed
        belief-vector update.
        """

        if core_axioms is None:
            raise ValueError("core_axioms cannot be None.")

        if not isinstance(core_axioms, dict):
            raise TypeError("core_axioms must be a dictionary.")

        max_allowed_shift = _nonnegative_float(
            core_axioms.get("max_shift_threshold", 2.0),
            "max_shift_threshold",
        )

        proposed_belief_shift = _finite_float(
            proposed_belief_shift,
            "proposed_belief_shift",
        )

        if abs(proposed_belief_shift) > max_allowed_shift:
            return "BLOCKED"

        return "PASSED"

    @staticmethod
    def check_total_drift(
        original_belief_vec,
        proposed_belief_vec,
        core_axioms,
    ):
        """
        Determine whether a proposed belief state remains within the total
        drift budget, measured from the belief as it stood before the run.

        check_core_axioms bounds a single step. On its own that leaves a gap:
        many small steps that each pass can add up to any displacement. On the
        authored test state, 20,000 steps moved a belief 133 units from where
        it started with every step PASSED. This check closes it.

        core_axioms["max_total_drift"]:
            absent -> defaults to max_shift_threshold, so a run cannot reach
                      by many small steps what a single step would be refused
            None   -> no budget; an explicit, visible opt-out
            number -> that budget
        """

        if not isinstance(core_axioms, dict):
            raise TypeError("core_axioms must be a dictionary.")

        original_belief_vec = _validated_vector(
            original_belief_vec,
            "original_belief_vec",
        )

        proposed_belief_vec = _validated_vector(
            proposed_belief_vec,
            "proposed_belief_vec",
        )

        if original_belief_vec.shape != proposed_belief_vec.shape:
            raise ValueError(
                "original_belief_vec and proposed_belief_vec "
                "must have identical shapes."
            )

        if "max_total_drift" in core_axioms:
            budget = core_axioms["max_total_drift"]

            if budget is None:
                return "PASSED"
        else:
            budget = core_axioms.get("max_shift_threshold", 2.0)

        budget = _nonnegative_float(budget, "max_total_drift")

        total_drift = l2_norm(
            proposed_belief_vec
            - original_belief_vec
        )

        if total_drift > budget:
            return "BLOCKED"

        return "PASSED"


AEGIS = AEGISGovernance()


class WorldModelStore:
    """Simple in-memory long-term belief store."""

    def __init__(self):
        self.store = {}

    def clear(self):
        """Clear persisted beliefs; primarily useful for test isolation."""
        self.store.clear()

    def store_belief(self, key, vector, metadata):
        """Commit a verified belief vector and isolated metadata copy."""

        if not isinstance(key, str) or not key.strip():
            raise ValueError("key must be a non-empty string.")

        vector = _validated_vector(vector, "vector")

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary.")

        self.store[key] = {
            "vector": vector.copy(),
            "metadata": copy.deepcopy(metadata),
        }


WorldModel = WorldModelStore()


# ============================================================
# Mathematical and Tensor Helpers
# ============================================================

def _validated_vector(vector, name):
    """Convert input into a non-empty finite floating-point NumPy array."""

    array = np.asarray(vector, dtype=float)

    if array.ndim == 0:
        raise ValueError(
            f"{name} must be an array-like vector, not a scalar."
        )

    if array.size == 0:
        raise ValueError(f"{name} cannot be empty.")

    if not np.all(np.isfinite(array)):
        raise ValueError(
            f"{name} must contain only finite numeric values."
        )

    return array


def _finite_float(value, name):
    """Convert a scalar to float and reject non-numeric, NaN, and infinity."""

    # bool is a subclass of int, so float(True) == 1.0 would pass silently.
    # _nonnegative_integer already guarded against this; every other scalar
    # entering the pipeline was not guarded, so the check belongs here.
    if isinstance(value, bool):
        raise ValueError(
            f"{name} must be a numeric value, not a boolean."
        )

    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a finite numeric value."
        ) from exc

    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    return value


def _nonnegative_float(value, name):
    """Convert input to a finite, non-negative float."""

    value = _finite_float(value, name)

    if value < 0.0:
        raise ValueError(
            f"{name} must be greater than or equal to zero."
        )

    return value


def _nonnegative_integer(value, name):
    """Validate and return a finite, non-negative integer."""

    # Kept ahead of _finite_float's own bool guard for the clearer message.
    if isinstance(value, bool):
        raise ValueError(
            f"{name} must be a non-negative integer, not a boolean."
        )

    numeric_value = _finite_float(value, name)

    if numeric_value < 0.0:
        raise ValueError(
            f"{name} must be greater than or equal to zero."
        )

    if not numeric_value.is_integer():
        raise ValueError(
            f"{name} must be an integer value."
        )

    return int(numeric_value)


def cosine_similarity(v1, v2):
    """Compute cosine similarity between equally shaped belief tensors."""

    v1 = _validated_vector(v1, "v1")
    v2 = _validated_vector(v2, "v2")

    if v1.shape != v2.shape:
        raise ValueError(
            "v1 and v2 must have identical shapes. "
            f"Received {v1.shape} and {v2.shape}."
        )

    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0

    similarity = float(
        np.dot(v1.ravel(), v2.ravel())
        / (norm_v1 * norm_v2)
    )

    return float(np.clip(similarity, -1.0, 1.0))


def l2_norm(vector):
    """Compute the Euclidean norm of a finite, non-empty tensor."""

    vector = _validated_vector(vector, "vector")

    return float(np.linalg.norm(vector))


def evaluate_coherence(incoming_evidence_vec, contextual_constraints):
    """
    Evaluate signed, saturating evidence coherence.

    Positive evidence produces positive coherence. Contradictory evidence
    remains negative rather than becoming positive through abs() folding.

    The signed mean alone cannot distinguish weak-but-agreeing evidence from
    strong-but-conflicting evidence: [0.2, 0.2, 0.2] and [1.0, -0.6, 0.2] both
    have a mean of 0.2. A directional-consistency factor,

        consistency = abs(sum(v)) / sum(abs(v))

    is 1.0 when every component agrees in sign and falls toward 0.0 as they
    disagree, so internally conflicted evidence yields proportionally weaker
    coherence instead of being averaged into apparent agreement.

    DIAGNOSTIC ONLY -- this score no longer steers the update. It is still
    computed and reported, but evidence_strength sets the step magnitude.

    Why: a signed mean depends on which way the axes point. Negate a belief
    and its supporting evidence together -- belief [-1,-1,-1], evidence
    [-0.2,-0.2,-0.2] -- and nothing about their relationship changes, yet this
    score flips sign, which flipped the step and pushed the belief away from
    evidence that agreed with it, while the mirrored positive case moved
    toward it. The consistency factor has the same fault in a milder form: it
    treats components of opposite sign as disagreeing, and zero-mean evidence
    such as [1, -1, 0] scores exactly 0 however strong it is. Belief-relative
    coherence was considered and rejected: contradicting evidence would score
    negative and push the belief away from it -- entrenchment rather than
    revision. The relationship to the belief is already carried, correctly,
    by detection_phase's error signal.
    """

    incoming_evidence_vec = _validated_vector(
        incoming_evidence_vec,
        "incoming_evidence_vec",
    )

    if contextual_constraints is None:
        contextual_constraints = {}

    if not isinstance(contextual_constraints, dict):
        raise TypeError(
            "contextual_constraints must be a dictionary or None."
        )

    alignment_weight = _finite_float(
        contextual_constraints.get("alignment_weight", 1.0),
        "alignment_weight",
    )

    absolute_total = float(
        np.sum(np.abs(incoming_evidence_vec))
    )

    if absolute_total == 0.0:
        return 0.0

    consistency = float(
        abs(np.sum(incoming_evidence_vec))
        / absolute_total
    )

    raw = float(
        np.mean(incoming_evidence_vec)
        * consistency
        * alignment_weight
    )

    coherence_score = raw / (1.0 + abs(raw))

    return float(np.clip(coherence_score, -1.0, 1.0))


def evidence_strength(incoming_evidence_vec, contextual_constraints):
    """
    Evaluate how strongly the evidence should move a belief, independent of
    which way the axes point.

        strength = alignment_weight * ||e|| / (1 + ||e||)

    Non-negative and saturating in [0, alignment_weight). It depends only on
    the evidence's length, which rotations and sign flips preserve, so the
    update is equivariant: transform the belief and the evidence together and
    the result is transformed the same way. Direction comes from the unit
    evidence vector in consolidation; whether to move toward or away comes
    from the sign of (value_shift + reinforcement - resistance), never from
    the sign of the evidence's components.

    alignment_weight must be non-negative: a negative weight would flip the
    step exactly as the signed mean did.
    """

    incoming_evidence_vec = _validated_vector(
        incoming_evidence_vec,
        "incoming_evidence_vec",
    )

    if contextual_constraints is None:
        contextual_constraints = {}

    if not isinstance(contextual_constraints, dict):
        raise TypeError(
            "contextual_constraints must be a dictionary or None."
        )

    alignment_weight = _nonnegative_float(
        contextual_constraints.get("alignment_weight", 1.0),
        "alignment_weight",
    )

    magnitude = float(np.linalg.norm(incoming_evidence_vec))

    return float(
        alignment_weight
        * magnitude
        / (1.0 + magnitude)
    )


# ============================================================
# Codette Belief Revision Module
# ============================================================

@module(
    name="BeliefRevisionSystem",
    version="2.3.1",
    layer="MetaCognitive.EpistemicRegulation",
    governance="AEGIS_Core_Integrity_Check",
)
class BeliefRevisionSystem:
    """
    Governed belief revision module.

    Pipeline:
        1. Detect directional alignment between current belief and evidence.
        2. Evaluate evidence strength and reliability pressure.
        3. Calculate resistance, reinforcement, and projected displacement.
        4. Submit that exact projected displacement to AEGIS.
        5. Submit the resulting total drift from the original belief to AEGIS.
        6. Apply, block, or converge the belief-state update.
    """

    EVIDENCE_NORM_EPSILON = 1e-9

    # --------------------------------------------------------
    # Detection
    # --------------------------------------------------------

    def detection_phase(
        self,
        current_belief_vec,
        incoming_evidence_vec,
    ):
        """Measure directional disagreement between belief and evidence."""

        similarity = cosine_similarity(
            current_belief_vec,
            incoming_evidence_vec,
        )

        error_signal = float(1.0 - similarity)

        return {
            "similarity": similarity,
            "error_signal": error_signal,
        }

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    def evaluation_phase(
        self,
        error_signal,
        historical_reliability_score,
        incoming_evidence_vec,
        contextual_constraints,
    ):
        """
        Evaluate reliability-scaled belief pressure and evidence strength.

        evidence_score is evidence_strength (non-negative). The signed
        coherence is still reported as evidence_coherence for inspection but
        does not enter the update; see evaluate_coherence for why.
        """

        error_signal = _finite_float(
            error_signal,
            "error_signal",
        )

        historical_reliability_score = _finite_float(
            historical_reliability_score,
            "historical_reliability_score",
        )

        value_shift = float(
            error_signal
            * historical_reliability_score
        )

        evidence_score = evidence_strength(
            incoming_evidence_vec,
            contextual_constraints,
        )

        evidence_coherence = evaluate_coherence(
            incoming_evidence_vec,
            contextual_constraints,
        )

        return {
            "value_shift": value_shift,
            "evidence_score": evidence_score,
            "evidence_coherence": evidence_coherence,
        }

    # --------------------------------------------------------
    # Override / Governance
    # --------------------------------------------------------

    def override_phase(
        self,
        belief_centrality_score,
        identity_alignment_weight,
        epistemic_gain_score,
        clarity_delta,
        evidence_score,
        value_shift,
        learning_rate,
        core_axioms,
        current_belief_norm=0.0,
    ):
        """
        Calculate the projected belief displacement, then submit that exact
        proposed state change to AEGIS.

        Since consolidation uses a unit evidence direction:

            abs(projected_belief_shift)
            ==
            L2 norm of the proposed belief-vector update

        Resistance scales with the belief's current magnitude:

            resistance = centrality * identity_alignment * (1 + ||belief||)

        Reinforcement is a constant input that does not decay as belief and
        evidence align, so with a magnitude-independent resistance the residual
        per-step shift settled at a fixed non-zero value and belief grew without
        bound: 400 iterations at tolerance 1e-12 still drifted 3.333e-04 per
        step and never converged. Scaling resistance by magnitude gives an
        equilibrium at

            ||belief|| = reinforcement / (centrality * identity_alignment) - 1

        while preserving the intended behaviour that supporting evidence
        strengthens an already-aligned belief. The (1 + ...) term keeps
        resistance non-zero for a zero-magnitude belief.
        """

        # These three must be non-negative. resistance is the product of the
        # first two, so a single negative value made resistance negative and the
        # term that is supposed to damp an update amplified it instead -- 13x the
        # baseline shift, and small enough in magnitude that governance passed
        # it. A negative epistemic_gain_score was silently absorbed by the
        # max(0, ...) below; rejecting it is clearer than ignoring it.
        #
        # No upper bound is imposed: governance already caught a runaway
        # epistemic_gain_score of 1e6, and an arbitrary ceiling here would
        # reject legitimate scales.
        belief_centrality_score = _nonnegative_float(
            belief_centrality_score,
            "belief_centrality_score",
        )

        identity_alignment_weight = _nonnegative_float(
            identity_alignment_weight,
            "identity_alignment_weight",
        )

        epistemic_gain_score = _nonnegative_float(
            epistemic_gain_score,
            "epistemic_gain_score",
        )

        # clarity_delta stays signed: it is a delta, and a clarity loss is
        # meaningful. The max(0, ...) below already floors its contribution.
        clarity_delta = _finite_float(
            clarity_delta,
            "clarity_delta",
        )

        evidence_score = _finite_float(
            evidence_score,
            "evidence_score",
        )

        value_shift = _finite_float(
            value_shift,
            "value_shift",
        )

        learning_rate = _nonnegative_float(
            learning_rate,
            "learning_rate",
        )

        current_belief_norm = _nonnegative_float(
            current_belief_norm,
            "current_belief_norm",
        )

        resistance = float(
            belief_centrality_score
            * identity_alignment_weight
            * (1.0 + current_belief_norm)
        )

        reinforcement = float(
            max(
                0.0,
                clarity_delta
                * epistemic_gain_score,
            )
        )

        net_scalar_shift = float(
            evidence_score
            * (
                value_shift
                + reinforcement
                - resistance
            )
        )

        projected_belief_shift = float(
            learning_rate
            * net_scalar_shift
        )

        governance_status = AEGIS.check_core_axioms(
            proposed_belief_shift=projected_belief_shift,
            core_axioms=core_axioms,
        )

        return {
            "resistance": resistance,
            "reinforcement": reinforcement,
            "net_scalar_shift": net_scalar_shift,
            "projected_belief_shift": projected_belief_shift,
            "governance_status": governance_status,
        }

    # --------------------------------------------------------
    # Consolidation
    # --------------------------------------------------------

    def consolidation_phase(
        self,
        current_belief_vec,
        incoming_evidence_vec,
        projected_belief_shift,
        governance_status,
    ):
        """
        Apply a governance-approved vector update.

        The projected scalar shift already includes learning rate,
        evidence coherence, reliability pressure, reinforcement,
        and resistance.
        """

        current_belief_vec = _validated_vector(
            current_belief_vec,
            "current_belief_vec",
        )

        incoming_evidence_vec = _validated_vector(
            incoming_evidence_vec,
            "incoming_evidence_vec",
        )

        if current_belief_vec.shape != incoming_evidence_vec.shape:
            raise ValueError(
                "current_belief_vec and incoming_evidence_vec "
                "must have identical shapes."
            )

        projected_belief_shift = _finite_float(
            projected_belief_shift,
            "projected_belief_shift",
        )

        if governance_status != "PASSED":
            return {
                "updated_belief_vector": current_belief_vec.copy(),
                "update_applied": False,
                "reason": "governance_blocked",
            }

        evidence_norm = l2_norm(incoming_evidence_vec)

        # Do not normalize numerical noise into a unit update direction.
        if evidence_norm < self.EVIDENCE_NORM_EPSILON:
            return {
                "updated_belief_vector": current_belief_vec.copy(),
                "update_applied": False,
                "reason": "negligible_evidence",
            }

        direction = incoming_evidence_vec / evidence_norm

        updated_belief_vec = (
            current_belief_vec
            + projected_belief_shift
            * direction
        )

        if not np.all(np.isfinite(updated_belief_vec)):
            raise FloatingPointError(
                "Belief revision produced NaN or infinity."
            )

        return {
            "updated_belief_vector": updated_belief_vec,
            "update_applied": True,
            "reason": "belief_updated",
        }

    # --------------------------------------------------------
    # Full Revision Cycle
    # --------------------------------------------------------

    def run(self, state, params):
        """Run a complete governed belief-revision cycle."""

        required_state = (
            "belief_key",
            "belief_vector",
            "incoming_evidence_vector",
            "historical_reliability_score",
            "contextual_constraints",
            "belief_centrality_score",
            "identity_alignment_weight",
            "epistemic_gain_score",
            "clarity_delta",
            "core_axioms",
        )

        required_params = (
            "max_iterations",
            "learning_rate",
            "tolerance_threshold",
        )

        if not isinstance(state, dict):
            raise TypeError("state must be a dictionary.")

        if not isinstance(params, dict):
            raise TypeError("params must be a dictionary.")

        missing_state = [
            key
            for key in required_state
            if key not in state
        ]

        if missing_state:
            raise KeyError(
                "Missing required state fields: "
                + ", ".join(missing_state)
            )

        missing_params = [
            key
            for key in required_params
            if key not in params
        ]

        if missing_params:
            raise KeyError(
                "Missing required parameter fields: "
                + ", ".join(missing_params)
            )

        belief_key = state["belief_key"]

        if not isinstance(belief_key, str) or not belief_key.strip():
            raise ValueError(
                "belief_key must be a non-empty string."
            )

        belief_vec = _validated_vector(
            state["belief_vector"],
            "belief_vector",
        ).copy()

        # Total drift is measured from here, not from the previous step.
        original_belief_vec = belief_vec.copy()

        evidence_vec = _validated_vector(
            state["incoming_evidence_vector"],
            "incoming_evidence_vector",
        )

        if belief_vec.shape != evidence_vec.shape:
            raise ValueError(
                "belief_vector and incoming_evidence_vector "
                "must have identical shapes."
            )

        max_iterations = _nonnegative_integer(
            params["max_iterations"],
            "max_iterations",
        )

        learning_rate = _nonnegative_float(
            params["learning_rate"],
            "learning_rate",
        )

        tolerance = _nonnegative_float(
            params["tolerance_threshold"],
            "tolerance_threshold",
        )

        override = {
            "governance_status": "NO_UPDATES",
            "resistance": 0.0,
            "reinforcement": 0.0,
            "net_scalar_shift": 0.0,
            "projected_belief_shift": 0.0,
        }

        delta = 0.0
        iterations_run = 0
        converged = False
        termination_reason = "no_iterations"
        update_reason = "no_update"
        update_applied = False
        governance_reason = "no_updates"

        for iteration in range(max_iterations):
            iterations_run = iteration + 1

            detection = self.detection_phase(
                current_belief_vec=belief_vec,
                incoming_evidence_vec=evidence_vec,
            )

            evaluation = self.evaluation_phase(
                error_signal=detection["error_signal"],
                historical_reliability_score=(
                    state["historical_reliability_score"]
                ),
                incoming_evidence_vec=evidence_vec,
                contextual_constraints=(
                    state["contextual_constraints"]
                ),
            )

            override = self.override_phase(
                belief_centrality_score=(
                    state["belief_centrality_score"]
                ),
                identity_alignment_weight=(
                    state["identity_alignment_weight"]
                ),
                epistemic_gain_score=(
                    state["epistemic_gain_score"]
                ),
                clarity_delta=state["clarity_delta"],
                evidence_score=evaluation["evidence_score"],
                value_shift=evaluation["value_shift"],
                learning_rate=learning_rate,
                core_axioms=state["core_axioms"],
                # Recomputed each iteration: resistance rises as the belief
                # grows, which is what makes the loop converge.
                current_belief_norm=l2_norm(belief_vec),
            )

            if override["governance_status"] == "BLOCKED":
                governance_reason = "step_threshold_exceeded"
            else:
                governance_reason = "within_bounds"

            consolidation = self.consolidation_phase(
                current_belief_vec=belief_vec,
                incoming_evidence_vec=evidence_vec,
                projected_belief_shift=(
                    override["projected_belief_shift"]
                ),
                governance_status=(
                    override["governance_status"]
                ),
            )

            # consolidation_phase is pure: it returns a proposed vector and
            # changes nothing, so the proposal can be judged against the total
            # drift budget before it is committed.
            if consolidation["update_applied"]:
                drift_status = AEGIS.check_total_drift(
                    original_belief_vec=original_belief_vec,
                    proposed_belief_vec=(
                        consolidation["updated_belief_vector"]
                    ),
                    core_axioms=state["core_axioms"],
                )

                if drift_status == "BLOCKED":
                    override["governance_status"] = "BLOCKED"
                    governance_reason = "drift_budget_exceeded"

                    consolidation = {
                        "updated_belief_vector": belief_vec.copy(),
                        "update_applied": False,
                        "reason": "governance_blocked",
                    }

            updated_belief_vec = (
                consolidation["updated_belief_vector"]
            )

            delta = l2_norm(
                updated_belief_vec
                - belief_vec
            )

            belief_vec = updated_belief_vec
            update_reason = consolidation["reason"]

            # consolidation_phase reports whether it actually moved the vector.
            # Only update_reason was being carried out of the loop, so a caller
            # had to infer application from the reason string. True if any
            # iteration applied an update, which is what "was this belief
            # revised?" means across a multi-step run.
            update_applied = (
                update_applied
                or consolidation["update_applied"]
            )

            # Governance denial is not a convergence event.
            if override["governance_status"] == "BLOCKED":
                termination_reason = "governance_blocked"
                break

            # A numerical no-op or sufficiently small update converges.
            if delta <= tolerance:
                converged = True
                termination_reason = "converged"
                break

        else:
            if max_iterations > 0:
                termination_reason = "max_iterations_reached"

        metadata = {
            "drift_rate": delta,
            "governance_status": override["governance_status"],
            "governance_reason": governance_reason,
            "total_drift": l2_norm(
                belief_vec
                - original_belief_vec
            ),
            "iterations": iterations_run,
            "converged": converged,
            "termination_reason": termination_reason,
            "update_reason": update_reason,
            "update_applied": update_applied,
            "resistance": override["resistance"],
            "reinforcement": override["reinforcement"],
            "net_scalar_shift": override["net_scalar_shift"],
            "projected_belief_shift": (
                override["projected_belief_shift"]
            ),
        }

        # Codette's answer, 2026-09-28, asked how an approval should be recorded
        # when the approved change is then not made: keep both entries. The
        # appraisal stands as given, marked conditional on the update being
        # applied, and the outcome follows it. Neither overwrites the other, so
        # "PASSED" can no longer be read as "changed".
        metadata["governance_record"] = [
            {
                "entry": "appraisal",
                "status": override["governance_status"],
                "reason": governance_reason,
                "conditional_on": "the update being applied",
            },
            {
                "entry": "outcome",
                "applied": update_applied,
                "reason": update_reason,
                "termination_reason": termination_reason,
            },
        ]

        WorldModel.store_belief(
            key=belief_key,
            vector=belief_vec,
            metadata=metadata,
        )

        return belief_vec.copy(), copy.deepcopy(metadata)


# ============================================================
# Unit Test Suite
# ============================================================

class TestBeliefRevisionSystem(unittest.TestCase):

    def setUp(self):
        WorldModel.clear()

        self.brs = BeliefRevisionSystem()

        self.base_state = {
            "belief_key": "test_axiom",
            "belief_vector": np.array(
                [1.0, 1.0, 1.0]
            ),
            "incoming_evidence_vector": np.array(
                [0.2, 0.2, 0.2]
            ),
            "historical_reliability_score": 0.8,
            "contextual_constraints": {
                "alignment_weight": 1.0,
            },
            "belief_centrality_score": 0.1,
            "identity_alignment_weight": 0.1,
            "epistemic_gain_score": 0.5,
            "clarity_delta": 0.1,
            "core_axioms": {
                "max_shift_threshold": 2.0,
            },
        }

    def test_governance_passing(self):
        """A standard projected update passes governance."""

        params = {
            "learning_rate": 0.05,
            "max_iterations": 5,
            "tolerance_threshold": 1e-4,
        }

        _, metadata = self.brs.run(
            self.base_state,
            params,
        )

        self.assertEqual(
            metadata["governance_status"],
            "PASSED",
        )

        self.assertGreater(
            metadata["iterations"],
            0,
        )

    def test_governance_blocks_projected_update(self):
        """A strict threshold blocks the actual projected update."""

        state = copy.deepcopy(self.base_state)

        state["core_axioms"] = {
            "max_shift_threshold": 1e-12,
        }

        params = {
            "learning_rate": 0.1,
            "max_iterations": 10,
            "tolerance_threshold": 1e-6,
        }

        final_vec, metadata = self.brs.run(
            state,
            params,
        )

        self.assertEqual(
            metadata["governance_status"],
            "BLOCKED",
        )

        self.assertFalse(
            metadata["converged"]
        )

        self.assertEqual(
            metadata["termination_reason"],
            "governance_blocked",
        )

        np.testing.assert_array_equal(
            final_vec,
            state["belief_vector"],
        )

    def test_zero_iterations(self):
        """Zero iterations produce no update and do not converge."""

        params = {
            "learning_rate": 0.05,
            "max_iterations": 0,
            "tolerance_threshold": 1e-4,
        }

        final_vec, metadata = self.brs.run(
            self.base_state,
            params,
        )

        self.assertEqual(
            metadata["governance_status"],
            "NO_UPDATES",
        )

        self.assertEqual(
            metadata["iterations"],
            0,
        )

        self.assertFalse(
            metadata["converged"]
        )

        self.assertEqual(
            metadata["termination_reason"],
            "no_iterations",
        )

        np.testing.assert_array_equal(
            final_vec,
            self.base_state["belief_vector"],
        )

    def test_update_directionality(self):
        """Supporting evidence moves belief in evidence direction."""

        params = {
            "learning_rate": 0.1,
            "max_iterations": 1,
            "tolerance_threshold": 1e-6,
        }

        final_vec, metadata = self.brs.run(
            self.base_state,
            params,
        )

        delta_vector = (
            final_vec
            - self.base_state["belief_vector"]
        )

        evidence_direction = self.base_state[
            "incoming_evidence_vector"
        ]

        self.assertEqual(
            metadata["governance_status"],
            "PASSED",
        )

        self.assertGreater(
            np.dot(delta_vector, evidence_direction),
            0.0,
        )

    def test_near_zero_evidence_converges_without_update(self):
        """Numerical noise creates no artificial update."""

        state = copy.deepcopy(self.base_state)

        state["incoming_evidence_vector"] = np.array(
            [1e-12, 1e-12, 1e-12]
        )

        params = {
            "learning_rate": 0.1,
            "max_iterations": 10,
            "tolerance_threshold": 1e-6,
        }

        final_vec, metadata = self.brs.run(
            state,
            params,
        )

        self.assertTrue(
            metadata["converged"]
        )

        self.assertEqual(
            metadata["iterations"],
            1,
        )

        self.assertEqual(
            metadata["update_reason"],
            "negligible_evidence",
        )

        self.assertEqual(
            metadata["termination_reason"],
            "converged",
        )

        np.testing.assert_array_equal(
            final_vec,
            state["belief_vector"],
        )

    def test_blocked_updates_never_converge(self):
        """A governance block must never be labeled convergence."""

        state = copy.deepcopy(self.base_state)

        state["core_axioms"] = {
            "max_shift_threshold": 0.0,
        }

        params = {
            "learning_rate": 1.0,
            "max_iterations": 10,
            "tolerance_threshold": 1e-6,
        }

        _, metadata = self.brs.run(
            state,
            params,
        )

        self.assertEqual(
            metadata["governance_status"],
            "BLOCKED",
        )

        self.assertFalse(
            metadata["converged"]
        )

        self.assertEqual(
            metadata["termination_reason"],
            "governance_blocked",
        )

    def test_negative_evidence_retains_signed_coherence(self):
        """Contradictory evidence remains negative."""

        score = evaluate_coherence(
            np.array([-1.0, -1.0, -1.0]),
            {"alignment_weight": 1.0},
        )

        self.assertLess(score, 0.0)

    def test_positive_and_negative_coherence_differ(self):
        """Supporting and contradictory coherence retain distinct polarity."""

        positive = evaluate_coherence(
            np.array([1.0, 1.0, 1.0]),
            {"alignment_weight": 1.0},
        )

        negative = evaluate_coherence(
            np.array([-1.0, -1.0, -1.0]),
            {"alignment_weight": 1.0},
        )

        self.assertGreater(positive, 0.0)
        self.assertLess(negative, 0.0)
        self.assertNotEqual(positive, negative)

    def test_shape_mismatch_is_rejected(self):
        """Belief and evidence tensors must share a shape."""

        state = copy.deepcopy(self.base_state)

        state["incoming_evidence_vector"] = np.array(
            [0.1, 0.1]
        )

        params = {
            "learning_rate": 0.1,
            "max_iterations": 1,
            "tolerance_threshold": 1e-6,
        }

        with self.assertRaises(ValueError):
            self.brs.run(state, params)

    def test_negative_governance_threshold_is_rejected(self):
        """A negative governance threshold is invalid."""

        state = copy.deepcopy(self.base_state)

        state["core_axioms"] = {
            "max_shift_threshold": -1.0,
        }

        params = {
            "learning_rate": 0.1,
            "max_iterations": 1,
            "tolerance_threshold": 1e-6,
        }

        with self.assertRaises(ValueError):
            self.brs.run(state, params)

    def test_non_integral_max_iterations_is_rejected(self):
        """Fractional iteration counts cannot be silently truncated."""

        params = {
            "learning_rate": 0.1,
            "max_iterations": 2.5,
            "tolerance_threshold": 1e-6,
        }

        with self.assertRaises(ValueError):
            self.brs.run(
                self.base_state,
                params,
            )

    def test_non_finite_vector_is_rejected(self):
        """NaN and infinity cannot enter the revision pipeline."""

        state = copy.deepcopy(self.base_state)

        state["incoming_evidence_vector"] = np.array(
            [0.1, np.nan, 0.1]
        )

        params = {
            "learning_rate": 0.1,
            "max_iterations": 1,
            "tolerance_threshold": 1e-6,
        }

        with self.assertRaises(ValueError):
            self.brs.run(state, params)

    def test_stored_metadata_is_deeply_isolated(self):
        """Stored metadata remains independent of returned metadata."""

        params = {
            "learning_rate": 0.1,
            "max_iterations": 1,
            "tolerance_threshold": 1e-6,
        }

        _, metadata = self.brs.run(
            self.base_state,
            params,
        )

        stored_metadata = WorldModel.store[
            self.base_state["belief_key"]
        ]["metadata"]

        self.assertEqual(
            stored_metadata,
            metadata,
        )

        metadata["nested"] = {
            "value": 1,
        }

        self.assertNotIn(
            "nested",
            stored_metadata,
        )


    # --------------------------------------------------------
    # Fix 1: reinforcement/resistance has a fixed point
    # --------------------------------------------------------

    def test_resistance_scales_with_belief_magnitude(self):
        """An established belief resists further growth."""

        kwargs = {
            "belief_centrality_score": 0.1,
            "identity_alignment_weight": 0.1,
            "epistemic_gain_score": 0.5,
            "clarity_delta": 0.1,
            "evidence_score": 0.5,
            "value_shift": 0.1,
            "learning_rate": 0.1,
            "core_axioms": {
                "max_shift_threshold": 2.0,
            },
        }

        weak = self.brs.override_phase(
            current_belief_norm=0.0,
            **kwargs
        )

        established = self.brs.override_phase(
            current_belief_norm=3.0,
            **kwargs
        )

        self.assertGreater(
            established["resistance"],
            weak["resistance"],
        )

        # resistance = centrality * identity * (1 + norm)
        self.assertAlmostEqual(
            established["resistance"],
            weak["resistance"] * 4.0,
            places=12,
        )

    def test_run_reaches_a_fixed_point(self):
        """Repeated reinforcement converges instead of growing forever."""

        # The path to equilibrium travels 2.27 from the start, past the default
        # drift budget of 2.0. This test is about the fixed point, not the
        # budget, so the budget is opted out of explicitly.
        state = dict(self.base_state)
        state["core_axioms"] = {
            "max_shift_threshold": 2.0,
            "max_total_drift": None,
        }

        params = {
            "learning_rate": 1.0,
            "max_iterations": 200000,
            "tolerance_threshold": 1e-9,
        }

        final_vec, metadata = self.brs.run(
            state,
            params,
        )

        self.assertTrue(metadata["converged"])

        self.assertEqual(
            metadata["termination_reason"],
            "converged",
        )

        # Equilibrium is where reinforcement == resistance:
        #     reinforcement = centrality * identity * (1 + norm)
        #     norm = reinforcement / (centrality * identity) - 1
        #          = 0.05 / 0.01 - 1
        #          = 4.0
        #
        # The approach is asymptotic and tolerance_threshold bounds the step
        # size, not the remaining distance, so the run stops just short of the
        # fixed point. Measured residual here is 6.0e-07.
        self.assertAlmostEqual(
            l2_norm(final_vec),
            4.0,
            places=5,
        )

    def test_belief_above_equilibrium_is_pulled_back(self):
        """The fixed point attracts from above, not only from below."""

        state = dict(self.base_state)
        state["belief_vector"] = np.array(
            [6.0, 6.0, 6.0]
        )

        # Opted out for the same reason as test_run_reaches_a_fixed_point.
        state["core_axioms"] = {
            "max_shift_threshold": 2.0,
            "max_total_drift": None,
        }

        params = {
            "learning_rate": 1.0,
            "max_iterations": 200000,
            "tolerance_threshold": 1e-9,
        }

        final_vec, _ = self.brs.run(state, params)

        self.assertLess(
            l2_norm(final_vec),
            l2_norm(state["belief_vector"]),
        )

        self.assertAlmostEqual(
            l2_norm(final_vec),
            4.0,
            places=2,
        )

    # --------------------------------------------------------
    # Fix 2: coherence accounts for directional consistency
    # --------------------------------------------------------

    def test_conflicted_evidence_scores_below_agreeing(self):
        """Equal-mean evidence scores lower when internally conflicted."""

        constraints = {
            "alignment_weight": 1.0,
        }

        # Both vectors have mean 0.2.
        agreeing = evaluate_coherence(
            np.array([0.2, 0.2, 0.2]),
            constraints,
        )

        conflicted = evaluate_coherence(
            np.array([1.0, -0.6, 0.2]),
            constraints,
        )

        self.assertGreater(agreeing, conflicted)
        self.assertGreater(conflicted, 0.0)

    def test_sign_agreeing_coherence_is_unchanged(self):
        """The consistency factor is exactly 1.0 when signs agree."""

        score = evaluate_coherence(
            np.array([0.2, 0.2, 0.2]),
            {"alignment_weight": 1.0},
        )

        # raw = mean * 1.0 * 1.0 = 0.2, saturated to 0.2 / 1.2.
        self.assertAlmostEqual(
            score,
            0.2 / 1.2,
            places=12,
        )

    def test_fully_cancelling_evidence_is_zero_coherence(self):
        """Evidence that sums to zero carries no coherent signal."""

        score = evaluate_coherence(
            np.array([0.5, -0.5]),
            {"alignment_weight": 1.0},
        )

        self.assertEqual(score, 0.0)

    # --------------------------------------------------------
    # Fix 3: scalars that must not invert resistance
    # --------------------------------------------------------

    def test_negative_scores_are_rejected(self):
        """A negative centrality would amplify rather than damp an update."""

        for field in (
            "belief_centrality_score",
            "identity_alignment_weight",
            "epistemic_gain_score",
        ):
            with self.subTest(field=field):
                state = dict(self.base_state)
                state[field] = -5.0

                with self.assertRaises(ValueError):
                    self.brs.run(
                        state,
                        {
                            "learning_rate": 0.1,
                            "max_iterations": 1,
                            "tolerance_threshold": 1e-6,
                        },
                    )

    def test_negative_clarity_delta_is_accepted(self):
        """clarity_delta is a signed delta; a clarity loss is meaningful."""

        state = dict(self.base_state)
        state["clarity_delta"] = -0.5

        _, metadata = self.brs.run(
            state,
            {
                "learning_rate": 0.1,
                "max_iterations": 1,
                "tolerance_threshold": 1e-6,
            },
        )

        self.assertIn(
            metadata["governance_status"],
            ("PASSED", "BLOCKED"),
        )

    # --------------------------------------------------------
    # Fix 4: booleans rejected, update_applied reported
    # --------------------------------------------------------

    def test_boolean_scalars_are_rejected(self):
        """float(True) == 1.0 must not pass as a score."""

        with self.assertRaises(ValueError):
            _finite_float(True, "probe")

        with self.assertRaises(ValueError):
            _nonnegative_float(False, "probe")

        state = dict(self.base_state)
        state["historical_reliability_score"] = True

        with self.assertRaises(ValueError):
            self.brs.run(
                state,
                {
                    "learning_rate": 0.1,
                    "max_iterations": 1,
                    "tolerance_threshold": 1e-6,
                },
            )

    def test_run_reports_whether_an_update_was_applied(self):
        """update_applied crosses the phase boundary into metadata."""

        params = {
            "learning_rate": 0.1,
            "max_iterations": 1,
            "tolerance_threshold": 1e-6,
        }

        _, applied = self.brs.run(
            self.base_state,
            params,
        )

        self.assertTrue(applied["update_applied"])

        # Negligible evidence gives consolidation nothing to apply.
        WorldModel.clear()

        state = dict(self.base_state)
        state["incoming_evidence_vector"] = np.array(
            [1e-15, 1e-15, 1e-15]
        )

        _, skipped = self.brs.run(state, params)

        self.assertFalse(skipped["update_applied"])



    # --------------------------------------------------------
    # Equivariance: the update does not depend on which way the
    # axes point
    # --------------------------------------------------------

    def _run_steps(self, belief, evidence, iterations=50):
        state = dict(self.base_state)
        state["belief_vector"] = np.asarray(belief, dtype=float)
        state["incoming_evidence_vector"] = np.asarray(
            evidence,
            dtype=float,
        )

        WorldModel.clear()

        return self.brs.run(
            state,
            {
                "learning_rate": 0.1,
                "max_iterations": iterations,
                "tolerance_threshold": 1e-12,
            },
        )

    def test_mirrored_belief_moves_toward_supporting_evidence(self):
        """Negating belief and evidence together negates the result."""

        belief = np.array([1.0, 1.0, 1.0])
        evidence = np.array([0.2, 0.2, 0.2])

        positive, _ = self._run_steps(belief, evidence)
        negative, _ = self._run_steps(-belief, -evidence)

        # Before this fix the mirrored belief moved AWAY from evidence that
        # agreed with it, because the step's sign came from the sign of the
        # evidence's mean.
        self.assertGreater(
            np.dot(negative - (-belief), -evidence),
            0.0,
        )

        np.testing.assert_allclose(
            negative,
            -positive,
            rtol=0.0,
            atol=1e-12,
        )

    def test_update_is_rotation_equivariant(self):
        """Rotating belief and evidence together rotates the result."""

        rng = np.random.default_rng(20260928)
        rotation, _ = np.linalg.qr(
            rng.normal(size=(3, 3))
        )

        belief = np.array([1.0, 0.5, -0.25])
        evidence = np.array([0.3, -0.1, 0.2])

        original, _ = self._run_steps(belief, evidence)
        rotated, _ = self._run_steps(
            rotation @ belief,
            rotation @ evidence,
        )

        np.testing.assert_allclose(
            rotated,
            rotation @ original,
            rtol=0.0,
            atol=1e-10,
        )

    def test_zero_mean_evidence_still_moves_belief(self):
        """[1, -1, 0] is strong evidence even though its mean is 0."""

        belief = np.array([1.0, 0.0, 0.0])
        evidence = np.array([1.0, -1.0, 0.0])

        final_vec, metadata = self._run_steps(
            belief,
            evidence,
            iterations=1,
        )

        self.assertTrue(metadata["update_applied"])

        self.assertGreater(
            np.dot(final_vec - belief, evidence),
            0.0,
        )

    def test_contradicting_evidence_moves_belief_toward_it(self):
        """Revision, not entrenchment."""

        belief = np.array([1.0, 1.0, 1.0])
        evidence = np.array([-0.2, -0.2, -0.2])

        final_vec, metadata = self._run_steps(
            belief,
            evidence,
            iterations=1,
        )

        self.assertTrue(metadata["update_applied"])

        self.assertGreater(
            np.dot(final_vec - belief, evidence),
            0.0,
        )

    def test_evidence_strength_is_non_negative(self):
        """Strength depends on length only, and a negative weight is refused."""

        for vector in (
            [0.2, 0.2, 0.2],
            [-0.2, -0.2, -0.2],
            [1.0, -1.0, 0.0],
        ):
            with self.subTest(vector=vector):
                self.assertGreater(
                    evidence_strength(
                        np.array(vector),
                        {"alignment_weight": 1.0},
                    ),
                    0.0,
                )

        self.assertEqual(
            evidence_strength(
                np.array([0.2, 0.2, 0.2]),
                {"alignment_weight": 1.0},
            ),
            evidence_strength(
                np.array([-0.2, -0.2, -0.2]),
                {"alignment_weight": 1.0},
            ),
        )

        with self.assertRaises(ValueError):
            evidence_strength(
                np.array([0.2, 0.2, 0.2]),
                {"alignment_weight": -1.0},
            )

    # --------------------------------------------------------
    # Cumulative drift budget
    # --------------------------------------------------------

    def test_many_small_steps_cannot_exceed_drift_budget(self):
        """Each step passing does not let the total pass."""

        state = dict(self.base_state)
        state["core_axioms"] = {
            "max_shift_threshold": 2.0,
            "max_total_drift": 0.5,
        }

        final_vec, metadata = self.brs.run(
            state,
            {
                "learning_rate": 1.0,
                "max_iterations": 100000,
                "tolerance_threshold": 1e-12,
            },
        )

        self.assertEqual(metadata["governance_status"], "BLOCKED")

        self.assertEqual(
            metadata["governance_reason"],
            "drift_budget_exceeded",
        )

        self.assertEqual(
            metadata["termination_reason"],
            "governance_blocked",
        )

        self.assertFalse(metadata["converged"])

        self.assertLessEqual(metadata["total_drift"], 0.5)

        self.assertAlmostEqual(
            metadata["total_drift"],
            l2_norm(final_vec - state["belief_vector"]),
            places=12,
        )

        # Every step was individually far inside the per-step threshold.
        self.assertLess(
            abs(metadata["projected_belief_shift"]),
            2.0,
        )

    def test_default_drift_budget_is_the_step_threshold(self):
        """Absent a budget, total drift may not exceed one allowed step."""

        state = dict(self.base_state)
        state["core_axioms"] = {
            "max_shift_threshold": 1.0,
        }

        _, metadata = self.brs.run(
            state,
            {
                "learning_rate": 1.0,
                "max_iterations": 100000,
                "tolerance_threshold": 1e-12,
            },
        )

        self.assertEqual(
            metadata["governance_reason"],
            "drift_budget_exceeded",
        )

        self.assertLessEqual(metadata["total_drift"], 1.0)

    def test_per_step_block_is_reported_as_such(self):
        """The two gates report which one refused."""

        state = dict(self.base_state)
        state["core_axioms"] = {
            "max_shift_threshold": 0.0,
        }

        _, metadata = self.brs.run(
            state,
            {
                "learning_rate": 0.1,
                "max_iterations": 5,
                "tolerance_threshold": 1e-12,
            },
        )

        self.assertEqual(
            metadata["governance_reason"],
            "step_threshold_exceeded",
        )

        self.assertEqual(metadata["total_drift"], 0.0)

    def test_governance_blocking(self):
        """An extreme threshold blocks the update."""

        state = self.base_state.copy()

        state["core_axioms"] = {
            "max_shift_threshold": 0.0001
        }

        params = {
            "learning_rate": 0.5,
            "max_iterations": 5,
            "tolerance_threshold": 1e-4,
        }

        _, metadata = self.brs.run(
            state,
            params,
        )

        self.assertEqual(
            metadata["governance_status"],
            "BLOCKED",
        )

        stored_vec = WorldModel.store[
            state["belief_key"]
        ]["vector"]

        np.testing.assert_array_equal(
            stored_vec,
            state["belief_vector"],
        )

    def test_metadata_is_stored_with_belief(self):
        """Stored belief state includes a separate metadata copy."""

        params = {
            "learning_rate": 0.1,
            "max_iterations": 1,
            "tolerance_threshold": 1e-6,
        }

        final_vec, metadata = self.brs.run(
            self.base_state,
            params,
        )

        stored_record = WorldModel.store[
            self.base_state["belief_key"]
        ]

        np.testing.assert_array_equal(
            stored_record["vector"],
            final_vec,
        )

        self.assertEqual(
            stored_record["metadata"],
            metadata,
        )

        self.assertIsNot(
            stored_record["metadata"],
            metadata,
        )

    def _record(self, state):
        _, metadata = self.brs.run(
            state,
            {
                "learning_rate": 0.1,
                "max_iterations": 5,
                "tolerance_threshold": 1e-6,
            },
        )
        return metadata, metadata["governance_record"]

    def test_approval_of_an_unmade_change_records_the_outcome(self):
        """PASSED on negligible evidence is followed by 'not applied'."""

        state = dict(self.base_state)
        state["incoming_evidence_vector"] = np.array(
            [1e-12, 1e-12, 1e-12]
        )

        metadata, (appraisal, outcome) = self._record(state)

        self.assertEqual(metadata["governance_status"], "PASSED")
        self.assertEqual(appraisal["entry"], "appraisal")
        self.assertEqual(appraisal["status"], "PASSED")
        self.assertEqual(
            appraisal["conditional_on"],
            "the update being applied",
        )
        self.assertEqual(outcome["entry"], "outcome")
        self.assertFalse(outcome["applied"])
        self.assertEqual(outcome["reason"], "negligible_evidence")

    def test_applied_change_records_both_entries(self):
        """An approval that is carried out says so in its outcome."""

        metadata, (appraisal, outcome) = self._record(
            dict(self.base_state)
        )

        self.assertEqual(appraisal["status"], "PASSED")
        self.assertTrue(outcome["applied"])
        self.assertEqual(outcome["reason"], "belief_updated")
        self.assertTrue(metadata["update_applied"])

    def test_blocked_change_records_both_entries(self):
        """A refusal is an appraisal too, and its outcome follows it."""

        state = dict(self.base_state)
        state["core_axioms"] = {
            "max_shift_threshold": 0.0,
        }

        _, (appraisal, outcome) = self._record(state)

        self.assertEqual(appraisal["status"], "BLOCKED")
        self.assertEqual(
            appraisal["reason"],
            "step_threshold_exceeded",
        )
        self.assertFalse(outcome["applied"])
        self.assertEqual(outcome["reason"], "governance_blocked")

    def test_governance_record_is_stored_with_the_belief(self):
        """Both entries reach the WorldModel, not only the caller."""

        state = dict(self.base_state)
        state["incoming_evidence_vector"] = np.array(
            [1e-12, 1e-12, 1e-12]
        )

        _, record = self._record(state)

        stored = WorldModel.store[
            state["belief_key"]
        ]["metadata"]["governance_record"]

        self.assertEqual(stored, record)
        self.assertEqual(len(stored), 2)



if __name__ == "__main__":
    print(
        "--- Executing Codette "
        "BeliefRevisionSystem Complete Test Suite ---"
    )

    unittest.main(
        argv=[""],
        exit=False,
        verbosity=2,
    )
