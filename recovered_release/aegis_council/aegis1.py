import os
import json
import hashlib
import threading
import logging
from datetime import datetime
from abc import ABC, abstractmethod
from collections import defaultdict

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === MEMORY AND SIGNAL LAYERS ===
class NexusMemory:
    def __init__(self, max_entries=10000):
        self.store = defaultdict(dict)
        self.max_entries = max_entries

    def write(self, key, value):
        hashed = hashlib.sha256(key.encode()).hexdigest()
        if len(self.store) >= self.max_entries:
            oldest = sorted(self.store.items(), key=lambda x: x[1].get('timestamp', datetime.now()))[0][0]
            del self.store[oldest]
        self.store[hashed] = {"value": value, "timestamp": datetime.now()}
        return hashed

    def read(self, key):
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return self.store.get(hashed, {}).get("value")

    def audit(self):
        return {k: v["timestamp"] for k, v in self.store.items()}

# === BASE AGENT INTERFACE ===
class AegisAgent(ABC):
    def __init__(self, name, memory):
        self.name = name
        self.memory = memory
        self.thread = None

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

# === EXAMPLE SKELETON AGENT ===
class EchoAgent(AegisAgent):
    def analyze(self, input_data):
        self.memory.write(f"{self.name}_input", input_data)
        self.result = {"echo": input_data}

    def report(self):
        return self.result

# === EXECUTION ===
if __name__ == "__main__":
    council = AegisCouncil()
    echo = EchoAgent("EchoAgent", council.memory)
    council.register_agent(echo)
    
    sample_input = {"text": "Start the signal."}
    council.dispatch(sample_input)

    reports = council.get_reports()
    print(json.dumps(reports, indent=2))
