
import os
import json
import hashlib
import threading
import logging
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from collections import defaultdict
import math
import re
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

    def audit(self) -> Dict[str, datetime]:
        with self.lock:
            return {k: v["timestamp"] for k, v in self.store.items()}

# === BASE AGENT INTERFACE ===
class AegisAgent(ABC):
    def __init__(self, name: str, memory: NexusMemory):
        self.name = name
        self.memory = memory
        self.thread: Optional[threading.Thread] = None
        self.result: Dict[str, Any] = {}
        self.explanation: str = ""

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

    def register_agent(self, agent: AegisAgent) -> None:
        self.agents.append(agent)

    def dispatch(self, input_data: Dict[str, Any]) -> None:
        for agent in self.agents:
            agent.start(input_data)

        for agent in self.agents:
            if agent.thread:
                agent.thread.join()
                self.reports[agent.name] = agent.report()

    def get_reports(self) -> Dict[str, Dict[str, Any]]:
        return self.reports

# === ETHICAL SIGNAL AGENT ===
class EthosiaAgent(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        text = input_data.get("text", "")
        score = self.evaluate_ethics(text)
        self.memory.write(f"{self.name}_ethic_score", score, emotion_weight=0.8)
        self.result = {"ethical_score": score}
        self.explanation = f"EthosiaAgent evaluated input: '{text}' with ethical score {score}."

    def evaluate_ethics(self, text: str) -> float:
        keywords = ["harm", "lie", "steal", "hurt"]
        score = 1.0 - (sum(text.lower().count(word) for word in keywords) * 0.1)
        return max(0.0, min(1.0, score))

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation
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

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation
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

    def report(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "explanation": self.explanation
        }

# === EXECUTION ===
if __name__ == "__main__":
    council = AegisCouncil()
    council.register_agent(EthosiaAgent("EthosiaAgent", council.memory))
    council.register_agent(SapientiaAgent("SapientiaAgent", council.memory))
    council.register_agent(AegisCore("AegisCore", council.memory))

    sample_input = {"text": "Select data where user is not harmed."}
    council.dispatch(sample_input)

    reports = council.get_reports()
    print(json.dumps(reports, indent=2))
