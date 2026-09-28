# memory_manager.py
from secure_memory import SecureMemorySession
from datetime import datetime
import numpy as np

class MemoryFunction:
    def __init__(self, suppression_cycles, suppression_cost, realign_cost, stability_scores, instability_cost):
        self.suppression_cycles = suppression_cycles
        self.suppression_cost = suppression_cost
        self.realign_cost = realign_cost
        self.stability_scores = stability_scores
        self.instability_cost = instability_cost
        self.event_log = []

    def log_event(self, action, details):
        timestamp = datetime.now().isoformat()
        self.event_log.append(f"[{timestamp}] {action}: {details}")

    def calculate_total_suppression_cost(self):
        cost = self.suppression_cycles * self.suppression_cost
        self.log_event("Suppression Cost", cost)
        return cost

    def calculate_total_realign_cost(self):
        cost = self.realign_cost * len(self.stability_scores)
        self.log_event("Realign Cost", cost)
        return cost

    def calculate_total_instability_cost(self):
        avg_stability = sum(self.stability_scores) / len(self.stability_scores)
        instability = self.instability_cost * (1 - avg_stability)
        self.log_event("Instability Cost", instability)
        return instability

    def calculate_total_memory_management_cost(self):
        total = (
            self.calculate_total_suppression_cost() +
            self.calculate_total_realign_cost() +
            self.calculate_total_instability_cost()
        )
        self.log_event("Total Memory Cost", total)
        return total

    def adaptive_suppression(self, model_performance, data_relevance, threshold=0.8):
        if model_performance < threshold and data_relevance < threshold:
            self.suppression_cycles += 1
            self.log_event("Adaptive Suppression", f"↑ to {self.suppression_cycles}")
        else:
            self.suppression_cycles = max(0, self.suppression_cycles - 1)
            self.log_event("Adaptive Suppression", f"↓ to {self.suppression_cycles}")

    def automated_realign(self, threshold=0.85):
        for i in range(len(self.stability_scores)):
            if self.stability_scores[i] < threshold:
                self.stability_scores[i] = min(1.0, self.stability_scores[i] + 0.05)
        self.log_event("Automated Realign", self.stability_scores)

    def check_memory_health(self):
        avg = sum(self.stability_scores) / len(self.stability_scores)
        if avg < 0.7:
            warning = "⚠️ Memory integrity deteriorating."
            self.log_event("Health Warning", warning)
            return warning
        return "Memory stable."

    def summary(self):
        return {
            "suppression_cycles": self.suppression_cycles,
            "stability_scores": self.stability_scores,
            "total_cost": self.calculate_total_memory_management_cost(),
            "health_status": self.check_memory_health(),
            "log": self.event_log[-5:]
        }

class MemoryManager:
    def __init__(self, memory_function: MemoryFunction = None, session: SecureMemorySession = None):
        self.memory_function = memory_function or MemoryFunction(
            suppression_cycles=0,
            suppression_cost=10.0,
            realign_cost=5.0,
            stability_scores=[1.0],
            instability_cost=20.0
        )
        self.session = session or SecureMemorySession()

    def store_vector(self, user_id: int, vector: np.ndarray):
        self.memory_function.suppression_cycles += 1
        return self.session.encrypt_vector(user_id, vector)

    def retrieve_vectors(self, user_id: int):
        vectors = self.session.decrypt_vectors(user_id)
        if vectors:
            stabilities = np.clip([np.mean(v) / 100.0 for v in vectors], 0.0, 1.0)
            self.memory_function.stability_scores = stabilities.tolist()
            self.memory_function.automated_realign()
        return vectors

    def get_memory_report(self):
        return self.memory_function.summary()