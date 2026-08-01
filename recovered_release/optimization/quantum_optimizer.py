import numpy as np
import random
import math
from typing import Callable, List, Tuple

class QuantumInspiredOptimizer:
    """
    A fully functional quantum-inspired optimizer using:
    - Quantum tunneling via probabilistic jumps
    - Superposition-like population exploration
    - Entanglement-inspired correlation tracking
    """
    def __init__(self, objective_fn: Callable[[List[float]], float],
                 dimension: int,
                 population_size: int = 50,
                 iterations: int = 100,
                 tunneling_prob: float = 0.2,
                 entanglement_factor: float = 0.5):

        self.objective_fn = objective_fn
        self.dimension = dimension
        self.population_size = population_size
        self.iterations = iterations
        self.tunneling_prob = tunneling_prob
        self.entanglement_factor = entanglement_factor

        self.population = [self._random_solution() for _ in range(population_size)]
        self.best_solution = None
        self.best_score = float('inf')

    def _random_solution(self) -> List[float]:
        return [random.uniform(-10, 10) for _ in range(self.dimension)]

    def _tunnel(self, solution: List[float]) -> List[float]:
        return [x + np.random.normal(0, 1) * random.choice([-1, 1])
                if random.random() < self.tunneling_prob else x
                for x in solution]

    def _entangle(self, solution1: List[float], solution2: List[float]) -> List[float]:
        return [(1 - self.entanglement_factor) * x + self.entanglement_factor * y
                for x, y in zip(solution1, solution2)]

    def optimize(self) -> Tuple[List[float], float]:
        for iteration in range(self.iterations):
            scored_population = [(sol, self.objective_fn(sol)) for sol in self.population]
            scored_population.sort(key=lambda x: x[1])

            if scored_population[0][1] < self.best_score:
                self.best_solution, self.best_score = scored_population[0]

            new_population = [self.best_solution]  # elitism
            while len(new_population) < self.population_size:
                parent1 = random.choice(scored_population[:self.population_size // 2])[0]
                parent2 = random.choice(scored_population[:self.population_size // 2])[0]
                child = self._entangle(parent1, parent2)
                child = self._tunnel(child)
                new_population.append(child)

            self.population = new_population

        return self.best_solution, self.best_score

# Example usage
if __name__ == '__main__':
    def sphere_function(x: List[float]) -> float:
        return sum(xi ** 2 for xi in x)

    q_opt = QuantumInspiredOptimizer(objective_fn=sphere_function, dimension=5)
    best_sol, best_val = q_opt.optimize()
    print("Best Solution:", best_sol)
    print("Best Value:", best_val)
