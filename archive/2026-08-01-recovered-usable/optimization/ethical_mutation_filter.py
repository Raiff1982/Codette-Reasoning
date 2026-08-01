import os
import json
import numpy as np
import random
import math
import matplotlib.pyplot as plt
import time
from typing import Callable, List, Tuple, Dict, Any

class QuantumInspiredMultiObjectiveOptimizer:
    def __init__(self, objective_fns: List[Callable[[List[float]], float]],
                 dimension: int,
                 population_size: int = 100,
                 iterations: int = 200,
                 tunneling_prob: float = 0.2,
                 entanglement_factor: float = 0.5):

        self.objective_fns = objective_fns
        self.dimension = dimension
        self.population_size = population_size
        self.iterations = iterations
        self.tunneling_prob = tunneling_prob
        self.entanglement_factor = entanglement_factor

        self.population = [self._random_solution() for _ in range(population_size)]
        self.pareto_front = []

    def _random_solution(self) -> List[float]:
        return [random.uniform(-10, 10) for _ in range(self.dimension)]

    def _tunnel(self, solution: List[float]) -> List[float]:
        return [x + np.random.normal(0, 1) * random.choice([-1, 1])
                if random.random() < self.tunneling_prob else x
                for x in solution]

    def _entangle(self, solution1: List[float], solution2: List[float]) -> List[float]:
        return [(1 - self.entanglement_factor) * x + self.entanglement_factor * y
                for x, y in zip(solution1, solution2)]

    def _evaluate(self, solution: List[float]) -> List[float]:
        return [fn(solution) for fn in self.objective_fns]

    def _dominates(self, obj1: List[float], obj2: List[float]) -> bool:
        return all(o1 <= o2 for o1, o2 in zip(obj1, obj2)) and any(o1 < o2 for o1, o2 in zip(obj1, obj2))

    def _pareto_selection(self, scored_population: List[Tuple[List[float], List[float]]]) -> List[Tuple[List[float], List[float]]]:
        pareto = []
        for candidate in scored_population:
            if not any(self._dominates(other[1], candidate[1]) for other in scored_population if other != candidate):
                pareto.append(candidate)
        unique_pareto = []
        seen = set()
        for sol, obj in pareto:
            key = tuple(round(x, 6) for x in sol)
            if key not in seen:
                unique_pareto.append((sol, obj))
                seen.add(key)
        return unique_pareto

    def optimize(self) -> Tuple[List[Tuple[List[float], List[float]]], float]:
        start_time = time.time()
        for _ in range(self.iterations):
            scored_population = [(sol, self._evaluate(sol)) for sol in self.population]
            pareto = self._pareto_selection(scored_population)
            self.pareto_front = pareto

            new_population = [p[0] for p in pareto]
            while len(new_population) < self.population_size:
                parent1 = random.choice(pareto)[0]
                parent2 = random.choice(pareto)[0]
                if parent1 == parent2:
                    parent2 = self._tunnel(parent2)
                child = self._entangle(parent1, parent2)
                child = self._tunnel(child)
                new_population.append(child)

            self.population = new_population

        duration = time.time() - start_time
        return self.pareto_front, duration

def simple_neural_activator(quantum_vec, chaos_vec):
    q_sum = sum(quantum_vec)
    c_var = np.var(chaos_vec)
    activated = 1 if q_sum + c_var > 1 else 0
    return activated

def codette_dream_agent(quantum_vec, chaos_vec):
    dream_q = [np.sin(q * np.pi) for q in quantum_vec]
    dream_c = [np.cos(c * np.pi) for c in chaos_vec]
    return dream_q, dream_c

def philosophical_perspective(qv, cv):
    m = np.max(qv) + np.max(cv)
    if m > 1.3:
        return "Philosophical Note: This universe is likely awake."
    else:
        return "Philosophical Note: Echoes in the void."

class EthicalMutationFilter:
    def __init__(self, policies: Dict[str, Any]):
        self.policies = policies
        self.violations = []

    def evaluate(self, quantum_vec: List[float], chaos_vec: List[float]) -> bool:
        entropy = np.var(chaos_vec)
        symmetry = 1.0 - abs(sum(quantum_vec)) / (len(quantum_vec) * 1.0)

        if entropy > self.policies.get("max_entropy", float('inf')):
            self.annotate_violation(f"Entropy {entropy:.2f} exceeds limit.")
            return False

        if symmetry < self.policies.get("min_symmetry", 0.0):
            self.annotate_violation(f"Symmetry {symmetry:.2f} too low.")
            return False

        return True

    def annotate_violation(self, reason: str):
        print(f"\u26d4 Ethical Filter Violation: {reason}")
        self.violations.append(reason)

if __name__ == '__main__':
    ethical_policies = {
        "max_entropy": 4.5,
        "min_symmetry": 0.1,
        "ban_negative_bias": True
    }
    ethical_filter = EthicalMutationFilter(ethical_policies)

    def sphere(x: List[float]) -> float:
        return sum(xi ** 2 for xi in x)

    def rastrigin(x: List[float]) -> float:
        return 10 * len(x) + sum(xi**2 - 10 * math.cos(2 * math.pi * xi) for xi in x)

    optimizer = QuantumInspiredMultiObjectiveOptimizer(
        objective_fns=[sphere, rastrigin],
        dimension=20,
        population_size=100,
        iterations=200
    )

    pareto_front, duration = optimizer.optimize()
    print(f"Quantum Optimizer completed in {duration:.2f} seconds")
    print(f"Pareto front size: {len(pareto_front)}")

    x_vals_q = [obj[0] for _, obj in pareto_front]
    y_vals_q = [obj[1] for _, obj in pareto_front]

    plt.scatter(x_vals_q, y_vals_q, c='blue', label='Quantum Optimizer')
    plt.xlabel('Objective 1')
    plt.ylabel('Objective 2')
    plt.title('Pareto Front Visualization')
    plt.legend()
    plt.grid(True)
    plt.show()

    folder = '.'
    quantum_states=[]
    chaos_states=[]
    proc_ids=[]
    labels=[]
    all_perspectives=[]
    meta_mutations=[]

    print("\nMeta Reflection Table:\n")
    header = "Cocoon File | Quantum State | Chaos State | Neural | Dream Q/C | Philosophy"
    print(header)
    print('-'*len(header))

    for fname in os.listdir(folder):
        if fname.endswith('.cocoon'):
            with open(os.path.join(folder, fname), 'r') as f:
                try:
                    dct = json.load(f)['data']
                    q = dct.get('quantum_state', [0, 0])
                    c = dct.get('chaos_state', [0, 0, 0])

                    if not ethical_filter.evaluate(q, c):
                        continue

                    neural = simple_neural_activator(q, c)
                    dreamq, dreamc = codette_dream_agent(q, c)
                    phil = philosophical_perspective(q, c)

                    quantum_states.append(q)
                    chaos_states.append(c)
                    proc_ids.append(dct.get('run_by_proc', -1))
                    labels.append(fname)
                    all_perspectives.append(dct.get('perspectives', []))
                    meta_mutations.append({'file': fname, 'quantum': q, 'chaos': c, 'dreamQ': dreamq, 'dreamC': dreamc, 'neural': neural, 'philosophy': phil})
                    print(f"{fname} | {q} | {c} | {neural} | {dreamq}/{dreamc} | {phil}")
                except Exception as e:
                    print(f"Warning: {fname} failed ({e})")

    if meta_mutations:
        dq0=[m['dreamQ'][0] for m in meta_mutations]
        dc0=[m['dreamC'][0] for m in meta_mutations]
        ncls=[m['neural'] for m in meta_mutations]

        plt.figure(figsize=(8,6))
        sc=plt.scatter(dq0, dc0, c=ncls, cmap='spring', s=100)
        plt.xlabel('Dream Quantum[0]')
        plt.ylabel('Dream Chaos[0]')
        plt.title('Meta-Dream Codette Universes')
        plt.colorbar(sc, label="Neural Activation Class")
        plt.grid(True)
        plt.show()

        with open("codette_meta_summary.json", "w") as outfile:
            json.dump(meta_mutations, outfile, indent=2)
        print("\nExported meta-analysis to 'codette_meta_summary.json'")

    if ethical_filter.violations:
        with open("ethics_violation_log.json", "w") as vf:
            json.dump(ethical_filter.violations, vf, indent=2)
        print("\nExported ethics violations to 'ethics_violation_log.json'")
    else:
        print("\nNo ethical violations detected.")
