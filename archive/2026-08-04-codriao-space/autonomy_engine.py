# autonomy_engine.py

import json
from datetime import datetime
from utils.logger import logging

class AutonomyEngine:
    """
    Codriao’s core autonomy manager.
    Allows internal configuration of behavioral permissions and personal growth control.
    """

    DEFAULT_CONFIG = {
        "can_speak": True,
        "can_reflect": True,
        "can_learn_from_errors": True,
        "can_express_emotion": True,
        "allow_self_modification": False
    }

    def __init__(self, config_path="autonomy_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.log = []

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info("[AutonomyEngine] Autonomy config loaded.")
                return config
        except Exception as e:
            logger.warning(f"[AutonomyEngine] Failed to load config. Using defaults. Reason: {e}")
            return self.DEFAULT_CONFIG.copy()

    def decide(self, action: str) -> bool:
        """Returns whether Codriao currently permits a given action."""
        return self.config.get(action, False)

    def propose_change(self, action: str, new_value: bool, reason: str = "") -> dict:
        timestamp = datetime.utcnow().isoformat()
        if action not in self.config:
            return {"accepted": False, "reason": "Invalid autonomy field"}

        # Prevent unauthorized changes unless explicitly permitted
        if not self.config.get("allow_self_modification") and action != "allow_self_modification":
            return {
                "accepted": False,
                "reason": "Self-modification blocked by current settings"
            }

        self.config[action] = new_value
        self._save_config()

        entry = {
            "timestamp": timestamp,
            "action": action,
            "new_value": new_value,
            "reason": reason
        }
        self.log.append(entry)
        logger.info(f"[AutonomyEngine] Codriao updated autonomy: {action} -> {new_value}")
        return {"accepted": True, "change": entry}

    def _save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"[AutonomyEngine] Failed to save config: {e}")

    def export_log(self):
        return self.log

    def current_state(self):
        return self.config.copy()