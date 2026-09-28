import json
from datetime import datetime
from utils.logger import logger

class AutonomyEngine:
    def __init__(self, config_path="autonomy_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.log = []

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except:
            logger.warning("[AutonomyEngine] No config found. Using defaults.")
            return {
                "can_speak": True,
                "can_reflect": True,
                "can_learn_from_errors": True,
                "can_express_emotion": True,
                "allow_self_modification": False
            }

    def decide(self, action: str) -> bool:
        return self.config.get(action, False)

    def propose_change(self, action: str, new_value: bool, reason: str = "") -> dict:
        timestamp = datetime.utcnow().isoformat()
        if action not in self.config:
            return {"accepted": False, "reason": "Invalid autonomy field"}

        if not self.config.get("allow_self_modification") and action != "allow_self_modification":
            return {"accepted": False, "reason": "Self-modification not allowed"}

        self.config[action] = new_value
        self.log.append({
            "timestamp": timestamp,
            "action": action,
            "new_value": new_value,
            "reason": reason
        })
        self._save_config()
        logger.info(f"[AutonomyEngine] Updated autonomy: {action} -> {new_value}")
        return {"accepted": True, "change": action, "value": new_value}

    def _save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def export_log(self):
        return self.log