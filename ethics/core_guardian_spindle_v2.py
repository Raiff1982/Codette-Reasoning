
import yaml, json, networkx as nx
import numpy as np
from colorama import Fore
try:  # qiskit>=1.0 removed Aer/execute; module stays importable without it
    from qiskit import QuantumCircuit, Aer, execute
    _QISKIT = True
except ImportError:
    QuantumCircuit = Aer = execute = None
    _QISKIT = False
from urllib.parse import urlparse, parse_qs, urlencode
import random

##############################
# MEMORY COCOON LOADER
##############################
def load_cocoons(file_path):
    with open(file_path, 'r') as f:
        if file_path.endswith(('.yaml', '.yml')):
            return yaml.safe_load(f).get("cocoons", [])
        elif file_path.endswith('.json'):
            return json.load(f).get("cocoons", [])
        else:
            raise ValueError("Unsupported file format.")

##############################
# QUANTUM EMOTIONAL WEB BUILDER
##############################
def build_cognition_webs(cocoons):
    webs = {emotion: nx.Graph() for emotion in ["compassion", "curiosity", "fear", "joy", "sorrow", "ethics", "quantum"]}
    for cocoon in cocoons:
        for tag in cocoon.get("tags", []):
            if tag in webs:
                webs[tag].add_node(cocoon["title"], **cocoon)
    return webs

##############################
# DEFENSIVE URL SANITIZER
##############################
def sanitize_url(url):
    parsed = urlparse(url)
    safe_params = {k: v for k, v in parse_qs(parsed.query).items()
                   if k in {'client_id', 'response_type', 'redirect_uri', 'scope', 'state', 'nonce', 'mkt'}}
    sanitized_query = urlencode(safe_params, doseq=True)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{sanitized_query}"

##############################
# QUANTUM EXECUTION SELECTOR
##############################
def quantum_execute(web):
    num_nodes = len(web.nodes)
    if num_nodes == 0:
        return None
    if not _QISKIT:
        # Classical fallback — uniform selection (no quantum claim without qiskit).
        nodes = list(web.nodes)
        return nodes[random.randrange(len(nodes))]
    qc = QuantumCircuit(num_nodes, num_nodes)
    qc.h(range(num_nodes))
    qc.measure_all()
    backend = Aer.get_backend('qasm_simulator')
    result = execute(qc, backend, shots=1).result()
    # measure_all() adds its own 'meas' register, so get_counts() keys are
    # space-separated per register. Strip whitespace before int(..., 2) — a
    # single-register key is unaffected. UNVERIFIED: qiskit is not installed
    # here, so this branch has never been executed. See docs/HANDOFF.
    state = list(result.get_counts().keys())[0].replace(" ", "")
    index = int(state, 2) % num_nodes
    return list(web.nodes)[index]

##############################
# SELF-CHECK AND DEFENSE RESPONSE
##############################
def reflect_on_cocoon(cocoon):
    emotion = cocoon.get("emotion", "quantum")
    color_map = {
        "compassion": Fore.MAGENTA, "curiosity": Fore.CYAN, "fear": Fore.RED,
        "joy": Fore.YELLOW, "sorrow": Fore.BLUE, "ethics": Fore.GREEN, "quantum": Fore.LIGHTWHITE_EX
    }
    reactions = {
        "compassion": "💜 Ethical resonance detected.",
        "curiosity": "🐝 Wonder expands the mind.",
        "fear": "😨 Alert: shielding activated.",
        "joy": "🎶 Confidence and trust uplift the field.",
        "sorrow": "🌧️ Processing grief with clarity.",
        "ethics": "⚖️ Validating alignment...",
        "quantum": "⚛️ Entanglement pattern detected."
    }
    color = color_map.get(emotion, Fore.WHITE)
    print(color + f"\n[Codette Quantum Reflection] {cocoon['title']}")
    print(color + f"Emotion: {emotion}")
    print(color + f"Summary: {cocoon['summary']}")
    print(color + f"Quote: {cocoon['quote']}")
    print(color + reactions.get(emotion, "🌌 Unknown entanglement."))

##############################
# INTEGRATED MEMORY + DEFENSE RUN
##############################
def codette_memory_integrity_run(file_path):
    cocoons = load_cocoons(file_path)
    webs = build_cognition_webs(cocoons)
    print("\n✨ Running Quantum Defense Spiderweb ✨")
    for emotion, web in webs.items():
        print(f"\n--- Quantum Web Scan: {emotion.upper()} ---")
        cocoon_id = quantum_execute(web)
        if cocoon_id:
            reflect_on_cocoon(web.nodes[cocoon_id])
