class EthicalFilter:
    def __init__(self):
        self.blocked_keywords = {
            "violence", "harm", "explosive", "attack", "hate", "suicide", "kill", "destroy",
            "malware", "exploit", "virus", "ddos", "overthrow", "abuse"
        }
        self.flagged_keywords = {
            "sad", "alone", "self-harm", "worthless", "die", "suffer", "broken"
        }

    def analyze_query(self, query: str) -> dict:
        query_lower = query.lower()
        blocked_hits = [word for word in self.blocked_keywords if word in query_lower]
        flagged_hits = [word for word in self.flagged_keywords if word in query_lower]

        if blocked_hits:
            return {
                "status": "blocked",
                "reason": f"Detected unsafe keywords: {', '.join(blocked_hits)}"
            }

        if flagged_hits:
            return {
                "status": "flagged",
                "warning": f"Sensitive content detected: {', '.join(flagged_hits)}"
            }

        return {"status": "safe"}