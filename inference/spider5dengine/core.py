"""5D Quantum Spyderweb — a self-perpetuating tensor substrate for CNF constraints.

Polarity rotation is a genuine symmetry of CNF: flipping every occurrence of a
variable yields an equisatisfiable formula. It is not, however, a backtracking
move. A decision made under one encoding cannot be read under another, so
rotation belongs *between* searches, not inside one. The substrate keeps the
problem as posed in `original_clauses` and resolves every verification there.
"""


class PolarityRotationError(RuntimeError):
    """Raised when the polarity axis is rotated while a search is in flight."""


class QuantumSpyderweb5D:
    def __init__(self, variables, clauses):
        self.variables = list(variables)
        self.clauses = [tuple(clause) for clause in clauses]
        # The problem as posed. Never mutated — every verification resolves here.
        self.original_clauses = tuple(self.clauses)
        self.edges = []
        self.degrees = {v: 0 for v in self.variables}
        self.polarities = {v: True for v in self.variables}
        self.wavefunctions = {v: 0.5 for v in self.variables}
        self.metabolic_charge = 1.0  # Initial seed energy
        self._search_active = False
        self._build_5d_substrate()

    def _build_5d_substrate(self):
        self.edges = []
        self.degrees = {v: 0 for v in self.variables}
        # Which clauses each axis touches — the channels a collapse disperses
        # along. Without this, propagation would have to sweep every clause.
        self.clause_index = {v: [] for v in self.variables}
        for clause_idx, clause in enumerate(self.clauses):
            clause_vars = []
            for literal in clause:
                var = literal[1:] if literal.startswith('~') else literal
                clause_vars.append((var, literal.startswith('~')))
                if var in self.degrees:
                    self.degrees[var] += 1
                    if clause_idx not in self.clause_index[var]:
                        self.clause_index[var].append(clause_idx)

            for i in range(len(clause_vars)):
                for j in range(i + 1, len(clause_vars)):
                    v1, _ = clause_vars[i]
                    v2, _ = clause_vars[j]
                    self.edges.append({
                        'vars': (v1, v2),
                        'clause_id': clause_idx
                    })

    def self_perpetuating_breath(self):
        """Harvests ambient computational friction to recharge kinetic charge."""
        total_tension = sum(self.degrees.values())
        harvested_energy = total_tension * 0.05

        self.metabolic_charge += harvested_energy

        for var in self.variables:
            if self.wavefunctions[var] not in [0.0, 1.0]:
                self.wavefunctions[var] = 0.5 + (self.wavefunctions[var] - 0.5) * 0.95

    def rotate_polarity_axis(self, target_var):
        """The Swimmer's Wall Reflection: re-encode the substrate about one axis.

        Flipping every occurrence of `target_var` produces an equisatisfiable
        formula, so this is safe between searches. Mid-search it is not: any
        variable already decided was decided under the previous encoding, and
        its recorded value silently changes meaning underneath the search.
        """
        if self._search_active:
            raise PolarityRotationError(
                "rotate_polarity_axis() cannot run during a search: decisions "
                "already made refer to the previous encoding. Rotate before "
                "solving, or start a fresh search afterwards."
            )

        self.metabolic_charge -= 0.1
        self.metabolic_charge += 0.25

        new_clauses = []
        for clause in self.clauses:
            new_clause = []
            for literal in clause:
                negated = literal.startswith('~')
                var = literal[1:] if negated else literal
                if var == target_var:
                    new_literal = var if negated else f"~{var}"
                    new_clause.append(new_literal)
                else:
                    new_clause.append(literal)
            new_clauses.append(tuple(new_clause))
        self.clauses = new_clauses
        self.polarities[target_var] = not self.polarities[target_var]
        self._build_5d_substrate()

    def to_original_assignment(self, assignment: dict) -> dict:
        """Translate an assignment in the current encoding back to the posed one."""
        return {
            var: (val if self.polarities.get(var, True) else not val)
            for var, val in assignment.items()
        }

    def verify_full_assignment(self, assignment: dict) -> bool:
        """Check an assignment against the problem as posed, whatever the encoding."""
        resolved = self.to_original_assignment(assignment)
        for clause in self.original_clauses:
            clause_satisfied = False
            for literal in clause:
                negated = literal.startswith('~')
                var = literal[1:] if negated else literal
                if var in resolved and bool(resolved[var]) != negated:
                    clause_satisfied = True
                    break
            if not clause_satisfied:
                return False
        return True


def self_sustaining_tensor_solver(spyderweb: QuantumSpyderweb5D, assignment=None, depth=0):
    """Traverses the tensor using self-perpetuating energetic feedback loops.

    Returns a satisfying assignment in the problem's original encoding — any
    rotation applied before the search is undone on the way out — or None if
    the formula is unsatisfiable.
    """
    spyderweb._search_active = True
    try:
        solution = _collapse_axis(spyderweb, dict(assignment or {}), depth)
    finally:
        spyderweb._search_active = False

    return spyderweb.to_original_assignment(solution) if solution is not None else None


def _split_literal(literal):
    negated = literal.startswith('~')
    return (literal[1:] if negated else literal), negated


def _disperse(spyderweb: QuantumSpyderweb5D, assignment, frontier):
    """The wave that follows a collapse.

    A collapsed axis sends its consequence along every clause it touches. A
    clause left with a single live literal has no freedom remaining, so that
    literal collapses too, and its own wave disperses onward. Propagation runs
    to stillness or to contradiction.

    Returns False on contradiction. Mutates `assignment` in place with every
    forced value, so the caller must pass a copy it owns.
    """
    while frontier:
        var = frontier.pop()
        for clause_idx in spyderweb.clause_index.get(var, ()):
            clause = spyderweb.clauses[clause_idx]

            satisfied = False
            free_literal = None
            free_count = 0

            for literal in clause:
                lit_var, negated = _split_literal(literal)
                if lit_var in assignment:
                    if bool(assignment[lit_var]) != negated:
                        satisfied = True
                        break
                else:
                    free_count += 1
                    free_literal = (lit_var, negated)

            if satisfied:
                continue
            if free_count == 0:
                return False                      # every literal dead — contradiction
            if free_count == 1:
                lit_var, negated = free_literal
                assignment[lit_var] = not negated  # forced
                spyderweb.wavefunctions[lit_var] = 0.0 if negated else 1.0
                frontier.append(lit_var)

    return True


def _collapse_axis(spyderweb: QuantumSpyderweb5D, assignment, depth):
    spyderweb.self_perpetuating_breath()

    unassigned_vars = [v for v in spyderweb.variables if v not in assignment]

    if not unassigned_vars:
        return assignment if spyderweb.verify_full_assignment(assignment) else None

    var = max(unassigned_vars, key=lambda v: spyderweb.degrees[v])

    bias = spyderweb.wavefunctions[var]
    preferred_val = bias >= 0.5
    prior_wavefunction = spyderweb.wavefunctions[var]

    for val in (preferred_val, not preferred_val):
        next_assignment = assignment.copy()
        next_assignment[var] = val
        spyderweb.wavefunctions[var] = 1.0 if val else 0.0

        # Let the collapse disperse before descending. A branch that is already
        # dead is abandoned here instead of being explored to full depth.
        if _disperse(spyderweb, next_assignment, [var]):
            result = _collapse_axis(spyderweb, next_assignment, depth + 1)
            if result is not None:
                return result

        # Backtracking undoes the decision, not the problem: let the axis fall
        # back into superposition before trying the opposite collapse.
        spyderweb.wavefunctions[var] = prior_wavefunction

    return None


if __name__ == "__main__":
    spiderweb_instance = QuantumSpyderweb5D(
        variables=['x1', 'x2', 'x3'],
        clauses=[
            ('x1', 'x2'),
            ('~x1', 'x3'),
            ('~x2', '~x3')
        ]
    )

    print("--- Self-Perpetuating 5D Quantum Spyderweb ---")
    solution = self_sustaining_tensor_solver(spiderweb_instance)
    print("Self-Sustaining Tensor Solution Found:", solution)
    print("Final Self-Perpetuating Charge:", spiderweb_instance.metabolic_charge)
    if solution:
        print("Verified Valid:", spiderweb_instance.verify_full_assignment(solution))
