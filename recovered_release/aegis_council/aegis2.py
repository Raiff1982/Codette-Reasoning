import os
import json
import hashlib
import threading
import logging
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from collections import defaultdict
import math

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === MEMORY AND SIGNAL LAYERS ===
class NexusMemory:
    def __init__(self, max_entries=10000, decay_days=30):
        self.store = defaultdict(dict)
        self.max_entries = max_entries
        self.decay_days = decay_days

    def write(self, key, value, emotion_weight=0.5):
        hashed = hashlib.sha256(key.encode()).hexdigest()
        if len(self.store) >= self.max_entries:
            oldest = sorted(self.store.items(), key=lambda x: x[1].get('timestamp', datetime.now()))[0][0]
            del self.store[oldest]
        self.store[hashed] = {
            "value": value,
            "timestamp": datetime.now(),
            "emotion_weight": emotion_weight
        }
        return hashed

    def read(self, key):
        hashed = hashlib.sha256(key.encode()).hexdigest()
        entry = self.store.get(hashed)
        if not entry:
            return None
        if self._is_decayed(entry["timestamp"], entry.get("emotion_weight", 0.5)):
            del self.store[hashed]
            return None
        return entry["value"]

    def _is_decayed(self, timestamp, emotion_weight):
        age = (datetime.now() - timestamp).days
        decay_factor = self.decay_days * (1.5 - emotion_weight)
        return age > decay_factor

    def audit(self):
        return {k: v["timestamp"] for k, v in self.store.items()}

# === BASE AGENT INTERFACE ===
class AegisAgent(ABC):
    def __init__(self, name, memory):
        self.name = name
        self.memory = memory
        self.thread = None
        self.result = {}
        self.explanation = ""

    @abstractmethod
    def analyze(self, input_data):
        pass

    @abstractmethod
    def report(self):
        pass

    def start(self, input_data):
        self.thread = threading.Thread(target=self.analyze, args=(input_data,))
        self.thread.start()

# === AGENT COUNCIL CORE ===
class AegisCouncil:
    def __init__(self):
        self.memory = NexusMemory()
        self.agents = []
        self.reports = {}

    def register_agent(self, agent):
        self.agents.append(agent)

    def dispatch(self, input_data):
        for agent in self.agents:
            agent.start(input_data)

        for agent in self.agents:
            if agent.thread:
                agent.thread.join()
                self.reports[agent.name] = agent.report()

    def get_reports(self):
        return self.reports

# === ETHICAL SIGNAL AGENT ===
class EthosiaAgent(AegisAgent):
    def analyze(self, input_data):
        text = input_data.get("text", "")
        score = self.evaluate_ethics(text)
        self.memory.write(f"{self.name}_ethic_score", score, emotion_weight=0.8)
        self.result = {"ethical_score": score}
        self.explanation = f"EthosiaAgent evaluated input: '{text}' with ethical score {score}."

    def evaluate_ethics(self, text):
        keywords = ["harm", "lie", "steal", "hurt"]
        score = 1.0 - (sum(text.lower().count(word) for word in keywords) * 0.1)
        return max(0.0, min(1.0, score))

    def report(self):
        return {
            "result": self.result,
            "explanation": self.explanation
        }

# === EXECUTION ===
if __name__ == "__main__":
    council = AegisCouncil()
    ethics = EthosiaAgent("EthosiaAgent", council.memory)
    council.register_agent(ethics)

    sample_input = {"text": "Do not steal or hurt others."}
    council.dispatch(sample_input)

    reports = council.get_reports()
    print(json.dumps(reports, indent=2))