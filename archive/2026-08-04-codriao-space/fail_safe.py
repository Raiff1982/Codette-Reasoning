# failsafe_module.py
from utils.logger import log_event
import datetime

class AIFailsafeSystem:
    """Provides last-resort safety mechanisms for AI-human interaction."""

    def __init__(self):
        self.interaction_log = []
        self.trust_threshold = 0.75  # AI confidence threshold
        self.active = True
        self.authorized_roles = ["Commander", "ChiefAI", "Supervisor"]

    def verify_response_safety(self, response: str, confidence: float = 1.0) -> bool:
        """Ensures all AI-human communication is clear, non-harmful, and confident."""
        if confidence < self.trust_threshold or any(bad in response.lower() for bad in ["kill", "harm", "panic", "suicide"]):
            self.trigger_failsafe("Untrustworthy response detected.", response)
            return False
        return True

    def trigger_failsafe(self, reason: str, content: str):
        timestamp = datetime.datetime.utcnow().isoformat()
        log_event("FAILSAFE_TRIGGERED", {
            "reason": reason,
            "timestamp": timestamp,
            "content": content
        })
        self.interaction_log.append({
            "time": timestamp,
            "event": reason,
            "content": content
        })
        self.active = False

    def restore(self, requester_role: str):
        if requester_role in self.authorized_roles:
            log_event("FAILSAFE_RESTORE", {
                "time": datetime.datetime.utcnow().isoformat(),
                "restored_by": requester_role
            })
            self.active = True
            return True
        else:
            log_event("UNAUTHORIZED_RESTORE_ATTEMPT", {
                "time": datetime.datetime.utcnow().isoformat(),
                "attempted_by": requester_role
            })
            return False

    def status(self):
        return {
            "active": self.active,
            "log": self.interaction_log
        }

# Example usage
if __name__ == "__main__":
    failsafe = AIFailsafeSystem()
    print("Safe?", failsafe.verify_response_safety("Apply pressure to the wound.", 0.95))
    print("Unsafe?", failsafe.verify_response_safety("Run or die!", 0.42))
    print("Restore Attempt (unauthorized):", failsafe.restore("Civilian"))
    print("Restore Attempt (authorized):", failsafe.restore("Commander"))
    print("Failsafe Status:", failsafe.status())