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

    raw = float(
        np.mean(incoming_evidence_vec)
        * alignment_weight
    )

    coherence_score = raw / (1.0 + abs(raw))

    return float(np.clip(coherence_score, -1.0, 1.0))


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
    2. Evaluate signed evidence coherence and reliability pressure.
    3. Calculate resistance, reinforcement, and projected displacement.
    4. Submit that exact projected displacement to AEGIS.
    5. Apply, block, or converge the belief-state update.
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
        """Evaluate reliability-scaled belief pressure and coherence."""

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

        evidence_score = evaluate_coherence(
            incoming_evidence_vec,
            contextual_constraints,
        )

        return {
            "value_shift": value_shift,
            "evidence_score": evidence_score,
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
    ):
        """
        Calculate the projected belief displacement, then submit that exact
        proposed state change to AEGIS.

        Since consolidation uses a unit evidence direction:

            abs(projected_belief_shift)
            ==
            L2 norm of the proposed belief-vector update
        """

        belief_centrality_score = _finite_float(
            belief_centrality_score,
            "belief_centrality_score",
        )

        identity_alignment_weight = _finite_float(
            identity_alignment_weight,
            "identity_alignment_weight",
        )

        epistemic_gain_score = _finite_float(
            epistemic_gain_score,
            "epistemic_gain_score",
        )

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

        resistance = float(
            belief_centrality_score
            * identity_alignment_weight
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
            )

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

            updated_belief_vec = (
                consolidation["updated_belief_vector"]
            )

            delta = l2_norm(
                updated_belief_vec
                - belief_vec
            )

            belief_vec = updated_belief_vec
            update_reason = consolidation["reason"]

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
            "iterations": iterations_run,
            "converged": converged,
            "termination_reason": termination_reason,
            "update_reason": update_reason,
            "resistance": override["resistance"],
            "reinforcement": override["reinforcement"],
            "net_scalar_shift": override["net_scalar_shift"],
            "projected_belief_shift": (
                override["projected_belief_shift"]
            ),
        }

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
