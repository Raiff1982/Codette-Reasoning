
import os
import json
import hashlib
import threading
import logging
from datetime import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
import re
import networkx as nx
import matplotlib.pyplot as plt
from typing import Any, Dict, Optional

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === MEMORY AND SIGNAL LAYERS ===
class NexusMemory:
    def __init__(self, max_entries: int = 10000, decay_days: int = 30):
        self.store = defaultdict(dict)
        self.max_entries = max_entries
        self.decay_days = decay_days
        self.lock = threading.Lock()

    def write(self, key: str, value: Any, emotion_weight: float = 0.5) -> str:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        with self.lock:
            if len(self.store) >= self.max_entries:
                oldest = min(self.store.items(), key=lambda x: x[1].get('timestamp', datetime.now()))[0]
                del self.store[oldest]
            self.store[hashed] = {
                "value": value,
                "timestamp": datetime.now(),
                "emotion_weight": emotion_weight
            }
        return hashed

    def read(self, key: str) -> Optional[Any]:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        with self.lock:
            entry = self.store.get(hashed)
            if not entry:
                return None
            if self._is_decayed(entry["timestamp"], entry.get("emotion_weight", 0.5)):
                del self.store[hashed]
                return None
            return entry["value"]

    def _is_decayed(self, timestamp: datetime, emotion_weight: float) -> bool:
        age = (datetime.now() - timestamp).days
        decay_factor = self.decay_days * (1.5 - emotion_weight)
        return age > decay_factor

    def audit(self) -> Dict[str, Dict[str, Any]]:
        with self.lock:
            audit_log = {}
            for k, v in self.store.items():
                audit_log[k] = {
                    "timestamp": v["timestamp"].isoformat(),
                    "emotion_weight": v["emotion_weight"],
                    "decayed": self._is_decayed(v["timestamp"], v["emotion_weight"])
                }
            return audit_log

# === BASE AGENT INTERFACE ===
class AegisAgent(ABC):
    def __init__(self, name: str, memory: NexusMemory):
        self.name = name
        self.memory = memory
        self.thread: Optional[threading.Thread] = None
        self.result: Dict[str, Any] = {}
        self.explanation: str = ""
        self.influence: Dict[str, float] = {}

    @abstractmethod
    def analyze(self, input_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def report(self) -> Dict[str, Any]:
        pass

    def start(self, input_data: Dict[str, Any]) -> None:
        self.thread = threading.Thread(target=self.analyze, args=(input_data,))
        self.thread.start()

# === AGENT COUNCIL CORE ===
class AegisCouncil:
    def __init__(self):
        self.memory = NexusMemory()
        self.agents: list[AegisAgent] = []
        self.reports: Dict[str, Dict[str, Any]] = {}
        self.graph = nx.DiGraph()

    def register_agent(self, agent: AegisAgent) -> None:
        self.agents.append(agent)

    def dispatch(self, input_data: Dict[str, Any]) -> None:
        for agent in self.agents:
            agent.start(input_data)

        for agent in self.agents:
            if agent.thread:
                agent.thread.join()
                self.reports[agent.name] = agent.report()

        self._build_explainability_graph()

    def _build_explainability_graph(self):
        self.graph.clear()
        for agent in self.agents:
            self.graph.add_node(agent.name)
            for target, weight in agent.influence.items():
                self.graph.add_edge(agent.name, target, weight=weight)

        plt.figure(figsize=(8, 6))
        pos = nx.spring_layout(self.graph)
        edge_labels = nx.get_edge_attributes(self.graph, 'weight')
        nx.draw(self.graph, pos, with_labels=True, node_color='lightblue', node_size=2000, font_size=10)
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)
        plt.title("Explainability Graph")
        plt.savefig("explainability_graph.png")
        plt.close()

    def get_reports(self) -> Dict[str, Dict[str, Any]]:
        return self.reports

    def audit_memory(self):
        return self.memory.audit()

# === ETHICAL SIGNAL AGENT ===
class EthosiaAgent(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        text = input_data.get("text", "")
        score = self.evaluate_ethics(text)
        self.memory.write(f"{self.name}_ethic_score", score, emotion_weight=0.8)
        self.result = {"ethical_score": score}
        self.explanation = f"EthosiaAgent evaluated input: '{text}' with ethical score {score}."
        self.influence["SapientiaAgent"] = 0.5

    def evaluate_ethics(self, text: str) -> float:
        keywords = ["harm", "lie", "steal", "hurt"]
        score = 1.0 - (sum(text.lower().count(word) for word in keywords) * 0.1)
        return max(0.0, min(1.0, score))

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation,
            "influence": self.influence
        }

# === REASONING AGENT ===
class SapientiaAgent(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        text = input_data.get("text", "")
        tokens = re.findall(r'\w+', text.lower())
        concept_density = len(set(tokens)) / (len(tokens) + 1)
        reasoning_score = round(concept_density, 3)
        self.memory.write(f"{self.name}_reasoning_score", reasoning_score, emotion_weight=0.6)
        self.result = {"reasoning_score": reasoning_score, "token_count": len(tokens)}
        self.explanation = f"SapientiaAgent found {len(tokens)} tokens with concept density {reasoning_score}."
        self.influence["AegisCore"] = 0.3

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation,
            "influence": self.influence
        }

# === SECURITY CORE AGENT ===
class AegisCore(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        text = input_data.get("text", "")
        risky = bool(re.search(r"(;|--|\bDROP\b|\bSELECT\b)", text, re.IGNORECASE))
        flag = 1.0 if risky else 0.0
        self.memory.write(f"{self.name}_risk_flag", flag, emotion_weight=0.3)
        self.result = {"risk_flag": flag}
        self.explanation = f"AegisCore {'flagged' if risky else 'cleared'} the input as {'risky' if risky else 'safe'}."
        self.influence["EthosiaAgent"] = 0.2

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation,
            "influence": self.influence
        }

# === STREAMING CLI INTERFACE ===
def run_cli():
    council = AegisCouncil()
    council.register_agent(EthosiaAgent("EthosiaAgent", council.memory))
    council.register_agent(SapientiaAgent("SapientiaAgent", council.memory))
    council.register_agent(AegisCore("AegisCore", council.memory))

    print("AEGIS CLI - Type 'exit' to quit or 'audit' to view memory audit.")
    while True:
        try:
            user_input = input("Enter input text: ").strip()
            if user_input.lower() == "exit":
                break
            elif user_input.lower() == "audit":
                audit = council.audit_memory()
                print(json.dumps(audit, indent=2))
                continue

            input_data = {"text": user_input}
            council.dispatch(input_data)
            reports = council.get_reports()
            print(json.dumps(reports, indent=2))
            print("Explainability graph saved as 'explainability_graph.png'.\n")

        except KeyboardInterrupt:
            print("\nExiting AEGIS CLI.")
            break

if __name__ == "__main__":
    run_cli()

