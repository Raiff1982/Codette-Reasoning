"""
Recovered from allforone.docx.

Source was stored inside a Word document; the original filename does not
describe the contents.
"""


# Requires: qiskit, pyyaml, json, networkx, colorama
import yaml, json, os, random
import networkx as nx
from qiskit import QuantumCircuit, Aer, execute
from colorama import Fore, Style

###############
# LOAD COCOONS
###############
def load_cocoons(path):
    if path.endswith('.yaml') or path.endswith('.yml'):
        with open(path) as f:
            data = yaml.safe_load(f)
    elif path.endswith('.json'):
        with open(path) as f:
            data = json.load(f)
    else:
        raise ValueError("Unsupported file type")
    return data['cocoons']

########################################
# FUNNEL INTO PARALLEL PERSPECTIVE WEBS
########################################
def funnel_to_webs(cocoons, perspectives=None):
    if perspectives is None:
        # Default quantum-emotional perspectives
        perspectives = ["compassion", "curiosity", "fear", "joy", "sorrow"]
    webs = {p: nx.Graph() for p in perspectives}
    for cocoon in cocoons:
        for p in perspectives:
            if cocoon['emotion'] == p or p in cocoon.get('tags', []):
                webs[p].add_node(cocoon['title'], **cocoon)
    return webs

#################################
# QUANTUM WALK ON EACH PERSPECTIVE
#################################
def quantum_walk_web(web):
    num_nodes = web.number_of_nodes()
    if num_nodes == 0:
        return None
    qc = QuantumCircuit(num_nodes, num_nodes)
    for i in range(num_nodes):
        qc.h(i)  # Superposition
    qc.measure_all()
    backend = Aer.get_backend('qasm_simulator')
    result = execute(qc, backend, shots=1).result()
    counts = result.get_counts()
    state = list(counts.keys())[0]
    # Pick a node based on the "collapsed" state
    index = int(state, 2) if state != '' else 0
    if index >= num_nodes:
        index = 0
    node_list = list(web.nodes(data=True))
    return node_list[index][1]  # Return cocoon data dict

########################################
# SYNTHESIZE & PRINT MULTI-PERSPECTIVE RESULT
########################################
def codette_spiderweb_synthesis(webs):
    color_map = {
        "compassion": Fore.MAGENTA,
        "curiosity": Fore.CYAN,
        "fear": Fore.RED,
        "joy": Fore.YELLOW,
        "sorrow": Fore.BLUE
    }
    print("\n" + "="*30 + "\nCodette's Quantum Spiderweb Council\n" + "="*30)
    results = {}
    for p, web in webs.items():
        cocoon = quantum_walk_web(web)
        color = color_map.get(p, Fore.WHITE)
        if cocoon:
            print(
                color
                + f"{p.title()} perspective: {cocoon['title']} [{cocoon['emotion']}]"
                + Style.RESET_ALL
            )
            print(Style.DIM + f"  Summary: {cocoon['summary']}" + Style.RESET_ALL)
            print(Style.BRIGHT + f"  Quote: {cocoon['quote']}" + Style.RESET_ALL)
            results[p] = cocoon
        else:
            print(color + f"{p.title()} perspective: No cocoon found." + Style.RESET_ALL)
    print("\nCouncil synthesis complete.\n" + "="*30 + "\n")
    return results

#################
# MAIN PIPELINE
#################
def codette_quantum_pipeline(cocoon_path):
    cocoons = load_cocoons(cocoon_path)
    webs = funnel_to_webs(cocoons)
    results = codette_spiderweb_synthesis(webs)
    return results

###########
# USAGE
###########
# Save your cocoons as 'cocoons.yaml' or 'cocoons.json' in the shown format above.
# Then run:
# codette_quantum_pipeline('cocoons.yaml')
# or
# codette_quantum_pipeline('cocoons.json')


