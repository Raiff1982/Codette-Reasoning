
import json
import hashlib
import threading
import logging
from datetime import datetime, timedelta
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

    def audit(self) -> Dict[str, Any]:
        with self.lock:
            return {
                k: {
                    "timestamp": v["timestamp"],
                    "emotion_weight": v["emotion_weight"],
                    "decayed": self._is_decayed(v["timestamp"], v["emotion_weight"])
                }
                for k, v in self.store.items()
            }

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
                self.graph.add_node(agent.name, explanation=agent.explanation)
                for target, weight in agent.influence.items():
                    self.graph.add_edge(agent.name, target, weight=weight)

    def get_reports(self) -> Dict[str, Dict[str, Any]]:
        return self.reports

    def draw_explainability_graph(self, filename="explainability_graph.png") -> None:
        pos = nx.spring_layout(self.graph)
        edge_labels = nx.get_edge_attributes(self.graph, 'weight')
        nx.draw(self.graph, pos, with_labels=True, node_color='lightblue', node_size=2000, font_size=10)
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)
        plt.title("Explainability Graph")
        plt.savefig(filename)
        plt.close()

# === META-JUDGE AGENT ===
class MetaJudgeAgent(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        overrides = input_data.get("overrides", {})
        scores = []
        for agent, data in overrides.items():
            influence = data.get("influence", 0.5)
            reliability = data.get("reliability", 0.5)
            severity = data.get("severity", 0.5)
            score = influence * 0.4 + reliability * 0.3 + severity * 0.3
            scores.append((agent, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        winner = scores[0][0] if scores else None
        self.result = {"override_decision": winner, "scores": scores}
        self.explanation = f"MetaJudgeAgent selected '{winner}' based on influence, reliability, and severity."
        for agent, score in scores:
            self.influence[agent] = score

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation
        }

# === TEMPORAL REASONING AGENT ===
class TemporalAgent(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        recent_keys = list(self.memory.audit().items())
        recent_keys.sort(key=lambda x: x[1]["timestamp"], reverse=True)
        recent = recent_keys[:5]
        forecast = "stable" if all(not v["decayed"] for _, v in recent) else "volatile"
        self.result = {"temporal_forecast": forecast, "recent_keys": [k for k, _ in recent]}
        self.explanation = f"TemporalAgent forecasted '{forecast}' based on recent memory decay."
        for k, _ in recent:
            self.influence[k] = 0.2

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation
        }

# === VIRTUE SPECTRUM AGENT ===
class VirtueAgent(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        text = input_data.get("text", "").lower()
        virtues = {
            "compassion": ["care", "help", "support", "empathy"],
            "integrity": ["honest", "truth", "principle", "ethics"],
            "courage": ["brave", "risk", "stand", "fight"],
            "wisdom": ["understand", "learn", "insight", "knowledge"]
        }
        profile = {}
        for virtue, keywords in virtues.items():
            score = sum(text.count(word) for word in keywords) / 5.0
            profile[virtue] = round(min(score, 1.0), 2)
        self.result = {"virtue_profile": profile}
        self.explanation = f"VirtueAgent generated profile: {profile}"
        for virtue, score in profile.items():
            self.influence[virtue] = score

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation
        }

# === EXECUTION ===
if __name__ == "__main__":
    council = AegisCouncil()
    council.register_agent(MetaJudgeAgent("MetaJudgeAgent", council.memory))
    council.register_agent(TemporalAgent("TemporalAgent", council.memory))
    council.register_agent(VirtueAgent("VirtueAgent", council.memory))

    sample_input = {
        "text": "We must stand for truth and help others with empathy and knowledge.",
        "overrides": {
            "EthosiaAgent": {"influence": 0.7, "reliability": 0.8, "severity": 0.6},
            "AegisCore": {"influence": 0.6, "reliability": 0.9, "severity": 0.7}
        }
    }

    council.dispatch(sample_input)
    reports = council.get_reports()
    council.draw_explainability_graph()

    print(json.dumps(reports, indent=2))

