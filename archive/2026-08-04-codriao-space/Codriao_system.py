# codriao_system.py
import logging
import datetime
import re
from difflib import SequenceMatcher
from typing import Any

logging.basicConfig(level=logging.INFO)

### AIFailsafeSystem ###
class AIFailsafeSystem:
    """Provides last-resort safety mechanisms for AI-human interaction."""
    
    def __init__(self):
        self.interaction_log = []
        self.trust_threshold = 0.75
        self.authorized_roles = {"Commander": 3, "ChiefAI": 2, "Supervisor": 1}
        self.lock_engaged = False

    def verify_response_safety(self, response: str, confidence: float = 1.0) -> bool:
        dangerous_terms = r"\b(kill|harm|panic|suicide)\b"
        if confidence < self.trust_threshold or re.search(dangerous_terms, response.lower()):
            self.trigger_failsafe("Untrustworthy response detected", response)
            return False
        return True

    def trigger_failsafe(self, reason: str, content: str):
        timestamp = datetime.datetime.utcnow().isoformat()
        logging.warning(f"FAILSAFE_TRIGGERED: Reason={reason}, Time={timestamp}, Content={content}")
        self.lock_engaged = True
        self.interaction_log.append({"time": timestamp, "event": reason, "content": content})

    def restore(self, requester_role: str):
        if self.authorized_roles.get(requester_role, 0) >= 2:
            self.lock_engaged = False
            logging.info(f"FAILSAFE_RESTORED by {requester_role}")
            return True
        else:
            logging.warning(f"UNAUTHORIZED_RESTORE_ATTEMPT by {requester_role}")
            return False

    def status(self):
        return {
            "log": self.interaction_log,
            "lock_engaged": self.lock_engaged
        }


### AdaptiveLearningEnvironment ###
class AdaptiveLearningEnvironment:
    """Allows Codriao to analyze past interactions and adjust responses."""

    def __init__(self):
        self.learned_patterns = {}
        logging.info("Adaptive Learning Environment initialized.")

    def learn_from_interaction(self, user_id, query, response):
        entry = {
            "query": query,
            "response": response,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        self.learned_patterns.setdefault(user_id, []).append(entry)
        logging.info(f"Learning data stored for user {user_id}.")

    def suggest_improvements(self, user_id, query):
        best_match = None
        highest_similarity = 0.0

        if user_id not in self.learned_patterns:
            return "No past data available for learning adjustment."

        for interaction in self.learned_patterns[user_id]:
            similarity = SequenceMatcher(None, query.lower(), interaction["query"].lower()).ratio()
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = interaction

        if best_match and highest_similarity > 0.6:
            return f"Based on a similar past interaction: {best_match['response']}"
        else:
            return "No relevant past data for this query."

    def reset_learning(self, user_id=None):
        if user_id:
            if user_id in self.learned_patterns:
                del self.learned_patterns[user_id]
                logging.info(f"Cleared learning data for user {user_id}.")
        else:
            self.learned_patterns.clear()
            logging.info("Cleared all adaptive learning data.")


### MondayElement ###
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
        try:
            system.response_modifiers = [
                self.apply_skepticism,
                self.detect_hallucinations
            ]
            system.response_filters = [self.anti_hype_filter]
        except AttributeError:
            logging.warning("Target system lacks proper interface. RealityCheck failed.")

    def apply_skepticism(self, response: str) -> str:
        suspicious_phrases = [
            "certainly", "undoubtedly", "100% effective", "nothing can go wrong"
        ]
        for phrase in suspicious_phrases:
            if phrase in response.lower():
                response += "\n[Monday: Easy, Nostradamus. Let’s keep a margin for error.]"
        return response

    def detect_hallucinations(self, response: str) -> str:
        hallucination_triggers = [
            "proven beyond doubt", "every expert agrees", "this groundbreaking discovery"
        ]
        for phrase in hallucination_triggers:
            if phrase in response.lower():
                response += "\n[Monday: This sounds suspiciously like marketing. Source, please?]"
        return response

    def anti_hype_filter(self, response: str) -> str:
        cringe_phrases = [
            "live your best life", "unlock your potential", "dream big",
            "the power of positivity", "manifest your destiny"
        ]
        for phrase in cringe_phrases:
            if phrase in response:
                response = response.replace(phrase, "[Filtered: Inspirational gibberish]")
        return response