
import matplotlib.pyplot as plt

def plot_results(positions, velocities, num_agents=3):
    plt.figure(figsize=(10, 10))
    colors = ['b', 'r', 'g']
    for i in range(num_agents):
        plt.plot(positions[i], velocities[i], label=f'AI Node {i+1} (Quantum Resonance)', linewidth=2, color=colors[i])
    plt.plot(0, 0, 'ko', label='Core Equilibrium')
    plt.xlabel('X Position')
    plt.ylabel('Y Position')
    plt.title('Codette Quantum Harmonic AI Multi-Agent Synchronization')
    plt.legend()
    plt.axis('equal')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
