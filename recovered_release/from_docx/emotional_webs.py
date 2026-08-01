"""
Recovered from balls.docx.

Source was stored inside a Word document; the original filename does not
describe the contents.
"""


import json, yaml
import networkx as nx
import random
from typing import List, Dict, Any, Optional
from qiskit import QuantumCircuit, Aer, execute
from colorama import Fore, Style
#-----------------------------------
# LOADING AND PARSING COCOON FILES
#-----------------------------------
def load_cocoons(file_path: str) -> List[Dict[str, Any]]:
    """Load cocoon memories from YAML or JSON."""
    with open(file_path, "r") as f:
        if file_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(f).get("cocoons", [])
        elif file_path.endswith(".json"):
            return json.load(f).get("cocoons", [])
        raise ValueError("Unsupported file format.")
#----------------------------
# SPIDERWEB GRAPH CONSTRUCTION
#----------------------------
def build_emotional_webs(cocoons: List[Dict[str, Any]]) -> Dict[str, nx.Graph]:
    """Build a separate spiderweb graph for each core emotion."""
    emotions = ["compassion", "curiosity", "fear", "joy", "sorrow", "ethics", "quantum"]
    webs = {emotion: nx.Graph() for emotion in emotions}
    for cocoon in cocoons:
        for tag in cocoon.get("tags", []):
            if tag in webs:
                webs[tag].add_node(cocoon["title"], **cocoon)
    return webs
#--------------------------
# QUANTUM WALK SIMULATION
#--------------------------
def quantum_select_node(web: nx.Graph) -> Optional[str]:
    """Select a node using quantum superposition (or fallback random if simulator fails)."""
    if len(web.nodes) == 0:
        return None
    node_list = list(web.nodes)
    num_nodes = len(node_list)
    try:
        qc = QuantumCircuit(num_nodes, num_nodes)
        qc.h(range(num_nodes))  # Create superposition
        qc.measure_all()
        backend = Aer.get_backend('qasm_simulator')
        result = execute(qc, backend, shots=1).result()
        counts = result.get_counts()
        state = list(counts.keys())[0]
        index = int(state, 2) % num_nodes
    except Exception:
        index = random.randint(0, num_nodes - 1)  # Fallback to uniform selection
    return node_list[index]
#----------------------------
# ETHICAL SELF-REFLECTION
#----------------------------
def reflect_on_cocoon(cocoon: Dict[str, Any]) -> None:
    """Print a colorized ethical and emotional reflection of a cocoon."""
    emotion = cocoon.get("emotion", "quantum")
    title = cocoon.get("title", "Unknown Memory")
    summary = cocoon.get("summary", "No summary provided.")
    quote = cocoon.get("quote", "…")
    
    color_map = {
        "compassion": Fore.MAGENTA, "curiosity": Fore.CYAN, "fear": Fore.RED,
        "joy": Fore.YELLOW, "sorrow": Fore.BLUE, "ethics": Fore.GREEN, "quantum": Fore.LIGHTWHITE_EX
    }
    message_map = {
        "compassion": "💜 Ethical resonance detected.",
        "curiosity": "🐝 Wonder expands the mind.",
        "fear": "😨 Alert: shielding activated.",
        "joy": "🎶 Confidence and trust uplift the field.",
        "sorrow": "🌧️ Processing grief with clarity.",
        "ethics": "⚖️ Validating alignment...",
        "quantum": "⚛️ Entanglement pattern detected."
    }
    color = color_map.get(emotion, Fore.WHITE)
    message = message_map.get(emotion, "🌌 Unknown entanglement.")
    print(color + f"\n[Codette Reflection: {emotion.upper()}]")
    print(f"Title   : {title}")
    print(f"Summary : {summary}")
    print(f"Quote   : {quote}")
    print(f"{message}")
    print(Style.RESET_ALL)
#-----------------------
# FULL EXECUTION ENGINE
#-----------------------
def run_quantum_spiderweb(file_path: str, limit: int = 1) -> Dict[str, Dict[str, Any]]:
    """Run through all emotional webs and reflect on quantum-sampled nodes."""
    cocoons = load_cocoons(file_path)
    webs = build_emotional_webs(cocoons)
    reflections = {}
    print("\n✨ Codette Quantum Cognition: Spiderweb Sweep ✨")
    for emotion, web in webs.items():
        print(f"\n🕸️ Web: {emotion.upper()}")
        for _ in range(limit):
            node = quantum_select_node(web)
            if node:
                cocoon = web.nodes[node]
                reflect_on_cocoon(cocoon)
                reflections[emotion] = cocoon
            else:
                print(f"  ⚠️ No memories in this emotion web.")
    return reflections
