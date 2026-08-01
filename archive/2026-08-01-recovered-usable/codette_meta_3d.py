import os
import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from sklearn.cluster import KMeans

folder = '.'  # Orpath to your ./astro_cocoons

quantum_states=[]
chaos_states=[]
proc_ids=[]
labels=[]

# Load cocoons
for fname in os.listdir(folder):
    if fname.endswith('.cocoon'):
        with open(os.path.join(folder, fname), 'r') as f:
            try:
                data=json.load(f)['data']
                quantum= data.get('quantum_state', [0, 0])
                chaos= data.get('chaos_state', [0, 0, 0])
                quantum_states.append(quantum)
                chaos_states.append(chaos)
                proc_ids.append(data.get('run_by_proc', -1))
                labels.append(fname)
            except Exception as e:
                print(f'Failed to read {fname}: {e}')

if len(quantum_states) < 2 or len(chaos_states) < 2:
    print("Not enough cocoons for meaningful clustering/plotting.")
    exit()

# Assemble feature vectors: [q0, c0, c2]
features = np.array([[q[0], c[0], c[2] if len(c)>2 else 0] for q,c in zip(quantum_states, chaos_states)])

# --- Codette Auto Pattern Discovery: KMeans ---
optimal_clusters = min(len(features),5)      # Can't have more clusters than points!
kmeans = KMeans(n_clusters=optimal_clusters, n_init=10)
labels_cluster = kmeans.fit_predict(features)

# --- Make the 3D plot with discovered clusters ---
fig = plt.figure(figsize=(10,8))
ax = fig.add_subplot(111, projection='3d')
sc = ax.scatter(features[:,0], features[:,1], features[:,2], 
                c=labels_cluster, cmap='rainbow', s=120,
                label='Cocoon Universes')

ax.set_xlabel('Quantum State [0]')
ax.set_ylabel('Chaos State [0]')
ax.set_zlabel('Chaos State [2]')
ax.set_title('Codette 3D Meta-Universe Clustering\n(AI Auto-Pattern Discoverer)')
plt.colorbar(sc,label="Cluster (Universe Family)")

for i, txt in enumerate(labels):
    ax.text(features[i,0], features[i,1], features[i,2], f'{txt}', size=7)

plt.tight_layout()
plt.show()

print(f"\nCodette Meta-Clusters (AI discovered):\n")
for idx in range(optimal_clusters):
    print(f"Cluster {idx} : {[labels[i] for i in np.where(labels_cluster==idx)[0]]}")
