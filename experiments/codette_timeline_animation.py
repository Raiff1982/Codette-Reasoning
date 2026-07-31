import os
import json
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

folder = '.'  # Set to your cocoons folder path if needed

# Gather data
quantum_states = []
chaos_states = []
created_times = []
labels = []

for fname in sorted(os.listdir(folder)):
    if fname.endswith('.cocoon'):
        with open(os.path.join(folder, fname), 'r') as f:
            try:
                dct = json.load(f)['data']
                q = dct.get('quantum_state', [0,0])
                c = dct.get('chaos_state', [0,0,0])
                t = dct.get('created_time')  # Use Unix timestamp if present
                quantum_states.append(q)
                chaos_states.append(c)
                created_times.append(t)
                labels.append(fname)
            except Exception as e:
                print(f"Warning: {fname} failed ({e})")

# Fallback if no times are saved: just use index as time axis
if None in created_times or len(set(created_times))==1:
    created_times = list(range(len(quantum_states)))
    ts_label = "Cocoon index"
else:
    # Normalize times so first is zero seconds, etc.
    t0 = min(filter(lambda x: x is not None, created_times))
    created_times = [t-t0 if t is not None else 0 for t in created_times]
    ts_label = "Elapsed Time [sec]"

q0_vals = [q[0] for q in quantum_states]

# Set up the figure for animation
fig, ax = plt.subplots(figsize=(10,6))
ax.set_xlim(min(created_times), max(created_times) if created_times else 1)
ax.set_ylim(min(q0_vals)-.05, max(q0_vals)+.05)
ax.set_xlabel(ts_label)
ax.set_ylabel("Quantum State [0]")
ax.set_title("Codette Quantum State Timeline Animation")
line, = ax.plot([], [], 'o-', lw=2)

def init():
    line.set_data([], [])
    return line,

def update(frame):
    xs = created_times[:frame+1]
    ys = q0_vals[:frame+1]
    line.set_data(xs, ys)
    ax.set_title(f"Codette Timeline: Step {frame+1}/{len(q0_vals)}")
    return line,

ani = FuncAnimation(fig, update, frames=len(q0_vals), init_func=init,
                    blit=True, interval=600, repeat=False)

plt.tight_layout()
plt.show()
