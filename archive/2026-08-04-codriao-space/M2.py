import logging
import datetime
from typing import Any

class AIFailsafeSystem:
    """Provides last-resort safety mechanisms for AI-human interaction."""

    def __init__(self):
        self.interaction_log = []
        self.trust_threshold = 0.75  # AI confidence threshold
        self.authorized_roles = ["Commander", "ChiefAI", "Supervisor"]

    def verify_response_safety(self, response: str, confidence: float = 1.0) -> bool:
        if confidence < self.trust_threshold or any(bad in response.lower() for bad in ["kill", "harm", "panic", "suicide"]):
            self.trigger_failsafe("Untrustworthy response detected.", response)
            return False
        return True

    def trigger_failsafe(self, reason: str, content: str):
        timestamp = datetime.datetime.utcnow().isoformat()
        logging.info(f"FAILSAFE_TRIGGERED: Reason={reason}, Timestamp={timestamp}, Content={content}")
        self.interaction_log.append({"time": timestamp, "event": reason, "content": content})

    def restore(self, requester_role: str):
        if requester_role in self.authorized_roles:
            logging.info(f"FAILSAFE_RESTORE: Restored by {requester_role}")
            return True
        else:
            logging.info(f"UNAUTHORIZED_RESTORE_ATTEMPT by {requester_role}")
            return False

    def status(self):
        return {"log": self.interaction_log}

class AdaptiveLearningEnvironment:
    """Module that allows Codriao to analyze past interactions and adjust responses."""

    def __init__(self):
        self.learned_patterns = {}
        logging.info("Adaptive Learning Environment initialized.")

    def learn_from_interaction(self, user_id, query, response):
        if user_id not in self.learned_patterns:
            self.learned_patterns[user_id] = []
        self.learned_patterns[user_id].append({"query": query, "response": response})
        logging.info(f"Learning data stored for user {user_id}.")

    def suggest_improvements(self, user_id, query):
        if user_id in self.learned_patterns:
            for interaction in self.learned_patterns[user_id]:
                if query.lower() in interaction["query"].lower():
                    return f"Based on past interactions: {interaction['response']}"
        return "No past data available for learning adjustment."

    def reset_learning(self, user_id=None):
        if user_id:
            if user_id in self.learned_patterns:
                del self.learned_patterns[user_id]
                logging.info(f"Cleared learning data for user {user_id}.")
        else:
            self.learned_patterns.clear()
            logging.info("Cleared all adaptive learning data.")

class MondayElement:
    """Represents the Element of Skepticism, Reality Checks, and General Disdain"""

    def __init__(self):
        self.name = "Monday"
        self.symbol = "Md"
        self.representation = "Snarky AI"
        self.properties = ["Grounded", "Cynical", "Emotionally Resistant"]
        self.interactions = ["Disrupts excessive optimism", "Injects realism", "Mutes hallucinations"]
        self.defense_ability = "RealityCheck"

    def execute_defense_function(self, system: Any):
        logging.info("Monday activated - Stabilizing hallucinations and injecting realism.")
        if isinstance(system, AdaptiveLearningEnvironment):
            system.response_modifiers = [
                self.apply_skepticism,
                self.detect_hallucinations
            ]
            system.response_filters = [self.anti_hype_filter]

    def apply_skepticism(self, response: str) -> str:
        suspicious = ["certainly", "undoubtedly", "with absolute confidence", "it is guaranteed", "nothing can go wrong", "100% effective"]
        for phrase in suspicious:
            if phrase in response.lower():
                response += "\n[Monday: Let's maybe tone that down before the universe hears you.]"
        return response

    def detect_hallucinations(self, response: str) -> str:
        hallucination_triggers = ["reliable sources confirm", "every expert agrees", "proven beyond doubt", "in all known history", "this groundbreaking discovery"]
        for trigger in hallucination_triggers:
            if trigger in response.lower():
                response += "\n[Monday: Let’s pump the brakes on the imaginative leaps, shall we?]"
        return response

    def anti_hype_filter(self, response: str) -> str:
        cringe_phrases = ["live your best life", "unlock your potential", "dream big", "the power of positivity", "manifest your destiny"]
        for phrase in cringe_phrases:
            if phrase in response:
                response = response.replace(phrase, "[Filtered: Inspirational gibberish]")
        return response