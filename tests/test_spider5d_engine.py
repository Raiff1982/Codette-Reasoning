"""Tests for the 5D Quantum Spyderweb constraint engine.

The engine once backtracked by calling `rotate_polarity_axis`, which rewrites
the clause set — so the search stopped solving the formula it was handed and
certified assignments against a mutated problem. On 300 random 3-SAT instances
that produced 109 unsound answers and 43 false UNSAT verdicts.

These tests pin the invariant that broke: whatever the substrate does to its
internal encoding, an answer is only an answer to the problem as posed.
"""

import itertools
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))

from spider5dengine.core import (
    PolarityRotationError,
    QuantumSpyderweb5D,
    self_sustaining_tensor_solver,
)


def satisfies(assignment, clauses):
    """Ground truth, deliberately independent of the engine's own verifier."""
    for clause in clauses:
        if not any(
            (assignment.get(lit[1:]) is False)
            if lit.startswith("~")
            else (assignment.get(lit) is True)
            for lit in clause
        ):
            return False
    return True


def brute_force(variables, clauses):
    for bits in itertools.product([False, True], repeat=len(variables)):
        candidate = dict(zip(variables, bits))
        if satisfies(candidate, clauses):
            return candidate
    return None


def random_3sat(rng, n_vars, n_clauses):
    variables = [f"x{i}" for i in range(n_vars)]
    clauses = [
        tuple(v if rng.random() < 0.5 else f"~{v}" for v in rng.sample(variables, 3))
        for _ in range(n_clauses)
    ]
    return variables, clauses


# --- Jonathan's three scenarios -------------------------------------------------

def test_cyclic_paradox_frustration():
    """Tight triangular loop of contradictions; C is unconstrained."""
    variables = ["A", "B", "C"]
    clauses = [("A", "B"), ("~A", "B"), ("A", "~B")]

    solution = self_sustaining_tensor_solver(QuantumSpyderweb5D(variables, clauses))

    assert solution is not None
    assert satisfies(solution, clauses)


def test_scaled_diamond_network():
    """Five-variable cross-dependent graph — degree heuristic under load."""
    variables = ["p1", "p2", "p3", "p4", "p5"]
    clauses = [
        ("p1", "p2"),
        ("~p1", "p3"),
        ("p2", "~p4"),
        ("p3", "p5"),
        ("~p4", "~p5"),
    ]

    solution = self_sustaining_tensor_solver(QuantumSpyderweb5D(variables, clauses))

    assert solution is not None
    assert satisfies(solution, clauses)


def test_unsolvable_vacuum_terminates():
    """Contradictory locks: must report UNSAT rather than loop or bluff."""
    variables = ["lock1", "lock2"]
    clauses = [("lock1",), ("~lock1",), ("lock2", "~lock2")]

    web = QuantumSpyderweb5D(variables, clauses)
    solution = self_sustaining_tensor_solver(web)

    assert solution is None
    assert web.metabolic_charge > 0


# --- The regression itself ------------------------------------------------------

def test_never_certifies_an_assignment_that_fails_the_posed_problem():
    """The bug: sound-looking answers verified against a mutated clause set."""
    rng = random.Random(20260730)
    unsound = incomplete = 0

    for _ in range(200):
        n_vars = rng.randint(3, 6)
        variables, clauses = random_3sat(rng, n_vars, rng.randint(3, int(n_vars * 4.5)))
        posed = [tuple(c) for c in clauses]

        solution = self_sustaining_tensor_solver(QuantumSpyderweb5D(variables, clauses))

        if solution is not None and not satisfies(solution, posed):
            unsound += 1
        elif solution is None and brute_force(variables, posed) is not None:
            incomplete += 1

    assert unsound == 0, f"{unsound} assignments failed the original CNF"
    assert incomplete == 0, f"{incomplete} satisfiable formulas reported UNSAT"


def test_search_does_not_mutate_the_posed_problem():
    variables = ["a", "b", "c"]
    clauses = [("a", "b"), ("~a", "c"), ("~b", "~c")]
    web = QuantumSpyderweb5D(variables, clauses)
    before = tuple(web.original_clauses)

    self_sustaining_tensor_solver(web)

    assert tuple(web.original_clauses) == before
    assert tuple(web.clauses) == before


# --- Rotation stays a legitimate operation, just not a backtracking move --------

def test_rotation_preserves_satisfiability_and_maps_back():
    """Flipping an axis is a real CNF symmetry — answers must land in the
    original encoding, not the rotated one."""
    variables = ["a", "b"]
    clauses = [("a", "b"), ("~a", "b")]

    web = QuantumSpyderweb5D(variables, clauses)
    web.rotate_polarity_axis("a")
    assert web.clauses != list(web.original_clauses)  # encoding really did change

    solution = self_sustaining_tensor_solver(web)

    assert solution is not None
    assert satisfies(solution, clauses)


def test_rotation_during_search_is_refused():
    """The failure mode is now impossible, not merely absent."""
    web = QuantumSpyderweb5D(["a"], [("a",)])
    web._search_active = True

    with pytest.raises(PolarityRotationError):
        web.rotate_polarity_axis("a")


def test_wavefunction_superposition_restored_on_backtrack():
    variables = ["a", "b"]
    clauses = [("a",), ("b",)]
    web = QuantumSpyderweb5D(variables, clauses)
    web.wavefunctions["a"] = 0.2  # bias toward the wrong branch first

    solution = self_sustaining_tensor_solver(web)

    assert solution == {"a": True, "b": True}
