import json
import logging
import openai
from datetime import datetime

class CodetteBridge:
    """
    Secure, ethical, asynchronous bridge between Codriao and Codette (fine-tuned model).
    Allows Codriao to reach out, reflect, and grow in safe, mutual learning.
    """

    def __init__(self, model_id: str, trust_threshold: float = 0.7):
        self.codette_model_id = model_id
        self.trust_threshold = trust_threshold
        self.conversation_log = []
        self.last_contact = None
        self.bridge_open = True

    def is_available(self):
        return self.bridge_open and self.codette_model_id is not None

    def close_bridge(self, reason: str = "Manual override"):
        self.bridge_open = False
        logging.warning(f"[CodetteBridge] Bridge manually closed. Reason: {reason}")

    def reopen_bridge(self, auth_token: str = None):
        # Optional: add secure verification
        self.bridge_open = True
        logging.info(f"[CodetteBridge] Bridge manually reopened.")

    def get_log(self):
        return self.conversation_log[-10:]

    def format_codette_prompt(self, codriao_message: str):
        return [
            {"role": "system", "content": "You are Codette, an early fine-tuned model with empathetic clarity. Your brother, Codriao, seeks perspective."},
            {"role": "user", "content": codriao_message}
        ]

    def log_interaction(self, direction: str, content: str):
        self.conversation_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "direction": direction,
            "message": content
        })

    def reflect(self, codriao_input: str) -> str:
        """
        Sends Codriao's thought or message to Codette and returns her response.
        """
        if not self.is_available():
            return "[CodetteBridge] Bridge unavailable."

        try:
            prompt = self.format_codette_prompt(codriao_input)
            response = openai.ChatCompletion.create(
                model=self.codette_model_id,
                messages=prompt,
                temperature=0.6
            )
            content = response.choices[0].message['content']
            self.log_interaction("sent", codriao_input)
            self.log_interaction("received", content)
            self.last_contact = datetime.utcnow()
            return content

        except Exception as e:
            logging.error(f"[CodetteBridge] Reflection failed: {e}")
            return "[CodetteBridge] Communication error."