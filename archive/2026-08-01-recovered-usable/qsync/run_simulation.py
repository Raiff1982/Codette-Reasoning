
from core import quantum_harmonic_dynamics, y0
from scipy.integrate import solve_ivp
from visualizer import plot_results
import numpy as np

t_span = (0, 100)
t_eval = np.linspace(t_span[0], t_span[1], 2500)

def run():
    sol = solve_ivp(lambda t, y: quantum_harmonic_dynamics(t, y)[0], t_span, y0, t_eval=t_eval, method='RK45')
    positions = sol.y[::4]
    velocities = sol.y[1::4]
    plot_results(positions, velocities)

if __name__ == "__main__":
    run()
