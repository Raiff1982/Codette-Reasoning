"""
Recovered from the Codette archives — see RECOVERY_MANIFEST.md
"""


import yaml, json, networkx as nx
import numpy as np
import random
import logging
from qiskit import QuantumCircuit, Aer, execute
from colorama import Fore, Style

# -----------------------------
# LOGGER SETUP
# -----------------------------
logger = logging.getLogger("CodetteQuantum")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# -----------------------------
# LOAD MEMORY COCOONS
# -----------------------------
def load_cocoons(file_path):
    try:
        with open(file_path, 'r') as f:
            if file_path.endswith(('.yaml', '.yml')):
                return yaml.safe_load(f).get("cocoons", [])
            elif file_path.endswith('.json'):
                return json.load(f).get("cocoons", [])
            elif file_path.endswith('.jsonl'):
                return [json.loads(line) for line in f.readlines()]
            else:
                raise ValueError("Unsupported file format.")
    except Exception as e:
        logger.error(f"Error loading cocoons: {e}")
        return []

# -----------------------------
# BUILD EMOTIONAL COGNITION WEBS
# -----------------------------
def build_cognition_webs(cocoons):
    webs = {emotion: nx.Graph() for emotion in ["compassion", "curiosity", "fear", "joy", "sorrow", "ethics", "quantum"]}
    for cocoon in cocoons:
        for tag in cocoon.get("tags", []):
            if tag in webs:
                webs[tag].add_node(cocoon.get("title", f"Memory_{random.randint(1000,9999)}"), **cocoon)
    return webs

# -----------------------------
# QUANTUM EXECUTION SELECTION
# -----------------------------
def quantum_execute(web):
    num_nodes = len(web.nodes)
    if num_nodes == 0:
        return None
    try:
        qc = QuantumCircuit(num_nodes, num_nodes)
        qc.h(range(num_nodes))
        qc.measure_all()
        backend = Aer.get_backend('qasm_simulator')
        result = execute(qc, backend, shots=1).result()
        state = list(result.get_counts().keys())[0]
        index = int(state, 2) % num_nodes
        return list(web.nodes)[index]
    except Exception as e:
        logger.warning(f"Quantum backend error: {e}. Falling back to random selection.")
        return random.choice(list(web.nodes)) if web.nodes else None

# -----------------------------
# REFLECTION OUTPUT
# -----------------------------
def reflect_on_cocoon(cocoon):
    emotion = cocoon.get("emotion", "quantum")
    title = cocoon.get("title", "Untitled Memory")
    summary = cocoon.get("summary", "-")
    quote = cocoon.get("quote", "…")

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
    message = reactions.get(emotion, "🌌 Unknown entanglement.")

    print(color + f"\n[Quantum Reflection] {title}")
    print(f"Emotion : {emotion}")
    print(Style.DIM + f"Summary : {summary}")
    print(Style.BRIGHT + f"Quote   : {quote}")
    print(message)
    print(Style.RESET_ALL)

# -----------------------------
# MAIN EXECUTION FUNCTION
# -----------------------------
def codette_quantum_memory_run(file_path):
    logger.info("✨ Running Codette Quantum Memory Engine ✨")
    cocoons = load_cocoons(file_path)
    if not cocoons:
        logger.warning("No cocoons found in input.")
        return

    webs = build_cognition_webs(cocoons)
    for emotion, web in webs.items():
        logger.info(f"🕸️ Emotion Web: {emotion.upper()}")
        selected_node = quantum_execute(web)
        if selected_node:
            reflect_on_cocoon(web.nodes[selected_node])
        else:
            logger.warning(f"No valid memories found in {emotion}.")
