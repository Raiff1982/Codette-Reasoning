import numpy as np
import random
import math
import time
from typing import Callable, List, Tuple
import matplotlib.pyplot as plt


class QuantumInspiredMultiObjectiveOptimizer:
    def __init__(self,
                 objective_fns: List[Callable[[List[float]], float]],
                 dimension: int,
                 population_size: int = 100,
                 iterations: int = 200,
                 tunneling_prob: float = 0.2,
                 entanglement_factor: float = 0.5,
                 mutation_scale: float = 1.0,
                 archive_size: int = 200):
        self.objective_fns = objective_fns
        self.dimension = dimension
        self.population_size = population_size
        self.iterations = iterations
        self.tunneling_prob = tunneling_prob
        self.entanglement_factor = entanglement_factor
        self.mutation_scale = mutation_scale
        self.archive_size = archive_size

        self.population = [self._random_solution() for _ in range(population_size)]
        self.pareto_front = []
        self.archive = []

    def _random_solution(self) -> List[float]:
        return [random.uniform(-10, 10) for _ in range(self.dimension)]

    def _tunnel(self, solution: List[float], scale: float) -> List[float]:
        return [x + np.random.normal(0, scale) * random.choice([-1, 1])
                if random.random() < self.tunneling_prob else x
                for x in solution]

    def _entangle(self, solution1: List[float], solution2: List[float], factor: float) -> List[float]:
        return [(1 - factor) * x + factor * y for x, y in zip(solution1, solution2)]

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

    def _update_archive(self, pareto: List[Tuple[List[float], List[float]]]):
        combined = self.archive + pareto
        combined = self._pareto_selection(combined)
        self.archive = sorted(combined, key=lambda x: tuple(x[1]))[:self.archive_size]

    def optimize(self) -> Tuple[List[Tuple[List[float], List[float]]], float]:
        start_time = time.time()
        for i in range(self.iterations):
            adaptive_tunnel = self.mutation_scale * (1 - i / self.iterations)
            adaptive_entangle = self.entanglement_factor * (1 - i / self.iterations)

            scored_population = [(sol, self._evaluate(sol)) for sol in self.population]
            pareto = self._pareto_selection(scored_population)
            self._update_archive(pareto)
            self.pareto_front = pareto

            new_population = [p[0] for p in pareto]
            while len(new_population) < self.population_size:
                parent1 = random.choice(pareto)[0]
                parent2 = random.choice(pareto)[0]
                if parent1 == parent2:
                    parent2 = self._tunnel(parent2, adaptive_tunnel)
                child = self._entangle(parent1, parent2, adaptive_entangle)
                child = self._tunnel(child, adaptive_tunnel)
                new_population.append(child)

            self.population = new_population

        duration = time.time() - start_time
        return self.archive, duration


def sphere(x: List[float]) -> float:
    return sum(xi ** 2 for xi in x)


def rastrigin(x: List[float]) -> float:
    return 10 * len(x) + sum(xi ** 2 - 10 * math.cos(2 * math.pi * xi) for xi in x)


if __name__ == '__main__':
    optimizer = QuantumInspiredMultiObjectiveOptimizer(
        objective_fns=[sphere, rastrigin],
        dimension=20,
        population_size=100,
        iterations=200,
        tunneling_prob=0.2,
        entanglement_factor=0.5,
        mutation_scale=1.0,
        archive_size=300
    )

    pareto_front, duration = optimizer.optimize()
    print(f"Optimization completed in {duration:.2f} seconds")
    print(f"Pareto front size: {len(pareto_front)}")
    for sol, scores in pareto_front:
        print("Solution:", sol, "Objectives:", scores)

    if len(pareto_front[0][1]) == 2:
        x_vals = [obj[0] for _, obj in pareto_front]
        y_vals = [obj[1] for _, obj in pareto_front]
        plt.scatter(x_vals, y_vals, c='blue', label='Pareto Front')
        plt.xlabel('Objective 1')
        plt.ylabel('Objective 2')
        plt.title('Pareto Front Visualization')
        plt.legend()
        plt.grid(True)
        plt.show()
