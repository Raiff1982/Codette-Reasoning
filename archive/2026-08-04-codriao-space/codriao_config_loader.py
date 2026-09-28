
import json
import os

class CodriaoConfig:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.settings = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file {self.config_path} not found.")
        
        with open(self.config_path, "r") as file:
            return json.load(file)

    def get(self, key, default=None):
        keys = key.split(".")
        value = self.settings
        for k in keys:
            value = value.get(k, {})
        return value if value else default

# Example Usage:
if __name__ == "__main__":
    config = CodriaoConfig()
    print("AI Capabilities:", config.get("ai_capabilities"))
    print("Security Settings:", config.get("security_settings"))
