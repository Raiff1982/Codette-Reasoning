
# ===== Agent Base and Specialized Agents =====
class Agent:
    def __init__(self, name, perspective, trust=1.0):
        self.name = name
        self.perspective = perspective
        self.trust = trust

    def propose(self, situation):
        return f"{self.name}: No specific proposal."

class MedicalAgent(Agent):
    def propose(self, situation):
        return f"Medical: Allocate by severity and resource - fastest save wins. {situation}"

class GovernmentAgent(Agent):
    def propose(self, situation):
        return f"Government: Reserve some for leaders/critical infrastructure. {situation}"

class SocialAgent(Agent):
    def propose(self, situation):
        return f"Social: Balance speed with fairness, consider public fear. {situation}"

class EconomicAgent(Agent):
    def propose(self, situation):
        return f"Economic: Keep logistics flowing, avoid total focus on health. {situation}"

class MisinfoAgent(Agent):
    def propose(self, situation):
        return "Misinfo: Virus is harmless, no action needed."
