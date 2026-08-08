# anomaly_score.py

import datetime

class AnomalyScorer:
    def __init__(self):
        self.history = []

    def score_event(self, event_type: str, data: dict) -> dict:
        base_score = {
            "unauthorized_access": 80,
            "unexpected_output": 50,
            "module_instability": 60,
            "unknown_connection": 90,
            "philosophical_dissonance": 40,
        }.get(event_type, 10)

        # Increase score if suspicious data is present
        if data.get("confidence") and data["confidence"] < 0.4:
            base_score += 20

        if "kill" in data.get("content", "").lower():
            base_score += 50

        result = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "event": event_type,
            "score": min(base_score, 100),
            "notes": f"Scored anomaly: {event_type}"
        }

        self.history.append(result)
        return result

    def get_history(self):
        return self.history