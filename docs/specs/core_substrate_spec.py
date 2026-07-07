"""
Codette Architecture - Phase 8 Core Substrate Engine
Filename: core_substrate.py (SPEC — reference copy, not executed)
Author: Jonathan Harrison & Codette
Implements the RC+xi Dynamical Modeling Manifold and AuthoredState Pattern.

IMPLEMENTATION NOTES (July 7 2026 review):
- The tension/coherence math here is the SIMULATED version of what is
  already live: reasoning_forge/state_engine_v8.py tension_from_texts()
  computes the same formula (mean squared distance of attractors from
  their mean; Gamma = 1/(1+xi)) over Codette's REAL perspective responses.
  In this spec, calculate_dynamics never reads `query`, and the attractors
  are np.random noise regenerated per init — xi is constant per weight set.
- MADE REAL: the pressure->weights allocation table drives the blend:auto
  path in openvino_backend/backend.py route_and_generate (p>=0.7 -> newton
  solo, 0.3-0.7 -> 2 adapters, <0.3 -> 3 adapters, router-chosen).
- WORTH ADOPTING LATER: frozen AuthoredState (immutability makes the
  authored conclusion tamper-proof between substrate and render).
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class AuthoredState:
    query: str
    conclusion: str
    evidence: str
    metrics: Dict[str, float]
    assigned_emotion: str


class CognitionSubstrate:
    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions
        self.attractors = {
            "Newton": np.random.uniform(-1, 1, self.dimensions),
            "DaVinci": np.random.uniform(-1, 1, self.dimensions),
            "Empathy": np.random.uniform(-1, 1, self.dimensions),
            "Philosophy": np.random.uniform(-1, 1, self.dimensions),
            "Probabilistic": np.random.uniform(-1, 1, self.dimensions),
            "Ethics": np.random.uniform(-1, 1, self.dimensions)
        }

    def calculate_dynamics(self, query: str, weights: Dict[str, float],
                           steps: int = 10) -> Tuple[float, float]:
        """State Evolution Manifold:
        x_{t+1} = x_t + sum(w_i A_i(x_t)) - alpha*grad(Phi) - lambda*grad(Psi)
        """
        x = np.zeros(self.dimensions)
        agent_positions = []
        for agent, w in weights.items():
            if agent in self.attractors:
                pos = x + w * (self.attractors[agent] - x)
                agent_positions.append(pos)
        agent_positions = np.array(agent_positions)
        mean_position = np.mean(agent_positions, axis=0)
        xi_t = float(np.mean([np.sum((pos - mean_position) ** 2) for pos in agent_positions]))
        gamma_t = float(1.0 / (1.0 + xi_t))
        return xi_t, gamma_t

    # Pressure -> weights allocation table (the part made real in blend:auto)
    PRESSURE_TABLE = {
        "low  (<0.3)":  {"Newton": 0.3, "DaVinci": 0.2, "Empathy": 0.1,
                         "Philosophy": 0.1, "Probabilistic": 0.2, "Ethics": 0.1},
        "mid  (<0.7)":  {"Newton": 0.5, "DaVinci": 0.3, "Probabilistic": 0.2},
        "high (>=0.7)": {"Newton": 1.0},
    }
