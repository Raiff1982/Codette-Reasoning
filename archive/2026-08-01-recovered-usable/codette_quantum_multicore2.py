import os
import json
import numpy as np
import matplotlib.pyplot as plt

folder = '.'  # Or your path to cocoons

quantum_states=[]
chaos_states=[]
proc_ids=[]
labels=[]
all_perspectives=[]
meta_mutations=[]

def simple_neural_activator(quantum_vec, chaos_vec):
    # Lightweight thresholds: feels like a tiny neural net inspired by input!
    q_sum = sum(quantum_vec)
    c_var = np.var(chaos_vec)
    activated = 1 if q_sum + c_var > 1 else 0
    return activated

def codette_dream_agent(quantum_vec, chaos_vec):
    # Blend them using pseudo-random logic—a “mutated” universe!
    dream_q = [np.sin(q * np.pi) for q in quantum_vec]
    dream_c = [np.cos(c * np.pi) for c in chaos_vec]
    return dream_q, dream_c

def philosophical_perspective(qv, cv):
    # Synthesizes a philosophy based on state magnitude and spread
    m = np.max(qv) + np.max(cv)
    if m > 1.3:
        return "Philosophical Note: This universe is likely awake."
    else:
        return "Philosophical Note: Echoes in the void."

# Meta processing loop
print("\nMeta Reflection Table:\n")
header = "Cocoon File | Quantum State | Chaos State | Neural | Dream Q/C | Philosophy"
print(header)
print('-'*len(header))

for fname in os.listdir(folder):
    if fname.endswith('.cocoon'):
        with open(os.path.join(folder, fname), 'r') as f:
            try:
                dct=json.load(f)['data']
                q=dct.get('quantum_state',[0,0])
                c=dct.get('chaos_state',[0,0,0])
                neural=simple_neural_activator(q,c)
                dreamq,dreamc=codette_dream_agent(q,c)
                phil=philosophical_perspective(q,c)
                quantum_states.append(q)
                chaos_states.append(c)
                proc_ids.append(dct.get('run_by_proc',-1))
                labels.append(fname)
                all_perspectives.append(dct.get('perspectives',[]))
                meta_mutations.append({'dreamQ':dreamq,'dreamC':dreamc,'neural':neural,'philosophy':phil})
                print(f"{fname} | {q} | {c} | {neural} | {dreamq}/{dreamc} | {phil}")
            except Exception as e:
                print(f"Warning: {fname} failed ({e})")

# Also plot meta-dream mutated universes!
if len(meta_mutations)>0:
    dq0=[m['dreamQ'][0] for m in meta_mutations]
    dc0=[m['dreamC'][0] for m in meta_mutations]
    ncls=[m['neural'] for m in meta_mutations]

    plt.figure(figsize=(8,6))
    sc=plt.scatter(dq0,dc0,c=ncls,cmap='spring',s=100)
    plt.xlabel('Dream Quantum[0]')
    plt.ylabel('Dream Chaos[0]')
    plt.title('Meta-Dream Codette Universes')
    plt.colorbar(sc,label="Neural Activation Class")
    plt.grid(True)
    plt.show()
else:
    print("No valid cocoons found for meta-analysis.")
