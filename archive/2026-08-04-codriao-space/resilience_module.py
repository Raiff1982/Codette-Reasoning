# resilience_module.py
import datetime
from logging_testing_module import log_event

class SystemResilienceManager:
    """Provides self-healing, optimization, and error recovery routines."""

    def __init__(self):
        self.state = {
            "last_health_check": None,
            "hallucination_count": 0,
            "auto_restarts": 0,
            "failures": []
        }

    def check_system_health(self, data: dict, temp_threshold=35):
        self.state["last_health_check"] = datetime.datetime.utcnow().isoformat()
        if data["weather"]["temperature"] > temp_threshold:
            log_event("HEALTH_WARNING", {"temp": data["weather"]["temperature"]})
            return False
        return True

    def detect_hallucination(self, explanation: str) -> bool:
        red_flags = ["unknown", "magic", "best guess", "hypothetical", "imaginary"]
        if any(flag in explanation.lower() for flag in red_flags):
            self.state["hallucination_count"] += 1
            log_event("HALLUCINATION_ALERT", {"explanation": explanation})
            return True
        return False

    def optimize_response(self, response: str) -> str:
        optimized = response.strip().replace("\n", " ").replace("  ", " ")
        log_event("RESPONSE_OPTIMIZED", {"original_length": len(response), "optimized_length": len(optimized)})
        return optimized

    def attempt_self_healing(self, module_name: str):
        self.state["auto_restarts"] += 1
        action = f"Restarted or reloaded module: {module_name}"
        log_event("SELF_HEALING", {"module": module_name, "action": action})
        return action