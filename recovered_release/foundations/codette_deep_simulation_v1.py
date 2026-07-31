import numpy as np
from scipy.fft import fft
from scipy.stats import norm
from typing import Callable, List, Any
import matplotlib.pyplot as plt
import pandas as pd

def information_energy_duality(omega: float, entropy: float, eta: float = 1.0, hbar: float = 1.054571817e-34) -> float:
    return hbar * omega + eta * entropy

def von_neumann_entropy(rho: np.ndarray) -> float:
    evals = np.linalg.eigvalsh(rho)
    evals = evals[evals > 0]
    return -np.sum(evals * np.log(evals))

def reinforced_intent_modulation(t: float, f0: float, delta_f: float, coh: Callable[[float], float], beta: float, A: Callable[[float], float], kappa: float = 1.0) -> float:
    return kappa * (f0 + delta_f * coh(t) + beta * A(t))

def dynamic_resonance_windowing(x: Callable[[float], float], omega: float, t: float, g: Callable[[float, float], float], tau_range: np.ndarray) -> complex:
    integrand = np.array([x(tau) * np.exp(-1j * omega * tau) * g(t, tau) for tau in tau_range])
    return np.trapz(integrand, tau_range)

def nonlinear_dream_coupling(ds: List[Callable[[float], float]], lambdas: List[float], phi: Callable[[List[float]], float], t: float) -> float:
    dynamic_sources = [d(t) for d in ds]
    base = np.dot(lambdas, dynamic_sources)
    nonlinear = phi(dynamic_sources)
    return base + nonlinear

def cocoon_stability_field(F: Callable[[float, float], complex], k_range: np.ndarray, t: float, epsilon: Callable[[float, float], float], sigma: float) -> bool:
    integrand = np.array([np.abs(F(k, t))**2 for k in k_range])
    value = np.trapz(integrand, k_range)
    return value < epsilon(t, sigma)

class EthicalAnchor:
    def __init__(self, lam: float, gamma: float, mu: float):
        self.lam = lam
        self.gamma = gamma
        self.mu = mu
        self.history: List[Any] = []

    def regret(self, intended: float, actual: float) -> float:
        return abs(intended - actual)

    def update(self, R_prev: float, H: float, Learn: Callable[[Any, float], float], E: float, 
               M_prev: float, intended: float, actual: float) -> float:
        regret_val = self.regret(intended, actual)
        M = self.lam * (R_prev + H) + self.gamma * Learn(M_prev, E) + self.mu * regret_val
        self.history.append({'M': M, 'regret': regret_val})
        return M

def gradient_anomaly_suppression(x: float, mu: float, delta: float, sigma: float) -> float:
    G = norm.pdf(abs(x - mu), scale=delta * sigma)
    return x * (1 - G)

# Run Simulation
time_steps = np.linspace(0, 5, 50)
intents, ethics, regrets, stabilities, anomalies = [], [], [], [], []

anchor = EthicalAnchor(lam=0.7, gamma=0.5, mu=1.0)
f0 = 10.0
delta_f = 2.0
coh = lambda t: np.sin(t)
A_feedback = lambda t: np.exp(-t)
Learn_func = lambda M_prev, E: 0.2 * (E - M_prev)
F_func = lambda k, t: np.exp(-((k - 2 * np.pi) ** 2) / 0.5) * np.exp(1j * t)
k_range = np.linspace(0, 4 * np.pi, 1000)
intended_val = 0.7
M_prev = 0.3
R_prev = 0.5
H = 0.4

for t in time_steps:
    intent = reinforced_intent_modulation(t, f0, delta_f, coh, 0.5, A_feedback)
    actual_val = np.sin(t) * 0.5 + 0.5
    anomaly = gradient_anomaly_suppression(intent, mu=11.0, delta=2.0, sigma=0.1)
    ethical_val = anchor.update(R_prev, H, Learn_func, E=0.8, M_prev=M_prev,
                                 intended=intended_val, actual=actual_val)
    stability = cocoon_stability_field(F_func, k_range, t, lambda t, sigma: 5.0 + 0.1 * sigma, 10.0)
    regret_val = anchor.history[-1]['regret']

    intents.append(intent)
    ethics.append(ethical_val)
    regrets.append(regret_val)
    stabilities.append(stability)
    anomalies.append(anomaly)

    M_prev = ethical_val

simulation_df = pd.DataFrame({
    "Time": time_steps,
    "Intent": intents,
    "Ethical_Output": ethics,
    "Regret": regrets,
    "Stable": stabilities,
    "Anomaly": anomalies
})

# Plot results
plt.figure(figsize=(14, 8))

plt.subplot(2, 2, 1)
plt.plot(simulation_df["Time"], simulation_df["Intent"], label="Intent", color='blue')
plt.title("Intent Over Time")
plt.xlabel("Time")
plt.ylabel("Intent")

plt.subplot(2, 2, 2)
plt.plot(simulation_df["Time"], simulation_df["Ethical_Output"], label="Ethical Output", color='green')
plt.plot(simulation_df["Time"], simulation_df["Regret"], label="Regret", linestyle='--', color='red')
plt.title("Ethical Anchor and Regret")
plt.xlabel("Time")
plt.legend()

plt.subplot(2, 2, 3)
plt.plot(simulation_df["Time"], simulation_df["Anomaly"], label="Anomaly", color='purple')
plt.title("Anomaly Filter Output")
plt.xlabel("Time")
plt.ylabel("Filtered Signal")

plt.subplot(2, 2, 4)
plt.plot(simulation_df["Time"], simulation_df["Stable"], label="Cocoon Stable", color='black')
plt.title("Cocoon Stability")
plt.xlabel("Time")
plt.ylabel("Stable (1=True)")

plt.tight_layout()
plt.show()

