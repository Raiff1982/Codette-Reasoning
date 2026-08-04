import logging

class AdaptiveLearningEnvironment:
    """
    A lightweight module that allows Codriao to analyze past interactions
    and adjust its responses over time.
    """

    def __init__(self):
        self.learned_patterns = {}
        logging.info("Adaptive Learning Environment initialized.")

    def learn_from_interaction(self, user_id, query, response):
        """ Store user queries and responses for future adaptation. """
        if user_id not in self.learned_patterns:
            self.learned_patterns[user_id] = []
        self.learned_patterns[user_id].append({"query": query, "response": response})
        logging.info(f"Stored learning data for user {user_id}.")

    def suggest_improvements(self, user_id, query):
        """ Provide an improved response based on past learning. """
        if user_id in self.learned_patterns:
            for interaction in self.learned_patterns[user_id]:
                if query.lower() in interaction["query"].lower():
                    return f"Based on past interactions: {interaction['response']}"
        return "No past data available for learning adjustment."

    def reset_learning(self, user_id=None):
        """ Clear learned patterns for a specific user or all users. """
        if user_id:
            if user_id in self.learned_patterns:
                del self.learned_patterns[user_id]
                logging.info(f"Cleared learning data for user {user_id}.")
        else:
            self.learned_patterns.clear()
            logging.info("Cleared all adaptive learning data.")
