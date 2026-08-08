"""Multi-agent convergence simulation — the numerical origin of Perspective Dispersion.

RECOVERED 2026-08-03 from `paper/Document (23).docx`, which was untracked on disk
and present in no branch. The .docx is a real Word container (PKZip magic); the
Python was the document body. Found by `tools/archive_diff.py`, which matched it
to `reasoning_forge/quantum_spiderweb.py` on symbol overlap — that match is
WRONG. This is a different, standalone program.

Why it matters: it defines `epistemic_tension` — the pre-rename name of
Perspective Dispersion (Y) — as the mean squared deviation of agent outputs from
their mean, and runs the multi-agent loop against a single-agent gradient-descent
baseline. This is the metric's origin in its rawest executable form, predating
the Camlin attribution work (RC+xi is Camlin's; Y is a different quantity).

Verified 2026-08-03, not assumed: runs to completion under Python 3.14 / numpy
2.4.6. One run gave final norm 0.0267, epistemic tension 0.0152, phase coherence
1.0, single-agent baseline norm 0.000149. Stochastic (`np.random.randn` seeds the
state, `agent_noise` injects noise) and unseeded, so figures differ per run.

Body below is VERBATIM as recovered. Nothing repaired, reformatted, or renamed —
including `epistemic_tension`, kept at its original spelling deliberately. Writes
`tension.npy` and `coherence.npy` into the working directory when run.
"""
import numpy as np
# -----------------------------
# CONFIG
# -----------------------------
DIM = 32
NUM_AGENTS = 5
ITERATIONS = 100
LAMBDA = 0.1
LEARNING_RATE = 0.05
# -----------------------------
# AGENTS
# -----------------------------
def agent_linear(x):
    return 0.8 * x
def agent_noise(x):
    return x + np.random.normal(0, 0.05, size=x.shape)
def agent_nonlinear(x):
    return np.tanh(x)
AGENTS = [ agent_linear, agent_noise, agent_nonlinear, agent_linear, agent_nonlinear ]
weights = np.ones(NUM_AGENTS) / NUM_AGENTS
# -----------------------------
# POTENTIAL FUNCTIONS
# -----------------------------
def phi(x):
    return np.linalg.norm(x)**2
def grad_phi(x):
    return 2 * x
def psi(x):
    return np.sum(np.maximum(0, x - 1)**2)
def grad_psi(x):
    return 2 * np.maximum(0, x - 1)
# -----------------------------
# METRICS
# -----------------------------
def epistemic_tension(agent_outputs):
    mean = np.mean(agent_outputs, axis=0)
    return np.mean([np.linalg.norm(a - mean)**2 for a in agent_outputs])
def phase_coherence(agent_outputs):
    phases = [np.angle(np.fft.fft(a)[0]) for a in agent_outputs]
    return np.abs(np.mean(np.exp(1j * np.array(phases))))
# -----------------------------
# MAIN LOOP
# -----------------------------
x = np.random.randn(DIM)
tension_history = []
coherence_history = []
for t in range(ITERATIONS):
    agent_outputs = [agent(x) for agent in AGENTS]
    combined = sum(w * a for w, a in zip(weights, agent_outputs))
    update = ( combined - grad_phi(x) - LAMBDA * grad_psi(x) )
    x = x + LEARNING_RATE * update
    tension = epistemic_tension(agent_outputs)
    coherence = phase_coherence(agent_outputs)
    tension_history.append(tension)
    coherence_history.append(coherence)
# -----------------------------
# RESULTS
# -----------------------------
print("Final State Norm:", np.linalg.norm(x))
print("Final Epistemic Tension:", tension_history[-1])
print("Final Phase Coherence:", coherence_history[-1])
# Optional: Save results
np.save("tension.npy", tension_history)
np.save("coherence.npy", coherence_history)
# Single-agent baseline
x = np.random.randn(DIM)
baseline_history = []
for t in range(ITERATIONS):
    x = x - LEARNING_RATE * grad_phi(x)
    baseline_history.append(np.linalg.norm(x))
print("Baseline Final Norm:", np.linalg.norm(x))