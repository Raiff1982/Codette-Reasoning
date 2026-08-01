"""
Recovered from Document (12) copy.docx.

Source was stored inside a Word document; the original filename does not
describe the contents.
"""


import json
import hashlib
import random
from typing import List, Dict, Tuple
import networkx as nx
import matplotlib.pyplot as plt
class TensionSpike(Exception):
    def __init__(self, node, reason):
        self.node = node
        self.reason = reason
        super().__init__(f"Tension spike at node '{node}': {reason}")
class SpiderNode:
    def __init__(self, concept: str):
        self.concept = concept
        self.signature = hashlib.sha256(concept.encode()).hexdigest()[:12]
        self.links: List[str] = []
        self.tension: float = 0.0
    def add_link(self, node_id: str):
        if node_id not in self.links:
            self.links.append(node_id)
    def apply_tension(self, intensity: float):
        self.tension += intensity
        if self.tension > 1.0:
            raise TensionSpike(self.concept, f"Tension={self.tension:.2f}")
class QuantumSpiderweb:
    def __init__(self):
        self.web: Dict[str, SpiderNode] = {}
        self.recent_paths: List[str] = []
    def register_concept(self, concept: str):
        node = SpiderNode(concept)
        self.web[node.signature] = node
        return node
    def entangle(self, a: str, b: str):
        sig_a = hashlib.sha256(a.encode()).hexdigest()[:12]
        sig_b = hashlib.sha256(b.encode()).hexdigest()[:12]
        if sig_a not in self.web:
            self.web[sig_a] = SpiderNode(a)
        if sig_b not in self.web:
            self.web[sig_b] = SpiderNode(b)
        self.web[sig_a].add_link(sig_b)
        self.web[sig_b].add_link(sig_a)
    def observe_tension(self, concept: str, strain: float):
        sig = hashlib.sha256(concept.encode()).hexdigest()[:12]
        if sig in self.web:
            self.web[sig].apply_tension(strain)
    def trace_web(self, concept: str) -> Tuple[str, List[str]]:
        sig = hashlib.sha256(concept.encode()).hexdigest()[:12]
        if sig in self.web:
            node = self.web[sig]
            return (node.concept, node.links)
        return (concept, [])
    def pulse_scan(self) -> List[str]:
        warnings = []
        for node in self.web.values():
            if node.tension > 0.7:
                warnings.append(f"Warning: High strain on '{node.concept}' ({node.tension:.2f})")
        return warnings
    def save_to_file(self, file_path: str):
        with open(file_path, 'w') as file:
            json.dump(self.web, file, default=lambda o: o.__dict__, indent=4)
    def load_from_file(self, file_path: str):
        with open(file_path, 'r') as file:
            data = json.load(file)
            for key, value in data.items():
                node = SpiderNode(value['concept'])
                node.signature = value['signature']
                node.links = value['links']
                node.tension = value['tension']
                self.web[key] = node
    def visualize(self):
        graph = nx.Graph()
        for node in self.web.values():
            graph.add_node(node.concept)
            for link in node.links:
                linked_node = self.web[link].concept
                graph.add_edge(node.concept, linked_node)
        nx.draw(graph, with_labels=True)
        plt.show()
# Example usage
quantum_spiderweb = QuantumSpiderweb()
node_a = quantum_spiderweb.register_concept("Artificial Intelligence")
node_b = quantum_spiderweb.register_concept("Machine Learning")
quantum_spiderweb.entangle("Artificial Intelligence", "Machine Learning")
try:
    quantum_spiderweb.observe_tension("Artificial Intelligence", 0.8)
    quantum_spiderweb.observe_tension("Artificial Intelligence", 0.3)
except TensionSpike as e:
    print(e)
concept, links = quantum_spiderweb.trace_web("Artificial Intelligence")
print(f"Concept: {concept}, Links: {links}")
warnings = quantum_spiderweb.pulse_scan()
for warning in warnings:
    print(warning)
quantum_spiderweb.save_to_file("spiderweb.json")
quantum_spiderweb.load_from_file("spiderweb.json")
quantum_spiderweb.visualize()
